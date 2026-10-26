#!/usr/bin/env python3

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

try:
    from fastapi.testclient import TestClient
except ImportError:  # Allows the stdlib suite to explain a missing dev dependency.
    TestClient = None

from routing_cache import SQLiteJsonCache  # noqa: E402


class FakeGeocoder:
    def __init__(self) -> None:
        self.calls = 0

    def geocode(self, query: str) -> dict:
        self.calls += 1
        coordinates = (
            {"lat": 61.5, "lon": 23.7}
            if query == "Origin address"
            else {"lat": 60.4, "lon": 21.8}
        )
        return {
            "query": query,
            "displayName": f"Resolved {query}",
            "coordinates": coordinates,
            "provider": "test",
            "attribution": "test data",
        }


class FakeRouter:
    provider = "test"

    def infer_road_area(self, point: dict, index: dict, *, mode: str) -> dict:
        area_id = "mainland_finland" if point["lat"] > 61 else "stop:Wihuri"
        return {"roadArea": {"id": area_id, "inference": "test_fixture"}}

    def matrix(
        self, sources: list[dict], targets: list[dict], mode: str,
        *, exclude_ferries: bool = True,
    ) -> list[dict]:
        return [
            {
                "from_index": source_index,
                "to_index": target_index,
                "time": 600 + target_index,
                "distance": 5 + target_index / 10,
            }
            for source_index in range(len(sources))
            for target_index in range(len(targets))
        ]

    def route_geometry(
        self, origin: dict, destination: dict, mode: str,
        *, exclude_ferries: bool = True,
    ) -> dict:
        return {
            "type": "LineString",
            "coordinates": [
                [origin["lon"], origin["lat"]],
                [destination["lon"], destination["lat"]],
            ],
        }


@unittest.skipIf(TestClient is None, "install requirements-dev.txt to test FastAPI")
class RoutingServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        from service.app import create_app

        self.temporary_directory = tempfile.TemporaryDirectory()
        app = create_app()
        app.state.cache = SQLiteJsonCache(
            Path(self.temporary_directory.name) / "cache.sqlite3",
        )
        app.state.geocoder = FakeGeocoder()
        app.state.router = FakeRouter()
        app.state.graph_path = ROOT / "routing-graph.json"
        app.state.stop_index_path = ROOT / "external-routing-stop-index.json"
        self.client_context = TestClient(app)
        self.client = self.client_context.__enter__()

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)
        self.temporary_directory.cleanup()

    def test_health(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_route_preview(self) -> None:
        response = self.client.get("/route")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Näe vaihtoehtoiset lauttavuorot", response.text)
        self.assertIn("Matka aikajanalla", response.text)
        self.assertIn("formatDistance(leg.distanceMeters)", response.text)
        self.assertIn("Valitse vuoro klikkaamalla lauttapalkkia", response.text)
        self.assertIn("function mainRouteOptions", response.text)
        self.assertIn('index === activeResult ? "active" : ""', response.text)
        self.assertNotIn("displayedRouteOptionKey", response.text)
        self.assertIn('virtualWait: true', response.text)
        self.assertIn('.filter((item) => !item.virtualWait)', response.text)
        self.assertIn("grid-template-columns: auto minmax(0, 1fr)", response.text)
        self.assertIn("overflow-wrap: anywhere", response.text)
        self.assertIn("function bestSelectedPath", response.text)
        self.assertIn("aOkay !== bOkay ? (aOkay ? -1 : 1) : 0", response.text)
        self.assertIn("selectedSailings.set", response.text)
        self.assertIn("const legPlaceName", response.text)
        self.assertIn('suffix = " (lauttaranta)"', response.text)
        self.assertIn("gantt-ferry-choice", response.text)
        self.assertIn("gantt-ferry-pinned", response.text)
        self.assertIn("gantt-ferry-blocking", response.text)
        self.assertIn(".gantt-ferry-selected:hover", response.text)
        self.assertIn(".gantt-ferry-pinned:hover", response.text)
        self.assertIn('class="fast-tooltip"', response.text)
        self.assertIn("function showFastTooltip(target, delay = 80)", response.text)
        self.assertIn('event.target.closest?.("[data-tooltip]")', response.text)
        self.assertIn("function selectConnection(connectionId)", response.text)
        self.assertIn("const unlock = previous === selectedService", response.text)
        self.assertIn("individualBlockers", response.text)
        self.assertIn("Estävä lukittu vuoro välähti kaaviossa", response.text)
        self.assertIn("Automaattinen valinta", response.text)
        self.assertIn("Lukittu valinta", response.text)
        self.assertIn("function sailingBarLayout(items)", response.text)
        self.assertIn("const sailingTop = Math.round", response.text)
        self.assertIn(".gantt-alternative { --bar: var(--sea); top: 14px; height: 8px; opacity: 1;", response.text)
        self.assertIn("12 + lane * 18", response.text)
        self.assertIn("ferryRowHeight", response.text)
        self.assertIn("gantt-wait-safe", response.text)
        self.assertIn("gantt-wait-short", response.text)
        self.assertIn(".gantt-readiness { --bar: #7da7b7; height: 16px", response.text)
        self.assertIn("gantt-selection-outline", response.text)
        self.assertIn("gantt-join-left", response.text)
        self.assertIn("gantt-join-right", response.text)
        self.assertIn("readinessBar", response.text)
        self.assertIn("leg.booking?.loadingReadinessMinutesBefore\n        ?? 0", response.text)
        self.assertIn("function loadingReadinessMinutes(leg)", response.text)
        self.assertIn("function waitProfile(leg)", response.text)
        self.assertIn("(lastausvalmius ${clockBefore(leg.departure, readiness)})", response.text)
        self.assertNotIn("leg.booking?.loadingReadinessMinutesBefore\n        ?? 15", response.text)
        self.assertNotIn("gantt-buffer-normal", response.text)
        self.assertIn("ylimääräistä aikaa", response.text)
        self.assertIn("function bufferTimeLabel", response.text)
        self.assertIn("vaaditun lastausvalmiuden jälkeen", response.text)
        self.assertIn("aikatauluun merkitty yhteys (ei taattu)", response.text)
        self.assertIn("Kauttakulkumaksu", response.text)
        self.assertIn('chargeLabel(leg) ? "€" : ""', response.text)
        self.assertIn("policy.paidWhenDepartingFrom.includes(leg.from)", response.text)
        self.assertIn("leg.operator", response.text)
        self.assertNotIn('` · +${formatDuration(risk.effectiveBufferMinutes)}', response.text)
        self.assertNotIn("Tauko autoiluosuudella", response.text)
        self.assertIn("function ganttModeIcon", response.text)
        self.assertIn('class="gantt-mode-icon"', response.text)
        self.assertIn("gantt-row-ferry", response.text)
        self.assertIn("min-height: 72px", response.text)
        self.assertIn("Poista valinnat", response.text)
        self.assertNotIn("Palauta ehdotus", response.text)
        self.assertIn("window.history.replaceState", response.text)
        self.assertNotIn("pausePlan", response.text)
        self.assertNotIn("pauseCandidates", response.text)
        self.assertIn("followsDisplayedApproach", response.text)
        self.assertIn("let ganttViewport = null", response.text)
        self.assertIn("function resetGanttViewport", response.text)
        self.assertIn("function ensureGanttViewport", response.text)
        self.assertIn("alternativeDeparture - prefixDuration", response.text)
        self.assertIn("extent.start -= 15 * 60000", response.text)
        self.assertIn("Math.min(ganttViewport.start, extent.start)", response.text)
        self.assertIn("Math.max(ganttViewport.end, extent.end)", response.text)
        self.assertNotIn('"Ei vaihtoa"', response.text)
        self.assertIn("originAddress?.displayName", response.text)
        self.assertIn("includeDecisionGraph", response.text)

    def test_route_returns_address_itineraries_and_geometry(self) -> None:
        response = self.client.post("/route", json={
            "origin": "Origin address",
            "destination": "Wihuri address",
            "date": "2026-11-01",
            "mode": "car",
            "sameDay": True,
            "maxResults": 2,
        })
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result["status"], "routes_found")
        external = [
            leg["externalRouting"]
            for itinerary in result["itineraries"]
            for leg in itinerary["legs"]
            if "externalRouting" in leg
        ]
        self.assertTrue(external)
        self.assertTrue(all(item["geometry"]["type"] == "LineString" for item in external))

    def test_unknown_request_field_is_rejected(self) -> None:
        response = self.client.post("/route", json={
            "origin": "Origin address",
            "destination": "Wihuri address",
            "date": "2026-11-01",
            "surprise": True,
        })
        self.assertEqual(response.status_code, 422)

    def test_route_can_include_compact_decision_graph(self) -> None:
        response = self.client.post("/route", json={
            "origin": "Origin address",
            "destination": "Wihuri address",
            "date": "2026-11-01",
            "mode": "car",
            "sameDay": True,
            "includeDecisionGraph": True,
            "includeGeometry": False,
        })
        self.assertEqual(response.status_code, 200, response.text)
        graph = response.json()["decisionGraph"]
        self.assertGreater(graph["candidatePathCount"], 0)
        self.assertTrue(graph["originNodeIds"])
        self.assertTrue(graph["destinationNodeIds"])

    def test_identical_route_response_is_served_from_cache(self) -> None:
        request = {
            "origin": "Origin address",
            "destination": "Wihuri address",
            "date": "2026-11-01",
            "mode": "car",
            "sameDay": True,
            "maxResults": 2,
        }
        first = self.client.post("/route", json=request)
        calls_after_first = self.client.app.state.geocoder.calls
        second = self.client.post("/route", json=request)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json(), first.json())
        self.assertEqual(self.client.app.state.geocoder.calls, calls_after_first)

    def test_start_time_must_be_a_local_minute(self) -> None:
        response = self.client.post("/route", json={
            "origin": "Origin address",
            "destination": "Wihuri address",
            "date": "2026-11-01",
            "startTime": "07:00:30",
        })
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
