#!/usr/bin/env python3
"""Separate outbound and inbound calls on ordered out-and-back routes."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


WEEKDAY_CLASSES = {0: "ma", 1: "ti-to", 2: "ti-to", 3: "ti-to", 4: "pe", 5: "la", 6: "su"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("journeys", type=Path)
    parser.add_argument("journey_stops", type=Path)
    parser.add_argument("route_directions", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--timezone", default="Europe/Helsinki")
    parser.add_argument("--minimum-samples", type=int, default=3)
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


def season(month: int) -> str:
    if month in {6, 7, 8}:
        return "kesä"
    if month in {4, 5, 9, 10}:
        return "kevät-syksy"
    return "talvi"


def time_band(hour: int) -> str:
    if hour < 10:
        return "aamu"
    if hour < 15:
        return "päivä"
    if hour < 19:
        return "iltapäivä"
    return "ilta-yö"


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = list(rows[0]) if rows else ["route_id"]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    timezone = ZoneInfo(args.timezone)
    structures = json.loads(args.route_directions.read_text(encoding="utf-8"))["routes"]

    journeys = {}
    for row in read_csv(args.journeys):
        if row["timing_confidence"] != "high" or row["route_id"] not in structures:
            continue
        departure = datetime.fromisoformat(row["departure_utc"].replace("Z", "+00:00"))
        local = departure.astimezone(timezone)
        journeys[row["journey_id"]] = {
            **row,
            "local": local,
            "weekday_class": WEEKDAY_CLASSES[local.weekday()],
            "season": season(local.month),
            "time_band": time_band(local.hour),
        }

    stops_by_journey: dict[str, list[dict]] = defaultdict(list)
    for row in read_csv(args.journey_stops):
        if row["journey_id"] in journeys and row["timing_confidence"] == "high":
            stops_by_journey[row["journey_id"]].append({
                **row,
                "stop_index": int(row["stop_index"]),
                "driving_elapsed_seconds": int(row["driving_elapsed_seconds"]),
            })
    for rows in stops_by_journey.values():
        rows.sort(key=lambda row: row["stop_index"])

    events = []
    ambiguous_journeys = 0
    for journey_id, journey in journeys.items():
        structure = structures[journey["route_id"]]
        ranks = {pier: index for index, pier in enumerate(structure["outboundStopOrder"])}
        calls = stops_by_journey.get(journey_id, [])
        ranked = [(index, ranks[row["destination_pier"]]) for index, row in enumerate(calls) if row["destination_pier"] in ranks and row["destination_pier"] != structure["mainPier"]]
        if not ranked:
            ambiguous_journeys += 1
            continue
        maximum_rank = max(rank for _, rank in ranked)
        turnaround_index = next(index for index, rank in ranked if rank == maximum_rank)
        for index, row in enumerate(calls):
            pier = row["destination_pier"]
            if pier == structure["mainPier"]:
                continue
            if index < turnaround_index:
                phases = ["outbound"]
            elif index == turnaround_index:
                phases = ["outbound", "inbound"]
            else:
                phases = ["inbound"]
            for phase in phases:
                events.append({
                    "journey_id": journey_id,
                    "route_id": journey["route_id"],
                    "main_pier": structure["mainPier"],
                    "pier": pier,
                    "phase": phase,
                    "driving_elapsed_seconds": row["driving_elapsed_seconds"],
                    "prefix": row["prefix"],
                    "departure_local": journey["local"].isoformat(),
                    "weekday_class": journey["weekday_class"],
                    "season": journey["season"],
                    "time_band": journey["time_band"],
                    "mmsi": journey["mmsi"],
                })

    groups: dict[tuple, list[dict]] = defaultdict(list)
    context_groups: dict[tuple, list[dict]] = defaultdict(list)
    for event in events:
        groups[(event["route_id"], event["main_pier"], event["pier"], event["phase"])].append(event)
        context_groups[(
            event["route_id"], event["main_pier"], event["pier"], event["phase"],
            event["weekday_class"], event["season"], event["time_band"],
        )].append(event)

    summary_rows = []
    for (route_id, main, pier, phase), group in sorted(groups.items()):
        if len(group) < args.minimum_samples:
            continue
        values = [row["driving_elapsed_seconds"] for row in group]
        summary_rows.append({
            "route_id": route_id,
            "main_pier": main,
            "pier": pier,
            "phase": phase,
            "observations": len(group),
            "path_variants": len({row["prefix"] for row in group}),
            "p10_seconds": percentile(values, 0.10),
            "median_seconds": percentile(values, 0.50),
            "p90_seconds": percentile(values, 0.90),
            "observed_min_seconds": min(values),
            "observed_max_seconds": max(values),
        })

    context_rows = []
    for key, group in sorted(context_groups.items()):
        if len(group) < args.minimum_samples:
            continue
        route_id, main, pier, phase, weekday_class, season_name, band = key
        values = [row["driving_elapsed_seconds"] for row in group]
        context_rows.append({
            "route_id": route_id,
            "main_pier": main,
            "pier": pier,
            "phase": phase,
            "weekday_class": weekday_class,
            "season": season_name,
            "time_band": band,
            "observations": len(group),
            "path_variants": len({row["prefix"] for row in group}),
            "p10_seconds": percentile(values, 0.10),
            "median_seconds": percentile(values, 0.50),
            "p90_seconds": percentile(values, 0.90),
            "observed_min_seconds": min(values),
            "observed_max_seconds": max(values),
        })

    write_csv(args.output / "directional-call-events.csv", events)
    write_csv(args.output / "directional-call-windows.csv", summary_rows)
    write_csv(args.output / "directional-context-windows.csv", context_rows)
    compact = {
        "schemaVersion": 1,
        "status": "draft",
        "modelVersion": "ais-directional-calls-v1",
        "timezone": args.timezone,
        "policy": {
            "basis": "historical_ais_observations",
            "intermediateWaitsIncluded": False,
            "turnaroundCallIncludedInBothPhases": True,
            "minimumSamples": args.minimum_samples,
        },
        "routes": [],
    }
    for route_id, structure in structures.items():
        compact["routes"].append({
            "id": route_id,
            "mainPier": structure["mainPier"],
            "outboundStopOrder": structure["outboundStopOrder"],
            "interpretation": structure["interpretation"],
            "calls": [
                {
                    "pier": row["pier"],
                    "phase": row["phase"],
                    "sampleSize": row["observations"],
                    "pathVariants": row["path_variants"],
                    "typicalMinutes": [
                        round(row["p10_seconds"] / 60),
                        round(row["median_seconds"] / 60),
                        round(row["p90_seconds"] / 60),
                    ],
                    "possibleMinutes": [
                        round(row["observed_min_seconds"] / 60),
                        round(row["observed_max_seconds"] / 60),
                    ],
                }
                for row in summary_rows
                if row["route_id"] == route_id
            ],
            "contextCalls": [
                {
                    "pier": row["pier"],
                    "phase": row["phase"],
                    "weekdayClass": row["weekday_class"],
                    "season": row["season"],
                    "timeBand": row["time_band"],
                    "sampleSize": row["observations"],
                    "pathVariants": row["path_variants"],
                    "typicalMinutes": [
                        round(row["p10_seconds"] / 60),
                        round(row["median_seconds"] / 60),
                        round(row["p90_seconds"] / 60),
                    ],
                    "possibleMinutes": [
                        round(row["observed_min_seconds"] / 60),
                        round(row["observed_max_seconds"] / 60),
                    ],
                }
                for row in context_rows
                if row["route_id"] == route_id
            ],
        })
    compact_path = args.compact_output or args.output / "directional-call-model.json"
    compact_path.parent.mkdir(parents=True, exist_ok=True)
    compact_path.write_text(
        json.dumps(compact, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    summary = {
        "routes": sorted(structures),
        "eligibleJourneys": len(journeys),
        "ambiguousJourneys": ambiguous_journeys,
        "directionalCallEvents": len(events),
        "directionalCallWindows": len(summary_rows),
        "directionalContextWindows": len(context_rows),
        "turnaroundCallIncludedInBothPhases": True,
    }
    (args.output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
