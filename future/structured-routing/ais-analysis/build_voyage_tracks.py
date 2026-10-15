#!/usr/bin/env python3
"""Create a review GeoJSON of sampled AIS voyages and application route lines."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
from collections import defaultdict
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("voyages", type=Path, help="Database created by build_voyages.py")
    parser.add_argument("saaristo", type=Path, help="saaristo.json")
    parser.add_argument("output", type=Path, help="Review GeoJSON")
    parser.add_argument("--pair-summary", type=Path)
    parser.add_argument("--minimum-voyages", type=int, default=5)
    parser.add_argument("--samples-per-direction", type=int, default=12)
    return parser.parse_args()


def percentile(values: list[int], fraction: float) -> int:
    if not values:
        return 0
    position = (len(values) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    return round(values[lower] * (upper - position) + values[upper] * (position - lower))


def line_features(feature: dict, properties: dict) -> list[dict]:
    output = []
    geometry = feature.get("geometry", {})
    if feature.get("type") == "Feature" and geometry.get("type") in {"LineString", "MultiLineString"}:
        output.append({"type": "Feature", "properties": properties, "geometry": geometry})
    for child in feature.get("features", []):
        output.extend(line_features(child, properties))
    return output


def sample_indexes(count: int, maximum: int) -> list[int]:
    if count <= maximum:
        return list(range(count))
    if maximum == 1:
        return [count // 2]
    return sorted({round(index * (count - 1) / (maximum - 1)) for index in range(maximum)})


def main() -> None:
    args = parse_args()
    connection = sqlite3.connect(f"file:{args.voyages}?mode=ro", uri=True)
    connection.execute("PRAGMA query_only=ON")
    rows = connection.execute(
        """
        SELECT voyage_id, mmsi, route_id, route_name, origin_pier, destination_pier,
               departure_utc, duration_seconds, track_distance_m, quality
        FROM voyages
        WHERE quality IN ('good', 'usable')
        ORDER BY route_id, origin_pier, destination_pier, departure_ms
        """
    ).fetchall()
    groups = defaultdict(list)
    for row in rows:
        groups[(row[2], row[4], row[5])].append(row)

    features = []
    represented_routes = set()
    represented_piers = set()
    pair_rows = []
    for (route_id, origin, destination), voyages in sorted(groups.items()):
        if len(voyages) < args.minimum_voyages:
            continue
        represented_routes.add(route_id)
        represented_piers.update((origin, destination))
        durations = sorted(row[7] for row in voyages)
        distances = sorted(row[8] or 0 for row in voyages)
        pair_rows.append({
            "route_id": route_id,
            "route_name": voyages[0][3],
            "origin_pier": origin,
            "destination_pier": destination,
            "voyages": len(voyages),
            "vessels": len({row[1] for row in voyages}),
            "duration_p10_seconds": percentile(durations, 0.10),
            "duration_median_seconds": percentile(durations, 0.50),
            "duration_p90_seconds": percentile(durations, 0.90),
            "track_distance_median_m": percentile(distances, 0.50),
        })
        for index in sample_indexes(len(voyages), args.samples_per_direction):
            voyage = voyages[index]
            coordinates = [
                [lng, lat]
                for lng, lat in connection.execute(
                    "SELECT lng, lat FROM voyage_points WHERE voyage_id=? ORDER BY sequence",
                    (voyage[0],),
                )
            ]
            if len(coordinates) < 2:
                continue
            features.append({
                "type": "Feature",
                "properties": {
                    "review_category": "ais_voyage",
                    "voyage_id": voyage[0],
                    "mmsi": voyage[1],
                    "route_id": route_id,
                    "route_name": voyage[3],
                    "origin_pier": origin,
                    "destination_pier": destination,
                    "departure_utc": voyage[6],
                    "duration_seconds": voyage[7],
                    "track_distance_m": voyage[8],
                    "quality": voyage[9],
                    "pair_voyages": len(voyages),
                },
                "geometry": {"type": "LineString", "coordinates": coordinates},
            })

    saaristo = json.loads(args.saaristo.read_text(encoding="utf-8-sig"))
    reference_features = []
    pier_features = []
    for feature in saaristo.get("features", []):
        properties = feature.get("properties", {})
        if properties.get("stype") == "connection" and properties.get("ref") in represented_routes:
            route_id = properties["ref"]
            reference_features.extend(line_features(feature, {
                "review_category": "application_route",
                "route_id": route_id,
            }))
        elif properties.get("stype") == "pier" and properties.get("ref") in represented_piers:
            pier_features.append({
                "type": "Feature",
                "properties": {
                    "review_category": "pier",
                    "pier": properties["ref"],
                },
                "geometry": feature["geometry"],
            })
    features = reference_features + features + pier_features
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if args.pair_summary:
        args.pair_summary.parent.mkdir(parents=True, exist_ok=True)
        with args.pair_summary.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(pair_rows[0]) if pair_rows else [])
            if pair_rows:
                writer.writeheader()
                writer.writerows(pair_rows)
    print(json.dumps({
        "qualified_pairs": len(pair_rows),
        "represented_routes": len(represented_routes),
        "sampled_ais_tracks": sum(
            feature["properties"].get("review_category") == "ais_voyage" for feature in features
        ),
        "application_route_features": len(reference_features),
        "pier_features": len(pier_features),
        "total_features": len(features),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
