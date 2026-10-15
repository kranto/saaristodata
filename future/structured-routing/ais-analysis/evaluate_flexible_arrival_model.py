#!/usr/bin/env python3
"""Backtest schedule-independent AIS arrival estimates on a later time period."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


WEEKDAY_CLASSES = {
    0: "ma", 1: "ti-to", 2: "ti-to", 3: "ti-to", 4: "pe", 5: "la", 6: "su"
}


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("journeys", type=Path)
    parser.add_argument("journey_stops", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--timezone", default="Europe/Helsinki")
    parser.add_argument("--test-days", type=int, default=90)
    parser.add_argument("--minimum-samples", type=int, default=5)
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


def prediction(values: list[int]) -> tuple[int, int, int]:
    return (
        percentile(values, 0.10),
        percentile(values, 0.50),
        percentile(values, 0.90),
    )


def write_csv(path: Path, rows: list[dict], default_field: str) -> None:
    fields = list(rows[0]) if rows else [default_field]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def metric_row(group: list[dict], route_id: str, method: str) -> dict:
    errors = [row["actual_seconds"] - row["median_seconds"] for row in group]
    absolute_errors = [abs(value) for value in errors]
    widths = [row["p90_seconds"] - row["p10_seconds"] for row in group]
    return {
        "route_id": route_id,
        "method": method,
        "predictions": len(group),
        "range_coverage_percent": round(
            100
            * sum(
                row["p10_seconds"] <= row["actual_seconds"] <= row["p90_seconds"]
                for row in group
            )
            / len(group),
            2,
        ),
        "median_absolute_error_minutes": round(percentile(absolute_errors, 0.50) / 60, 1),
        "p90_absolute_error_minutes": round(percentile(absolute_errors, 0.90) / 60, 1),
        "median_signed_error_minutes": round(percentile(errors, 0.50) / 60, 1),
        "median_range_width_minutes": round(percentile(widths, 0.50) / 60, 1),
        "within_10_minutes_percent": round(
            100 * sum(value <= 10 * 60 for value in absolute_errors) / len(group), 2
        ),
        "within_20_minutes_percent": round(
            100 * sum(value <= 20 * 60 for value in absolute_errors) / len(group), 2
        ),
    }


def main() -> None:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    timezone = ZoneInfo(args.timezone)

    journeys: dict[str, dict] = {}
    latest_departure: datetime | None = None
    for row in read_csv(args.journeys):
        if row["timing_confidence"] != "high":
            continue
        departure = datetime.fromisoformat(row["departure_utc"].replace("Z", "+00:00"))
        local = departure.astimezone(timezone)
        journeys[row["journey_id"]] = {**row, "departure": departure, "local": local}
        latest_departure = max(latest_departure, departure) if latest_departure else departure
    if latest_departure is None:
        raise SystemExit("No eligible journeys")
    cutoff = latest_departure - timedelta(days=args.test_days)

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

    leg_groups: dict[tuple, list[int]] = defaultdict(list)
    path_groups: dict[tuple, list[int]] = defaultdict(list)
    contextual_destination_groups: dict[tuple, list[int]] = defaultdict(list)
    train_journeys = test_journeys = 0
    for journey_id, journey in journeys.items():
        rows = stops_by_journey.get(journey_id, [])
        if not rows:
            continue
        if journey["departure"] >= cutoff:
            test_journeys += 1
            continue
        train_journeys += 1
        previous = journey["start_pier"]
        previous_elapsed = 0
        seen = {previous}
        for row in rows:
            destination = row["destination_pier"]
            leg_seconds = row["driving_elapsed_seconds"] - previous_elapsed
            if leg_seconds > 0:
                leg_groups[(journey["route_id"], previous, destination)].append(leg_seconds)
            if destination not in seen:
                seen.add(destination)
                path_groups[(
                    journey["route_id"],
                    journey["start_pier"],
                    destination,
                    row["prefix"],
                )].append(row["driving_elapsed_seconds"])
                contextual_destination_groups[(
                    journey["route_id"],
                    journey["start_pier"],
                    destination,
                    WEEKDAY_CLASSES[journey["local"].weekday()],
                    season(journey["local"].month),
                    time_band(journey["local"].hour),
                )].append(row["driving_elapsed_seconds"])
            previous = destination
            previous_elapsed = row["driving_elapsed_seconds"]

    reliable_paths = {
        key: values
        for key, values in path_groups.items()
        if len(values) >= args.minimum_samples
    }
    destination_paths: dict[tuple, list[list[int]]] = defaultdict(list)
    all_destination_paths: dict[tuple, list[list[int]]] = defaultdict(list)
    for (route_id, start, destination, _prefix), values in path_groups.items():
        all_destination_paths[(route_id, start, destination)].append(values)
    for (route_id, start, destination, _prefix), values in reliable_paths.items():
        destination_paths[(route_id, start, destination)].append(values)

    predictions = []
    eligible_test_destinations = 0
    for journey_id, journey in journeys.items():
        if journey["departure"] < cutoff:
            continue
        rows = stops_by_journey.get(journey_id, [])
        previous = journey["start_pier"]
        seen = {previous}
        for row in rows:
            destination = row["destination_pier"]
            if destination in seen:
                previous = destination
                continue
            seen.add(destination)
            eligible_test_destinations += 1
            prefix = row["prefix"]
            path_key = (
                journey["route_id"],
                journey["start_pier"],
                destination,
                prefix,
            )
            methods: dict[str, tuple[int, int, int, int]] = {}
            exact_values = reliable_paths.get(path_key)
            if exact_values:
                methods["observed_path"] = (*prediction(exact_values), len(exact_values))

            names = prefix.split(">")
            leg_values = [
                leg_groups.get((journey["route_id"], origin, target), [])
                for origin, target in zip(names, names[1:])
            ]
            if leg_values and all(len(values) >= args.minimum_samples for values in leg_values):
                leg_predictions = [prediction(values) for values in leg_values]
                methods["summed_legs"] = (
                    sum(item[0] for item in leg_predictions),
                    sum(item[1] for item in leg_predictions),
                    sum(item[2] for item in leg_predictions),
                    min(len(values) for values in leg_values),
                )

            fallback_paths = destination_paths.get(
                (journey["route_id"], journey["start_pier"], destination), []
            )
            if fallback_paths:
                all_paths = all_destination_paths[
                    (journey["route_id"], journey["start_pier"], destination)
                ]
                pooled = [value for values in fallback_paths for value in values]
                methods["destination_fallback"] = (
                    min(value for values in all_paths for value in values),
                    percentile(pooled, 0.50),
                    max(value for values in all_paths for value in values),
                    len(pooled),
                )

            context_values = contextual_destination_groups.get((
                journey["route_id"],
                journey["start_pier"],
                destination,
                WEEKDAY_CLASSES[journey["local"].weekday()],
                season(journey["local"].month),
                time_band(journey["local"].hour),
            ), [])
            if len(context_values) >= 3:
                methods["context_fallback"] = (
                    min(context_values),
                    percentile(context_values, 0.50),
                    max(context_values),
                    len(context_values),
                )

            selected = next(
                (method for method in ("observed_path", "summed_legs", "context_fallback", "destination_fallback") if method in methods),
                None,
            )
            for method, (p10, median, p90, sample_size) in methods.items():
                predictions.append({
                    "journey_id": journey_id,
                    "departure_local": journey["local"].isoformat(),
                    "route_id": journey["route_id"],
                    "start_pier": journey["start_pier"],
                    "destination_pier": destination,
                    "prefix": prefix,
                    "method": method,
                    "selected": "1" if method == selected else "0",
                    "sample_size": sample_size,
                    "actual_seconds": row["driving_elapsed_seconds"],
                    "p10_seconds": p10,
                    "median_seconds": median,
                    "p90_seconds": p90,
                    "absolute_error_seconds": abs(row["driving_elapsed_seconds"] - median),
                    "inside_p10_p90": "1" if p10 <= row["driving_elapsed_seconds"] <= p90 else "0",
                })
            previous = destination

    metric_rows = []
    selected_predictions = [row for row in predictions if row["selected"] == "1"]
    for method in ("observed_path", "summed_legs", "context_fallback", "destination_fallback"):
        group = [row for row in predictions if row["method"] == method]
        if group:
            metric_rows.append(metric_row(group, "ALL", method))
    if selected_predictions:
        metric_rows.append(metric_row(selected_predictions, "ALL", "selected_hierarchy"))
    routes = sorted({row["route_id"] for row in selected_predictions})
    for route_id in routes:
        group = [row for row in selected_predictions if row["route_id"] == route_id]
        metric_rows.append(metric_row(group, route_id, "selected_hierarchy"))

    write_csv(args.output / "backtest-predictions.csv", predictions, "journey_id")
    write_csv(args.output / "backtest-metrics.csv", metric_rows, "route_id")
    summary = {
        "trainingJourneys": train_journeys,
        "testJourneys": test_journeys,
        "testDays": args.test_days,
        "trainingBeforeUtc": cutoff.isoformat().replace("+00:00", "Z"),
        "eligibleTestDestinations": eligible_test_destinations,
        "selectedPredictions": len(selected_predictions),
        "coveragePercent": round(
            100 * len(selected_predictions) / eligible_test_destinations, 2
        ) if eligible_test_destinations else 0,
        "selectedMethods": {
            method: sum(row["method"] == method for row in selected_predictions)
            for method in ("observed_path", "summed_legs", "context_fallback", "destination_fallback")
        },
        "metrics": next(
            (row for row in metric_rows if row["route_id"] == "ALL" and row["method"] == "selected_hierarchy"),
            None,
        ),
        "parameters": {"minimumSamples": args.minimum_samples},
    }
    (args.output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
