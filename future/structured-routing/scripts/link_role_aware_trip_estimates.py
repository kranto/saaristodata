#!/usr/bin/env python3
"""Attach AIS-derived timing windows to untimed connection-vessel calls.

The input timetable stays untouched.  Exact historical path variants are used
only when their visited-stop prefix fits the ordered optional calls in the
published trip.  Broad route-level fallback medians are deliberately excluded.
"""

from __future__ import annotations

import argparse
import copy
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path


ROUTE_ALIASES = {"hitisalva": "hitisrutt", "hitisjurmo": "hitisrutt"}
STOP_ALIASES = {
    "hitisalva": {"Stora Ängesö": "Ängesö", "Vänoxa släten": "Vänoxasläten"},
    "hitisjurmo": {
        "Stora Ängesö": "Ängesö",
        "Vänöxaby": "Vänoxaby",
        "Vänöxa, Släten": "Vänoxasläten",
    },
    "houtskarrutt": {"Seili": "Själö", "Sövdö": "Södö"},
    "korporutt": {"Korppoo": "Verkan"},
    "nagunorra": {"TorsholmaI": "Torsholma"},
    "nagusodra": {"Pensar": "PensarL"},
    "pargasrutt": {"Pensar": "PensarI"},
}
FLEXIBLE_PATH_ROUTES = {"pargasrutt", "utorutt"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("timetables", type=Path)
    parser.add_argument("role_estimates", type=Path)
    parser.add_argument("flexible_estimates", type=Path)
    parser.add_argument("anchor_estimates", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("report", type=Path)
    return parser.parse_args()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def clock(call: dict) -> str | None:
    return call.get("departure") or call.get("time") or call.get("arrival")


def minute_value(value: str) -> int:
    hour, minute = map(int, value.split(":"))
    return hour * 60 + minute


def elapsed_to_clock(origin: str, elapsed: float) -> tuple[str, int]:
    start = datetime(2000, 1, 1, *map(int, origin.split(":")))
    result = start + timedelta(minutes=round(elapsed))
    return result.strftime("%H:%M"), (result.date() - start.date()).days


def is_subsequence(values: list[str], sequence: list[str]) -> bool:
    position = 0
    for value in values:
        try:
            position = sequence.index(value, position) + 1
        except ValueError:
            return False
    return True


def is_target_aligned_subsequence(values: list[str], sequence: list[str]) -> bool:
    """Require the historical target to map to this call, not an earlier repeat."""
    position = 0
    matched_index = -1
    for value in values:
        try:
            matched_index = sequence.index(value, position)
        except ValueError:
            return False
        position = matched_index + 1
    return matched_index == len(sequence) - 1


def weighted_median(items: list[tuple[float, int]]) -> float:
    threshold = sum(weight for _, weight in items) / 2
    cumulative = 0
    for value, weight in sorted(items):
        cumulative += weight
        if cumulative >= threshold:
            return value
    return max(value for value, _ in items)


def normalized_stop(route_id: str, stop: str) -> str:
    return STOP_ALIASES.get(route_id, {}).get(stop, stop)


def trip_shape(stops: list[str]) -> str:
    if stops[0] != stops[-1]:
        return "terminal_to_terminal"
    internal = stops[1:-1]
    if len(internal) == 1:
        return "simple_turnaround"
    if len(set(internal)) < len(internal):
        return "closed_with_repeated_pier"
    return "closed_with_single_calls"


def call_role(stops: list[str], index: int) -> str:
    if index == len(stops) - 1:
        return "journey_endpoint"
    target = stops[index]
    occurrences = [i for i, stop in enumerate(stops) if stop == target]
    if len(occurrences) > 1:
        return "outbound" if index == occurrences[0] else "inbound"
    if stops[0] != stops[-1]:
        return "terminal_to_terminal"
    if len(stops) == 3:
        return "turnaround"
    return "single_loop_call"


def compatible_roles(stops: list[str], index: int) -> set[str]:
    """Return roles possible after optional timetable calls are skipped."""
    role = call_role(stops, index)
    if role in {"journey_endpoint", "outbound", "inbound", "terminal_to_terminal"}:
        return {role}
    # A unique call on a closed published trip can be the turnaround when all
    # later optional calls are skipped, or a single call on a longer loop.
    return {"single_loop_call", "turnaround"}


def next_published_elapsed(calls: list[dict], index: int, start: str) -> int | None:
    start_minutes = minute_value(start)
    for call in calls[index + 1:]:
        value = clock(call)
        if value:
            return (minute_value(value) - start_minutes) % (24 * 60)
    return None


def aggregate(candidates: list[dict], cap: int | None) -> dict | None:
    if cap is not None:
        candidates = [item for item in candidates if item["typicalMinutes"][1] <= cap]
    if not candidates:
        return None
    sample_size = sum(item["sampleSize"] for item in candidates)
    typical = [
        min(item["typicalMinutes"][0] for item in candidates),
        weighted_median([(item["typicalMinutes"][1], item["sampleSize"]) for item in candidates]),
        max(item["typicalMinutes"][2] for item in candidates),
    ]
    possible = [
        min(item["observedMinutes"][0] for item in candidates),
        max(item["observedMinutes"][1] for item in candidates),
    ]
    if cap is not None:
        typical[2] = min(typical[2], cap)
        possible[1] = min(possible[1], cap)
    if possible[0] > possible[1] or typical[0] > typical[2]:
        return None
    return {
        "sampleSize": sample_size,
        "pathVariants": len(candidates),
        "typicalMinutes": [round(value, 1) for value in typical],
        "possibleMinutes": [round(value, 1) for value in possible],
        "constrainedByNextPublishedCall": cap is not None,
    }


def flexible_candidates(
    route: dict,
    start: str,
    target: str,
    schedule_prefix: list[str],
    required_prefix: list[str],
) -> list[dict]:
    result = []
    for path in route.get("observedPaths", []):
        historical_prefix = [path["from"], *path.get("via", []), path["to"]]
        if path["from"] != start or path["to"] != target:
            continue
        if not is_target_aligned_subsequence(historical_prefix, schedule_prefix):
            continue
        if not is_subsequence(required_prefix, historical_prefix):
            continue
        result.append({
            "sampleSize": path["sampleSize"],
            "typicalMinutes": path["minutes"],
            "observedMinutes": [path["minutes"][0], path["minutes"][2]],
        })
    return result


def conservative_range(
    route_id: str,
    role_route: dict | None,
    flexible_route: dict | None,
    anchor_route: dict | None,
    start: str,
    end: str,
    target: str,
    allowed_roles: set[str],
    cap: int | None,
    require_journey_end: bool,
) -> dict | None:
    candidates = []
    if route_id in FLEXIBLE_PATH_ROUTES and flexible_route:
        for item in flexible_route.get("destinationFallbacks", []):
            if item["from"] == start and item["to"] == target:
                candidates.append({
                    "sampleSize": item["sampleSize"],
                    "possibleMinutes": item["possibleMinutes"],
                })
    if anchor_route:
        for item in anchor_route.get("destinationFallbacks", []):
            if item["from"] == start and item["to"] == target:
                candidates.append(item)
    if role_route:
        for item in role_route.get("fallbackWindows", []):
            if item["from"] != start or item["to"] != target:
                continue
            if require_journey_end and item["journeyEnd"] != end:
                continue
            if item["role"] not in allowed_roles:
                continue
            candidates.append(item)
    if not candidates:
        return None
    lower = min(item["possibleMinutes"][0] for item in candidates)
    upper = max(item["possibleMinutes"][1] for item in candidates)
    if cap is not None:
        upper = min(upper, cap)
    if lower > upper:
        return None
    return {
        "sampleSize": sum(item["sampleSize"] for item in candidates),
        "roleVariants": len(candidates),
        "possibleMinutes": [round(lower, 1), round(upper, 1)],
        "constrainedByNextPublishedCall": cap is not None,
    }


def main() -> None:
    args = parse_args()
    output = copy.deepcopy(read_json(args.timetables))
    role_data = read_json(args.role_estimates)
    flexible_data = read_json(args.flexible_estimates)
    anchor_data = read_json(args.anchor_estimates)
    role_routes = {route["id"]: route for route in role_data["routes"]}
    flexible_routes = {route["id"]: route for route in flexible_data["routes"]}
    anchor_routes = {route["id"]: route for route in anchor_data["routes"]}
    generated_at = "2026-10-12T00:00:00+03:00"
    route_reports = []
    total_outcomes = Counter()
    total_matching_methods = Counter()

    for route in output["routes"]:
        route_id = route["id"]
        trips = route.get("trips", [])
        if not trips:
            continue
        ais_route_id = ROUTE_ALIASES.get(route_id, route_id)
        role_route = role_routes.get(ais_route_id)
        flexible_route = flexible_routes.get(ais_route_id)
        anchor_route = anchor_routes.get(ais_route_id)
        route_outcomes = Counter()
        route_matching_methods = Counter()
        attached = 0
        range_attached = 0
        completion_attached = 0
        completion_range_attached = 0
        holiday_estimates_copied = 0
        untimed = 0
        for trip in trips:
            calls = trip.get("calls", [])
            if len(calls) < 2:
                continue
            start_time = clock(calls[0])
            stops = [normalized_stop(route_id, call["stop"]) for call in calls]
            shape = trip_shape(stops)
            for index, call in enumerate(calls[1:], start=1):
                if clock(call):
                    route_outcomes["published_time_preserved"] += 1
                    continue
                untimed += 1
                if not start_time:
                    route_outcomes["missing_departure_anchor"] += 1
                    continue
                if route_id == "nagutvar":
                    route_outcomes["no_ais_source"] += 1
                    continue
                target = stops[index]
                schedule_prefix = stops[: index + 1]
                required_prefix = [stops[0]] + [
                    stops[prior_index]
                    for prior_index in range(1, index)
                    if clock(calls[prior_index])
                ] + [target]
                cap = next_published_elapsed(calls, index, start_time)
                candidates = []
                method = "role_aware_compatible_paths"
                model_version = role_data["modelVersion"]
                role = call_role(stops, index)
                allowed_roles = compatible_roles(stops, index)
                end_is_model_terminal = bool(
                    role_route and stops[-1] in role_route.get("terminals", [])
                )
                if role_route and not end_is_model_terminal:
                    # The published table can begin or end at an overnight or
                    # demand pier which the AIS journey detector does not use as
                    # a terminal.  Exact prefix compatibility still protects
                    # the estimate, while the full-journey role is not known.
                    allowed_roles = {
                        "terminal_to_terminal", "turnaround", "outbound",
                        "inbound", "single_loop_call", "journey_endpoint",
                    }
                if route_id in FLEXIBLE_PATH_ROUTES and flexible_route:
                    candidates = flexible_candidates(
                        flexible_route, stops[0], target, schedule_prefix, required_prefix
                    )
                    method = "compatible_observed_paths"
                    model_version = flexible_data["modelVersion"]
                elif role_route:
                    for window in role_route.get("pathWindows", []):
                        if window["from"] != stops[0] or window["to"] != target:
                            continue
                        if end_is_model_terminal and window["journeyEnd"] != stops[-1]:
                            continue
                        if window["role"] not in allowed_roles:
                            continue
                        if not is_target_aligned_subsequence(window["prefix"], schedule_prefix):
                            continue
                        if not is_subsequence(required_prefix, window["prefix"]):
                            continue
                        candidates.append(window)
                if not candidates and anchor_route:
                    candidates = [
                        window
                        for window in anchor_route.get("pathWindows", [])
                        if window["from"] == stops[0]
                        and window["to"] == target
                        and is_target_aligned_subsequence(window["prefix"], schedule_prefix)
                        and is_subsequence(required_prefix, window["prefix"])
                    ]
                    if candidates:
                        method = "anchor_compatible_paths"
                        model_version = anchor_data["modelVersion"]
                if not candidates:
                    fallback = conservative_range(
                        route_id, role_route, flexible_route, anchor_route,
                        stops[0], stops[-1],
                        target, allowed_roles, cap, end_is_model_terminal,
                    )
                    if fallback:
                        earliest_clock, earliest_day = elapsed_to_clock(
                            start_time, fallback["possibleMinutes"][0]
                        )
                        latest_clock, latest_day = elapsed_to_clock(
                            start_time, fallback["possibleMinutes"][1]
                        )
                        call["historicalRangeEstimate"] = {
                            "basis": "historical_ais_role_fallback_range",
                            "range": {"earliest": earliest_clock, "latest": latest_clock},
                            "rangeDayOffsets": [earliest_day, latest_day],
                            **fallback,
                            "compatibleHistoricalRoles": sorted(allowed_roles),
                            "matchingMethod": "conservative_role_range",
                            "modelVersion": "combined-conservative-ranges-v1",
                            "generatedAt": generated_at,
                            "typicalTimeAvailable": False,
                            "disclosureRequired": True,
                        }
                        range_attached += 1
                        route_outcomes["conservative_range_attached"] += 1
                    else:
                        route_outcomes["no_compatible_historical_path"] += 1
                    continue
                estimate = aggregate(candidates, cap)
                if not estimate:
                    route_outcomes["incompatible_with_next_published_time"] += 1
                    continue
                median_clock, day_offset = elapsed_to_clock(start_time, estimate["typicalMinutes"][1])
                earliest_clock, earliest_day = elapsed_to_clock(start_time, estimate["possibleMinutes"][0])
                latest_clock, latest_day = elapsed_to_clock(start_time, estimate["possibleMinutes"][1])
                call["historicalEstimate"] = {
                    "basis": "historical_ais_compatible_paths",
                    "typical": median_clock,
                    "range": {"earliest": earliest_clock, "latest": latest_clock},
                    "dayOffset": day_offset,
                    "rangeDayOffsets": [earliest_day, latest_day],
                    **estimate,
                    "callRole": role,
                    "compatibleHistoricalRoles": sorted(allowed_roles),
                    "matchingMethod": method,
                    "modelVersion": model_version,
                    "generatedAt": generated_at,
                    "disclosureRequired": True,
                }
                attached += 1
                route_outcomes["estimate_attached"] += 1
                route_matching_methods[method] += 1
            final_call = calls[-1]
            final_time = clock(final_call)
            if start_time and final_time and anchor_route:
                required_completion = [stops[0]] + [
                    stops[prior_index]
                    for prior_index in range(1, len(calls) - 1)
                    if clock(calls[prior_index])
                ] + [stops[-1]]
                completion_candidates = [
                    window
                    for window in anchor_route.get("completionPathWindows", [])
                    if window["from"] == stops[0]
                    and window["to"] == stops[-1]
                    and is_target_aligned_subsequence(window["prefix"], stops)
                    and is_subsequence(required_completion, window["prefix"])
                ]
                completion_estimate = aggregate(completion_candidates, None)
                completion_method = "completion_compatible_paths"
                if completion_estimate is None:
                    completion_fallbacks = [
                        item
                        for item in anchor_route.get(
                            "completionDestinationFallbacks", []
                        )
                        if item["from"] == stops[0]
                        and item["to"] == stops[-1]
                    ]
                    if completion_fallbacks:
                        completion_estimate = {
                            "sampleSize": sum(
                                item["sampleSize"] for item in completion_fallbacks
                            ),
                            "pathVariants": len(completion_fallbacks),
                            "possibleMinutes": [
                                min(
                                    item["possibleMinutes"][0]
                                    for item in completion_fallbacks
                                ),
                                max(
                                    item["possibleMinutes"][1]
                                    for item in completion_fallbacks
                                ),
                            ],
                        }
                        completion_method = "completion_destination_range"
                if completion_estimate:
                    scheduled_elapsed = (
                        minute_value(final_time) - minute_value(start_time)
                    ) % (24 * 60)
                    earliest_clock, earliest_day = elapsed_to_clock(
                        start_time, completion_estimate["possibleMinutes"][0]
                    )
                    latest_clock, latest_day = elapsed_to_clock(
                        start_time, completion_estimate["possibleMinutes"][1]
                    )
                    historical_completion = {
                        "basis": "historical_ais_complete_route_elapsed_time",
                        "scheduled": final_time,
                        "range": {
                            "earliest": earliest_clock,
                            "latest": latest_clock,
                        },
                        "rangeDayOffsets": [earliest_day, latest_day],
                        "possibleMinutes": completion_estimate["possibleMinutes"],
                        "scheduleOffsetRangeMinutes": [
                            round(
                                completion_estimate["possibleMinutes"][0]
                                - scheduled_elapsed,
                                1,
                            ),
                            round(
                                completion_estimate["possibleMinutes"][1]
                                - scheduled_elapsed,
                                1,
                            ),
                        ],
                        "sampleSize": completion_estimate["sampleSize"],
                        "pathVariants": completion_estimate["pathVariants"],
                        "matchingMethod": completion_method,
                        "modelVersion": anchor_data["modelVersion"],
                        "generatedAt": generated_at,
                        "shortIntermediateWaitsIncluded": True,
                        "longWaitsExcluded": True,
                        "disclosureRequired": True,
                    }
                    if "typicalMinutes" in completion_estimate:
                        typical_clock, typical_day = elapsed_to_clock(
                            start_time, completion_estimate["typicalMinutes"][1]
                        )
                        historical_completion.update({
                            "typical": typical_clock,
                            "typicalDayOffset": typical_day,
                            "typicalMinutes": completion_estimate["typicalMinutes"],
                            "scheduleOffsetTypicalMinutes": round(
                                completion_estimate["typicalMinutes"][1]
                                - scheduled_elapsed,
                                1,
                            ),
                            "typicalTimeAvailable": True,
                        })
                        completion_attached += 1
                        route_outcomes["completion_estimate_attached"] += 1
                    else:
                        historical_completion["typicalTimeAvailable"] = False
                        completion_range_attached += 1
                        route_outcomes["completion_range_attached"] += 1
                    final_call["historicalCompletionEstimate"] = historical_completion
        templates = {trip.get("id"): trip for trip in trips}
        for override in route.get("holidayTripOverrides", []):
            for holiday_trip in override.get("trips", []):
                template = templates.get(holiday_trip.get("sourceTemplateId"))
                if not template:
                    continue
                for holiday_call, template_call in zip(
                    holiday_trip.get("calls", []), template.get("calls", [])
                ):
                    if holiday_call.get("stop") != template_call.get("stop"):
                        continue
                    for key in ("historicalEstimate", "historicalRangeEstimate"):
                        if key in template_call and not clock(holiday_call):
                            holiday_call[key] = copy.deepcopy(template_call[key])
                            holiday_estimates_copied += 1
                holiday_calls = holiday_trip.get("calls", [])
                template_calls = template.get("calls", [])
                if holiday_calls and template_calls:
                    holiday_start = clock(holiday_calls[0])
                    holiday_end = clock(holiday_calls[-1])
                    template_completion = template_calls[-1].get(
                        "historicalCompletionEstimate"
                    )
                    if holiday_start and holiday_end and template_completion:
                        completion = copy.deepcopy(template_completion)
                        completion["scheduled"] = holiday_end
                        earliest_clock, earliest_day = elapsed_to_clock(
                            holiday_start, completion["possibleMinutes"][0]
                        )
                        latest_clock, latest_day = elapsed_to_clock(
                            holiday_start, completion["possibleMinutes"][1]
                        )
                        scheduled_elapsed = (
                            minute_value(holiday_end) - minute_value(holiday_start)
                        ) % (24 * 60)
                        completion["range"] = {
                            "earliest": earliest_clock,
                            "latest": latest_clock,
                        }
                        completion["rangeDayOffsets"] = [earliest_day, latest_day]
                        completion["scheduleOffsetRangeMinutes"] = [
                            round(completion["possibleMinutes"][0] - scheduled_elapsed, 1),
                            round(completion["possibleMinutes"][1] - scheduled_elapsed, 1),
                        ]
                        if completion.get("typicalTimeAvailable"):
                            typical_clock, typical_day = elapsed_to_clock(
                                holiday_start, completion["typicalMinutes"][1]
                            )
                            completion["typical"] = typical_clock
                            completion["typicalDayOffset"] = typical_day
                            completion["scheduleOffsetTypicalMinutes"] = round(
                                completion["typicalMinutes"][1] - scheduled_elapsed, 1
                            )
                        holiday_calls[-1]["historicalCompletionEstimate"] = completion
                        holiday_estimates_copied += 1
        if untimed or route_id in {"norralinjen", "sodralinjen"}:
            route_reports.append({
                "routeId": route_id,
                "aisRouteId": ais_route_id,
                "trips": len(trips),
                "untimedCalls": untimed,
                "estimatesAttached": attached,
                "conservativeRangesAttached": range_attached,
                "completionEstimatesAttached": completion_attached,
                "completionRangesAttached": completion_range_attached,
                "holidayEstimateCallsCopied": holiday_estimates_copied,
                "coverage": round((attached + range_attached) / untimed, 3) if untimed else 1.0,
                "outcomes": dict(sorted(route_outcomes.items())),
                "matchingMethods": dict(sorted(route_matching_methods.items())),
            })
            total_outcomes.update(route_outcomes)
            total_matching_methods.update(route_matching_methods)

    output["status"] = "draft_connection_trips_with_role_aware_ais_estimates"
    output["historicalEstimatePolicy"] = {
        "publishedTimesAlwaysWin": True,
        "broadRoleFallbackTypicalTimesUsed": False,
        "conservativeRoleFallbackRangesUsed": True,
        "compatibleHistoricalPathsOnly": True,
        "publishedJourneyEndTimesIncludeHistoricalCompletionComparison": True,
        "completionElapsedTimeIncludesShortIntermediateWaits": True,
        "arbitraryPublishedDepartureAnchors": True,
        "alandTimingAuthority": "published_timetable",
        "naguTransverse": "kept_without_ais_estimates_because_vessel_has_no_ais",
        "discontinuedRoute": "aland_transverse",
    }
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "status": "draft_requires_semantic_review",
        "generatedAt": generated_at,
        "routes": route_reports,
        "summary": {
            "routes": len(route_reports),
            "untimedCalls": sum(item["untimedCalls"] for item in route_reports),
            "estimatesAttached": sum(item["estimatesAttached"] for item in route_reports),
            "conservativeRangesAttached": sum(
                item["conservativeRangesAttached"] for item in route_reports
            ),
            "completionEstimatesAttached": sum(
                item["completionEstimatesAttached"] for item in route_reports
            ),
            "completionRangesAttached": sum(
                item["completionRangesAttached"] for item in route_reports
            ),
            "holidayEstimateCallsCopied": sum(
                item["holidayEstimateCallsCopied"] for item in route_reports
            ),
            "coverage": round(
                sum(
                    item["estimatesAttached"] + item["conservativeRangesAttached"]
                    for item in route_reports
                )
                / sum(item["untimedCalls"] for item in route_reports), 3
            ),
            "outcomes": dict(sorted(total_outcomes.items())),
            "matchingMethods": dict(sorted(total_matching_methods.items())),
        },
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
