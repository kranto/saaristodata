#!/usr/bin/env python3
"""Tests for arbitrary-address routing orchestration."""

from __future__ import annotations

import sys
import json
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from query_address_routes import (  # noqa: E402
    DEFAULT_STOP_INDEX,
    DESTINATION_NODE,
    MAX_ADDRESS_ROUTE_LEGS,
    ORIGIN_NODE,
    add_external_edges,
    known_stop,
    query_address_routes,
    usable_matrix_entries,
)


class FakeGeocoder:
    def geocode(self, query: str) -> dict:
        if query == "Origin address":
            coordinates = {"lat": 61.5, "lon": 23.7}
        else:
            coordinates = {"lat": 60.4, "lon": 21.8}
        return {
            "query": query,
            "displayName": f"Resolved {query}",
            "coordinates": coordinates,
            "provider": "test",
            "attribution": "test data",
        }


class KnownStopTrackingGeocoder(FakeGeocoder):
    def __init__(self) -> None:
        self.queries = []

    def geocode(self, query: str) -> dict:
        self.queries.append(query)
        if query.casefold() in {"wihuri", "ruotsalainen", "maisaari"}:
            raise AssertionError("known stop names must not be sent to external geocoding")
        return super().geocode(query)


class FakeRouter:
    def infer_road_area(self, point: dict, index: dict, *, mode: str) -> dict:
        area_id = "mainland_finland" if point["lat"] > 61 else "stop:Wihuri"
        return {
            "roadArea": {"id": area_id, "inference": "test_fixture"},
        }

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


class FakeLimitedMatrixRouter(FakeRouter):
    def matrix(
        self, sources: list[dict], targets: list[dict], mode: str,
        *, exclude_ferries: bool = True,
    ) -> list[dict]:
        raise RuntimeError("matrix distance limit")

    def measure_route(
        self, origin: dict, destination: dict, mode: str,
        *, exclude_ferries: bool = True,
    ) -> dict:
        return {"durationSeconds": 900, "distanceMeters": 10_000}


class FakePartialMatrixRouter(FakeRouter):
    def __init__(self) -> None:
        self.measured = []

    def matrix(
        self, sources: list[dict], targets: list[dict], mode: str,
        *, exclude_ferries: bool = True,
    ) -> list[dict]:
        return [
            {"from_index": 0, "to_index": 0, "time": 600, "distance": 5},
            {"from_index": 0, "to_index": 1, "time": None, "distance": None},
        ]

    def measure_route(
        self, origin: dict, destination: dict, mode: str,
        *, exclude_ferries: bool = True,
    ) -> dict:
        self.measured.append((origin, destination))
        return {"durationSeconds": 900, "distanceMeters": 10_000}


class AddressGraphTests(unittest.TestCase):
    def test_address_routes_allow_long_archipelago_chains(self) -> None:
        self.assertEqual(MAX_ADDRESS_ROUTE_LEGS, 21)

    def test_known_stop_names_are_case_insensitive_and_unambiguous(self) -> None:
        index = json.loads(DEFAULT_STOP_INDEX.read_text())
        self.assertEqual(known_stop(index, "wihuri")["id"], "Wihuri")
        self.assertEqual(known_stop(index, "RUOTSALAINEN")["id"], "Ruotsalainen")
        self.assertEqual(known_stop(index, "maisaari")["id"], "Maisaari")
        self.assertIsNone(known_stop(index, "Kumlinge"))
        self.assertEqual(
            known_stop(index, "Kumlinge (lauttaranta)")["id"], "Kumlinge",
        )

    def test_all_stops_in_each_road_area_become_candidates(self) -> None:
        graph = {
            "nodes": [
                {"id": "A"}, {"id": "B"}, {"id": "C"}, {"id": "D"},
            ],
            "edges": [],
        }
        index = {
            "stops": [
                {"id": "A", "roadAreaId": "origin", "coordinates": {"lat": 1, "lon": 1}},
                {"id": "B", "roadAreaId": "origin", "coordinates": {"lat": 1, "lon": 2}},
                {"id": "C", "roadAreaId": "destination", "coordinates": {"lat": 2, "lon": 1}},
                {"id": "D", "roadAreaId": "destination", "coordinates": {"lat": 2, "lon": 2}},
            ]
        }
        location = {"displayName": "Address", "coordinates": {"lat": 0, "lon": 0}}
        result = add_external_edges(
            graph, index, FakeRouter(), location, location,
            "origin", "destination", "car",
        )
        pairs = {(edge["from"], edge["to"]) for edge in result["edges"]}
        self.assertEqual(
            pairs,
            {
                (ORIGIN_NODE, "A"), (ORIGIN_NODE, "B"),
                ("C", DESTINATION_NODE), ("D", DESTINATION_NODE),
            },
        )

    def test_bicycle_access_over_150_kilometres_is_dropped(self) -> None:
        values = usable_matrix_entries(
            [
                {"from_index": 0, "to_index": 0, "time": 100, "distance": 149.9},
                {"from_index": 0, "to_index": 1, "time": 100, "distance": 150.1},
            ],
            mode="bicycle",
        )
        self.assertEqual([item["toIndex"] for item in values], [0])

    def test_matrix_limit_falls_back_to_all_individual_routes(self) -> None:
        graph = {
            "nodes": [{"id": f"A{number}"} for number in range(10)] + [{"id": "B"}],
            "edges": [],
        }
        index = {
            "stops": [
                {
                    "id": f"A{number}",
                    "roadAreaId": "origin",
                    "coordinates": {"lat": 1, "lon": 1 + number / 100},
                }
                for number in range(10)
            ] + [{
                "id": "B",
                "roadAreaId": "destination",
                "coordinates": {"lat": 2, "lon": 2},
            }]
        }
        location = {"displayName": "Address", "coordinates": {"lat": 1, "lon": 1}}
        result = add_external_edges(
            graph, index, FakeLimitedMatrixRouter(), location, location,
            "origin", "destination", "car",
        )
        access = [
            edge for edge in result["edges"]
            if edge["from"] == ORIGIN_NODE
        ]
        self.assertEqual(len(access), 10)

    def test_null_matrix_entry_falls_back_to_individual_route(self) -> None:
        router = FakePartialMatrixRouter()
        graph = {"nodes": [{"id": "A"}, {"id": "B"}, {"id": "C"}], "edges": []}
        index = {
            "stops": [
                {"id": "A", "roadAreaId": "origin", "coordinates": {"lat": 1, "lon": 1}},
                {"id": "B", "roadAreaId": "origin", "coordinates": {"lat": 1, "lon": 2}},
                {"id": "C", "roadAreaId": "destination", "coordinates": {"lat": 2, "lon": 2}},
            ]
        }
        location = {"displayName": "Address", "coordinates": {"lat": 0, "lon": 0}}
        result = add_external_edges(
            graph, index, router, location, location,
            "origin", "destination", "car",
        )
        access = [edge for edge in result["edges"] if edge["from"] == ORIGIN_NODE]
        self.assertEqual({edge["to"] for edge in access}, {"A", "B"})
        self.assertGreaterEqual(len(router.measured), 1)

    def test_address_query_uses_external_access_and_internal_schedule(self) -> None:
        result = query_address_routes(
            "Origin address",
            "Wihuri address",
            date(2026, 11, 1),
            mode="car",
            same_day=True,
            max_results=2,
            geocoder=FakeGeocoder(),
            router=FakeRouter(),
        )
        self.assertEqual(result["status"], "routes_found")
        self.assertEqual(result["query"]["originRoadArea"]["id"], "mainland_finland")
        self.assertEqual(result["query"]["destinationRoadArea"]["id"], "stop:Wihuri")
        first = result["itineraries"][0]
        self.assertEqual(first["legs"][0]["from"], ORIGIN_NODE)
        self.assertEqual(first["legs"][0]["externalRouting"]["role"], "access")
        self.assertEqual(first["legs"][-1]["to"], DESTINATION_NODE)
        route_ids = {leg.get("routeId") for leg in first["legs"]}
        self.assertIn("rymattylanreitti", route_ids)

    def test_known_destination_stop_bypasses_geocoding_and_external_egress(self) -> None:
        geocoder = KnownStopTrackingGeocoder()
        result = query_address_routes(
            "Origin address",
            "wihuri",
            date(2026, 11, 1),
            mode="car",
            same_day=True,
            max_results=2,
            geocoder=geocoder,
            router=FakeRouter(),
        )
        self.assertEqual(result["status"], "routes_found")
        self.assertEqual(geocoder.queries, ["Origin address"])
        self.assertEqual(result["query"]["destinationAddress"]["displayName"], "Wihuri")
        self.assertEqual(result["query"]["destinationRoadArea"]["inference"], "known_stop_name")
        self.assertEqual(result["itineraries"][0]["legs"][-1]["to"], "Wihuri")


if __name__ == "__main__":
    unittest.main()
