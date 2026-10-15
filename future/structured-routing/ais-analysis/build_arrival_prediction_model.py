#!/usr/bin/env python3
"""Build departure-slot and stop-sequence based connection-vessel arrival predictions."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("journeys", type=Path)
    parser.add_argument("journey_stops", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--timezone", default="Europe/Helsinki")
    parser.add_argument("--slot-minutes", type=int, default=15)
    parser.add_argument("--minimum-slot-journeys", type=int, default=3)
    parser.add_argument("--minimum-variant-observations", type=int, default=3)
    parser.add_argument("--minimum-prediction-variant-observations", type=int, default=5)
    parser.add_argument(
        "--compact-output",
        type=Path,
        help="Optional application-facing compact JSON output path",
    )
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


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def rounded_slot(local_departure: datetime, slot_minutes: int) -> tuple[int, int]:
    minute = local_departure.hour * 60 + local_departure.minute
    slot = round(minute / slot_minutes) * slot_minutes
    weekday = local_departure.weekday()
    if slot >= 24 * 60:
        slot -= 24 * 60
        weekday = (weekday + 1) % 7
    return weekday, slot


def format_minute(minute: int) -> str:
    return f"{minute // 60:02d}:{minute % 60:02d}"


def confidence(observations: int) -> str:
    if observations >= 20:
        return "strong"
    if observations >= 5:
        return "usable"
    return "limited"


def rounded_minutes(seconds: int | None) -> int | None:
    if seconds is None:
        return None
    return round(seconds / 60)


def main() -> None:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    timezone = ZoneInfo(args.timezone)

    journeys = {}
    eligible_journeys = []
    for row in read_csv(args.journeys):
        journeys[row["journey_id"]] = row
        if row["timing_confidence"] != "high":
            continue
        departure = datetime.fromisoformat(row["departure_utc"].replace("Z", "+00:00"))
        local_departure = departure.astimezone(timezone)
        weekday, slot_minute = rounded_slot(local_departure, args.slot_minutes)
        row = {
            **row,
            "local_departure": local_departure,
            "local_date": local_departure.date().isoformat(),
            "weekday": weekday,
            "slot_minute": slot_minute,
            "slot_key": (row["route_id"], row["start_pier"], weekday, slot_minute),
        }
        eligible_journeys.append(row)
        journeys[row["journey_id"]] = row

    stops_by_journey: dict[str, list[dict]] = defaultdict(list)
    for row in read_csv(args.journey_stops):
        journey = journeys.get(row["journey_id"])
        if not journey or "slot_key" not in journey or row["timing_confidence"] != "high":
            continue
        row["elapsed_seconds"] = int(row["elapsed_seconds"])
        row["driving_elapsed_seconds"] = int(row["driving_elapsed_seconds"])
        row["intermediate_wait_seconds"] = int(row["intermediate_wait_seconds"])
        stops_by_journey[row["journey_id"]].append(row)

    slot_groups: dict[tuple, list[dict]] = defaultdict(list)
    for journey in eligible_journeys:
        slot_groups[journey["slot_key"]].append(journey)

    pooled_path_groups: dict[tuple, list[dict]] = defaultdict(list)
    for journey in eligible_journeys:
        seen_destinations = {journey["start_pier"]}
        for stop in stops_by_journey.get(journey["journey_id"], []):
            if stop["destination_pier"] in seen_destinations:
                continue
            seen_destinations.add(stop["destination_pier"])
            pooled_path_groups[(
                journey["route_id"],
                journey["start_pier"],
                stop["destination_pier"],
                stop["prefix"],
            )].append({**stop, "journey": journey})

    pooled_paths_by_route: dict[str, list[dict]] = defaultdict(list)
    for (route_id, start_pier, destination_pier, prefix), group in sorted(
        pooled_path_groups.items()
    ):
        if len(group) < args.minimum_prediction_variant_observations:
            continue
        values = [row["driving_elapsed_seconds"] for row in group]
        pooled_paths_by_route[route_id].append({
            "from": start_pier,
            "stop": destination_pier,
            "via": prefix.split(">")[1:-1],
            "sampleSize": len(group),
            "seconds": [
                percentile(values, 0.10),
                percentile(values, 0.50),
                percentile(values, 0.90),
            ],
            "observedFrom": min(row["journey"]["local_date"] for row in group),
            "observedTo": max(row["journey"]["local_date"] for row in group),
            "vesselCount": len({row["journey"]["mmsi"] for row in group}),
        })

    slot_rows = []
    variant_rows = []
    destination_rows = []
    model_routes: dict[str, dict] = defaultdict(lambda: {"starts": defaultdict(list)})
    covered_journey_ids = set()

    for (route_id, start_pier, weekday, slot_minute), group in sorted(slot_groups.items()):
        if len(group) < args.minimum_slot_journeys:
            continue
        covered_journey_ids.update(row["journey_id"] for row in group)
        slot_id = f"{route_id}:{start_pier}:{weekday}:{slot_minute}"
        complete_group = [row for row in group if row["complete"] == "1"]
        sequence_counts = Counter(row["sequence"] for row in group)
        complete_sequence_counts = Counter(row["sequence"] for row in complete_group)
        actual_minutes = [
            row["local_departure"].hour * 60 + row["local_departure"].minute
            for row in group
        ]
        slot_row = {
            "slot_id": slot_id,
            "route_id": route_id,
            "route_name": group[0]["route_name"],
            "start_pier": start_pier,
            "weekday": weekday,
            "departure_time": format_minute(slot_minute),
            "journeys": len(group),
            "complete_journeys": len(complete_group),
            "first_local_date": min(row["local_date"] for row in group),
            "last_local_date": max(row["local_date"] for row in group),
            "departure_p10_minute": percentile(actual_minutes, 0.10),
            "departure_median_minute": percentile(actual_minutes, 0.50),
            "departure_p90_minute": percentile(actual_minutes, 0.90),
            "sequences": len(sequence_counts),
            "confidence": confidence(len(group)),
        }
        slot_rows.append(slot_row)

        observations_by_destination: dict[str, list[dict]] = defaultdict(list)
        for journey in group:
            seen_destinations = {start_pier}
            for stop in stops_by_journey.get(journey["journey_id"], []):
                if stop["destination_pier"] in seen_destinations:
                    continue
                seen_destinations.add(stop["destination_pier"])
                observations_by_destination[stop["destination_pier"]].append({
                    **stop,
                    "journey": journey,
                })

        destination_payload = []
        for destination_pier, observations in sorted(observations_by_destination.items()):
            destination_journeys = {row["journey_id"] for row in observations}
            driving_elapsed = [row["driving_elapsed_seconds"] for row in observations]
            waits_removed = [row["intermediate_wait_seconds"] for row in observations]
            by_prefix: dict[str, list[dict]] = defaultdict(list)
            for observation in observations:
                by_prefix[observation["prefix"]].append(observation)
            variants = []
            retained_observations = []
            retained_variant_observations = 0
            for prefix, variant_group in sorted(
                by_prefix.items(), key=lambda item: (-len(item[1]), item[0])
            ):
                if len(variant_group) < args.minimum_variant_observations:
                    continue
                retained_variant_observations += len(variant_group)
                if len(variant_group) >= args.minimum_prediction_variant_observations:
                    retained_observations.extend(variant_group)
                values = [row["driving_elapsed_seconds"] for row in variant_group]
                variant_waits = [row["intermediate_wait_seconds"] for row in variant_group]
                variant = {
                    "prefix": prefix,
                    "observations": len(variant_group),
                    "share_of_destination_visits": round(
                        len(variant_group) / len(observations), 4
                    ),
                    "driving_p10_seconds": percentile(values, 0.10),
                    "driving_median_seconds": percentile(values, 0.50),
                    "driving_p90_seconds": percentile(values, 0.90),
                    "removed_wait_median_seconds": percentile(variant_waits, 0.50),
                    "first_local_date": min(
                        row["journey"]["local_date"] for row in variant_group
                    ),
                    "last_local_date": max(
                        row["journey"]["local_date"] for row in variant_group
                    ),
                    "observed_months": sorted({
                        row["journey"]["local_departure"].month
                        for row in variant_group
                    }),
                    "vessels": len({row["journey"]["mmsi"] for row in variant_group}),
                    "confidence": confidence(len(variant_group)),
                }
                variants.append(variant)
                variant_rows.append({
                    "slot_id": slot_id,
                    "route_id": route_id,
                    "start_pier": start_pier,
                    "weekday": weekday,
                    "departure_time": format_minute(slot_minute),
                    "destination_pier": destination_pier,
                    **variant,
                })
            prediction_variants = [
                variant
                for variant in variants
                if variant["observations"] >= args.minimum_prediction_variant_observations
            ]
            retained_driving = [
                row["driving_elapsed_seconds"] for row in retained_observations
            ]
            possible_p10 = min(
                (variant["driving_p10_seconds"] for variant in prediction_variants),
                default=None,
            )
            possible_p90 = max(
                (variant["driving_p90_seconds"] for variant in prediction_variants),
                default=None,
            )
            widest_variant_seconds = max(
                (
                    variant["driving_p90_seconds"]
                    - variant["driving_p10_seconds"]
                    for variant in prediction_variants
                ),
                default=None,
            )
            possible_width_seconds = (
                possible_p90 - possible_p10
                if possible_p10 is not None and possible_p90 is not None
                else None
            )
            if not prediction_variants:
                prediction_status = "insufficient_repetition"
            elif possible_width_seconds <= 30 * 60:
                prediction_status = "compact"
            elif len(prediction_variants) >= 2 and widest_variant_seconds <= 20 * 60:
                prediction_status = "wide_route_alternatives"
            else:
                prediction_status = "wide_within_variant"
            destination = {
                "pier": destination_pier,
                "journeys_visiting": len(destination_journeys),
                "visit_probability": (
                    round(
                        len({
                            row["journey_id"]
                            for row in observations
                            if row["journey"]["complete"] == "1"
                        }) / len(complete_group),
                        4,
                    )
                    if complete_group
                    else None
                ),
                "visit_probability_basis": "complete_journeys" if complete_group else None,
                "observations": len(observations),
                "reliable_observations": len(retained_observations),
                "reliable_observation_share": round(
                    len(retained_observations) / len(observations), 4
                ),
                "reliable_variants": len(prediction_variants),
                "limited_variants": len(variants) - len(prediction_variants),
                "prediction_status": prediction_status,
                "driving_typical_p10_seconds": percentile(retained_driving, 0.10),
                "driving_typical_median_seconds": percentile(retained_driving, 0.50),
                "driving_typical_p90_seconds": percentile(retained_driving, 0.90),
                "driving_possible_p10_seconds": possible_p10,
                "driving_possible_p90_seconds": possible_p90,
                "widest_variant_p10_p90_seconds": widest_variant_seconds,
                "driving_any_path_p10_seconds": percentile(driving_elapsed, 0.10),
                "driving_any_path_median_seconds": percentile(driving_elapsed, 0.50),
                "driving_any_path_p90_seconds": percentile(driving_elapsed, 0.90),
                "removed_wait_median_seconds": percentile(waits_removed, 0.50),
                "first_local_date": min(
                    row["journey"]["local_date"] for row in observations
                ),
                "last_local_date": max(
                    row["journey"]["local_date"] for row in observations
                ),
                "retained_variant_observations": retained_variant_observations,
                "other_variant_observations": len(observations) - retained_variant_observations,
                "variants": variants,
            }
            destination_payload.append(destination)
            destination_rows.append({
                "slot_id": slot_id,
                "route_id": route_id,
                "start_pier": start_pier,
                "weekday": weekday,
                "departure_time": format_minute(slot_minute),
                "destination_pier": destination_pier,
                **{key: value for key, value in destination.items() if key not in {"pier", "variants"}},
            })

        slot_payload = {
            "id": slot_id,
            "weekday": weekday,
            "departure_time": format_minute(slot_minute),
            "journeys": len(group),
            "complete_journeys": len(complete_group),
            "first_local_date": slot_row["first_local_date"],
            "last_local_date": slot_row["last_local_date"],
            "confidence": slot_row["confidence"],
            "sequences": [
                {
                    "sequence": sequence,
                    "journeys": count,
                    "observed_share": round(count / len(group), 4),
                    "complete_journeys": complete_sequence_counts.get(sequence, 0),
                    "complete_journey_share": (
                        round(complete_sequence_counts.get(sequence, 0) / len(complete_group), 4)
                        if complete_group
                        else None
                    ),
                }
                for sequence, count in sequence_counts.most_common()
            ],
            "destinations": destination_payload,
        }
        route_entry = model_routes[route_id]
        route_entry["name"] = group[0]["route_name"]
        route_entry["starts"][start_pier].append(slot_payload)

    model = {
        "timezone": args.timezone,
        "slot_minutes": args.slot_minutes,
        "weekday": ["maanantai", "tiistai", "keskiviikko", "torstai", "perjantai", "lauantai", "sunnuntai"],
        "routes": {
            route_id: {
                "name": entry["name"],
                "starts": dict(entry["starts"]),
            }
            for route_id, entry in sorted(model_routes.items())
        },
    }
    (args.output / "arrival-prediction-model.json").write_text(
        json.dumps(model, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    compact_routes = []
    for route_id, route in model["routes"].items():
        departures = []
        for start_pier, slots in route["starts"].items():
            for slot in slots:
                destinations = []
                for destination in slot["destinations"]:
                    reliable_variants = [
                        variant
                        for variant in destination["variants"]
                        if variant["observations"]
                        >= args.minimum_prediction_variant_observations
                    ]
                    if not reliable_variants:
                        continue
                    destinations.append({
                        "stop": destination["pier"],
                        "sampleSize": destination["reliable_observations"],
                        "observedFrom": min(
                            variant["first_local_date"] for variant in reliable_variants
                        ),
                        "observedTo": max(
                            variant["last_local_date"] for variant in reliable_variants
                        ),
                        "status": destination["prediction_status"],
                        "typicalMinutes": [
                            rounded_minutes(destination["driving_typical_p10_seconds"]),
                            rounded_minutes(destination["driving_typical_median_seconds"]),
                            rounded_minutes(destination["driving_typical_p90_seconds"]),
                        ],
                        "possibleMinutes": [
                            rounded_minutes(destination["driving_possible_p10_seconds"]),
                            rounded_minutes(destination["driving_possible_p90_seconds"]),
                        ],
                        "variants": [
                            {
                                "via": variant["prefix"].split(">")[1:-1],
                                "sampleSize": variant["observations"],
                                "minutes": [
                                    rounded_minutes(variant["driving_p10_seconds"]),
                                    rounded_minutes(variant["driving_median_seconds"]),
                                    rounded_minutes(variant["driving_p90_seconds"]),
                                ],
                                "observedFrom": variant["first_local_date"],
                                "observedTo": variant["last_local_date"],
                            }
                            for variant in reliable_variants
                        ],
                    })
                if destinations:
                    departures.append({
                        "from": start_pier,
                        "weekday": slot["weekday"],
                        "time": slot["departure_time"],
                        "sampleSize": slot["journeys"],
                        "observedFrom": slot["first_local_date"],
                        "observedTo": slot["last_local_date"],
                        "destinations": destinations,
                    })
        if departures:
            compact_routes.append({
                "id": route_id,
                "name": route["name"],
                "departures": departures,
                "pooledPaths": [
                    {
                        **{key: value for key, value in path.items() if key != "seconds"},
                        "minutes": [rounded_minutes(value) for value in path["seconds"]],
                    }
                    for path in pooled_paths_by_route.get(route_id, [])
                ],
            })
    compact_model = {
        "$schema": "ais-arrival-estimates.schema.json",
        "schemaVersion": 1,
        "status": "draft",
        "modelVersion": "ais-driving-v1",
        "timezone": args.timezone,
        "weekday": model["weekday"],
        "policy": {
            "basis": "historical_ais_observations",
            "role": "advisory",
            "scheduledTimesTakePrecedence": True,
            "intermediateWaitsIncluded": False,
            "minimumDepartureSamples": args.minimum_slot_journeys,
            "minimumVariantSamples": args.minimum_prediction_variant_observations,
        },
        "routes": compact_routes,
    }
    compact_path = args.compact_output or (
        args.output / "arrival-prediction-model.compact.json"
    )
    compact_path.parent.mkdir(parents=True, exist_ok=True)
    compact_path.write_text(
        json.dumps(compact_model, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    write_csv(args.output / "departure-slots.csv", slot_rows, list(slot_rows[0]) if slot_rows else ["slot_id"])
    write_csv(
        args.output / "destination-windows.csv",
        destination_rows,
        list(destination_rows[0]) if destination_rows else ["slot_id"],
    )
    write_csv(
        args.output / "sequence-variant-windows.csv",
        variant_rows,
        list(variant_rows[0]) if variant_rows else ["slot_id"],
    )
    wide_destination_rows = [
        row
        for row in destination_rows
        if row["prediction_status"] in {
            "wide_route_alternatives",
            "wide_within_variant",
        }
    ]
    wide_destination_rows.sort(
        key=lambda row: (
            -(
                row["driving_possible_p90_seconds"]
                - row["driving_possible_p10_seconds"]
            ),
            row["route_id"],
            row["slot_id"],
            row["destination_pier"],
        )
    )
    write_csv(
        args.output / "wide-destination-windows.csv",
        wide_destination_rows,
        list(destination_rows[0]) if destination_rows else ["slot_id"],
    )

    summary = {
        "eligible_high_confidence_journeys": len(eligible_journeys),
        "eligible_high_confidence_complete_journeys": sum(
            row["complete"] == "1" for row in eligible_journeys
        ),
        "journeys_in_retained_departure_slots": len(covered_journey_ids),
        "journey_coverage_percent": round(
            100 * len(covered_journey_ids) / len(eligible_journeys), 2
        ) if eligible_journeys else 0,
        "departure_slots": len(slot_rows),
        "destination_windows": len(destination_rows),
        "sequence_variant_windows": len(variant_rows),
        "wide_route_alternative_windows": sum(
            row["prediction_status"] == "wide_route_alternatives"
            for row in destination_rows
        ),
        "wide_within_variant_windows": sum(
            row["prediction_status"] == "wide_within_variant"
            for row in destination_rows
        ),
        "insufficient_repetition_windows": sum(
            row["prediction_status"] == "insufficient_repetition"
            for row in destination_rows
        ),
        "routes": len(model_routes),
        "compact_routes": len(compact_routes),
        "compact_departures": sum(
            len(route["departures"]) for route in compact_routes
        ),
        "compact_destinations": sum(
            len(departure["destinations"])
            for route in compact_routes
            for departure in route["departures"]
        ),
        "compact_pooled_paths": sum(
            len(route["pooledPaths"]) for route in compact_routes
        ),
        "parameters": {
            "timezone": args.timezone,
            "slot_minutes": args.slot_minutes,
            "minimum_slot_journeys": args.minimum_slot_journeys,
            "minimum_variant_observations": args.minimum_variant_observations,
            "minimum_prediction_variant_observations": (
                args.minimum_prediction_variant_observations
            ),
            "time_measure": "sum_of_pier_to_pier_driving_times",
            "intermediate_waits_included": False,
            "destination_occurrence": "first_visit_after_departure",
        },
    }
    (args.output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
