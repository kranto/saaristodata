#!/usr/bin/env python3
"""Render sampled AIS voyages as a compact inline visualization payload."""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("voyages", type=Path)
    parser.add_argument("saaristo", type=Path)
    parser.add_argument("area", type=Path)
    parser.add_argument("coastline", type=Path)
    parser.add_argument("template", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--minimum-voyages", type=int, default=20)
    parser.add_argument("--samples-per-direction", type=int, default=3)
    return parser.parse_args()


def encode_polyline(coordinates: list[tuple[float, float]]) -> str:
    output = []
    previous_lat = 0
    previous_lng = 0
    for lng, lat in coordinates:
        lat_value = round(lat * 100_000)
        lng_value = round(lng * 100_000)
        for value in (lat_value - previous_lat, lng_value - previous_lng):
            value = ~(value << 1) if value < 0 else value << 1
            while value >= 0x20:
                output.append(chr((0x20 | (value & 0x1F)) + 63))
                value >>= 5
            output.append(chr(value + 63))
        previous_lat = lat_value
        previous_lng = lng_value
    return "".join(output)


def sample_indexes(count: int, maximum: int) -> list[int]:
    if count <= maximum:
        return list(range(count))
    if maximum == 1:
        return [count // 2]
    return sorted({round(index * (count - 1) / (maximum - 1)) for index in range(maximum)})


def line_geometries(feature: dict) -> list[list[tuple[float, float]]]:
    output = []
    geometry = feature.get("geometry", {})
    if geometry.get("type") == "LineString":
        output.append(geometry["coordinates"])
    elif geometry.get("type") == "MultiLineString":
        output.extend(geometry["coordinates"])
    for child in feature.get("features", []):
        output.extend(line_geometries(child))
    return output


def main() -> None:
    args = parse_args()
    connection = sqlite3.connect(f"file:{args.voyages}?mode=ro", uri=True)
    rows = connection.execute(
        """
        SELECT voyage_id, route_id, route_name, origin_pier, destination_pier,
               duration_seconds, departure_ms
        FROM voyages
        WHERE quality IN ('good', 'usable')
        ORDER BY route_id, origin_pier, destination_pier, departure_ms
        """
    ).fetchall()
    groups = defaultdict(list)
    for row in rows:
        groups[(row[1], row[3], row[4])].append(row)

    route_payload = defaultdict(lambda: {"name": "", "tracks": [], "pairs": 0, "voyages": 0})
    represented_piers = defaultdict(set)
    for (route_id, origin, destination), voyages in groups.items():
        if len(voyages) < args.minimum_voyages:
            continue
        payload = route_payload[route_id]
        payload["name"] = voyages[0][2]
        payload["pairs"] += 1
        payload["voyages"] += len(voyages)
        represented_piers[route_id].update((origin, destination))
        durations = sorted(row[5] for row in voyages)
        median = durations[len(durations) // 2]
        for index in sample_indexes(len(voyages), args.samples_per_direction):
            voyage_id = voyages[index][0]
            coordinates = connection.execute(
                "SELECT lng, lat FROM voyage_points WHERE voyage_id=? ORDER BY sequence",
                (voyage_id,),
            ).fetchall()
            if len(coordinates) >= 2:
                payload["tracks"].append([
                    encode_polyline(coordinates), origin, destination, len(voyages), median,
                ])

    saaristo = json.loads(args.saaristo.read_text(encoding="utf-8-sig"))
    pier_coordinates = {}
    for feature in saaristo.get("features", []):
        properties = feature.get("properties", {})
        if properties.get("stype") == "pier" and feature.get("geometry", {}).get("type") == "Point":
            pier_coordinates[properties.get("ref")] = feature["geometry"]["coordinates"]
        elif properties.get("stype") == "connection" and properties.get("ref") in route_payload:
            route_payload[properties["ref"]]["reference"] = [
                encode_polyline(line) for line in line_geometries(feature)
            ]
    routes = []
    for route_id, payload in route_payload.items():
        payload["id"] = route_id
        payload.setdefault("reference", [])
        payload["piers"] = [
            [pier, *pier_coordinates[pier]]
            for pier in sorted(represented_piers[route_id])
            if pier in pier_coordinates
        ]
        routes.append(payload)
    routes.sort(key=lambda route: (-route["voyages"], route["name"]))
    coastline = json.loads(args.coastline.read_text(encoding="utf-8"))
    data = {
        "area": json.loads(args.area.read_text(encoding="utf-8")),
        "coastline": coastline["lines"],
        "routes": routes,
    }
    template = args.template.read_text(encoding="utf-8")
    if template.count("__DATA__") != 1:
        raise ValueError("Template must contain exactly one __DATA__ placeholder")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        template.replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":"))),
        encoding="utf-8",
    )
    print(json.dumps({
        "routes": len(routes),
        "tracks": sum(len(route["tracks"]) for route in routes),
        "bytes": args.output.stat().st_size,
        "output": str(args.output),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
