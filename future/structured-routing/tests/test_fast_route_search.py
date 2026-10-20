#!/usr/bin/env python3
"""Correctness checks for the precompiled timetable search index."""

from __future__ import annotations

import json
import sys
import unittest
from datetime import date, datetime, time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from route_itineraries import ScheduledInstanceIndex, find_itineraries  # noqa: E402
from route_itinerary import next_scheduled_instance  # noqa: E402


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
            {"relaxed": 35, "tight": 5},
        )


if __name__ == "__main__":
    unittest.main()
