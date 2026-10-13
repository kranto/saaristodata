#!/usr/bin/env python3
"""Flatten structured connection trips into a runtime-neutral prediction catalog."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("report", type=Path)
    return parser.parse_args()


def published_time(call: dict) -> str | None:
    return call.get("departure") or call.get("time") or call.get("arrival")


def catalog_call(call: dict, occurrence: int) -> dict:
    result = {"stop": call["stop"], "occurrence": occurrence}
    value = published_time(call)
    if value:
        result["timing"] = {
            "kind": "published",
            "time": value,
            "dayOffset": call.get("dayOffset", 0),
        }
    elif "historicalEstimate" in call:
        estimate = call["historicalEstimate"]
        result["timing"] = {
            "kind": "historical_typical_and_range",
            "elapsedMinutes": {
                "typical": estimate["typicalMinutes"],
                "possible": estimate["possibleMinutes"],
            },
            "sampleSize": estimate["sampleSize"],
            "pathVariants": estimate["pathVariants"],
            "matchingMethod": estimate["matchingMethod"],
            "modelVersion": estimate["modelVersion"],
            "disclosureRequired": True,
        }
    elif "historicalRangeEstimate" in call:
        estimate = call["historicalRangeEstimate"]
        result["timing"] = {
            "kind": "historical_conservative_range",
            "elapsedMinutes": {"possible": estimate["possibleMinutes"]},
            "sampleSize": estimate["sampleSize"],
            "matchingMethod": estimate["matchingMethod"],
            "modelVersion": estimate["modelVersion"],
            "typicalTimeAvailable": False,
            "disclosureRequired": True,
        }
    else:
        result["timing"] = {"kind": "unavailable"}
    if "historicalCompletionEstimate" in call:
        completion = call["historicalCompletionEstimate"]
        result["historicalCompletion"] = {
            "scheduled": completion["scheduled"],
            "elapsedMinutes": {
                "possible": completion["possibleMinutes"],
            },
            "clockRange": completion["range"],
            "scheduleOffsetRangeMinutes": completion["scheduleOffsetRangeMinutes"],
            "sampleSize": completion["sampleSize"],
            "pathVariants": completion["pathVariants"],
            "matchingMethod": completion["matchingMethod"],
            "modelVersion": completion["modelVersion"],
            "shortIntermediateWaitsIncluded": True,
            "longWaitsExcluded": True,
            "typicalTimeAvailable": completion["typicalTimeAvailable"],
            "disclosureRequired": True,
        }
        if completion["typicalTimeAvailable"]:
            result["historicalCompletion"].update({
                "typical": completion["typical"],
                "typicalMinutes": completion["typicalMinutes"],
                "scheduleOffsetTypicalMinutes": completion[
                    "scheduleOffsetTypicalMinutes"
                ],
            })
    if call.get("callCondition"):
        result["callCondition"] = call["callCondition"]
    return result


def catalog_trip(route_id: str, trip: dict, service: dict) -> dict:
    occurrences = Counter()
    calls = []
    for call in trip.get("calls", []):
        occurrences[call["stop"]] += 1
        calls.append(catalog_call(call, occurrences[call["stop"]]))
    first_time = published_time(trip["calls"][0]) if trip.get("calls") else None
    return {
        "routeId": route_id,
        "tripId": trip["id"],
        **service,
        "startPier": trip["calls"][0]["stop"],
        "endPier": trip["calls"][-1]["stop"],
        "scheduledDeparture": first_time,
        "calls": calls,
    }


def catalog_route(route: dict) -> dict:
    result = {
        "routeId": route["id"],
        "provider": route.get("provider"),
    }
    for key in (
        "publicTimetableUrl",
        "serviceType",
        "classificationEvidence",
        "vessel",
        "vessels",
        "capacity",
        "contact",
        "booking",
        "callConditions",
        "callMarkerPolicy",
        "pierAccess",
        "travelerInformation",
        "departureAnnotations",
        "connections",
        "generalNotes",
        "onDemandExtra",
        "sourceAnnotations",
        "routingPolicy",
    ):
        if key in route:
            result[key] = route[key]
    return result


def main() -> None:
    args = parse_args()
    source = json.loads(args.source.read_text(encoding="utf-8"))
    trips = []
    no_service_dates = []
    for route in source["routes"]:
        if "tripNormalization" not in route:
            continue
        route_id = route["id"]
        for trip in route.get("trips", []):
            trips.append(catalog_trip(route_id, trip, {
                "serviceKind": "regular",
                "operatingDays": trip.get("operatingDays"),
            }))
        for override in route.get("holidayTripOverrides", []):
            if override["action"] == "no_service":
                no_service_dates.append({"routeId": route_id, "date": override["date"]})
                continue
            for trip in override.get("trips", []):
                trips.append(catalog_trip(route_id, trip, {
                    "serviceKind": "holiday_override",
                    "operatingDate": override["date"],
                    "sourceTemplateId": trip.get("sourceTemplateId"),
                }))
    counts = Counter(
        call["timing"]["kind"]
        for trip in trips
        for call in trip["calls"][1:]
    )
    completion_counts = Counter(
        (
            "typical_and_range"
            if call["historicalCompletion"].get("typicalTimeAvailable")
            else "range_only"
        )
        for trip in trips
        for call in trip["calls"]
        if "historicalCompletion" in call
    )
    output = {
        "schemaVersion": 1,
        "status": "experimental_not_for_current_application",
        "policy": {
            "publishedTimesAlwaysWin": True,
            "estimateApplication": "add elapsedMinutes to the actual departure time from startPier",
            "longIntermediateWaitsExcluded": True,
            "completionRangesIncludeShortIntermediateWaits": True,
            "historicalDisclosureRequired": True,
            "alandPublishedTimetableAuthoritative": True,
            "unspecifiedOriginRequiresSuggestedRoadAccess": True,
            "showAllApplicableTravelerInformation": True,
        },
        "routes": [
            catalog_route(route)
            for route in source["routes"]
            if "tripNormalization" in route
        ],
        "trips": trips,
        "noServiceDates": no_service_dates,
    }
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "trips": len(trips),
        "regularTrips": sum(item["serviceKind"] == "regular" for item in trips),
        "holidayTrips": sum(item["serviceKind"] == "holiday_override" for item in trips),
        "noServiceDates": len(no_service_dates),
        "internalCallTimings": dict(sorted(counts.items())),
        "historicalCompletionTimings": dict(sorted(completion_counts.items())),
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
