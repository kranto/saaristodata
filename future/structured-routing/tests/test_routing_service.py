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
        self.assertIn("Mahdolliset vuorot tällä lauttavälillä", response.text)
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
