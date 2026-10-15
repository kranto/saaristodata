#!/usr/bin/env python3
"""Normalize connection-vessel timetable tables into machine-readable trips.

This is an analysis artifact. It leaves the current application data and the
source-faithful structured-timetables.json unchanged.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
from collections import Counter
from pathlib import Path


WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DAY_INDEX = {day: index for index, day in enumerate(WEEKDAYS)}
SWEDISH_DAYS = {
    "Måndag": "monday", "Tisdag": "tuesday", "Onsdag": "wednesday",
    "Torsdag": "thursday", "Fredag": "friday", "Lördag": "saturday",
    "Söndag": "sunday",
}
NAMED_DAY_PATTERNS = {
    "monday": "1______", "tuesday": "_2_____", "wednesday": "__3____",
    "thursday": "___4___", "friday": "____5__", "saturday": "_____6_",
    "sunday": "______7",
}

ADDITIONAL_HOLIDAY_RULES = {
    "korporutt": [
        {"date": "2026-12-06", "action": "use_day_pattern", "scheduleTemplate": "sunday"},
        {"date": "2026-12-23", "action": "use_day_pattern", "scheduleTemplate": "friday"},
        {"date": "2026-12-24", "action": "no_service"},
        {"date": "2026-12-25", "action": "no_service"},
        {"date": "2026-12-26", "action": "use_day_pattern", "scheduleTemplate": "sunday"},
        {"date": "2026-12-27", "action": "use_day_pattern", "scheduleTemplate": "sunday"},
        {"date": "2027-01-01", "action": "use_day_pattern", "scheduleTemplate": "friday"},
        {"date": "2027-01-06", "action": "no_service"},
        {"date": "2027-03-25", "action": "use_day_pattern", "scheduleTemplate": "friday"},
        {"date": "2027-03-26", "action": "no_service"},
        {"date": "2027-03-27", "action": "use_day_pattern", "scheduleTemplate": "sunday"},
        {"date": "2027-03-28", "action": "no_service"},
        {"date": "2027-03-29", "action": "use_day_pattern", "scheduleTemplate": "monday"},
        {"date": "2027-05-01", "action": "no_service"},
        {"date": "2027-05-16", "action": "use_day_pattern", "scheduleTemplate": "sunday"},
    ],
    "utorutt": [
        {"date": "2026-12-06", "action": "use_day_pattern", "scheduleTemplate": "sunday"},
        {"date": "2026-12-23", "action": "use_day_pattern", "scheduleTemplate": "wednesday"},
        {"date": "2026-12-24", "action": "no_service"},
        {"date": "2026-12-25", "action": "no_service"},
        {"date": "2026-12-26", "action": "use_day_pattern", "scheduleTemplate": "wednesday"},
        {"date": "2026-12-27", "action": "use_day_pattern", "scheduleTemplate": "monday"},
        {"date": "2026-12-31", "action": "use_day_pattern", "scheduleTemplate": "thursday"},
        {"date": "2027-01-01", "action": "use_day_pattern", "scheduleTemplate": "saturday"},
        {"date": "2027-01-05", "action": "use_day_pattern", "scheduleTemplate": "wednesday"},
        {"date": "2027-01-06", "action": "no_service"},
        {"date": "2027-03-25", "action": "use_day_pattern", "scheduleTemplate": "friday", "notBefore": "18:00"},
        {"date": "2027-03-26", "action": "no_service"},
        {"date": "2027-03-27", "action": "use_day_pattern", "scheduleTemplate": "saturday"},
        {"date": "2027-03-28", "action": "no_service"},
        {"date": "2027-03-29", "action": "use_day_pattern", "scheduleTemplate": "sunday"},
        {"date": "2027-03-30", "action": "use_day_pattern", "scheduleTemplate": "monday"},
        {"date": "2027-05-01", "action": "use_day_pattern", "scheduleTemplate": "saturday"},
        {"date": "2027-05-06", "action": "use_day_pattern", "scheduleTemplate": "thursday"},
    ],
}

TARGET_ROUTES = {
    "hitisalva", "hitisjurmo", "houtskarrutt", "korporutt", "nagunorra",
    "nagusodra", "nagutvar", "norralinjen", "pargasrutt",
    "rymattylanreitti", "sodralinjen", "utorutt", "velkuanreitti",
}

FINFERRIES_TERMINALS = {
    "houtskarrutt": {"Själö", "Roslax", "Näsby", "TorsholmaI", "Kannvik", "Norrby"},
    "nagunorra": {"Åvensor", "Lavarn", "Nagu"},
    "nagusodra": {"Kirjais"},
    "nagutvar": {"Hummelholm", "Pärnäs", "Kirjais"},
    "pargasrutt": {"Granvik"},
    "rymattylanreitti": {"Haapala"},
    "korporutt": {"Verkan"},
    "utorutt": {"Pärnäs", "Utö"},
    "velkuanreitti": {"Teersalo", "Hakkenpää"},
}

STOP_ALIASES = {
    "Lavarn (Houtsala)": "Lavarn",
    "Nagu/Nauvo": "Nagu",
    "Pärnäs/Pärnäinen": "Pärnäs",
    "Själö/Seili *": "Seili",
    "Penö": "Peno",
    "NÄSBY": "Näsby",
    "Torsholma": "TorsholmaI",
    "Vänoxa släten": "Vänoxasläten",
    "Storpensar": "Storpensor",
    "Lillpensar": "Lillpensor",
    "Havstrask": "Havträsk",
    "Korpo/Korppoo": "Verkan",
    "Korppo/Korppoo": "Verkan",
    "Fiskö/ Korpo/Korppoo": "Verkan",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("report", type=Path)
    return parser.parse_args()


def day_pattern(day: str) -> str:
    index = DAY_INDEX[day]
    return "".join(str(i + 1) if i == index else "_" for i in range(7))


def merge_day(pattern: str, day: str) -> str:
    values = list(pattern)
    index = DAY_INDEX[day]
    values[index] = str(index + 1)
    return "".join(values)


def clean_stop(value: str) -> str:
    value = re.sub(r"\s+", " ", value.replace("\n", " ")).strip()
    value = re.sub(r"\s*\([^)]*\)\s*$", "", value).strip()
    value = re.sub(r"\d+\)", "", value).strip()
    if value.isupper():
        value = value.title()
    return STOP_ALIASES.get(value, value)


def expanded_stops(route: dict, source_stop: str) -> list[str]:
    expansion = route.get("sourceRowExpansions", {}).get(source_stop)
    if expansion:
        return [STOP_ALIASES.get(stop, stop) for stop in expansion["stops"]]
    if source_stop in STOP_ALIASES:
        return [STOP_ALIASES[source_stop]]
    return [clean_stop(source_stop)]


def parse_cell(value: str | None) -> dict | None:
    if value is None:
        return None
    source = re.sub(r"\s+", " ", str(value)).strip()
    if not source or source in {"–", "-"}:
        return None
    match = re.search(r"(\d{1,2})[.:](\d{2})", source)
    result = {"sourceValue": source}
    if match:
        result["time"] = f"{int(match.group(1)):02d}:{match.group(2)}"
    marker = re.search(r"(?<![A-Za-z])[yx](?![A-Za-z])", source, re.I)
    if marker:
        result["callCondition"] = marker.group(0).lower()
    if source.startswith("~"):
        result["timeNature"] = "approximate"
    elif match and "(" in source[: match.start() + 1]:
        result["timeNature"] = "estimated_intermediate"
    notes = re.findall(r"\*+|\++|\d+\)|[A-Z]\)", source)
    if notes:
        result["sourceAnnotations"] = notes
    return result


def append_expanded_calls(calls: list[dict], stops: list[str], parsed: dict) -> None:
    for index, stop in enumerate(stops):
        call = {"stop": stop, **parsed}
        if index and "time" in call:
            call.pop("time")
            call["timeNature"] = "shared_source_row_without_individual_time"
        calls.append(call)


def apply_route_specific_call_order(route_id: str, calls: list[dict]) -> list[dict]:
    """Apply reviewed sailing order where the PDF row order is not chronological."""
    if route_id != "rymattylanreitti":
        return calls
    # The Rymättylä PDF lists demand-call rows as Wihuri, Pyytti, but AIS
    # journeys consistently reach Pyytti before Wihuri on this branch. The
    # table's vertical row order is therefore not the sailing order.
    wihuri = next((index for index, call in enumerate(calls) if call["stop"] == "Wihuri"), None)
    pyytti = next((index for index, call in enumerate(calls) if call["stop"] == "Pyytti"), None)
    if wihuri is not None and pyytti is not None and wihuri < pyytti:
        result = list(calls)
        pyytti_call = result.pop(pyytti)
        result.insert(wihuri, pyytti_call)
        return result
    return calls


def strip_nonchronological_intermediate_time(active: list[dict], parsed: dict) -> dict:
    """Keep a source marker but do not treat a backwards daytime time as this trip's time."""
    if "time" not in parsed:
        return parsed
    previous = next((call.get("time") for call in reversed(active) if call.get("time")), None)
    if not previous:
        return parsed
    previous_minutes = int(previous[:2]) * 60 + int(previous[3:])
    current_minutes = int(parsed["time"][:2]) * 60 + int(parsed["time"][3:])
    if current_minutes < previous_minutes and previous_minutes < 18 * 60:
        result = dict(parsed)
        result.pop("time")
        result["timeNature"] = "source_table_nonchronological_needs_review"
        return result
    return parsed


def finish_trip(trips: list[dict], calls: list[dict] | None, day: str, route_id: str) -> None:
    if not calls or len(calls) < 2 or "time" not in calls[0]:
        return
    calls = apply_route_specific_call_order(route_id, calls)
    trips.append({
        "id": f"{route_id}-{day}-{len(trips) + 1:03d}",
        "operatingDays": day_pattern(day),
        "normalizationStatus": "machine_generated_requires_semantic_review",
        "calls": calls,
    })


def merge_identical_trips(trips: list[dict], route_id: str) -> list[dict]:
    merged: dict[str, dict] = {}
    for trip in trips:
        key = json.dumps(trip["calls"], ensure_ascii=False, sort_keys=True)
        if key not in merged:
            merged[key] = copy.deepcopy(trip)
        else:
            for day in WEEKDAYS:
                if day_pattern(day) == trip["operatingDays"]:
                    merged[key]["operatingDays"] = merge_day(merged[key]["operatingDays"], day)
                    break
    result = list(merged.values())
    result.sort(key=lambda trip: (trip["calls"][0].get("time", ""), trip["operatingDays"], key))
    for index, trip in enumerate(result, start=1):
        trip["id"] = f"{route_id}-normalized-{index:03d}"
    return result


def merged_holiday_rules(route: dict) -> list[dict]:
    by_date = {
        rule["date"]: copy.deepcopy(rule)
        for rule in ADDITIONAL_HOLIDAY_RULES.get(route["id"], [])
    }
    for rule in route.get("holidayExceptions", []):
        date = rule.get("date")
        if date:
            by_date[date] = {**by_date.get(date, {}), **copy.deepcopy(rule)}
    return [by_date[date] for date in sorted(by_date)]


def normalize_holiday_overrides(route: dict) -> list[dict]:
    overrides = []
    for rule in merged_holiday_rules(route):
        cutoff = rule.get("notBefore")
        if not cutoff and re.fullmatch(r"\d{1,2}:\d{2}", str(rule.get("from", ""))):
            cutoff = rule["from"]
        no_service = rule.get("action") == "no_service" or (
            rule.get("service") == "none" and not cutoff
        )
        if no_service:
            overrides.append({
                "date": rule["date"],
                "action": "no_service",
                "sourceRule": rule,
                "trips": [],
            })
            continue
        pattern = rule.get("operatingDays")
        template = rule.get("scheduleTemplate")
        if template:
            pattern = NAMED_DAY_PATTERNS.get(template.lower())
        if not pattern:
            continue
        selected = []
        for trip in route.get("trips", []):
            operating_days = trip.get("operatingDays", "_______")
            if not any(a != "_" and b != "_" for a, b in zip(operating_days, pattern)):
                continue
            departure = next(
                (call.get("departure") or call.get("time") for call in trip.get("calls", []) if call.get("departure") or call.get("time")),
                None,
            )
            if cutoff and departure and departure < cutoff:
                continue
            holiday_trip = copy.deepcopy(trip)
            holiday_trip["sourceTemplateId"] = trip["id"]
            holiday_trip["id"] = f"{rule['date']}-{trip['id']}"
            holiday_trip["operatingDate"] = rule["date"]
            holiday_trip.pop("operatingDays", None)
            if rule.get("forceCallCondition"):
                for call in holiday_trip.get("calls", []):
                    if call.get("callCondition"):
                        call["callCondition"] = rule["forceCallCondition"]
            selected.append(holiday_trip)
        overrides.append({
            "date": rule["date"],
            "action": "replace_regular_schedule",
            "sourceRule": rule,
            "trips": selected,
        })
    return overrides


def normalize_finferries(route: dict) -> list[dict]:
    route_id = route["id"]
    terminals = FINFERRIES_TERMINALS[route_id]
    table = next(
        (table for table in route.get("sourceTables", []) if len(table.get("rows", [])) >= 3 and len(table["rows"][0]) >= 7),
        None,
    )
    if not table:
        return []
    rows = table["rows"][1:]
    trips = []
    for day_index, day in enumerate(WEEKDAYS):
        active = None
        for row in rows:
            source_stop = (row[0] or "").strip() if row else ""
            if not source_stop:
                finish_trip(trips, active, day, route_id)
                active = None
                continue
            values = list(row[-7:])
            parsed = parse_cell(values[day_index])
            if not parsed:
                continue
            stops = expanded_stops(route, source_stop)
            first_stop = stops[0]
            if active is None:
                if "time" not in parsed:
                    continue
                active = []
                append_expanded_calls(active, stops, parsed)
                continue
            if (
                len(active) == 1
                and first_stop in terminals
                and active[0]["stop"] == first_stop
            ):
                # Consecutive entries at the same terminal describe waiting at
                # the terminal, not a zero-distance sailing.  The later time is
                # the next useful departure anchor.
                active = []
                append_expanded_calls(active, stops, parsed)
                continue
            parsed = strip_nonchronological_intermediate_time(active, parsed)
            append_expanded_calls(active, stops, parsed)
            if first_stop in terminals and "time" in parsed:
                finish_trip(trips, active, day, route_id)
                active = None
        finish_trip(trips, active, day, route_id)
    return merge_identical_trips(trips, route_id)


def aland_stop_headers(table: dict) -> list[str]:
    return [clean_stop(value or "") for value in table["rows"][1][2:]]


def parse_packed_line(line: str, inherited_day: str | None) -> tuple[str | None, str | None, list[str]]:
    line = re.sub(r"\s+", " ", line).strip()
    day = inherited_day
    for label, normalized in SWEDISH_DAYS.items():
        if line.startswith(label + " "):
            day = normalized
            line = line[len(label):].strip()
            break
    tokens = line.split()
    if not tokens:
        return day, None, []
    vessel = tokens.pop(0)
    values = [token for token in tokens if token == "–" or re.search(r"\d{1,2}:\d{2}", token)]
    return day, vessel, values


def aland_rows(table: dict) -> list[tuple[str, str, list[str | None]]]:
    count = len(aland_stop_headers(table))
    rows = table["rows"]
    result = []
    current_day = None
    index = 2
    while index < len(rows):
        row = rows[index]
        first = (row[0] or "").strip() if row else ""
        second = row[1] if len(row) > 1 else None
        if second not in (None, ""):
            for label, normalized in SWEDISH_DAYS.items():
                if first.startswith(label):
                    current_day = normalized
                    break
            if current_day:
                result.append((current_day, str(second).strip(), list(row[2:2 + count])))
            index += 1
            continue
        lines = first.splitlines() if first else []
        parsed_lines = []
        inherited = current_day
        for line in lines:
            day, vessel, values = parse_packed_line(line, inherited)
            if not day or not vessel or not values:
                continue
            inherited = day
            current_day = day
            parsed_lines.append((day, vessel, values))
        if not parsed_lines:
            index += 1
            continue
        for offset, (day, vessel, prefix) in enumerate(parsed_lines):
            suffix_row = rows[index + offset] if index + offset < len(rows) else []
            suffix = list(suffix_row[2:2 + count])
            values = []
            for stop_index in range(count):
                if stop_index < len(prefix):
                    values.append(prefix[stop_index])
                else:
                    values.append(suffix[stop_index] if stop_index < len(suffix) else None)
            result.append((day, vessel, values))
        consumes_continuations = any(len(prefix) < count for _, _, prefix in parsed_lines)
        index += len(parsed_lines) if consumes_continuations else 1
    return result


def normalize_aland(route: dict) -> list[dict]:
    route_id = route["id"]
    regular_pages = {5} if route_id == "norralinjen" else {9, 10}
    trips = []
    for table in route.get("sourceTables", []):
        if table.get("page") not in regular_pages or len(table.get("rows", [])) < 3:
            continue
        stops = aland_stop_headers(table)
        for day, vessel, values in aland_rows(table):
            calls = []
            day_offset = 0
            last_minutes = None
            for stop, source_value in zip(stops, values):
                parsed = parse_cell(source_value)
                if not parsed or "time" not in parsed:
                    continue
                hour, minute = map(int, parsed["time"].split(":"))
                minutes = hour * 60 + minute
                if last_minutes is not None and minutes < last_minutes - 12 * 60:
                    day_offset += 1
                last_minutes = minutes
                call = {"stop": stop, **parsed}
                if day_offset:
                    call["dayOffset"] = day_offset
                calls.append(call)
            if len(calls) >= 2:
                trips.append({
                    "id": f"{route_id}-{day}-{len(trips) + 1:03d}",
                    "operatingDays": day_pattern(day),
                    "vesselCode": vessel,
                    "schedule": "regular",
                    "normalizationStatus": "machine_generated_requires_semantic_review",
                    "calls": calls,
                })
    return merge_identical_trips(trips, route_id)


def main() -> None:
    args = parse_args()
    source = json.loads(args.source.read_text(encoding="utf-8"))
    output = copy.deepcopy(source)
    output["status"] = "draft_connection_trips_normalized"
    report_routes = []
    for route in output["routes"]:
        if route["id"] not in TARGET_ROUTES:
            continue
        original_count = len(route.get("trips", []))
        generated = []
        method = "existing_reviewed_draft"
        if route["id"] in FINFERRIES_TERMINALS:
            generated = normalize_finferries(route)
            if generated:
                method = "finferries_weekday_columns"
        elif not original_count and route["id"] in {"norralinjen", "sodralinjen"}:
            generated = normalize_aland(route)
            method = "aland_regular_tables"
        if generated:
            route["trips"] = generated
        holiday_rules = merged_holiday_rules(route)
        if holiday_rules:
            route["holidayExceptions"] = holiday_rules
        holiday_overrides = normalize_holiday_overrides(route)
        if holiday_overrides:
            route["holidayTripOverrides"] = holiday_overrides
        holiday_overrides_complete = bool(holiday_rules) and len(holiday_overrides) == len(holiday_rules) and all(
            item["action"] == "no_service" or bool(item.get("trips"))
            for item in holiday_overrides
        )
        route["tripNormalization"] = {
            "method": method,
            "status": "machine_generated_requires_semantic_review" if generated else "source_transcription",
            "regularScheduleCovered": bool(route.get("trips")),
            "holidayRulesPreserved": bool(holiday_rules),
            "holidayTripOverridesNormalized": holiday_overrides_complete,
        }
        missing_time_calls = sum(
            not any(call.get(key) for key in ("time", "arrival", "departure"))
            for trip in route.get("trips", [])
            for call in trip.get("calls", [])
        )
        report_routes.append({
            "routeId": route["id"],
            "method": method,
            "trips": len(route.get("trips", [])),
            "calls": sum(len(trip.get("calls", [])) for trip in route.get("trips", [])),
            "callsWithoutPublishedTime": missing_time_calls,
            "regularScheduleCovered": bool(route.get("trips")),
            "holidayRulesPreserved": bool(holiday_rules),
            "holidayTripOverridesNormalized": holiday_overrides_complete,
            "holidayRules": len(holiday_rules),
            "holidayTripOverrides": len(holiday_overrides),
        })
    output["statistics"]["connectionRouteTripCount"] = sum(item["trips"] for item in report_routes)
    output["statistics"]["connectionRouteCount"] = len(report_routes)
    output["statistics"]["connectionRoutesWithTrips"] = sum(item["trips"] > 0 for item in report_routes)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "status": "draft",
        "routes": report_routes,
        "summary": {
            "routes": len(report_routes),
            "routesWithTrips": sum(item["trips"] > 0 for item in report_routes),
            "trips": sum(item["trips"] for item in report_routes),
            "calls": sum(item["calls"] for item in report_routes),
            "callsWithoutPublishedTime": sum(item["callsWithoutPublishedTime"] for item in report_routes),
            "routesWithPreservedHolidayRules": sum(item["holidayRulesPreserved"] for item in report_routes),
            "routesWithNormalizedHolidayTripOverrides": sum(
                item["holidayTripOverridesNormalized"] for item in report_routes
            ),
        },
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
