#!/usr/bin/env python3
"""Prepare a compact, analysis-friendly database from a lauttalive SQLite file.

The source table contains one row per vessel returned by a polling round. SQLite
rowid preserves collection order, while ``timestamp`` is the vessel's external
AIS timestamp. This program infers polling-round boundaries, estimates each
round's collection time, clips observations to a polygon, and collapses
consecutive copies of an unchanged AIS observation.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import shutil
import sqlite3
import statistics
import sys
import tempfile
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable


SCHEMA = """
CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE collection_rounds (
    round_id INTEGER PRIMARY KEY,
    first_source_rowid INTEGER NOT NULL,
    last_source_rowid INTEGER NOT NULL,
    estimated_collection_ms INTEGER NOT NULL,
    source_rows INTEGER NOT NULL,
    inside_rows INTEGER NOT NULL,
    stale_rows INTEGER NOT NULL,
    future_rows INTEGER NOT NULL
);
CREATE TABLE observations (
    observation_id INTEGER PRIMARY KEY,
    mmsi INTEGER NOT NULL,
    ais_timestamp INTEGER NOT NULL,
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    sog REAL NOT NULL,
    heading INTEGER NOT NULL,
    first_source_rowid INTEGER NOT NULL,
    last_source_rowid INTEGER NOT NULL,
    first_round_id INTEGER NOT NULL,
    last_round_id INTEGER NOT NULL,
    first_collection_ms INTEGER NOT NULL,
    last_collection_ms INTEGER NOT NULL,
    age_at_first_ms INTEGER NOT NULL,
    age_at_last_ms INTEGER NOT NULL,
    poll_count INTEGER NOT NULL
);
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="Source .db or .db.gz file")
    parser.add_argument("output", type=Path, help="Output SQLite database")
    parser.add_argument(
        "--area",
        type=Path,
        default=Path(__file__).with_name("analysis-area.geojson"),
        help="GeoJSON Polygon used to clip observations",
    )
    parser.add_argument(
        "--stale-seconds",
        type=int,
        default=300,
        help="Mark an observation stale after this many seconds (default: 300)",
    )
    parser.add_argument(
        "--future-tolerance-seconds",
        type=int,
        default=60,
        help="Allowed AIS timestamp lead over estimated collection time",
    )
    parser.add_argument("--summary-csv", type=Path)
    parser.add_argument("--summary-json", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def load_polygon(path: Path) -> list[tuple[float, float]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    geometry = data.get("geometry", data)
    if geometry.get("type") != "Polygon" or not geometry.get("coordinates"):
        raise ValueError(f"{path} does not contain a GeoJSON Polygon")
    ring = [(float(lng), float(lat)) for lng, lat in geometry["coordinates"][0]]
    if ring[0] == ring[-1]:
        ring.pop()
    if len(ring) < 3:
        raise ValueError("Analysis polygon needs at least three distinct points")
    return ring


def point_in_polygon(lng: float, lat: float, polygon: list[tuple[float, float]]) -> bool:
    inside = False
    previous = polygon[-1]
    for current in polygon:
        x1, y1 = previous
        x2, y2 = current
        if (y1 > lat) != (y2 > lat):
            crossing_x = (x2 - x1) * (lat - y1) / (y2 - y1) + x1
            if lng < crossing_x:
                inside = not inside
        previous = current
    return inside


def estimate_collection_time(rows: list[tuple]) -> int:
    """Use the median of the newest decile to resist isolated future timestamps."""
    timestamps = sorted(row[2] for row in rows if row[2] > 0)
    if not timestamps:
        return 0
    newest_decile = timestamps[max(0, int(len(timestamps) * 0.9)) :]
    return int(statistics.median(newest_decile))


def source_database(path: Path):
    """Yield a plain SQLite path, temporarily decompressing gzip input."""
    if path.suffix != ".gz":
        yield path
        return
    temporary = tempfile.NamedTemporaryFile(prefix="ais-", suffix=".db", delete=False)
    temporary_path = Path(temporary.name)
    temporary.close()
    try:
        with gzip.open(path, "rb") as compressed, temporary_path.open("wb") as output:
            shutil.copyfileobj(compressed, output, length=16 * 1024 * 1024)
        yield temporary_path
    finally:
        temporary_path.unlink(missing_ok=True)


class SourceDatabase:
    def __init__(self, path: Path):
        self.path = path
        self._context = None

    def __enter__(self) -> Path:
        self._context = source_database(self.path)
        return next(self._context)

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        try:
            next(self._context)
        except StopIteration:
            pass


def observation_values(record: dict) -> tuple:
    return (
        record["mmsi"],
        record["timestamp"],
        record["lat"],
        record["lng"],
        record["sog"],
        record["heading"],
        record["first_rowid"],
        record["last_rowid"],
        record["first_round"],
        record["last_round"],
        record["first_collection"],
        record["last_collection"],
        record["first_collection"] - record["timestamp"],
        record["last_collection"] - record["timestamp"],
        record["poll_count"],
    )


def write_summaries(
    output: sqlite3.Connection,
    csv_path: Path | None,
    json_path: Path | None,
    general: dict,
) -> None:
    query = """
        SELECT mmsi,
               COUNT(*) AS observations,
               SUM(poll_count) AS poll_rows,
               COUNT(DISTINCT date(ais_timestamp / 1000, 'unixepoch')) AS active_days,
               datetime(MIN(ais_timestamp) / 1000, 'unixepoch') AS first_utc,
               datetime(MAX(ais_timestamp) / 1000, 'unixepoch') AS last_utc,
               ROUND(100.0 * SUM(age_at_first_ms > ?) / COUNT(*), 2) AS stale_first_pct,
               ROUND(100.0 * SUM(age_at_last_ms > ?) / COUNT(*), 2) AS stale_last_pct,
               MIN(lat) AS min_lat, MAX(lat) AS max_lat,
               MIN(lng) AS min_lng, MAX(lng) AS max_lng
        FROM observations
        GROUP BY mmsi
        ORDER BY poll_rows DESC
    """
    stale_ms = int(general["stale_seconds"]) * 1000
    cursor = output.execute(query, (stale_ms, stale_ms))
    columns = [description[0] for description in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor]
    if csv_path:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with csv_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
    if json_path:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"summary": general, "vessels": rows}
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare(args: argparse.Namespace, source_path: Path) -> dict:
    if args.output.exists():
        if not args.overwrite:
            raise FileExistsError(f"Output exists: {args.output}; use --overwrite")
        args.output.unlink()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    polygon = load_polygon(args.area)
    min_lng = min(point[0] for point in polygon)
    max_lng = max(point[0] for point in polygon)
    min_lat = min(point[1] for point in polygon)
    max_lat = max(point[1] for point in polygon)

    source = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
    output = sqlite3.connect(args.output)
    output.executescript(SCHEMA)
    output.execute("PRAGMA journal_mode=WAL")
    output.execute("PRAGMA synchronous=NORMAL")

    stale_ms = args.stale_seconds * 1000
    future_tolerance_ms = args.future_tolerance_seconds * 1000
    started = time.monotonic()
    source_rows = 0
    inside_rows = 0
    round_count = 0
    observation_count = 0
    pending_by_mmsi: dict[int, dict] = {}
    insert_buffer: list[tuple] = []

    def emit(record: dict) -> None:
        nonlocal observation_count
        insert_buffer.append(observation_values(record))
        observation_count += 1
        if len(insert_buffer) >= 10_000:
            output.executemany(
                """INSERT INTO observations (
                    mmsi, ais_timestamp, lat, lng, sog, heading,
                    first_source_rowid, last_source_rowid, first_round_id,
                    last_round_id, first_collection_ms, last_collection_ms,
                    age_at_first_ms, age_at_last_ms, poll_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                insert_buffer,
            )
            insert_buffer.clear()

    def flush_round(rows: list[tuple]) -> None:
        nonlocal inside_rows, round_count
        if not rows:
            return
        round_count += 1
        collection_ms = estimate_collection_time(rows)
        round_inside = 0
        stale_rows = 0
        future_rows = 0
        for rowid, mmsi, timestamp, lat, lng, sog, heading in rows:
            in_bbox = min_lng <= lng <= max_lng and min_lat <= lat <= max_lat
            if not in_bbox or not point_in_polygon(lng, lat, polygon):
                previous = pending_by_mmsi.pop(mmsi, None)
                if previous:
                    emit(previous)
                continue
            round_inside += 1
            age_ms = collection_ms - timestamp
            stale_rows += age_ms > stale_ms
            future_rows += age_ms < -future_tolerance_ms
            key = (timestamp, lat, lng, sog, heading)
            previous = pending_by_mmsi.get(mmsi)
            if previous and previous["key"] == key:
                previous["last_rowid"] = rowid
                previous["last_round"] = round_count
                previous["last_collection"] = collection_ms
                previous["poll_count"] += 1
            else:
                if previous:
                    emit(previous)
                pending_by_mmsi[mmsi] = {
                    "key": key,
                    "mmsi": mmsi,
                    "timestamp": timestamp,
                    "lat": lat,
                    "lng": lng,
                    "sog": sog,
                    "heading": heading,
                    "first_rowid": rowid,
                    "last_rowid": rowid,
                    "first_round": round_count,
                    "last_round": round_count,
                    "first_collection": collection_ms,
                    "last_collection": collection_ms,
                    "poll_count": 1,
                }
        inside_rows += round_inside
        output.execute(
            "INSERT INTO collection_rounds VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                round_count,
                rows[0][0],
                rows[-1][0],
                collection_ms,
                len(rows),
                round_inside,
                stale_rows,
                future_rows,
            ),
        )
        if round_count % 10_000 == 0:
            output.commit()
            elapsed = time.monotonic() - started
            print(
                f"rounds={round_count:,} source_rows={source_rows:,} "
                f"inside_rows={inside_rows:,} observations={observation_count:,} "
                f"elapsed={elapsed:.0f}s",
                file=sys.stderr,
                flush=True,
            )

    current_rows: list[tuple] = []
    current_mmsis: set[int] = set()
    cursor = source.execute(
        "SELECT rowid, mmsi, timestamp, lat, lng, sog, heading FROM snapshots ORDER BY rowid"
    )
    for row in cursor:
        source_rows += 1
        mmsi = row[1]
        if mmsi in current_mmsis:
            flush_round(current_rows)
            current_rows = []
            current_mmsis = set()
        current_rows.append(row)
        current_mmsis.add(mmsi)
    flush_round(current_rows)
    for record in pending_by_mmsi.values():
        emit(record)
    if insert_buffer:
        output.executemany(
            """INSERT INTO observations (
                mmsi, ais_timestamp, lat, lng, sog, heading,
                first_source_rowid, last_source_rowid, first_round_id,
                last_round_id, first_collection_ms, last_collection_ms,
                age_at_first_ms, age_at_last_ms, poll_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            insert_buffer,
        )
    output.commit()
    output.executescript(
        """
        CREATE INDEX observations_mmsi_time ON observations (mmsi, ais_timestamp);
        CREATE INDEX observations_time ON observations (ais_timestamp);
        CREATE INDEX observations_position ON observations (lat, lng);
        """
    )

    general = {
        "source": str(args.source.resolve()),
        "area": str(args.area.resolve()),
        "created_utc": datetime.now(UTC).isoformat(),
        "source_rows": source_rows,
        "inside_rows": inside_rows,
        "inside_percent": round(100 * inside_rows / source_rows, 2) if source_rows else 0,
        "collection_rounds": round_count,
        "observations": observation_count,
        "stale_seconds": args.stale_seconds,
        "future_tolerance_seconds": args.future_tolerance_seconds,
        "elapsed_seconds": round(time.monotonic() - started, 1),
    }
    output.executemany(
        "INSERT INTO metadata VALUES (?, ?)",
        [(key, json.dumps(value, ensure_ascii=False)) for key, value in general.items()],
    )
    output.commit()
    write_summaries(output, args.summary_csv, args.summary_json, general)
    output.close()
    source.close()
    return general


def main() -> None:
    args = parse_args()
    with SourceDatabase(args.source) as source_path:
        result = prepare(args, source_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
