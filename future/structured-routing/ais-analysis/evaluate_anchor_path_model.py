#!/usr/bin/env python3
"""Temporal backtest for exact paths beginning at any observed pier."""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("voyages", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--test-days", type=int, default=90)
    parser.add_argument("--minimum-samples", type=int, default=5)
    parser.add_argument("--maximum-wait-minutes", type=int, default=30)
    parser.add_argument("--maximum-path-legs", type=int, default=20)
    return parser.parse_args()


def percentile(values: list[float], fraction: float) -> float:
    values = sorted(values)
    position = (len(values) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    return values[lower] * (upper - position) + values[upper] * (position - lower)


def main() -> None:
    args = parse_args()
    connection = sqlite3.connect(f"file:{args.voyages}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    rows = [dict(row) for row in connection.execute(
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
    )]
    maximum_wait_ms = args.maximum_wait_minutes * 60_000
    segments, active = [], []
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

    events = []
    for segment in segments:
        for start in range(len(segment)):
            sequence = [segment[start]["origin_pier"]]
            duration = 0
            for end in range(start, min(len(segment), start + args.maximum_path_legs)):
                leg = segment[end]
                sequence.append(leg["destination_pier"])
                duration += leg["duration_seconds"]
                events.append((leg["route_id"], tuple(sequence), segment[start]["departure_ms"], duration))
    latest_ms = max(event[2] for event in events)
    cutoff_ms = latest_ms - args.test_days * 86_400_000
    training: dict[tuple[str, tuple[str, ...]], list[int]] = defaultdict(list)
    testing = []
    for route_id, sequence, departure_ms, duration in events:
        if departure_ms < cutoff_ms:
            training[(route_id, sequence)].append(duration)
        else:
            testing.append((route_id, sequence, duration))
    predictions = []
    by_route = defaultdict(list)
    for route_id, sequence, actual in testing:
        values = training.get((route_id, sequence), [])
        if len(values) < args.minimum_samples:
            continue
        p10 = percentile(values, 0.10)
        median = percentile(values, 0.50)
        p90 = percentile(values, 0.90)
        result = {
            "absoluteErrorMinutes": abs(actual - median) / 60,
            "insideP10P90": p10 <= actual <= p90,
        }
        predictions.append(result)
        by_route[route_id].append(result)

    def summary(items: list[dict]) -> dict:
        errors = [item["absoluteErrorMinutes"] for item in items]
        return {
            "predictions": len(items),
            "medianAbsoluteErrorMinutes": round(percentile(errors, 0.50), 2) if errors else None,
            "p90AbsoluteErrorMinutes": round(percentile(errors, 0.90), 2) if errors else None,
            "within10Minutes": round(sum(value <= 10 for value in errors) / len(errors), 4) if errors else None,
            "p10P90Coverage": round(sum(item["insideP10P90"] for item in items) / len(items), 4) if items else None,
        }

    report = {
        "status": "temporal_backtest",
        "modelVersion": "ais-anchor-paths-v1",
        "testDays": args.test_days,
        "cutoffUtc": datetime.fromtimestamp(cutoff_ms / 1000, tz=timezone.utc).isoformat(),
        "overall": summary(predictions),
        "routes": [
            {"routeId": route_id, **summary(items)}
            for route_id, items in sorted(by_route.items())
        ],
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
