#!/usr/bin/env python3
"""List direct scheduled rides between two routing-graph piers on a date.

This is the first executable query layer for the experimental graph. It does
not yet search transfers; it deliberately proves calendar filtering, published
departure times, historical arrival ranges and passenger information first.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parents[1]
DEFAULT_GRAPH = EXPERIMENT / "routing-graph.json"


def date_in_periods(day: date, periods: list[dict]) -> bool:
    if not periods:
        return True
    return any(
        date.fromisoformat(period["validFrom"]) <= day <= date.fromisoformat(period["validTo"])
        for period in periods
        if period.get("validFrom") and period.get("validTo")
    )


def day_pattern_runs(pattern: str | None, day: date) -> bool:
    if not pattern or len(pattern) != 7:
        return False
    return pattern[day.weekday()] != "_"


def holiday_decision(route: dict, day: date) -> tuple[str | None, str | None]:
    """Return an action and optional replacement weekday pattern."""
    key = day.isoformat()
    for exception in route.get("holidayExceptions", []):
        if exception.get("date") != key:
            continue
        action = exception.get("action")
        if action == "no_service":
            return action, None
        if action == "use_day_pattern":
            pattern = exception.get("operatingDays")
            templates = {
                "monday": "1______", "tuesday": "_2_____", "wednesday": "__3____",
                "thursday": "___4___", "friday": "____5__", "saturday": "_____6_",
                "sunday": "______7",
            }
            return action, pattern or templates.get(exception.get("scheduleTemplate"))
        return action, None
    return None, None


def timing_summary(timing: dict) -> dict:
    result = {"status": timing.get("status")}
    for key in (
        "time", "dayOffset", "range", "rangeDayOffsets", "sampleSize",
        "modelVersion", "disclosureRequired", "timeNature",
    ):
        if key in timing:
            result[key] = timing[key]
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("origin")
    parser.add_argument("destination")
    parser.add_argument("travel_date", type=date.fromisoformat)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--mode", choices=("foot", "bicycle", "motorcycle", "car"), default="foot")
    args = parser.parse_args()

    graph = json.loads(args.graph.read_text())
    routes = {route["id"]: route for route in graph["routes"]}
    node_ids = {node["id"] for node in graph["nodes"]}
    for value, label in ((args.origin, "origin"), (args.destination, "destination")):
        if value not in node_ids:
            raise SystemExit(f"unknown {label}: {value}")

    results = []
    for edge in graph["edges"]:
        if (
            edge["kind"] != "scheduled_service"
            or not edge.get("enabledForAutomaticRouting", True)
            or edge["from"] != args.origin
            or edge["to"] != args.destination
        ):
            continue
        if edge.get("mobility", {}).get(args.mode) not in {
            "allowed", "allowed_subject_to_operator_conditions", "booking_validation_required",
        }:
            continue
        route = routes[edge["routeId"]]
        schedule = edge["schedule"]
        if not date_in_periods(args.travel_date, schedule.get("validPeriods", [])):
            continue
        action, replacement_pattern = holiday_decision(route, args.travel_date)
        if action == "no_service":
            continue
        operating_days = schedule.get("operatingDays")
        if replacement_pattern:
            # Select trips belonging to the replacement day, not trips matching
            # the calendar weekday of the exception date.
            if operating_days != replacement_pattern:
                continue
        elif not day_pattern_runs(operating_days, args.travel_date):
            continue
        departure = schedule.get("departure", {})
        if not departure.get("time"):
            continue
        results.append({
            "routeId": edge["routeId"],
            "tripPatternId": edge["tripPatternId"],
            "from": edge["from"],
            "to": edge["to"],
            "date": args.travel_date.isoformat(),
            "departure": timing_summary(departure),
            "arrival": timing_summary(schedule.get("arrival", {})),
            "duration": schedule.get("duration"),
            "mode": args.mode,
            "modeRule": edge.get("mobility", {}).get(args.mode),
            "callConditions": {
                "origin": edge.get("conditions", {}).get("fromCallCondition"),
                "destination": edge.get("conditions", {}).get("toCallCondition"),
            },
            "intermediateCalls": edge.get("conditions", {}).get("intermediateCalls", []),
            "vessel": route.get("vessel"),
            "vessels": route.get("vessels"),
            "capacity": route.get("capacity"),
            "contact": route.get("contact"),
            "booking": route.get("booking"),
            "travelerInformation": route.get("travelerInformation"),
            "publicTimetableUrl": route.get("publicTimetableUrl"),
        })

    results.sort(key=lambda item: item["departure"]["time"])
    print(json.dumps({
        "queryType": "direct_scheduled_service",
        "origin": args.origin,
        "destination": args.destination,
        "date": args.travel_date.isoformat(),
        "mode": args.mode,
        "resultCount": len(results),
        "results": results,
        "limitations": [
            "does not search transfers yet",
            "does not yet expand continuous on-demand ferry service",
            "non-standard holiday modifications still require review",
        ],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
