#!/usr/bin/env python3
"""Attach unambiguous AIS arrival estimates to structured timetable calls."""

from __future__ import annotations

import argparse
import copy
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("timetables", type=Path)
    parser.add_argument("estimates", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("--overrides", type=Path)
    parser.add_argument("--slot-minutes", type=int, default=15)
    return parser.parse_args()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def minute_value(clock: str) -> int:
    hour, minute = map(int, clock.split(":"))
    return hour * 60 + minute


def rounded_clock(clock: str, slot_minutes: int) -> tuple[int, str]:
    minute = round(minute_value(clock) / slot_minutes) * slot_minutes
    day_offset = minute // (24 * 60)
    minute %= 24 * 60
    return day_offset, f"{minute // 60:02d}:{minute % 60:02d}"


def shifted_clock(clock: str, minutes: int) -> tuple[str, int]:
    origin = datetime(2000, 1, 1, *map(int, clock.split(":")))
    shifted = origin + timedelta(minutes=minutes)
    return shifted.strftime("%H:%M"), (shifted.date() - origin.date()).days


def operating_weekdays(pattern: str | None) -> list[int]:
    if not pattern or len(pattern) != 7:
        return []
    return [index for index, value in enumerate(pattern) if value != "_"]


def start_time(call: dict) -> str | None:
    return call.get("departure") or call.get("time")


def is_subsequence(values: list[str], sequence: list[str]) -> bool:
    iterator = iter(sequence)
    return all(any(candidate == value for candidate in iterator) for value in values)


def weighted_median(values: list[tuple[int, int]]) -> int:
    threshold = sum(weight for _, weight in values) / 2
    cumulative = 0
    for value, weight in sorted(values):
        cumulative += weight
        if cumulative >= threshold:
            return value
    return max(value for value, _ in values)


def main() -> None:
    args = parse_args()
    source = read_json(args.timetables)
    output = copy.deepcopy(source)
    estimates = read_json(args.estimates)
    overrides = read_json(args.overrides) if args.overrides else {}
    route_aliases = overrides.get("routeAliases", {})
    stop_aliases = overrides.get("stopAliases", {})

    estimate_routes = {route["id"]: route for route in estimates["routes"]}
    estimate_index = {}
    for route in estimates["routes"]:
        for departure in route["departures"]:
            key = (
                route["id"],
                departure["from"],
                departure["weekday"],
                departure["time"],
            )
            estimate_index[key] = departure

    outcomes = Counter()
    trip_reports = []
    attached_calls = 0
    for route in output["routes"]:
        source_route_id = route["id"]
        estimate_route_id = route_aliases.get(source_route_id, source_route_id)
        aliases = stop_aliases.get(source_route_id, {})
        route_estimates = estimate_routes.get(estimate_route_id)
        trips = route.get("trips", [])
        if not route_estimates:
            outcomes["route_without_ais_model"] += 1
            continue
        if not trips:
            outcomes["route_without_structured_trips"] += 1
            continue
        for trip in trips:
            calls = trip.get("calls", [])
            first = calls[0] if calls else {}
            departure_time = start_time(first)
            weekdays = operating_weekdays(trip.get("operatingDays"))
            report = {
                "structuredRouteId": source_route_id,
                "aisRouteId": estimate_route_id,
                "tripId": trip.get("id"),
                "from": first.get("stop"),
                "departure": departure_time,
                "weekdays": weekdays,
                "status": None,
                "matchedCalls": 0,
            }
            if not calls or not departure_time or not weekdays:
                report["status"] = "trip_without_matchable_departure"
                outcomes[report["status"]] += 1
                trip_reports.append(report)
                continue
            departure_day_offset, slot_time = rounded_clock(
                departure_time, args.slot_minutes
            )
            if departure_day_offset:
                weekdays = [(weekday + departure_day_offset) % 7 for weekday in weekdays]
            normalized_start = aliases.get(first["stop"], first["stop"])
            matches = []
            for weekday in weekdays:
                key = (estimate_route_id, normalized_start, weekday, slot_time)
                if key in estimate_index:
                    matches.append(estimate_index[key])
            estimate = None
            matching_method = "pooled_route_paths"
            if len(matches) == len(weekdays):
                unique_departures = {
                    json.dumps(match, ensure_ascii=False, sort_keys=True)
                    for match in matches
                }
                if len(unique_departures) == 1:
                    estimate = matches[0]
                    matching_method = "weekday_departure_slot"
            destinations = (
                {item["stop"]: item for item in estimate["destinations"]}
                if estimate
                else {}
            )
            pooled_paths = [
                path
                for path in route_estimates.get("pooledPaths", [])
                if path["from"] == normalized_start
            ]
            normalized_prior_stops = []
            attached_methods = set()
            attached_indices = []
            estimated_elapsed_minutes = {}
            for call_index, call in enumerate(calls[1:], start=1):
                normalized_stop = aliases.get(call["stop"], call["stop"])
                destination = destinations.get(normalized_stop)
                call_matching_method = (
                    "weekday_departure_slot" if destination else "pooled_route_paths"
                )
                if not destination:
                    candidates = [
                        path
                        for path in pooled_paths
                        if path["stop"] == normalized_stop
                        and is_subsequence(path["via"], normalized_prior_stops)
                    ]
                    if candidates:
                        destination = {
                            "sampleSize": sum(path["sampleSize"] for path in candidates),
                            "observedFrom": min(path["observedFrom"] for path in candidates),
                            "observedTo": max(path["observedTo"] for path in candidates),
                            "typicalMinutes": [
                                min(path["minutes"][0] for path in candidates),
                                weighted_median([
                                    (path["minutes"][1], path["sampleSize"])
                                    for path in candidates
                                ]),
                                max(path["minutes"][2] for path in candidates),
                            ],
                            "possibleMinutes": [
                                min(path["minutes"][0] for path in candidates),
                                max(path["minutes"][2] for path in candidates),
                            ],
                        }
                if not destination:
                    normalized_prior_stops.append(normalized_stop)
                    continue
                typical, typical_day = shifted_clock(
                    departure_time, destination["typicalMinutes"][1]
                )
                earliest, earliest_day = shifted_clock(
                    departure_time, destination["possibleMinutes"][0]
                )
                latest, latest_day = shifted_clock(
                    departure_time, destination["possibleMinutes"][1]
                )
                if len({typical_day, earliest_day, latest_day}) != 1:
                    continue
                call["historicalEstimate"] = {
                    "basis": "historical_observations",
                    "typical": typical,
                    "range": {"earliest": earliest, "latest": latest},
                    "dayOffset": typical_day,
                    "sampleSize": destination["sampleSize"],
                    "observedFrom": destination["observedFrom"],
                    "observedTo": destination["observedTo"],
                    "generatedAt": "2026-10-12T00:00:00+03:00",
                    "modelVersion": estimates["modelVersion"],
                    "confidence": min(
                        1 if call_matching_method == "weekday_departure_slot" else 0.75,
                        destination["sampleSize"] / 20,
                    ),
                    "matchingMethod": call_matching_method,
                    "disclosureRequired": True,
                    "disclosureKey": "timetable.historicalEstimateDisclaimer",
                }
                report["matchedCalls"] += 1
                attached_calls += 1
                attached_methods.add(call_matching_method)
                attached_indices.append(call_index)
                estimated_elapsed_minutes[call_index] = destination["typicalMinutes"][1]
                normalized_prior_stops.append(normalized_stop)
            incompatible_with_published_time = False
            for call_index in attached_indices:
                for later_call in calls[call_index + 1:]:
                    later_time = (
                        later_call.get("arrival")
                        or later_call.get("time")
                        or later_call.get("departure")
                    )
                    if not later_time:
                        continue
                    published_elapsed = (
                        minute_value(later_time) - minute_value(departure_time)
                    ) % (24 * 60)
                    if estimated_elapsed_minutes[call_index] > published_elapsed:
                        incompatible_with_published_time = True
                    break
            if incompatible_with_published_time:
                for call_index in attached_indices:
                    calls[call_index].pop("historicalEstimate", None)
                attached_calls -= report["matchedCalls"]
                report["matchedCalls"] = 0
                report["status"] = "pooled_model_incompatible_with_published_trip"
                report["roundedDeparture"] = slot_time
                report["matchedWeekdays"] = sorted({m["weekday"] for m in matches})
                outcomes[report["status"]] += 1
                trip_reports.append(report)
                continue
            if not report["matchedCalls"]:
                report["status"] = "no_compatible_path_estimates"
            elif len(attached_methods) == 1:
                report["status"] = f"attached_{next(iter(attached_methods))}"
            else:
                report["status"] = "attached_mixed_methods"
            report["roundedDeparture"] = slot_time
            report["matchedWeekdays"] = sorted({m["weekday"] for m in matches})
            outcomes[report["status"]] += 1
            trip_reports.append(report)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    report = {
        "modelVersion": estimates["modelVersion"],
        "attachedCalls": attached_calls,
        "outcomes": dict(sorted(outcomes.items())),
        "trips": trip_reports,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
