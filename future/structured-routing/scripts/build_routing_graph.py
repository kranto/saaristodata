#!/usr/bin/env python3
"""Build one time-dependent graph from roads and structured ferry services."""

from __future__ import annotations

import argparse
import copy
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT = Path(__file__).resolve().parents[1]
DEFAULT_TIMETABLES = EXPERIMENT / "structured-connection-timetables-with-ais.json"
DEFAULT_ROADS = EXPERIMENT / "road-network.json"
DEFAULT_STOPS = ROOT.parent / "saaristolautat" / "public" / "data" / "saaristo.json"
DEFAULT_OVERRIDES = EXPERIMENT / "routing-stop-overrides.json"
DEFAULT_OUTPUT = EXPERIMENT / "routing-graph.json"
DEFAULT_REPORT = EXPERIMENT / "routing-graph-report.json"

SOURCE_CONTAINER_ROUTE_IDS = {
    # This record carries common Åland cable-ferry source metadata. The actual
    # routable services are represented by their individual line records.
    "alandsvajerfarjor",
}


def load_piers(path: Path) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    result = {}
    for feature in data["features"]:
        props = feature.get("properties", {})
        coordinates = feature.get("geometry", {}).get("coordinates")
        if props.get("stype") == "pier" and props.get("ref") and coordinates:
            result[props["ref"]] = {"lon": coordinates[0], "lat": coordinates[1]}
    return result


def service_type(route: dict) -> str:
    if route.get("serviceType"):
        return route["serviceType"]
    if route["id"] == "korporutt":
        return "connection_vessel"
    return "unknown"


def mobility_for(service: str) -> dict:
    if service in {
        "road_ferry", "cable_ferry", "alandstrafiken_archipelago_ferry",
        "commercial_ferry",
    }:
        return {mode: "allowed" for mode in ("foot", "bicycle", "motorcycle", "car")}
    if service == "connection_vessel":
        return {
            "foot": "allowed",
            "bicycle": "allowed_subject_to_operator_conditions",
            "motorcycle": "booking_validation_required",
            "car": "booking_validation_required",
        }
    return {mode: "source_validation_required" for mode in ("foot", "bicycle", "motorcycle", "car")}


def route_aliases(route: dict, global_aliases: dict) -> dict[str, str]:
    aliases = {name: item["canonicalId"] for name, item in global_aliases.items()}
    for name, item in route.get("stopAliases", {}).items():
        if isinstance(item, dict) and item.get("canonicalId"):
            aliases[name] = item["canonicalId"]
    for name, item in route.get("canonicalStopNames", {}).items():
        if isinstance(item, str):
            aliases[name] = item
    return aliases


def time_model(call: dict) -> dict:
    if call.get("time"):
        nature = call.get("timeNature", "published_or_source_time")
        return {
            "status": "published" if nature.startswith("published") else "source_time",
            "time": call["time"],
            "dayOffset": call.get("dayOffset", 0),
            "timeNature": nature,
        }
    if call.get("timeRange"):
        return {"status": "published_range", "range": copy.deepcopy(call["timeRange"])}
    estimate = call.get("historicalEstimate")
    if estimate and estimate.get("typical"):
        return {
            "status": "historical_estimate",
            "time": estimate["typical"],
            "dayOffset": estimate.get("dayOffset", 0),
            "range": copy.deepcopy(estimate.get("range")),
            "rangeDayOffsets": copy.deepcopy(estimate.get("rangeDayOffsets")),
            "sampleSize": estimate.get("sampleSize"),
            "modelVersion": estimate.get("modelVersion"),
            "disclosureRequired": estimate.get("disclosureRequired", True),
        }
    estimate = call.get("historicalRangeEstimate")
    if estimate and estimate.get("range"):
        return {
            "status": "historical_range_only",
            "range": copy.deepcopy(estimate["range"]),
            "rangeDayOffsets": copy.deepcopy(estimate.get("rangeDayOffsets")),
            "sampleSize": estimate.get("sampleSize"),
            "modelVersion": estimate.get("modelVersion"),
            "disclosureRequired": estimate.get("disclosureRequired", True),
        }
    if call.get("timeAlternatives"):
        return {
            "status": "unresolved_time_alternatives",
            "alternatives": copy.deepcopy(call["timeAlternatives"]),
        }
    return {"status": "unknown"}


def clock_minutes(value: str) -> int:
    hours, minutes = (int(item) for item in value.split(":"))
    return hours * 60 + minutes


def segment_duration(departure: dict, arrival: dict) -> dict | None:
    if not departure.get("time") or not arrival.get("time"):
        return None
    start = clock_minutes(departure["time"]) + 1440 * departure.get("dayOffset", 0)
    end = clock_minutes(arrival["time"]) + 1440 * arrival.get("dayOffset", 0)
    while end < start:
        end += 1440
    return {
        "minutes": end - start,
        "nature": "published_or_estimated_from_call_times",
    }


def selected_route_metadata(route: dict) -> dict:
    keys = (
        "provider", "serviceType", "serviceRole", "validPeriods", "holidayExceptions",
        "booking", "callConditions", "capacity", "contact", "publicTimetableUrl",
        "travelerInformation", "vessel", "vessels", "vesselByCode", "notes", "generalNotes",
        "sources", "routingService", "routingPolicy", "review",
    )
    result = {"id": route["id"], "serviceType": service_type(route)}
    result["graphRole"] = (
        "source_container" if route["id"] in SOURCE_CONTAINER_ROUTE_IDS else "routable_service"
    )
    for key in keys:
        if key in route:
            result[key] = copy.deepcopy(route[key])
    result["normalizedHolidayDates"] = [
        item["date"] for item in route.get("holidayTripOverrides", [])
        if item.get("date")
    ]
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timetables", type=Path, default=DEFAULT_TIMETABLES)
    parser.add_argument("--roads", type=Path, default=DEFAULT_ROADS)
    parser.add_argument("--stops", type=Path, default=DEFAULT_STOPS)
    parser.add_argument("--overrides", type=Path, default=DEFAULT_OVERRIDES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    timetables = json.loads(args.timetables.read_text())
    roads = json.loads(args.roads.read_text())
    overrides = json.loads(args.overrides.read_text())
    pier_coordinates = load_piers(args.stops)
    pier_coordinates.update({
        ref: {"lon": point["lon"], "lat": point["lat"]}
        for ref, point in roads.get("pierCoordinates", {}).items()
    })
    preferred_names = roads.get("preferredNames", {})
    global_aliases = overrides.get("aliases", {})
    multi_stop_cells = overrides.get("multiStopCells", {})
    ambiguous_groups = overrides.get("ambiguousStopGroups", {})

    nodes: dict[str, dict] = {}
    node_aliases: defaultdict[str, set[str]] = defaultdict(set)
    unresolved_stops: set[str] = set()
    used_ambiguous_groups: set[str] = set()
    used_multi_stop_cells: set[str] = set()

    def ensure_node(node_id: str, *, raw_name: str | None = None, kind: str = "pier") -> str:
        node = nodes.setdefault(node_id, {
            "id": node_id,
            "kind": kind,
            "name": preferred_names.get(node_id, node_id),
        })
        if node_id in pier_coordinates:
            node["coordinates"] = pier_coordinates[node_id]
        if raw_name and raw_name != node_id:
            node_aliases[node_id].add(raw_name)
        return node_id

    def canonical_stop(raw_name: str, aliases: dict[str, str]) -> str:
        if raw_name in ambiguous_groups:
            node_id = f"group:{raw_name}"
            group = ambiguous_groups[raw_name]
            node = nodes.setdefault(node_id, {
                "id": node_id,
                "kind": "alternative_stop_group",
                "name": raw_name,
                "members": copy.deepcopy(group["members"]),
                "reason": group["reason"],
                "enabledForAutomaticRouting": False,
            })
            used_ambiguous_groups.add(raw_name)
            for member in node["members"]:
                ensure_node(member)
            return node_id
        canonical = aliases.get(raw_name, raw_name)
        if canonical not in pier_coordinates:
            node_id = f"unresolved:{canonical}"
            unresolved_stops.add(raw_name)
            return ensure_node(node_id, raw_name=raw_name, kind="unresolved_stop")
        return ensure_node(canonical, raw_name=raw_name)

    road_components: defaultdict[str, list[str]] = defaultdict(list)
    for component in roads["components"]:
        for ref in component["piers"]:
            road_components[ref].append(component["id"])
    for ref, component_ids in road_components.items():
        ensure_node(ref)
        nodes[ref]["roadComponentIds"] = component_ids

    edges = []
    edge_ids = set()

    def add_edge(edge: dict) -> None:
        if edge["id"] in edge_ids:
            raise SystemExit(f"duplicate edge id: {edge['id']}")
        edge_ids.add(edge["id"])
        edges.append(edge)

    for transfer in roads["transfers"]:
        ensure_node(transfer["from"])
        ensure_node(transfer["to"])
        add_edge({
            "id": f"road:{transfer['componentId']}:{transfer['from']}:{transfer['to']}",
            "kind": "road",
            "from": transfer["from"],
            "to": transfer["to"],
            "componentId": transfer["componentId"],
            "modes": copy.deepcopy(transfer["modes"]),
        })

    route_metadata = []
    trip_patterns = []
    routes_with_edges: set[str] = set()
    timing_statuses = Counter()

    for route in timetables["routes"]:
        route_id = route["id"]
        route_service_type = service_type(route)
        route_metadata.append(selected_route_metadata(route))
        aliases = route_aliases(route, global_aliases)
        route_mobility = mobility_for(route_service_type)
        normalized_trips = []

        source_trips = list(route.get("trips", []))
        source_trips.extend(
            trip
            for override in route.get("holidayTripOverrides", [])
            for trip in override.get("trips", [])
        )
        for trip in source_trips:
            original_trip_id = trip.get("id") or f"trip-{len(normalized_trips) + 1}"
            trip_id = f"{route_id}:{original_trip_id}"
            normalized_trip = copy.deepcopy(trip)
            normalized_trip["id"] = trip_id
            normalized_trip["sourceTripId"] = original_trip_id
            normalized_trip["routeId"] = route_id
            normalized_trip["serviceType"] = route_service_type
            normalized_calls = []
            trip_requires_review = False
            for source_call_index, call in enumerate(trip.get("calls", [])):
                raw_stop = call.get("stop")
                if not raw_stop:
                    normalized_call = copy.deepcopy(call)
                    normalized_call["stopId"] = None
                    normalized_call["sourceCallIndex"] = source_call_index
                    normalized_call["timing"] = time_model(call)
                    normalized_calls.append(normalized_call)
                    trip_requires_review = True
                    continue

                if raw_stop in multi_stop_cells:
                    definition = multi_stop_cells[raw_stop]
                    members = definition["members"]
                    used_multi_stop_cells.add(raw_stop)
                    for member_index, member in enumerate(members):
                        normalized_call = copy.deepcopy(call)
                        stop_id = canonical_stop(member, aliases)
                        normalized_call["stop"] = member
                        normalized_call["stopId"] = stop_id
                        normalized_call["sourceStop"] = raw_stop
                        normalized_call["sourceCallIndex"] = source_call_index
                        normalized_call["multiStopCell"] = {
                            "sourceStop": raw_stop,
                            "members": copy.deepcopy(members),
                            "memberIndex": member_index,
                            "allMembersMayBeCalled": definition.get("allMembersMayBeCalled", True),
                            "eachMemberConditional": definition.get("eachMemberConditional", True),
                            "reason": definition["reason"],
                        }
                        normalized_call["timing"] = time_model(call)
                        if normalized_call["timing"]["status"] != "unknown":
                            normalized_call["timing"]["sharedBySourceCellMembers"] = True
                        normalized_calls.append(normalized_call)
                    continue

                normalized_call = copy.deepcopy(call)
                stop_id = canonical_stop(raw_stop, aliases)
                normalized_call["sourceCallIndex"] = source_call_index
                normalized_call["stopId"] = stop_id
                if stop_id != raw_stop:
                    normalized_call["sourceStop"] = raw_stop
                if stop_id.startswith(("group:", "unresolved:")):
                    trip_requires_review = True
                normalized_call["timing"] = time_model(call)
                normalized_calls.append(normalized_call)
            normalized_trip["calls"] = normalized_calls
            normalized_trip["routability"] = "review_required" if trip_requires_review else "routable"
            normalized_trips.append(normalized_trip)
            trip_patterns.append(normalized_trip)

            # A ride edge is emitted for every ordered pair of calls on the
            # same trip. This is intentional: conditional intermediate calls
            # (including slash cells) must not be interpreted as mandatory,
            # and a passenger remains on board when an intermediate call is
            # omitted.
            for from_index, from_call in enumerate(normalized_calls[:-1]):
                for to_index in range(from_index + 1, len(normalized_calls)):
                    to_call = normalized_calls[to_index]
                    from_id, to_id = from_call.get("stopId"), to_call.get("stopId")
                    if not from_id or not to_id:
                        continue
                    departure = from_call["timing"]
                    arrival = to_call["timing"]
                    duration = segment_duration(departure, arrival)
                    routing_service = route.get("routingService", {})
                    if (
                        duration is None
                        and to_index == from_index + 1
                        and departure.get("time")
                        and routing_service.get("crossingMinutes")
                    ):
                        duration = {
                            "minutes": routing_service["crossingMinutes"],
                            "nature": routing_service.get("crossingTimeNature", "route_level_crossing_time"),
                        }
                    if departure["status"] == "unknown":
                        timing_status = "departure_unknown"
                    elif arrival["status"] == "unknown" and duration is None:
                        timing_status = "arrival_unknown"
                    else:
                        timing_status = "usable"
                    timing_statuses[timing_status] += 1
                    add_edge({
                        "id": f"scheduled:{trip_id}:{from_index}:{to_index}",
                        "kind": "scheduled_service",
                        "from": from_id,
                        "to": to_id,
                        "routeId": route_id,
                        "tripPatternId": trip_id,
                        "fromCallIndex": from_index,
                        "toCallIndex": to_index,
                        "intermediateCallIndices": list(range(from_index + 1, to_index)),
                        "serviceType": route_service_type,
                        "mobility": route_mobility,
                        "schedule": {
                            "operatingDays": trip.get("operatingDays"),
                            "operatingDate": trip.get("operatingDate"),
                            "validPeriods": copy.deepcopy(trip.get("validPeriods", route.get("validPeriods", []))),
                            "specialDays": copy.deepcopy(trip.get("specialDays", [])),
                            "publicHolidayPolicy": trip.get("publicHolidayPolicy"),
                            "departure": departure,
                            "arrival": arrival,
                            "duration": duration,
                        },
                        "conditions": {
                            "trip": copy.deepcopy(trip.get("conditions", [])),
                            "fromCall": copy.deepcopy(from_call.get("conditions", [])),
                            "toCall": copy.deepcopy(to_call.get("conditions", [])),
                            "fromCallCondition": from_call.get("callCondition"),
                            "toCallCondition": to_call.get("callCondition"),
                            "intermediateCalls": [
                                {
                                    "callIndex": index,
                                    "stopId": normalized_calls[index].get("stopId"),
                                    "callCondition": normalized_calls[index].get("callCondition"),
                                    "multiStopCell": copy.deepcopy(normalized_calls[index].get("multiStopCell")),
                                }
                                for index in range(from_index + 1, to_index)
                            ],
                        },
                        "timingStatus": timing_status,
                        "enabledForAutomaticRouting": not (
                            from_id.startswith(("group:", "unresolved:"))
                            or to_id.startswith(("group:", "unresolved:"))
                        ),
                    })
                    routes_with_edges.add(route_id)

        for service_index, service in enumerate(route.get("continuousServices", [])):
            terminals = service.get("terminals") or route.get("routingService", {}).get("terminals", [])
            if len(terminals) != 2:
                continue
            first = canonical_stop(terminals[0], aliases)
            second = canonical_stop(terminals[1], aliases)
            for from_id, to_id, direction in ((first, second, "forward"), (second, first, "reverse")):
                add_edge({
                    "id": f"continuous:{route_id}:{service_index}:{direction}",
                    "kind": "continuous_ferry",
                    "from": from_id,
                    "to": to_id,
                    "routeId": route_id,
                    "serviceType": route_service_type,
                    "mobility": route_mobility,
                    "availability": copy.deepcopy(service),
                    "crossingMinutes": route.get("routingService", {}).get("crossingMinutes"),
                    "crossingTimeStatus": route.get("routingService", {}).get(
                        "crossingTimeNature",
                        route.get("routingService", {}).get("crossingTimeStatus", "unknown"),
                    ),
                })
                routes_with_edges.add(route_id)

    for node_id, aliases in node_aliases.items():
        nodes[node_id]["aliases"] = sorted(aliases)

    for raw_name in used_ambiguous_groups:
        group_id = f"group:{raw_name}"
        for member in ambiguous_groups[raw_name]["members"]:
            for direction, from_id, to_id in (
                ("to_member", group_id, member), ("from_member", member, group_id)
            ):
                add_edge({
                    "id": f"ambiguous:{raw_name}:{direction}:{member}",
                    "kind": "ambiguous_stop_membership",
                    "from": from_id,
                    "to": to_id,
                    "durationMinutes": 0,
                    "enabledForAutomaticRouting": False,
                    "reason": ambiguous_groups[raw_name]["reason"],
                })

    edge_counts = Counter(edge["kind"] for edge in edges)
    service_edge_counts = Counter(
        edge.get("serviceType") for edge in edges
        if edge["kind"] in {"scheduled_service", "continuous_ferry"}
    )
    routes_without_edges = [
        {
            "routeId": route["id"],
            "serviceType": service_type(route),
            "validPeriods": copy.deepcopy(route.get("validPeriods", [])),
            "reason": "no normalized trips or continuous-service network edges",
        }
        for route in timetables["routes"]
        if route["id"] not in routes_with_edges and route["id"] not in SOURCE_CONTAINER_ROUTE_IDS
    ]
    nodes_without_coordinates = sorted(
        node_id for node_id, node in nodes.items()
        if "coordinates" not in node and node["kind"] == "pier"
    )
    report = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "statistics": {
            "nodeCount": len(nodes),
            "edgeCount": len(edges),
            "tripPatternCount": len(trip_patterns),
            "routeMetadataCount": len(route_metadata),
            "routesWithEdgesCount": len(routes_with_edges),
            "routesWithoutEdgesCount": len(routes_without_edges),
            "sourceContainerRouteCount": len(SOURCE_CONTAINER_ROUTE_IDS),
            "nodesWithoutCoordinatesCount": len(nodes_without_coordinates),
            "unresolvedStopCount": len(unresolved_stops),
            "ambiguousStopGroupCount": len(used_ambiguous_groups),
            "multiStopCellCount": len(used_multi_stop_cells),
            "edgeCountsByKind": dict(sorted(edge_counts.items())),
            "serviceEdgeCountsByType": dict(sorted(service_edge_counts.items(), key=lambda item: str(item[0]))),
            "scheduledTimingStatusCounts": dict(sorted(timing_statuses.items())),
        },
        "routesWithoutEdges": routes_without_edges,
        "nodesWithoutCoordinates": nodes_without_coordinates,
        "unresolvedStops": sorted(unresolved_stops),
        "ambiguousStopGroups": {
            name: ambiguous_groups[name] for name in sorted(used_ambiguous_groups)
        },
        "multiStopCells": {
            name: multi_stop_cells[name] for name in sorted(used_multi_stop_cells)
        },
    }
    graph_status = "review_required" if routes_without_edges or unresolved_stops else "routing_ready"
    graph = {
        "schemaVersion": 1,
        "status": graph_status,
        "generatedAt": report["generatedAt"],
        "sources": {
            "timetables": str(args.timetables),
            "roads": str(args.roads),
            "stops": str(args.stops),
            "stopOverrides": str(args.overrides),
        },
        "policies": {
            "timeDependent": True,
            "roadEdgesAreFerryFree": True,
            "ambiguousStopGroupsEnabledForAutomaticRouting": False,
            "multiStopCellSemantics": "each listed member is an independent conditional call; either or both may be called",
            "connectionVesselVehicleRule": "booking_validation_required",
            "historicalTimesRequireDisclosure": True,
        },
        "nodes": [nodes[node_id] for node_id in sorted(nodes)],
        "edges": edges,
        "routes": route_metadata,
        "tripPatterns": trip_patterns,
        "statistics": report["statistics"],
    }
    args.output.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n")
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report["statistics"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
