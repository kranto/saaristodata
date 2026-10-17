#!/usr/bin/env python3
"""Enumerate distinct time-dependent multimodal itinerary alternatives."""

from __future__ import annotations

import argparse
import copy
import heapq
import itertools
import json
from collections import Counter, defaultdict
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
    routing_booking_requirement,
    routing_intermediate_stops,
    routing_traveler_information,
    transfer_risk,
)


RISK_ORDER = {
    "relaxed": 0,
    "normal": 1,
    "tight": 2,
    "very_tight": 3,
    "below_required_readiness": 4,
}
DEFAULT_ORIGIN_BOARDING_BUFFER_MINUTES = 15


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
    records: list[dict], routes: dict[str, dict], not_before: datetime | None = None,
) -> tuple[timedelta, int | None]:
    """Move an all-road prefix later so the first ferry is reached just in time."""
    first_service_index = next(
        (index for index, item in enumerate(records) if item["edge"]["kind"] != "road"),
        None,
    )
    if first_service_index is None or first_service_index == 0:
        return timedelta(0), first_service_index
    first_service = records[first_service_index]
    readiness = routes[first_service["edge"]["routeId"]].get("booking", {}).get(
        "loadingReadinessMinutesBefore", 0
    )
    boarding_buffer = readiness if readiness else DEFAULT_ORIGIN_BOARDING_BUFFER_MINUTES
    target = first_service["instance"]["departure"] - timedelta(
        minutes=boarding_buffer
    )
    current_arrival = records[first_service_index - 1]["instance"]["arrival"]
    shift = target - current_arrival
    if not_before is not None:
        first_departure = records[0]["instance"]["departure"]
        shift = max(shift, not_before - first_departure)
    return shift, first_service_index


def partial_origin_departure(records: list[dict], routes: dict[str, dict], start: datetime) -> datetime:
    if not records:
        return start
    shift, _ = prefix_road_shift(records, routes, start)
    return records[0]["instance"]["departure"] + shift


def partial_worst_risk(records: list[dict], routes: dict[str, dict]) -> str:
    worst = "relaxed"
    shift, first_service_index = prefix_road_shift(records, routes)
    for index, item in enumerate(records):
        edge = item["edge"]
        if edge["kind"] == "road" or not any(
            previous["edge"]["kind"] != "road" for previous in records[:index]
        ):
            continue
        ready = item["ready"]
        if shift and index == first_service_index:
            ready += shift
        wait = round((item["instance"]["departure"] - ready).total_seconds() / 60)
        readiness = routes[edge["routeId"]].get("booking", {}).get("loadingReadinessMinutesBefore", 0)
        level = transfer_risk(wait, readiness)["level"]
        if RISK_ORDER[level] > RISK_ORDER[worst]:
            worst = level
    return worst


def format_candidate(
    records: list[dict], routes: dict[str, dict], start: datetime, destination_arrival: datetime,
    mode: str, timing_profile: str, trip_patterns: dict[str, dict],
) -> dict:
    shift, first_service_index = prefix_road_shift(records, routes, start)
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
                "vessel": vessel.get("name") if vessel else None,
                "mobilityRule": edge.get("mobility", {}).get(mode),
                "booking": routing_booking_requirement(
                    edge, route, date.fromisoformat(instance["serviceDate"]),
                    instance["departure"], instance["arrival"], trip_patterns,
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

            if edge["kind"] == "scheduled_service" and any(
                previous["edge"]["kind"] != "road" for previous in records[:index]
            ):
                readiness = route.get("booking", {}).get("loadingReadinessMinutesBefore", 0)
                risk = transfer_risk(leg["waitMinutes"], readiness)
                leg["transferRisk"] = risk
                risk_counts[risk["level"]] += 1
                if worst_risk is None or RISK_ORDER[risk["level"]] > RISK_ORDER[worst_risk]:
                    worst_risk = risk["level"]
        legs.append(leg)

    suggested_departure = legs[0]["departure"] if legs else start.isoformat(timespec="minutes")
    return {
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


def edge_instance(
    edge: dict, routes: dict[str, dict], moment: datetime, mode: str, timing_profile: str,
    *, enforce_loading_readiness: bool = False,
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
            route.get("booking", {}).get("loadingReadinessMinutesBefore", 0)
            if enforce_loading_readiness else 0
        )
        boarding_ready = moment + timedelta(minutes=readiness)
        return next_scheduled_instance(edge, route, boarding_ready, timing_profile)
    return next_continuous_instance(edge, moment)


def earliest_candidate_from_seed(
    adjacency: dict[str, list[dict]], routes: dict[str, dict], origin: str, destination: str,
    seed: datetime, deadline: datetime, mode: str, timing_profile: str, max_legs: int,
) -> tuple[list[dict], datetime] | None:
    """Return the earliest feasible itinerary after one exact origin seed.

    Running this small earliest-arrival search for each origin seed complements
    the diverse-label search below. In particular, a later useful feeder must
    not disappear merely because an earlier label reached the same road node.
    """
    serial = itertools.count()
    queue = [(seed, next(serial), origin, [], (origin,))]
    best: dict[tuple[str, str | None], datetime] = {}
    while queue:
        moment, _, node_id, records, visited_nodes = heapq.heappop(queue)
        last_trip = (
            records[-1]["edge"].get("tripPatternId")
            if records and records[-1]["edge"]["kind"] == "scheduled_service"
            else None
        )
        state = (node_id, last_trip)
        if moment >= best.get(state, datetime.max):
            continue
        best[state] = moment
        if node_id == destination:
            return records, moment
        if moment > deadline or len(records) >= max_legs:
            continue
        for edge in adjacency.get(node_id, []):
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
                enforce_loading_readiness=not any(
                    item["edge"]["kind"] != "road" for item in records
                ),
            )
            if not instance or instance["arrival"] > deadline:
                continue
            record = {"edge": edge, "instance": instance, "ready": moment}
            heapq.heappush(queue, (
                instance["arrival"], next(serial), edge["to"], records + [record],
                visited_nodes + (edge["to"],),
            ))
    return None


def candidate_dominates(first: dict, second: dict) -> bool:
    """Whether first is unambiguously preferable to second."""
    first_departure = datetime.fromisoformat(first["suggestedOriginDeparture"])
    second_departure = datetime.fromisoformat(second["suggestedOriginDeparture"])
    first_arrival = datetime.fromisoformat(first["arrival"])
    second_arrival = datetime.fromisoformat(second["arrival"])
    first_risk = RISK_ORDER.get(first["riskSummary"]["worstConnectionRisk"], -1)
    second_risk = RISK_ORDER.get(second["riskSummary"]["worstConnectionRisk"], -1)
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
    return no_worse and strictly_better


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
    origin_sweep_minutes: int = 30,
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
        origin_sweep_minutes=origin_sweep_minutes,
        same_day=same_day,
        graph=graph_path,
    )
    graph = (
        copy.deepcopy(graph_data)
        if graph_data is not None
        else json.loads(args.graph.read_text())
    )
    routes = {item["id"]: item for item in graph["routes"]}
    trip_patterns = {item["id"]: item for item in graph["tripPatterns"]}
    nodes = {item["id"]: item for item in graph["nodes"]}
    for value, label in ((args.origin, "origin"), (args.destination, "destination")):
        if value not in nodes:
            raise ValueError(f"unknown {label}: {value}")

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
    deadline = (
        datetime.combine(args.travel_date, time(23, 59, 59))
        if args.same_day else start + timedelta(days=3)
    )
    serial = itertools.count()
    queue = []
    seed = start
    while seed <= deadline:
        heapq.heappush(queue, (seed, next(serial), args.origin, [], (args.origin,)))
        seed += timedelta(minutes=args.origin_sweep_minutes)
    accepted_per_node_hour = Counter()
    best_origin_departure_by_state = {}
    candidates_by_signature = {}
    expansions = 0

    while queue and len(candidates_by_signature) < args.max_candidates:
        moment, _, node_id, records, visited_nodes = heapq.heappop(queue)
        if moment > deadline:
            continue
        state_key = (
            node_id,
            moment,
            records[-1]["edge"].get("tripPatternId") if records else None,
            partial_worst_risk(records, routes),
        )
        origin_departure = partial_origin_departure(records, routes, start)
        if origin_departure <= best_origin_departure_by_state.get(state_key, datetime.min):
            continue
        best_origin_departure_by_state[state_key] = origin_departure
        if node_id == args.destination:
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
        previous_trip = records[-1]["edge"].get("tripPatternId") if records else None
        label_bucket = (
            node_id, hour_bucket, partial_worst_risk(records, routes), previous_trip,
        )
        accepted_per_node_hour[label_bucket] += 1
        if accepted_per_node_hour[label_bucket] > args.max_labels_per_node_hour:
            continue
        if len(records) >= args.max_legs:
            continue
        expansions += 1

        for edge in adjacency.get(node_id, []):
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
                enforce_loading_readiness=not any(
                    item["edge"]["kind"] != "road" for item in records
                ),
            )
            if not instance:
                continue
            if instance["arrival"] > deadline:
                continue
            record = {"edge": edge, "instance": instance, "ready": moment}
            heapq.heappush(queue, (
                instance["arrival"], next(serial), edge["to"], records + [record],
                visited_nodes + (edge["to"],),
            ))

    # Preserve useful later-departure chains that the bounded diverse-label
    # search may prune at a shared road node. Each seed contributes its one
    # earliest-arrival itinerary; identical ferry sequences are deduplicated.
    swept_seed_count = 0
    swept_candidate_count = 0
    seed = start
    while seed <= deadline:
        swept_seed_count += 1
        found = earliest_candidate_from_seed(
            adjacency, routes, args.origin, args.destination, seed, deadline,
            args.mode, args.timing_profile, args.max_legs,
        )
        if found:
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
        seed += timedelta(minutes=args.origin_sweep_minutes)

    candidates = list(candidates_by_signature.values())
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
        group.sort(key=lambda item: item["suggestedOriginDeparture"], reverse=True)
        chosen = []
        seen_risks = set()
        for candidate in group:
            risk = candidate["riskSummary"]["worstConnectionRisk"]
            if risk in seen_risks:
                continue
            chosen.append(candidate)
            seen_risks.add(risk)
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
    return {
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
            "maxLabelsPerNodeHour": args.max_labels_per_node_hour,
            "maxLegs": args.max_legs,
            "originSweepMinutes": args.origin_sweep_minutes,
            "sweptSeedCount": swept_seed_count,
            "sweptCandidateUpdates": swept_candidate_count,
            "limitations": [
                "result diversity is based on distinct ferry-service sequences",
                "continuous ferry edges without a known crossing time are not routable",
                "specialized holiday and parity-based break rules still require expansion",
            ],
        },
    }


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
    parser.add_argument("--origin-sweep-minutes", type=int, default=30)
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
            origin_sweep_minutes=args.origin_sweep_minutes,
            same_day=args.same_day,
            graph_path=args.graph,
        )
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(response, ensure_ascii=False, indent=2))
    return 0 if response["status"] == "routes_found" else 2


if __name__ == "__main__":
    raise SystemExit(main())
