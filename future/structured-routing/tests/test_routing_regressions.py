#!/usr/bin/env python3
"""Regression tests for the experimental time-dependent routing graph."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "routing-graph.json"
REPORT = ROOT / "routing-graph-report.json"
AIS_LINK_REPORT = ROOT / "connection-ais-estimate-link-report.json"
ROUTER = ROOT / "scripts" / "route_itinerary.py"
PUBLIC_ROUTER = ROOT / "scripts" / "query_routes.py"


def route(origin: str, destination: str, date: str, time: str = "00:00") -> dict:
    completed = subprocess.run(
        [sys.executable, str(ROUTER), origin, destination, date, time, "--mode", "car"],
        cwd=ROOT.parents[1],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode not in {0, 2}:
        raise AssertionError(completed.stderr or completed.stdout)
    return json.loads(completed.stdout)


def public_routes(origin: str, destination: str, date: str, time: str = "00:00") -> dict:
    completed = subprocess.run(
        [
            sys.executable, str(PUBLIC_ROUTER), origin, destination, date, time,
            "--mode", "car", "--same-day", "--max-results", "3",
        ],
        cwd=ROOT.parents[1],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode not in {0, 2}:
        raise AssertionError(completed.stderr or completed.stdout)
    return json.loads(completed.stdout)


class RoutingGraphCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.graph = json.loads(GRAPH.read_text())
        cls.report = json.loads(REPORT.read_text())
        cls.ais_link_report = json.loads(AIS_LINK_REPORT.read_text())

    def test_every_real_route_has_edges(self) -> None:
        self.assertEqual(self.report["statistics"]["routesWithoutEdgesCount"], 0)
        self.assertEqual(self.report["routesWithoutEdges"], [])

    def test_newly_normalized_routes_have_usable_edges(self) -> None:
        route_ids = {
            "avajurmo", "enklingelinjen", "foglolinjen", "iniorutt",
            "osnasava", "velkuataivassalo",
        }
        for route_id in route_ids:
            edges = [
                edge for edge in self.graph["edges"]
                if edge.get("routeId") == route_id
            ]
            self.assertTrue(edges, route_id)
            self.assertTrue(
                any(edge.get("timingStatus") == "usable" for edge in edges),
                route_id,
            )

    def test_velkua_and_inio_ais_aliases_have_full_coverage(self) -> None:
        routes = {
            item["routeId"]: item
            for item in self.ais_link_report["routes"]
        }
        self.assertEqual(routes["velkuataivassalo"]["aisRouteId"], "velkuanreitti")
        self.assertEqual(routes["velkuataivassalo"]["coverage"], 1)
        self.assertEqual(routes["iniorutt"]["aisRouteId"], "houtskarrutt")
        self.assertEqual(routes["iniorutt"]["coverage"], 1)

    def test_legacy_velkua_duplicate_is_not_in_graph(self) -> None:
        route_ids = {item["id"] for item in self.graph["routes"]}
        self.assertIn("velkuataivassalo", route_ids)
        self.assertNotIn("velkuanreitti", route_ids)

    def test_all_continuous_crossings_have_a_routing_duration(self) -> None:
        edge_ids = {
            edge["id"]
            for edge in self.graph["edges"]
            if edge["kind"] == "continuous_ferry"
            and edge.get("crossingMinutes") is None
        }
        self.assertEqual(edge_ids, set())

    def test_commercial_ferries_are_in_the_graph(self) -> None:
        route_ids = {
            edge["routeId"]
            for edge in self.graph["edges"]
            if edge.get("serviceType") == "commercial_ferry"
        }
        self.assertEqual(route_ids, {
            "finnlines-naantali-langnas",
            "tallink-helsinki-aland",
            "tallink-turku-aland",
            "viking-helsinki-aland",
            "viking-turku-aland",
        })


class ExampleJourneyTests(unittest.TestCase):
    def assert_route_ids(self, result: dict, expected: list[str]) -> None:
        self.assertEqual(result["status"], "route_found")
        actual = [leg["routeId"] for leg in result["legs"] if leg.get("routeId")]
        self.assertEqual(actual, expected)

    def test_turku_to_storpensor(self) -> None:
        result = route("Turku", "Storpensor", "2026-10-30")
        self.assert_route_ids(result, ["pargasnagu", "nagukorpo", "korporutt"])
        self.assertEqual(result["arrival"], "2026-10-30T08:00")

    def test_turku_to_wihuri_uses_ais_arrival_not_route_end(self) -> None:
        result = route("Turku", "Wihuri", "2026-11-01")
        self.assert_route_ids(result, ["rymattylanreitti"])
        self.assertLess(result["arrival"], "2026-11-01T10:30")

    def test_nagu_to_degerby_uses_the_now_complete_earliest_road_ferry_path(self) -> None:
        result = route("Nagu", "Degerby", "2026-11-03")
        self.assert_route_ids(
            result,
            ["pargasnagu", "vartsala", "osnasava", "norralinjen", "toftolinjen", "foglolinjen"],
        )

    def test_nagu_to_all_reviewed_foglo_destinations(self) -> None:
        expected = {
            "Överö": ["nagukorpo", "sodralinjen"],
            "Jyddö": ["nagukorpo", "sodralinjen"],
            "Finholma": ["nagukorpo", "sodralinjen", "embarsundslinjen"],
            "Degerby": ["pargasnagu", "vartsala", "osnasava", "norralinjen", "toftolinjen", "foglolinjen"],
        }
        for destination, route_ids in expected.items():
            with self.subTest(destination=destination):
                result = route("Nagu", destination, "2026-11-03")
                self.assert_route_ids(result, route_ids)

    def test_open_ended_vartsala_timetable_is_routable(self) -> None:
        result = route("Kivimaa", "Vartsala", "2026-11-03", "08:00")
        self.assert_route_ids(result, ["vartsala"])
        self.assertEqual(result["arrival"], "2026-11-03T08:18")

    def test_published_commercial_ferry_examples(self) -> None:
        examples = [
            ("Turku", "Mariehamn", "08:00", "viking-turku-aland", "2026-11-03T14:10"),
            ("Naantali", "Långnäs", "09:00", "finnlines-naantali-langnas", "2026-11-03T15:45"),
        ]
        for origin, destination, departure, route_id, arrival in examples:
            with self.subTest(origin=origin, destination=destination):
                result = route(origin, destination, "2026-11-03", departure)
                self.assert_route_ids(result, [route_id])
                self.assertEqual(result["arrival"], arrival)

    def test_commercial_origin_specific_vehicle_readiness(self) -> None:
        just_early_enough = route("Långnäs", "Turku", "2026-11-03", "13:35")
        self.assert_route_ids(just_early_enough, ["tallink-turku-aland"])
        too_late_for_tallink = route("Långnäs", "Turku", "2026-11-03", "13:36")
        self.assert_route_ids(too_late_for_tallink, ["finnlines-naantali-langnas"])

    def test_finnlines_cancelled_holiday_night_departure_is_not_used(self) -> None:
        result = route("Naantali", "Långnäs", "2026-12-27", "18:00")
        route_ids = [leg["routeId"] for leg in result["legs"] if leg.get("routeId")]
        self.assertNotIn("finnlines-naantali-langnas", route_ids)

    def test_public_response_enforces_first_boarding_readiness(self) -> None:
        result = public_routes("Turku", "Wihuri", "2026-11-01")
        self.assertEqual(result["schemaVersion"], "1.0")
        self.assertNotIn("diagnostics", result)
        self.assertEqual(result["status"], "routes_found")
        first = result["itineraries"][0]
        self.assertEqual(first["suggestedOriginDeparture"], "2026-11-01T06:55")
        self.assertEqual(first["legs"][0]["arrival"], "2026-11-01T07:50")
        self.assertNotIn("transferRisk", first["legs"][1])
        self.assertIsNone(first["riskSummary"]["worstConnectionRisk"])
        self.assertTrue(first["timingBasis"]["usesHistoricalEstimate"])

    def test_ava_jurmo_is_routable(self) -> None:
        result = route("Åva", "JurmoB", "2026-11-02", "05:00")
        self.assert_route_ids(result, ["avajurmo"])
        self.assertEqual(result["arrival"], "2026-11-02T06:00")

    def test_osnas_ava_is_routable(self) -> None:
        result = route("Vuosnainen", "Åva", "2026-11-02", "09:00")
        self.assert_route_ids(result, ["osnasava"])
        self.assertEqual(result["arrival"], "2026-11-02T11:20")

    def test_velkua_uses_ais_arrival_and_rich_canonical_metadata(self) -> None:
        result = route("Teersalo", "Talosmeri", "2026-11-02", "05:00")
        self.assert_route_ids(result, ["velkuataivassalo"])
        leg = result["legs"][0]
        self.assertEqual(leg["arrival"], "2026-11-02T06:38")
        self.assertEqual(leg["arrivalTiming"]["status"], "historical_estimate")
        self.assertEqual(leg["vessel"], "M/S Kaita")
        self.assertEqual(leg["capacity"]["cars"], 8)
        self.assertTrue(leg["booking"]["required"])
        self.assertIsNotNone(leg["contact"])
        self.assertIsNotNone(leg["publicTimetableUrl"])

    def test_inio_uses_houtskar_ais_model(self) -> None:
        result = route("Själö", "Kvarnholm", "2026-11-02", "05:00")
        self.assert_route_ids(result, ["iniorutt"])
        leg = result["legs"][0]
        self.assertEqual(leg["arrival"], "2026-11-02T06:02")
        self.assertEqual(leg["arrivalTiming"]["status"], "historical_estimate")
        self.assertGreaterEqual(leg["arrivalTiming"]["sampleSize"], 1)

    def test_enklinge_booking_marker_is_resolved(self) -> None:
        result = route("Kumlinge", "Enklinge", "2026-11-02", "05:00")
        self.assert_route_ids(result, ["enklingelinjen"])
        leg = result["legs"][0]
        self.assertEqual(leg["departure"], "2026-11-02T06:15")
        self.assertTrue(leg["booking"]["required"])
        self.assertEqual(leg["booking"]["deadline"], "2026-11-01T20:00")

    def test_foglo_christmas_exception_uses_bookable_late_trip(self) -> None:
        result = route("Svinö", "Degerby", "2026-12-24", "20:00")
        self.assert_route_ids(result, ["foglolinjen"])
        leg = result["legs"][0]
        self.assertEqual(leg["departure"], "2026-12-24T23:00")
        self.assertTrue(leg["booking"]["required"])
        self.assertEqual(leg["booking"]["deadline"], "2026-12-24T21:30")

    def test_inio_additional_route_is_routable(self) -> None:
        result = route("Själö", "Kannvik", "2026-11-02", "05:00")
        self.assert_route_ids(result, ["iniorutt"])
        self.assertEqual(result["arrival"], "2026-11-02T07:25")


if __name__ == "__main__":
    unittest.main()
