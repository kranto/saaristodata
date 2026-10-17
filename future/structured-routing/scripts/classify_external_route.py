#!/usr/bin/env python3
"""Identify the first known ferry boarding in a Valhalla route response."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX = EXPERIMENT / "external-routing-stop-index.json"


def decode_polyline(encoded: str, precision: int = 6) -> list[dict]:
    """Decode Valhalla's precision-six encoded route shape."""
    factor = 10 ** precision
    points = []
    index = 0
    lat = 0
    lon = 0
    while index < len(encoded):
        deltas = []
        for _ in range(2):
            result = 0
            shift = 0
            while True:
                if index >= len(encoded):
                    raise ValueError("truncated encoded polyline")
                value = ord(encoded[index]) - 63
                index += 1
                result |= (value & 0x1F) << shift
                shift += 5
                if value < 0x20:
                    break
            deltas.append(~(result >> 1) if result & 1 else result >> 1)
        lat += deltas[0]
        lon += deltas[1]
        points.append({"lat": lat / factor, "lon": lon / factor})
    return points


def distance_meters(first: dict, second: dict) -> float:
    radius = 6_371_000
    lat1 = math.radians(first["lat"])
    lat2 = math.radians(second["lat"])
    delta_lat = lat2 - lat1
    delta_lon = math.radians(second["lon"] - first["lon"])
    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(value))


def nearest_known_stop(point: dict, stops: list[dict], maximum_meters: float) -> dict | None:
    if not stops:
        return None
    distance, stop = min(
        (distance_meters(point, candidate["coordinates"]), candidate)
        for candidate in stops
    )
    if distance > maximum_meters:
        return None
    return {
        "id": stop["id"],
        "name": stop["name"],
        "distanceMeters": round(distance),
        "roadAreaId": stop["roadAreaId"],
        "roadAreaKind": stop["roadAreaKind"],
    }


def classify(
    response: dict, index: dict, maximum_meters: float | None = None,
    anchor_road_area_id: str | None = None,
) -> dict:
    trip = response.get("trip") or {}
    maximum = (
        maximum_meters
        if maximum_meters is not None
        else index["matchingPolicy"]["maximumDistanceMeters"]
    )
    boardings = []
    first_known = None

    for leg_index, leg in enumerate(trip.get("legs", [])):
        shape = leg.get("shape")
        maneuvers = leg.get("maneuvers")
        if not shape or maneuvers is None:
            continue
        points = decode_polyline(shape)
        for maneuver_index, maneuver in enumerate(maneuvers):
            if maneuver.get("type") != 28:
                continue
            shape_index = maneuver.get("begin_shape_index")
            if not isinstance(shape_index, int) or not 0 <= shape_index < len(points):
                raise ValueError("ferry-enter maneuver has an invalid begin_shape_index")
            point = points[shape_index]
            matched = nearest_known_stop(point, index["stops"], maximum)
            boarding = {
                "sequence": len(boardings) + 1,
                "legIndex": leg_index,
                "maneuverIndex": maneuver_index,
                "coordinate": point,
                "routeNames": maneuver.get("street_names", []),
                "distanceKilometers": maneuver.get("length"),
                "externalEstimatedSeconds": maneuver.get("time"),
                "matchedStop": matched,
            }
            boardings.append(boarding)
            if matched and first_known is None:
                first_known = {
                    "boardingSequence": boarding["sequence"],
                    "stop": matched,
                    "roadAreaId": matched["roadAreaId"],
                }

    has_ferry = bool((trip.get("summary") or {}).get("has_ferry"))
    if has_ferry and not any(leg.get("maneuvers") is not None for leg in trip.get("legs", [])):
        status = "maneuvers_required"
    elif first_known:
        status = "known_road_area_found"
    elif boardings:
        status = "no_known_boarding_stop"
    elif has_ferry:
        status = "ferry_reported_but_no_boarding_maneuver"
    elif anchor_road_area_id:
        status = "known_road_area_found"
    else:
        status = "no_ferry_in_external_route_anchor_required"

    road_area = None
    if first_known:
        road_area = {
            "id": first_known["roadAreaId"],
            "inference": "first_known_ferry_boarding",
            "boardingSequence": first_known["boardingSequence"],
            "stop": first_known["stop"],
        }
    elif not has_ferry and anchor_road_area_id:
        road_area = {
            "id": anchor_road_area_id,
            "inference": "no_ferry_to_known_anchor",
        }

    return {
        "schemaVersion": 1,
        "status": status,
        "maximumMatchDistanceMeters": maximum,
        "externalRouteHasFerry": has_ferry,
        "roadArea": road_area,
        "firstKnownBoarding": first_known,
        "unknownBoardingsBeforeFirstKnown": (
            first_known["boardingSequence"] - 1 if first_known else len(boardings)
        ),
        "ferryBoardings": boardings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("response", type=Path, help="Valhalla route response JSON")
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--maximum-distance", type=float)
    parser.add_argument(
        "--anchor-road-area",
        help="known road area of the external route destination; used when the route has no ferry",
    )
    args = parser.parse_args()

    response = json.loads(args.response.read_text())
    index = json.loads(args.index.read_text())
    result = classify(
        response, index, args.maximum_distance, args.anchor_road_area
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] != "maneuvers_required" else 2


if __name__ == "__main__":
    raise SystemExit(main())
