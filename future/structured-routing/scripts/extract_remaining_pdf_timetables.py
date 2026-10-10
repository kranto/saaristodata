#!/usr/bin/env python3
"""Extract every remaining active PDF timetable into source-faithful JSON tables.

This is deliberately a lossless intermediate representation.  It removes PDF
layout as a dependency, but does not pretend that every visual table has been
split into routing-ready trips.  The review queue records that semantic work.
"""

from __future__ import annotations

import json
from pathlib import Path

import pdfplumber


EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
ORIGINALS = REPOSITORY_ROOT / ".timetable-checker" / "originals"
OUTPUT = EXPERIMENT_ROOT / "structured-timetable-transcriptions"

# Pages are one-based.  Only periods that are active on 2026-10-10 or later are
# included.  Reused Åland timetable templates point to the current source page.
SOURCES = {
    # Finferries
    "finferries-hitisalva-hiittisten-itainen-reitti-talviaikataulu-2026": ("hitisalva", "finferries", "2026-01-01", "2026-12-31", None),
    "finferries-houtskarrutt-houtskarin-reitti-talvi-1.10.2026-30.4.2027": ("houtskarrutt", "finferries", "2026-10-01", "2027-04-30", None),
    "finferries-iniokustavi-inio-kustavi-talvi-1.1.-7.5.2026-ja-14.9.-31.12.2026": ("iniokustavi", "finferries", "2026-09-14", "2026-12-31", None),
    "finferries-iniorutt-inion-lisareitti-talvi-19.8.2026-30.4.2027": ("iniorutt", "finferries", "2026-08-19", "2027-04-30", None),
    "finferries-kasnashitis-kasnas-hiittinen-aurora-talvi-1.1.-31.12.2026": ("kasnashitis", "finferries", "2026-01-01", "2026-12-31", None),
    "finferries-nagunorra-nauvon-pohjoinen-reitti-talvi-11.8.2026-30.5.2027": ("nagunorra", "finferries", "2026-08-11", "2027-05-30", None),
    "finferries-nagusodra-nauvon-etelainen-reitti-talvi-1.10.2026-24.3.2027": ("nagusodra", "finferries", "2026-10-01", "2027-03-24", None),
    "finferries-nagutvar-nauvon-poikittainen-reitti-talvi-1.10.2026-24.3.2027": ("nagutvar", "finferries", "2026-10-01", "2027-03-24", None),
    "finferries-pargasrutt-paraisten-reittialue-talvi-1.9.2026-31.5.2027": ("pargasrutt", "finferries", "2026-09-01", "2027-05-31", None),
    "finferries-rymattylanreitti-rymattylan-reitti-28.9.2026-2.5.2027": ("rymattylanreitti", "finferries", "2026-09-28", "2027-05-02", None),
    "finferries-utorutt-uton-reitti-talvi-1.10.2026-31.5.2027": ("utorutt", "finferries", "2026-10-01", "2027-05-31", None),
    "finferries-velkuanreitti-velkuan-reitti-talvi-14.9.2026-6.5.2027": ("velkuanreitti", "finferries", "2026-09-14", "2027-05-06", None),
    "finferries-velkuataivassalo-velkuan-reitti-talvi-14.9.2026-6.5.2027": ("velkuataivassalo", "finferries", "2026-09-14", "2027-05-06", None),
    # Ålandstrafiken
    "alandstrafiken-ava-jurmo-25.08": ("avajurmo", "alandstrafiken", "2026-09-14", "2026-12-31", [3]),
    "alandstrafiken-ava-osnas-1.9.2026": ("osnasava", "alandstrafiken", "2026-09-14", "2026-12-31", [3]),
    "alandstrafiken-enklinge-kumlinge-14.9.2026": ("enklingelinjen", "alandstrafiken", "2026-09-14", "2026-12-31", [3, 4]),
    "alandstrafiken-foglo-27.5.2026": ("foglolinjen", "alandstrafiken", "2026-09-01", "2026-12-31", [1]),
    "alandstrafiken-huto-11.9.2026": ("norralinjen", "alandstrafiken", "2026-09-14", "2026-12-31", [5, 6]),
    "alandstrafiken-linfarjor": ("alandsvajerfarjor", "alandstrafiken", "2026-01-01", "2026-12-31", [1]),
    "alandstrafiken-seglinge-linfarja-14.9-31.12-1": ("seglingelinjen", "alandstrafiken", "2026-09-14", "2026-12-31", [1]),
    "alandstrafiken-simskala-1": ("simskalalinjen", "alandstrafiken", "2026-01-01", "2026-12-31", [1]),
    "alandstrafiken-sodra-linjen-30.9.2026": ("sodralinjen", "alandstrafiken", "2026-09-28", "2027-01-01", [9, 10, 11]),
    "alandstrafiken-toftolinjen-inkl-avvikelser": ("toftolinjen", "alandstrafiken", "2026-01-01", "2026-12-31", [1]),
    # Saaristolinjat
    "saaristolinjat-korppoon-reittialue-2026-09-01": ("korporutt", "saaristolinjat", "2026-09-01", "2027-06-01", [1]),
}


def clean(value):
    if value is None:
        return None
    value = "\n".join(line.strip() for line in str(value).replace("\xa0", " ").splitlines())
    return value.strip()


def main() -> None:
    OUTPUT.mkdir(exist_ok=True)
    for source_id, (route_id, provider, valid_from, valid_to, selected_pages) in SOURCES.items():
        path = ORIGINALS / provider / f"{source_id}.pdf"
        tables = []
        page_text = []
        with pdfplumber.open(path) as pdf:
            pages = selected_pages or list(range(1, len(pdf.pages) + 1))
            for page_number in pages:
                page = pdf.pages[page_number - 1]
                extracted = page.extract_tables()
                for table_index, rows in enumerate(extracted, 1):
                    tables.append({
                        "page": page_number,
                        "tableIndex": table_index,
                        "rows": [[clean(cell) for cell in row] for row in rows],
                    })
                text = clean(page.extract_text() or "")
                if text:
                    page_text.append({"page": page_number, "text": text})

        data = {
            "routeId": route_id,
            "provider": provider,
            "sourceLanguageAuthority": "sv" if provider == "alandstrafiken" else "fi",
            "languageConflictPolicy": (
                "Åland source: Swedish is the default authority when language versions conflict"
                if provider == "alandstrafiken" else
                "Mainland Finland source: Finnish is the default authority when language versions conflict"
            ),
            "sourceId": source_id,
            "review": {
                "status": "machine_extracted_requires_semantic_review",
                "method": "pdfplumber table extraction",
                "sourcePages": pages,
                "routingReady": False,
            },
            "validPeriods": [{"validFrom": valid_from, "validTo": valid_to}],
            "sourceTables": tables,
            "sourcePageText": page_text,
            "extractionDiagnostics": {
                "tableCount": len(tables),
                "rowCount": sum(len(table["rows"]) for table in tables),
                "losslessIntent": True,
            },
        }
        if source_id == "finferries-hitisalva-hiittisten-itainen-reitti-talviaikataulu-2026":
            stops_morning = [
                "Dalsbruk", "Bolax", "Bötesö", "Grönvik", "Djupö",
                "Stora Ängesö", "Vänoxaby", "Vänoxa släten", "Biskopsö",
                "Dalsbruk",
            ]
            stops_afternoon = [
                "Dalsbruk", "Stora Ängesö", "Biskopsö", "Vänoxa släten",
                "Vänoxaby", "Grönvik", "Djupö", "Bötesö", "Bolax",
            ]
            data.update({
                "serviceRole": {
                    "primaryPurpose": "school_transport",
                    "routingInterpretation": "The morning service is a bookable round trip from Dalsbruk via ordered island stops back to Dalsbruk at 08:05. The unpublished departure may be around 06:00 or earlier. The 15:00 service runs only outbound from Dalsbruk to the islands.",
                    "stopOrderPolicy": "published_order_is_expected",
                    "stopOrderConfidence": "high",
                    "bookingControlsCallOccurrenceNotRouteOrder": True,
                },
                "booking": {
                    "defaultPolicy": "required",
                    "deadline": {
                        "relativeTo": "previous_operating_day",
                        "time": "17:30",
                    },
                    "channel": "operator_booking_system",
                    "earliestBookingDaysBefore": 14,
                    "loadingReadinessMinutesBefore": 10,
                },
                "callConditions": {
                    "y": {
                        "type": "booking_required",
                        "meaning": "The call is operated only when ordered.",
                    }
                },
                "trips": [
                    {
                        "id": "weekday-morning",
                        "operatingDays": "12345__",
                        "bookingRequired": True,
                        "tripRole": "school_morning_inbound",
                        "routingDirection": "dalsbruk_islands_dalsbruk_round_trip",
                        "publishedStartTime": False,
                        "calls": [
                            {
                                "stop": stop,
                                **({"time": "08:05"} if index == len(stops_morning) - 1 else {}),
                                **({"callCondition": "y"} if index < len(stops_morning) - 1 else {}),
                                **({"historicalEstimateCandidate": True} if index < len(stops_morning) - 1 else {}),
                            }
                            for index, stop in enumerate(stops_morning)
                        ],
                    },
                    {
                        "id": "weekday-afternoon",
                        "operatingDays": "12345__",
                        "bookingRequired": True,
                        "tripRole": "school_afternoon_outbound",
                        "routingDirection": "dalsbruk_to_islands_only",
                        "reverseJourneyAvailable": False,
                        "calls": [
                            {
                                "stop": stop,
                                **({"time": "15:00"} if index == 0 else {}),
                                **({"callCondition": "y"} if index > 0 else {}),
                                **({"historicalEstimateCandidate": True} if index > 0 else {}),
                            }
                            for index, stop in enumerate(stops_afternoon)
                        ],
                    },
                ],
                "generalNotes": [
                    "All trips must be booked through the booking system.",
                    "The service primarily carries schoolchildren. The morning circuit starts in Dalsbruk, visits ordered island stops and returns to Dalsbruk at 08:05; it can also carry passengers from Dalsbruk to the islands, but the early departure time is not published.",
                    "The 15:00 afternoon circuit runs from Dalsbruk to the islands only. The timetable does not provide an afternoon journey from the islands to Dalsbruk.",
                    "The published stop order is expected to remain nearly constant; bookings determine which requested calls are made, not a freely optimized stop order.",
                    "The PDF publishes only the morning return time to Dalsbruk and the afternoon departure time from Dalsbruk; other call times are not published.",
                    "Unpublished call times may later receive advisory ranges based on historical observations, never as operator-published times.",
                ],
            })
        if source_id == "saaristolinjat-korppoon-reittialue-2026-09-01":
            common = {
                "operatingDays": "_2_____",
                "serviceRole": "school_transport",
                "passengerEligibility": {
                    "default": "school_transport_only",
                    "generalPublic": "not_normally_available",
                    "operatorExceptionPossible": True,
                },
                "bookingRequired": True,
                "bookingDeadline": {
                    "relativeTo": "previous_day",
                    "time": "15:00",
                },
                "vesselAlternatives": ["M/S Fiskö", "taxi_boat"],
                "vesselSelectionBasis": "not_published",
                "vehiclePolicy": {
                    "M/S Fiskö": "vehicle_space_must_be_reserved",
                    "taxi_boat": "vehicles_not_supported",
                    "routingRequirement": "assigned_vessel_must_be_known_before_offering_vehicle_transport",
                },
            }
            data.update({
                "booking": {
                    "defaultPolicy": "required_for_y_services",
                    "deadline": {"relativeTo": "previous_day", "time": "15:00"},
                    "phone": "+358447618000",
                    "vehicleSpace": {
                        "role": "passenger_information_only",
                        "affectsRouting": False,
                        "reservationWindow": {
                            "opensDaysBeforeDeparture": 30,
                            "closesDaysBeforeDeparture": 7,
                        },
                        "interpretation": (
                            "Vehicle space must be reserved no earlier than one month "
                            "and no later than one week before departure."
                        ),
                        "sourceWordingAmbiguous": True,
                    },
                },
                "trips": [
                    {
                        "id": "tuesday-school-morning-storpensar",
                        **common,
                        "calls": [
                            {"stop": "Korppoo", "time": "07:30"},
                            {"stop": "Storpensar", "time": "08:00"},
                            {"stop": "Korppoo", "time": "08:45"},
                        ],
                    },
                    {
                        "id": "tuesday-school-afternoon-storpensar",
                        **common,
                        "calls": [
                            {"stop": "Korppoo", "time": "15:10"},
                            {"stop": "Storpensar", "time": "15:40"},
                            {"stop": "Korppoo", "time": "16:40"},
                        ],
                    },
                ],
                "generalNotes": [
                    "On Tuesdays only school transport is operated. General-public passengers are not normally eligible.",
                    "The two Tuesday Korppoo–Storpensar round trips are operated by either M/S Fiskö or a taxi boat. The source does not state how the vessel is selected.",
                    "Vehicle transport can only be offered when M/S Fiskö is assigned and vehicle space has been reserved; a taxi boat does not carry vehicles.",
                    "As non-routing passenger information, vehicle-space reservations are interpreted as available from one month until one week before departure. The source's separate confirmation wording is ambiguous and is not modeled as an additional routing condition.",
                ],
            })
            data["sourceTableCorrections"] = [{
                "page": 1,
                "location": "Sunday column before 2026-11-02",
                "sourceIssue": "The visual grouping leaves the relationship between the Österskär and Berghamn times ambiguous.",
                "interpretation": {
                    "separateTrips": True,
                    "trips": [{
                        "id": "sunday-osterskar",
                        "from": "Korppoo",
                        "departure": "10:00",
                        "destination": "Österskär",
                        "publishedDestinationTime": "12:00",
                        "destinationTimeConfidence": "source_value_but_operationally_uncertain",
                        "historicalEstimateCandidate": True,
                        "expectedTypicalDurationMinutes": 90,
                        "returnMustPrecede": "13:00",
                        "operatesUntil": "2026-11-01",
                        "calls": [
                            {"stop": "Brunskär", "callCondition": "y"},
                            {"stop": "Kälö", "callCondition": "y"},
                            {"stop": "Österskär", "publishedTime": "12:00", "callCondition": "y"},
                        ],
                        "seasonalSuspension": {
                            "validFrom": "2026-11-02",
                            "validTo": "2027-04-30",
                            "appliesToEntireTrip": True,
                        },
                    }, {
                        "id": "sunday-berghamn",
                        "from": "Korppoo",
                        "departure": "13:00",
                        "destination": "Berghamn",
                        "publishedDestinationTime": "14:00",
                        "returnTo": "Korppoo",
                        "publishedReturnTime": "15:30",
                    }],
                },
            }]
            data["sourceRowExpansions"] = {
                "Brunskär/Kälö": {
                    "stops": ["Brunskär", "Kälö"],
                    "semantics": "two_separate_optional_calls",
                    "inheritCellMarkersForEachStop": True,
                    "bothCallsBelongTo": "sunday-osterskar",
                    "bothCallsMayOccurOnSameTrip": True,
                }
            }
        if source_id == "alandstrafiken-linfarjor":
            data["routeApplications"] = [
                {
                    "routeId": "seglingelinjen",
                    "normalScheduleContribution": "none_redundant_with_route_timetable",
                    "holidayExceptions": [{
                        "date": "2026-12-24",
                        "regularTrafficUntil": "18:00",
                        "onOrderDepartures": ["19:00", "20:00", "21:00", "22:00", "23:00", "00:00"],
                        "bookingDeadline": "18:00",
                        "returnFrom": "Snäckö",
                        "returnTiming": "immediately_after_arrival",
                    }, {
                        "date": "2026-12-25",
                        "trafficResumes": "06:00",
                    }],
                },
                {
                    "routeId": "simskalalinjen",
                    "normalScheduleContribution": "none_redundant_with_route_timetable",
                    "holidayExceptions": [{
                        "date": "2026-12-24",
                        "trafficEnds": "22:00",
                        "onOrderDepartures": ["23:00", "00:00", "01:00"],
                    }, {
                        "date": "2026-12-25",
                        "trafficResumes": "06:00",
                    }],
                },
                {
                    "routeId": "toftolinjen",
                    "normalScheduleContribution": "none_redundant_with_route_timetable",
                    "holidayExceptions": [{
                        "date": "2026-12-24",
                        "trafficEnds": "00:00",
                        "onOrderDepartures": ["01:00"],
                    }, {
                        "date": "2026-12-25",
                        "trafficResumes": "06:00",
                    }],
                },
                {
                    "routeId": "embarsundslinjen",
                    "normalScheduleContribution": "active_source",
                    "validPeriods": [{"validFrom": "2026-09-01", "validTo": "2026-12-31"}],
                    "service": {
                        "type": "continuous_or_on_demand",
                        "operation": "on_demand",
                        "scheduledTimetable": False,
                    },
                    "holidayExceptions": [{
                        "date": "2026-12-24",
                        "trafficEnds": "22:00",
                        "onOrderDepartures": ["23:00", "00:00", "01:00"],
                    }, {
                        "date": "2026-12-25",
                        "trafficResumes": "06:00",
                    }],
                },
            ]
        if source_id == "alandstrafiken-toftolinjen-inkl-avvikelser":
            data["routingPolicy"] = {
                "weekendAndHolidayNightMorningService": {
                    "operatingDays": "_____67",
                    "alsoAppliesOnPublicHolidays": True,
                    "validFromTime": "22:00",
                    "validToTime": "07:50",
                    "operation": "on_demand_without_timetable",
                    "scheduledDeparturesSuppressed": {
                        "from": "06:00",
                        "to": "07:45",
                        "intervalMinutes": 15,
                    },
                    "firstScheduledDepartureAfterWindow": "08:00",
                    "interpretation": (
                        "The printed 06:00-07:45 quarter-hour entries marked 2) "
                        "are not scheduled weekend or holiday departures. They are "
                        "covered by the continuous on-demand period ending at 07:50."
                    ),
                }
            }
            data["holidayExceptions"] = [
                {
                    "date": "2026-12-24",
                    "baseSchedule": "sunday",
                    "cancelledBreak": {
                        "from": "17:55",
                        "to": "18:30",
                    },
                    "lastScheduledDeparture": "21:45",
                    "onDemandService": {
                        "from": "22:00",
                        "to": "00:00",
                    },
                },
                {
                    "date": "2026-12-25",
                    "specialOrderedDeparture": "01:00",
                    "noOtherServiceBefore": "06:00",
                    "onDemandService": {
                        "from": "06:00",
                        "to": "07:50",
                    },
                    "scheduledServiceResumes": "08:00",
                },
            ]
        if source_id == "alandstrafiken-simskala-1":
            data["canonicalStopNames"] = {
                "Timskär": {
                    "sourceContextName": "Simskäla",
                },
                "Vattungsrevet": {
                    "sourceContextName": "Sandö",
                },
            }
            data["routingPolicy"] = {
                "publishedDirection": {
                    "from": "Timskär",
                    "to": "Vattungsrevet",
                    "usesPublishedTimes": True,
                },
                "returnDirection": {
                    "from": "Vattungsrevet",
                    "to": "Timskär",
                    "departureOffsetMinutesApproximate": 7,
                    "timeNature": "estimated_from_published_Timskär_departure",
                    "serviceActivation": {
                        "passengerMustBeAtPierByPublishedTimskärTime": True,
                        "alternative": "call_ferry_by_published_Timskär_time",
                        "phone": "+3584573798869",
                    },
                    "operatorMayDelayReturnMinutes": {
                        "commercialTraffic": 10,
                        "otherTraffic": 5,
                    },
                },
            }
        if source_id == "alandstrafiken-sodra-linjen-30.9.2026":
            data["validPeriods"] = [
                {
                    "validFrom": "2026-09-28",
                    "validTo": "2026-12-22",
                    "schedule": "regular",
                    "sourcePages": [9, 10],
                },
                {
                    "validFrom": "2026-12-23",
                    "validTo": "2026-12-25",
                    "schedule": "christmas_special",
                    "sourcePages": [11],
                },
                {
                    "validFrom": "2026-12-26",
                    "validTo": "2026-12-29",
                    "schedule": "regular",
                    "sourcePages": [9, 10],
                },
                {
                    "validFrom": "2026-12-30",
                    "validTo": "2027-01-01",
                    "schedule": "new_year_special",
                    "sourcePages": [11],
                },
            ]
            data["callConditions"] = {
                "HusöAndKyrkogårdsö": {
                    "stops": ["Husö", "Kyrkogårdsö"],
                    "operation": "booking_required",
                    "bookingDeadline": {
                        "minutesBeforeDepartureFromOrigin": 60,
                    },
                    "withVehicle": {
                        "ferryCallMayBeBooked": True,
                    },
                    "withoutVehicle": {
                        "default": "use_connecting_passenger_boat_via_Sottunga",
                        "ferryCallMayBeBookedWhen": [
                            "no_connecting_passenger_boat_is_available",
                            "journey_is_to_or_from_Galtby",
                        ],
                    },
                    "downstreamDelayMinutesApproximate": {
                        "Husö": 10,
                        "Kyrkogårdsö": 20,
                    },
                    "combinedCalls": {
                        "assumedDownstreamDelayMinutesApproximate": 30,
                        "calculation": "sum_of_individual_published_delays",
                        "confidence": "low",
                        "historicalValidationRequired": True,
                        "uncertainty": (
                            "A smaller fairway appears to connect Husö and Kyrkogårdsö. "
                            "If the ferries use it, the delays may not be cumulative."
                        ),
                    },
                },
                "Överö": {
                    "operation": "booking_required",
                    "bookingDeadline": {
                        "minutesBeforeEstimatedArrivalAtStop": 45,
                    },
                    "eligibleJourneys": {
                        "fromÖverö": "eastbound_beyond_Överö",
                        "toÖverö": "arriving_from_the_east",
                    },
                    "ineligibleJourneys": [
                        "Överö-Långnäs",
                        "Långnäs-Överö",
                    ],
                    "geographicContext": {
                        "GaltbySide": "east",
                        "LångnäsSide": "west",
                    },
                }
            }
            data["timeNotationPolicy"] = {
                "tripOrigin": {
                    "earliestDepartureOffsetMinutes": 0,
                    "publishedTimeNature": "scheduled_not_early",
                },
                "intermediateStops": {
                    "earliestDepartureOffsetMinutes": -5,
                    "latestDepartureOffsetMinutes": 0,
                    "publishedTimeNature": "may_depart_up_to_five_minutes_early",
                    "passengerAdvice": "be_ready_at_least_five_minutes_before_published_time",
                },
            }
            data["routingPolicy"] = {
                "specialSaturdays": {
                    "dates": ["2026-10-03", "2026-11-07", "2026-12-05"],
                    "LångnäsToGaltby": {
                        "operateDepartures": ["06:00", "10:30"],
                        "suppressDeparture": "09:15",
                    },
                    "GaltbyToLångnäs": {
                        "operateDeparture": "20:15",
                        "departure14:45": {
                            "operates": True,
                            "vessel": "M/S Skiftet",
                            "replacesUsualVessel": "M/S Gudingen",
                        },
                    },
                },
                "otherSaturdays": {
                    "LångnäsToGaltby": {
                        "operateDeparture": "09:15",
                        "suppressDepartures": ["06:00", "10:30"],
                    },
                    "GaltbyToLångnäs": {
                        "suppressDeparture": "20:15",
                        "departure14:45": {
                            "operates": True,
                            "vessel": "M/S Gudingen",
                        },
                    },
                },
                "sourceFootnoteWarning": (
                    "Footnote 4 has different semantics in the two direction tables: "
                    "service suppression from Långnäs, but only a vessel substitution "
                    "from Galtby."
                ),
            }
        if source_id == "finferries-nagusodra-nauvon-etelainen-reitti-talvi-1.10.2026-24.3.2027":
            data["routingPolicy"] = {
                "servicePattern": "reservation_activated_island_loop",
                "serviceRunsWhen": "at_least_one_island_journey_is_reserved",
                "emptyLoopNotOperated": True,
                "terminalAnchorsAreOperationalNotPassengerJourney": True,
                "sameTerminalOriginDestinationAllowed": False,
                "publishedDepartureTimeRole": "exact",
                "approximateReturnTimeDependsOn": [
                    "which_island_calls_are_reserved",
                    "weather_and_operating_conditions",
                ],
                "intermediateCalls": "only_for_reservations_to_or_from_that_pier",
                "typicalPassengerJourney": "terminal_to_island_or_island_to_terminal",
                "island_to_islandJourney": "possible_but_uncommon",
            }
            data["canonicalStopNames"] = {
                "Penö": "Peno",
            }
            data["sourceRowExpansions"] = {
                "Gloskär / Trunsö": {
                    "stops": ["Gloskär", "Trunsö"],
                    "semantics": "two_separate_optional_calls",
                    "inheritCellMarkersForEachStop": True,
                    "bothCallsMayOccurOnSameTrip": True,
                    "reason": "Separate nearby islands combined on one row to keep the printed timetable compact.",
                }
            }
        if source_id == "finferries-rymattylanreitti-rymattylan-reitti-28.9.2026-2.5.2027":
            data["sourceRowExpansions"] = {
                "Korvenmaa/Wihuri/Pyytti": {
                    "stops": ["Korvenmaa", "Wihuri", "Pyytti"],
                    "semantics": "three_separate_calls",
                    "inheritCellMarkersForEachStop": True,
                    "allCallsIndependentlyAvailable": True,
                    "geography": {
                        "Korvenmaa": "island",
                        "Wihuri": "separate_pier_on_Korvenmaa_island",
                        "Pyytti": "island",
                    },
                    "reason": "Nearby separate destinations combined on one row to keep the printed timetable compact.",
                }
            }
            data["timeNotationPolicy"] = {
                "parenthesizedTime": {
                    "type": "estimated_intermediate_time",
                    "scheduledOffsetFromDeparture": True,
                    "strictTime": False,
                    "examples": [
                        {"stop": "Ruotsalainen", "offsetMinutes": 20},
                        {"stop": "Pakinainen", "offsetMinutes": 40},
                    ],
                },
                "slashSeparatedAlternativeTime": {
                    "example": "Pakinainen (16:40/17:05)x on Sunday",
                    "alternatives": [{
                        "time": "16:40",
                        "condition": "Pähkinäinen call before Pakinainen is not operated",
                    }, {
                        "time": "17:05",
                        "condition": "Pähkinäinen call before Pakinainen is operated",
                    }],
                    "notIndependentDepartures": True,
                },
            }
            data["routingPolicy"] = {
                "xCalls": {
                    "operation": "when_needed",
                    "usuallyOperated": True,
                    "bookingDeadline": {"relativeTo": "same_day", "time": "09:00"},
                },
                "unpublishedIntermediateTimes": "no_estimate_should_be_invented",
                "returnToHaapala": {
                    "publishedTimeRole": "loop_frame_not_guaranteed_arrival",
                    "actualTimeDependsOn": "number_and_sequence_of_optional_calls",
                    "example": "If the Wednesday Pähkinäinen call is not needed, arrival may be around 12:00 as on Tuesday rather than the later printed frame time.",
                },
            }
        if source_id == "finferries-pargasrutt-paraisten-reittialue-talvi-1.9.2026-31.5.2027":
            data["timeNotationPolicy"] = {
                "parenthesizedPensarTime": {
                    "type": "estimated_intermediate_time",
                    "stop": "Pensar",
                    "strictTime": False,
                    "routingUse": "useful_approximate_call_time",
                    "interpretation": (
                        "Pensar is the farthest point of the route. The printed "
                        "time gives passengers a useful estimate and may normally "
                        "be fairly stable, including for passengers boarding at "
                        "subsequent stops, but it is not guaranteed to the minute."
                    ),
                    "actualTimeDependsOn": "ordered_calls_and_operating_conditions",
                }
            }
            data["booking"] = {
                "defaultPolicy": "required",
                "interpretation": (
                    "Every passenger journey must be booked. This general rule "
                    "is distinct from whether an individual route deviation "
                    "needs a separate call order."
                ),
                "deadlineRules": [{
                    "appliesTo": {
                        "departureFrom": "Granvik",
                        "time": "06:00",
                        "role": "first_departure_of_day",
                    },
                    "deadline": {
                        "relativeTo": "previous_day",
                        "time": "17:00",
                    },
                    "interpretationConfidence": "medium",
                    "sourceAmbiguity": (
                        "The source says 'morning tour'; this is interpreted as "
                        "only the first departure of the day."
                    ),
                }, {
                    "appliesTo": "all_other_departures",
                    "deadlineMinutesBeforeDeparture": 10,
                }],
            }
            data["callConditions"] = {
                "Granholmen": {
                    "operation": "booking_required",
                    "availableJourneys": "Granvik-Granholmen and Granholmen-Granvik on all services unless excluded below",
                    "structuralExpansion": (
                        "Treat Granholmen as an omitted timetable row adjacent "
                        "to every Heisala call, before or after Heisala according "
                        "to the direction of travel."
                    ),
                    "passengerJourneyBookingRequired": True,
                    "serviceExclusions": [{
                        "departuresFromGranvik": ["07:45", "14:00"],
                        "route": ["Granvik", "Heisala", "Granvik"],
                        "GranholmenCallAvailable": False,
                        "affectedJourneys": [
                            "Granvik-Granholmen",
                            "Granholmen-Granvik",
                        ],
                    }],
                    "routeContext": (
                        "Granvik-Heisala is nearly a shuttle service and "
                        "Granholmen is only a small deviation. Granholmen was "
                        "omitted as a repeated timetable row for readability."
                    ),
                },
                "Stenholm": {
                    "operation": "on_separate_call_order",
                    "eligibleServices": "every service extending to Pensar",
                    "eligibleDirections": ["Granvik-Stenholm", "Stenholm-Granvik"],
                    "availableOnShorterServices": False,
                    "passengerJourneyBookingAlsoRequired": True,
                },
                "Ramsholm": {
                    "operation": "only_when_conditions_require",
                    "normalTimetableStop": False,
                    "independentSearchablePier": True,
                    "location": "opposite end of Heisala island",
                    "userNotice": {
                        "fi": "varattavissa vain olosuhteiden niin vaatiessa",
                        "sv": "kan bokas endast när omständigheterna kräver det",
                        "en": "bookable only when circumstances require it",
                    },
                },
            }
            data["routingPolicy"] = {
                "stopOrderFromGranvik": [
                    "Björkholm", "Ramsholm", "Stenholm", "Aspholm"
                ],
                "RamsholmAndStenholmOmittedFromPrintedTable": True,
                "retiredStops": [{
                    "stop": "Östra Tallholm",
                    "excludedFromCurrentRoute": True,
                    "evidence": (
                        "The stop appeared in at least the 2019 timetable but "
                        "not in the checked 2025 summer timetables or the "
                        "current 2026-2027 winter timetable."
                    ),
                }],
            }
        if source_id == "finferries-iniokustavi-inio-kustavi-talvi-1.1.-7.5.2026-ja-14.9.-31.12.2026":
            data["departureAnnotations"] = [{
                "operatingDays": "_2_4___",
                "from": "Heponiemi",
                "time": "07:00",
                "type": "dangerous_goods_transport",
                "passengerCapacityReduced": True,
                "userNotice": {
                    "fi": "Vaarallisten aineiden kuljetus, rajoitettu matkustajamäärä",
                    "sv": "Transport av farliga ämnen, begränsat passagerarantal",
                    "en": "Dangerous goods transport, limited number of passengers",
                },
            }, {
                "operatingDays": "_2_4___",
                "from": "Kannvik",
                "time": "09:30",
                "type": "dangerous_goods_transport",
                "passengerCapacityReduced": True,
                "userNotice": {
                    "fi": "Vaarallisten aineiden kuljetus, rajoitettu matkustajamäärä",
                    "sv": "Transport av farliga ämnen, begränsat passagerarantal",
                    "en": "Dangerous goods transport, limited number of passengers",
                },
            }]
        if source_id == "finferries-kasnashitis-kasnas-hiittinen-aurora-talvi-1.1.-31.12.2026":
            dangerous_goods_notice = {
                "fi": "Vaarallisten aineiden kuljetus, rajoitettu matkustajamäärä",
                "sv": "Transport av farliga ämnen, begränsat passagerarantal",
                "en": "Dangerous goods transport, limited number of passengers",
            }
            data["departureAnnotations"] = [{
                "operatingDays": "12345__",
                "from": "Kasnäs",
                "time": "06:30",
                "type": "dangerous_goods_transport",
                "passengerCapacityReduced": True,
                "userNotice": dangerous_goods_notice,
            }, {
                "operatingDays": "12345__",
                "from": "Långnäs",
                "time": "08:30",
                "type": "dangerous_goods_transport",
                "passengerCapacityReduced": True,
                "userNotice": dangerous_goods_notice,
            }]
        if source_id == "finferries-utorutt-uton-reitti-talvi-1.10.2026-31.5.2027":
            tx_notice = {
                "type": "passenger_only_priority_service",
                "importance": "important",
                "messages": {
                    "fi": "Vain henkilökuljetus; vuoro on tarkoitettu ensisijaisesti koululaisille ja paikallisille asukkaille",
                    "sv": "Endast persontransport; turen är främst avsedd för skolbarn och lokala invånare",
                    "en": "Passenger transport only; primarily intended for schoolchildren and local residents",
                },
                "effects": {
                    "vehiclesAllowed": False,
                    "localAndSchoolPriority": True,
                    "generalPublicAllowed": True,
                    "showInGeneralJourneySearch": True,
                    "availabilitySubjectToAcceptedBooking": True,
                    "UtöPier": "village_pier",
                },
                "sourceAnnotations": ["tx"],
            }
            data["serviceRole"] = {
                "principalTerminal": "Pärnäs",
                "principalTerminalNames": {
                    "fi": "Pärnäinen", "sv": "Pärnäs", "en": "Pärnäs"
                },
            }
            data["routingPolicy"] = {
                "suppressedTransferSuggestions": [{
                    "arrivalTrip": "tx-monday-inbound",
                    "arrivalAtPärnäs": "08:15",
                    "departureTrip": "regular-monday-outbound",
                    "departureFromPärnäs": "08:30",
                    "physicalTransferPossible": True,
                    "recommended": False,
                    "reason": (
                        "The tx inbound service has already called at Jurmo, "
                        "Aspö and Nötö. Transferring at Pärnäs to travel back "
                        "towards the same islands is not a useful connection."
                    ),
                }],
            }
            data["callConditions"] = {
                "z": {
                    "stop": "Berghamn",
                    "appliesTo": {
                        "operatingDays": "____5__",
                        "trip": "Utö 05:30 - Pärnäs 10:00",
                    },
                    "operation": "booking_required",
                    "bookingDeadline": {
                        "relativeTo": "previous_day",
                        "time": "17:00",
                    },
                    "weekParity": "odd_iso_weeks_only",
                    "availableOnEvenWeeks": False,
                }
            }
            data["holidayExceptions"] = [{
                "date": "2027-03-25",
                "before": "18:00",
                "service": "none",
                "from": "18:00",
                "scheduleTemplate": "friday",
                "interpretation": (
                    "No service operates before 18:00. The normal Thursday "
                    "daytime schedule is not combined with the Friday evening "
                    "schedule; the approximately five-hour journey makes two "
                    "such rotations impossible."
                ),
            }, {
                "date": "2027-03-29",
                "scheduleTemplate": "sunday",
                "shiftedOvernightRotation": "tx-sunday-monday-overnight",
                "leg": "outbound",
                "from": "Pärnäs",
                "departure": "17:05",
                "to": "Utö",
                "arrival": "19:30",
                "continuesOn": "2027-03-30",
                "bookingDeadline": "2027-03-27T15:00:00+02:00",
            }, {
                "date": "2027-03-30",
                "scheduleTemplate": "monday",
                "shiftedOvernightRotation": "tx-sunday-monday-overnight",
                "leg": "inbound",
                "from": "Utö",
                "departure": "06:00",
                "to": "Pärnäs",
                "arrival": "08:15",
                "otherService": "none",
                "normalScheduleResumes": "2027-03-31",
            }]
            data["trips"] = [{
                "id": "tx-sunday-outbound",
                "rotationId": "tx-sunday-monday-overnight",
                "operatingDays": "______7",
                "bookingRequired": True,
                "bookingDeadline": {
                    "weekday": 6,
                    "time": "15:00",
                    "relation": "preceding_saturday",
                },
                "passengerOnly": True,
                "generalPublicAllowed": True,
                "vessels": ["Myrskylintu", "Berghamn"],
                "continuesAs": "tx-monday-inbound",
                "userNotices": [tx_notice],
                "calls": [
                    {"stop": "Pärnäs", "departure": "17:05"},
                    {"stop": "Nötö", "bookingRequired": True},
                    {"stop": "Aspö", "bookingRequired": True},
                    {"stop": "Jurmo", "bookingRequired": True},
                    {"stop": "Utö", "arrival": "19:30", "pier": "village_pier"},
                ],
            }, {
                "id": "tx-monday-inbound",
                "rotationId": "tx-sunday-monday-overnight",
                "operatingDays": "1______",
                "bookingRequired": True,
                "bookingDeadline": {
                    "weekday": 6,
                    "time": "15:00",
                    "relation": "preceding_saturday",
                },
                "passengerOnly": True,
                "generalPublicAllowed": True,
                "vessels": ["Myrskylintu", "Berghamn"],
                "continuesFrom": "tx-sunday-outbound",
                "userNotices": [tx_notice],
                "calls": [
                    {"stop": "Utö", "departure": "06:00", "pier": "village_pier"},
                    {"stop": "Jurmo", "bookingRequired": True},
                    {"stop": "Aspö", "bookingRequired": True},
                    {"stop": "Nötö", "bookingRequired": True},
                    {"stop": "Pärnäs", "arrival": "08:15"},
                ],
            }]
        if source_id == "finferries-nagutvar-nauvon-poikittainen-reitti-talvi-1.10.2026-24.3.2027":
            data["callConditions"] = {
                "requestOnlyStops": {
                    "operation": "on_separate_call_order",
                    "stops": [
                        "Fagerholm", "Rockelholm", "Grötö", "Triören", "Killingholm"
                    ],
                    "sourceStatement": "Poiketaan tilauksesta",
                    "TriörenDataStatus": (
                        "Current timetable stop confirmed. A provisional pier on the "
                        "southeast shore and a route east of Furuskär and Mottonskär "
                        "are stored in the local map data; the exact landing point "
                        "will be verified from historical live data."
                    ),
                }
            }
            data["sourceRowExpansions"] = {
                "Ängsö / Lånholm": {
                    "stops": ["Ängsö", "Lånholm"],
                    "semantics": "two_separate_calls",
                    "inheritCellMarkersForEachStop": True,
                    "allCallsIndependentlyAvailable": True,
                    "bothCallsMayOccurOnSameTrip": True,
                    "geography": "separate piers on opposite sides of the same large island, more than 2 km apart",
                }
            }
            data["stopAliases"] = {
                "Pärnäs/Pärnäinen": {
                    "canonicalId": "Pärnäs",
                    "names": {"fi": "Pärnäinen", "sv": "Pärnäs", "en": "Pärnäs"},
                    "sameStop": True,
                }
            }
            data["routingPolicy"] = {
                "tuesdayFalköDuty": {
                    "operatingDays": "_2_____",
                    "vessel": "M/S Falkö",
                    "vesselHomeRoute": "nagusodra",
                    "departure": {"stop": "Kirjais", "time": "09:30"},
                    "stopOrder": [
                        "Kirjais", "Byskär", "Brännskär", "Ängsö", "Lånholm",
                        "Hummelholm", "Berghamn", "Kirjais"
                    ],
                    "arrival": {"stop": "Kirjais", "time": "12:00"},
                    "bookingRequired": True,
                    "serviceBelongsTo": "nagutvar",
                },
                "sundayContinuationFromSouthernRoute": {
                    "operatingDays": "______7",
                    "sameTrip": True,
                    "separateTransverseDeparture": False,
                    "origin": {"stop": "Borstö", "time": "12:00"},
                    "sourceRoute": "nagusodra",
                    "transverseSectionStops": [
                        "Berghamn", "Ängsö", "Lånholm", "Hummelholm"
                    ],
                    "omittedSharedContinuationStops": [
                        "Brännskär", "Grötö", "Stenskär", "Gullkrona"
                    ],
                    "fullConfirmedContinuationOrder": [
                        "Berghamn", "Ängsö", "Lånholm", "Hummelholm",
                        "Brännskär", "Grötö", "Stenskär", "Gullkrona", "Kirjais"
                    ],
                    "omissionReason": (
                        "The transverse timetable avoids adding rows used only "
                        "by this single Sunday continuation."
                    ),
                    "destination": {"stop": "Kirjais", "timeApproximate": "18:00"},
                    "visualEvidence": "shared_orange_background",
                },
            }
        if source_id == "finferries-nagusodra-nauvon-etelainen-reitti-talvi-1.10.2026-24.3.2027":
            data["routingPolicy"]["tuesdayTransverseDuty"] = {
                "operatingDays": "_2_____",
                "vessel": "M/S Falkö",
                "notSeparateSouthernPassengerLoop": True,
                "departure": {"stop": "Kirjais", "timeApproximate": "09:30"},
                "operatesRoute": "nagutvar",
                "arrival": {"stop": "Kirjais", "time": "12:00"},
                "laterSouthernService": {
                    "departure": "16:00",
                    "separateTrip": True,
                },
            }
            data["routingPolicy"]["weekdayMorningWindow"] = {
                "operatingDays": "12345__",
                "from": "Kirjais",
                "departureWindow": {
                    "earliest": "06:15",
                    "latest": "06:50",
                },
                "exactDepartureProvidedWithBooking": True,
                "exactDepartureDependsOn": "booked_calls",
                "publishedAnchors": [{
                    "stop": "Brännskär",
                    "time": "07:20",
                }, {
                    "stop": "Kirjais",
                    "time": "07:45",
                    "role": "return",
                }],
                "doNotCollapseWindowToSingleEstimatedTime": True,
            }
            data["routingPolicy"]["weekendBorstöRotation"] = {
                "principalTerminal": "Kirjais",
                "farthestStop": "Borstö",
                "outbound": {
                    "operatingDays": "_____6_",
                    "from": "Kirjais",
                    "departure": "10:00",
                    "to": "Borstö",
                    "arrivalApproximate": "13:25",
                },
                "vesselOvernightsAt": "Borstö",
                "inbound": {
                    "operatingDays": "______7",
                    "from": "Borstö",
                    "departure": "12:00",
                    "to": "Kirjais",
                    "arrivalApproximate": "18:00",
                    "bookingMarker": "y+",
                    "bookingDeadline": {
                        "relativeTo": "previous_day",
                        "time": "12:00",
                    },
                    "deadlineAppliesToWholeTrip": True,
                },
            }
            data["routingPolicy"]["sundayServiceBoundary"] = {
                "previousTripEnds": {"stop": "Kirjais", "timeApproximate": "18:00"},
                "nextTrip": {
                    "route": ["Kirjais", "Peno", "Pensar", "Kirjais"],
                    "departure": "18:00",
                    "return": "19:00",
                    "bookingMarker": "y",
                    "bookingDeadline": {
                        "relativeTo": "previous_day",
                        "time": "18:00",
                    },
                },
                "strongPrintedRuleDoesNotJoinTrips": True,
            }
            data["routingPolicy"]["sundayTransverseDetour"] = {
                "interpretationConfidence": "medium",
                "vesselChange": False,
                "vessel": "M/S Falkö",
                "appliesAfter": "Kopparholm",
                "normalStopSkipped": "Knivskär",
                "normalStopSkippedConfirmed": True,
                "detourStopOrder": ["Berghamn", "Ängsö", "Lånholm", "Hummelholm"],
                "returnsToSouthernRouteAt": "Brännskär",
                "thenContinues": ["Grötö", "Stenskär", "Gullkrona", "Kirjais"],
                "sharedContinuationStopsConfirmed": True,
                "sourceMarkerInterpretation": (
                    "The y*+ marker printed only at Kopparholm may describe the "
                    "whole section from Borstö through Kopparholm before Falkö "
                    "switches temporarily to the transverse route. This remains "
                    "a plausible but not fully confirmed interpretation."
                ),
                "sameTripAcrossSourceTables": True,
                "visualEvidence": "shared_orange_background",
            }
        if source_id == "finferries-nagunorra-nauvon-pohjoinen-reitti-talvi-11.8.2026-30.5.2027":
            data["stopAliases"] = {
                "Lavarn (Houtsala)": {
                    "canonicalId": "Lavarn",
                    "names": {"fi": "Lavarn", "sv": "Lavarn", "en": "Lavarn"},
                    "sameStop": True,
                    "locationContext": "Houtsala",
                    "locationContextType": "island_or_area",
                    "locationQualifierNeededInNormalDisplay": False,
                    "interpretation": (
                        "Lavarn is the unique pier name; Houtsala identifies the "
                        "surrounding island or area, not another stop and not a "
                        "disambiguating qualifier."
                    ),
                },
                "Själö/Seili *": {
                    "canonicalId": "Seili",
                    "names": {"fi": "Seili", "sv": "Själö", "en": "Seili"},
                    "sameStop": True,
                    "secondaryDomesticNameRecommended": True,
                    "recommendedDisplays": {
                        "fi": "Seili / Själö",
                        "sv": "Själö / Seili",
                        "en": "Seili / Själö",
                    },
                },
                "Nagu/Nauvo": {
                    "canonicalId": "Nagu",
                    "names": {"fi": "Nauvo", "sv": "Nagu", "en": "Nagu"},
                    "sameStop": True,
                },
                "Nagu / Nauvo": {
                    "canonicalId": "Nagu",
                    "names": {"fi": "Nauvo", "sv": "Nagu", "en": "Nagu"},
                    "sameStop": True,
                },
            }
            data["routingPolicy"] = {
                "yDoubleAsterisk": {
                    "operatingDays": "______7",
                    "validPeriods": [{
                        "validFrom": "2027-05-09",
                        "validTo": "2027-05-31",
                    }, {
                        "validFrom": "2026-08-11",
                        "validTo": "2026-09-13",
                    }],
                    "replacementType": "combine_two_marked_services_into_one",
                    "replaces": [
                        "Nagu-Själö-Nagu",
                        "Nagu-Innamo-Järvsor-Maskinnamo-Åvensor",
                    ],
                    "combinedService": {
                        "departure": {"stop": "Nagu", "time": "17:50"},
                        "stopOrder": [
                            "Nagu", "Själö", "Nagu", "Innamo", "Järvsor",
                            "Maskinnamo", "Åvensor"
                        ],
                        "bookingRequired": True,
                    },
                    "doNotOperateReplacedServicesSeparately": True,
                }
            }
        if source_id in {
            "finferries-velkuanreitti-velkuan-reitti-talvi-14.9.2026-6.5.2027",
            "finferries-velkuataivassalo-velkuan-reitti-talvi-14.9.2026-6.5.2027",
        }:
            data["sourceRowExpansionPolicy"] = {
                "separator": "/",
                "semantics": "each_name_is_a_separate_island_and_call",
                "inheritCellMarkersForEachStop": True,
                "allCallsIndependentlyAvailable": True,
            }
            data["sourceRowExpansions"] = {
                value: {
                    "stops": [part.strip() for part in value.split("/")],
                    "semantics": "separate_island_calls",
                    "inheritCellMarkersForEachStop": True,
                }
                for value in (
                    "Munninmaa / Kettumaa",
                    "Tammisluoto/Liettinen",
                    "Munninmaa/Kettumaa/Liettinen",
                    "Munninmaa/Kettumaa/Liettinen/Tammisluoto",
                    "Munninmaa/Kettumaa/Tammisluoto",
                    "Munninmaa/Kettumaa",
                )
            }
        if source_id == "finferries-houtskarrutt-houtskarin-reitti-talvi-1.10.2026-30.4.2027":
            data["sourceTableCorrections"] = [{
                "page": 1,
                "tableIndex": 1,
                "location": "weekday header between Monday and Tuesday",
                "sourceIssue": "missing vertical divider visually merges the Monday and Tuesday headings",
                "interpretation": {
                    "timeColumns": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
                    "05:50_morning_loop_operatingDays": "_23____",
                    "mondayService": False,
                },
            }, {
                "page": 1,
                "location": "Sunday Själö–Torsholma–Själö segment",
                "interpretation": {
                    "outboundIntermediateCall": {"stop": "Själö", "approximateTime": "13:20"},
                    "turnaround": {
                        "stop": "Torsholma",
                        "arrival": "13:55",
                        "departure": "14:10",
                    },
                    "returnIntermediateCall": {"stop": "Själö", "approximateTime": "14:50"},
                    "sameRoundTrip": True,
                },
            }]
            data["connections"] = [{
                "id": "iniorutt-to-houtskarrutt-at-sjalo",
                "fromRouteId": "iniorutt",
                "toRouteId": "houtskarrutt",
                "direction": "iniorutt_to_houtskarrutt_only",
                "transferStop": "Själö",
                "type": "planned_timetable_connection",
                "guaranteedHold": "not_stated_by_source",
                "example": {
                    "operatingDays": "____5__",
                    "origin": "Åselholm",
                    "firstLeg": {
                        "routeId": "iniorutt",
                        "departure": "13:10",
                        "arrivalStop": "Själö",
                        "arrival": "13:40",
                        "arrivalTimeRole": "approximate_source_time",
                    },
                    "transfer": {
                        "stop": "Själö",
                        "nextVesselStartsFrom": "Torsholma",
                        "nextVesselStartTime": "14:30",
                        "pickupTime": None,
                        "pickupTimeRole": "after_14:30_historical_estimate_candidate",
                        "waitDescription": "more than one hour in normal operation",
                    },
                    "secondLeg": {
                        "routeId": "houtskarrutt",
                        "arrivalStop": "Roslax",
                        "arrival": "17:40",
                    },
                },
            }, {
                "id": "iniorutt-houtskarrutt-bidirectional-sjalo",
                "routes": ["iniorutt", "houtskarrutt"],
                "direction": "bidirectional",
                "transferStop": "Själö",
                "operatingDays": "1_3___7",
                "timeOfDay": "afternoon",
                "type": "official_timetable_connection",
                "basis": "both vessels are scheduled at Själö at the same time and the connection is marked blue in the source timetable",
                "sourceVisualEncoding": "blue_connection_marking",
                "guaranteedHold": "not_stated_by_source",
                "distinctionFromFridayConnection": "Unlike Friday's one-way connection with a long wait, this is an official simultaneous bidirectional connection.",
            }]
        (OUTPUT / f"{source_id}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        )


if __name__ == "__main__":
    main()
