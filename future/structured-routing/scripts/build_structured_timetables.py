#!/usr/bin/env python3
"""Build the first structured timetable draft from locally accepted sources.

The output is deliberately source-faithful: timetable annotations are retained
verbatim and generated records stay unreviewed until compared with the source.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from datetime import date, datetime
from pathlib import Path


EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CHECKS = REPOSITORY_ROOT / "timetable-checks.json"
ORIGINALS = REPOSITORY_ROOT / ".timetable-checker" / "originals"
OUTPUT = EXPERIMENT_ROOT / "structured-timetables.json"
TRANSCRIPTIONS = EXPERIMENT_ROOT / "structured-timetable-transcriptions"

EXPIRED_PDF_SOURCES = {
    "finferries-houtskarrutt-houtskarin-reitti-talvi-19.8.2026-30.9.2026",
    "finferries-utorutt-uton-reitti-talvi-1.9.2026-30.9.2026",
    "finferries-velkuanreitti-velkuan-reitti-kesa-8.5.-13.9.2026",
    "finferries-velkuataivassalo-velkuan-reitti-kesa-8.5.-13.9.2026",
    "alandstrafiken-embarsund-8.6.2026",
    "alandstrafiken-passbaten",
    "alandstrafiken-seglinge-linfarja-1.1-13.9",
}

NON_ROUTING_SOURCES = {
    # Fuel-only compilation is not a passenger timetable.  Relevant fuel-trip
    # capacity effects belong to the actual line timetable instead.
    "alandstrafiken-bransleturlista-2026",
}

# Finferries uses "yhteysalus" for the multi-stop connection-vessel services,
# not for point-to-point road ferries.  Every journey on these routes is booked
# in the common booking system; a cell marker such as y additionally controls
# whether the vessel calls at that particular pier.
FINFERRIES_CONNECTION_VESSEL_ROUTES = {
    "hitisalva", "hitisjurmo", "houtskarrutt", "iniorutt", "nagunorra",
    "nagusodra", "nagutvar", "pargasrutt", "rymattylanreitti", "utorutt",
    "velkuanreitti", "velkuataivassalo",
}

FINFERRIES_ROAD_FERRY_ROUTES = {
    "iniokustavi", "kasnashitis",
}

DAY_NAMES = {
    "0": "sunday",
    "1": "monday",
    "2": "tuesday",
    "3": "wednesday",
    "4": "thursday",
    "5": "friday",
    "6": "saturday",
}

DAY_NUMBERS = {
    "monday": 1,
    "tuesday": 2,
    "wednesday": 3,
    "thursday": 4,
    "friday": 5,
    "saturday": 6,
    "sunday": 7,
}


def day_pattern(weekdays: list[str]) -> str:
    """Return an airline-style seven-character Monday-to-Sunday pattern."""
    included = {DAY_NUMBERS[day] for day in weekdays}
    return "".join(str(day) if day in included else "_" for day in range(1, 8))


def departure_calendar(source_id: str, weekdays: list[str], marker: str) -> dict:
    """Resolve source-specific departure markers into routing semantics."""
    effective_days = list(weekdays)
    conditions = []
    marker_lower = marker.lower()
    interpretation_status = "not_applicable" if not marker else "unresolved"

    if source_id == "finferries-hogsara-weekday":
        if "k+" in marker_lower:
            effective_days = ["wednesday"]
            conditions.append({
                "type": "weekday_override",
                "meaning": "only",
                "weekdays": ["wednesday"],
            })
            interpretation_status = "resolved"
        elif "k-" in marker_lower:
            effective_days = [day for day in weekdays if day != "wednesday"]
            conditions.append({
                "type": "weekday_override",
                "meaning": "except",
                "weekdays": ["wednesday"],
            })
            interpretation_status = "resolved"
        elif marker == "*":
            conditions.append({
                "type": "related_service",
                "mode": "bus",
                "relationship": "source_states_connection",
            })
            interpretation_status = "resolved"
    elif source_id == "finferries-hogsara-saturday" and "t" in marker_lower:
        conditions.append({
            "type": "booking_requirement",
            "requirement": "required",
            "annualPeriod": {"from": "11-01", "to": "04-30"},
            "bookingDeadline": {"time": "20:00", "sourceDoesNotSpecifyDayOffset": True},
            "phone": "+358407066291",
        })
        interpretation_status = "resolved"

    result = {
        "operatingDays": day_pattern(effective_days),
        "noteInterpretationStatus": interpretation_status,
    }
    if conditions:
        result["conditions"] = conditions
    return result


def clean_markup(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value).replace("\xa0", " ")
    return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in value.splitlines()).strip()


def iso_date(value: str) -> str | None:
    if not value:
        return None
    return value.split(" ", 1)[0]


def route_id(source_id: str) -> str:
    value = source_id.removeprefix("finferries-")
    for suffix in (
        "-special-sunday", "-early-weekend", "-weekday", "-weekend",
        "-saturday", "-sunday", "-holiday", "-source",
    ):
        if value.endswith(suffix):
            return value[: -len(suffix)]
    return value


def extract_row(source: dict, body: str) -> dict:
    row_match = re.search(r'<div class="ajax_timetable_row"(?P<attrs>.*?)>(?P<body>.*)</div>\s*</div>\s*</body>', body, re.S)
    if not row_match:
        raise ValueError("ajax_timetable_row puuttuu")
    attrs = row_match.group("attrs")
    row = row_match.group("body")

    def attr(name: str) -> str:
        match = re.search(rf'data-{name}="([^"]*)"', attrs)
        return html.unescape(match.group(1)).strip() if match else ""

    day_tokens = attr("days").split()
    weekdays = [DAY_NAMES[token] for token in day_tokens if token in DAY_NAMES]
    special_days = ["public_holiday"] if "99" in day_tokens else []
    title_match = re.search(r'<h3[^>]*>(.*?)(?:<button|<span class="effective_header")', row, re.S)
    title = clean_markup(title_match.group(1)) if title_match else ""

    columns = re.findall(r'<div class="column column--1-2">(.*?)(?=<div class="column column--1-2">|</div>\s*</div>)', row, re.S)
    directions = []
    free_text = []
    for column in columns:
        heading_match = re.search(r'<h4[^>]*>(.*?)</h4>', column, re.S)
        if not heading_match:
            continue
        heading = clean_markup(heading_match.group(1))
        times = []
        for item in re.findall(r'<li[^>]*>(.*?)</li>', column, re.S):
            text = clean_markup(item)
            match = re.match(r'^(\d{1,2}:\d{2})(.*)$', text)
            if not match:
                continue
            source_time = match.group(1).zfill(5)
            normalized_time = "00:00" if source_time == "24:00" else source_time
            marker = match.group(2).strip()
            times.append({
                "time": normalized_time,
                **({"dayOffset": 1, "sourceTime": source_time} if source_time == "24:00" else {}),
                **departure_calendar(source["id"], weekdays, marker),
                **({"noteRefs": [marker]} if marker else {}),
            })
        paragraphs = [clean_markup(p) for p in re.findall(r'<p[^>]*>(.*?)</p>', column, re.S)]
        paragraphs = [p for p in paragraphs if p]
        if times:
            directions.append({"name": heading, "departures": times})
        elif heading or paragraphs:
            free_text.extend(([heading] if heading else []) + paragraphs)

    all_paragraphs = [clean_markup(p) for p in re.findall(r'<p[^>]*>(.*?)</p>', row, re.S)]
    notes = []
    seen = set(free_text)
    for paragraph in all_paragraphs:
        if paragraph and paragraph not in seen:
            notes.append(paragraph)
            seen.add(paragraph)

    if directions:
        service = {"type": "scheduled_departures", "directions": directions}
    else:
        text = "\n".join(free_text + notes)
        break_text = re.split(r'TAUOT\s*/\s*PAUSER\s*/\s*BREAKS:', text, flags=re.I)
        break_text = break_text[-1] if len(break_text) > 1 else text
        breaks = [
            {"start": f"{h1.zfill(2)}:{m1}", "end": f"{h2.zfill(2)}:{m2}"}
            for h1, m1, h2, m2 in re.findall(r'(\d{1,2})[.:](\d{2})\s*[–-]\s*(\d{1,2})[.:](\d{2})', break_text)
        ]
        operating_windows = []
        for line in text.splitlines():
            match = re.match(r'^([^\d\n]+?)\s+(\d{1,2})[.:](\d{2})\s*[–-]\s*(\d{1,2})[.:](\d{2})$', line.strip())
            if match and "TAUOT" not in line.upper():
                operating_windows.append({
                    "sourceLabel": match.group(1).strip(),
                    "start": f"{match.group(2).zfill(2)}:{match.group(3)}",
                    "end": f"{match.group(4).zfill(2)}:{match.group(5)}",
                })
        service = {
            "type": "continuous_or_on_demand",
            "description": text,
            **({"operatingWindows": operating_windows} if operating_windows else {}),
            **({"breaks": breaks} if breaks else {}),
        }

    return {
        "id": source["id"],
        "routeId": route_id(source["id"]),
        "provider": "finferries",
        "calendar": {
            "validFrom": iso_date(attr("effective-from")),
            "validTo": iso_date(attr("effective-to")),
            "weekdays": weekdays,
            "specialDays": special_days,
            "sourceLabel": title,
        },
        "service": service,
        "notes": notes,
        "source": {
            "sourceId": source["id"],
            "url": source["url"],
            "sha256": source["fingerprint"]["sha256"],
            "localFile": str((ORIGINALS / "finferries" / f'{source["id"]}.html').relative_to(REPOSITORY_ROOT)),
        },
        "review": {
            "status": "generated_unreviewed",
            "method": "finferries_html",
        },
    }


def group_routes(schedules: list[dict]) -> list[dict]:
    """Hide source-page fragmentation behind route-level timetables."""
    grouped = {}
    for schedule in schedules:
        route = grouped.setdefault(schedule["routeId"], {
            "id": schedule["routeId"],
            "provider": schedule["provider"],
            "departures": {},
            "continuousServices": [],
            "notes": [],
            "sources": [],
            "review": {"status": "generated_unreviewed"},
        })
        route["sources"].append(schedule["source"])
        route["notes"].extend(
            {"sourceId": schedule["id"], "text": note}
            for note in schedule["notes"]
        )

        calendar = schedule["calendar"]
        if schedule["service"]["type"] == "continuous_or_on_demand":
            route["continuousServices"].append({
                **schedule["service"],
                "validFrom": calendar["validFrom"],
                "validTo": calendar["validTo"],
                "operatingDays": day_pattern(calendar["weekdays"]),
                "specialDays": calendar["specialDays"],
                "sourceId": schedule["id"],
            })
            continue

        for direction in schedule["service"]["directions"]:
            for departure in direction["departures"]:
                key = (direction["name"], departure["time"], departure.get("dayOffset", 0))
                item = route["departures"].setdefault(key, {
                    "from": direction["name"],
                    "time": departure["time"],
                    **({"dayOffset": departure["dayOffset"], "sourceTime": departure["sourceTime"]} if departure.get("dayOffset") else {}),
                    "operations": [],
                })
                item["operations"].append({
                    "validFrom": calendar["validFrom"],
                    "validTo": calendar["validTo"],
                    "operatingDays": departure["operatingDays"],
                    "specialDays": calendar["specialDays"],
                    "noteInterpretationStatus": departure["noteInterpretationStatus"],
                    **({"conditions": departure["conditions"]} if departure.get("conditions") else {}),
                    **({"noteRefs": departure["noteRefs"]} if departure.get("noteRefs") else {}),
                    "sourceId": schedule["id"],
                })

    routes = []
    for route in grouped.values():
        route["departures"] = sorted(
            route["departures"].values(),
            key=lambda item: (item["from"], item.get("dayOffset", 0), item["time"]),
        )
        route["sources"] = sorted(route["sources"], key=lambda item: item["sourceId"])
        routes.append(route)
    return sorted(routes, key=lambda item: item["id"])


def build() -> dict:
    checks = json.loads(CHECKS.read_text())
    as_of_date = date.today()
    schedules = []
    unconverted = []
    expired_source_count = 0
    for source in checks["sources"]:
        local = ORIGINALS / source["provider"] / f'{source["id"]}.{source["kind"]}'
        if source["id"] in EXPIRED_PDF_SOURCES:
            expired_source_count += 1
            continue
        if source["id"] in NON_ROUTING_SOURCES or (
            source["kind"] == "html" and source["id"].endswith("-source")
        ):
            continue
        if source["provider"] == "finferries" and source["kind"] == "html":
            body = local.read_text(errors="replace")
            if re.search(r'<li[^>]*>\s*\d{1,2}:\d{2}', body) or re.search(r'liikennöi tarvittaessa|trafikerar vid behov|runs when needed', html.unescape(body), re.I):
                schedule = extract_row(source, body)
                valid_to = schedule["calendar"]["validTo"]
                if valid_to and date.fromisoformat(valid_to) < as_of_date:
                    expired_source_count += 1
                    continue
                schedules.append(schedule)
                continue
        unconverted.append({
            "sourceId": source["id"],
            "provider": source["provider"],
            "kind": source["kind"],
            "url": source["url"],
            "sha256": source["fingerprint"]["sha256"],
            "reason": "requires_pdf_transcription" if source["kind"] == "pdf" else "no_active_departures",
        })

    routes = group_routes(schedules)
    routes_by_id = {route["id"]: route for route in routes}
    sources_by_id = {source["id"]: source for source in checks["sources"]}
    transcription_count = 0
    if TRANSCRIPTIONS.exists():
        for path in sorted(TRANSCRIPTIONS.glob("*.json")):
            transcription = json.loads(path.read_text())
            source = sources_by_id[transcription["sourceId"]]
            transcription["validPeriods"] = [
                period for period in transcription.get("validPeriods", [])
                if date.fromisoformat(period["validTo"]) >= as_of_date
            ]
            transcription["holidayExceptions"] = [
                item for item in transcription.get("holidayExceptions", [])
                if date.fromisoformat(item["date"]) >= as_of_date
            ]
            active_trips = []
            for trip in transcription.get("trips", []):
                if "validPeriods" in trip:
                    trip["validPeriods"] = [
                        period for period in trip["validPeriods"]
                        if date.fromisoformat(period["validTo"]) >= as_of_date
                    ]
                    if not trip["validPeriods"]:
                        continue
                active_trips.append(trip)
            transcription["trips"] = active_trips
            unconverted = [item for item in unconverted if item["sourceId"] != source["id"]]
            if not transcription["validPeriods"]:
                expired_source_count += 1
                continue
            route = routes_by_id.setdefault(transcription["routeId"], {
                "id": transcription["routeId"],
                "provider": transcription["provider"],
                "departures": [],
                "continuousServices": [],
                "notes": [],
                "sources": [],
                "review": transcription["review"],
            })
            route["review"] = transcription["review"]
            route["sources"].append({
                "sourceId": source["id"],
                "url": source["url"],
                "sha256": source["fingerprint"]["sha256"],
                "localFile": str((ORIGINALS / source["provider"] / f'{source["id"]}.{source["kind"]}').relative_to(REPOSITORY_ROOT)),
            })
            for key in (
                "vessel", "vessels", "sourceLanguageAuthority",
                "languageConflictPolicy", "validPeriods", "booking",
                "callConditions", "departureAnnotations", "holidayExceptions", "capacity", "trips",
                "generalNotes", "onDemandExtra", "sourceAnnotations",
                "annualSchedulePattern", "extractionDiagnostics",
                "sourceTables", "sourcePageText",
                "serviceRole",
                "routeApplications",
                "routingPolicy", "canonicalStopNames", "sourceRowExpansions",
                "sourceRowExpansionPolicy",
                "timeNotationPolicy",
                "sourceTableCorrections",
                "stopAliases",
                "connections",
            ):
                if key in transcription:
                    route[key] = transcription[key]
            transcription_count += 1
    routes = sorted(routes_by_id.values(), key=lambda item: item["id"])
    for route in routes:
        if route["provider"] == "finferries" and route["id"] in FINFERRIES_ROAD_FERRY_ROUTES:
            route["serviceType"] = "road_ferry"
            route["classificationEvidence"] = {
                "geoJsonSubtype": "conn2",
                "terminalCount": 2,
                "bookingRuleInheritedFromConnectionVessels": False,
            }
        if route["provider"] == "finferries" and route["id"] in FINFERRIES_CONNECTION_VESSEL_ROUTES:
            route["serviceType"] = "connection_vessel"
            route["classificationEvidence"] = {
                "geoJsonSubtype": "conn4",
                "bookingRuleInheritedFromConnectionVessels": True,
            }
            route["booking"] = {
                **route.get("booking", {}),
                "requiredForAllTrips": True,
                "url": "https://booking.finferries.fi/",
            }
            route["callMarkerPolicy"] = {
                "journeyReservationIsSeparate": True,
                "y": "call_at_pier_requires_advance_order",
                "x": "call_at_pier_when_needed_without_separate_order",
                "expectedUsage": "y is expected at bookable intermediate calls; terminal times may omit it because every connection-vessel journey already requires a reservation",
            }
    return {
        "schemaVersion": 1,
        # Use the accepted source set timestamp so unchanged inputs produce an
        # identical version-controlled artifact.
        "generatedAt": checks["acceptedAt"],
        "status": "draft",
        "timingEstimatePolicy": {
            "field": "historicalEstimate",
            "basis": "historical_observations",
            "role": "advisory",
            "scheduledTimesTakePrecedence": True,
            "disclosureRequired": True,
            "disclosureKey": "timetable.historicalEstimateDisclaimer",
        },
        "stopDisplayPolicy": {
            "primaryName": "selected_locale",
            "secondaryDomesticName": "when_names_are_not_readily_recognizable_as_the_same_place",
            "duplicateNameQualifier": "search_results_only_when_same-name_stops_from_different_routes_may_be_confused",
            "ordinaryRouteAndMapViewsUseQualifier": False,
            "duplicateNameTestCases": ["Berghamn"],
        },
        "routes": routes,
        "unconvertedSources": unconverted,
        "statistics": {
            "routeCount": len(routes),
            "convertedSourceCount": len(schedules) + transcription_count,
            "manualTranscriptionCount": transcription_count,
            "tripCount": sum(len(route.get("trips", [])) for route in routes),
            "scheduledDepartureCount": sum(
                len(route["departures"])
                for route in routes
            ),
            "unconvertedSourceCount": len(unconverted),
            "expiredSourceCount": expired_source_count,
            "unresolvedDepartureNoteCount": sum(
                operation["noteInterpretationStatus"] == "unresolved"
                for route in routes
                for departure in route["departures"]
                for operation in departure["operations"]
            ),
        },
    }


def validate(data: dict) -> list[str]:
    errors = []
    ids = set()
    for route in data["routes"]:
        if route["id"] in ids:
            errors.append(f'duplicate id: {route["id"]}')
        ids.add(route["id"])
        for departure in route["departures"]:
            if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', departure["time"]):
                errors.append(f'{route["id"]}: invalid time {departure["time"]}')
            for operation in departure["operations"]:
                for key in ("validFrom", "validTo"):
                    if operation[key]:
                        try:
                            datetime.strptime(operation[key], "%Y-%m-%d")
                        except ValueError:
                            errors.append(f'{route["id"]}: invalid {key}')
        known_conditions = set(route.get("callConditions", {}))
        trip_ids = set()
        for trip in route.get("trips", []):
            if trip["id"] in trip_ids:
                errors.append(f'{route["id"]}: duplicate trip id {trip["id"]}')
            trip_ids.add(trip["id"])
            if not re.fullmatch(r'[1_][2_][3_][4_][5_][6_][7_]', trip["operatingDays"]):
                errors.append(f'{route["id"]}/{trip["id"]}: invalid operatingDays')
            if len(trip["calls"]) < 2:
                errors.append(f'{route["id"]}/{trip["id"]}: fewer than two calls')
            for call in trip["calls"]:
                refs = (
                    ([call["callCondition"]] if call.get("callCondition") else [])
                    + call.get("additionalConditions", [])
                    + call.get("conditions", [])
                )
                for ref in refs:
                    if ref not in known_conditions:
                        errors.append(f'{route["id"]}/{trip["id"]}: unknown call condition {ref}')
                for value in ([call["time"]] if call.get("time") else []) + call.get("timeAlternatives", []):
                    if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', value):
                        errors.append(f'{route["id"]}/{trip["id"]}: invalid call time {value}')
                for value in call.get("timeRange", {}).values():
                    if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', value):
                        errors.append(f'{route["id"]}/{trip["id"]}: invalid call time range {value}')
                estimate = call.get("historicalEstimate")
                if estimate:
                    if estimate.get("basis") != "historical_observations":
                        errors.append(f'{route["id"]}/{trip["id"]}: invalid estimate basis')
                    if estimate.get("disclosureRequired") is not True:
                        errors.append(f'{route["id"]}/{trip["id"]}: estimate disclosure is not required')
                    for value in estimate.get("range", {}).values():
                        if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', value):
                            errors.append(f'{route["id"]}/{trip["id"]}: invalid estimate time {value}')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify that the generated file is current")
    args = parser.parse_args()
    data = build()
    errors = validate(data)
    if errors:
        raise SystemExit("\n".join(errors))
    rendered = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUTPUT.exists():
            raise SystemExit(f"missing {OUTPUT.name}")
        existing = json.loads(OUTPUT.read_text())
        data.pop("generatedAt", None)
        existing.pop("generatedAt", None)
        if existing != data:
            raise SystemExit(f"{OUTPUT.name} is out of date")
    else:
        OUTPUT.write_text(rendered)
        print(f"wrote {OUTPUT.name}: {data['statistics']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
