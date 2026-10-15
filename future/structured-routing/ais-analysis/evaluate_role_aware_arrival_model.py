#!/usr/bin/env python3
"""Temporal backtest for role-aware AIS arrival windows."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("call_roles", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--test-days", type=int, default=90)
    parser.add_argument("--minimum-samples", type=int, default=5)
    return parser.parse_args()


def percentile(values: list[int], fraction: float) -> int:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return round(ordered[lower] * (upper - position) + ordered[upper] * (position - lower))


def metrics(rows: list[dict]) -> dict:
    if not rows:
        return {"predictions": 0}
    errors = sorted(abs(row["actual"] - row["median"]) for row in rows)
    widths = sorted(row["p90"] - row["p10"] for row in rows)
    return {
        "predictions": len(rows),
        "medianAbsoluteErrorMinutes": round(percentile(errors, 0.50) / 60, 2),
        "p90AbsoluteErrorMinutes": round(percentile(errors, 0.90) / 60, 2),
        "medianRangeWidthMinutes": round(percentile(widths, 0.50) / 60, 2),
        "rangeCoveragePercent": round(
            100 * sum(row["p10"] <= row["actual"] <= row["p90"] for row in rows) / len(rows), 2
        ),
        "observedRangeCoveragePercent": round(
            100 * sum(row["minimum"] <= row["actual"] <= row["maximum"] for row in rows) / len(rows), 2
        ),
        "within10MinutesPercent": round(
            100 * sum(abs(row["actual"] - row["median"]) <= 600 for row in rows) / len(rows), 2
        ),
        "within20MinutesPercent": round(
            100 * sum(abs(row["actual"] - row["median"]) <= 1200 for row in rows) / len(rows), 2
        ),
    }


def main() -> None:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with args.call_roles.open(encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    for row in rows:
        row["departure"] = datetime.fromisoformat(row["departure_utc"].replace("Z", "+00:00"))
        row["actual"] = int(row["driving_elapsed_seconds"])
    cutoff = max(row["departure"] for row in rows) - timedelta(days=args.test_days)
    training = [row for row in rows if row["departure"] < cutoff]
    testing = [row for row in rows if row["departure"] >= cutoff]

    exact_groups: dict[tuple, list[int]] = defaultdict(list)
    fallback_groups: dict[tuple, list[int]] = defaultdict(list)
    for row in training:
        base = (
            row["route_id"], row["start_pier"], row["end_pier"], row["pier"],
            row["call_role"], row["journey_shape"],
        )
        exact_groups[base + (row["prefix"],)].append(row["actual"])
        fallback_groups[base].append(row["actual"])

    predictions = []
    for row in testing:
        base = (
            row["route_id"], row["start_pier"], row["end_pier"], row["pier"],
            row["call_role"], row["journey_shape"],
        )
        exact = exact_groups.get(base + (row["prefix"],), [])
        fallback = fallback_groups.get(base, [])
        if len(exact) >= args.minimum_samples:
            source, values = "exact_path", exact
        elif len(fallback) >= args.minimum_samples:
            source, values = "role_fallback", fallback
        else:
            continue
        predictions.append({
            "route_id": row["route_id"],
            "source": source,
            "actual": row["actual"],
            "p10": percentile(values, 0.10),
            "median": percentile(values, 0.50),
            "p90": percentile(values, 0.90),
            "minimum": min(values),
            "maximum": max(values),
        })

    fieldnames = ["route_id", "source", "actual", "p10", "median", "p90", "minimum", "maximum"]
    with (args.output / "predictions.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(predictions)

    by_route = {}
    for route_id in sorted({row["route_id"] for row in testing}):
        by_route[route_id] = metrics([row for row in predictions if row["route_id"] == route_id])
        by_route[route_id]["testEvents"] = sum(row["route_id"] == route_id for row in testing)
        by_route[route_id]["coveragePercent"] = round(
            100 * by_route[route_id]["predictions"] / by_route[route_id]["testEvents"], 2
        ) if by_route[route_id]["testEvents"] else 0.0
    summary = {
        "cutoffUtc": cutoff.isoformat(),
        "testDays": args.test_days,
        "minimumSamples": args.minimum_samples,
        "trainingEvents": len(training),
        "testEvents": len(testing),
        "predictionCoveragePercent": round(100 * len(predictions) / len(testing), 2),
        "overall": metrics(predictions),
        "bySource": {
            source: metrics([row for row in predictions if row["source"] == source])
            for source in ("exact_path", "role_fallback")
        },
        "byRoute": by_route,
    }
    (args.output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
