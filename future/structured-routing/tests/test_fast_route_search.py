#!/usr/bin/env python3
"""Correctness checks for the precompiled timetable search index."""

from __future__ import annotations

import json
import sys
import unittest
from datetime import date, datetime, time, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from route_itineraries import (  # noqa: E402
    ScheduledInstanceIndex,
    annotate_transit_charge,
    candidate_departure_preference,
    candidate_dominates,
    default_origin_boarding_buffer_minutes,
    find_itineraries,
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
        def candidate(parnas_departure: str, risk: str) -> dict:
            return {
                "suggestedOriginDeparture": "2026-10-25T12:45",
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

        early = candidate("2026-10-25T14:00", "relaxed")
        later = candidate("2026-10-25T14:20", "normal")
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
                "2026-11-01T06:55",
                "2026-11-01T12:55",
                "2026-11-01T14:55",
            ],
        )
        self.assertEqual(
            result["diagnostics"]["sweepStrategy"],
            "adaptive_first_service_boundaries",
        )
        self.assertLessEqual(result["diagnostics"]["sweptSeedCount"], 4)

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
