#!/usr/bin/env python3
"""Correctness checks for the precompiled timetable search index."""

from __future__ import annotations

import json
import sys
import unittest
from datetime import date, datetime, time, timedelta
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from route_itineraries import (  # noqa: E402
    ScheduledInstanceIndex,
    annotate_transit_charge,
    candidate_sweep_seed,
    candidate_departure_preference,
    candidate_dominates,
    default_origin_boarding_buffer_minutes,
    edge_instance,
    find_itineraries,
    is_redundant_consecutive_road,
    next_adaptive_sweep_seeds,
    nonlocal_route_ids,
    prune_return_only_dead_ends,
    same_provider_direct_ferry_connection,
    prefix_road_shift,
)
from route_itinerary import next_scheduled_instance, transfer_risk  # noqa: E402


class FastRouteSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.graph = json.loads((ROOT / "routing-graph.json").read_text())

    def test_precompiled_instances_match_legacy_timetable_interpretation(self) -> None:
        start = datetime.combine(date(2026, 11, 3), time.min)
        deadline = datetime.combine(date(2026, 11, 3), time.max)
        routes = {item["id"]: item for item in self.graph["routes"]}
        index = ScheduledInstanceIndex(
            self.graph["edges"], routes, start, deadline, "typical",
        )
        checked = 0
        for edge in self.graph["edges"]:
            if edge["kind"] != "scheduled_service":
                continue
            legacy = next_scheduled_instance(
                edge, routes[edge["routeId"]], start, "typical",
            )
            if legacy is not None and legacy["departure"] > deadline:
                legacy = None
            self.assertEqual(index.next(edge, start), legacy, edge["id"])
            checked += 1
        self.assertGreater(checked, 100)

    def test_search_does_not_mutate_reusable_graph(self) -> None:
        find_itineraries(
            "Turku", "Wihuri", date(2026, 11, 1),
            same_day=True, max_results=3, graph_data=self.graph,
        )
        self.assertTrue(all("_schedules" not in route for route in self.graph["routes"]))

    def test_kokkila_uses_angelniemi_road_catchment(self) -> None:
        def road(edge_id: str, from_id: str, to_id: str, minutes: int) -> dict:
            return {
                "id": edge_id,
                "kind": "road",
                "from": from_id,
                "to": to_id,
                "modes": {
                    "auto": {
                        "status": "ok",
                        "durationSeconds": minutes * 60,
                        "distanceMeters": minutes * 1000,
                    },
                },
            }

        salo_edges = [
            road("salo-kokkila", "Salo", "Kokkila", 56),
            road("salo-angelniemi", "Salo", "Angelniemi", 94),
        ]
        angelniemi_side_edges = [
            road("local-kokkila", "local-origin", "Kokkila", 60),
            road("local-angelniemi", "local-origin", "Angelniemi", 20),
        ]

        self.assertEqual(
            nonlocal_route_ids(salo_edges, "Salo", "Föglö", "car"),
            {"kokkila"},
        )
        self.assertEqual(
            nonlocal_route_ids(
                angelniemi_side_edges, "local-origin", "Föglö", "car",
            ),
            set(),
        )

    def test_consecutive_road_leg_is_redundant(self) -> None:
        records = [{"edge": {"kind": "road"}}]

        self.assertTrue(
            is_redundant_consecutive_road(records, {"kind": "road"}),
        )
        self.assertFalse(
            is_redundant_consecutive_road(records, {"kind": "scheduled_service"}),
        )
        self.assertFalse(
            is_redundant_consecutive_road([], {"kind": "road"}),
        )

    def test_return_only_island_branch_is_pruned(self) -> None:
        adjacency = {
            "gateway": [
                {"from": "gateway", "to": "island", "id": "dead-end-ferry"},
                {"from": "gateway", "to": "mainland", "id": "onward-road"},
            ],
            "island": [
                {"from": "island", "to": "gateway", "id": "return-ferry"},
            ],
            "mainland": [
                {"from": "mainland", "to": "destination", "id": "destination-road"},
            ],
        }

        pruned, removed = prune_return_only_dead_ends(adjacency, "destination")

        self.assertEqual(
            [edge["id"] for edge in pruned["gateway"]],
            ["onward-road"],
        )
        self.assertEqual(removed, 1)

    def test_island_branch_with_another_exit_is_preserved(self) -> None:
        adjacency = {
            "gateway": [
                {"from": "gateway", "to": "island", "id": "outbound-ferry"},
            ],
            "island": [
                {"from": "island", "to": "gateway", "id": "return-ferry"},
                {"from": "island", "to": "mainland", "id": "other-exit"},
            ],
            "mainland": [
                {"from": "mainland", "to": "destination", "id": "destination-road"},
            ],
        }

        pruned, _ = prune_return_only_dead_ends(adjacency, "destination")

        self.assertEqual(
            [edge["id"] for edge in pruned["gateway"]],
            ["outbound-ferry"],
        )

    def test_first_sailing_may_move_to_a_later_day(self) -> None:
        graph = {
            "nodes": [{"id": "origin"}, {"id": "destination"}],
            "routes": [{"id": "three-day-service"}],
            "tripPatterns": [{"id": "three-day-trip", "calls": []}],
            "edges": [{
                "id": "three-day-edge",
                "kind": "scheduled_service",
                "from": "origin",
                "to": "destination",
                "routeId": "three-day-service",
                "tripPatternId": "three-day-trip",
                "serviceType": "connection_vessel",
                "mobility": {"car": "allowed"},
                "schedule": {
                    "operatingDays": "___4___",
                    "departure": {"time": "06:00"},
                    "arrival": {"time": "07:00"},
                },
            }],
        }

        result = find_itineraries(
            "origin", "destination", date(2026, 11, 2), time(8, 0),
            same_day=True, max_results=1, graph_data=graph,
        )

        self.assertEqual(result["status"], "routes_found")
        self.assertEqual(
            result["results"][0]["suggestedOriginDeparture"],
            "2026-11-05T06:00",
        )

    def test_ferry_chain_is_limited_to_twelve_hours(self) -> None:
        def graph(final_arrival: str) -> dict:
            return {
                "nodes": [
                    {"id": "origin"}, {"id": "transfer"},
                    {"id": "destination"},
                ],
                "routes": [{"id": "feeder"}, {"id": "onward"}],
                "tripPatterns": [
                    {"id": "feeder-trip", "calls": []},
                    {"id": "onward-trip", "calls": []},
                ],
                "edges": [
                    {
                        "id": "feeder-edge",
                        "kind": "scheduled_service",
                        "from": "origin",
                        "to": "transfer",
                        "routeId": "feeder",
                        "tripPatternId": "feeder-trip",
                        "serviceType": "connection_vessel",
                        "mobility": {"car": "allowed"},
                        "schedule": {
                            "operatingDays": "1234567",
                            "departure": {"time": "06:00"},
                            "arrival": {"time": "06:10"},
                        },
                    },
                    {
                        "id": "onward-edge",
                        "kind": "scheduled_service",
                        "from": "transfer",
                        "to": "destination",
                        "routeId": "onward",
                        "tripPatternId": "onward-trip",
                        "serviceType": "connection_vessel",
                        "mobility": {"car": "allowed"},
                        "schedule": {
                            "operatingDays": "1234567",
                            "departure": {"time": "17:55"},
                            "arrival": {"time": final_arrival},
                        },
                    },
                ],
            }

        within_limit = find_itineraries(
            "origin", "destination", date(2026, 11, 2),
            same_day=True, max_results=1, graph_data=graph("18:00"),
        )
        beyond_limit = find_itineraries(
            "origin", "destination", date(2026, 11, 2),
            same_day=True, max_results=1, graph_data=graph("18:01"),
        )

        self.assertEqual(within_limit["status"], "routes_found")
        self.assertEqual(beyond_limit["status"], "no_route")

    def test_initial_drive_buffer_scales_with_driving_time(self) -> None:
        def records(minutes: int) -> list[dict]:
            departure = datetime(2026, 10, 30, 8, 0)
            return [
                {
                    "edge": {"kind": "road"},
                    "instance": {
                        "departure": departure,
                        "arrival": departure + timedelta(minutes=minutes),
                    },
                },
                {"edge": {"kind": "scheduled_service"}, "instance": {}},
            ]

        self.assertEqual(default_origin_boarding_buffer_minutes(records(59), 1), 5)
        self.assertEqual(default_origin_boarding_buffer_minutes(records(60), 1), 10)
        self.assertEqual(default_origin_boarding_buffer_minutes(records(119), 1), 10)
        self.assertEqual(default_origin_boarding_buffer_minutes(records(120), 1), 15)

    def test_initial_drive_buffer_is_added_to_loading_readiness(self) -> None:
        records = [
            {
                "edge": {"kind": "road"},
                "instance": {
                    "departure": datetime(2026, 10, 25, 11, 46),
                    "arrival": datetime(2026, 10, 25, 12, 5),
                },
            },
            {
                "edge": {
                    "kind": "scheduled_service", "routeId": "ferry",
                    "from": "Degerby",
                },
                "instance": {"departure": datetime(2026, 10, 25, 12, 15)},
            },
        ]
        with patch("route_itineraries.loading_readiness_minutes", return_value=10):
            shift, first_service_index = prefix_road_shift(records, {"ferry": {}}, "car")
        self.assertEqual(first_service_index, 1)
        self.assertEqual(shift, timedelta(minutes=-5))

    def test_continuous_ferry_adds_five_minutes_after_road_approach(self) -> None:
        edge = next(
            item for item in self.graph["edges"]
            if item["kind"] == "continuous_ferry"
            and item.get("routeId") == "embarsundslinjen"
            and item["from"] == "Jyddö"
        )
        ready = datetime(2026, 10, 25, 19, 41)
        instance = edge_instance(
            edge, {}, ready, "car", "typical",
            continuous_approach_minutes=5,
        )
        self.assertEqual(instance["departure"], datetime(2026, 10, 25, 19, 46))

    def test_adaptive_sweep_keeps_five_minute_normal_risk_boundary(self) -> None:
        seed = datetime(2026, 10, 25, 6, 1)
        departure = datetime(2026, 10, 25, 10, 0)
        records = [
            {
                "edge": {"kind": "continuous_ferry", "routeId": "feeder"},
                "instance": {"departure": seed, "arrival": seed + timedelta(minutes=5)},
                "ready": seed,
            },
            {
                "edge": {
                    "kind": "scheduled_service", "routeId": "onward",
                    "from": "Överö", "to": "Galtby",
                },
                "instance": {"departure": departure, "arrival": departure + timedelta(hours=4)},
                "ready": departure - timedelta(minutes=21),
            },
        ]
        routes = {
            "feeder": {},
            "onward": {"booking": {"loadingReadinessMinutesBefore": 15}},
        }

        self.assertEqual(
            next_adaptive_sweep_seeds(
                records, seed, routes, departure + timedelta(hours=8), "car",
            ),
            [seed + timedelta(minutes=1)],
        )

    def test_later_intermediate_departure_wins_same_risk_tie(self) -> None:
        def candidate(departure: str) -> dict:
            return {
                "suggestedOriginDeparture": "2026-10-25T09:42",
                "legs": [{"kind": "scheduled_service", "departure": departure}],
            }

        early = candidate("2026-10-25T13:40")
        late = candidate("2026-10-25T14:00")
        self.assertGreater(
            candidate_departure_preference(late),
            candidate_departure_preference(early),
        )

    def test_later_feeder_survives_shared_onward_sailing(self) -> None:
        result = find_itineraries(
            "Lillmälö", "Finholma", date(2026, 10, 25), time(12, 0),
            same_day=True, max_results=20, graph_data=self.graph,
        )
        direct = next(
            item for item in result["results"]
            if any(
                leg.get("routeId") == "sodralinjen" and leg["to"] == "Överö"
                for leg in item["legs"]
            )
            and item["riskSummary"]["worstConnectionRisk"] == "normal"
        )
        parnas_departure = next(
            leg["departure"] for leg in direct["legs"]
            if leg["from"] == "Pärnäs" and leg["to"] == "Retais"
        )
        self.assertEqual(parnas_departure, "2026-10-25T14:40")

    def test_loading_readiness_margin_is_not_itself_a_tight_connection(self) -> None:
        self.assertEqual(transfer_risk(21, 15)["level"], "normal")
        self.assertEqual(transfer_risk(20, 15)["level"], "normal")
        self.assertEqual(transfer_risk(19, 15)["level"], "tight")
        self.assertEqual(transfer_risk(15, 15)["level"], "very_tight")
        self.assertEqual(transfer_risk(14, 15)["level"], "below_required_readiness")

    def test_safe_later_feeder_dominates_unnecessary_wait(self) -> None:
        def candidate(origin_departure: str, parnas_departure: str, risk: str) -> dict:
            return {
                "suggestedOriginDeparture": origin_departure,
                "arrival": "2026-10-25T19:46",
                "riskSummary": {"worstConnectionRisk": risk},
                "legs": [
                    {
                        "kind": "scheduled_service", "routeId": "pargasnagu",
                        "from": "Lillmälö", "to": "Prostvik",
                        "departure": "2026-10-25T12:45",
                    },
                    {
                        "kind": "scheduled_service", "routeId": "nagukorpo",
                        "from": "Pärnäs", "to": "Retais",
                        "departure": parnas_departure,
                    },
                ],
            }

        early = candidate("2026-10-25T12:30", "2026-10-25T14:00", "relaxed")
        later = candidate("2026-10-25T12:45", "2026-10-25T14:20", "normal")
        self.assertTrue(candidate_dominates(later, early))
        self.assertFalse(candidate_dominates(early, later))

    def test_same_sailing_detour_is_dominated_after_useful_stop(self) -> None:
        shared = {
            "kind": "scheduled_service",
            "routeId": "sodralinjen",
            "tripPatternId": "sodralinjen:test",
            "departure": "2026-10-25T15:15",
        }
        direct = {
            "suggestedOriginDeparture": "2026-10-25T09:42",
            "arrival": "2026-10-25T20:00",
            "riskSummary": {"worstConnectionRisk": "normal"},
            "legs": [{**shared, "from": "Galtby", "to": "Överö"}],
        }
        detour = {
            "suggestedOriginDeparture": "2026-10-25T09:42",
            "arrival": "2026-10-25T22:34",
            "riskSummary": {"worstConnectionRisk": "relaxed"},
            "legs": [
                {**shared, "from": "Galtby", "to": "Långnäs"},
                {
                    "kind": "scheduled_service",
                    "routeId": "foglolinjen",
                    "tripPatternId": "foglolinjen:test",
                    "departure": "2026-10-25T21:45",
                    "from": "Svinö",
                    "to": "Degerby",
                },
            ],
        }
        self.assertTrue(candidate_dominates(direct, detour))

    def test_different_commercial_operators_remain_distinct_choices(self) -> None:
        def candidate(operator: str, departure: str, arrival: str) -> dict:
            return {
                "suggestedOriginDeparture": departure,
                "arrival": arrival,
                "riskSummary": {"worstConnectionRisk": None},
                "legs": [{
                    "kind": "scheduled_service",
                    "routeId": operator.lower().replace(" ", "-"),
                    "operator": operator,
                    "from": "Långnäs",
                    "to": "Turku",
                    "departure": departure,
                }],
            }

        faster = candidate("Tallink Silja", "2026-10-26T14:20", "2026-10-26T18:30")
        slower = candidate("Viking Line", "2026-10-26T13:20", "2026-10-26T19:50")
        self.assertFalse(candidate_dominates(faster, slower))

    def test_published_aland_connection_is_not_ranked_below_readiness(self) -> None:
        result = find_itineraries(
            "Vuosnainen", "Hummelvik", date(2026, 10, 25), time(12, 30),
            same_day=True, max_results=5, graph_data=self.graph,
        )
        connection = result["results"][0]["legs"][-1]
        self.assertEqual(connection["publishedConnection"], {
            "guaranteed": False,
            "source": "published_timetable",
        })
        self.assertEqual(connection["transferRisk"]["level"], "normal")
        self.assertEqual(connection["transferRisk"]["effectiveBufferMinutes"], -14)

    def test_same_port_same_provider_ferry_transfer_ignores_readiness_shortfall(self) -> None:
        moment = datetime(2026, 11, 2, 8, 40)
        records = [
            {
                "edge": {
                    "kind": "scheduled_service", "routeId": "feeder",
                    "from": "Norrby", "to": "Själö",
                },
                "instance": {"arrival": moment},
            },
            {
                "edge": {
                    "kind": "scheduled_service", "routeId": "connection",
                    "from": "Själö", "to": "Roslax",
                },
                "instance": {"departure": moment + timedelta(minutes=5)},
            },
        ]
        connection = same_provider_direct_ferry_connection(
            records, 1, {
                "feeder": {"provider": "finferries"},
                "connection": {"provider": "finferries"},
            },
        )
        self.assertEqual(connection, {
            "guaranteed": False,
            "source": "same_provider_direct_ferry_transfer",
        })
        self.assertIsNone(same_provider_direct_ferry_connection(
            records, 1, {
                "feeder": {"provider": "finferries"},
                "connection": {"provider": "alandstrafiken"},
            },
        ))

    def test_non_bookable_foglo_service_keeps_loading_readiness(self) -> None:
        result = find_itineraries(
            "Degerby", "Svinö", date(2026, 10, 25), time(11, 0),
            same_day=True, max_results=2, graph_data=self.graph,
        )
        leg = result["results"][0]["legs"][0]
        self.assertFalse(leg["booking"]["required"])
        self.assertEqual(leg["booking"]["loadingReadinessMinutesBefore"], 10)
        self.assertEqual(leg["travelerInformation"]["farePolicy"]["vehicles"], "paid")
        self.assertEqual(
            leg["travelerInformation"]["farePolicy"]["paidWhenDepartingFrom"],
            ["Svinö"],
        )

    def test_vuosnainen_vehicle_charge_is_departure_specific(self) -> None:
        result = find_itineraries(
            "Vuosnainen", "Åva", date(2026, 10, 25), time(12, 30),
            same_day=True, max_results=1, graph_data=self.graph,
        )
        policy = result["results"][0]["legs"][0]["travelerInformation"]["farePolicy"]
        self.assertEqual(policy["vehicles"], "paid")
        self.assertEqual(policy["paidWhenDepartingFrom"], ["Vuosnainen"])

    def test_aland_transit_charge_requires_complete_gateway_pair(self) -> None:
        def south_leg(destination: str) -> dict:
            return {
                "kind": "scheduled_service",
                "routeId": "sodralinjen",
                "from": "Galtby",
                "to": destination,
                "travelerInformation": {
                    "farePolicy": {
                        "vehicles": "paid",
                        "transitChargePairs": [
                            {
                                "from": "Galtby",
                                "to": "Långnäs",
                                "chargeLegEndpoint": "Galtby",
                            },
                            {
                                "from": "Galtby",
                                "to": "Svinö",
                                "chargeLegEndpoint": "Galtby",
                            },
                        ],
                    },
                },
            }

        overo_only = [south_leg("Överö")]
        self.assertIsNone(annotate_transit_charge(overo_only))
        self.assertNotIn("fare", overo_only[0])

        galtby_langnas = [south_leg("Långnäs")]
        summary = annotate_transit_charge(galtby_langnas)
        self.assertEqual(summary["transitPair"], {"from": "Galtby", "to": "Långnäs"})
        self.assertEqual(
            galtby_langnas[0]["fare"]["chargeType"],
            "aland_archipelago_transit",
        )

        galtby_svino = [
            south_leg("Överö"),
            {"kind": "road", "from": "Överö", "to": "Svinö"},
        ]
        summary = annotate_transit_charge(galtby_svino)
        self.assertEqual(summary["transitPair"], {"from": "Galtby", "to": "Svinö"})
        self.assertEqual(
            galtby_svino[0]["fare"]["chargeType"],
            "aland_archipelago_transit",
        )

    def test_adaptive_sweep_finds_all_wihuri_departures_without_half_hour_scan(self) -> None:
        result = find_itineraries(
            "Turku", "Wihuri", date(2026, 11, 1),
            same_day=True, max_results=10, graph_data=self.graph,
        )
        self.assertEqual(
            [item["suggestedOriginDeparture"] for item in result["results"]],
            [
                "2026-11-01T06:50",
                "2026-11-01T12:50",
                "2026-11-01T14:50",
            ],
        )
        self.assertEqual(
            result["diagnostics"]["sweepStrategy"],
            "adaptive_reused_candidate_boundaries",
        )
        self.assertLessEqual(result["diagnostics"]["sweptSeedCount"], 4)

    def test_reused_candidate_sweep_keeps_latest_feeder_to_same_final_sailing(self) -> None:
        result = find_itineraries(
            "Turku", "Storpensor", date(2026, 10, 30),
            same_day=True, max_results=20, graph_data=self.graph,
        )
        final_connection = next(
            item for item in result["results"]
            if item["arrival"] == "2026-10-30T20:00"
        )

        self.assertEqual(
            final_connection["suggestedOriginDeparture"],
            "2026-10-30T17:05",
        )
        self.assertGreater(result["diagnostics"]["sweptCandidateJumps"], 0)
        self.assertLessEqual(result["diagnostics"]["sweptSeedCount"], 15)

    def test_sweep_jump_from_origin_ferry_starts_after_its_departure(self) -> None:
        candidate = {
            "suggestedOriginDeparture": "2026-11-02T13:40",
            "legs": [{
                "kind": "scheduled_service",
                "departure": "2026-11-02T13:40",
                "readyAtOrigin": "2026-11-02T06:01",
                "booking": {"loadingReadinessMinutesBefore": 0},
            }],
        }

        self.assertEqual(
            candidate_sweep_seed(candidate, datetime(2026, 11, 2, 23, 59)),
            datetime(2026, 11, 2, 13, 41),
        )

    def test_reused_candidate_sweep_keeps_later_keistio_routes(self) -> None:
        result = find_itineraries(
            "Keistiö", "Galtby", date(2026, 11, 2), time(6, 1),
            same_day=True, max_results=20, graph_data=self.graph,
        )

        self.assertEqual(result["resultCount"], 7)
        self.assertEqual(
            result["results"][-1]["suggestedOriginDeparture"],
            "2026-11-02T17:10",
        )

    def test_decision_graph_keeps_leg_specific_risk_alternatives(self) -> None:
        result = find_itineraries(
            "Turku", "Storpensor", date(2026, 10, 30),
            same_day=True, max_results=20, graph_data=self.graph,
            include_decision_graph=True,
        )
        graph = result["decisionGraph"]
        self.assertGreater(graph["candidatePathCount"], result["resultCount"])
        node_ids = {item["id"] for item in graph["nodes"]}
        connection_ids = {item["id"] for item in graph["connections"]}
        self.assertTrue(set(graph["originNodeIds"]) <= node_ids)
        self.assertTrue(set(graph["destinationNodeIds"]) <= node_ids)
        self.assertTrue(all(
            item["fromNode"] in node_ids and item["toNode"] in node_ids
            for item in graph["connections"]
        ))
        self.assertTrue(all(
            variant["connectionId"] in connection_ids
            for item in graph["transferChoices"]
            for variant in item["variants"]
        ))
        choice = next(
            item for item in graph["transferChoices"]
            if item["service"]["from"] == "Pärnäs"
            and item["service"]["departure"] == "2026-10-30T13:00"
        )
        self.assertEqual(
            {
                item["risk"]["level"]: item["risk"]["effectiveBufferMinutes"]
                for item in choice["variants"]
            },
            {"relaxed": 35, "normal": 5},
        )


if __name__ == "__main__":
    unittest.main()
