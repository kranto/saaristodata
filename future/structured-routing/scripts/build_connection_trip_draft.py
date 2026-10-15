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
    "avajurmo": [
        {"date": "2026-12-24", "action": "use_day_pattern", "scheduleTemplate": "thursday", "notAfter": "17:25", "forceCallCondition": "holiday_booking"},
        {"date": "2026-12-25", "action": "use_day_pattern", "scheduleTemplate": "sunday", "notBefore": "11:05", "notAfter": "16:55"},
        {"date": "2026-12-26", "action": "use_day_pattern", "scheduleTemplate": "sunday", "notBefore": "11:05", "notAfter": "16:55"},
        {"date": "2026-12-31", "action": "use_day_pattern", "scheduleTemplate": "thursday", "notAfter": "17:25", "forceCallCondition": "holiday_booking"},
    ],
    "enklingelinjen": [
        {"date": "2026-10-14", "action": "use_day_pattern", "scheduleTemplate": "wednesday", "forceCallCondition": "holiday_booking"},
        {"date": "2026-10-15", "action": "use_day_pattern", "scheduleTemplate": "thursday", "forceCallCondition": "holiday_booking"},
        {"date": "2026-10-16", "action": "use_day_pattern", "scheduleTemplate": "friday", "forceCallCondition": "holiday_booking"},
        {"date": "2026-12-23", "action": "use_day_pattern", "scheduleTemplate": "wednesday", "forceCallCondition": "holiday_booking"},
        {"date": "2026-12-24", "action": "use_day_pattern", "scheduleTemplate": "thursday", "forceCallCondition": "holiday_booking"},
        {"date": "2026-12-25", "action": "use_day_pattern", "scheduleTemplate": "sunday", "forceCallCondition": "holiday_booking",
         "extraTrips": [["Kumlinge", "06:30", "Enklinge", "06:45"], ["Enklinge", "06:45", "Kumlinge", "07:00"], ["Kumlinge", "21:45", "Enklinge", "22:00"], ["Enklinge", "22:00", "Kumlinge", "22:15"]]},
        {"date": "2026-12-26", "action": "use_day_pattern", "scheduleTemplate": "sunday", "forceCallCondition": "holiday_booking",
         "extraTrips": [["Kumlinge", "06:30", "Enklinge", "06:45"], ["Enklinge", "06:45", "Kumlinge", "07:00"], ["Kumlinge", "21:45", "Enklinge", "22:00"], ["Enklinge", "22:00", "Kumlinge", "22:15"]]},
        {"date": "2026-12-27", "action": "use_day_pattern", "scheduleTemplate": "sunday", "forceCallCondition": "holiday_booking"},
        {"date": "2026-12-28", "action": "use_day_pattern", "scheduleTemplate": "monday", "forceCallCondition": "holiday_booking"},
        {"date": "2026-12-29", "action": "use_day_pattern", "scheduleTemplate": "tuesday", "forceCallCondition": "holiday_booking"},
        {"date": "2026-12-30", "action": "use_day_pattern", "scheduleTemplate": "wednesday", "forceCallCondition": "holiday_booking"},
        {"date": "2026-12-31", "action": "use_day_pattern", "scheduleTemplate": "thursday", "forceCallCondition": "holiday_booking"},
    ],
    "foglolinjen": [
        {"date": "2026-10-31", "action": "use_day_pattern", "scheduleTemplate": "sunday"},
        {"date": "2026-12-06", "action": "use_day_pattern", "scheduleTemplate": "sunday"},
        {"date": "2026-12-24", "action": "use_day_pattern", "scheduleTemplate": "thursday", "notAfter": "16:55",
         "extraTrips": [["Degerby", "22:25", "Svinö", "22:55"], ["Svinö", "23:00", "Degerby", "23:30"]]},
        {"date": "2026-12-25", "action": "use_day_pattern", "scheduleTemplate": "sunday", "notBefore": "12:15"},
        {"date": "2026-12-26", "action": "use_day_pattern", "scheduleTemplate": "sunday", "notBefore": "10:45"},
        {"date": "2026-12-31", "action": "use_day_pattern", "scheduleTemplate": "thursday", "notAfter": "20:25"},
    ],
    "iniorutt": [
        {"date": "2026-12-06", "action": "use_day_pattern", "scheduleTemplate": "sunday"},
        {"date": "2026-12-24", "action": "use_day_pattern", "scheduleTemplate": "saturday"},
        {"date": "2026-12-25", "action": "no_service"},
        {"date": "2026-12-26", "action": "use_day_pattern", "scheduleTemplate": "saturday"},
        {"date": "2026-12-31", "action": "use_day_pattern", "scheduleTemplate": "friday"},
        {"date": "2027-01-01", "action": "use_day_pattern", "scheduleTemplate": "saturday"},
        {"date": "2027-01-06", "action": "use_day_pattern", "scheduleTemplate": "saturday"},
        {"date": "2027-03-25", "action": "use_day_pattern", "scheduleTemplate": "friday"},
        {"date": "2027-03-26", "action": "use_day_pattern", "scheduleTemplate": "saturday"},
        {"date": "2027-03-27", "action": "no_service"},
        {"date": "2027-03-28", "action": "no_service"},
        {"date": "2027-03-29", "action": "use_day_pattern", "scheduleTemplate": "sunday"},
    ],
    "osnasava": [
        {"date": "2026-12-24", "action": "use_day_pattern", "scheduleTemplate": "thursday", "notAfter": "17:30"},
        {"date": "2026-12-25", "action": "use_day_pattern", "scheduleTemplate": "sunday", "notBefore": "16:05", "notAfter": "17:00"},
        {"date": "2026-12-26", "action": "use_day_pattern", "scheduleTemplate": "sunday", "notBefore": "13:05", "notAfter": "19:00"},
        {"date": "2026-12-31", "action": "use_day_pattern", "scheduleTemplate": "thursday", "notAfter": "17:30"},
    ],
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
    "velkuataivassalo": [
        {"date": "2026-12-06", "action": "use_day_pattern", "scheduleTemplate": "sunday"},
        {"date": "2026-12-24", "action": "use_day_pattern", "scheduleTemplate": "saturday"},
        {"date": "2026-12-25", "action": "use_day_pattern", "scheduleTemplate": "sunday"},
        {"date": "2026-12-26", "action": "use_day_pattern", "scheduleTemplate": "saturday"},
        {"date": "2026-12-31", "action": "use_day_pattern", "scheduleTemplate": "sunday", "notAfter": "17:45"},
        {"date": "2027-01-01", "action": "use_day_pattern", "scheduleTemplate": "sunday"},
        {"date": "2027-01-06", "action": "use_day_pattern", "scheduleTemplate": "saturday"},
        {"date": "2027-03-25", "action": "use_day_pattern", "scheduleTemplate": "friday"},
        {"date": "2027-03-26", "action": "use_day_pattern", "scheduleTemplate": "saturday"},
        {"date": "2027-03-29", "action": "use_day_pattern", "scheduleTemplate": "sunday"},
    ],
}

TARGET_ROUTES = {
    "avajurmo", "enklingelinjen", "foglolinjen", "hitisalva", "hitisjurmo",
    "houtskarrutt", "iniorutt", "korporutt", "nagunorra", "nagusodra",
    "nagutvar", "norralinjen", "osnasava", "pargasrutt",
    "rymattylanreitti", "sodralinjen", "utorutt", "velkuanreitti",
    "velkuataivassalo",
}

FINFERRIES_TERMINALS = {
    "houtskarrutt": {"Själö", "Roslax", "Näsby", "TorsholmaI", "Kannvik", "Norrby"},
    "iniorutt": {"Kannvik", "Själö"},
    "nagunorra": {"Åvensor", "Lavarn", "Nagu"},
    "nagusodra": {"Kirjais"},
    "nagutvar": {"Hummelholm", "Pärnäs", "Kirjais"},
    "pargasrutt": {"Granvik"},
    "rymattylanreitti": {"Haapala"},
    "korporutt": {"Verkan"},
    "utorutt": {"Pärnäs", "Utö"},
    "velkuanreitti": {"Teersalo", "Hakkenpää"},
    "velkuataivassalo": {"Teersalo", "Hakkenpää"},
}

ALAND_TWO_TERMINAL_ROUTES = {
    "avajurmo": {"terminals": ["JurmoB", "Åva"], "tablePairs": [(0, 1, 2), (0, 4, 5)], "startRow": 2},
    "enklingelinjen": {"terminals": ["Kumlinge", "Enklinge"], "tablePairs": [(0, 1, 2), (0, 4, 5)], "startRow": 1},
    "osnasava": {"terminals": ["Vuosnainen", "Åva"], "tablePairs": [(0, 1, 2), (1, 0, 1)], "startRow": 2},
}

ALAND_DAY_GROUP_LABELS = {
    "Måndag": ["monday"],
    "Tisdag": ["tuesday", "wednesday", "thursday"],
    "Fredag": ["friday"],
    "Lördag": ["saturday"],
    "Söndag": ["sunday"],
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
    marker = re.search(r"(?<![A-Za-z])(xy|y\+\+|y\*\*|y\*|y|x)(?![A-Za-z])", source, re.I)
    if marker:
        result["callCondition"] = marker.group(0).lower()
    if source.startswith("~"):
        result["timeNature"] = "approximate"
    elif match and "(" in source[: match.start() + 1]:
        result["timeNature"] = "estimated_intermediate"
    annotation_source = source[match.end():] if match else source
    notes = re.findall(r"\*+|\++|\d+\)|[A-ZÅ]+\)", annotation_source)
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
        end_cutoff = rule.get("notAfter")
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
            if end_cutoff and departure and departure > end_cutoff:
                continue
            holiday_trip = copy.deepcopy(trip)
            holiday_trip["sourceTemplateId"] = trip["id"]
            holiday_trip["id"] = f"{rule['date']}-{trip['id']}"
            holiday_trip["operatingDate"] = rule["date"]
            holiday_trip.pop("operatingDays", None)
            if rule.get("forceCallCondition"):
                calls = holiday_trip.get("calls", [])
                if calls:
                    calls[0]["callCondition"] = rule["forceCallCondition"]
            selected.append(holiday_trip)
        for extra_index, extra in enumerate(rule.get("extraTrips", []), start=1):
            origin, departure, destination, arrival = extra
            extra_trip = {
                "id": f"{rule['date']}-{route['id']}-extra-{extra_index:02d}",
                "operatingDate": rule["date"],
                "normalizationStatus": "manually_normalized_holiday_exception",
                "calls": [
                    {"stop": origin, "time": departure, "timeNature": "published_departure", "callCondition": rule.get("forceCallCondition", "1")},
                    {"stop": destination, "time": arrival, "timeNature": "published_arrival"},
                ],
            }
            selected.append(extra_trip)
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


def source_time_tokens(value: object) -> list[str]:
    """Extract source times with their immediately following footnote markers."""
    if value in (None, ""):
        return []
    return re.findall(r"\d{1,2}:\d{2}(?:(?:[A-ZÅ]+|\d+)\))*", str(value))


def aland_row_day_group(value: object, current: list[str] | None) -> list[str] | None:
    text = str(value or "").strip()
    for label, days in ALAND_DAY_GROUP_LABELS.items():
        if text.startswith(label):
            return days
    return current


def normalized_two_terminal_trip(
    route_id: str, days: list[str], origin: str, destination: str,
    departure_source: str, arrival_source: str, sequence: int,
) -> dict:
    departure = parse_cell(departure_source) or {}
    arrival = parse_cell(arrival_source) or {}
    for parsed in (departure, arrival):
        annotations = parsed.get("sourceAnnotations", [])
        if "1)" in annotations:
            parsed["callCondition"] = "1"
        elif "2)" in annotations:
            parsed["callCondition"] = "2"
    departure_minutes = int(departure["time"][:2]) * 60 + int(departure["time"][3:])
    arrival_minutes = int(arrival["time"][:2]) * 60 + int(arrival["time"][3:])
    if arrival_minutes < departure_minutes:
        arrival["dayOffset"] = 1
    return {
        "id": f"{route_id}-normalized-{sequence:03d}",
        "operatingDays": "".join(
            str(index + 1) if day in days else "_"
            for index, day in enumerate(WEEKDAYS)
        ),
        "normalizationStatus": "machine_generated_from_two_terminal_source_table",
        "calls": [
            {"stop": origin, **departure, "timeNature": "published_departure"},
            {"stop": destination, **arrival, "timeNature": "published_arrival"},
        ],
    }


def normalize_aland_two_terminal(route: dict) -> list[dict]:
    """Normalize the small Åland two-terminal tables, including packed PDF rows."""
    spec = ALAND_TWO_TERMINAL_ROUTES[route["id"]]
    terminals = spec["terminals"]
    trips = []
    current_days = None
    primary_table = route["sourceTables"][0]
    for row_index in range(spec["startRow"], len(primary_table["rows"])):
        primary_row = primary_table["rows"][row_index]
        current_days = aland_row_day_group(primary_row[0] if primary_row else None, current_days)
        if not current_days:
            continue
        for table_index, departure_column, arrival_column in spec["tablePairs"]:
            table = route["sourceTables"][table_index]
            if row_index >= len(table["rows"]):
                continue
            row = table["rows"][row_index]
            # Packed extraction rows put both values in one cell, while ordinary
            # rows keep departure and arrival in adjacent cells.
            combined = " ".join(
                str(row[column] or "")
                for column in (departure_column, arrival_column)
                if column < len(row)
            )
            tokens = source_time_tokens(combined)
            if not tokens and table_index == 0 and departure_column == 1:
                tokens = source_time_tokens(row[0] if row else None)
            if len(tokens) % 2:
                continue
            if table_index == 0 and departure_column in {1, 4}:
                direction = 0 if departure_column == 1 else 1
            else:
                direction = table_index
            origin = terminals[direction]
            destination = terminals[1 - direction]
            for token_index in range(0, len(tokens), 2):
                trips.append(normalized_two_terminal_trip(
                    route["id"], current_days, origin, destination,
                    tokens[token_index], tokens[token_index + 1], len(trips) + 1,
                ))
    return merge_identical_trips(trips, route["id"])


def add_clock_minutes(value: str, minutes: int, day_offset: int = 0) -> tuple[str, int]:
    hour, minute = map(int, value.split(":"))
    absolute = day_offset * 1440 + hour * 60 + minute + minutes
    return f"{absolute // 60 % 24:02d}:{absolute % 60:02d}", absolute // 1440


def normalize_foglo(route: dict) -> list[dict]:
    """Normalize Föglö's departure-only table with its published 30 min crossing."""
    trips = []
    directions = [("Degerby", "Svinö"), ("Svinö", "Degerby")]
    for table, (origin, destination) in zip(route["sourceTables"][:2], directions):
        for day_index, day in enumerate(WEEKDAYS):
            tokens = []
            for row in table["rows"][2:]:
                if day_index < len(row):
                    tokens.extend(source_time_tokens(row[day_index]))
            seen = set()
            for source_value in tokens:
                parsed = parse_cell(source_value) or {}
                annotations = parsed.get("sourceAnnotations", [])
                if "1)" in annotations:
                    parsed["callCondition"] = "1"
                elif "2)" in annotations:
                    parsed["callCondition"] = "2"
                departure = parsed.get("time")
                if not departure or departure in seen:
                    continue
                seen.add(departure)
                departure_offset = 1 if departure < "03:00" else 0
                arrival, arrival_offset = add_clock_minutes(departure, 30, departure_offset)
                trips.append({
                    "id": f"foglolinjen-normalized-{len(trips) + 1:03d}",
                    "operatingDays": day_pattern(day),
                    "normalizationStatus": "machine_generated_from_departure_table",
                    "calls": [
                        {"stop": origin, **parsed, "dayOffset": departure_offset,
                         "timeNature": "published_departure"},
                        {"stop": destination, "time": arrival, "dayOffset": arrival_offset,
                         "timeNature": "estimated_from_published_crossing_duration",
                         "offsetMinutes": 30},
                    ],
                })
    return merge_identical_trips(trips, route["id"])


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
        elif route["id"] in ALAND_TWO_TERMINAL_ROUTES:
            generated = normalize_aland_two_terminal(route)
            if generated:
                method = "aland_two_terminal_tables"
        elif route["id"] == "foglolinjen":
            generated = normalize_foglo(route)
            if generated:
                method = "aland_departure_columns_with_crossing_duration"
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
