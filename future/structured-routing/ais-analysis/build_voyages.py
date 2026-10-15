#!/usr/bin/env python3
"""Build pier-to-pier voyages and their AIS tracks from prepared observations."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path


EARTH_RADIUS_M = 6_371_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path, help="Database created by prepare_ais.py")
    parser.add_argument("calls", type=Path, help="pier-calls.csv")
    parser.add_argument("weekly_candidates", type=Path, help="weekly-route-candidates.csv")
    parser.add_argument("data", type=Path, help="data.json containing route definitions")
    parser.add_argument("saaristo", type=Path, help="saaristo.json containing pier coordinates")
    parser.add_argument("output", type=Path, help="Output SQLite database")
    parser.add_argument("--summary-csv", type=Path)
    parser.add_argument("--summary-json", type=Path)
    parser.add_argument("--duplicate-call-minutes", type=int, default=30)
    parser.add_argument("--maximum-voyage-hours", type=float, default=12)
    parser.add_argument("--maximum-stale-seconds", type=int, default=300)
    parser.add_argument("--good-gap-seconds", type=int, default=300)
    parser.add_argument("--usable-gap-seconds", type=int, default=1200)
    parser.add_argument("--good-endpoint-seconds", type=int, default=180)
    parser.add_argument("--usable-endpoint-seconds", type=int, default=600)
    parser.add_argument("--minimum-points", type=int, default=3)
    parser.add_argument("--dock-radius-m", type=float, default=50)
    parser.add_argument(
        "--pier-calibration",
        type=Path,
        help="Optional pier-calibration.json from calibrate_pier_timing.py",
    )
    parser.add_argument("--slow-knots", type=float, default=1.5)
    parser.add_argument(
        "--minimum-route-piers",
        type=int,
        default=3,
        help="Ignore two-pier shuttle and cable-ferry routes by default",
    )
    return parser.parse_args()


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as file:
        return list(csv.DictReader(file))


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def epoch_ms(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def week_start(value: datetime) -> date:
    return value.date() - timedelta(days=value.weekday())


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    lat1r = math.radians(lat1)
    lat2r = math.radians(lat2)
    dlat = lat2r - lat1r
    dlng = math.radians(lng2 - lng1)
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1r) * math.cos(lat2r) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(value))


def confidence(score: float, margin: float) -> str:
    if score >= 0.65 and margin >= 0.08:
        return "high"
    if score >= 0.50 and margin >= 0.03:
        return "probable"
    return "ambiguous"


def load_routes(path: Path, minimum_piers: int) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    routes = {}
    for route_id, route in data.get("routes", {}).items():
        if route.get("obsolete"):
            continue
        pier_ids = {
            pier.get("id") or pier.get("name")
            for pier in route.get("piers", [])
            if pier.get("id") or pier.get("name")
        }
        if len(pier_ids) < minimum_piers:
            continue
        routes[route_id] = {
            "name": route.get("name_fi") or route.get("name") or route_id,
            "piers": pier_ids,
        }
    return routes


def load_piers(path: Path) -> dict[str, tuple[float, float]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    piers = {}
    for feature in data.get("features", []):
        properties = feature.get("properties", {})
        geometry = feature.get("geometry", {})
        if properties.get("stype") != "pier" or geometry.get("type") != "Point":
            continue
        pier = properties.get("ref")
        coordinates = geometry.get("coordinates", [])
        if pier and len(coordinates) >= 2:
            piers[pier] = (float(coordinates[1]), float(coordinates[0]))
    return piers


def load_pier_calibration(path: Path | None) -> dict[str, dict]:
    if not path:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_assignments(path: Path, retained_routes: set[str]) -> dict[tuple[int, date], dict]:
    assignments = {}
    for row in read_csv(path):
        if row["rank"] != "1":
            continue
        if row["route_id"] not in retained_routes:
            continue
        score = float(row["score"])
        margin = float(row["margin"] or 0)
        row_confidence = confidence(score, margin)
        if row_confidence == "ambiguous":
            continue
        assignments[(int(row["mmsi"]), date.fromisoformat(row["week_start"]))] = {
            "route_id": row["route_id"],
            "route_name": row["route_name"],
            "confidence": row_confidence,
            "score": score,
            "margin": margin,
        }
    return assignments


def accepted_and_collapsed_calls(path: Path, duplicate_minutes: int, retained_mmsis: set[int]) -> list[dict]:
    calls = []
    for row in read_csv(path):
        mmsi = int(row["mmsi"])
        if row.get("operational") != "1" or mmsi not in retained_mmsis:
            continue
        calls.append({
            **row,
            "mmsi": mmsi,
            "arrival": parse_utc(row["arrival_utc"]),
            "departure": parse_utc(row["departure_utc"]),
            "merged_calls": 1,
        })
    calls.sort(key=lambda row: (row["mmsi"], row["arrival"]))
    collapsed = []
    maximum_gap = duplicate_minutes * 60
    for call in calls:
        if collapsed:
            previous = collapsed[-1]
            gap = (call["arrival"] - previous["departure"]).total_seconds()
            if call["mmsi"] == previous["mmsi"] and call["pier"] == previous["pier"] and 0 <= gap <= maximum_gap:
                previous["departure"] = max(previous["departure"], call["departure"])
                previous["departure_utc"] = previous["departure"].isoformat().replace("+00:00", "Z")
                previous["merged_calls"] += 1
                continue
        collapsed.append(call)
    for call_id, call in enumerate(collapsed, start=1):
        call["call_id"] = call_id
        call["arrival_ms"] = epoch_ms(call["arrival"])
        call["departure_ms"] = epoch_ms(call["departure"])
    return collapsed


def interpolate_crossing_ms(
    earlier_ms: int, earlier_distance: float, later_ms: int, later_distance: float, radius: float
) -> int:
    difference = later_distance - earlier_distance
    if not difference:
        return later_ms
    fraction = (radius - earlier_distance) / difference
    fraction = min(1.0, max(0.0, fraction))
    return round(earlier_ms + fraction * (later_ms - earlier_ms))


def estimate_call_endpoints(
    source: sqlite3.Connection,
    calls: list[dict],
    piers: dict[str, tuple[float, float]],
    retained_mmsis: set[int],
    dock_radius_m: float,
    pier_calibration: dict[str, dict],
    slow_knots: float,
    maximum_stale_seconds: int,
) -> Counter:
    """Estimate pier arrival/departure inside the broader 250 m call windows."""
    calls_by_vessel = defaultdict(list)
    for call in calls:
        calls_by_vessel[call["mmsi"]].append(call)
        call["endpoint_state"] = None
    placeholders = ",".join("?" for _ in retained_mmsis)
    query = f"""
        SELECT mmsi, ais_timestamp, lat, lng, sog, age_at_first_ms
        FROM observations
        WHERE mmsi IN ({placeholders})
        ORDER BY mmsi, ais_timestamp, observation_id
    """
    indexes = defaultdict(int)
    counts = Counter()
    for mmsi, timestamp, lat, lng, sog, age_ms in source.execute(
        query, tuple(sorted(retained_mmsis))
    ):
        vessel_calls = calls_by_vessel.get(mmsi)
        if not vessel_calls:
            continue
        index = indexes[mmsi]
        while index < len(vessel_calls) and timestamp > vessel_calls[index]["departure_ms"]:
            index += 1
        indexes[mmsi] = index
        if index >= len(vessel_calls):
            continue
        call = vessel_calls[index]
        if timestamp < call["arrival_ms"]:
            continue
        if not (-60_000 <= age_ms <= maximum_stale_seconds * 1000) or not (0 <= sog < 102.3):
            continue
        calibration = pier_calibration.get(call["pier"])
        calibrated_centers = calibration.get("centers", []) if calibration else []
        pier_cores = (
            [
                (float(center["lat"]), float(center["lng"]), float(center.get("radius_m", dock_radius_m)))
                for center in calibrated_centers
            ]
            if calibrated_centers
            else [
                (
                    float(calibration["lat"]),
                    float(calibration["lng"]),
                    float(calibration.get("radius_m", dock_radius_m)),
                )
            ]
            if calibration
            else [(*piers[call["pier"]], dock_radius_m)] if call["pier"] in piers else []
        )
        if not pier_cores:
            counts["missing_pier_coordinate"] += 1
            continue
        distances = [haversine_m(lat, lng, core[0], core[1]) for core in pier_cores]
        closest_core = min(range(len(pier_cores)), key=distances.__getitem__)
        distance = distances[closest_core]
        pier_radius_m = pier_cores[closest_core][2]
        state = call["endpoint_state"]
        if state is None:
            method = "sampled_core" if distance <= pier_radius_m else None
            slow_core = distance <= pier_radius_m and sog <= slow_knots
            state = {
                "closest_ms": timestamp,
                "closest_distance_m": distance,
                "arrival_ms": timestamp if method else None,
                "arrival_method": method,
                "arrival_uncertainty_seconds": None,
                "departure_ms": timestamp if method else None,
                "departure_method": method,
                "departure_uncertainty_seconds": None,
                "first_slow_ms": timestamp if slow_core else None,
                "last_slow_ms": timestamp if slow_core else None,
                "previous_ms": timestamp,
                "previous_distance_m": distance,
                "radius_m": pier_radius_m,
            }
            call["endpoint_state"] = state
            continue
        if distance < state["closest_distance_m"]:
            state["closest_ms"] = timestamp
            state["closest_distance_m"] = distance
        previous_ms = state["previous_ms"]
        previous_distance = state["previous_distance_m"]
        radius_m = state["radius_m"]
        gap_seconds = max(0, round((timestamp - previous_ms) / 1000))
        if distance <= radius_m and sog <= slow_knots:
            if state["first_slow_ms"] is None:
                state["first_slow_ms"] = timestamp
            state["last_slow_ms"] = timestamp
        if previous_distance > radius_m >= distance and state["arrival_ms"] is None:
            state["arrival_ms"] = interpolate_crossing_ms(
                previous_ms, previous_distance, timestamp, distance, radius_m
            )
            state["arrival_method"] = "interpolated_core"
            state["arrival_uncertainty_seconds"] = gap_seconds
        elif distance <= radius_m and state["arrival_ms"] is None:
            state["arrival_ms"] = timestamp
            state["arrival_method"] = "sampled_core"
        if previous_distance <= radius_m < distance:
            state["departure_ms"] = interpolate_crossing_ms(
                previous_ms, previous_distance, timestamp, distance, radius_m
            )
            state["departure_method"] = "interpolated_core"
            state["departure_uncertainty_seconds"] = gap_seconds
        elif distance <= radius_m:
            state["departure_ms"] = timestamp
            state["departure_method"] = "sampled_core"
        state["previous_ms"] = timestamp
        state["previous_distance_m"] = distance

    for call in calls:
        state = call.pop("endpoint_state", None)
        if not state:
            counts["no_fresh_observation"] += 1
            continue
        for endpoint in ("arrival", "departure"):
            slow_ms = state["first_slow_ms"] if endpoint == "arrival" else state["last_slow_ms"]
            endpoint_ms = slow_ms if slow_ms is not None else state[f"{endpoint}_ms"]
            method = "slow_core" if slow_ms is not None else state[f"{endpoint}_method"]
            uncertainty = 60 if slow_ms is not None else state[f"{endpoint}_uncertainty_seconds"]
            if endpoint_ms is None:
                endpoint_ms = state["closest_ms"]
                method = "closest_approach"
            call[f"dock_{endpoint}_ms"] = endpoint_ms
            call[f"dock_{endpoint}_method"] = method
            call[f"dock_{endpoint}_uncertainty_seconds"] = uncertainty
        call["closest_distance_m"] = round(state["closest_distance_m"], 1)
        counts[call["dock_arrival_method"]] += 1
    return counts


def build_intervals(calls: list[dict], assignments: dict, routes: dict, maximum_hours: float):
    calls_by_vessel = defaultdict(list)
    for call in calls:
        calls_by_vessel[call["mmsi"]].append(call)
    intervals = defaultdict(list)
    rejected = Counter()
    voyage_id = 0
    for mmsi, vessel_calls in calls_by_vessel.items():
        for origin, destination in zip(vessel_calls, vessel_calls[1:]):
            if origin["pier"] == destination["pier"]:
                rejected["same_pier"] += 1
                continue
            if "dock_departure_ms" not in origin or "dock_arrival_ms" not in destination:
                rejected["missing_dock_endpoint"] += 1
                continue
            departure_ms = origin["dock_departure_ms"]
            arrival_ms = destination["dock_arrival_ms"]
            departure = datetime.fromtimestamp(departure_ms / 1000, UTC)
            arrival = datetime.fromtimestamp(arrival_ms / 1000, UTC)
            duration_seconds = round((arrival_ms - departure_ms) / 1000)
            if duration_seconds <= 0:
                rejected["nonpositive_duration"] += 1
                continue
            if duration_seconds > maximum_hours * 3600:
                rejected["too_long"] += 1
                continue
            assignment = assignments.get((mmsi, week_start(departure)))
            if not assignment:
                rejected["no_reliable_weekly_route"] += 1
                continue
            route = routes.get(assignment["route_id"])
            if not route or origin["pier"] not in route["piers"] or destination["pier"] not in route["piers"]:
                rejected["pier_outside_assigned_route"] += 1
                continue
            voyage_id += 1
            intervals[mmsi].append({
                "voyage_id": voyage_id,
                "mmsi": mmsi,
                "route_id": assignment["route_id"],
                "route_name": assignment["route_name"],
                "assignment_confidence": assignment["confidence"],
                "assignment_score": assignment["score"],
                "origin_pier": origin["pier"],
                "destination_pier": destination["pier"],
                "origin_call_type": origin["call_type"],
                "destination_call_type": destination["call_type"],
                "origin_endpoint_method": origin["dock_departure_method"],
                "destination_endpoint_method": destination["dock_arrival_method"],
                "origin_endpoint_uncertainty_seconds": origin["dock_departure_uncertainty_seconds"],
                "destination_endpoint_uncertainty_seconds": destination["dock_arrival_uncertainty_seconds"],
                "origin_closest_distance_m": origin["closest_distance_m"],
                "destination_closest_distance_m": destination["closest_distance_m"],
                "departure_utc": departure.isoformat().replace("+00:00", "Z"),
                "arrival_utc": arrival.isoformat().replace("+00:00", "Z"),
                "departure_ms": departure_ms,
                "arrival_ms": arrival_ms,
                "duration_seconds": duration_seconds,
            })
    return intervals, rejected


def create_output(path: Path) -> sqlite3.Connection:
    if path.exists():
        path.unlink()
    connection = sqlite3.connect(path)
    connection.executescript("""
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        CREATE TABLE voyages (
            voyage_id INTEGER PRIMARY KEY,
            mmsi INTEGER NOT NULL,
            route_id TEXT NOT NULL,
            route_name TEXT NOT NULL,
            assignment_confidence TEXT NOT NULL,
            assignment_score REAL NOT NULL,
            origin_pier TEXT NOT NULL,
            destination_pier TEXT NOT NULL,
            origin_call_type TEXT NOT NULL,
            destination_call_type TEXT NOT NULL,
            origin_endpoint_method TEXT NOT NULL,
            destination_endpoint_method TEXT NOT NULL,
            origin_endpoint_uncertainty_seconds INTEGER,
            destination_endpoint_uncertainty_seconds INTEGER,
            origin_closest_distance_m REAL NOT NULL,
            destination_closest_distance_m REAL NOT NULL,
            departure_utc TEXT NOT NULL,
            arrival_utc TEXT NOT NULL,
            departure_ms INTEGER NOT NULL,
            arrival_ms INTEGER NOT NULL,
            duration_seconds INTEGER NOT NULL,
            raw_observations INTEGER NOT NULL DEFAULT 0,
            accepted_points INTEGER NOT NULL DEFAULT 0,
            rejected_stale_points INTEGER NOT NULL DEFAULT 0,
            rejected_speed_points INTEGER NOT NULL DEFAULT 0,
            first_point_offset_seconds INTEGER,
            last_point_offset_seconds INTEGER,
            maximum_ais_gap_seconds INTEGER,
            maximum_collection_gap_seconds INTEGER,
            track_distance_m INTEGER,
            average_speed_knots REAL,
            maximum_segment_speed_knots REAL,
            maximum_stationary_seconds INTEGER,
            quality TEXT NOT NULL DEFAULT 'unprocessed'
        );
        CREATE TABLE voyage_points (
            voyage_id INTEGER NOT NULL,
            sequence INTEGER NOT NULL,
            ais_timestamp INTEGER NOT NULL,
            collection_ms INTEGER NOT NULL,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            sog REAL NOT NULL,
            heading INTEGER NOT NULL,
            age_at_collection_ms INTEGER NOT NULL,
            poll_count INTEGER NOT NULL,
            PRIMARY KEY (voyage_id, sequence)
        ) WITHOUT ROWID;
    """)
    return connection


def main() -> None:
    args = parse_args()
    started = time.monotonic()
    routes = load_routes(args.data, args.minimum_route_piers)
    piers = load_piers(args.saaristo)
    pier_calibration = load_pier_calibration(args.pier_calibration)
    assignments = load_assignments(args.weekly_candidates, set(routes))
    retained_mmsis = {mmsi for mmsi, _week in assignments}
    calls = accepted_and_collapsed_calls(args.calls, args.duplicate_call_minutes, retained_mmsis)
    source = sqlite3.connect(f"file:{args.database}?mode=ro", uri=True)
    source.execute("PRAGMA query_only=ON")
    endpoint_counts = estimate_call_endpoints(
        source,
        calls,
        piers,
        retained_mmsis,
        args.dock_radius_m,
        pier_calibration,
        args.slow_knots,
        args.maximum_stale_seconds,
    )
    intervals, rejected = build_intervals(calls, assignments, routes, args.maximum_voyage_hours)
    interval_count = sum(len(rows) for rows in intervals.values())
    print(
        f"calls={len(calls):,} candidate_voyages={interval_count:,} vessels={len(intervals):,}",
        file=sys.stderr,
        flush=True,
    )

    output = create_output(args.output)
    voyage_rows = [row for vessel_rows in intervals.values() for row in vessel_rows]
    output.executemany(
        """
        INSERT INTO voyages (
            voyage_id, mmsi, route_id, route_name, assignment_confidence, assignment_score,
            origin_pier, destination_pier, origin_call_type, destination_call_type,
            origin_endpoint_method, destination_endpoint_method,
            origin_endpoint_uncertainty_seconds, destination_endpoint_uncertainty_seconds,
            origin_closest_distance_m, destination_closest_distance_m,
            departure_utc, arrival_utc, departure_ms, arrival_ms, duration_seconds
        ) VALUES (
            :voyage_id, :mmsi, :route_id, :route_name, :assignment_confidence, :assignment_score,
            :origin_pier, :destination_pier, :origin_call_type, :destination_call_type,
            :origin_endpoint_method, :destination_endpoint_method,
            :origin_endpoint_uncertainty_seconds, :destination_endpoint_uncertainty_seconds,
            :origin_closest_distance_m, :destination_closest_distance_m,
            :departure_utc, :arrival_utc, :departure_ms, :arrival_ms, :duration_seconds
        )
        """,
        voyage_rows,
    )
    output.commit()

    placeholders = ",".join("?" for _ in retained_mmsis)
    query = f"""
        SELECT mmsi, ais_timestamp, lat, lng, sog, heading,
               first_collection_ms, age_at_first_ms, poll_count
        FROM observations
        WHERE mmsi IN ({placeholders})
        ORDER BY mmsi, ais_timestamp, observation_id
    """
    interval_indexes = defaultdict(int)
    states = {}
    point_buffer = []
    processed = 0
    stored = 0

    def finalize(voyage: dict, state: dict | None) -> None:
        if not state:
            output.execute(
                "UPDATE voyages SET quality='gapped' WHERE voyage_id=?",
                (voyage["voyage_id"],),
            )
            return
        point_count = state["accepted_points"]
        first_offset = (
            max(0, (state["first_timestamp"] - voyage["departure_ms"]) // 1000)
            if point_count else None
        )
        last_offset = (
            max(0, (voyage["arrival_ms"] - state["last_timestamp"]) // 1000)
            if point_count else None
        )
        maximum_ais_gap = state["maximum_ais_gap_ms"] // 1000 if point_count >= 2 else None
        maximum_collection_gap = state["maximum_collection_gap_ms"] // 1000 if point_count >= 2 else None
        if (
            point_count >= args.minimum_points
            and first_offset <= args.good_endpoint_seconds
            and last_offset <= args.good_endpoint_seconds
            and maximum_collection_gap <= args.good_gap_seconds
        ):
            quality = "good"
        elif (
            point_count >= args.minimum_points
            and first_offset <= args.usable_endpoint_seconds
            and last_offset <= args.usable_endpoint_seconds
            and maximum_collection_gap <= args.usable_gap_seconds
        ):
            quality = "usable"
        else:
            quality = "gapped"
        average_speed = (
            state["track_distance_m"] / voyage["duration_seconds"] * 1.943844
            if voyage["duration_seconds"] else 0
        )
        output.execute(
            """
            UPDATE voyages SET
                raw_observations=?, accepted_points=?, rejected_stale_points=?, rejected_speed_points=?,
                first_point_offset_seconds=?, last_point_offset_seconds=?, maximum_ais_gap_seconds=?,
                maximum_collection_gap_seconds=?, track_distance_m=?, average_speed_knots=?, quality=?
                , maximum_segment_speed_knots=?, maximum_stationary_seconds=?
            WHERE voyage_id=?
            """,
            (
                state["raw_observations"], point_count, state["rejected_stale_points"],
                state["rejected_speed_points"], first_offset, last_offset, maximum_ais_gap,
                maximum_collection_gap, round(state["track_distance_m"]), round(average_speed, 2),
                quality, round(state["maximum_segment_speed_knots"], 2),
                state["maximum_stationary_ms"] // 1000, voyage["voyage_id"],
            ),
        )

    current_mmsi = None
    vessel_intervals = []
    current_voyage = None
    state = None
    for row in source.execute(query, tuple(sorted(retained_mmsis))):
        processed += 1
        mmsi, timestamp, lat, lng, sog, heading, collection_ms, age_ms, poll_count = row
        if mmsi != current_mmsi:
            if current_voyage:
                finalize(current_voyage, state)
            current_mmsi = mmsi
            vessel_intervals = intervals.get(mmsi, [])
            interval_indexes[mmsi] = 0
            current_voyage = vessel_intervals[0] if vessel_intervals else None
            state = None
        while current_voyage and timestamp > current_voyage["arrival_ms"]:
            finalize(current_voyage, state)
            interval_indexes[mmsi] += 1
            index = interval_indexes[mmsi]
            current_voyage = vessel_intervals[index] if index < len(vessel_intervals) else None
            state = None
        if not current_voyage or timestamp < current_voyage["departure_ms"]:
            continue
        if state is None:
            state = {
                "raw_observations": 0,
                "accepted_points": 0,
                "rejected_stale_points": 0,
                "rejected_speed_points": 0,
                "first_timestamp": None,
                "last_timestamp": None,
                "last_collection_ms": None,
                "last_lat": None,
                "last_lng": None,
                "maximum_ais_gap_ms": 0,
                "maximum_collection_gap_ms": 0,
                "track_distance_m": 0.0,
                "maximum_segment_speed_knots": 0.0,
                "slow_run_start_ms": None,
                "maximum_stationary_ms": 0,
            }
        state["raw_observations"] += 1
        if not (-60_000 <= age_ms <= args.maximum_stale_seconds * 1000):
            state["rejected_stale_points"] += 1
            continue
        if not (0 <= sog < 102.3):
            state["rejected_speed_points"] += 1
            continue
        sequence = state["accepted_points"]
        if sequence:
            state["maximum_ais_gap_ms"] = max(
                state["maximum_ais_gap_ms"], timestamp - state["last_timestamp"]
            )
            state["maximum_collection_gap_ms"] = max(
                state["maximum_collection_gap_ms"], collection_ms - state["last_collection_ms"]
            )
            segment_distance = haversine_m(
                state["last_lat"], state["last_lng"], lat, lng
            )
            state["track_distance_m"] += segment_distance
            collection_gap_seconds = (collection_ms - state["last_collection_ms"]) / 1000
            if collection_gap_seconds > 0:
                state["maximum_segment_speed_knots"] = max(
                    state["maximum_segment_speed_knots"],
                    segment_distance / collection_gap_seconds * 1.943844,
                )
        else:
            state["first_timestamp"] = timestamp
        state["accepted_points"] += 1
        if sog <= args.slow_knots:
            if state["slow_run_start_ms"] is None:
                state["slow_run_start_ms"] = timestamp
            state["maximum_stationary_ms"] = max(
                state["maximum_stationary_ms"], timestamp - state["slow_run_start_ms"]
            )
        else:
            state["slow_run_start_ms"] = None
        state["last_timestamp"] = timestamp
        state["last_collection_ms"] = collection_ms
        state["last_lat"] = lat
        state["last_lng"] = lng
        point_buffer.append((
            current_voyage["voyage_id"], sequence, timestamp, collection_ms,
            lat, lng, sog, heading, age_ms, poll_count,
        ))
        stored += 1
        if len(point_buffer) >= 50_000:
            output.executemany(
                "INSERT INTO voyage_points VALUES (?,?,?,?,?,?,?,?,?,?)", point_buffer
            )
            point_buffer.clear()
        if processed % 1_000_000 == 0:
            print(
                f"observations={processed:,} points={stored:,} elapsed={time.monotonic() - started:.0f}s",
                file=sys.stderr,
                flush=True,
            )
    if current_voyage:
        finalize(current_voyage, state)
    if point_buffer:
        output.executemany("INSERT INTO voyage_points VALUES (?,?,?,?,?,?,?,?,?,?)", point_buffer)
    output.execute("UPDATE voyages SET quality='gapped' WHERE quality='unprocessed'")
    output.executescript("""
        CREATE INDEX voyage_route_pair ON voyages (route_id, origin_pier, destination_pier, quality);
        CREATE INDEX voyage_mmsi_time ON voyages (mmsi, departure_ms);
        CREATE INDEX voyage_points_time ON voyage_points (ais_timestamp);
    """)
    output.commit()

    summary_rows = []
    fields = [row[1] for row in output.execute("PRAGMA table_info(voyages)")]
    for values in output.execute("SELECT * FROM voyages ORDER BY voyage_id"):
        summary_rows.append(dict(zip(fields, values)))
    if args.summary_csv:
        args.summary_csv.parent.mkdir(parents=True, exist_ok=True)
        with args.summary_csv.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(summary_rows)

    quality_counts = dict(output.execute(
        "SELECT quality, COUNT(*) FROM voyages GROUP BY quality ORDER BY quality"
    ).fetchall())
    route_counts = {
        route_id: count
        for route_id, count in output.execute(
            "SELECT route_id, COUNT(*) FROM voyages WHERE quality != 'gapped' GROUP BY route_id ORDER BY COUNT(*) DESC"
        )
    }
    summary = {
        "source_database": str(args.database.resolve()),
        "collapsed_operational_calls": len(calls),
        "candidate_voyages": interval_count,
        "voyage_points": stored,
        "vessels": len(intervals),
        "quality": quality_counts,
        "usable_voyages_by_route": route_counts,
        "rejected_transitions": dict(rejected),
        "call_endpoint_methods": dict(endpoint_counts),
        "parameters": {
            "duplicate_call_minutes": args.duplicate_call_minutes,
            "maximum_voyage_hours": args.maximum_voyage_hours,
            "maximum_stale_seconds": args.maximum_stale_seconds,
            "good_gap_seconds": args.good_gap_seconds,
            "usable_gap_seconds": args.usable_gap_seconds,
            "good_endpoint_seconds": args.good_endpoint_seconds,
            "usable_endpoint_seconds": args.usable_endpoint_seconds,
            "minimum_points": args.minimum_points,
            "dock_radius_m": args.dock_radius_m,
            "pier_calibration": str(args.pier_calibration) if args.pier_calibration else None,
            "slow_knots": args.slow_knots,
            "minimum_route_piers": args.minimum_route_piers,
        },
    }
    if args.summary_json:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
