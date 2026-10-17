#!/usr/bin/env python3
"""Route between arbitrary Finnish addresses through the archipelago graph."""

from __future__ import annotations

import argparse
import copy
import json
import math
from datetime import date, time
from pathlib import Path

from classify_external_route import distance_meters
from external_routing import (
    DEFAULT_NOMINATIM_URL,
    DEFAULT_USER_AGENT,
    DEFAULT_VALHALLA_URL,
    NominatimGeocoder,
    ValhallaRouter,
)
from query_routes import public_response
from route_itineraries import find_itineraries
from route_itinerary import DEFAULT_GRAPH, parse_clock


EXPERIMENT = Path(__file__).resolve().parents[1]
DEFAULT_STOP_INDEX = EXPERIMENT / "external-routing-stop-index.json"
ORIGIN_NODE = "address:origin"
DESTINATION_NODE = "address:destination"
MAX_BICYCLE_EXTERNAL_METERS = 150_000
MAX_ROUTE_FALLBACK_CANDIDATES = 8


def graph_stop_ids(graph: dict) -> set[str]:
    return {item["id"] for item in graph["nodes"]}


def area_stops(index: dict, graph: dict, road_area_id: str) -> list[dict]:
    node_ids = graph_stop_ids(graph)
    return sorted(
        (
            item for item in index["stops"]
            if item["roadAreaId"] == road_area_id and item["id"] in node_ids
        ),
        key=lambda item: item["id"],
    )


def usable_matrix_entries(
    entries: list[dict],
    *,
    mode: str,
    maximum_bicycle_meters: int = MAX_BICYCLE_EXTERNAL_METERS,
) -> list[dict]:
    usable = []
    for item in entries:
        seconds = item.get("time")
        distance_km = item.get("distance")
        if seconds is None or distance_km is None:
            continue
        distance_meters = round(float(distance_km) * 1000)
        if mode == "bicycle" and distance_meters > maximum_bicycle_meters:
            continue
        usable.append({
            "fromIndex": int(item.get("from_index", 0)),
            "toIndex": int(item.get("to_index", 0)),
            "durationSeconds": max(0, round(float(seconds))),
            "distanceMeters": max(0, distance_meters),
        })
    return usable


def external_road_edge(
    edge_id: str,
    origin: str,
    destination: str,
    measurement: dict,
    *,
    mode: str,
    role: str,
    road_area_id: str,
) -> dict:
    road_mode = "auto" if mode in {"car", "motorcycle"} else "bicycle"
    duration = measurement["durationSeconds"]
    return {
        "id": edge_id,
        "kind": "road",
        "from": origin,
        "to": destination,
        "componentId": f"external:{road_area_id}",
        "modes": {
            road_mode: {
                "status": "ok",
                "distanceMeters": measurement["distanceMeters"],
                "durationSeconds": duration,
                "displayMinutes": math.ceil(duration / 60),
            }
        },
        "externalRouting": {
            "provider": "Valhalla",
            "role": role,
            "roadAreaId": road_area_id,
            "ferriesExcluded": True,
        },
    }


def external_measurements(
    router,
    sources: list[dict],
    targets: list[dict],
    mode: str,
    *,
    fallback_from_source: bool,
) -> list[dict]:
    """Use a matrix first, then a bounded route-by-route fallback.

    The public Valhalla demo has a shorter distance limit for matrices than
    for ordinary routes.  A production deployment can use a Valhalla instance
    with a larger matrix limit; the fallback keeps the prototype useful with
    the public service without issuing a request for every known stop.
    """
    try:
        values = usable_matrix_entries(
            router.matrix(
                sources, targets, mode, exclude_ferries=True,
            ),
            mode=mode,
        )
    except RuntimeError:
        values = []
    if values:
        return values

    if fallback_from_source:
        point = sources[0]
        ranked = sorted(
            range(len(targets)),
            key=lambda index: distance_meters(point, targets[index]),
        )[:MAX_ROUTE_FALLBACK_CANDIDATES]
        pairs = [(0, target_index) for target_index in ranked]
    else:
        point = targets[0]
        ranked = sorted(
            range(len(sources)),
            key=lambda index: distance_meters(sources[index], point),
        )[:MAX_ROUTE_FALLBACK_CANDIDATES]
        pairs = [(source_index, 0) for source_index in ranked]

    for source_index, target_index in pairs:
        try:
            measurement = router.measure_route(
                sources[source_index], targets[target_index], mode,
                exclude_ferries=True,
            )
        except RuntimeError:
            continue
        if not measurement:
            continue
        if (
            mode == "bicycle"
            and measurement["distanceMeters"] > MAX_BICYCLE_EXTERNAL_METERS
        ):
            continue
        values.append({
            "fromIndex": source_index,
            "toIndex": target_index,
            **measurement,
        })
    return values


def add_external_edges(
    graph: dict,
    index: dict,
    router,
    origin: dict,
    destination: dict,
    origin_area_id: str,
    destination_area_id: str,
    mode: str,
) -> dict:
    """Return a graph augmented with address access and egress road edges."""
    result = copy.deepcopy(graph)
    origin_stops = area_stops(index, result, origin_area_id)
    destination_stops = area_stops(index, result, destination_area_id)
    if not origin_stops:
        raise ValueError(f"road area has no routing stops: {origin_area_id}")
    if not destination_stops:
        raise ValueError(f"road area has no routing stops: {destination_area_id}")

    result["nodes"].extend([
        {
            "id": ORIGIN_NODE,
            "kind": "address",
            "name": origin["displayName"],
            "coordinates": origin["coordinates"],
            "roadComponentIds": [f"external:{origin_area_id}"],
        },
        {
            "id": DESTINATION_NODE,
            "kind": "address",
            "name": destination["displayName"],
            "coordinates": destination["coordinates"],
            "roadComponentIds": [f"external:{destination_area_id}"],
        },
    ])

    access_values = external_measurements(
        router,
        [origin["coordinates"]],
        [item["coordinates"] for item in origin_stops],
        mode,
        fallback_from_source=True,
    )
    for value in access_values:
        stop = origin_stops[value["toIndex"]]
        result["edges"].append(external_road_edge(
            f"external:access:{stop['id']}", ORIGIN_NODE, stop["id"], value,
            mode=mode, role="access", road_area_id=origin_area_id,
        ))

    egress_values = external_measurements(
        router,
        [item["coordinates"] for item in destination_stops],
        [destination["coordinates"]],
        mode,
        fallback_from_source=False,
    )
    for value in egress_values:
        stop = destination_stops[value["fromIndex"]]
        result["edges"].append(external_road_edge(
            f"external:egress:{stop['id']}", stop["id"], DESTINATION_NODE, value,
            mode=mode, role="egress", road_area_id=destination_area_id,
        ))

    if origin_area_id == destination_area_id:
        direct_values = external_measurements(
            router,
            [origin["coordinates"]], [destination["coordinates"]], mode,
            fallback_from_source=True,
        )
        if direct_values:
            result["edges"].append(external_road_edge(
                "external:direct", ORIGIN_NODE, DESTINATION_NODE, direct_values[0],
                mode=mode, role="direct", road_area_id=origin_area_id,
            ))

    if not access_values:
        raise ValueError("no ferry-free road route from the origin to a routing stop")
    if not egress_values:
        raise ValueError("no ferry-free road route from a routing stop to the destination")
    return result


def public_road_area(classification: dict) -> dict:
    area = classification["roadArea"]
    result = {"id": area["id"], "inference": area["inference"]}
    if area.get("stop"):
        result["matchedStop"] = area["stop"]
    return result


def query_address_routes(
    origin_query: str,
    destination_query: str,
    travel_date: date,
    start_time: time = time(0, 0),
    *,
    mode: str = "car",
    timing_profile: str = "typical",
    same_day: bool = False,
    max_results: int = 12,
    include_diagnostics: bool = False,
    graph_path: Path = DEFAULT_GRAPH,
    stop_index_path: Path = DEFAULT_STOP_INDEX,
    geocoder=None,
    router=None,
) -> dict:
    geocoder = geocoder or NominatimGeocoder()
    router = router or ValhallaRouter()
    graph = json.loads(graph_path.read_text())
    index = json.loads(stop_index_path.read_text())

    origin = geocoder.geocode(origin_query)
    destination = geocoder.geocode(destination_query)
    origin_classification = router.infer_road_area(
        origin["coordinates"], index, mode=mode
    )
    destination_classification = router.infer_road_area(
        destination["coordinates"], index, mode=mode
    )
    origin_area_id = origin_classification["roadArea"]["id"]
    destination_area_id = destination_classification["roadArea"]["id"]
    augmented = add_external_edges(
        graph, index, router, origin, destination,
        origin_area_id, destination_area_id, mode,
    )
    internal = find_itineraries(
        ORIGIN_NODE,
        DESTINATION_NODE,
        travel_date,
        start_time,
        mode=mode,
        timing_profile=timing_profile,
        same_day=same_day,
        max_results=max_results,
        max_legs=16,
        graph_path=graph_path,
        graph_data=augmented,
    )
    response = public_response(internal, include_diagnostics=include_diagnostics)
    response["query"].update({
        "originAddress": origin,
        "destinationAddress": destination,
        "originRoadArea": public_road_area(origin_classification),
        "destinationRoadArea": public_road_area(destination_classification),
    })
    response["externalServices"] = {
        "geocoding": origin.get("provider", "injected"),
        "roadRouting": getattr(router, "provider", "injected"),
        "attribution": ["© OpenStreetMap contributors"],
    }
    return response


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("origin_address")
    parser.add_argument("destination_address")
    parser.add_argument("travel_date", type=date.fromisoformat)
    parser.add_argument("start_time", type=parse_clock, nargs="?", default=time(0, 0))
    parser.add_argument("--mode", choices=("car", "motorcycle", "bicycle"), default="car")
    parser.add_argument("--timing-profile", choices=("typical", "conservative"), default="typical")
    parser.add_argument("--same-day", action="store_true")
    parser.add_argument("--max-results", type=int, default=12)
    parser.add_argument("--include-diagnostics", action="store_true")
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--stop-index", type=Path, default=DEFAULT_STOP_INDEX)
    parser.add_argument("--nominatim-url", default=DEFAULT_NOMINATIM_URL)
    parser.add_argument("--valhalla-url", default=DEFAULT_VALHALLA_URL)
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    args = parser.parse_args()
    geocoder = NominatimGeocoder(args.nominatim_url, user_agent=args.user_agent)
    router = ValhallaRouter(args.valhalla_url, user_agent=args.user_agent)
    try:
        response = query_address_routes(
            args.origin_address,
            args.destination_address,
            args.travel_date,
            args.start_time,
            mode=args.mode,
            timing_profile=args.timing_profile,
            same_day=args.same_day,
            max_results=args.max_results,
            include_diagnostics=args.include_diagnostics,
            graph_path=args.graph,
            stop_index_path=args.stop_index,
            geocoder=geocoder,
            router=router,
        )
    except (RuntimeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(response, ensure_ascii=False, indent=2))
    return 0 if response["status"] == "routes_found" else 2


if __name__ == "__main__":
    raise SystemExit(main())
