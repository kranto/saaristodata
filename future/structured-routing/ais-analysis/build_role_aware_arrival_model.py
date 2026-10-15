#!/usr/bin/env python3
"""Build arrival-time windows without mixing structurally different calls."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("call_roles", type=Path)
    parser.add_argument("topology", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--minimum-samples", type=int, default=5)
    parser.add_argument("--compact-output", type=Path)
    return parser.parse_args()


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as file:
        return list(csv.DictReader(file))


def percentile(values: list[int], fraction: float) -> int:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return round(ordered[lower] * (upper - position) + ordered[upper] * (position - lower))


def summarize(values: list[int]) -> dict[str, int]:
    return {
        "p10_seconds": percentile(values, 0.10),
        "median_seconds": percentile(values, 0.50),
        "p90_seconds": percentile(values, 0.90),
        "observed_min_seconds": min(values),
        "observed_max_seconds": max(values),
    }


def write_csv(path: Path, rows: list[dict], fallback_fields: list[str]) -> None:
    fields = list(rows[0]) if rows else fallback_fields
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def minute_triplet(row: dict) -> list[float]:
    return [round(row[key] / 60, 1) for key in ("p10_seconds", "median_seconds", "p90_seconds")]


def main() -> None:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    structures = json.loads(args.topology.read_text(encoding="utf-8"))["routes"]
    events = read_csv(args.call_roles)
    events = [
        {**row, "driving_elapsed_seconds": int(row["driving_elapsed_seconds"])}
        for row in events
        if row["route_id"] in structures
    ]

    path_groups: dict[tuple, list[dict]] = defaultdict(list)
    fallback_groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in events:
        path_groups[(
            row["route_id"], row["start_pier"], row["end_pier"], row["pier"],
            row["call_role"], row["journey_shape"], row["prefix"],
        )].append(row)
        fallback_groups[(
            row["route_id"], row["start_pier"], row["end_pier"], row["pier"],
            row["call_role"], row["journey_shape"],
        )].append(row)

    path_rows = []
    for key, group in sorted(path_groups.items()):
        if len(group) < args.minimum_samples:
            continue
        route_id, start, end, pier, role, shape, prefix = key
        values = [row["driving_elapsed_seconds"] for row in group]
        path_rows.append({
            "route_id": route_id,
            "start_pier": start,
            "end_pier": end,
            "pier": pier,
            "call_role": role,
            "journey_shape": shape,
            "prefix": prefix,
            "observations": len(group),
            **summarize(values),
        })

    fallback_rows = []
    for key, group in sorted(fallback_groups.items()):
        if len(group) < args.minimum_samples:
            continue
        route_id, start, end, pier, role, shape = key
        values = [row["driving_elapsed_seconds"] for row in group]
        prefixes = {row["prefix"] for row in group}
        repeated_prefixes = {
            prefix for prefix in prefixes
            if sum(1 for row in group if row["prefix"] == prefix) >= args.minimum_samples
        }
        fallback_rows.append({
            "route_id": route_id,
            "start_pier": start,
            "end_pier": end,
            "pier": pier,
            "call_role": role,
            "journey_shape": shape,
            "observations": len(group),
            "path_variants": len(prefixes),
            "repeated_path_variants": len(repeated_prefixes),
            **summarize(values),
        })

    write_csv(args.output / "role-aware-path-windows.csv", path_rows, ["route_id"])
    write_csv(args.output / "role-aware-destination-windows.csv", fallback_rows, ["route_id"])

    compact_routes = []
    for route_id, structure in structures.items():
        schedule_authoritative = structure["topology"].startswith("published_")
        compact_route = {
            "id": route_id,
            "topology": structure["topology"],
            "terminals": structure["terminals"],
            "timingAuthority": "published_timetable" if schedule_authoritative else "historical_ais",
            "scheduleKnowledge": structure.get("scheduleKnowledge", "partial_or_variable"),
            "aisUse": "validation_and_realized_variation" if schedule_authoritative else "arrival_estimation",
            "pathWindows": [
                {
                    "from": row["start_pier"],
                    "journeyEnd": row["end_pier"],
                    "to": row["pier"],
                    "role": row["call_role"],
                    "journeyShape": row["journey_shape"],
                    "prefix": row["prefix"].split(">"),
                    "sampleSize": row["observations"],
                    "typicalMinutes": minute_triplet(row),
                    "observedMinutes": [
                        round(row["observed_min_seconds"] / 60, 1),
                        round(row["observed_max_seconds"] / 60, 1),
                    ],
                }
                for row in path_rows if row["route_id"] == route_id
            ],
            "fallbackWindows": [
                {
                    "from": row["start_pier"],
                    "journeyEnd": row["end_pier"],
                    "to": row["pier"],
                    "role": row["call_role"],
                    "journeyShape": row["journey_shape"],
                    "sampleSize": row["observations"],
                    "pathVariants": row["path_variants"],
                    "use": "conservative_possible_range_only",
                    "possibleMinutes": [
                        round(row["observed_min_seconds"] / 60, 1),
                        round(row["observed_max_seconds"] / 60, 1),
                    ],
                }
                for row in fallback_rows if row["route_id"] == route_id
            ],
        }
        if "scheduleRules" in structure:
            compact_route["scheduleRules"] = structure["scheduleRules"]
        compact_routes.append(compact_route)

    compact = {
        "schemaVersion": 1,
        "status": "draft",
        "modelVersion": "ais-role-aware-arrivals-v1",
        "policy": {
            "basis": "driving time from complete high-confidence AIS journeys",
            "intermediateWaitsIncluded": False,
            "minimumSamples": args.minimum_samples,
            "structurallyDifferentCallsAreNotMixed": True,
            "exactPathProvidesTypicalRange": True,
            "roleFallbackUse": "conservative_possible_range_only",
            "publishedSchedulesRemainAuthoritative": True,
            "publishedApplicationDataModified": False,
        },
        "routes": compact_routes,
    }
    compact_path = args.compact_output or args.output / "role-aware-arrival-model.json"
    compact_path.parent.mkdir(parents=True, exist_ok=True)
    compact_path.write_text(
        json.dumps(compact, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    summary = {
        "routes": len(structures),
        "callEvents": len(events),
        "pathWindows": len(path_rows),
        "fallbackWindows": len(fallback_rows),
        "minimumSamples": args.minimum_samples,
        "publishedApplicationDataModified": False,
    }
    (args.output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
