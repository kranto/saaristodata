#!/usr/bin/env python3
"""Detect pier calls and preliminary route candidates from prepared AIS data."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path


EARTH_RADIUS_M = 6_371_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path, help="Database created by prepare_ais.py")
    parser.add_argument("saaristo", type=Path, help="saaristo.json containing pier coordinates")
    parser.add_argument("data", type=Path, help="data.json containing route definitions")
    parser.add_argument("output", type=Path, help="Output directory")
    parser.add_argument("--pier-radius-m", type=float, default=250)
    parser.add_argument("--certain-distance-m", type=float, default=50)
    parser.add_argument("--close-proximity-max-speed-knots", type=float, default=5)
    parser.add_argument("--stop-speed-knots", type=float, default=1.5)
    parser.add_argument("--minimum-call-seconds", type=int, default=45)
    parser.add_argument("--maximum-call-hours", type=float, default=6)
    parser.add_argument("--maximum-stale-seconds", type=int, default=300)
    parser.add_argument("--turnaround-degrees", type=float, default=120)
    parser.add_argument("--minimum-direction-leg-m", type=float, default=75)
    parser.add_argument("--vessel-summary", type=Path)
    parser.add_argument("--minimum-active-days", type=int, default=0)
    return parser.parse_args()


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    lat1r = math.radians(lat1)
    lat2r = math.radians(lat2)
    dlat = lat2r - lat1r
    dlng = math.radians(lng2 - lng1)
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1r) * math.cos(lat2r) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(value))


def iso_utc(milliseconds: int) -> str:
    return datetime.fromtimestamp(milliseconds / 1000, UTC).isoformat().replace("+00:00", "Z")


def bearing_degrees(first: dict, second: dict, minimum_distance_m: float = 0) -> float | None:
    if haversine_m(first["lat"], first["lng"], second["lat"], second["lng"]) < minimum_distance_m:
        return None
    lat1 = math.radians(first["lat"])
    lat2 = math.radians(second["lat"])
    dlng = math.radians(second["lng"] - first["lng"])
    x = math.sin(dlng) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlng)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def direction_change_degrees(first: float | None, second: float | None) -> float | None:
    if first is None or second is None:
        return None
    difference = abs(first - second) % 360
    return min(difference, 360 - difference)


def load_piers(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    piers = []
    seen = set()
    for feature in data.get("features", []):
        properties = feature.get("properties", {})
        geometry = feature.get("geometry", {})
        if properties.get("stype") != "pier" or geometry.get("type") != "Point":
            continue
        pier_id = properties.get("ref") or properties.get("sname")
        coordinates = geometry.get("coordinates", [])
        if not pier_id or len(coordinates) < 2 or pier_id in seen:
            continue
        seen.add(pier_id)
        piers.append({"id": pier_id, "lng": float(coordinates[0]), "lat": float(coordinates[1])})
    return piers


class PierIndex:
    def __init__(self, piers: list[dict], cell_size: float = 0.02):
        self.cell_size = cell_size
        self.cells: dict[tuple[int, int], list[dict]] = defaultdict(list)
        for pier in piers:
            self.cells[self.cell(pier["lat"], pier["lng"])].append(pier)

    def cell(self, lat: float, lng: float) -> tuple[int, int]:
        return int(math.floor(lat / self.cell_size)), int(math.floor(lng / self.cell_size))

    def nearest(self, lat: float, lng: float, maximum_m: float) -> tuple[dict | None, float | None]:
        row, column = self.cell(lat, lng)
        best = None
        best_distance = maximum_m
        for row_offset in (-1, 0, 1):
            for column_offset in (-1, 0, 1):
                for pier in self.cells.get((row + row_offset, column + column_offset), []):
                    distance = haversine_m(lat, lng, pier["lat"], pier["lng"])
                    if distance <= best_distance:
                        best = pier
                        best_distance = distance
        return best, best_distance if best else None


def load_routes(path: Path, known_piers: set[str]) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    routes = {}
    for route_id, route in data.get("routes", {}).items():
        if route.get("obsolete"):
            continue
        pier_ids = []
        for pier in route.get("piers", []):
            pier_id = pier.get("id") or pier.get("name")
            if pier_id in known_piers and pier_id not in pier_ids:
                pier_ids.append(pier_id)
        routes[route_id] = {
            "id": route_id,
            "name": route.get("name_fi") or route.get("name") or route_id,
            "piers": pier_ids,
        }
    return routes


def write_csv(path: Path, fieldnames: list[str], rows) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as file:
        return list(csv.DictReader(file))


def main() -> None:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    piers = load_piers(args.saaristo)
    pier_index = PierIndex(piers)
    routes = load_routes(args.data, {pier["id"] for pier in piers})
    connection = sqlite3.connect(f"file:{args.database}?mode=ro", uri=True)
    connection.execute("PRAGMA query_only=ON")
    retained_mmsis = None
    if args.vessel_summary:
        retained_mmsis = {
            int(row["mmsi"])
            for row in read_csv(args.vessel_summary)
            if int(row["active_days"]) >= args.minimum_active_days
        }

    calls: list[dict] = []
    unknown_cells: dict[tuple[int, int], dict] = {}
    current_mmsi = None
    current_call = None
    last_collection_ms = None
    previous_point = None
    processed = 0
    accepted = 0
    started = time.monotonic()

    def finish_call(after_point: dict | None = None) -> None:
        nonlocal current_call
        if not current_call:
            return
        duration_seconds = max(
            0,
            (current_call["departure_collection_ms"] - current_call["arrival_collection_ms"]) // 1000,
        )
        current_call["duration_seconds"] = duration_seconds
        inbound = bearing_degrees(
            current_call["before_point"], current_call["closest_point"], args.minimum_direction_leg_m
        ) if current_call["before_point"] else None
        outbound = bearing_degrees(
            current_call["closest_point"], after_point, args.minimum_direction_leg_m
        ) if after_point else None
        position_turn = direction_change_degrees(inbound, outbound)
        heading_before = current_call["before_point"]["heading"] if current_call["before_point"] else None
        heading_after = after_point["heading"] if after_point else None
        if heading_before == 511 or heading_after == 511:
            heading_turn = None
        else:
            heading_turn = direction_change_degrees(heading_before, heading_after)
        turnaround = position_turn is not None and position_turn >= args.turnaround_degrees
        slow_dwell = (
            duration_seconds >= args.minimum_call_seconds
            and current_call["minimum_sog"] <= args.stop_speed_knots
        )
        area_dwell = duration_seconds >= args.minimum_call_seconds and current_call["observations"] >= 2
        slow_sample = (
            current_call["minimum_sog"] <= args.stop_speed_knots
            and current_call["minimum_distance_m"] <= min(150, args.pier_radius_m)
        )
        close_proximity = (
            current_call["minimum_distance_m"] <= args.certain_distance_m
            and current_call["minimum_sog"] <= args.close_proximity_max_speed_knots
        )
        duration_valid = duration_seconds <= args.maximum_call_hours * 3600
        current_call["position_turn_degrees"] = round(position_turn, 1) if position_turn is not None else ""
        current_call["heading_turn_degrees"] = round(heading_turn, 1) if heading_turn is not None else ""
        current_call["call_type"] = (
            "slow_dwell"
            if slow_dwell
            else "area_dwell"
            if area_dwell
            else "close_proximity"
            if close_proximity
            else "turnaround"
            if turnaround
            else "slow_sample"
            if slow_sample
            else "unconfirmed"
        )
        current_call["operational"] = int(
            duration_valid and (slow_dwell or area_dwell or close_proximity or turnaround or slow_sample)
        )
        current_call["arrival_utc"] = iso_utc(current_call.pop("arrival_ais_ms"))
        current_call["departure_utc"] = iso_utc(current_call.pop("departure_ais_ms"))
        current_call.pop("arrival_collection_ms")
        current_call.pop("departure_collection_ms")
        current_call.pop("before_point")
        current_call.pop("closest_point")
        calls.append(current_call)
        current_call = None

    query = """
        SELECT mmsi, ais_timestamp, lat, lng, sog, heading,
               first_collection_ms, last_collection_ms,
               age_at_first_ms, age_at_last_ms, poll_count
        FROM observations
    """
    parameters: tuple[int, ...] = ()
    if retained_mmsis is not None:
        placeholders = ",".join("?" for _ in retained_mmsis)
        query += f" WHERE mmsi IN ({placeholders})"
        parameters = tuple(sorted(retained_mmsis))
    query += " ORDER BY mmsi, ais_timestamp, observation_id"
    for row in connection.execute(query, parameters):
        processed += 1
        if processed % 1_000_000 == 0:
            print(
                f"observations={processed:,} calls={len(calls):,} elapsed={time.monotonic() - started:.0f}s",
                file=sys.stderr,
                flush=True,
            )
        (
            mmsi,
            timestamp,
            lat,
            lng,
            sog,
            _heading,
            first_collection,
            last_collection,
            age_at_first,
            _age_at_last,
            poll_count,
        ) = row
        if mmsi != current_mmsi:
            finish_call()
            current_mmsi = mmsi
            last_collection_ms = None
            previous_point = None
        valid_age = -60_000 <= age_at_first <= args.maximum_stale_seconds * 1000
        valid_speed = 0 <= sog < 102.3
        if not valid_age or not valid_speed:
            finish_call()
            last_collection_ms = last_collection
            previous_point = None
            continue
        accepted += 1
        point = {"lat": lat, "lng": lng, "heading": _heading, "timestamp": timestamp}
        pier, distance = pier_index.nearest(lat, lng, args.pier_radius_m)
        stopped = sog <= args.stop_speed_knots
        gap_too_long = last_collection_ms is not None and first_collection - last_collection_ms > 20 * 60 * 1000
        if gap_too_long:
            finish_call()
            previous_point = None
        if pier:
            if current_call and current_call["pier"] == pier["id"]:
                current_call["departure_ais_ms"] = max(current_call["departure_ais_ms"], timestamp)
                current_call["departure_collection_ms"] = max(
                    current_call["departure_collection_ms"],
                    min(last_collection, timestamp + args.maximum_stale_seconds * 1000),
                )
                current_call["observations"] += 1
                current_call["polls"] += poll_count
                current_call["minimum_sog"] = min(current_call["minimum_sog"], sog)
                if distance < current_call["minimum_distance_m"]:
                    current_call["minimum_distance_m"] = round(distance, 1)
                    current_call["closest_point"] = point
            else:
                finish_call(point)
                current_call = {
                    "mmsi": mmsi,
                    "pier": pier["id"],
                    "month": datetime.fromtimestamp(timestamp / 1000, UTC).strftime("%Y-%m"),
                    "arrival_ais_ms": timestamp,
                    "departure_ais_ms": timestamp,
                    "arrival_collection_ms": first_collection,
                    "departure_collection_ms": min(
                        last_collection, timestamp + args.maximum_stale_seconds * 1000
                    ),
                    "observations": 1,
                    "polls": poll_count,
                    "minimum_distance_m": round(distance, 1),
                    "minimum_sog": sog,
                    "before_point": previous_point,
                    "closest_point": point,
                }
        else:
            finish_call(point)
        if not pier and stopped:
            cell_size = 0.002
            key = (int(math.floor(lat / cell_size)), int(math.floor(lng / cell_size)))
            cell = unknown_cells.setdefault(
                key,
                {
                    "lat_sum": 0.0,
                    "lng_sum": 0.0,
                    "observations": 0,
                    "polls": 0,
                    "mmsis": set(),
                    "days": set(),
                },
            )
            cell["lat_sum"] += lat
            cell["lng_sum"] += lng
            cell["observations"] += 1
            cell["polls"] += poll_count
            cell["mmsis"].add(mmsi)
            cell["days"].add(datetime.fromtimestamp(timestamp / 1000, UTC).date().isoformat())
        last_collection_ms = last_collection
        previous_point = point
    finish_call()

    operational_calls = [call for call in calls if call["operational"]]
    call_fields = [
        "mmsi",
        "pier",
        "month",
        "arrival_utc",
        "departure_utc",
        "duration_seconds",
        "observations",
        "polls",
        "minimum_distance_m",
        "minimum_sog",
        "position_turn_degrees",
        "heading_turn_degrees",
        "call_type",
        "operational",
    ]
    write_csv(args.output / "pier-calls.csv", call_fields, calls)

    calls_by_vessel_month: dict[tuple[int, str], Counter] = defaultdict(Counter)
    for call in operational_calls:
        calls_by_vessel_month[(call["mmsi"], call["month"])][call["pier"]] += 1
    candidate_rows = []
    for (mmsi, month), pier_counts in calls_by_vessel_month.items():
        total_calls = sum(pier_counts.values())
        candidates = []
        for route in routes.values():
            route_piers = set(route["piers"])
            matched_piers = route_piers.intersection(pier_counts)
            if len(route_piers) < 2 or len(matched_piers) < 2:
                continue
            matched_calls = sum(pier_counts[pier] for pier in matched_piers)
            coverage = len(matched_piers) / len(route_piers)
            call_share = matched_calls / total_calls
            score = coverage * call_share
            candidates.append((score, matched_calls, len(matched_piers), route))
        for rank, (score, matched_calls, matched_piers, route) in enumerate(
            sorted(candidates, reverse=True, key=lambda item: (item[0], item[1]))[:3], start=1
        ):
            candidate_rows.append(
                {
                    "month": month,
                    "mmsi": mmsi,
                    "rank": rank,
                    "route_id": route["id"],
                    "route_name": route["name"],
                    "score": round(score, 4),
                    "matched_calls": matched_calls,
                    "total_calls": total_calls,
                    "matched_piers": matched_piers,
                    "route_piers": len(route["piers"]),
                    "observed_piers": ";".join(
                        f"{pier}:{count}" for pier, count in pier_counts.most_common()
                    ),
                }
            )
    candidate_fields = [
        "month",
        "mmsi",
        "rank",
        "route_id",
        "route_name",
        "score",
        "matched_calls",
        "total_calls",
        "matched_piers",
        "route_piers",
        "observed_piers",
    ]
    write_csv(args.output / "route-candidates.csv", candidate_fields, candidate_rows)

    unknown_rows = []
    for cell in unknown_cells.values():
        if cell["observations"] < 10 or len(cell["days"]) < 2:
            continue
        unknown_rows.append(
            {
                "lat": round(cell["lat_sum"] / cell["observations"], 6),
                "lng": round(cell["lng_sum"] / cell["observations"], 6),
                "observations": cell["observations"],
                "polls": cell["polls"],
                "vessels": len(cell["mmsis"]),
                "active_days": len(cell["days"]),
                "mmsis": ";".join(str(value) for value in sorted(cell["mmsis"])),
            }
        )
    unknown_rows.sort(key=lambda row: (row["active_days"], row["observations"]), reverse=True)
    write_csv(
        args.output / "unknown-stop-cells.csv",
        ["lat", "lng", "observations", "polls", "vessels", "active_days", "mmsis"],
        unknown_rows,
    )

    summary = {
        "database": str(args.database.resolve()),
        "known_piers_with_coordinates": len(piers),
        "active_routes": len(routes),
        "processed_observations": processed,
        "accepted_fresh_observations": accepted,
        "pier_calls": len(calls),
        "operational_pier_calls": len(operational_calls),
        "call_types": dict(Counter(call["call_type"] for call in calls)),
        "operational_call_types": dict(Counter(call["call_type"] for call in operational_calls)),
        "vessel_months_with_calls": len(calls_by_vessel_month),
        "route_candidate_rows": len(candidate_rows),
        "unknown_stop_cells": len(unknown_rows),
        "parameters": {
            "pier_radius_m": args.pier_radius_m,
            "certain_distance_m": args.certain_distance_m,
            "close_proximity_max_speed_knots": args.close_proximity_max_speed_knots,
            "stop_speed_knots": args.stop_speed_knots,
            "minimum_call_seconds": args.minimum_call_seconds,
            "maximum_call_hours": args.maximum_call_hours,
            "maximum_stale_seconds": args.maximum_stale_seconds,
            "turnaround_degrees": args.turnaround_degrees,
            "minimum_direction_leg_m": args.minimum_direction_leg_m,
            "minimum_active_days": args.minimum_active_days if args.vessel_summary else None,
            "retained_vessels": len(retained_mmsis) if retained_mmsis is not None else None,
        },
    }
    (args.output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
