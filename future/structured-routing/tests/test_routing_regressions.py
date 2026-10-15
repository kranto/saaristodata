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

    def test_nagu_to_degerby_uses_southern_line_and_foglo_road_network(self) -> None:
        result = route("Nagu", "Degerby", "2026-11-03")
        self.assert_route_ids(
            result, ["nagukorpo", "sodralinjen", "embarsundslinjen"]
        )

    def test_nagu_to_all_reviewed_foglo_destinations(self) -> None:
        expected = {
            "Överö": ["nagukorpo", "sodralinjen"],
            "Jyddö": ["nagukorpo", "sodralinjen"],
            "Finholma": ["nagukorpo", "sodralinjen", "embarsundslinjen"],
            "Degerby": ["nagukorpo", "sodralinjen", "embarsundslinjen"],
        }
        for destination, route_ids in expected.items():
            with self.subTest(destination=destination):
                result = route("Nagu", destination, "2026-11-03")
                self.assert_route_ids(result, route_ids)

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
