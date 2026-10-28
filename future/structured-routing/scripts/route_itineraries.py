#!/usr/bin/env python3
"""Enumerate distinct time-dependent multimodal itinerary alternatives."""

from __future__ import annotations

import argparse
import bisect
import heapq
import itertools
import json
import sys
from collections import Counter, defaultdict, deque
from datetime import date, datetime, time, timedelta
from pathlib import Path

from route_itinerary import (
    DEFAULT_GRAPH,
    mode_allowed,
    next_continuous_instance,
    next_scheduled_instance,
    parse_clock,
    range_datetimes,
    road_duration,
    operating_vessel,
    loading_readiness_minutes,
    commercial_operator,
    routing_booking_requirement,
    routing_intermediate_stops,
    routing_traveler_information,
    transfer_risk,
    scheduled_edge_available,
    service_runs,
    timing_datetime,
)


RISK_ORDER = {
    "relaxed": 0,
    "normal": 1,
    "tight": 2,
    "very_tight": 3,
    "below_required_readiness": 4,
}

CONTINUOUS_FERRY_APPROACH_MINUTES = 5
MAX_FERRY_CHAIN_DURATION = timedelta(hours=12)
# Structured schedules use a seven-day operating pattern. Looking through one
# complete cycle lets the first usable sailing move to a later day without
# turning that wait into part of the journey-duration limit.
INITIAL_SERVICE_LOOKAHEAD = timedelta(days=7)

# These short local crossings are useful for endpoints on one particular side
# of the ferry, but considering them in every long-distance search creates a
# large set of detours that can never become useful alternatives. Define the
# ordinary-road catchment whose trips may use each crossing.
LOCAL_ENDPOINT_ROUTE_CATCHMENTS = {
    "kokkila": ("Kokkila", "Angelniemi"),
}


def nonlocal_route_ids(
    edges: list[dict], origin: str, destination: str, mode: str,
) -> set[str]:
    """Return local ferry routes outside both endpoints' road catchments."""
    road_seconds: dict[tuple[str, str], float] = {}
    for edge in edges:
        if edge["kind"] != "road":
            continue
        value = road_duration(edge, mode)
        if value is None:
            continue
        key = (edge["from"], edge["to"])
        road_seconds[key] = min(road_seconds.get(key, float("inf")), value[0])

    def belongs_to_local_side(
        endpoint: str, mainland_pier: str, local_pier: str, *, destination_role: bool,
    ) -> bool:
        if endpoint == local_pier:
            return True
        if endpoint == mainland_pier:
            return False
        if destination_role:
            mainland_seconds = road_seconds.get((mainland_pier, endpoint))
            local_seconds = road_seconds.get((local_pier, endpoint))
        else:
            mainland_seconds = road_seconds.get((endpoint, mainland_pier))
            local_seconds = road_seconds.get((endpoint, local_pier))
        return (
            mainland_seconds is not None
            and local_seconds is not None
            and local_seconds < mainland_seconds
        )

    excluded = set()
    for route_id, (mainland_pier, local_pier) in LOCAL_ENDPOINT_ROUTE_CATCHMENTS.items():
        if not (
            belongs_to_local_side(
                origin, mainland_pier, local_pier, destination_role=False,
            )
            or belongs_to_local_side(
                destination, mainland_pier, local_pier, destination_role=True,
            )
        ):
            excluded.add(route_id)
    return excluded


def default_origin_boarding_buffer_minutes(
    records: list[dict], first_service_index: int,
) -> int:
    """Return a distance-independent safety margin for the initial drive.

    This is not a published loading-readiness requirement. It only absorbs
    ordinary uncertainty in the road ETA before the first ferry.
    """
    driving_minutes = sum(
        (item["instance"]["arrival"] - item["instance"]["departure"]).total_seconds() / 60
        for item in records[:first_service_index]
        if item["edge"]["kind"] == "road"
    )
    if driving_minutes < 60:
        return 5
    if driving_minutes < 120:
        return 10
    return 15


class ScheduledInstanceIndex:
    """Materialize each timetable edge once for the query horizon.

    The original search interpreted operating days, holiday exceptions and
    timing ranges every time a label inspected an outgoing edge. A moderately
    broad query can inspect the same edge millions of times. This index keeps
    the exact same timetable semantics but turns the hot-path operation into a
    binary search over already resolved departures.
    """

    def __init__(
        self,
        edges: list[dict],
        routes: dict[str, dict],
        start: datetime,
        deadline: datetime,
        profile: str,
    ) -> None:
        self._values: dict[str, tuple[list[datetime], list[dict]]] = {}
        first_day = start.date()
        final_day = deadline.date()
        day_count = (final_day - first_day).days + 1
        days = [first_day + timedelta(days=offset) for offset in range(day_count)]
        for edge in edges:
            if edge["kind"] != "scheduled_service":
                continue
            route = routes[edge["routeId"]]
            schedule = edge["schedule"]
            instances = []
            for service_day in days:
                if not service_runs(route, schedule, service_day):
                    continue
                if not scheduled_edge_available(edge, route, service_day):
                    continue
                departure = timing_datetime(
                    schedule.get("departure", {}), service_day,
                    role="departure", profile=profile,
                )
                arrival = timing_datetime(
                    schedule.get("arrival", {}), service_day,
                    role="arrival", profile=profile,
                )
                if departure is None or arrival is None:
                    continue
                while arrival < departure:
                    arrival += timedelta(days=1)
                if arrival == departure and edge["from"] != edge["to"]:
                    continue
                if departure > deadline or arrival < start:
                    continue
                instances.append({
                    "departure": departure,
                    "arrival": arrival,
                    "serviceDate": service_day.isoformat(),
                })
            if instances:
                instances.sort(key=lambda item: item["departure"])
                self._values[edge["id"]] = (
                    [item["departure"] for item in instances], instances,
                )

    def next(self, edge: dict, ready: datetime) -> dict | None:
        value = self._values.get(edge["id"])
        if value is None:
            return None
        departures, instances = value
        index = bisect.bisect_left(departures, ready)
        return instances[index] if index < len(instances) else None

    def minimum_duration_seconds(self, edge: dict) -> int | None:
        value = self._values.get(edge["id"])
        if value is None:
            return None
        return min(
            round((item["arrival"] - item["departure"]).total_seconds())
            for item in value[1]
        )


def prune_return_only_dead_ends(
    adjacency: dict[str, list[dict]], destination: str,
) -> tuple[dict[str, list[dict]], int]:
    """Remove departures whose only onward path revisits their origin node.

    The searches below only consider simple paths: after leaving a node they
    will not return to it. A ferry from a mainland gateway to an island whose
    only exit is the same gateway can therefore never be part of a result.
    The ordinary reverse-reachability check misses this because it sees the
    unusable island -> gateway -> destination walk.

    For each possible departure node, compute destination reachability with
    that node removed. An outgoing edge is safe to discard when its target is
    absent from that set. The calculation is query-local, mode-aware and uses
    the same enabled adjacency as the actual search.
    """
    reverse_adjacency: dict[str, set[str]] = defaultdict(set)
    for from_node, edges in adjacency.items():
        for edge in edges:
            reverse_adjacency[edge["to"]].add(from_node)

    pruned: dict[str, list[dict]] = defaultdict(list)
    removed = 0
    for blocked_node, edges in adjacency.items():
        reachable = {destination}
        queue = deque([destination])
        while queue:
            node_id = queue.popleft()
            for previous_node in reverse_adjacency.get(node_id, ()):
                if previous_node == blocked_node or previous_node in reachable:
                    continue
                reachable.add(previous_node)
                queue.append(previous_node)
        for edge in edges:
            if edge["to"] in reachable:
                pruned[blocked_node].append(edge)
            else:
                removed += 1
    return pruned, removed


def service_signature(records: list[dict]) -> tuple:
    return tuple(
        (
            item["edge"].get("routeId"),
            item["edge"].get("tripPatternId"),
            item["instance"]["departure"].isoformat(),
            item["edge"]["from"],
            item["edge"]["to"],
        )
        for item in records
        if item["edge"]["kind"] != "road"
    )


def prefix_road_shift(
    records: list[dict], routes: dict[str, dict], mode: str,
    not_before: datetime | None = None,
) -> tuple[timedelta, int | None]:
    """Move an all-road prefix later so the first ferry is reached just in time."""
    first_service_index = next(
        (index for index, item in enumerate(records) if item["edge"]["kind"] != "road"),
        None,
    )
    if first_service_index is None or first_service_index == 0:
        return timedelta(0), first_service_index
    first_service = records[first_service_index]
    readiness = loading_readiness_minutes(
        routes[first_service["edge"]["routeId"]], first_service["edge"]["from"], mode,
    )
    boarding_buffer = readiness + default_origin_boarding_buffer_minutes(
        records, first_service_index,
    )
    target = first_service["instance"]["departure"] - timedelta(
        minutes=boarding_buffer
    )
    current_arrival = records[first_service_index - 1]["instance"]["arrival"]
    shift = target - current_arrival
    if not_before is not None:
        first_departure = records[0]["instance"]["departure"]
        shift = max(shift, not_before - first_departure)
    return shift, first_service_index


def partial_origin_departure(
    records: list[dict], routes: dict[str, dict], start: datetime, mode: str,
) -> datetime:
    if not records:
        return start
    shift, _ = prefix_road_shift(records, routes, mode, start)
    return records[0]["instance"]["departure"] + shift


def published_road_connection(
    records: list[dict], index: int, routes: dict[str, dict],
) -> dict | None:
    if index < 2 or records[index - 1]["edge"]["kind"] != "road":
        return None
    current = records[index]
    feeder = records[index - 2]
    if feeder["edge"]["kind"] != "scheduled_service":
        return None
    road_edge = records[index - 1]["edge"]
    feeder_route = routes[feeder["edge"]["routeId"]]
    feeder_arrival = feeder["instance"]["arrival"]
    elapsed = round(
        (current["instance"]["departure"] - feeder_arrival).total_seconds() / 60
    )
    for connection in feeder_route.get("connections", []):
        if (
            connection.get("type") == "published_road_connection"
            and connection.get("fromStop") == road_edge["from"]
            and connection.get("toStop") == road_edge["to"]
            and connection.get("toRouteId") == current["edge"].get("routeId")
            and feeder_arrival.strftime("%H:%M") in connection.get("arrivalTimes", [])
            and 0 <= elapsed <= connection.get("maximumMinutesFromArrivalToDeparture", 0)
        ):
            return {
                "guaranteed": bool(connection.get("guaranteed")),
                "source": "published_timetable",
            }
    return None


def same_provider_direct_ferry_connection(
    records: list[dict], index: int, routes: dict[str, dict],
) -> dict | None:
    """Recognize a direct same-port transfer between one provider's ferries."""
    if index < 1:
        return None
    current = records[index]
    feeder = records[index - 1]
    if (
        current["edge"]["kind"] != "scheduled_service"
        or feeder["edge"]["kind"] != "scheduled_service"
        or feeder["edge"]["to"] != current["edge"]["from"]
        or feeder["instance"]["arrival"] > current["instance"]["departure"]
    ):
        return None
    feeder_route = routes[feeder["edge"]["routeId"]]
    current_route = routes[current["edge"]["routeId"]]
    provider = feeder_route.get("provider")
    if not provider or provider != current_route.get("provider"):
        return None
    return {
        "guaranteed": False,
        "source": "same_provider_direct_ferry_transfer",
    }


def annotate_transit_charge(legs: list[dict]) -> dict | None:
    """Mark an Åland transit charge only for a complete gateway-to-gateway chain."""
    if not legs:
        return None
    locations = [legs[0]["from"], *(leg["to"] for leg in legs)]
    location_set = set(locations)
    for leg in legs:
        policy = (leg.get("travelerInformation") or {}).get("farePolicy") or {}
        for pair in policy.get("transitChargePairs", []):
            start, end = pair.get("from"), pair.get("to")
            if not start or not end or not {start, end}.issubset(location_set):
                continue
            endpoint = pair.get("chargeLegEndpoint")
            charged_leg = next(
                (
                    candidate for candidate in legs
                    if candidate.get("routeId") == leg.get("routeId")
                    and endpoint in {candidate.get("from"), candidate.get("to")}
                ),
                leg,
            )
            charged_leg["fare"] = {
                "paid": True,
                "chargeType": "aland_archipelago_transit",
            }
            return {
                "paid": True,
                "transitCharge": True,
                "transitPair": {"from": start, "to": end},
            }
    return None


def format_candidate(
    records: list[dict], routes: dict[str, dict], start: datetime, destination_arrival: datetime,
    mode: str, timing_profile: str, trip_patterns: dict[str, dict],
) -> dict:
    shift, first_service_index = prefix_road_shift(records, routes, mode, start)
    legs = []
    risk_counts = Counter()
    worst_risk = None

    for index, item in enumerate(records):
        edge, instance, ready = item["edge"], item["instance"], item["ready"]
        departure, arrival = instance["departure"], instance["arrival"]
        if shift and edge["kind"] == "road" and all(
            previous["edge"]["kind"] == "road" for previous in records[:index]
        ):
            departure += shift
            arrival += shift
            ready += shift
        elif shift and index == first_service_index:
            ready += shift
        leg = {
            "index": index + 1,
            "kind": edge["kind"],
            "from": edge["from"],
            "to": edge["to"],
            "readyAtOrigin": ready.isoformat(timespec="minutes"),
            "departure": departure.isoformat(timespec="minutes"),
            "arrival": arrival.isoformat(timespec="minutes"),
            "waitMinutes": round((departure - ready).total_seconds() / 60),
        }
        if edge["kind"] == "road":
            leg.update({
                "distanceMeters": instance["road"]["distanceMeters"],
                "durationMinutes": round((arrival - departure).total_seconds() / 60),
            })
            if edge.get("externalRouting"):
                leg["externalRouting"] = edge["externalRouting"]
        else:
            route = routes[edge["routeId"]]
            vessel = operating_vessel(route, edge, trip_patterns)
            leg.update({
                "routeId": edge["routeId"],
                "tripPatternId": edge.get("tripPatternId"),
                "serviceType": edge.get("serviceType"),
                "operator": commercial_operator(route),
                "vessel": vessel.get("name") if vessel else None,
                "mobilityRule": edge.get("mobility", {}).get(mode),
                "booking": routing_booking_requirement(
                    edge, route, date.fromisoformat(instance["serviceDate"]),
                    instance["departure"], instance["arrival"], trip_patterns, mode,
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

            published_connection = (
                published_road_connection(records, index, routes)
                or same_provider_direct_ferry_connection(records, index, routes)
            )
            if published_connection:
                leg["publishedConnection"] = published_connection

            if edge["kind"] == "scheduled_service" and any(
                previous["edge"]["kind"] != "road" for previous in records[:index]
            ):
                readiness = loading_readiness_minutes(route, edge["from"], mode)
                risk = transfer_risk(leg["waitMinutes"], readiness)
                if published_connection and RISK_ORDER[risk["level"]] > RISK_ORDER["normal"]:
                    risk["level"] = "normal"
                leg["transferRisk"] = risk
                risk_counts[risk["level"]] += 1
                if worst_risk is None or RISK_ORDER[risk["level"]] > RISK_ORDER[worst_risk]:
                    worst_risk = risk["level"]
        legs.append(leg)

    suggested_departure = legs[0]["departure"] if legs else start.isoformat(timespec="minutes")
    result = {
        "suggestedOriginDeparture": suggested_departure,
        "arrival": destination_arrival.isoformat(timespec="minutes"),
        "elapsedFromSuggestedDepartureMinutes": round(
            (destination_arrival - datetime.fromisoformat(suggested_departure)).total_seconds() / 60
        ),
        "timingProfile": timing_profile,
        "riskSummary": {
            "worstConnectionRisk": worst_risk,
            "counts": dict(sorted(risk_counts.items())),
        },
        "legs": legs,
    }
    fare_summary = annotate_transit_charge(legs)
    if fare_summary:
        result["fareSummary"] = fare_summary
    return result


def edge_instance(
    edge: dict, routes: dict[str, dict], moment: datetime, mode: str, timing_profile: str,
    *, enforce_loading_readiness: bool = False,
    continuous_approach_minutes: int = 0,
    scheduled_instances: ScheduledInstanceIndex | None = None,
) -> dict | None:
    if edge["kind"] == "road":
        duration_seconds, details = road_duration(edge, mode)  # type: ignore[misc]
        return {
            "departure": moment,
            "arrival": moment + timedelta(seconds=duration_seconds),
            "road": details,
        }
    if edge["kind"] == "scheduled_service":
        route = routes[edge["routeId"]]
        readiness = (
            loading_readiness_minutes(route, edge["from"], mode)
            if enforce_loading_readiness else 0
        )
        boarding_ready = moment + timedelta(minutes=readiness)
        if scheduled_instances is not None:
            return scheduled_instances.next(edge, boarding_ready)
        return next_scheduled_instance(edge, route, boarding_ready, timing_profile)
    return next_continuous_instance(
        edge, moment + timedelta(minutes=continuous_approach_minutes),
    )


def is_redundant_consecutive_road(records: list[dict], edge: dict) -> bool:
    """Whether this road edge would unnecessarily split one road journey.

    Each drivable road component is represented by direct edges between all
    routing stops in that component. Query-specific address access and egress
    edges follow the same rule, so a road-to-road chain cannot add reachability.
    """
    return bool(
        records
        and records[-1]["edge"]["kind"] == "road"
        and edge["kind"] == "road"
    )


def minimum_remaining_travel_seconds(
    adjacency: dict[str, list[dict]], destination: str, mode: str,
    scheduled_instances: ScheduledInstanceIndex | None = None,
) -> dict[str, int]:
    """Admissible destination heuristic shared by all seed-sweep searches.

    Road and known crossing durations are unavoidable, while all ferry waiting
    is valued at zero. The result can therefore only underestimate the
    remaining journey time and is safe for ordering an exact earliest-arrival
    search.
    """
    reverse_edges: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for from_node, edges in adjacency.items():
        for edge in edges:
            seconds = 0
            if edge["kind"] == "road":
                duration = road_duration(edge, mode)
                if duration is None:
                    continue
                seconds = duration[0]
            elif edge["kind"] == "continuous_ferry":
                seconds = round(edge["crossingMinutes"] * 60)
            elif scheduled_instances is not None:
                seconds = scheduled_instances.minimum_duration_seconds(edge) or 0
            reverse_edges[edge["to"]].append((from_node, seconds))

    minimum = {destination: 0}
    queue = [(0, destination)]
    while queue:
        seconds, node_id = heapq.heappop(queue)
        if seconds != minimum.get(node_id):
            continue
        for previous_node, edge_seconds in reverse_edges.get(node_id, []):
            candidate = seconds + edge_seconds
            if candidate < minimum.get(previous_node, sys.maxsize):
                minimum[previous_node] = candidate
                heapq.heappush(queue, (candidate, previous_node))
    return minimum


def earliest_candidate_from_seed(
    adjacency: dict[str, list[dict]], routes: dict[str, dict], origin: str, destination: str,
    seed: datetime, deadline: datetime, mode: str, timing_profile: str, max_legs: int,
    scheduled_instances: ScheduledInstanceIndex | None = None,
    minimum_legs_to_destination: dict[str, int] | None = None,
    minimum_remaining_seconds: dict[str, int] | None = None,
    search_stats: Counter | None = None,
) -> tuple[list[dict], datetime] | None:
    """Return the earliest feasible itinerary after one exact origin seed.

    Running this small earliest-arrival search for each origin seed complements
    the diverse-label search below. In particular, a later useful feeder must
    not disappear merely because an earlier label reached the same road node.
    """
    serial = itertools.count()
    heuristic = minimum_remaining_seconds or {}
    queue = [(
        seed + timedelta(seconds=heuristic.get(origin, 0)),
        next(serial), seed, origin, [], (origin,), None, False, None,
    )]
    best: dict[tuple[str, str | None, datetime | None], datetime] = {}
    while queue:
        (
            _, _, moment, node_id, records, visited_nodes, last_trip,
            has_used_service, first_service_departure,
        ) = heapq.heappop(queue)
        state = (node_id, last_trip, first_service_departure)
        if moment >= best.get(state, datetime.max):
            continue
        best[state] = moment
        if node_id == destination:
            return records, moment
        journey_deadline = (
            first_service_departure + MAX_FERRY_CHAIN_DURATION
            if first_service_departure else None
        )
        if journey_deadline is not None and moment > journey_deadline:
            continue
        if moment > deadline or len(records) >= max_legs:
            continue
        if search_stats is not None:
            search_stats["expandedLabels"] += 1
        for edge in adjacency.get(node_id, []):
            if is_redundant_consecutive_road(records, edge):
                continue
            if minimum_legs_to_destination is not None and (
                edge["to"] not in minimum_legs_to_destination
                or len(records) + 1 + minimum_legs_to_destination[edge["to"]] > max_legs
            ):
                continue
            if edge["to"] in visited_nodes and edge["to"] != destination:
                continue
            if (
                last_trip
                and edge["kind"] == "scheduled_service"
                and edge.get("tripPatternId") == last_trip
            ):
                # Direct ride edges already span every intermediate call.
                continue
            instance = edge_instance(
                edge, routes, moment, mode, timing_profile,
                enforce_loading_readiness=not has_used_service,
                continuous_approach_minutes=(
                    CONTINUOUS_FERRY_APPROACH_MINUTES
                    if records and records[-1]["edge"]["kind"] == "road"
                    else 0
                ),
                scheduled_instances=scheduled_instances,
            )
            if not instance or (
                instance["arrival"] > deadline
                and not (edge["kind"] == "road" and edge["to"] == destination)
            ):
                continue
            next_first_service_departure = first_service_departure
            if next_first_service_departure is None and edge["kind"] != "road":
                next_first_service_departure = instance["departure"]
            next_journey_deadline = (
                next_first_service_departure + MAX_FERRY_CHAIN_DURATION
                if next_first_service_departure else None
            )
            if (
                next_journey_deadline is not None
                and instance["arrival"] > next_journey_deadline
                and not (
                    edge["kind"] == "road" and edge["to"] == destination
                )
            ):
                continue
            record = {"edge": edge, "instance": instance, "ready": moment}
            next_last_trip = (
                edge.get("tripPatternId")
                if edge["kind"] == "scheduled_service" else None
            )
            heapq.heappush(queue, (
                instance["arrival"] + timedelta(
                    seconds=heuristic.get(edge["to"], 0),
                ),
                next(serial), instance["arrival"], edge["to"], records + [record],
                visited_nodes + (edge["to"],),
                next_last_trip, has_used_service or edge["kind"] != "road",
                next_first_service_departure,
            ))
    return None


def next_adaptive_sweep_seeds(
    records: list[dict],
    seed: datetime,
    routes: dict[str, dict],
    deadline: datetime,
    mode: str,
) -> list[datetime]:
    """Return the next meaningful origin times for one earliest itinerary.

    Before the first scheduled departure, road and continuous-ferry legs move
    with the origin time. The itinerary changes only at a transfer-risk
    boundary or when that scheduled departure can no longer be reached. A
    fixed 30-minute sweep therefore repeats the same search many times and can
    still miss a boundary by almost half an hour.
    """
    has_used_service = False
    for item in records:
        edge = item["edge"]
        if edge["kind"] != "scheduled_service":
            has_used_service |= edge["kind"] != "road"
            continue
        instance = item["instance"]
        ready = item["ready"]
        route = routes[edge["routeId"]]
        readiness = (
            loading_readiness_minutes(route, edge["from"], mode)
            if not has_used_service else 0
        )
        catch_slack = round(
            (instance["departure"] - ready).total_seconds() / 60
        ) - readiness
        values = []
        # One minute beyond the usable slack forces the earliest-arrival
        # search to select a different first scheduled departure.
        if catch_slack >= 0:
            values.append(seed + timedelta(minutes=catch_slack + 1))
        if has_used_service:
            booking_readiness = loading_readiness_minutes(route, edge["from"], mode)
            effective_buffer = round(
                (instance["departure"] - ready).total_seconds() / 60
            ) - booking_readiness
            # Last whole-minute value in each weaker risk class. Crossing the
            # threshold produces normal, tight, very tight and finally a
            # below-readiness alternative when each is feasible.
            for target_buffer in (29, 5, 4, 0, -1):
                shift = effective_buffer - target_buffer
                if shift > 0:
                    values.append(seed + timedelta(minutes=shift))
        future_values = sorted({value for value in values if seed < value <= deadline})
        # Advance to the closest boundary only. Later boundaries are discovered
        # from the next earliest itinerary; enqueueing every boundary here
        # creates a branching sweep and repeats the same searches.
        return future_values[:1]
    return []


def candidate_sweep_seed(candidate: dict, deadline: datetime) -> datetime | None:
    """First origin minute at which this candidate's first schedule is missed."""
    origin_departure = datetime.fromisoformat(candidate["suggestedOriginDeparture"])
    has_used_service = False
    for index, leg in enumerate(candidate["legs"]):
        if leg["kind"] != "scheduled_service":
            has_used_service |= leg["kind"] != "road"
            continue
        departure = datetime.fromisoformat(leg["departure"])
        ready = datetime.fromisoformat(leg["readyAtOrigin"])
        readiness = 0
        if not has_used_service:
            readiness = (leg.get("booking") or {}).get(
                "loadingReadinessMinutesBefore", 0,
            )
        if index == 0:
            seed = departure - timedelta(minutes=readiness) + timedelta(minutes=1)
            return seed if seed <= deadline else None
        catch_slack = round((departure - ready).total_seconds() / 60) - readiness
        seed = origin_departure + timedelta(minutes=max(0, catch_slack) + 1)
        return seed if seed <= deadline else None
    return None


def candidate_dominates(first: dict, second: dict) -> bool:
    """Whether first is unambiguously preferable to second."""
    first_operators = tuple(
        leg["operator"] for leg in first["legs"] if leg.get("operator")
    )
    second_operators = tuple(
        leg["operator"] for leg in second["legs"] if leg.get("operator")
    )
    # A traveller may deliberately prefer Viking Line, Tallink Silja or
    # Finnlines even when another operator is faster. Keep one result per
    # commercial operator chain for the UI to compare.
    if (first_operators or second_operators) and first_operators != second_operators:
        return False
    first_departure = datetime.fromisoformat(first["suggestedOriginDeparture"])
    second_departure = datetime.fromisoformat(second["suggestedOriginDeparture"])
    first_arrival = datetime.fromisoformat(first["arrival"])
    second_arrival = datetime.fromisoformat(second["arrival"])
    first_risk = RISK_ORDER.get(first["riskSummary"]["worstConnectionRisk"], -1)
    second_risk = RISK_ORDER.get(second["riskSummary"]["worstConnectionRisk"], -1)
    # A relaxed connection is not intrinsically better than a normal one if
    # both lead through the same services to the same arrival. In that case
    # retain the later useful feeder: waiting at the preceding ferry landing
    # is not a passenger benefit.
    first_shape = tuple(
        (leg["kind"], leg.get("routeId"), leg["from"], leg["to"])
        for leg in first["legs"]
    )
    second_shape = tuple(
        (leg["kind"], leg.get("routeId"), leg["from"], leg["to"])
        for leg in second["legs"]
    )
    comparable_safe_feeders = (
        first_arrival == second_arrival
        and first_risk <= RISK_ORDER["normal"]
        and second_risk <= RISK_ORDER["normal"]
        and first_shape == second_shape
    )
    if comparable_safe_feeders:
        return (
            candidate_departure_preference(first)
            > candidate_departure_preference(second)
        )

    no_worse = (
        first_departure >= second_departure
        and first_arrival <= second_arrival
        and first_risk <= second_risk
    )
    strictly_better = (
        first_departure > second_departure
        or first_arrival < second_arrival
        or first_risk < second_risk
    )
    if no_worse and strictly_better:
        return True

    # Do not preserve a long detour merely because it has a looser transfer.
    # If both candidates board the same physical sailing, the better one gets
    # off earlier, reaches the destination earlier with no more ferry legs,
    # and still satisfies a normal connection margin, continuing past that
    # useful stop and returning through another ferry is never worthwhile.
    first_services = [
        leg for leg in first["legs"] if leg["kind"] == "scheduled_service"
    ]
    second_services = [
        leg for leg in second["legs"] if leg["kind"] == "scheduled_service"
    ]
    first_instances = {
        (leg.get("routeId"), leg.get("tripPatternId"), leg["departure"])
        for leg in first_services
    }
    second_instances = {
        (leg.get("routeId"), leg.get("tripPatternId"), leg["departure"])
        for leg in second_services
    }
    redundant_same_sailing_detour = (
        first_departure >= second_departure
        and first_arrival < second_arrival
        and first_risk <= RISK_ORDER["normal"]
        and len(first_services) <= len(second_services)
        and bool(first_instances & second_instances)
    )
    return redundant_same_sailing_detour


def candidate_departure_preference(candidate: dict) -> tuple:
    """Prefer later useful legs when otherwise selecting the same risk class."""
    return (
        candidate["suggestedOriginDeparture"],
        tuple(
            leg["departure"]
            for leg in candidate["legs"]
            if leg["kind"] != "road"
        ),
    )


def build_decision_graph(candidates: list[dict], origin: str, destination: str) -> dict:
    """Compact complete candidate paths into a time-expanded decision graph.

    Equal place-and-time states and equal following legs are shared. This
    preserves locally safer prefixes that the normal itinerary list may omit,
    while avoiding a full copy of every common suffix.
    """
    nodes: dict[tuple[str, str], dict] = {}
    connections: dict[str, dict] = {}
    connection_keys: dict[str, str] = {}
    origin_node_ids = set()
    destination_node_ids = set()

    def node_id(location: str, timestamp: str) -> str:
        key = (location, timestamp)
        if key not in nodes:
            identifier = f"n{len(nodes) + 1}"
            nodes[key] = {
                "id": identifier,
                "location": location,
                "time": timestamp,
            }
        return nodes[key]["id"]

    for candidate in candidates:
        legs = candidate.get("legs", [])
        if not legs:
            continue
        origin_node_ids.add(node_id(origin, legs[0]["readyAtOrigin"]))
        for leg in legs:
            from_node = node_id(leg["from"], leg["readyAtOrigin"])
            to_node = node_id(leg["to"], leg["arrival"])
            public_leg = {key: value for key, value in leg.items() if key != "index"}
            key = json.dumps(
                [from_node, to_node, public_leg],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            if key not in connection_keys:
                identifier = f"c{len(connections) + 1}"
                connection_keys[key] = identifier
                connections[identifier] = {
                    "id": identifier,
                    "fromNode": from_node,
                    "toNode": to_node,
                    "leg": public_leg,
                }
        destination_node_ids.add(node_id(destination, legs[-1]["arrival"]))

    transfer_groups: dict[tuple, list[dict]] = defaultdict(list)
    for connection in connections.values():
        leg = connection["leg"]
        risk = leg.get("transferRisk")
        if leg["kind"] != "scheduled_service" or risk is None:
            continue
        service_key = (
            leg.get("routeId"), leg.get("tripPatternId"), leg["from"], leg["to"],
            leg["departure"], leg["arrival"],
        )
        transfer_groups[service_key].append({
            "connectionId": connection["id"],
            "readyAtOrigin": leg["readyAtOrigin"],
            "waitMinutes": leg["waitMinutes"],
            "risk": risk,
        })

    transfer_choices = []
    for service_key, variants in transfer_groups.items():
        best_by_level = {}
        for variant in variants:
            level = variant["risk"]["level"]
            previous = best_by_level.get(level)
            if previous is None or variant["readyAtOrigin"] > previous["readyAtOrigin"]:
                best_by_level[level] = variant
        variants = list(best_by_level.values())
        if len(variants) < 2:
            continue
        route_id, trip_pattern_id, from_stop, to_stop, departure, arrival = service_key
        variants.sort(
            key=lambda item: (
                RISK_ORDER[item["risk"]["level"]],
                -item["risk"]["effectiveBufferMinutes"],
                item["readyAtOrigin"],
            )
        )
        transfer_choices.append({
            "id": f"t{len(transfer_choices) + 1}",
            "service": {
                "routeId": route_id,
                "tripPatternId": trip_pattern_id,
                "from": from_stop,
                "to": to_stop,
                "departure": departure,
                "arrival": arrival,
            },
            "variants": variants,
        })

    return {
        "candidatePathCount": len(candidates),
        "nodes": list(nodes.values()),
        "connections": list(connections.values()),
        "originNodeIds": sorted(origin_node_ids),
        "destinationNodeIds": sorted(destination_node_ids),
        "transferChoices": transfer_choices,
    }


def find_itineraries(
    origin: str,
    destination: str,
    travel_date: date,
    start_time: time = time(0, 0),
    *,
    mode: str = "car",
    timing_profile: str = "typical",
    max_results: int = 12,
    max_results_per_final_service: int = 3,
    max_candidates: int = 1000,
    max_labels_per_node_hour: int = 20,
    max_legs: int = 12,
    include_seed_sweep: bool = True,
    include_decision_graph: bool = False,
    same_day: bool = False,
    graph_path: Path = DEFAULT_GRAPH,
    graph_data: dict | None = None,
) -> dict:
    """Return distinct useful itineraries as a reusable Python API."""
    if mode not in {"car", "motorcycle", "bicycle"}:
        raise ValueError(f"unsupported mode: {mode}")
    if timing_profile not in {"typical", "conservative"}:
        raise ValueError(f"unsupported timing profile: {timing_profile}")
    args = argparse.Namespace(
        origin=origin,
        destination=destination,
        travel_date=travel_date,
        start_time=start_time,
        mode=mode,
        timing_profile=timing_profile,
        max_results=max_results,
        max_results_per_final_service=max_results_per_final_service,
        max_candidates=max_candidates,
        max_labels_per_node_hour=max_labels_per_node_hour,
        max_legs=max_legs,
        same_day=same_day,
        graph=graph_path,
    )
    graph = graph_data if graph_data is not None else json.loads(args.graph.read_text())
    # Route dictionaries receive a query-local schedule index below. Keep the
    # large graph immutable so a long-lived service can safely reuse it across
    # requests without deep-copying nearly ten thousand edges.
    routes = {
        item["id"]: {**item, "_schedules": []}
        for item in graph["routes"]
    }
    trip_patterns = {item["id"]: item for item in graph["tripPatterns"]}
    nodes = {item["id"]: item for item in graph["nodes"]}
    for value, label in ((args.origin, "origin"), (args.destination, "destination")):
        if value not in nodes:
            raise ValueError(f"unknown {label}: {value}")

    adjacency: dict[str, list[dict]] = defaultdict(list)
    skipped_continuous_unknown = 0
    excluded_route_ids = nonlocal_route_ids(
        graph["edges"], args.origin, args.destination, args.mode,
    )
    skipped_nonlocal_edges = 0
    for edge in graph["edges"]:
        if not edge.get("enabledForAutomaticRouting", True):
            continue
        if edge.get("routeId") in excluded_route_ids:
            skipped_nonlocal_edges += 1
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

    adjacency, _ = prune_return_only_dead_ends(
        adjacency, args.destination,
    )

    start = datetime.combine(args.travel_date, args.start_time)
    # Waiting for the first sailing is not journey time. Search one complete
    # weekly timetable cycle for that sailing, then allow at most twelve hours
    # from its departure to the final pier. A final road leg may finish later.
    deadline = start + INITIAL_SERVICE_LOOKAHEAD + MAX_FERRY_CHAIN_DURATION
    scheduled_instances = ScheduledInstanceIndex(
        [edge for edges in adjacency.values() for edge in edges],
        routes, start, deadline, args.timing_profile,
    )
    minimum_remaining_seconds = minimum_remaining_travel_seconds(
        adjacency, args.destination, args.mode, scheduled_instances,
    )
    reverse_adjacency: dict[str, set[str]] = defaultdict(set)
    for from_node, edges in adjacency.items():
        for edge in edges:
            reverse_adjacency[edge["to"]].add(from_node)
    minimum_legs_to_destination = {args.destination: 0}
    reverse_queue = deque([args.destination])
    while reverse_queue:
        node_id = reverse_queue.popleft()
        next_distance = minimum_legs_to_destination[node_id] + 1
        for previous_node in reverse_adjacency.get(node_id, ()):
            if previous_node not in minimum_legs_to_destination:
                minimum_legs_to_destination[previous_node] = next_distance
                reverse_queue.append(previous_node)
    serial = itertools.count()
    # The diverse search needs one initial label. Later useful departures are
    # covered explicitly by the bounded earliest-arrival sweep below. Seeding
    # both searches every 30 minutes duplicated most of the state space,
    # particularly for a three-day query.
    queue = [(
        start, next(serial), args.origin, [], (args.origin,),
        start, "relaxed", False, None,
    )]
    accepted_per_node_hour = Counter()
    pareto_frontiers: dict[tuple, list[tuple[datetime, datetime]]] = defaultdict(list)
    candidates_by_signature = {}
    expansions = 0
    first_result_day_deadline: datetime | None = None

    while queue and len(candidates_by_signature) < args.max_candidates:
        (
            moment, _, node_id, records, visited_nodes,
            origin_departure, worst_risk, has_used_service,
            first_service_departure,
        ) = heapq.heappop(queue)
        if first_result_day_deadline is not None and moment > first_result_day_deadline:
            break
        if moment > deadline and node_id != args.destination:
            continue
        journey_deadline = (
            first_service_departure + MAX_FERRY_CHAIN_DURATION
            if first_service_departure else None
        )
        if (
            journey_deadline is not None
            and moment > journey_deadline
            and not (
                node_id == args.destination
                and records
                and records[-1]["edge"]["kind"] == "road"
            )
        ):
            continue
        # Keep the feeder sailing identity across a following road leg. Two
        # different ferries can reach the same island road network and still
        # catch the same onward departure; collapsing them at the road node
        # would always retain the earliest feeder and hide later useful ones.
        recent_trips = tuple(reversed([
            (
                item["edge"].get("routeId"),
                item["edge"].get("tripPatternId"),
                item["instance"]["departure"].isoformat(),
            )
            for item in reversed(records)
            if item["edge"]["kind"] == "scheduled_service"
        ][:2]))
        # Whether a vessel has already been used changes both first-boarding
        # readiness enforcement and transfer-risk semantics. It is therefore
        # part of the routing state, especially after continuous road ferries
        # which have no tripPatternId of their own.
        state_key = (
            node_id, recent_trips, worst_risk, has_used_service,
            first_service_departure,
        )
        frontier = pareto_frontiers[state_key]
        if any(
            previous_arrival <= moment and previous_departure >= origin_departure
            for previous_arrival, previous_departure in frontier
        ):
            continue
        pareto_frontiers[state_key] = [
            (previous_arrival, previous_departure)
            for previous_arrival, previous_departure in frontier
            if not (
                moment <= previous_arrival
                and origin_departure >= previous_departure
            )
        ]
        pareto_frontiers[state_key].append((moment, origin_departure))
        if node_id == args.destination:
            if first_result_day_deadline is None:
                first_result_day_deadline = datetime.combine(
                    moment.date(), time(23, 59, 59),
                )
            signature = service_signature(records)
            final_service = signature[-1] if signature else ("road_only",)
            candidate = format_candidate(
                records, routes, start, moment, args.mode, args.timing_profile, trip_patterns
            )
            candidate["_finalService"] = final_service
            previous_candidate = candidates_by_signature.get(signature)
            if (
                previous_candidate is None
                or candidate["suggestedOriginDeparture"] > previous_candidate["suggestedOriginDeparture"]
            ):
                candidates_by_signature[signature] = candidate
            continue
        hour_bucket = moment.replace(minute=0, second=0, microsecond=0)
        label_bucket = (
            node_id, hour_bucket, worst_risk, recent_trips,
            first_service_departure,
        )
        accepted_per_node_hour[label_bucket] += 1
        if accepted_per_node_hour[label_bucket] > args.max_labels_per_node_hour:
            continue
        if len(records) >= args.max_legs:
            continue
        expansions += 1

        for edge in adjacency.get(node_id, []):
            if is_redundant_consecutive_road(records, edge):
                continue
            if (
                edge["to"] not in minimum_legs_to_destination
                or len(records) + 1 + minimum_legs_to_destination[edge["to"]] > args.max_legs
            ):
                continue
            if edge["to"] in visited_nodes and edge["to"] != args.destination:
                continue
            if (
                records
                and edge["kind"] == "scheduled_service"
                and records[-1]["edge"]["kind"] == "scheduled_service"
                and edge.get("tripPatternId") == records[-1]["edge"].get("tripPatternId")
            ):
                # The graph already has a direct ride edge across every
                # intermediate call. Splitting the same vessel trip here would
                # manufacture a transfer where the passenger stays on board.
                continue
            instance = edge_instance(
                edge, routes, moment, args.mode, args.timing_profile,
                enforce_loading_readiness=not has_used_service,
                continuous_approach_minutes=(
                    CONTINUOUS_FERRY_APPROACH_MINUTES
                    if records and records[-1]["edge"]["kind"] == "road"
                    else 0
                ),
                scheduled_instances=scheduled_instances,
            )
            if not instance:
                continue
            if (
                instance["arrival"] > deadline
                and not (
                    edge["kind"] == "road" and edge["to"] == args.destination
                )
            ):
                continue
            next_first_service_departure = first_service_departure
            if next_first_service_departure is None and edge["kind"] != "road":
                next_first_service_departure = instance["departure"]
            next_journey_deadline = (
                next_first_service_departure + MAX_FERRY_CHAIN_DURATION
                if next_first_service_departure else None
            )
            if (
                next_journey_deadline is not None
                and instance["arrival"] > next_journey_deadline
                and not (
                    edge["kind"] == "road"
                    and edge["to"] == args.destination
                )
            ):
                continue
            record = {"edge": edge, "instance": instance, "ready": moment}
            next_records = records + [record]
            next_has_used_service = has_used_service or edge["kind"] != "road"
            next_origin_departure = origin_departure
            if not records and edge["kind"] == "road":
                next_origin_departure = instance["departure"]
            if not has_used_service and edge["kind"] != "road":
                next_origin_departure = partial_origin_departure(
                    next_records, routes, start, mode,
                )
            next_worst_risk = worst_risk
            if has_used_service and edge["kind"] != "road":
                route = routes[edge["routeId"]]
                wait = round(
                    (instance["departure"] - moment).total_seconds() / 60
                )
                readiness = loading_readiness_minutes(route, edge["from"], mode)
                level = transfer_risk(wait, readiness)["level"]
                if (
                    published_road_connection(next_records, len(next_records) - 1, routes)
                    and RISK_ORDER[level] > RISK_ORDER["normal"]
                ):
                    level = "normal"
                if RISK_ORDER[level] > RISK_ORDER[next_worst_risk]:
                    next_worst_risk = level
            heapq.heappush(queue, (
                instance["arrival"], next(serial), edge["to"], next_records,
                visited_nodes + (edge["to"],), next_origin_departure,
                next_worst_risk, next_has_used_service,
                next_first_service_departure,
            ))

    # Preserve useful later-departure chains that the bounded diverse-label
    # search may prune at a shared road node. Each seed contributes its one
    # earliest-arrival itinerary; identical ferry sequences are deduplicated.
    swept_seed_count = 0
    swept_candidate_count = 0
    swept_jump_count = 0
    sweep_stats = Counter()
    if include_seed_sweep:
        sweep_deadline = first_result_day_deadline or deadline
        pending_seeds = [start]
        seen_seeds = set()
        while pending_seeds:
            seed = heapq.heappop(pending_seeds)
            if seed in seen_seeds or seed > sweep_deadline:
                continue
            seen_seeds.add(seed)
            swept_seed_count += 1
            found = earliest_candidate_from_seed(
                adjacency, routes, args.origin, args.destination, seed, sweep_deadline,
                args.mode, args.timing_profile, args.max_legs, scheduled_instances,
                minimum_legs_to_destination, minimum_remaining_seconds, sweep_stats,
            )
            if not found:
                continue
            records, arrival = found
            signature = service_signature(records)
            final_service = signature[-1] if signature else ("road_only",)
            candidate = format_candidate(
                records, routes, start, arrival, args.mode, args.timing_profile, trip_patterns
            )
            candidate["_finalService"] = final_service
            previous_candidate = candidates_by_signature.get(signature)
            if (
                previous_candidate is None
                or candidate["suggestedOriginDeparture"] > previous_candidate["suggestedOriginDeparture"]
            ):
                candidates_by_signature[signature] = candidate
                swept_candidate_count += 1
            next_seeds = next_adaptive_sweep_seeds(
                records, seed, routes, sweep_deadline, args.mode,
            )
            reusable_candidates = [
                item for item in candidates_by_signature.values()
                if item["_finalService"] == final_service
                and item["arrival"] == candidate["arrival"]
                and item["riskSummary"]["worstConnectionRisk"]
                == candidate["riskSummary"]["worstConnectionRisk"]
                and item["suggestedOriginDeparture"]
                > candidate["suggestedOriginDeparture"]
            ]
            if next_seeds and reusable_candidates:
                latest_known = max(
                    reusable_candidates,
                    key=lambda item: item["suggestedOriginDeparture"],
                )
                reusable_seed = candidate_sweep_seed(
                    latest_known, sweep_deadline,
                )
                if reusable_seed is not None and reusable_seed > next_seeds[0]:
                    next_seeds = [reusable_seed]
                    swept_jump_count += 1
            for next_seed in next_seeds:
                if next_seed not in seen_seeds:
                    heapq.heappush(pending_seeds, next_seed)

    candidates = list(candidates_by_signature.values())
    decision_graph = (
        build_decision_graph(candidates, args.origin, args.destination)
        if include_decision_graph else None
    )
    candidates = [
        candidate for candidate in candidates
        if not any(
            other is not candidate and candidate_dominates(other, candidate)
            for other in candidates
        )
    ]
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate["_finalService"]].append(candidate)
    selected = []
    for group in grouped.values():
        group.sort(key=candidate_departure_preference, reverse=True)
        chosen = []
        for risk in RISK_ORDER:
            candidate = next(
                (
                    item for item in group
                    if item["riskSummary"]["worstConnectionRisk"] == risk
                ),
                None,
            )
            if candidate is None:
                continue
            chosen.append(candidate)
            if len(chosen) >= args.max_results_per_final_service:
                break
        if len(chosen) < args.max_results_per_final_service:
            for candidate in group:
                if candidate in chosen:
                    continue
                chosen.append(candidate)
                if len(chosen) >= args.max_results_per_final_service:
                    break
        selected.extend(chosen)

    results = sorted(
        selected,
        key=lambda item: (item["arrival"], item["suggestedOriginDeparture"]),
    )[:args.max_results]
    for item in results:
        item.pop("_finalService", None)
    for index, item in enumerate(results, 1):
        item["rank"] = index
    response = {
        "status": "routes_found" if results else "no_route",
        "origin": args.origin,
        "destination": args.destination,
        "departureNotBefore": start.isoformat(timespec="minutes"),
        "arrivalDeadline": deadline.isoformat(timespec="minutes"),
        "mode": args.mode,
        "timingProfile": args.timing_profile,
        "resultCount": len(results),
        "results": results,
        "diagnostics": {
            "expandedLabels": expansions,
            "candidateCount": len(candidates),
            "skippedContinuousEdgesWithoutCrossingTime": skipped_continuous_unknown,
            "excludedNonlocalRoutes": sorted(excluded_route_ids),
            "skippedNonlocalRouteEdges": skipped_nonlocal_edges,
            "maxLabelsPerNodeHour": args.max_labels_per_node_hour,
            "maxLegs": args.max_legs,
            "maxFerryChainHours": round(
                MAX_FERRY_CHAIN_DURATION.total_seconds() / 3600
            ),
            "sweepStrategy": "adaptive_reused_candidate_boundaries",
            "sweptSeedCount": swept_seed_count,
            "sweptCandidateUpdates": swept_candidate_count,
            "sweptCandidateJumps": swept_jump_count,
            "sweptExpandedLabels": sweep_stats["expandedLabels"],
            "firstResultDayDeadline": (
                first_result_day_deadline.isoformat(timespec="minutes")
                if first_result_day_deadline else None
            ),
            "limitations": [
                "result diversity is based on distinct ferry-service sequences",
                "continuous ferry edges without a known crossing time are not routable",
                "specialized holiday and parity-based break rules still require expansion",
            ],
        },
    }
    if decision_graph is not None:
        response["decisionGraph"] = decision_graph
    return response


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("origin")
    parser.add_argument("destination")
    parser.add_argument("travel_date", type=date.fromisoformat)
    parser.add_argument("start_time", type=parse_clock, nargs="?", default=time(0, 0))
    parser.add_argument("--mode", choices=("car", "motorcycle", "bicycle"), default="car")
    parser.add_argument("--timing-profile", choices=("typical", "conservative"), default="typical")
    parser.add_argument("--max-results", type=int, default=12)
    parser.add_argument("--max-results-per-final-service", type=int, default=3)
    parser.add_argument("--max-candidates", type=int, default=1000)
    parser.add_argument("--max-labels-per-node-hour", type=int, default=20)
    parser.add_argument("--max-legs", type=int, default=12)
    parser.add_argument("--include-decision-graph", action="store_true")
    parser.add_argument("--same-day", action="store_true")
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    args = parser.parse_args()
    try:
        response = find_itineraries(
            args.origin,
            args.destination,
            args.travel_date,
            args.start_time,
            mode=args.mode,
            timing_profile=args.timing_profile,
            max_results=args.max_results,
            max_results_per_final_service=args.max_results_per_final_service,
            max_candidates=args.max_candidates,
            max_labels_per_node_hour=args.max_labels_per_node_hour,
            max_legs=args.max_legs,
            include_decision_graph=args.include_decision_graph,
            same_day=args.same_day,
            graph_path=args.graph,
        )
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(response, ensure_ascii=False, indent=2))
    return 0 if response["status"] == "routes_found" else 2


if __name__ == "__main__":
    raise SystemExit(main())
