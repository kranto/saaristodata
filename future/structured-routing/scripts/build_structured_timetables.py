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
COMMERCIAL_FERRIES = EXPERIMENT_ROOT / "commercial-ferry-timetables.json"

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

# This legacy route/source pair is the same Velkua–Taivassalo timetable as the
# newer, fully transcribed source below.  Keeping both creates duplicate trips
# and lets routing choose the copy without vessel, booking and contact data.
SUPERSEDED_SOURCES = {
    "finferries-velkuanreitti-velkuan-reitti-talvi-14.9.2026-6.5.2027":
        "finferries-velkuataivassalo-velkuan-reitti-talvi-14.9.2026-6.5.2027",
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
    "iniokustavi", "kasnashitis", "korpohoutskar", "korponorrskata",
    "nagukorpo", "pargasnagu",
}

FINFERRIES_CABLE_FERRY_ROUTES = {
    "hammaronsalmi", "hogsar", "hogsara", "keistio", "kivimo",
    "kokkila", "mossala", "palva", "saverkeit", "skagen", "vano",
    "vartsala", "velkuanmaa",
}

ALANDSTRAFIKEN_CABLE_FERRY_ROUTES = {
    "alandsvajerfarjor", "angosundslinjen", "bjorkolinjen",
    "embarsundslinjen", "seglingelinjen", "simskalalinjen", "toftolinjen",
}

ALAND_SCHEDULED_CABLE_FERRIES = {
    "seglingelinjen": {
        "terminals": ["Seglinge", "Snäckö"],
        "crossingMinutes": 7,
        "returnDepartureOffsetMinutes": 7,
        "times": [
            "06:00", "06:40", "07:10", "07:40", "08:00", "08:40",
            "09:10", "09:40", "10:10", "11:10", "11:40", "12:10",
            "12:30", "12:50", "13:10", "13:40", "14:10", "14:40",
            "15:10", "15:40", "16:10", "16:50", "17:40", "18:10",
            "18:40", "19:00", "19:40", "20:10", "20:40", "21:10",
            "21:40", "22:00",
        ],
        "weekdayOnlyTimes": ["12:30"],
        "advanceBookingByTime": {"06:00": "05:45"},
        "tripRunsOnlyWithTraveler": True,
        "returnMayBeDelayedMinutes": {"commercialTraffic": 10, "otherTrafficWithValidReason": 10},
        "validPeriods": [{"validFrom": "2026-09-14", "validTo": "2026-12-31"}],
        "continuousServices": [{
            "serviceMode": "on_demand", "start": "22:20", "end": "05:40",
            "crossesMidnight": True, "operatingDays": "1234567",
        }],
        "breaks": [{"start": "10:30", "end": "11:05"}, {"start": "17:00", "end": "17:35"}],
        "sourceId": "alandstrafiken-seglinge-linfarja-14.9-31.12-1",
        "phone": "+358407685792",
    },
    "simskalalinjen": {
        "terminals": ["Timskär", "Vattungsrevet"],
        "crossingMinutes": 7,
        "returnDepartureOffsetMinutes": 7,
        "times": [
            "06:10", "06:30", "06:50", "07:10", "07:40", "08:15",
            "08:45", "09:15", "09:45", "10:15", "10:45", "11:15",
            "12:15", "12:45", "13:15", "13:45", "14:15", "14:50",
            "15:15", "15:45", "16:20", "16:50", "17:40", "18:00",
            "18:30", "19:00", "19:30", "20:00", "20:30", "21:00",
            "21:30",
        ],
        "weekdayOnlyTimes": ["06:50"],
        "waitForConnectionTimes": ["07:10", "08:15", "13:15"],
        "tripRunsOnlyWithTraveler": True,
        "returnMayBeDelayedMinutes": {"commercialTraffic": 10, "otherTraffic": 5},
        "validPeriods": [{"validFrom": "2026-01-01", "validTo": "2026-12-31"}],
        "continuousServices": [{
            "serviceMode": "on_demand", "start": "22:00", "end": "05:50",
            "crossesMidnight": True, "operatingDays": "1234567",
        }],
        "breaks": [
            {"start": "11:35", "end": "12:10"},
            {"start": "14:00", "end": "14:15"},
            {"start": "17:05", "end": "17:40"},
        ],
        "sourceId": "alandstrafiken-simskala-1",
        "phone": "+3584573798869",
    },
    "toftolinjen": {
        "terminals": ["Töftö", "Prästö"],
        "crossingMinutes": 4,
        "returnDepartureOffsetRangeMinutes": [5, 7],
        "times": [
            *[f"{hour:02d}:{minute:02d}" for hour in range(6, 22) for minute in (0, 15, 30, 45)],
        ],
        "weekdayOnlyTimes": [
            "06:00", "06:15", "06:30", "06:45",
            "07:00", "07:15", "07:30", "07:45",
            "09:15", "12:00", "12:15", "18:00", "18:15", "20:00",
        ],
        "waitForConnectionTimes": ["06:45", "07:45", "15:45", "16:45", "17:45"],
        "validPeriods": [{"validFrom": "2026-01-01", "validTo": "2026-12-31"}],
        "continuousServices": [
            {"serviceMode": "on_demand", "start": "22:00", "end": "05:50", "crossesMidnight": True, "operatingDays": "12345__"},
            {"serviceMode": "on_demand", "start": "22:00", "end": "07:50", "crossesMidnight": True, "operatingDays": "_____67", "alsoAppliesOnPublicHolidays": True},
        ],
        "breaks": [{"start": "02:30", "end": "03:05", "operatingDays": "1234567"}],
        "weekendAndHolidayBreaks": [
            {"start": "09:10", "end": "09:30"},
            {"start": "11:55", "end": "12:30"},
            {"start": "17:55", "end": "18:30"},
            {"start": "19:55", "end": "20:15"},
        ],
        "sourceId": "alandstrafiken-toftolinjen-inkl-avvikelser",
        "phone": "+3584573421279",
    },
}

ALAND_CONTINUOUS_CABLE_FERRIES = {
    "bjorkolinjen": {
        "terminals": ["LappoL", "BjörköK"],
        "phone": "+3584575242854",
        "breaks": [{"start": "11:10", "end": "11:45"}, {"start": "17:30", "end": "18:05"}],
        "night": {"start": "22:00", "end": "06:00", "bookingDeadline": "21:00"},
    },
    "embarsundslinjen": {
        "terminals": ["Finholma", "Jyddö"],
        "phone": "+3584573798871",
        "breaks": [{"start": "10:25", "end": "11:00"}, {"start": "17:10", "end": "17:45"}],
    },
    "angosundslinjen": {
        "terminals": ["Norrboda", "Ängö"],
        "phone": "+3584575295082",
        "breaks": [
            {"start": "11:00", "end": "11:30"},
            {"start": "13:30", "end": "14:30", "only": "even_iso_week_wednesday"},
            {"start": "19:00", "end": "19:30"},
        ],
        "night": {"start": "22:00", "end": "06:00", "bookingDeadline": "21:00"},
    },
}

ALAND_CABLE_FERRY_HOLIDAY_EXCEPTIONS = {
    "bjorkolinjen": [
        {"date": "2026-12-24", "trafficEnds": "22:00", "onOrderDepartures": ["23:00", "00:00", "01:00"]},
        {"date": "2026-12-25", "trafficResumes": "06:00"},
    ],
    "angosundslinjen": [
        {"date": "2026-12-24", "trafficEnds": "22:00", "onOrderDepartures": ["23:00", "00:00", "01:00"]},
        {"date": "2026-12-25", "trafficResumes": "06:00"},
    ],
    "embarsundslinjen": [
        {"date": "2026-12-24", "trafficEnds": "22:00", "onOrderDepartures": ["23:00", "00:00", "01:00"]},
        {"date": "2026-12-25", "trafficResumes": "06:00"},
    ],
    "simskalalinjen": [
        {"date": "2026-12-24", "trafficEnds": "22:00", "onOrderDepartures": ["23:00", "00:00", "01:00"]},
        {"date": "2026-12-25", "trafficResumes": "06:00"},
    ],
    "seglingelinjen": [
        {"date": "2026-12-24", "regularTrafficUntil": "18:00", "onOrderDepartures": ["19:00", "20:00", "21:00", "22:00", "23:00", "00:00"], "bookingDeadline": "18:00", "returnFrom": "Snäckö", "returnTiming": "immediately_after_arrival"},
        {"date": "2026-12-25", "trafficResumes": "06:00"},
    ],
    "toftolinjen": [
        {"date": "2026-04-03", "scheduleDayOverride": "sunday", "cancelledBreak": {"from": "17:55", "to": "18:30"}},
        {"date": "2026-05-01", "scheduleDayOverride": "sunday", "cancelledBreak": {"from": "17:55", "to": "18:30"}},
        {"date": "2026-05-14", "scheduleDayOverride": "sunday", "cancelledBreak": {"from": "17:55", "to": "18:30"}},
        {"date": "2026-06-19", "scheduleDayOverride": "friday"},
        {"date": "2026-12-24", "scheduleDayOverride": "sunday", "cancelledBreak": {"from": "17:55", "to": "18:30"}, "trafficEnds": "00:00", "onOrderDepartures": ["01:00"]},
        {"date": "2026-12-25", "trafficResumes": "06:00"},
    ],
}

# A routing client sees both scheduled road ferries and on-demand cable ferries
# as two-terminal edges. Source headings are retained in departures, while this
# table maps them to the canonical pier names used by the rest of the data.
# crossingMinutes is a routing duration from departure to arrival.  The source
# and the derivation are retained because several cable-ferry operators publish
# only the route length and departure times, not a formal crossing duration.
# Values based on an official transport analysis are kept separate from values
# reported by a local or route-information source.
FERRY_ROUTE_MODELS = {
    "iniokustavi": {
        "mode": "road_ferry", "terminals": ["Kannvik", "Heponiemi"],
        "crossingMinutes": 25,
        "origins": {"Iniö (Kannvik)": "Kannvik", "Kustavi/Gustavs (Heponiemi)": "Heponiemi"},
    },
    "kasnashitis": {
        "mode": "road_ferry", "terminals": ["Kasnäs", "LångnäsH"],
        "crossingMinutes": 25,
        "origins": {"Kasnäs": "Kasnäs", "Hiittinen / Hitis (Långnäs)": "LångnäsH"},
    },
    "korpohoutskar": {
        "mode": "road_ferry", "terminals": ["Galtby", "Kittuis"],
        "crossingMinutes": 35,
        "origins": {"Korppoo / Korpo": "Galtby", "Houtskari / Houtskär": "Kittuis"},
    },
    "korponorrskata": {
        "mode": "road_ferry", "terminals": ["Galtby", "Olofsnäs"],
        "crossingMinutes": 15,
        "origins": {"Korppoo / Korpo (Galtby)": "Galtby", "Norrskata": "Olofsnäs"},
    },
    "nagukorpo": {
        "mode": "road_ferry", "terminals": ["Pärnäs", "Retais"],
        "crossingMinutes": 5,
        "origins": {"Nauvo/Nagu-Korppoo/Korpo": "Pärnäs", "Korppoo/Korpo-Nauvo/Nagu": "Retais"},
    },
    "pargasnagu": {
        "mode": "road_ferry", "terminals": ["Lillmälö", "Prostvik"],
        "crossingMinutes": 10,
        "origins": {"Parainen / Pargas": "Lillmälö", "Nauvo / Nagu": "Prostvik"},
    },
    "hammaronsalmi": {
        "mode": "cable_ferry", "terminals": ["Airismaa", "Aasla"],
        "crossingMinutes": 3,
        "returnImmediatelyAfterPublishedCrossing": True,
        "crossingTimeBasis": "current_route_information_estimate",
        "crossingTimeSourceUrl": "https://lautta.junatiedot.fi/hammaronsalmen-lossi",
        "origins": {"Hämmärönsalmi (Aasla)": "Aasla"},
    },
    "hogsar": {
        "mode": "cable_ferry", "terminals": ["Grännäs", "Ängholm"],
        "crossingMinutes": 3,
        "crossingTimeBasis": "estimate_from_official_319_m_route_length",
        "crossingTimeSourceUrl": "https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/hogsar.html",
        "origins": {},
    },
    "hogsara": {
        "mode": "cable_ferry", "terminals": ["Svartnäs", "Högsåra"],
        "crossingMinutes": 10,
        "crossingTimeBasis": "local_destination_route_information",
        "crossingTimeSourceUrl": "https://www.farmorscafe.fi/sv/yhteystiedot/",
        "origins": {"Svartnäs": "Svartnäs", "Högsåra": "Högsåra"},
    },
    "keistio": {
        "mode": "cable_ferry", "terminals": ["Dalen", "Keistiö"],
        "crossingMinutes": 12,
        "crossingTimeBasis": "local_archipelago_route_information",
        "crossingTimeSourceUrl": "https://www.vskylat.fi/wp-content/uploads/2021/11/Keistio.pdf",
        "origins": {"Dalen": "Dalen", "Keistiö": "Keistiö"},
    },
    "kivimo": {
        "mode": "cable_ferry", "terminals": ["Roslax", "Kivimo"],
        "crossingMinutes": 1,
        "crossingTimeBasis": "official_transport_analysis_travel_time",
        "crossingTimeSourceUrl": "https://www.doria.fi/bitstream/handle/10024/172554/vj_2019-42_978-952-317-721-5.pdf?sequence=5&isAllowed=y",
        "origins": {},
    },
    "kokkila": {
        "mode": "cable_ferry", "terminals": ["Kokkila", "Angelniemi"],
        "crossingMinutes": 6,
        "returnImmediatelyAfterPublishedCrossing": True,
        "crossingTimeBasis": "current_route_information_estimate",
        "crossingTimeSourceUrl": "https://lautta.junatiedot.fi/kokkila-lossi",
        "origins": {"Kokkila (saari/ö)": "Kokkila"},
    },
    "mossala": {
        "mode": "cable_ferry", "terminals": ["BjörköH", "MossalaE"],
        "crossingMinutes": 2,
        "crossingTimeBasis": "official_transport_analysis_travel_time",
        "crossingTimeSourceUrl": "https://www.doria.fi/bitstream/handle/10024/172554/vj_2019-42_978-952-317-721-5.pdf?sequence=5&isAllowed=y",
        "origins": {},
    },
    "palva": {
        "mode": "cable_ferry", "terminals": ["Teersalo", "PalvaI"],
        "crossingMinutes": 8,
        "crossingTimeBasis": "current_route_information_estimate",
        "crossingTimeSourceUrl": "https://fi.ferje.info/palva-lossi",
        "origins": {"Teersalo": "Teersalo", "Palva": "PalvaI"},
    },
    "saverkeit": {
        "mode": "cable_ferry", "terminals": ["NäsbyI", "Saverkeit"],
        "crossingMinutes": 2,
        "crossingTimeBasis": "official_transport_analysis_travel_time",
        "crossingTimeSourceUrl": "https://www.doria.fi/bitstream/handle/10024/172554/vj_2019-42_978-952-317-721-5.pdf?sequence=5&isAllowed=y",
        "origins": {},
    },
    "skagen": {
        "mode": "cable_ferry", "terminals": ["Skagen", "JumoE"],
        "crossingMinutes": 5,
        "crossingTimeBasis": "route_information_estimate",
        "crossingTimeSourceUrl": "https://www.2cv.fi/lautat-raid2papp-reitilla-kesakuussa-2017/",
        "origins": {},
    },
    "vano": {
        "mode": "cable_ferry", "terminals": ["Våno", "Mielisholm"],
        "crossingMinutes": 3,
        "returnImmediatelyAfterPublishedCrossing": True,
        "crossingTimeBasis": "current_route_information_estimate",
        "crossingTimeSourceUrl": "https://fi.ferje.info/vanon-lossi",
        "origins": {"Våno (mantere/fastland)": "Våno"},
    },
    "vartsala": {
        "mode": "cable_ferry", "terminals": ["Kivimaa", "Vartsala"],
        "crossingMinutes": 8,
        "crossingTimeBasis": "upper_bound_of_current_route_information_estimate",
        "crossingTimeSourceUrl": "https://fi.ferje.info/vartsalan-lossi",
        "origins": {"Kustavi/Gustavs (mantere/fastland)": "Kivimaa", "Vartsala (saari/ö)": "Vartsala"},
    },
    "velkuanmaa": {
        "mode": "cable_ferry", "terminals": ["PalvaL", "Velkuanmaa"],
        "crossingMinutes": 8,
        "crossingTimeBasis": "estimate_from_route_length_and_published_departure_spacing",
        "crossingTimeSourceUrl": "https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/velkuanmaa.html",
        "origins": {"Palva": "PalvaL", "Velkuanmaa": "Velkuanmaa"},
    },
    "seglingelinjen": {"mode": "cable_ferry", "terminals": ["Seglinge", "Snäckö"], "crossingMinutes": 7, "origins": {}},
    "simskalalinjen": {"mode": "cable_ferry", "terminals": ["Timskär", "Vattungsrevet"], "crossingMinutes": 7, "origins": {}},
    "toftolinjen": {"mode": "cable_ferry", "terminals": ["Töftö", "Prästö"], "crossingMinutes": 4, "origins": {}},
    "bjorkolinjen": {
        "mode": "cable_ferry", "terminals": ["LappoL", "BjörköK"],
        "crossingMinutes": 5,
        "crossingDistanceMeters": 555,
        "crossingTimeBasis": "estimate_from_route_length_and_comparable_aland_cable_ferries",
        "origins": {},
    },
    # The maintained route length for this short crossing is 215 m.
    # Five minutes is a conservative routing approximation comparable to the
    # other short cable-ferry crossings; it is not a published timetable time.
    "embarsundslinjen": {
        "mode": "cable_ferry", "terminals": ["Finholma", "Jyddö"],
        "crossingMinutes": 5,
        "crossingDistanceMeters": 215,
        "crossingTimeBasis": "maintained_conservative_routing_estimate",
        "origins": {},
    },
    "angosundslinjen": {
        "mode": "cable_ferry", "terminals": ["Norrboda", "Ängö"],
        "crossingMinutes": 4,
        "crossingDistanceMeters": 280,
        "crossingTimeBasis": "estimate_from_route_length_and_comparable_aland_cable_ferries",
        "origins": {},
    },
}

# Route-scoped because names such as Torsholma occur in more than one
# archipelago. roadAccess means that a traveller can bring a road vehicle to
# the pier through the regional road/road-ferry network without first using
# the connection-vessel service being queried. It deliberately does not mean
# merely that an island has local roads or that the connection vessel can carry
# a car. suggestForUnspecifiedOrigin is the stricter routing-search rule used
# when the user supplies a destination but no origin.
PIER_ACCESS_BY_ROUTE = {
    "hitisalva": {
        "Dalsbruk": {"roadAccess": True, "suggestForUnspecifiedOrigin": True, "role": "gateway_terminal"},
        "Bolax": {"roadAccess": False, "suggestForUnspecifiedOrigin": False, "role": "island_call"},
    },
    "hitisjurmo": {
        "Kasnäs": {"roadAccess": True, "suggestForUnspecifiedOrigin": True, "role": "gateway_terminal"},
        "Dalsbruk": {"roadAccess": True, "suggestForUnspecifiedOrigin": True, "role": "gateway_terminal"},
    },
    "houtskarrutt": {
        "Roslax": {"roadAccess": True, "suggestForUnspecifiedOrigin": True, "role": "gateway_terminal"},
        "Näsby": {"roadAccess": True, "suggestForUnspecifiedOrigin": True, "role": "gateway_terminal"},
        "TorsholmaI": {
            "roadAccess": True,
            "suggestForUnspecifiedOrigin": True,
            "role": "gateway_terminal",
            "displayQualifier": "Brändö, eastern pier",
            "island": "Brändö",
            "locality": "Torsholma",
            "berthVariant": "east",
            "relatedPier": "Torsholma",
            "connectedToRelatedPierByRoad": True,
        },
        "Själö": {"roadAccess": False, "suggestForUnspecifiedOrigin": False, "role": "island_call"},
    },
    "iniorutt": {
        "Kannvik": {"roadAccess": True, "suggestForUnspecifiedOrigin": True, "role": "gateway_terminal"},
        "Norrby": {"roadAccess": True, "suggestForUnspecifiedOrigin": True, "role": "road_accessible_pier"},
        "Själö": {"roadAccess": False, "suggestForUnspecifiedOrigin": False, "role": "island_call"},
    },
    "korporutt": {
        "Verkan": {"roadAccess": True, "suggestForUnspecifiedOrigin": True, "role": "gateway_terminal"},
        "Kittuis": {"roadAccess": True, "suggestForUnspecifiedOrigin": True, "role": "gateway_terminal"},
        "Havträsk": {"roadAccess": True, "suggestForUnspecifiedOrigin": True, "role": "road_accessible_terminal"},
        "Berghamn": {"roadAccess": False, "suggestForUnspecifiedOrigin": False, "role": "island_call"},
        "Storpensor": {"roadAccess": False, "suggestForUnspecifiedOrigin": False, "role": "island_call"},
    },
    "nagunorra": {
        "Nagu": {"roadAccess": True, "suggestForUnspecifiedOrigin": True, "role": "gateway_terminal"},
        "Lavarn": {"roadAccess": True, "suggestForUnspecifiedOrigin": True, "role": "road_accessible_terminal"},
        "Seili": {"roadAccess": False, "suggestForUnspecifiedOrigin": False, "role": "island_call"},
    },
    "nagusodra": {
        "Kirjais": {"roadAccess": True, "suggestForUnspecifiedOrigin": True, "role": "gateway_terminal"},
        "Borstö": {"roadAccess": False, "suggestForUnspecifiedOrigin": False, "role": "overnight_island_terminal"},
    },
    "nagutvar": {
        "Pärnäs": {"roadAccess": True, "suggestForUnspecifiedOrigin": True, "role": "gateway_terminal"},
        "Kirjais": {"roadAccess": True, "suggestForUnspecifiedOrigin": True, "role": "gateway_terminal"},
        "Hummelholm": {"roadAccess": False, "suggestForUnspecifiedOrigin": False, "role": "island_call"},
    },
    "norralinjen": {
        "Hummelvik": {"roadAccess": True, "suggestForUnspecifiedOrigin": True, "role": "gateway_terminal", "displayQualifier": "Vårdö"},
        "TorsholmaI": {
            "roadAccess": True,
            "suggestForUnspecifiedOrigin": True,
            "role": "temporary_gateway_terminal",
            "displayQualifier": "Brändö, eastern pier",
            "island": "Brändö",
            "locality": "Torsholma",
            "berthVariant": "east",
            "relatedPier": "Torsholma",
            "connectedToRelatedPierByRoad": True,
            "currentUse": {
                "state": "northern_line_uses_eastern_pier_while_larger_harbour_is_unavailable",
                "validThrough": "2026-12-31",
                "mustBeRecheckedWithNextTimetable": True,
            },
        },
        "Kumlinge": {"roadAccess": False, "suggestForUnspecifiedOrigin": False, "role": "island_terminal"},
    },
    "pargasrutt": {
        "Granvik": {"roadAccess": True, "suggestForUnspecifiedOrigin": True, "role": "gateway_terminal"},
        "Pensar": {"roadAccess": False, "suggestForUnspecifiedOrigin": False, "role": "island_turnaround"},
    },
    "rymattylanreitti": {
        "Haapala": {"roadAccess": True, "suggestForUnspecifiedOrigin": True, "role": "gateway_terminal"},
    },
    "sodralinjen": {
        "Galtby": {"roadAccess": True, "suggestForUnspecifiedOrigin": True, "role": "gateway_terminal", "displayQualifier": "Korppoo"},
        "Långnäs": {"roadAccess": True, "suggestForUnspecifiedOrigin": True, "role": "gateway_terminal", "displayQualifier": "Lumparland"},
        "Överö": {
            "roadAccess": True,
            "suggestForUnspecifiedOrigin": False,
            "role": "island_network_intermediate",
            "displayQualifier": "Föglö",
            "exclusionReason": "not_a_practical_gateway_for_travelers_who_are_not_already_in_Föglö",
        },
        "Kökar": {"roadAccess": False, "suggestForUnspecifiedOrigin": False, "role": "island_terminal"},
        "Sottunga": {"roadAccess": False, "suggestForUnspecifiedOrigin": False, "role": "island_terminal"},
    },
    "utorutt": {
        "Pärnäs": {"roadAccess": True, "suggestForUnspecifiedOrigin": True, "role": "gateway_terminal"},
        "Utö": {"roadAccess": False, "suggestForUnspecifiedOrigin": False, "role": "overnight_island_terminal"},
    },
    "velkuanreitti": {
        "Teersalo": {"roadAccess": True, "suggestForUnspecifiedOrigin": True, "role": "gateway_terminal"},
        "Hakkenpää": {"roadAccess": True, "suggestForUnspecifiedOrigin": True, "role": "road_accessible_terminal"},
    },
    "velkuataivassalo": {
        "Teersalo": {"roadAccess": True, "suggestForUnspecifiedOrigin": True, "role": "gateway_terminal"},
        "Hakkenpää": {"roadAccess": True, "suggestForUnspecifiedOrigin": True, "role": "road_accessible_terminal"},
    },
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
            value = value[: -len(suffix)]
            break
    # The HTML source uses the short id "inio", while the maintained route and
    # PDF transcription use "iniokustavi". They are one routing edge.
    return {"inio": "iniokustavi"}.get(value, value)


def add_minutes(time_value: str, day_offset: int, minutes: int) -> tuple[str, int]:
    hour, minute = map(int, time_value.split(":"))
    absolute = day_offset * 24 * 60 + hour * 60 + minute + minutes
    return f"{(absolute // 60) % 24:02d}:{absolute % 60:02d}", absolute // (24 * 60)


def normalize_ferry_route(route: dict, model: dict) -> list[str]:
    """Add a common two-terminal routing model without discarding source data."""
    terminals = model["terminals"]
    route["serviceType"] = model["mode"]
    route["routingService"] = {
        "model": "scheduled_departures" if route["departures"] else "continuous_or_on_demand",
        "networkEdge": True,
        "terminals": terminals,
        "vehicleAccessAtAllTerminals": True,
        "connectionVesselVehicleLoadingCapabilityModeled": False,
        **({
            "crossingMinutes": model["crossingMinutes"],
            "crossingTimeNature": "approximate",
            **({"crossingTimeBasis": model["crossingTimeBasis"]}
               if model.get("crossingTimeBasis") else {}),
            **({"crossingTimeSourceUrl": model["crossingTimeSourceUrl"]}
               if model.get("crossingTimeSourceUrl") else {}),
            **({"crossingDistanceMeters": model["crossingDistanceMeters"]}
               if model.get("crossingDistanceMeters") is not None else {}),
        }
           if model.get("crossingMinutes") is not None else
           {"crossingTimeStatus": "not_available_do_not_invent"}),
    }

    for service in route["continuousServices"]:
        service["serviceMode"] = "on_demand"
        service["terminals"] = terminals
        if model.get("crossingMinutes") is not None:
            service["crossingMinutes"] = model["crossingMinutes"]

    trips = []
    unmapped = []
    for departure in route["departures"]:
        origin = model["origins"].get(departure["from"])
        if origin not in terminals:
            unmapped.append(departure["from"])
            continue
        destination = terminals[1] if origin == terminals[0] else terminals[0]
        for operation in departure["operations"]:
            calls = [{
                "stop": origin,
                "time": departure["time"],
                "dayOffset": departure.get("dayOffset", 0),
                "timeNature": "published_departure",
            }]
            destination_call = {"stop": destination}
            if model.get("crossingMinutes") is not None:
                arrival, arrival_day = add_minutes(
                    departure["time"], departure.get("dayOffset", 0), model["crossingMinutes"]
                )
                destination_call.update({
                    "time": arrival,
                    "dayOffset": arrival_day,
                    "timeNature": "estimated_from_approximate_crossing_duration",
                    "offsetMinutes": model["crossingMinutes"],
                })
            else:
                destination_call["timeNature"] = "unknown_crossing_duration"
            calls.append(destination_call)
            normalized_trip = {
                "id": f'{route["id"]}-ferry-{len(trips) + 1:04d}',
                "operatingDays": operation["operatingDays"],
                "validPeriods": [{
                    "validFrom": operation["validFrom"],
                    "validTo": operation["validTo"],
                }],
                "specialDays": operation.get("specialDays", []),
                "sourceId": operation["sourceId"],
                "sourceDepartureLabel": departure["from"],
                "calls": calls,
                **({"conditions": operation["conditions"]} if operation.get("conditions") else {}),
                **({"noteRefs": operation["noteRefs"]} if operation.get("noteRefs") else {}),
                "normalizationStatus": (
                    "machine_generated_requires_semantic_review"
                    if operation.get("noteInterpretationStatus") == "unresolved"
                    else "machine_generated"
                ),
            }
            trips.append(normalized_trip)
            if model.get("returnImmediatelyAfterPublishedCrossing"):
                reverse_departure, reverse_departure_day = add_minutes(
                    departure["time"], departure.get("dayOffset", 0), model["crossingMinutes"]
                )
                reverse_arrival, reverse_arrival_day = add_minutes(
                    departure["time"], departure.get("dayOffset", 0), 2 * model["crossingMinutes"]
                )
                trips.append({
                    **normalized_trip,
                    "id": f'{route["id"]}-ferry-{len(trips) + 1:04d}',
                    "calls": [
                        {
                            "stop": destination,
                            "time": reverse_departure,
                            "dayOffset": reverse_departure_day,
                            "timeNature": "estimated_immediate_return_departure",
                            "offsetMinutes": model["crossingMinutes"],
                        },
                        {
                            "stop": origin,
                            "time": reverse_arrival,
                            "dayOffset": reverse_arrival_day,
                            "timeNature": "estimated_from_approximate_crossing_duration",
                            "offsetMinutes": 2 * model["crossingMinutes"],
                        },
                    ],
                })
    if route["departures"]:
        route["trips"] = trips
    return sorted(set(unmapped))


def aland_cable_ferry_trip(
    route_id_value: str,
    sequence: int,
    operating_days: str,
    valid_periods: list[dict],
    source_id: str,
    calls: list[dict],
    public_holiday_policy: str,
) -> dict:
    return {
        "id": f"{route_id_value}-cable-{sequence:04d}",
        "operatingDays": operating_days,
        "validPeriods": valid_periods,
        "publicHolidayPolicy": public_holiday_policy,
        "sourceId": source_id,
        "calls": calls,
        "normalizationStatus": "manually_normalized_from_visually_verified_pdf",
    }


def normalize_aland_scheduled_cable_ferry(route: dict, schedule: dict) -> None:
    """Expand a one-shore Åland timetable into both traversable directions."""
    terminals = schedule["terminals"]
    route["routingService"].update({
        "model": "hybrid_scheduled_and_on_demand",
        "publishedDepartureTerminal": terminals[0],
        "returnDepartureRule": (
            {"offsetMinutes": schedule["returnDepartureOffsetMinutes"], "timeNature": "approximate"}
            if schedule.get("returnDepartureOffsetMinutes") is not None else
            {"offsetRangeMinutes": schedule["returnDepartureOffsetRangeMinutes"], "timeNature": "approximate"}
        ),
    })
    route["continuousServices"] = []
    for item in schedule["continuousServices"]:
        route["continuousServices"].append({
            **item,
            "type": "continuous_or_on_demand",
            "terminals": terminals,
            "crossingMinutes": schedule["crossingMinutes"],
            "validPeriods": schedule["validPeriods"],
            "sourceId": schedule["sourceId"],
            "breaks": schedule["breaks"],
            **({"weekendAndHolidayBreaks": schedule["weekendAndHolidayBreaks"]}
               if schedule.get("weekendAndHolidayBreaks") else {}),
        })

    trips = []
    weekday_only = set(schedule["weekdayOnlyTimes"])
    for published in schedule["times"]:
        weekdays = "12345__" if published in weekday_only else "1234567"
        holiday_policy = "excluded" if published in weekday_only else "included"
        arrival, arrival_day = add_minutes(published, 0, schedule["crossingMinutes"])
        trips.append(aland_cable_ferry_trip(
            route["id"], len(trips) + 1, weekdays, schedule["validPeriods"], schedule["sourceId"],
            [
                {"stop": terminals[0], "time": published, "dayOffset": 0, "timeNature": "published_departure"},
                {"stop": terminals[1], "time": arrival, "dayOffset": arrival_day, "timeNature": "estimated_crossing_arrival"},
            ],
            holiday_policy,
        ))
        source_conditions = []
        if published in schedule.get("waitForConnectionTimes", []):
            source_conditions.append({
                "type": "may_wait_for_scheduled_bus_or_school_transport",
                "sourceMarkedDeparture": published,
            })
        if published in schedule.get("advanceBookingByTime", {}):
            source_conditions.append({
                "type": "advance_booking",
                "deadline": schedule["advanceBookingByTime"][published],
            })
        if source_conditions:
            trips[-1]["conditions"] = source_conditions

        if schedule.get("returnDepartureOffsetMinutes") is not None:
            offset = schedule["returnDepartureOffsetMinutes"]
            return_departure, return_day = add_minutes(published, 0, offset)
            return_arrival, return_arrival_day = add_minutes(published, 0, offset + schedule["crossingMinutes"])
            reverse_calls = [
                {"stop": terminals[1], "time": return_departure, "dayOffset": return_day, "timeNature": "estimated_return_departure", "offsetMinutes": offset},
                {"stop": terminals[0], "time": return_arrival, "dayOffset": return_arrival_day, "timeNature": "estimated_crossing_arrival", "offsetMinutes": offset + schedule["crossingMinutes"]},
            ]
        else:
            low, high = schedule["returnDepartureOffsetRangeMinutes"]
            dep_low, _ = add_minutes(published, 0, low)
            dep_high, _ = add_minutes(published, 0, high)
            arr_low, _ = add_minutes(published, 0, low + schedule["crossingMinutes"])
            arr_high, _ = add_minutes(published, 0, high + schedule["crossingMinutes"])
            reverse_calls = [
                {"stop": terminals[1], "timeRange": {"earliest": dep_low, "latest": dep_high}, "timeNature": "estimated_return_departure_range", "offsetRangeMinutes": [low, high]},
                {"stop": terminals[0], "timeRange": {"earliest": arr_low, "latest": arr_high}, "timeNature": "estimated_crossing_arrival_range", "offsetRangeMinutes": [low + schedule["crossingMinutes"], high + schedule["crossingMinutes"]]},
            ]
        trips.append(aland_cable_ferry_trip(
            route["id"], len(trips) + 1, weekdays, schedule["validPeriods"], schedule["sourceId"],
            reverse_calls, holiday_policy,
        ))
        if source_conditions:
            trips[-1]["conditions"] = source_conditions

    if route["id"] == "seglingelinjen":
        published = "10:55"
        arrival, arrival_day = add_minutes(published, 0, schedule["crossingMinutes"])
        trips.append({
            **aland_cable_ferry_trip(
                route["id"], len(trips) + 1, "______7", schedule["validPeriods"], schedule["sourceId"],
                [
                    {"stop": terminals[0], "time": published, "dayOffset": 0, "timeNature": "on_request_departure"},
                    {"stop": terminals[1], "time": arrival, "dayOffset": arrival_day, "timeNature": "estimated_crossing_arrival"},
                ],
                "included",
            ),
            "conditions": [{"type": "advance_booking", "deadline": "10:00", "purpose": "sunday_church_service"}],
        })
    route["trips"] = trips
    route["travelerInformation"] = {
        "queueMode": "non_stop_outside_breaks",
        "mayDepartWhenDeckIsFullOrCapacityReached": True,
        "priorityTraffic": [
            "emergency_vehicles", "scheduled_buses", "fuel_transport",
            "urgent_medical_transport",
        ],
        **({
            "scheduledTripRunsOnlyWhenTravelerIsWaitingAtEitherTerminal": True,
            "remoteTerminalTravelerMustBePresentByPublishedOriginTimeOrCallByThatTime": True,
        } if schedule.get("tripRunsOnlyWithTraveler") else {}),
        **({"returnMayBeDelayedMinutes": schedule["returnMayBeDelayedMinutes"]}
           if schedule.get("returnMayBeDelayedMinutes") else {}),
    }
    if route["id"] == "toftolinjen":
        route["travelerInformation"]["vehicleMustBeLoadedBeforeBreak"] = {
            "minutes": 5,
            "break": {"start": "02:30", "end": "03:05"},
        }
    route["contact"] = {"phone": schedule["phone"]}
    route["review"] = {
        **route.get("review", {}),
        "status": "manually_normalized_from_visually_verified_source",
        "routingReady": True,
        "scheduleNormalization": "visually_verified_pdf_colors_and_footnotes",
    }


def add_aland_continuous_cable_ferries(routes_by_id: dict) -> None:
    aggregate = routes_by_id.get("alandsvajerfarjor")
    if not aggregate:
        return
    valid_periods = aggregate.get("validPeriods", [])
    for route_id_value, model in ALAND_CONTINUOUS_CABLE_FERRIES.items():
        daytime = {
            "type": "continuous_or_on_demand",
            "serviceMode": "on_demand_without_timetable",
            "operatingDays": "1234567",
            "terminals": model["terminals"],
            "validPeriods": valid_periods,
            "breaks": model["breaks"],
            "sourceId": aggregate["sources"][0]["sourceId"],
        }
        if model.get("night"):
            daytime["operatingWindow"] = {"start": model["night"]["end"], "end": model["night"]["start"]}
            night = {
                "type": "continuous_or_on_demand",
                "serviceMode": "advance_booking_required",
                "operatingDays": "1234567",
                "terminals": model["terminals"],
                "validPeriods": valid_periods,
                "operatingWindow": {"start": model["night"]["start"], "end": model["night"]["end"], "crossesMidnight": True},
                "bookingDeadline": model["night"]["bookingDeadline"],
                "sourceId": aggregate["sources"][0]["sourceId"],
            }
            services = [daytime, night]
        else:
            services = [daytime]
        route = {
            "id": route_id_value,
            "provider": "alandstrafiken",
            "departures": [],
            "continuousServices": services,
            "notes": [],
            "sources": aggregate["sources"],
            "validPeriods": valid_periods,
            "holidayExceptions": ALAND_CABLE_FERRY_HOLIDAY_EXCEPTIONS.get(route_id_value, []),
            "contact": {"phone": model["phone"]},
            "travelerInformation": {
                "vehicleMustBeLoadedBeforeEveryScheduledBreakMinutes": 5,
            },
            "review": {
                "status": "manually_normalized_from_source_compilation",
                "routingReady": True,
            },
        }
        routes_by_id[route_id_value] = route


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
    superseded_source_count = 0
    for source in checks["sources"]:
        local = ORIGINALS / source["provider"] / f'{source["id"]}.{source["kind"]}'
        if source["id"] in SUPERSEDED_SOURCES:
            superseded_source_count += 1
            continue
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
            if transcription["sourceId"] in SUPERSEDED_SOURCES:
                continue
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
                "vessel", "vessels", "vesselByCode", "sourceLanguageAuthority",
                "languageConflictPolicy", "validPeriods", "booking",
                "callConditions", "departureAnnotations", "holidayExceptions", "capacity", "contact",
                "publicTimetableUrl", "trips",
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
                "travelerInformation",
            ):
                if key in transcription:
                    route[key] = transcription[key]
            transcription_count += 1
    commercial_route_count = 0
    if COMMERCIAL_FERRIES.exists():
        commercial_data = json.loads(COMMERCIAL_FERRIES.read_text())
        for commercial_route in commercial_data["routes"]:
            if commercial_route["id"] in routes_by_id:
                raise ValueError(f'duplicate commercial ferry route id: {commercial_route["id"]}')
            routes_by_id[commercial_route["id"]] = commercial_route
            commercial_route_count += 1
    add_aland_continuous_cable_ferries(routes_by_id)
    routes = sorted(routes_by_id.values(), key=lambda item: item["id"])
    unmapped_ferry_departures = {}
    for route in routes:
        if route["id"] in PIER_ACCESS_BY_ROUTE:
            route["pierAccess"] = PIER_ACCESS_BY_ROUTE[route["id"]]
        if route["provider"] == "alandstrafiken":
            if route["id"] in ALANDSTRAFIKEN_CABLE_FERRY_ROUTES:
                route["serviceType"] = "cable_ferry"
            else:
                route["serviceType"] = "alandstrafiken_archipelago_ferry"
            route["classificationEvidence"] = {
                "providerNetwork": "alandstrafiken",
                "separateFromMainlandConnectionVessels": True,
                "routePattern": "point_to_point_or_multi_stop",
                "cableFerry": route["id"] in ALANDSTRAFIKEN_CABLE_FERRY_ROUTES,
            }
        if route["provider"] == "finferries" and route["id"] in FINFERRIES_ROAD_FERRY_ROUTES:
            route["serviceType"] = "road_ferry"
            route["classificationEvidence"] = {
                "geoJsonSubtype": "conn2",
                "terminalCount": 2,
                "bookingRuleInheritedFromConnectionVessels": False,
            }
        if route["provider"] == "finferries" and route["id"] in FINFERRIES_CABLE_FERRY_ROUTES:
            route["serviceType"] = "cable_ferry"
            route["classificationEvidence"] = {
                "terminalCount": 2,
                "partOfRoadRoutingNetwork": True,
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
            call_conditions = route.get("callConditions", {})
            route["callMarkerPolicy"] = {
                "journeyReservationIsSeparate": True,
                "y": call_conditions.get("y", {
                    "operation": "booking_required",
                    "interpretationStatus": "route_specific_deadline_not_normalized",
                }),
                "x": call_conditions.get("x", {
                    "operation": "source_specific_condition",
                    "interpretationStatus": "unresolved",
                }),
                "expectedUsage": "y is expected at bookable intermediate calls; terminal times may omit it because every connection-vessel journey already requires a reservation",
            }
        if route["id"] in FERRY_ROUTE_MODELS:
            unmapped = normalize_ferry_route(route, FERRY_ROUTE_MODELS[route["id"]])
            if unmapped:
                unmapped_ferry_departures[route["id"]] = unmapped
        if route["id"] in ALAND_SCHEDULED_CABLE_FERRIES:
            normalize_aland_scheduled_cable_ferry(route, ALAND_SCHEDULED_CABLE_FERRIES[route["id"]])
        if route["id"] in ALAND_CABLE_FERRY_HOLIDAY_EXCEPTIONS:
            route["holidayExceptions"] = ALAND_CABLE_FERRY_HOLIDAY_EXCEPTIONS[route["id"]]
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
        "pierAccessPolicy": {
            "roadAccessDefinition": "reachable with a road vehicle through the regional road and road-ferry network without first using the connection-vessel service being queried",
            "localIslandRoadAloneIsInsufficient": True,
            "vehicleCapacityDoesNotImplyRoadAccess": True,
            "unspecifiedOriginSearch": "include only piers where suggestForUnspecifiedOrigin is true",
            "routeScopedNames": True,
        },
        "roadRoutingPolicy": {
            "roadAndRoadFerryConnectionsFormOneGraph": True,
            "separateRoadOrRoadFerryConnectivityFlagRequired": False,
            "roadFerryAndCableFerryTerminalsAreRoadVehicleAccessible": True,
            "connectionVesselVehicleLoadingCapabilityModeled": False,
            "connectionVesselVehicleFeasibilityDelegatedToBookingSystem": True,
            "futureRoadEdges": {
                "endpoints": "pier_ids",
                "measurements": ["distance_km", "car_minutes", "bicycle_minutes"],
            },
        },
        "travelerInformationPolicy": {
            "showAllApplicableSourceInformation": True,
            "mustNotSuppress": [
                "booking_requirement",
                "booking_deadline",
                "loading_readiness",
                "early_departure_rule",
                "vehicle_restriction",
                "capacity_limit",
                "service_exception",
                "connection_guarantee_or_disclaimer",
            ],
        },
        "routes": routes,
        "unconvertedSources": unconverted,
        "statistics": {
            "routeCount": len(routes),
            "convertedSourceCount": len(schedules) + transcription_count,
            "manualTranscriptionCount": transcription_count,
            "commercialFerryRouteCount": commercial_route_count,
            "tripCount": sum(len(route.get("trips", [])) for route in routes),
            "normalizedFerryRouteCount": sum(route["id"] in FERRY_ROUTE_MODELS for route in routes),
            "normalizedFerryTripCount": sum(
                len(route.get("trips", []))
                for route in routes
                if route["id"] in FERRY_ROUTE_MODELS
            ),
            "continuousFerryServiceCount": sum(
                len(route["continuousServices"])
                for route in routes
                if route["id"] in FERRY_ROUTE_MODELS
            ),
            "unmappedFerryDepartureLabelCount": sum(map(len, unmapped_ferry_departures.values())),
            "scheduledDepartureCount": sum(
                len(route["departures"])
                for route in routes
            ),
            "unconvertedSourceCount": len(unconverted),
            "expiredSourceCount": expired_source_count,
            "supersededSourceCount": superseded_source_count,
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
        routing_service = route.get("routingService")
        if routing_service:
            terminals = routing_service.get("terminals", [])
            if len(terminals) != 2 or terminals[0] == terminals[1]:
                errors.append(f'{route["id"]}: ferry routing edge must have two distinct terminals')
            if route["departures"] and not route.get("trips"):
                errors.append(f'{route["id"]}: scheduled ferry has no normalized trips')
            for service in route["continuousServices"]:
                if service.get("terminals") != terminals:
                    errors.append(f'{route["id"]}: continuous service terminals differ from routing edge')
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
