#!/usr/bin/env python3
"""Route between arbitrary Finnish addresses through the archipelago graph."""

from __future__ import annotations

import argparse
import json
import math
import unicodedata
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
# Allow the longest plausible 19-leg archipelago chain plus address access
# and egress. The bound still keeps the time-dependent search finite.
MAX_ADDRESS_ROUTE_LEGS = 21


def normalized_place_name(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def known_stop(index: dict, query: str) -> dict | None:
    """Resolve an unambiguous stop id or name before external geocoding."""
    normalized = normalized_place_name(query)
    explicit_stop = False
    for suffix in (" (lauttaranta)", " lauttaranta"):
        if normalized.endswith(suffix):
            normalized = normalized.removesuffix(suffix).strip()
            explicit_stop = True
            break
    matches = [
        item for item in index["stops"]
        if normalized in {
            normalized_place_name(item["id"]),
            normalized_place_name(item.get("name", item["id"])),
        }
        and (explicit_stop or item.get("roadAreaKind") == "singleton_stop")
    ]
    return matches[0] if len(matches) == 1 else None


def resolve_endpoint(index: dict, query: str, geocoder) -> dict:
    stop = known_stop(index, query)
    if stop is None:
        return geocoder.geocode(query)
    return {
        "query": query,
        "displayName": stop.get("name", stop["id"]),
        "coordinates": routing_coordinates(stop),
        "provider": "saaristolautat",
        "routingStopId": stop["id"],
    }


def endpoint_classification(index: dict, endpoint: dict, router, mode: str) -> dict:
    stop_id = endpoint.get("routingStopId")
    if stop_id is None:
        return router.infer_road_area(endpoint["coordinates"], index, mode=mode)
    stop = next(item for item in index["stops"] if item["id"] == stop_id)
    return {
        "roadArea": {
            "id": stop["roadAreaId"],
            "inference": "known_stop_name",
            "stop": {"id": stop["id"], "name": stop.get("name", stop["id"])},
        },
    }


def routing_coordinates(stop: dict) -> dict:
    return stop.get("routingCoordinates", stop["coordinates"])


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
    """Use a matrix first, then a complete route-by-route fallback.

    The public Valhalla demo has a shorter distance limit for matrices than
    for ordinary routes.  A production deployment can use a Valhalla instance
    with a larger matrix limit. The complete fallback is intentionally slower,
    but it never drops a valid access point merely because it was not among a
    fixed number of geographically nearest stops. Persistent caching keeps the
    cost bounded after the first query.
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
    completed_pairs = {
        (item["fromIndex"], item["toIndex"])
        for item in values
    }

    if fallback_from_source:
        point = sources[0]
        ranked = sorted(
            range(len(targets)),
            key=lambda index: distance_meters(point, targets[index]),
        )
        pairs = [
            (0, target_index) for target_index in ranked
            if (0, target_index) not in completed_pairs
        ]
    else:
        point = targets[0]
        ranked = sorted(
            range(len(sources)),
            key=lambda index: distance_meters(sources[index], point),
        )
        pairs = [
            (source_index, 0) for source_index in ranked
            if (source_index, 0) not in completed_pairs
        ]

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
    *,
    origin_stop_id: str | None = None,
    destination_stop_id: str | None = None,
) -> dict:
    """Return a graph augmented with address access and egress road edges."""
    # Only the top-level node and edge arrays are extended. Their existing
    # members stay immutable, so copying the whole graph for every request is
    # unnecessary and expensive.
    result = {
        **graph,
        "nodes": list(graph["nodes"]),
        "edges": list(graph["edges"]),
    }
    origin_stops = [] if origin_stop_id else area_stops(index, result, origin_area_id)
    destination_stops = [] if destination_stop_id else area_stops(index, result, destination_area_id)
    if not origin_stop_id and not origin_stops:
        raise ValueError(f"road area has no routing stops: {origin_area_id}")
    if not destination_stop_id and not destination_stops:
        raise ValueError(f"road area has no routing stops: {destination_area_id}")

    if not origin_stop_id:
        result["nodes"].append({
            "id": ORIGIN_NODE,
            "kind": "address",
            "name": origin["displayName"],
            "coordinates": origin["coordinates"],
            "roadComponentIds": [f"external:{origin_area_id}"],
        })
    if not destination_stop_id:
        result["nodes"].append({
            "id": DESTINATION_NODE,
            "kind": "address",
            "name": destination["displayName"],
            "coordinates": destination["coordinates"],
            "roadComponentIds": [f"external:{destination_area_id}"],
        })

    access_values = [] if origin_stop_id else external_measurements(
        router, [origin["coordinates"]],
        [routing_coordinates(item) for item in origin_stops], mode,
        fallback_from_source=True,
    )
    for value in access_values:
        stop = origin_stops[value["toIndex"]]
        result["edges"].append(external_road_edge(
            f"external:access:{stop['id']}", ORIGIN_NODE, stop["id"], value,
            mode=mode, role="access", road_area_id=origin_area_id,
        ))

    egress_values = [] if destination_stop_id else external_measurements(
        router,
        [routing_coordinates(item) for item in destination_stops],
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

    if not origin_stop_id and not destination_stop_id and origin_area_id == destination_area_id:
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

    if not origin_stop_id and not access_values:
        raise ValueError("no ferry-free road route from the origin to a routing stop")
    if not destination_stop_id and not egress_values:
        raise ValueError("no ferry-free road route from a routing stop to the destination")
    return result


def public_road_area(classification: dict) -> dict:
    area = classification["roadArea"]
    result = {"id": area["id"], "inference": area["inference"]}
    if area.get("stop"):
        result["matchedStop"] = area["stop"]
    return result


def enrich_external_geometries(
    response: dict,
    router,
    origin: dict,
    destination: dict,
    index: dict,
    mode: str,
) -> None:
    """Fetch geometry only for external road legs in selected itineraries."""
    coordinates = {
        item["id"]: routing_coordinates(item) for item in index["stops"]
    }
    coordinates[ORIGIN_NODE] = origin["coordinates"]
    coordinates[DESTINATION_NODE] = destination["coordinates"]
    geometries = {}
    for itinerary in response.get("itineraries", []):
        for leg in itinerary.get("legs", []):
            if "externalRouting" not in leg:
                continue
            pair = (leg["from"], leg["to"])
            if pair not in geometries:
                geometries[pair] = router.route_geometry(
                    coordinates[pair[0]], coordinates[pair[1]], mode,
                    exclude_ferries=True,
                )
            if geometries[pair] is not None:
                leg["externalRouting"]["geometry"] = geometries[pair]


def enrich_road_navigation_coordinates(
    response: dict,
    origin: dict,
    destination: dict,
    index: dict,
) -> None:
    """Attach lightweight endpoint coordinates to road legs.

    Navigation links only need the two endpoints, not the potentially large
    routed geometry. Include the same data in decision-graph legs so a road
    segment selected after changing a sailing remains navigable.
    """
    coordinates = {
        item["id"]: routing_coordinates(item) for item in index["stops"]
    }
    coordinates[ORIGIN_NODE] = origin["coordinates"]
    coordinates[DESTINATION_NODE] = destination["coordinates"]

    def enrich(leg: dict) -> None:
        if leg.get("kind") != "road":
            return
        from_coordinates = coordinates.get(leg.get("from"))
        to_coordinates = coordinates.get(leg.get("to"))
        if from_coordinates is not None and to_coordinates is not None:
            leg["navigationCoordinates"] = {
                "from": from_coordinates,
                "to": to_coordinates,
            }

    for itinerary in response.get("itineraries", []):
        for leg in itinerary.get("legs", []):
            enrich(leg)
    for connection in (response.get("decisionGraph") or {}).get("connections", []):
        enrich(connection.get("leg", {}))


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
    include_decision_graph: bool = False,
    include_external_geometry: bool = False,
    graph_path: Path = DEFAULT_GRAPH,
    stop_index_path: Path = DEFAULT_STOP_INDEX,
    graph_data: dict | None = None,
    stop_index_data: dict | None = None,
    geocoder=None,
    router=None,
) -> dict:
    geocoder = geocoder or NominatimGeocoder()
    router = router or ValhallaRouter()
    graph = graph_data if graph_data is not None else json.loads(graph_path.read_text())
    index = (
        stop_index_data
        if stop_index_data is not None
        else json.loads(stop_index_path.read_text())
    )

    origin = resolve_endpoint(index, origin_query, geocoder)
    destination = resolve_endpoint(index, destination_query, geocoder)
    origin_classification = endpoint_classification(index, origin, router, mode)
    destination_classification = endpoint_classification(index, destination, router, mode)
    origin_area_id = origin_classification["roadArea"]["id"]
    destination_area_id = destination_classification["roadArea"]["id"]
    augmented = add_external_edges(
        graph, index, router, origin, destination,
        origin_area_id, destination_area_id, mode,
        origin_stop_id=origin.get("routingStopId"),
        destination_stop_id=destination.get("routingStopId"),
    )
    origin_node = origin.get("routingStopId", ORIGIN_NODE)
    destination_node = destination.get("routingStopId", DESTINATION_NODE)
    internal = find_itineraries(
        origin_node,
        destination_node,
        travel_date,
        start_time,
        mode=mode,
        timing_profile=timing_profile,
        same_day=same_day,
        max_results=max_results,
        max_legs=MAX_ADDRESS_ROUTE_LEGS,
        include_decision_graph=include_decision_graph,
        graph_path=graph_path,
        graph_data=augmented,
    )
    response = public_response(internal, include_diagnostics=include_diagnostics)
    enrich_road_navigation_coordinates(response, origin, destination, index)
    if include_external_geometry:
        enrich_external_geometries(
            response, router, origin, destination, index, mode,
        )
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
    parser.add_argument("--include-decision-graph", action="store_true")
    parser.add_argument("--include-external-geometry", action="store_true")
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
            include_decision_graph=args.include_decision_graph,
            include_external_geometry=args.include_external_geometry,
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
