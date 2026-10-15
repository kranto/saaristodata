#!/usr/bin/env python3
"""Prepare an embedded OSM coastline and filter offshore stop clusters."""

from __future__ import annotations

import argparse
import collections
import json
import math
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("overpass", type=Path)
    parser.add_argument("review", type=Path)
    parser.add_argument("coastline_output", type=Path)
    parser.add_argument("review_output", type=Path)
    parser.add_argument("--max-offshore-metres", type=float, default=100.0)
    parser.add_argument("--simplify-degrees", type=float, default=0.0005)
    return parser.parse_args()


def point_segment_distance_metres(
    point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]
) -> float:
    lon, lat = point
    scale_x = 111_320.0 * math.cos(math.radians(lat))
    scale_y = 110_540.0
    x1, y1 = (start[0] - lon) * scale_x, (start[1] - lat) * scale_y
    x2, y2 = (end[0] - lon) * scale_x, (end[1] - lat) * scale_y
    dx, dy = x2 - x1, y2 - y1
    denominator = dx * dx + dy * dy
    if denominator:
        t = max(0.0, min(1.0, -(x1 * dx + y1 * dy) / denominator))
        x1 += t * dx
        y1 += t * dy
    return math.hypot(x1, y1)


def simplify(points: list[tuple[float, float]], epsilon: float) -> list[tuple[float, float]]:
    if len(points) <= 2:
        return points
    keep = {0, len(points) - 1}
    stack = [(0, len(points) - 1)]
    epsilon_squared = epsilon * epsilon
    while stack:
        first, last = stack.pop()
        x1, y1 = points[first]
        x2, y2 = points[last]
        dx, dy = x2 - x1, y2 - y1
        denominator = dx * dx + dy * dy
        furthest = -1
        furthest_distance = epsilon_squared
        for index in range(first + 1, last):
            x, y = points[index]
            if denominator:
                t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / denominator))
                nearest_x, nearest_y = x1 + t * dx, y1 + t * dy
            else:
                nearest_x, nearest_y = x1, y1
            distance = (x - nearest_x) ** 2 + (y - nearest_y) ** 2
            if distance > furthest_distance:
                furthest = index
                furthest_distance = distance
        if furthest >= 0:
            keep.add(furthest)
            stack.extend(((first, furthest), (furthest, last)))
    return [points[index] for index in sorted(keep)]


def encode_polyline(points: list[tuple[float, float]]) -> str:
    result: list[str] = []
    previous_lat = 0
    previous_lon = 0
    for lon, lat in points:
        lat_value = round(lat * 100_000)
        lon_value = round(lon * 100_000)
        for delta in (lat_value - previous_lat, lon_value - previous_lon):
            value = ~(delta << 1) if delta < 0 else delta << 1
            while value >= 0x20:
                result.append(chr((0x20 | (value & 0x1F)) + 63))
                value >>= 5
            result.append(chr(value + 63))
        previous_lat = lat_value
        previous_lon = lon_value
    return "".join(result)


def merge_ways(ways: list[tuple[list[int], list[tuple[float, float]]]]) -> list[list[tuple[float, float]]]:
    endpoints: dict[int, list[int]] = collections.defaultdict(list)
    for index, (nodes, _points) in enumerate(ways):
        endpoints[nodes[0]].append(index)
        endpoints[nodes[-1]].append(index)
    unused = set(range(len(ways)))
    chains: list[list[tuple[float, float]]] = []
    while unused:
        index = unused.pop()
        nodes, points = ways[index]
        nodes = list(nodes)
        points = list(points)
        for extend_start in (False, True):
            while True:
                node = nodes[0] if extend_start else nodes[-1]
                candidate = next((item for item in endpoints[node] if item in unused), None)
                if candidate is None:
                    break
                unused.remove(candidate)
                other_nodes, other_points = ways[candidate]
                if extend_start:
                    if other_nodes[-1] == node:
                        nodes = other_nodes[:-1] + nodes
                        points = other_points[:-1] + points
                    else:
                        nodes = list(reversed(other_nodes[1:])) + nodes
                        points = list(reversed(other_points[1:])) + points
                elif other_nodes[0] == node:
                    nodes += other_nodes[1:]
                    points += other_points[1:]
                else:
                    nodes += list(reversed(other_nodes[:-1]))
                    points += list(reversed(other_points[:-1]))
        chains.append(points)
    return chains


def main() -> None:
    args = parse_args()
    overpass = json.loads(args.overpass.read_text(encoding="utf-8"))
    review = json.loads(args.review.read_text(encoding="utf-8"))

    ways: list[tuple[list[int], list[tuple[float, float]]]] = []
    for element in overpass.get("elements", []):
        nodes = element.get("nodes", [])
        points = [(point["lon"], point["lat"]) for point in element.get("geometry", [])]
        if len(points) >= 2 and len(nodes) == len(points):
            ways.append((nodes, points))

    unknown = [
        feature
        for feature in review["features"]
        if feature["properties"].get("review_category") == "unknown_stop"
    ]
    stop_points = [tuple(feature["geometry"]["coordinates"]) for feature in unknown]
    minimum_distances = [math.inf] * len(stop_points)
    cell_size = 0.02
    stop_cells: dict[tuple[int, int], list[int]] = collections.defaultdict(list)
    for index, (lon, lat) in enumerate(stop_points):
        stop_cells[(math.floor(lon / cell_size), math.floor(lat / cell_size))].append(index)

    for _nodes, points in ways:
        for start, end in zip(points, points[1:]):
            min_x = math.floor(min(start[0], end[0]) / cell_size) - 1
            max_x = math.floor(max(start[0], end[0]) / cell_size) + 1
            min_y = math.floor(min(start[1], end[1]) / cell_size) - 1
            max_y = math.floor(max(start[1], end[1]) / cell_size) + 1
            for cell_x in range(min_x, max_x + 1):
                for cell_y in range(min_y, max_y + 1):
                    for stop_index in stop_cells.get((cell_x, cell_y), []):
                        distance = point_segment_distance_metres(stop_points[stop_index], start, end)
                        if distance < minimum_distances[stop_index]:
                            minimum_distances[stop_index] = distance

    retained_unknown_ids: set[int] = set()
    for feature, distance in zip(unknown, minimum_distances):
        feature["properties"]["distance_to_coast_m"] = round(distance) if math.isfinite(distance) else None
        if distance <= args.max_offshore_metres:
            retained_unknown_ids.add(id(feature))
    review["features"] = [
        feature
        for feature in review["features"]
        if feature["properties"].get("review_category") != "unknown_stop"
        or id(feature) in retained_unknown_ids
    ]

    reference_points = [
        tuple(feature["geometry"]["coordinates"])
        for feature in review["features"]
        if feature["geometry"]["type"] == "Point"
    ]
    encoded_lines: list[str] = []
    retained_coordinate_count = 0
    for chain in merge_ways(ways):
        longitudes = [point[0] for point in chain]
        latitudes = [point[1] for point in chain]
        west, east = min(longitudes), max(longitudes)
        south, north = min(latitudes), max(latitudes)
        is_significant = max(east - west, north - south) >= 0.01
        is_near_point = any(
            west - 0.02 <= lon <= east + 0.02 and south - 0.02 <= lat <= north + 0.02
            for lon, lat in reference_points
        )
        if not is_significant and not is_near_point:
            continue
        simplified = simplify(chain, args.simplify_degrees)
        if len(simplified) < 2:
            continue
        encoded_lines.append(encode_polyline(simplified))
        retained_coordinate_count += len(simplified)

    coastline = {
        "source": "OpenStreetMap contributors via Overpass API",
        "encoding": "google-polyline-1e5-lat-lon",
        "lines": encoded_lines,
        "line_count": len(encoded_lines),
        "coordinate_count": retained_coordinate_count,
    }
    args.coastline_output.parent.mkdir(parents=True, exist_ok=True)
    args.review_output.parent.mkdir(parents=True, exist_ok=True)
    args.coastline_output.write_text(json.dumps(coastline, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    args.review_output.write_text(json.dumps(review, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(
        f"Retained {len(retained_unknown_ids)}/{len(unknown)} unknown-stop clusters within "
        f"{args.max_offshore_metres:.0f} m of coastline; coastline has "
        f"{len(encoded_lines)} lines and {retained_coordinate_count} coordinates"
    )


if __name__ == "__main__":
    main()
