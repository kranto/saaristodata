#!/usr/bin/env python3
"""Build connection-vessel journeys and arrival-time distributions from voyages."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("voyages", type=Path, help="SQLite database created by build_voyages.py")
    parser.add_argument("data", type=Path, help="data.json with route and pier definitions")
    parser.add_argument("output", type=Path)
    parser.add_argument("--maximum-wait-hours", type=float, default=6)
    parser.add_argument("--minimum-pattern-count", type=int, default=3)
    parser.add_argument("--maximum-observation-gap-seconds", type=int, default=90)
    parser.add_argument("--maximum-implied-speed-knots", type=float, default=20)
    parser.add_argument("--maximum-stationary-seconds", type=int, default=180)
    parser.add_argument(
        "--route-overrides",
        type=Path,
        help="Optional JSON file with analysis-only additional_main_piers by route",
    )
    return parser.parse_args()


def percentile(values: list[int], fraction: float) -> int | None:
    if not values:
        return None
    values = sorted(values)
    position = (len(values) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    return round(values[lower] * (upper - position) + values[upper] * (position - lower))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def route_metadata(path: Path, overrides_path: Path | None = None) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    output = {}
    for route_id, route in data.get("routes", {}).items():
        piers = [pier.get("id") or pier.get("name") for pier in route.get("piers", [])]
        output[route_id] = {
            "name": route.get("name_fi") or route.get("name") or route_id,
            "main_piers": {
                pier.get("id") or pier.get("name")
                for pier in route.get("piers", [])
                if str(pier.get("type")) == "1"
            },
            "piers": {pier for pier in piers if pier},
        }
    if overrides_path:
        overrides = json.loads(overrides_path.read_text(encoding="utf-8"))
        for route_id, piers in overrides.get("additional_main_piers", {}).items():
            if route_id in output:
                output[route_id]["main_piers"].update(piers)
    return output


def finish_journey(journey: dict, complete: bool, journeys: list[dict], stops: list[dict]) -> None:
    legs = journey["legs"]
    if not legs:
        return
    sequence = [legs[0]["origin_pier"]] + [leg["destination_pier"] for leg in legs]
    journey_id = len(journeys) + 1
    start_ms = legs[0]["departure_ms"]
    end_ms = legs[-1]["arrival_ms"]
    driving_duration_ms = sum(
        leg["arrival_ms"] - leg["departure_ms"] for leg in legs
    )
    driving_duration_seconds = round(driving_duration_ms / 1000)
    elapsed_duration_seconds = round((end_ms - start_ms) / 1000)
    fallback_legs = sum(
        leg["origin_endpoint_method"] == "closest_approach"
        or leg["destination_endpoint_method"] == "closest_approach"
        for leg in legs
    )
    journeys.append({
        "journey_id": journey_id,
        "mmsi": journey["mmsi"],
        "route_id": journey["route_id"],
        "route_name": journey["route_name"],
        "start_pier": sequence[0],
        "end_pier": sequence[-1],
        "departure_utc": legs[0]["departure_utc"],
        "arrival_utc": legs[-1]["arrival_utc"],
        "week_start": datetime.fromtimestamp(start_ms / 1000).date().isoformat(),
        "duration_seconds": elapsed_duration_seconds,
        "driving_duration_seconds": driving_duration_seconds,
        "intermediate_wait_seconds": max(
            0, elapsed_duration_seconds - driving_duration_seconds
        ),
        "legs": len(legs),
        "stops_after_departure": max(0, len(sequence) - 2),
        "sequence": ">".join(sequence),
        "complete": int(complete),
        "fallback_legs": fallback_legs,
        "timing_confidence": "high" if fallback_legs == 0 else "estimated",
    })
    prefix = [sequence[0]]
    driving_elapsed_ms = 0
    for stop_index, leg in enumerate(legs, start=1):
        prefix.append(leg["destination_pier"])
        driving_elapsed_ms += leg["arrival_ms"] - leg["departure_ms"]
        driving_elapsed_seconds = round(driving_elapsed_ms / 1000)
        wall_elapsed_seconds = round((leg["arrival_ms"] - start_ms) / 1000)
        stops.append({
            "journey_id": journey_id,
            "mmsi": journey["mmsi"],
            "route_id": journey["route_id"],
            "start_pier": sequence[0],
            "destination_pier": leg["destination_pier"],
            "stop_index": stop_index,
            "prior_intermediate_stops": max(0, stop_index - 1),
            "prefix": ">".join(prefix),
            "elapsed_seconds": wall_elapsed_seconds,
            "driving_elapsed_seconds": driving_elapsed_seconds,
            "intermediate_wait_seconds": max(
                0, wall_elapsed_seconds - driving_elapsed_seconds
            ),
            "arrival_utc": leg["arrival_utc"],
            "timing_confidence": (
                "high"
                if all(
                    previous["origin_endpoint_method"] != "closest_approach"
                    and previous["destination_endpoint_method"] != "closest_approach"
                    for previous in legs[:stop_index]
                )
                else "estimated"
            ),
        })


def main() -> None:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    routes = route_metadata(args.data, args.route_overrides)
    connection = sqlite3.connect(f"file:{args.voyages}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    voyage_rows = [
        dict(row)
        for row in connection.execute(
            """
            SELECT voyage_id, mmsi, route_id, route_name, origin_pier, destination_pier,
                   departure_utc, arrival_utc, departure_ms, arrival_ms, duration_seconds,
                   origin_endpoint_method, destination_endpoint_method, quality
            FROM voyages
            WHERE quality IN ('good', 'usable')
              AND maximum_collection_gap_seconds <= ?
              AND maximum_segment_speed_knots <= ?
              AND maximum_stationary_seconds <= ?
            ORDER BY mmsi, departure_ms, voyage_id
            """,
            (
                args.maximum_observation_gap_seconds,
                args.maximum_implied_speed_knots,
                args.maximum_stationary_seconds,
            ),
        )
    ]
    by_vessel: dict[int, list[dict]] = defaultdict(list)
    for voyage in voyage_rows:
        by_vessel[voyage["mmsi"]].append(voyage)

    leg_groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for voyage in voyage_rows:
        leg_groups[(voyage["route_id"], voyage["origin_pier"], voyage["destination_pier"])].append(voyage)
    leg_rows = []
    for (route_id, origin_pier, destination_pier), group in sorted(leg_groups.items()):
        timings = [
            row["duration_seconds"]
            for row in group
            if row["origin_endpoint_method"] == "slow_core"
            and row["destination_endpoint_method"] == "slow_core"
        ]
        if len(timings) < args.minimum_pattern_count:
            continue
        leg_rows.append({
            "route_id": route_id,
            "route_name": group[0]["route_name"],
            "origin_pier": origin_pier,
            "destination_pier": destination_pier,
            "voyages": len(group),
            "vessels": len({row["mmsi"] for row in group}),
            "slow_core_timings": len(timings),
            "duration_p10_seconds": percentile(timings, 0.10),
            "duration_median_seconds": percentile(timings, 0.50),
            "duration_p90_seconds": percentile(timings, 0.90),
        })
    leg_fields = [
        "route_id", "route_name", "origin_pier", "destination_pier", "voyages",
        "vessels", "slow_core_timings", "duration_p10_seconds",
        "duration_median_seconds", "duration_p90_seconds",
    ]
    write_csv(args.output / "leg-windows.csv", leg_rows, leg_fields)

    maximum_wait_ms = round(args.maximum_wait_hours * 3_600_000)
    journeys: list[dict] = []
    stops: list[dict] = []
    rejected = Counter()
    for mmsi, vessel_voyages in by_vessel.items():
        current = None
        for voyage in vessel_voyages:
            metadata = routes.get(voyage["route_id"])
            if not metadata or not metadata["main_piers"]:
                rejected["route_without_main_pier"] += 1
                continue
            if current:
                previous = current["legs"][-1]
                continuous = (
                    voyage["route_id"] == current["route_id"]
                    and voyage["origin_pier"] == previous["destination_pier"]
                    and 0 <= voyage["departure_ms"] - previous["arrival_ms"] <= maximum_wait_ms
                )
                if continuous:
                    current["legs"].append(voyage)
                    if voyage["destination_pier"] in metadata["main_piers"]:
                        finish_journey(current, True, journeys, stops)
                        current = None
                    continue
                finish_journey(current, False, journeys, stops)
                current = None
            if voyage["origin_pier"] in metadata["main_piers"]:
                current = {
                    "mmsi": mmsi,
                    "route_id": voyage["route_id"],
                    "route_name": voyage["route_name"],
                    "legs": [voyage],
                }
                if voyage["destination_pier"] in metadata["main_piers"]:
                    finish_journey(current, True, journeys, stops)
                    current = None
            else:
                rejected["not_started_at_main_pier"] += 1
        if current:
            finish_journey(current, False, journeys, stops)

    journey_fields = [
        "journey_id", "mmsi", "route_id", "route_name", "start_pier", "end_pier",
        "departure_utc", "arrival_utc", "week_start", "duration_seconds",
        "driving_duration_seconds", "intermediate_wait_seconds", "legs",
        "stops_after_departure", "sequence", "complete", "fallback_legs", "timing_confidence",
    ]
    stop_fields = [
        "journey_id", "mmsi", "route_id", "start_pier", "destination_pier", "stop_index",
        "prior_intermediate_stops", "prefix", "elapsed_seconds", "driving_elapsed_seconds",
        "intermediate_wait_seconds", "arrival_utc", "timing_confidence",
    ]
    write_csv(args.output / "journeys.csv", journeys, journey_fields)
    write_csv(args.output / "journey-stops.csv", stops, stop_fields)

    pattern_groups: dict[tuple, list[dict]] = defaultdict(list)
    for journey in journeys:
        if journey["complete"]:
            pattern_groups[(journey["route_id"], journey["start_pier"], journey["sequence"])].append(journey)
    pattern_rows = []
    for (route_id, start_pier, sequence), group in sorted(pattern_groups.items()):
        if len(group) < args.minimum_pattern_count:
            continue
        durations = [row["duration_seconds"] for row in group if row["timing_confidence"] == "high"]
        pattern_rows.append({
            "route_id": route_id,
            "route_name": group[0]["route_name"],
            "start_pier": start_pier,
            "sequence": sequence,
            "journeys": len(group),
            "vessels": len({row["mmsi"] for row in group}),
            "first_departure_utc": min(row["departure_utc"] for row in group),
            "last_departure_utc": max(row["departure_utc"] for row in group),
            "high_confidence_timings": len(durations),
            "duration_p10_seconds": percentile(durations, 0.10),
            "duration_median_seconds": percentile(durations, 0.50),
            "duration_p90_seconds": percentile(durations, 0.90),
        })
    pattern_fields = [
        "route_id", "route_name", "start_pier", "sequence", "journeys", "vessels",
        "first_departure_utc", "last_departure_utc", "high_confidence_timings",
        "duration_p10_seconds", "duration_median_seconds", "duration_p90_seconds",
    ]
    write_csv(args.output / "journey-patterns.csv", pattern_rows, pattern_fields)

    arrival_groups: dict[tuple, list[dict]] = defaultdict(list)
    complete_ids = {row["journey_id"] for row in journeys if row["complete"]}
    for stop in stops:
        if stop["journey_id"] in complete_ids:
            arrival_groups[(stop["route_id"], stop["start_pier"], stop["destination_pier"], stop["prefix"])].append(stop)
    arrival_rows = []
    for (route_id, start_pier, destination_pier, prefix), group in sorted(arrival_groups.items()):
        timings = [row["elapsed_seconds"] for row in group if row["timing_confidence"] == "high"]
        if len(group) < args.minimum_pattern_count or len(timings) < args.minimum_pattern_count:
            continue
        arrival_rows.append({
            "route_id": route_id,
            "start_pier": start_pier,
            "destination_pier": destination_pier,
            "prefix": prefix,
            "prior_intermediate_stops": group[0]["prior_intermediate_stops"],
            "journeys": len(group),
            "high_confidence_timings": len(timings),
            "elapsed_p10_seconds": percentile(timings, 0.10),
            "elapsed_median_seconds": percentile(timings, 0.50),
            "elapsed_p90_seconds": percentile(timings, 0.90),
        })
    arrival_fields = [
        "route_id", "start_pier", "destination_pier", "prefix", "prior_intermediate_stops",
        "journeys", "high_confidence_timings", "elapsed_p10_seconds",
        "elapsed_median_seconds", "elapsed_p90_seconds",
    ]
    write_csv(args.output / "arrival-windows.csv", arrival_rows, arrival_fields)

    summary = {
        "input_voyages": len(voyage_rows),
        "journeys": len(journeys),
        "complete_journeys": sum(row["complete"] for row in journeys),
        "high_confidence_complete_journeys": sum(
            row["complete"] and row["timing_confidence"] == "high" for row in journeys
        ),
        "journey_patterns": len(pattern_rows),
        "arrival_windows": len(arrival_rows),
        "leg_windows": len(leg_rows),
        "routes": len({row["route_id"] for row in journeys}),
        "vessels": len({row["mmsi"] for row in journeys}),
        "rejected_or_unstarted_legs": dict(rejected),
        "parameters": {
            "maximum_wait_hours": args.maximum_wait_hours,
            "minimum_pattern_count": args.minimum_pattern_count,
            "maximum_observation_gap_seconds": args.maximum_observation_gap_seconds,
            "maximum_implied_speed_knots": args.maximum_implied_speed_knots,
            "maximum_stationary_seconds": args.maximum_stationary_seconds,
            "route_overrides": str(args.route_overrides) if args.route_overrides else None,
        },
    }
    (args.output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
