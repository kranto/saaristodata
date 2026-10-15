#!/usr/bin/env python3
"""Build schedule-independent connection-vessel travel-time estimates.

The primary timing unit is a directed pier-to-pier leg.  Calendar context is
used to describe which stop chains tend to occur, not to decide whether a leg
observation is usable.  This keeps the model useful when timetables change.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


WEEKDAY_CLASSES = {
    0: "ma",
    1: "ti-to",
    2: "ti-to",
    3: "ti-to",
    4: "pe",
    5: "la",
    6: "su",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("journeys", type=Path)
    parser.add_argument("journey_stops", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--timezone", default="Europe/Helsinki")
    parser.add_argument("--minimum-audit-samples", type=int, default=3)
    parser.add_argument("--minimum-model-samples", type=int, default=5)
    parser.add_argument("--compact-output", type=Path)
    return parser.parse_args()


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as file:
        return list(csv.DictReader(file))


def percentile(values: list[int], fraction: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return round(ordered[lower] * (upper - position) + ordered[upper] * (position - lower))


def quantiles(values: list[int]) -> dict[str, int | None]:
    return {
        "p05_seconds": percentile(values, 0.05),
        "p10_seconds": percentile(values, 0.10),
        "median_seconds": percentile(values, 0.50),
        "p90_seconds": percentile(values, 0.90),
        "p95_seconds": percentile(values, 0.95),
    }


def minute_quantiles(values: list[int]) -> list[int | None]:
    return [
        round(percentile(values, fraction) / 60)
        for fraction in (0.10, 0.50, 0.90)
    ]


def write_csv(path: Path, rows: list[dict], default_field: str) -> None:
    fields = list(rows[0]) if rows else [default_field]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


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


def confidence(samples: int) -> str:
    if samples >= 20:
        return "strong"
    if samples >= 5:
        return "usable"
    return "limited"


def main() -> None:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    timezone = ZoneInfo(args.timezone)

    journeys: dict[str, dict] = {}
    for row in read_csv(args.journeys):
        if row["timing_confidence"] != "high":
            continue
        departure = datetime.fromisoformat(row["departure_utc"].replace("Z", "+00:00"))
        local = departure.astimezone(timezone)
        journeys[row["journey_id"]] = {
            **row,
            "local": local,
            "local_date": local.date().isoformat(),
            "weekday_class": WEEKDAY_CLASSES[local.weekday()],
            "season": season(local.month),
            "time_band": time_band(local.hour),
        }

    stops_by_journey: dict[str, list[dict]] = defaultdict(list)
    for row in read_csv(args.journey_stops):
        if row["journey_id"] not in journeys or row["timing_confidence"] != "high":
            continue
        stops_by_journey[row["journey_id"]].append({
            **row,
            "stop_index": int(row["stop_index"]),
            "driving_elapsed_seconds": int(row["driving_elapsed_seconds"]),
        })
    for rows in stops_by_journey.values():
        rows.sort(key=lambda row: row["stop_index"])

    leg_groups: dict[tuple, list[dict]] = defaultdict(list)
    contextual_leg_groups: dict[tuple, list[dict]] = defaultdict(list)
    path_groups: dict[tuple, list[dict]] = defaultdict(list)
    destination_groups: dict[tuple, list[dict]] = defaultdict(list)
    contextual_destination_groups: dict[tuple, list[dict]] = defaultdict(list)
    pattern_groups: dict[tuple, list[dict]] = defaultdict(list)

    for journey_id, journey in journeys.items():
        stops = stops_by_journey.get(journey_id, [])
        previous_pier = journey["start_pier"]
        previous_driving = 0
        seen_destinations = {previous_pier}
        for stop in stops:
            leg_seconds = stop["driving_elapsed_seconds"] - previous_driving
            if leg_seconds <= 0:
                previous_pier = stop["destination_pier"]
                previous_driving = stop["driving_elapsed_seconds"]
                continue
            observation = {
                "seconds": leg_seconds,
                "journey": journey,
                "journey_id": journey_id,
            }
            leg_key = (journey["route_id"], previous_pier, stop["destination_pier"])
            leg_groups[leg_key].append(observation)
            context_key = (
                *leg_key,
                journey["weekday_class"],
                journey["season"],
                journey["time_band"],
            )
            contextual_leg_groups[context_key].append(observation)

            destination = stop["destination_pier"]
            if destination not in seen_destinations:
                seen_destinations.add(destination)
                path_key = (
                    journey["route_id"],
                    journey["start_pier"],
                    destination,
                    stop["prefix"],
                )
                path_observation = {
                    "seconds": stop["driving_elapsed_seconds"],
                    "journey": journey,
                    "journey_id": journey_id,
                }
                path_groups[path_key].append(path_observation)
                destination_groups[path_key[:3]].append({
                    **path_observation,
                    "prefix": stop["prefix"],
                })
                contextual_destination_groups[(
                    journey["route_id"],
                    journey["start_pier"],
                    destination,
                    journey["weekday_class"],
                    journey["season"],
                    journey["time_band"],
                )].append({
                    **path_observation,
                    "prefix": stop["prefix"],
                })
            previous_pier = destination
            previous_driving = stop["driving_elapsed_seconds"]

        if stops:
            pattern_key = (
                journey["route_id"],
                journey["start_pier"],
                journey["weekday_class"],
                journey["season"],
                journey["time_band"],
            )
            pattern_groups[pattern_key].append(journey)

    route_names = {
        row["route_id"]: row["route_name"]
        for row in journeys.values()
    }

    leg_rows = []
    compact_legs: dict[str, list[dict]] = defaultdict(list)
    for (route_id, origin, destination), group in sorted(leg_groups.items()):
        if len(group) < args.minimum_audit_samples:
            continue
        values = [item["seconds"] for item in group]
        row = {
            "route_id": route_id,
            "route_name": route_names[route_id],
            "origin_pier": origin,
            "destination_pier": destination,
            "observations": len(group),
            "vessels": len({item["journey"]["mmsi"] for item in group}),
            "first_local_date": min(item["journey"]["local_date"] for item in group),
            "last_local_date": max(item["journey"]["local_date"] for item in group),
            **quantiles(values),
            "confidence": confidence(len(group)),
        }
        leg_rows.append(row)
        if len(group) >= args.minimum_model_samples:
            compact_legs[route_id].append({
                "from": origin,
                "to": destination,
                "sampleSize": len(group),
                "minutes": minute_quantiles(values),
                "observedFrom": row["first_local_date"],
                "observedTo": row["last_local_date"],
                "vesselCount": row["vessels"],
            })

    contextual_rows = []
    for key, group in sorted(contextual_leg_groups.items()):
        if len(group) < args.minimum_audit_samples:
            continue
        route_id, origin, destination, weekday_class, season_name, band = key
        contextual_rows.append({
            "route_id": route_id,
            "origin_pier": origin,
            "destination_pier": destination,
            "weekday_class": weekday_class,
            "season": season_name,
            "time_band": band,
            "observations": len(group),
            **quantiles([item["seconds"] for item in group]),
            "confidence": confidence(len(group)),
        })

    path_rows = []
    compact_paths: dict[str, list[dict]] = defaultdict(list)
    for (route_id, start, destination, prefix), group in sorted(path_groups.items()):
        if len(group) < args.minimum_audit_samples:
            continue
        values = [item["seconds"] for item in group]
        row = {
            "route_id": route_id,
            "route_name": route_names[route_id],
            "start_pier": start,
            "destination_pier": destination,
            "via": ">".join(prefix.split(">")[:-1]),
            "prefix": prefix,
            "observations": len(group),
            "vessels": len({item["journey"]["mmsi"] for item in group}),
            "first_local_date": min(item["journey"]["local_date"] for item in group),
            "last_local_date": max(item["journey"]["local_date"] for item in group),
            **quantiles(values),
            "confidence": confidence(len(group)),
        }
        path_rows.append(row)
        if len(group) >= args.minimum_model_samples:
            compact_paths[route_id].append({
                "from": start,
                "to": destination,
                "via": prefix.split(">")[1:-1],
                "sampleSize": len(group),
                "minutes": minute_quantiles(values),
                "observedFrom": row["first_local_date"],
                "observedTo": row["last_local_date"],
                "vesselCount": row["vessels"],
            })

    destination_rows = []
    compact_destinations: dict[str, list[dict]] = defaultdict(list)
    for (route_id, start, destination), group in sorted(destination_groups.items()):
        reliable_prefixes = {
            prefix
            for candidate_route, candidate_start, candidate_destination, prefix in path_groups
            if candidate_route == route_id
            and candidate_start == start
            and candidate_destination == destination
            and len(path_groups[(candidate_route, candidate_start, candidate_destination, prefix)])
            >= args.minimum_model_samples
        }
        retained = [item for item in group if item["prefix"] in reliable_prefixes]
        if not retained:
            continue
        values = [item["seconds"] for item in retained]
        variants = [
            path
            for path in compact_paths[route_id]
            if path["from"] == start and path["to"] == destination
        ]
        # The fallback is intentionally conservative. A timetable change can
        # revive a rare chain, so even a single high-confidence historical
        # path may extend the possible envelope. Typical values still require
        # repeated paths and therefore use ``retained`` above.
        all_observed_values = [item["seconds"] for item in group]
        possible = [
            round(min(all_observed_values) / 60),
            round(max(all_observed_values) / 60),
        ]
        row = {
            "route_id": route_id,
            "route_name": route_names[route_id],
            "start_pier": start,
            "destination_pier": destination,
            "observations": len(retained),
            "path_variants": len(variants),
            "all_observed_path_variants": len({item["prefix"] for item in group}),
            "typical_p10_seconds": percentile(values, 0.10),
            "typical_median_seconds": percentile(values, 0.50),
            "typical_p90_seconds": percentile(values, 0.90),
            "possible_min_seconds": possible[0] * 60,
            "possible_max_seconds": possible[1] * 60,
            "first_local_date": min(item["journey"]["local_date"] for item in retained),
            "last_local_date": max(item["journey"]["local_date"] for item in retained),
            "confidence": confidence(len(retained)),
        }
        destination_rows.append(row)
        compact_destinations[route_id].append({
            "from": start,
            "to": destination,
            "sampleSize": len(retained),
            "pathVariants": len(variants),
            "possiblePathVariants": row["all_observed_path_variants"],
            "typicalMinutes": minute_quantiles(values),
            "possibleMinutes": possible,
            "possibleRangeBasis": "all_high_confidence_observed_paths",
            "observedFrom": row["first_local_date"],
            "observedTo": row["last_local_date"],
        })

    pattern_rows = []
    compact_patterns: dict[str, list[dict]] = defaultdict(list)
    for key, group in sorted(pattern_groups.items()):
        route_id, start, weekday_class, season_name, band = key
        counts = Counter(item["sequence"] for item in group)
        for sequence, count in counts.most_common():
            if count < args.minimum_audit_samples:
                continue
            row = {
                "route_id": route_id,
                "start_pier": start,
                "weekday_class": weekday_class,
                "season": season_name,
                "time_band": band,
                "sequence": sequence,
                "observations": count,
                "context_journeys": len(group),
                "share": round(count / len(group), 4),
                "first_local_date": min(item["local_date"] for item in group if item["sequence"] == sequence),
                "last_local_date": max(item["local_date"] for item in group if item["sequence"] == sequence),
            }
            pattern_rows.append(row)
        retained = [row for row in pattern_rows if row["route_id"] == route_id and row["start_pier"] == start and row["weekday_class"] == weekday_class and row["season"] == season_name and row["time_band"] == band]
        if retained:
            compact_patterns[route_id].append({
                "from": start,
                "weekdayClass": weekday_class,
                "season": season_name,
                "timeBand": band,
                "sampleSize": len(group),
                "sequences": [
                    {
                        "stops": row["sequence"].split(">"),
                        "sampleSize": row["observations"],
                        "share": row["share"],
                    }
                    for row in retained
                ],
            })

    contextual_destination_rows = []
    compact_contextual_destinations: dict[str, list[dict]] = defaultdict(list)
    for key, group in sorted(contextual_destination_groups.items()):
        if len(group) < args.minimum_audit_samples:
            continue
        route_id, start, destination, weekday_class, season_name, band = key
        values = [item["seconds"] for item in group]
        context_journeys = pattern_groups[(
            route_id, start, weekday_class, season_name, band
        )]
        row = {
            "route_id": route_id,
            "start_pier": start,
            "destination_pier": destination,
            "weekday_class": weekday_class,
            "season": season_name,
            "time_band": band,
            "observations": len(group),
            "context_journeys": len(context_journeys),
            "visit_probability": round(len(group) / len(context_journeys), 4),
            "path_variants": len({item["prefix"] for item in group}),
            "p10_seconds": percentile(values, 0.10),
            "median_seconds": percentile(values, 0.50),
            "p90_seconds": percentile(values, 0.90),
            "observed_min_seconds": min(values),
            "observed_max_seconds": max(values),
            "first_local_date": min(item["journey"]["local_date"] for item in group),
            "last_local_date": max(item["journey"]["local_date"] for item in group),
            "confidence": confidence(len(group)),
        }
        contextual_destination_rows.append(row)
        compact_contextual_destinations[route_id].append({
            "from": start,
            "to": destination,
            "weekdayClass": weekday_class,
            "season": season_name,
            "timeBand": band,
            "sampleSize": len(group),
            "contextJourneys": len(context_journeys),
            "visitProbability": row["visit_probability"],
            "pathVariants": row["path_variants"],
            "typicalMinutes": minute_quantiles(values),
            "possibleMinutes": [round(min(values) / 60), round(max(values) / 60)],
            "observedFrom": row["first_local_date"],
            "observedTo": row["last_local_date"],
        })

    write_csv(args.output / "leg-windows-flexible.csv", leg_rows, "route_id")
    write_csv(args.output / "contextual-leg-windows.csv", contextual_rows, "route_id")
    write_csv(args.output / "path-windows-flexible.csv", path_rows, "route_id")
    write_csv(args.output / "destination-windows-flexible.csv", destination_rows, "route_id")
    write_csv(args.output / "service-pattern-contexts.csv", pattern_rows, "route_id")
    write_csv(
        args.output / "contextual-destination-windows.csv",
        contextual_destination_rows,
        "route_id",
    )

    route_ids = sorted(set(compact_legs) | set(compact_paths) | set(compact_destinations))
    compact = {
        "schemaVersion": 2,
        "status": "draft",
        "modelVersion": "ais-driving-flexible-v2",
        "timezone": args.timezone,
        "policy": {
            "basis": "historical_ais_observations",
            "role": "advisory",
            "scheduledTimesTakePrecedence": True,
            "intermediateWaitsIncluded": False,
            "primaryTimingUnit": "directed_pier_to_pier_leg",
            "calendarContextAffects": "observed_service_pattern_frequency",
            "exactDepartureMatchRequired": False,
            "minimumModelSamples": args.minimum_model_samples,
            "minimumContextSamples": args.minimum_audit_samples,
        },
        "weekdayClasses": ["ma", "ti-to", "pe", "la", "su"],
        "seasons": ["talvi", "kevät-syksy", "kesä"],
        "timeBands": ["aamu", "päivä", "iltapäivä", "ilta-yö"],
        "routes": [
            {
                "id": route_id,
                "name": route_names[route_id],
                "legs": compact_legs[route_id],
                "observedPaths": compact_paths[route_id],
                "destinationFallbacks": compact_destinations[route_id],
                "contextualDestinationFallbacks": compact_contextual_destinations[route_id],
                "servicePatternContexts": compact_patterns[route_id],
            }
            for route_id in route_ids
        ],
    }
    compact_path = args.compact_output or args.output / "arrival-prediction-model.flexible.json"
    compact_path.parent.mkdir(parents=True, exist_ok=True)
    compact_path.write_text(json.dumps(compact, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

    summary = {
        "eligibleHighConfidenceJourneys": len(journeys),
        "routes": len(route_ids),
        "directedLegWindows": len(leg_rows),
        "modelDirectedLegs": sum(len(rows) for rows in compact_legs.values()),
        "contextualLegWindowsForAudit": len(contextual_rows),
        "observedPathWindows": len(path_rows),
        "modelObservedPaths": sum(len(rows) for rows in compact_paths.values()),
        "destinationFallbacks": len(destination_rows),
        "contextualDestinationWindows": len(contextual_destination_rows),
        "servicePatternContexts": sum(len(rows) for rows in compact_patterns.values()),
        "parameters": {
            "minimumAuditSamples": args.minimum_audit_samples,
            "minimumModelSamples": args.minimum_model_samples,
            "minimumContextSamples": args.minimum_audit_samples,
            "exactDepartureMatchRequired": False,
            "intermediateWaitsIncluded": False,
        },
    }
    (args.output / "summary-flexible.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
