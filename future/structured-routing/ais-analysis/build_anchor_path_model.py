#!/usr/bin/env python3
"""Build exact AIS travel-time paths from any observed departure pier.

Unlike the main-pier journey model, this model can use a published departure
from an overnight or demand pier as the timing anchor.  Only uninterrupted,
high-confidence voyage legs are included and long waits are chain boundaries.
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
from collections import defaultdict
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("voyages", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--minimum-samples", type=int, default=5)
    parser.add_argument("--maximum-wait-minutes", type=int, default=30)
    parser.add_argument("--maximum-path-legs", type=int, default=20)
    return parser.parse_args()


def percentile(values: list[int], fraction: float) -> int:
    values = sorted(values)
    position = (len(values) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    return round(values[lower] * (upper - position) + values[upper] * (position - lower))


def minutes(seconds: int) -> float:
    return round(seconds / 60, 1)


def main() -> None:
    args = parse_args()
    connection = sqlite3.connect(f"file:{args.voyages}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    rows = [
        dict(row)
        for row in connection.execute(
            """
            SELECT voyage_id, mmsi, route_id, origin_pier, destination_pier,
                   departure_ms, arrival_ms, duration_seconds
            FROM voyages
            WHERE quality IN ('good', 'usable')
              AND maximum_collection_gap_seconds <= 90
              AND maximum_segment_speed_knots <= 20
              AND maximum_stationary_seconds <= 180
              AND origin_endpoint_method != 'closest_approach'
              AND destination_endpoint_method != 'closest_approach'
            ORDER BY mmsi, departure_ms, voyage_id
            """
        )
    ]
    maximum_wait_ms = args.maximum_wait_minutes * 60_000
    segments = []
    active = []
    for row in rows:
        if active:
            previous = active[-1]
            continuous = (
                row["mmsi"] == previous["mmsi"]
                and row["route_id"] == previous["route_id"]
                and row["origin_pier"] == previous["destination_pier"]
                and 0 <= row["departure_ms"] - previous["arrival_ms"] <= maximum_wait_ms
            )
            if not continuous:
                segments.append(active)
                active = []
        active.append(row)
    if active:
        segments.append(active)

    groups: dict[tuple[str, tuple[str, ...]], list[int]] = defaultdict(list)
    completion_groups: dict[tuple[str, tuple[str, ...]], list[int]] = defaultdict(list)
    for segment in segments:
        for start in range(len(segment)):
            sequence = [segment[start]["origin_pier"]]
            driving_seconds = 0
            for end in range(start, min(len(segment), start + args.maximum_path_legs)):
                leg = segment[end]
                sequence.append(leg["destination_pier"])
                driving_seconds += leg["duration_seconds"]
                groups[(leg["route_id"], tuple(sequence))].append(driving_seconds)
                completion_seconds = round(
                    (leg["arrival_ms"] - segment[start]["departure_ms"]) / 1000
                )
                completion_groups[(leg["route_id"], tuple(sequence))].append(
                    completion_seconds
                )

    route_rows: dict[str, list[dict]] = defaultdict(list)
    destination_groups: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for (route_id, sequence), values in groups.items():
        destination_groups[(route_id, sequence[0], sequence[-1])].extend(values)
        if len(values) < args.minimum_samples:
            continue
        route_rows[route_id].append({
            "from": sequence[0],
            "to": sequence[-1],
            "prefix": list(sequence),
            "sampleSize": len(values),
            "typicalMinutes": [
                minutes(percentile(values, 0.10)),
                minutes(percentile(values, 0.50)),
                minutes(percentile(values, 0.90)),
            ],
            "observedMinutes": [minutes(min(values)), minutes(max(values))],
        })
    fallback_rows: dict[str, list[dict]] = defaultdict(list)
    for (route_id, origin, destination), values in destination_groups.items():
        if len(values) < args.minimum_samples:
            continue
        fallback_rows[route_id].append({
            "from": origin,
            "to": destination,
            "sampleSize": len(values),
            "possibleMinutes": [minutes(min(values)), minutes(max(values))],
            "use": "conservative_possible_range_only",
        })
    completion_route_rows: dict[str, list[dict]] = defaultdict(list)
    completion_destination_groups: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for (route_id, sequence), values in completion_groups.items():
        completion_destination_groups[(route_id, sequence[0], sequence[-1])].extend(values)
        if len(values) < args.minimum_samples:
            continue
        completion_route_rows[route_id].append({
            "from": sequence[0],
            "to": sequence[-1],
            "prefix": list(sequence),
            "sampleSize": len(values),
            "typicalMinutes": [
                minutes(percentile(values, 0.10)),
                minutes(percentile(values, 0.50)),
                minutes(percentile(values, 0.90)),
            ],
            "observedMinutes": [minutes(min(values)), minutes(max(values))],
        })
    completion_fallback_rows: dict[str, list[dict]] = defaultdict(list)
    for (route_id, origin, destination), values in completion_destination_groups.items():
        if len(values) < args.minimum_samples:
            continue
        completion_fallback_rows[route_id].append({
            "from": origin,
            "to": destination,
            "sampleSize": len(values),
            "possibleMinutes": [minutes(min(values)), minutes(max(values))],
            "use": "conservative_completion_range_only",
        })
    routes = []
    for route_id in sorted(
        set(route_rows)
        | set(fallback_rows)
        | set(completion_route_rows)
        | set(completion_fallback_rows)
    ):
        paths = route_rows[route_id]
        paths.sort(key=lambda item: (item["from"], item["to"], item["prefix"]))
        fallbacks = fallback_rows[route_id]
        fallbacks.sort(key=lambda item: (item["from"], item["to"]))
        completion_paths = completion_route_rows[route_id]
        completion_paths.sort(key=lambda item: (item["from"], item["to"], item["prefix"]))
        completion_fallbacks = completion_fallback_rows[route_id]
        completion_fallbacks.sort(key=lambda item: (item["from"], item["to"]))
        routes.append({
            "id": route_id,
            "pathWindows": paths,
            "destinationFallbacks": fallbacks,
            "completionPathWindows": completion_paths,
            "completionDestinationFallbacks": completion_fallbacks,
        })
    output = {
        "schemaVersion": 2,
        "status": "experimental_not_for_current_application",
        "modelVersion": "ais-anchor-paths-v2",
        "policy": {
            "minimumSamples": args.minimum_samples,
            "maximumWaitMinutesWithinChain": args.maximum_wait_minutes,
            "maximumPathLegs": args.maximum_path_legs,
            "longWaitsExcluded": True,
            "shortIntermediateWaitsIncludedInCompletion": True,
            "closestApproachTimingsExcluded": True,
            "exactPathOnly": True,
        },
        "routes": routes,
    }
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "routes": len(routes),
        "pathWindows": sum(len(route["pathWindows"]) for route in routes),
        "destinationFallbacks": sum(len(route["destinationFallbacks"]) for route in routes),
        "completionPathWindows": sum(
            len(route["completionPathWindows"]) for route in routes
        ),
        "completionDestinationFallbacks": sum(
            len(route["completionDestinationFallbacks"]) for route in routes
        ),
        "inputVoyages": len(rows),
        "continuousSegments": len(segments),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
