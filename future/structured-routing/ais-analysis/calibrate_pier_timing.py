#!/usr/bin/env python3
"""Infer pier-specific berth centres and timing radii from repeated slow AIS calls."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from statistics import median


EARTH_RADIUS_M = 6_371_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path, help="Database created by prepare_ais.py")
    parser.add_argument("calls", type=Path, help="pier-calls.csv")
    parser.add_argument("weekly_candidates", type=Path, help="weekly-route-candidates.csv")
    parser.add_argument("data", type=Path, help="data.json containing route definitions")
    parser.add_argument("saaristo", type=Path, help="saaristo.json containing pier coordinates")
    parser.add_argument("output", type=Path)
    parser.add_argument("--maximum-stale-seconds", type=int, default=300)
    parser.add_argument("--slow-knots", type=float, default=1.5)
    parser.add_argument("--cluster-radius-m", type=float, default=50)
    parser.add_argument("--minimum-cluster-calls", type=int, default=5)
    parser.add_argument("--minimum-dominant-share", type=float, default=0.60)
    parser.add_argument(
        "--overrides",
        type=Path,
        help="Optional confirmed multi-berth pier configuration",
    )
    return parser.parse_args()


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as file:
        return list(csv.DictReader(file))


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def week_start(value: datetime) -> date:
    return value.date() - timedelta(days=value.weekday())


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    lat1r = math.radians(lat1)
    lat2r = math.radians(lat2)
    dlat = lat2r - lat1r
    dlng = math.radians(lng2 - lng1)
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1r) * math.cos(lat2r) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(value))


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def load_piers(path: Path) -> dict[str, tuple[float, float]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    piers = {}
    for feature in data.get("features", []):
        properties = feature.get("properties", {})
        geometry = feature.get("geometry", {})
        coordinates = geometry.get("coordinates", [])
        if properties.get("stype") == "pier" and geometry.get("type") == "Point" and len(coordinates) >= 2:
            pier = properties.get("ref")
            if pier:
                piers[pier] = (float(coordinates[1]), float(coordinates[0]))
    return piers


def load_route_piers(path: Path) -> dict[str, set[str]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return {
        route_id: {
            pier.get("id") or pier.get("name")
            for pier in route.get("piers", [])
            if pier.get("id") or pier.get("name")
        }
        for route_id, route in data.get("routes", {}).items()
    }


def confidence(score: float, margin: float) -> str:
    if score >= 0.65 and margin >= 0.08:
        return "high"
    if score >= 0.50 and margin >= 0.03:
        return "probable"
    return "ambiguous"


def load_assignments(path: Path) -> dict[tuple[int, date], str]:
    assignments = {}
    for row in read_csv(path):
        if row["rank"] != "1":
            continue
        if confidence(float(row["score"]), float(row["margin"] or 0)) == "ambiguous":
            continue
        assignments[(int(row["mmsi"]), date.fromisoformat(row["week_start"]))] = row["route_id"]
    return assignments


def load_calls(path: Path, assignments: dict, route_piers: dict) -> list[dict]:
    calls = []
    for row in read_csv(path):
        if row.get("operational") != "1" or row.get("call_type") != "slow_dwell":
            continue
        arrival = parse_utc(row["arrival_utc"])
        mmsi = int(row["mmsi"])
        route_id = assignments.get((mmsi, week_start(arrival)))
        if not route_id or row["pier"] not in route_piers.get(route_id, set()):
            continue
        calls.append({
            "mmsi": mmsi,
            "pier": row["pier"],
            "route_id": route_id,
            "arrival_ms": round(arrival.timestamp() * 1000),
            "departure_ms": round(parse_utc(row["departure_utc"]).timestamp() * 1000),
            "slow_points": [],
        })
    calls.sort(key=lambda row: (row["mmsi"], row["arrival_ms"]))
    return calls


def collect_call_positions(
    database: Path,
    calls: list[dict],
    slow_knots: float,
    maximum_stale_seconds: int,
) -> dict[str, list[dict]]:
    by_vessel: dict[int, list[dict]] = defaultdict(list)
    for call in calls:
        by_vessel[call["mmsi"]].append(call)
    retained_mmsis = sorted(by_vessel)
    placeholders = ",".join("?" for _ in retained_mmsis)
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    indexes = defaultdict(int)
    query = f"""
        SELECT mmsi, ais_timestamp, lat, lng, sog, age_at_first_ms
        FROM observations
        WHERE mmsi IN ({placeholders})
        ORDER BY mmsi, ais_timestamp, observation_id
    """
    for mmsi, timestamp, lat, lng, sog, age_ms in connection.execute(query, retained_mmsis):
        vessel_calls = by_vessel[mmsi]
        index = indexes[mmsi]
        while index < len(vessel_calls) and timestamp > vessel_calls[index]["departure_ms"]:
            index += 1
        indexes[mmsi] = index
        if index >= len(vessel_calls):
            continue
        call = vessel_calls[index]
        if timestamp < call["arrival_ms"]:
            continue
        if -60_000 <= age_ms <= maximum_stale_seconds * 1000 and 0 <= sog <= slow_knots:
            call["slow_points"].append((float(lat), float(lng)))
    connection.close()

    positions: dict[str, list[dict]] = defaultdict(list)
    for call in calls:
        if not call["slow_points"]:
            continue
        positions[call["pier"]].append({
            "lat": median(point[0] for point in call["slow_points"]),
            "lng": median(point[1] for point in call["slow_points"]),
            "route_id": call["route_id"],
            "mmsi": call["mmsi"],
        })
    return positions


def connected_clusters(points: list[dict], radius_m: float) -> list[list[int]]:
    if not points:
        return []
    reference_lat = median(point["lat"] for point in points)
    metres_lat = math.pi * EARTH_RADIUS_M / 180
    metres_lng = metres_lat * math.cos(math.radians(reference_lat))
    xy = [(point["lng"] * metres_lng, point["lat"] * metres_lat) for point in points]
    cells: dict[tuple[int, int], list[int]] = defaultdict(list)
    parents = list(range(len(points)))

    def find(value: int) -> int:
        while parents[value] != value:
            parents[value] = parents[parents[value]]
            value = parents[value]
        return value

    def union(first: int, second: int) -> None:
        first_root, second_root = find(first), find(second)
        if first_root != second_root:
            parents[second_root] = first_root

    for index, (x, y) in enumerate(xy):
        cell = (math.floor(x / radius_m), math.floor(y / radius_m))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for other in cells.get((cell[0] + dx, cell[1] + dy), []):
                    ox, oy = xy[other]
                    if math.hypot(x - ox, y - oy) <= radius_m:
                        union(index, other)
        cells[cell].append(index)
    clusters: dict[int, list[int]] = defaultdict(list)
    for index in range(len(points)):
        clusters[find(index)].append(index)
    return sorted(clusters.values(), key=len, reverse=True)


def calibrate_pier(
    pier: str,
    points: list[dict],
    application_position: tuple[float, float] | None,
    args: argparse.Namespace,
    override: dict | None = None,
) -> dict:
    cluster_radius_m = float((override or {}).get("cluster_radius_m", args.cluster_radius_m))
    clusters = connected_clusters(points, cluster_radius_m)
    dominant = clusters[0] if clusters else []
    dominant_points = [points[index] for index in dominant]
    inferred_lat = median(point["lat"] for point in dominant_points) if dominant_points else None
    inferred_lng = median(point["lng"] for point in dominant_points) if dominant_points else None
    distances = (
        [haversine_m(inferred_lat, inferred_lng, point["lat"], point["lng"]) for point in dominant_points]
        if dominant_points else []
    )
    spread_p90 = percentile(distances, 0.90)
    dominant_share = len(dominant) / len(points) if points else 0
    offset = (
        haversine_m(*application_position, inferred_lat, inferred_lng)
        if application_position and inferred_lat is not None else None
    )
    accepted_cluster_count = int((override or {}).get("accepted_clusters", 1))
    minimum_radius_m = float((override or {}).get("minimum_radius_m", 50))
    accepted_clusters = clusters[:accepted_cluster_count]
    accepted_centers = []
    for cluster in accepted_clusters:
        cluster_points = [points[index] for index in cluster]
        if len(cluster_points) < args.minimum_cluster_calls:
            continue
        centre_lat = median(point["lat"] for point in cluster_points)
        centre_lng = median(point["lng"] for point in cluster_points)
        centre_distances = [
            haversine_m(centre_lat, centre_lng, point["lat"], point["lng"])
            for point in cluster_points
        ]
        centre_p90 = percentile(centre_distances, 0.90) or 0
        accepted_centers.append({
            "lat": round(centre_lat, 7),
            "lng": round(centre_lng, 7),
            "radius_m": round(min(75.0, max(minimum_radius_m, centre_p90 + 10)), 1),
            "calls": len(cluster_points),
            "spread_p90_m": round(centre_p90, 1),
        })
    if len(accepted_centers) >= 2:
        status = "multi_berth"
    elif accepted_centers and (override or {}).get("confirmed"):
        status = "calibrated_override"
    elif len(dominant) < args.minimum_cluster_calls:
        status = "insufficient"
    elif dominant_share < args.minimum_dominant_share:
        status = "multimodal"
    elif spread_p90 is not None and spread_p90 > 60:
        status = "diffuse"
    elif offset is not None and offset > 150:
        status = "review_offset"
    elif offset is not None and offset > 50:
        status = "calibrated_offset"
    else:
        status = "calibrated"
    timing_radius = min(75.0, max(50.0, (spread_p90 or 0) + 10))
    return {
        "pier": pier,
        "status": status,
        "calls_with_slow_position": len(points),
        "dominant_cluster_calls": len(dominant),
        "dominant_cluster_share": round(dominant_share, 4),
        "secondary_cluster_calls": len(clusters[1]) if len(clusters) > 1 else 0,
        "routes": ";".join(sorted({point["route_id"] for point in dominant_points})),
        "vessels": len({point["mmsi"] for point in dominant_points}),
        "application_lat": application_position[0] if application_position else None,
        "application_lng": application_position[1] if application_position else None,
        "inferred_lat": round(inferred_lat, 7) if inferred_lat is not None else None,
        "inferred_lng": round(inferred_lng, 7) if inferred_lng is not None else None,
        "application_offset_m": round(offset, 1) if offset is not None else None,
        "cluster_spread_p50_m": round(percentile(distances, 0.50), 1) if distances else None,
        "cluster_spread_p90_m": round(spread_p90, 1) if spread_p90 is not None else None,
        "timing_radius_m": round(timing_radius, 1),
        "accepted_centers": len(accepted_centers),
        "secondary_inferred_lat": accepted_centers[1]["lat"] if len(accepted_centers) > 1 else None,
        "secondary_inferred_lng": accepted_centers[1]["lng"] if len(accepted_centers) > 1 else None,
        "secondary_cluster_spread_p90_m": accepted_centers[1]["spread_p90_m"] if len(accepted_centers) > 1 else None,
        "_centers": accepted_centers,
    }


def main() -> None:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    assignments = load_assignments(args.weekly_candidates)
    route_piers = load_route_piers(args.data)
    piers = load_piers(args.saaristo)
    overrides = (
        json.loads(args.overrides.read_text(encoding="utf-8")) if args.overrides else {}
    )
    calls = load_calls(args.calls, assignments, route_piers)
    positions = collect_call_positions(
        args.database, calls, args.slow_knots, args.maximum_stale_seconds
    )
    rows = [
        calibrate_pier(pier, pier_points, piers.get(pier), args, overrides.get(pier))
        for pier, pier_points in sorted(positions.items())
    ]
    fields = [field for field in rows[0] if not field.startswith("_")] if rows else ["pier"]
    with (args.output / "pier-calibration.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field) for field in fields} for row in rows)
    usable_statuses = {
        "calibrated", "calibrated_offset", "calibrated_override", "multi_berth"
    }
    calibration = {
        row["pier"]: {
            "lat": row["inferred_lat"],
            "lng": row["inferred_lng"],
            "radius_m": row["timing_radius_m"],
            "status": row["status"],
            "calls": row["dominant_cluster_calls"],
            "application_offset_m": row["application_offset_m"],
            "centers": row["_centers"],
        }
        for row in rows
        if row["status"] in usable_statuses
    }
    (args.output / "pier-calibration.json").write_text(
        json.dumps(calibration, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    summary = {
        "eligible_slow_calls": len(calls),
        "calls_with_fresh_slow_position": sum(len(value) for value in positions.values()),
        "piers": len(rows),
        "usable_piers": len(calibration),
        "status": dict(sorted({status: sum(row["status"] == status for row in rows) for status in {row["status"] for row in rows}}.items())),
        "parameters": {
            "maximum_stale_seconds": args.maximum_stale_seconds,
            "slow_knots": args.slow_knots,
            "cluster_radius_m": args.cluster_radius_m,
            "minimum_cluster_calls": args.minimum_cluster_calls,
            "minimum_dominant_share": args.minimum_dominant_share,
        },
    }
    (args.output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
