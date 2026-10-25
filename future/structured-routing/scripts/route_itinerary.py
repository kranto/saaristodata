#!/usr/bin/env python3
"""Find a time-dependent multi-leg itinerary in routing-graph.json.

The initial router combines ferry-free road transfers, scheduled ferry and
connection-vessel rides, and continuous/on-demand ferries whose crossing time
is known. Uncertainty and transfer risk stay attached to individual legs.
"""

from __future__ import annotations

import argparse
import copy
import heapq
import json
import re
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parents[1]
DEFAULT_GRAPH = EXPERIMENT / "routing-graph.json"
MAX_SEARCH_DAYS = 3


def parse_clock(value: str) -> time:
    return time.fromisoformat(value)


def at_clock(day: date, value: str, day_offset: int = 0) -> datetime:
    return datetime.combine(day + timedelta(days=day_offset), parse_clock(value))


def valid_on(day: date, periods: list[dict]) -> bool:
    if not periods:
        return True
    for item in periods:
        start = date.fromisoformat(item["validFrom"]) if item.get("validFrom") else None
        end = date.fromisoformat(item["validTo"]) if item.get("validTo") else None
        if (start is None or start <= day) and (end is None or day <= end):
            return True
    return False


def pattern_runs(pattern: str | None, day: date) -> bool:
    return bool(pattern and len(pattern) == 7 and pattern[day.weekday()] != "_")


def holiday_pattern(route: dict, day: date) -> tuple[str | None, str | None]:
    templates = {
        "monday": "1______", "tuesday": "_2_____", "wednesday": "__3____",
        "thursday": "___4___", "friday": "____5__", "saturday": "_____6_",
        "sunday": "______7",
    }
    for item in route.get("holidayExceptions", []):
        if item.get("date") != day.isoformat():
            continue
        action = item.get("action")
        if action == "no_service":
            return action, None
        if action == "use_day_pattern":
            return action, item.get("operatingDays") or templates.get(item.get("scheduleTemplate"))
        return action, None
    return None, None


def service_runs(route: dict, schedule: dict, day: date) -> bool:
    if not valid_on(day, schedule.get("validPeriods", [])):
        return False
    if schedule.get("operatingDate"):
        return schedule["operatingDate"] == day.isoformat()
    if day.isoformat() in route.get("normalizedHolidayDates", []):
        return False
    action, replacement = holiday_pattern(route, day)
    if action == "no_service":
        return False
    pattern = schedule.get("operatingDays")
    return pattern == replacement if replacement else pattern_runs(pattern, day)


def date_in_month_day_period(day: date, start: str, end: str) -> bool:
    value = (day.month, day.day)
    start_value = tuple(map(int, start.split("-")))
    end_value = tuple(map(int, end.split("-")))
    if start_value <= end_value:
        return start_value <= value <= end_value
    return value >= start_value or value <= end_value


def stop_available(route: dict, stop: str, day: date) -> bool:
    notices = (route.get("travelerInformation") or {}).get("notices", [])
    for notice in notices:
        if notice.get("type") != "seasonal_stop_availability":
            continue
        if stop not in notice.get("stops", []):
            continue
        closed = notice.get("closedPeriod") or {}
        if closed.get("from") and closed.get("to") and date_in_month_day_period(
            day, closed["from"], closed["to"]
        ):
            return False
    return True


def scheduled_edge_available(edge: dict, route: dict, day: date) -> bool:
    """Apply stop-specific operating restrictions inside the router."""
    return all(stop_available(route, stop, day) for stop in (edge["from"], edge["to"]))


def routing_call_conditions(edge: dict, route: dict, service_day: date) -> dict | None:
    conditions = edge.get("conditions")
    if not conditions:
        return None
    result = copy.deepcopy(conditions)
    result["intermediateCalls"] = [
        {key: value for key, value in item.items() if key != "multiStopCell"}
        for item in result.get("intermediateCalls", [])
        if stop_available(route, item.get("stopId"), service_day)
    ]
    return result


def public_stop_timing(timing: dict, service_day: date) -> dict | None:
    """Resolve a call's internal clock fields into UI-ready datetimes."""
    if not timing or timing.get("status") == "unknown":
        return None
    result = {"status": timing.get("status")}
    if timing.get("time"):
        result["time"] = at_clock(
            service_day, timing["time"], timing.get("dayOffset", 0)
        ).isoformat(timespec="minutes")
    span = range_datetimes(timing, service_day)
    if span:
        result["range"] = {
            "earliest": span[0].isoformat(timespec="minutes"),
            "latest": span[1].isoformat(timespec="minutes"),
        }
    return result if result.get("time") or result.get("range") else None


def intermediate_call_is_mandatory(call: dict, route: dict) -> bool:
    """Interpret timetable markers instead of exposing them to the UI."""
    optional_operations = {
        "booking_required",
        "on_request",
        "on_separate_call_order",
        "only_when_conditions_require",
    }
    multi_stop = call.get("multiStopCell") or {}
    if multi_stop.get("eachMemberConditional"):
        return False
    stop_id = call.get("stopId") or call.get("stop")
    route_conditions = route.get("callConditions") or {}
    # Some source footnotes apply to named stops but are not encoded as a
    # marker on every individual timetable cell. Ålandstrafiken's shared
    # Husö/Kyrkogårdsö booking rule is one such case.
    for condition_id, condition in route_conditions.items():
        scoped_stops = set(condition.get("stops", []))
        scoped_stop = condition.get("stop")
        applies_to_stop = (
            stop_id in scoped_stops
            or scoped_stop == stop_id
            or condition_id == stop_id
        )
        operation = condition.get("operation") or condition.get("type")
        if applies_to_stop and operation in optional_operations:
            return False
    marker = call.get("callCondition")
    if not marker:
        return True
    condition = route_conditions.get(marker, {})
    operation = condition.get("operation") or condition.get("type")
    return operation not in optional_operations


def routing_intermediate_stops(
    edge: dict, route: dict, service_day: date, trip_patterns: dict[str, dict],
) -> list[dict]:
    """Return the calls crossed while the passenger remains on this vessel."""
    pattern = trip_patterns.get(edge.get("tripPatternId"))
    if not pattern:
        return []
    calls = pattern.get("calls", [])
    result = []
    for call_index in edge.get("intermediateCallIndices", []):
        if not isinstance(call_index, int) or not 0 <= call_index < len(calls):
            continue
        call = calls[call_index]
        stop_id = call.get("stopId") or call.get("stop")
        if not stop_id or not stop_available(route, stop_id, service_day):
            continue
        result.append({
            "id": stop_id,
            "mandatory": intermediate_call_is_mandatory(call, route),
            "timing": public_stop_timing(call.get("timing") or {}, service_day),
        })
    return result


def route_operates_on(route: dict, day: date) -> bool:
    return any(service_runs(route, schedule, day) for schedule in route.get("_schedules", []))


def previous_operating_day(route: dict, service_day: date) -> date | None:
    candidate = service_day - timedelta(days=1)
    for _ in range(370):
        if route_operates_on(route, candidate):
            return candidate
        candidate -= timedelta(days=1)
    return None


def deadline_datetime(
    rule: dict, route: dict, service_day: date, departure: datetime,
) -> datetime | None:
    if "dayOffset" in rule and rule.get("time"):
        return at_clock(service_day, rule["time"], rule["dayOffset"])
    relative = rule.get("relativeTo")
    if relative == "same_day" and rule.get("time"):
        return at_clock(service_day, rule["time"])
    if relative == "previous_day" and rule.get("time"):
        return at_clock(service_day - timedelta(days=1), rule["time"])
    if relative == "previous_operating_day" and rule.get("time"):
        previous = previous_operating_day(route, service_day)
        return at_clock(previous, rule["time"]) if previous else None
    if relative in {"trip_departure", "departure_from_starting_harbour"}:
        return departure + timedelta(minutes=rule.get("offsetMinutes", 0))
    if rule.get("weekday") and rule.get("time"):
        weekday = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6,
        }.get(str(rule["weekday"]).lower())
        if weekday is not None:
            candidate = service_day
            while candidate.weekday() != weekday:
                candidate -= timedelta(days=1)
            return at_clock(candidate, rule["time"])
    return None


def route_condition_stops(condition_id: str, condition: dict) -> set[str]:
    stops = set(condition.get("stops", []))
    if condition.get("stop"):
        stops.add(condition["stop"])
    if not stops:
        stops.add(condition_id)
    return stops


def condition_applies_to_journey(
    condition_id: str, condition: dict, edge: dict,
) -> bool:
    stops = route_condition_stops(condition_id, condition)
    if condition.get("appliesWhenBoardingAtStop"):
        return edge["from"] in stops and f'{edge["from"]}-{edge["to"]}' not in condition.get(
            "ineligibleJourneys", []
        )
    if not stops.intersection({edge["from"], edge["to"]}):
        return False
    journey = f'{edge["from"]}-{edge["to"]}'
    return journey not in condition.get("ineligibleJourneys", [])


def trip_origin_departure(
    trip_pattern: dict | None, service_day: date, fallback: datetime,
) -> datetime:
    if not trip_pattern:
        return fallback
    for call in trip_pattern.get("calls", []):
        timing = call.get("timing") or {}
        if timing.get("time"):
            return at_clock(service_day, timing["time"], timing.get("dayOffset", 0))
    return fallback


def operating_vessel(
    route: dict, edge: dict, trip_patterns: dict[str, dict],
) -> dict | None:
    pattern = trip_patterns.get(edge.get("tripPatternId"), {})
    code = pattern.get("vesselCode")
    details = (route.get("vesselByCode") or {}).get(code)
    if details:
        return details
    vessel = route.get("vessel")
    if vessel:
        return {
            "name": vessel,
            "contact": route.get("contact"),
            "capacity": route.get("capacity"),
        }
    return None


def resolve_booking_deadline(
    rule: dict, route: dict, service_day: date, departure: datetime,
    edge: dict, trip_patterns: dict[str, dict],
) -> datetime | None:
    base = departure
    if rule.get("relativeTo") == "departure_from_starting_harbour":
        base = trip_origin_departure(
            trip_patterns.get(edge.get("tripPatternId")), service_day, departure
        )
    return deadline_datetime(rule, route, service_day, base)


def route_deadline_rule(route: dict, departure: datetime, edge_from: str | None = None) -> dict | None:
    booking = route.get("booking") or {}
    for item in booking.get("deadlineRules", []):
        applies = item.get("appliesTo")
        if applies == "departures_after_16:00" and departure.time() > time(16, 0):
            return item.get("deadline")
        if applies == "all_other_y_departures" and departure.time() <= time(16, 0):
            return item.get("deadline")
        if applies == "all_other_departures":
            if item.get("deadlineMinutesBeforeDeparture") is not None:
                return {
                    "relativeTo": "trip_departure",
                    "offsetMinutes": -item["deadlineMinutesBeforeDeparture"],
                }
            return item.get("deadline")
        if isinstance(applies, dict):
            weekdays = applies.get("weekdays")
            weekday_matches = not weekdays or departure.strftime("%A").lower() in weekdays
            departure_stop = applies.get("departureStop")
            if applies.get("departureFrom") and not re.fullmatch(r"\d{2}:\d{2}", applies["departureFrom"]):
                departure_stop = applies["departureFrom"]
            stop_matches = not departure_stop or departure_stop == edge_from
            exact_matches = not applies.get("time") or applies["time"] == departure.strftime("%H:%M")
            clock = departure.strftime("%H:%M")
            lower = applies.get("departureTimeFrom")
            if applies.get("departureFrom") and re.fullmatch(r"\d{2}:\d{2}", applies["departureFrom"]):
                lower = applies["departureFrom"]
            lower_matches = not lower or clock >= lower
            upper_matches = not applies.get("departureBefore") or clock < applies["departureBefore"]
            if weekday_matches and stop_matches and exact_matches and lower_matches and upper_matches:
                return item.get("deadline")
    return booking.get("deadline")


def routing_booking_requirement(
    edge: dict, route: dict, service_day: date, departure: datetime,
    arrival: datetime, trip_patterns: dict[str, dict], mode: str,
) -> dict | None:
    booking = route.get("booking") or {}
    conditions = edge.get("conditions") or {}
    markers = [
        marker for marker in (
            conditions.get("fromCallCondition"), conditions.get("toCallCondition")
        ) if marker
    ]
    applicable_conditions = []
    route_conditions = route.get("callConditions") or {}
    for condition_id, condition in route_conditions.items():
        if condition_id in markers or condition_applies_to_journey(condition_id, condition, edge):
            applicable_conditions.append((condition_id, condition))
    required = bool(booking.get("requiredForAllTrips"))
    recommended = bool(booking.get("recommendedForVehicles"))
    deadline_candidates = []
    booking_contact_source = None
    for condition_id, condition in applicable_conditions:
        operation = condition.get("operation") or condition.get("type")
        if operation in {"booking_required", "on_request"}:
            required = True
        booking_contact_source = (condition.get("bookingContact") or {}).get("source") or booking_contact_source
        rule = condition.get("deadline")
        if condition.get("deadlineRule") == "route_booking_deadline_rules":
            rule = route_deadline_rule(route, departure, edge["from"])
        if rule:
            resolved = resolve_booking_deadline(
                rule, route, service_day, departure, edge, trip_patterns
            )
            if resolved:
                deadline_candidates.append(resolved)
        booking_deadline = condition.get("bookingDeadline") or {}
        if booking_deadline.get("minutesBeforeEstimatedArrivalAtStop") is not None:
            stop = next(
                (item for item in route_condition_stops(condition_id, condition) if item in {edge["from"], edge["to"]}),
                edge["to"],
            )
            stop_time = arrival if stop == edge["to"] else departure
            deadline_candidates.append(stop_time - timedelta(
                minutes=booking_deadline["minutesBeforeEstimatedArrivalAtStop"]
            ))
        if booking_deadline.get("minutesBeforeDepartureFromOrigin") is not None:
            pattern = trip_patterns.get(edge.get("tripPatternId"))
            origin_departure = trip_origin_departure(pattern, service_day, departure)
            deadline_candidates.append(origin_departure - timedelta(
                minutes=booking_deadline["minutesBeforeDepartureFromOrigin"]
            ))
    if (required or recommended) and not deadline_candidates:
        rule = route_deadline_rule(route, departure, edge["from"])
        if rule:
            resolved = resolve_booking_deadline(
                rule, route, service_day, departure, edge, trip_patterns
            )
            if resolved:
                deadline_candidates.append(resolved)
    loading_readiness = loading_readiness_minutes(route, edge["from"], mode)
    if not required and not recommended and not deadline_candidates and not loading_readiness:
        return None
    result = {"required": required}
    if loading_readiness:
        result["loadingReadinessMinutesBefore"] = loading_readiness
    if recommended and not required:
        result["recommended"] = True
    if deadline_candidates:
        result["deadline"] = min(deadline_candidates).isoformat(timespec="minutes")
    channel = booking.get("url") or booking.get("channel")
    if channel:
        result["channel"] = channel
    for key in (
        "phone", "email", "earliestBookingDaysBefore", "vehicleAndCargoBookingOpensDaysBefore",
        "vehicleSpace",
    ):
        if booking.get(key) is not None:
            result[key] = booking[key]
    if not required:
        for key in ("vehicleSpaceGuaranteedOnlyWithBooking", "unbookedVehiclePolicy"):
            if booking.get(key) is not None:
                result[key] = booking[key]
    if booking_contact_source == "operating_vessel":
        vessel = operating_vessel(route, edge, trip_patterns) or {}
        vessel_phones = (vessel.get("contact") or {}).get("phones", [])
        result.pop("email", None)
        result["channel"] = "phone"
        if vessel_phones:
            result["phone"] = vessel_phones[0]
    elif booking_contact_source == "route_operator":
        route_phones = (route.get("contact") or {}).get("phones", [])
        if route_phones:
            result["phone"] = route_phones[0]
    return result


def routing_traveler_information(route: dict, edge: dict) -> dict | None:
    """Return only traveler notices relevant to this result leg.

    Stop availability and destination classification remain source metadata.
    The former is enforced by the router and neither belongs in its public
    itinerary response.
    """
    information = route.get("travelerInformation")
    if not information:
        return None
    internal_types = {
        "seasonal_stop_availability", "destination_character", "booking_requirement",
    }
    touched_stops = {edge["from"], edge["to"]}
    touched_stops.update(
        item.get("stopId") for item in edge.get("conditions", {}).get("intermediateCalls", [])
    )
    notices = []
    for notice in information.get("notices", []):
        if notice.get("type") in internal_types:
            continue
        scoped_stops = set(notice.get("stops", []))
        if scoped_stops and not touched_stops.intersection(scoped_stops):
            continue
        notices.append(notice)
    result = {
        key: value for key, value in information.items()
        if key not in {"displayPolicy", "notices"}
    }
    if notices:
        result["notices"] = notices
    return result or None


def range_datetimes(timing: dict, service_day: date) -> tuple[datetime, datetime] | None:
    value = timing.get("range")
    if not value or not value.get("earliest") or not value.get("latest"):
        return None
    offsets = timing.get("rangeDayOffsets") or [timing.get("dayOffset", 0)] * 2
    earliest = at_clock(service_day, value["earliest"], offsets[0])
    latest = at_clock(service_day, value["latest"], offsets[-1])
    while latest < earliest:
        latest += timedelta(days=1)
    return earliest, latest


def timing_datetime(timing: dict, service_day: date, *, role: str, profile: str) -> datetime | None:
    span = range_datetimes(timing, service_day)
    if profile == "conservative" and span:
        # To guarantee boarding, be prepared for the earliest departure. For
        # onward routing, reserve time until the latest plausible arrival.
        return span[0] if role == "departure" else span[1]
    if timing.get("time"):
        return at_clock(service_day, timing["time"], timing.get("dayOffset", 0))
    if span:
        # A range without a typical value does not justify inventing a
        # midpoint. Use the earliest bound for boarding readiness and the
        # latest bound for onward-routing feasibility.
        return span[0] if role == "departure" else span[1]
    return None


def next_scheduled_instance(edge: dict, route: dict, ready: datetime, profile: str) -> dict | None:
    schedule = edge["schedule"]
    for offset in range(MAX_SEARCH_DAYS + 1):
        service_day = ready.date() + timedelta(days=offset)
        if not service_runs(route, schedule, service_day):
            continue
        if not scheduled_edge_available(edge, route, service_day):
            continue
        departure = timing_datetime(schedule.get("departure", {}), service_day, role="departure", profile=profile)
        arrival = timing_datetime(schedule.get("arrival", {}), service_day, role="arrival", profile=profile)
        if departure is None or arrival is None or departure < ready:
            continue
        while arrival < departure:
            arrival += timedelta(days=1)
        if arrival == departure and edge["from"] != edge["to"]:
            continue
        return {
            "departure": departure,
            "arrival": arrival,
            "serviceDate": service_day.isoformat(),
        }
    return None


def availability_windows(availability: dict, day: date) -> list[tuple[datetime, datetime]]:
    if not valid_on(day, availability.get("validPeriods", [])):
        return []
    if not pattern_runs(availability.get("operatingDays"), day):
        return []
    window = availability.get("operatingWindow") or availability
    start_value, end_value = window.get("start"), window.get("end")
    if not start_value or not end_value:
        # An on-demand cable ferry with only listed breaks operates throughout
        # the day outside those breaks. Absence of an operatingWindow is not an
        # absence of service.
        start = datetime.combine(day, time.min)
        return [(start, start + timedelta(days=1))]
    start, end = at_clock(day, start_value), at_clock(day, end_value)
    if window.get("crossesMidnight") or end <= start:
        end += timedelta(days=1)
    return [(start, end)]


def active_break_end(availability: dict, moment: datetime) -> datetime | None:
    for item in availability.get("breaks", []):
        if item.get("only"):
            # Specialized parity/weekday rules remain visible in the output,
            # but are not guessed by this initial router.
            continue
        pattern = item.get("operatingDays")
        if pattern and not pattern_runs(pattern, moment.date()):
            continue
        start = at_clock(moment.date(), item["start"])
        end = at_clock(moment.date(), item["end"])
        if end <= start:
            end += timedelta(days=1)
        if start <= moment < end:
            return end
    return None


def next_continuous_instance(edge: dict, ready: datetime) -> dict | None:
    crossing = edge.get("crossingMinutes")
    if crossing is None:
        return None
    availability = edge["availability"]
    for offset in range(MAX_SEARCH_DAYS + 1):
        day = ready.date() + timedelta(days=offset)
        for start, end in availability_windows(availability, day):
            departure = max(ready, start)
            break_end = active_break_end(availability, departure)
            if break_end:
                departure = break_end
            arrival = departure + timedelta(minutes=crossing)
            if arrival <= end:
                return {"departure": departure, "arrival": arrival, "serviceDate": day.isoformat()}
    return None


def mode_allowed(edge: dict, mode: str) -> bool:
    value = edge.get("mobility", {}).get(mode)
    return value in {"allowed", "allowed_subject_to_operator_conditions", "booking_validation_required"}


def road_duration(edge: dict, mode: str) -> tuple[int, dict] | None:
    road_mode = "auto" if mode in {"car", "motorcycle"} else mode
    value = edge.get("modes", {}).get(road_mode)
    if not value or value.get("status") != "ok":
        return None
    # Published ferry times and traveler-facing output have one-minute
    # precision. Sub-minute OSRM precision otherwise produces misleading
    # values such as 06:54 when the displayed drive is 55 minutes and the
    # required pier-ready time is 07:50.
    rounded_seconds = max(60, round(value["durationSeconds"] / 60) * 60)
    return rounded_seconds, value


def transfer_risk(wait_minutes: int, readiness_minutes: int) -> dict:
    effective = wait_minutes - readiness_minutes
    if effective < 0:
        level = "below_required_readiness"
    elif effective == 0:
        level = "very_tight"
    elif effective < 5:
        level = "tight"
    elif effective < 30:
        level = "normal"
    else:
        level = "relaxed"
    return {
        "level": level,
        "rawBufferMinutes": wait_minutes,
        "requiredReadinessMinutes": readiness_minutes,
        "effectiveBufferMinutes": effective,
    }


def loading_readiness_minutes(route: dict, origin: str, mode: str) -> int:
    booking = route.get("booking", {})
    origin_rule = booking.get("loadingReadinessMinutesBeforeByOrigin", {}).get(origin)
    if isinstance(origin_rule, int):
        return origin_rule
    if isinstance(origin_rule, dict):
        value = origin_rule.get(mode, origin_rule.get("default"))
        if value is not None:
            return value
    return booking.get("loadingReadinessMinutesBefore", 0)


COMMERCIAL_OPERATOR_NAMES = {
    "finnlines": "Finnlines",
    "tallink": "Tallink Silja",
    "vikingline": "Viking Line",
}


def commercial_operator(route: dict) -> str | None:
    """Return a passenger-facing operator name for commercial ferries."""
    return COMMERCIAL_OPERATOR_NAMES.get(route.get("provider"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("origin")
    parser.add_argument("destination")
    parser.add_argument("travel_date", type=date.fromisoformat)
    parser.add_argument("start_time", type=parse_clock)
    parser.add_argument("--mode", choices=("car", "motorcycle", "bicycle"), default="car")
    parser.add_argument("--timing-profile", choices=("typical", "conservative"), default="typical")
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    args = parser.parse_args()

    graph = json.loads(args.graph.read_text())
    routes = {item["id"]: item for item in graph["routes"]}
    trip_patterns = {item["id"]: item for item in graph["tripPatterns"]}
    nodes = {item["id"]: item for item in graph["nodes"]}
    for value, label in ((args.origin, "origin"), (args.destination, "destination")):
        if value not in nodes:
            raise SystemExit(f"unknown {label}: {value}")

    adjacency: dict[str, list[dict]] = defaultdict(list)
    skipped_continuous_unknown = 0
    for edge in graph["edges"]:
        if not edge.get("enabledForAutomaticRouting", True):
            continue
        if edge["kind"] == "road" and road_duration(edge, args.mode):
            adjacency[edge["from"]].append(edge)
        elif edge["kind"] == "scheduled_service" and mode_allowed(edge, args.mode):
            routes[edge["routeId"]].setdefault("_schedules", []).append(edge["schedule"])
            adjacency[edge["from"]].append(edge)
        elif edge["kind"] == "continuous_ferry" and mode_allowed(edge, args.mode):
            if edge.get("crossingMinutes") is None:
                skipped_continuous_unknown += 1
            else:
                adjacency[edge["from"]].append(edge)

    start = datetime.combine(args.travel_date, args.start_time)
    initial_state = (args.origin, False)
    best = {initial_state: start}
    previous: dict[tuple[str, bool], tuple[tuple[str, bool], dict]] = {}
    queue = [(start, args.origin, False)]
    destination_state = None

    while queue:
        moment, node_id, has_used_ferry = heapq.heappop(queue)
        state = (node_id, has_used_ferry)
        if moment != best.get(state):
            continue
        if node_id == args.destination:
            destination_state = state
            break
        for edge in adjacency.get(node_id, []):
            if edge["kind"] == "road":
                duration_seconds, details = road_duration(edge, args.mode)  # type: ignore[misc]
                instance = {
                    "departure": moment,
                    "arrival": moment + timedelta(seconds=duration_seconds),
                    "road": details,
                }
            elif edge["kind"] == "scheduled_service":
                route = routes[edge["routeId"]]
                # A ferry loop back to the journey origin must not turn the
                # original boarding into a nominal transfer and thereby
                # bypass its full check-in/readiness requirement.
                is_real_transfer = has_used_ferry and node_id != args.origin
                readiness = 0 if is_real_transfer else loading_readiness_minutes(
                    route, edge["from"], args.mode
                )
                boarding_ready = moment + timedelta(minutes=readiness)
                instance = next_scheduled_instance(edge, route, boarding_ready, args.timing_profile)
                if not instance:
                    continue
            else:
                instance = next_continuous_instance(edge, moment)
                if not instance:
                    continue
            arrival = instance["arrival"]
            next_has_used_ferry = has_used_ferry or edge["kind"] != "road"
            next_state = (edge["to"], next_has_used_ferry)
            if arrival < best.get(next_state, datetime.max):
                best[next_state] = arrival
                previous[next_state] = (state, {"edge": edge, "instance": instance, "ready": moment})
                heapq.heappush(queue, (arrival, edge["to"], next_has_used_ferry))

    if destination_state is None:
        print(json.dumps({
            "status": "no_route",
            "origin": args.origin,
            "destination": args.destination,
            "departureNotBefore": start.isoformat(timespec="minutes"),
            "mode": args.mode,
            "timingProfile": args.timing_profile,
            "skippedContinuousEdgesWithoutCrossingTime": skipped_continuous_unknown,
        }, ensure_ascii=False, indent=2))
        return 2

    raw_legs = []
    cursor = destination_state
    while cursor != initial_state:
        previous_state, record = previous[cursor]
        raw_legs.append((previous_state[0], cursor[0], previous_state[1], record))
        cursor = previous_state
    raw_legs.reverse()

    legs = []
    for index, (from_id, to_id, had_used_ferry, record) in enumerate(raw_legs):
        edge, instance, ready = record["edge"], record["instance"], record["ready"]
        leg = {
            "index": index + 1,
            "kind": edge["kind"],
            "from": from_id,
            "to": to_id,
            "readyAtOrigin": ready.isoformat(timespec="minutes"),
            "departure": instance["departure"].isoformat(timespec="minutes"),
            "arrival": instance["arrival"].isoformat(timespec="minutes"),
            "waitMinutes": round((instance["departure"] - ready).total_seconds() / 60),
        }
        if edge["kind"] == "road":
            leg["distanceMeters"] = instance["road"]["distanceMeters"]
            leg["durationMinutes"] = round((instance["arrival"] - instance["departure"]).total_seconds() / 60)
        else:
            route = routes[edge["routeId"]]
            vessel = operating_vessel(route, edge, trip_patterns)
            leg.update({
                "routeId": edge["routeId"],
                "tripPatternId": edge.get("tripPatternId"),
                "serviceType": edge.get("serviceType"),
                "operator": commercial_operator(route),
                "vessel": vessel.get("name") if vessel else None,
                "mobilityRule": edge.get("mobility", {}).get(args.mode),
                "booking": routing_booking_requirement(
                    edge, route, date.fromisoformat(instance["serviceDate"]),
                    instance["departure"], instance["arrival"], trip_patterns, args.mode,
                ),
                "contact": vessel.get("contact") if vessel else route.get("contact"),
                "capacity": vessel.get("capacity") if vessel else route.get("capacity"),
                "publicTimetableUrl": route.get("publicTimetableUrl"),
                "travelerInformation": routing_traveler_information(route, edge),
                "intermediateStops": routing_intermediate_stops(
                    edge, route, date.fromisoformat(instance["serviceDate"]), trip_patterns
                ),
            })
            if edge["kind"] == "scheduled_service":
                leg["departureTiming"] = edge["schedule"].get("departure")
                leg["arrivalTiming"] = edge["schedule"].get("arrival")
                arrival_span = range_datetimes(
                    edge["schedule"].get("arrival", {}),
                    date.fromisoformat(instance["serviceDate"]),
                )
                if arrival_span and arrival_span[0] < instance["departure"]:
                    leg["timingWarnings"] = [
                        "source arrival range begins before this departure; latest bound was used for routing"
                    ]
            else:
                leg["availability"] = edge.get("availability")
        if had_used_ferry and edge["kind"] == "scheduled_service":
            readiness = loading_readiness_minutes(
                routes[edge["routeId"]], edge["from"], args.mode
            )
            leg["transferRisk"] = transfer_risk(leg["waitMinutes"], readiness)
        legs.append(leg)

    print(json.dumps({
        "status": "route_found",
        "origin": args.origin,
        "destination": args.destination,
        "departureNotBefore": start.isoformat(timespec="minutes"),
        "arrival": best[destination_state].isoformat(timespec="minutes"),
        "elapsedMinutes": round((best[destination_state] - start).total_seconds() / 60),
        "mode": args.mode,
        "timingProfile": args.timing_profile,
        "legs": legs,
        "diagnostics": {
            "skippedContinuousEdgesWithoutCrossingTime": skipped_continuous_unknown,
            "limitations": [
                "returns the earliest-arrival itinerary only",
                "does not yet enumerate later or riskier alternatives",
                "continuous ferry edges without a known crossing time are not routable",
                "specialized holiday and parity-based break rules still require expansion",
            ],
        },
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
