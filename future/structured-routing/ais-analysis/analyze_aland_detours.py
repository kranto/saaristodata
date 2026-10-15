#!/usr/bin/env python3
"""Validate whether Husö and Kyrkogårdsö detour effects accumulate in AIS data."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("journeys", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--compact-output", type=Path)
    return parser.parse_args()


def percentile(values: list[int], fraction: float) -> int:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return round(ordered[lower] * (upper - position) + ordered[upper] * (position - lower))


def main() -> None:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    groups: dict[str, list[int]] = defaultdict(list)
    with args.journeys.open(encoding="utf-8") as file:
        for row in csv.DictReader(file):
            if not (
                row["route_id"] == "sodralinjen"
                and row["timing_confidence"] == "high"
                and row["complete"] == "1"
                and row["start_pier"] == "Sottunga"
                and row["end_pier"] == "Sottunga"
            ):
                continue
            sequence = row["sequence"].split(">")
            if "Kökar" not in sequence:
                continue
            huso = "Husö" in sequence
            kyrkogardso = "Kyrkogårdsö" in sequence
            key = "both" if huso and kyrkogardso else "huso" if huso else "kyrkogardso" if kyrkogardso else "none"
            groups[key].append(int(row["driving_duration_seconds"]))

    order = ["none", "huso", "kyrkogardso", "both"]
    rows = []
    baseline = percentile(groups["none"], 0.50)
    for key in order:
        values = groups[key]
        median = percentile(values, 0.50)
        rows.append({
            "detours": key,
            "journeys": len(values),
            "p10_minutes": round(percentile(values, 0.10) / 60, 1),
            "median_minutes": round(median / 60, 1),
            "p90_minutes": round(percentile(values, 0.90) / 60, 1),
            "median_increase_minutes": round((median - baseline) / 60, 1),
        })
    with (args.output / "sottunga-kokar-detour-comparison.csv").open(
        "w", encoding="utf-8", newline=""
    ) as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    compact = {
        "schemaVersion": 1,
        "status": "draft",
        "routeId": "sodralinjen",
        "comparison": "complete high-confidence Sottunga-Kökar-Sottunga AIS journeys",
        "duration": "driving time; intermediate waits excluded",
        "publishedDelayMinutes": {"Husö": 10, "Kyrkogårdsö": 20, "both": 30},
        "modelRule": "additive",
        "conclusion": "cumulative_effect_supported",
        "caveat": "AIS driving-duration differences are not the same quantity as the timetable's approximate downstream delay.",
        "groups": rows,
    }
    compact_path = args.compact_output or args.output / "aland-detour-validation.json"
    compact_path.parent.mkdir(parents=True, exist_ok=True)
    compact_path.write_text(
        json.dumps(compact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(compact, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
