#!/usr/bin/env python3
"""Build a PMTiles archive from normalized complementary land-cover GeoJSON."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from common import REPO_ROOT, area_config, load_manifest


def require_command(name: str) -> str:
    command = shutil.which(name)
    if command is None:
        raise RuntimeError(f"Required command {name!r} was not found in PATH")
    return command


def tile_statistics(mbtiles: Path) -> dict[str, dict[str, float | int]]:
    with sqlite3.connect(mbtiles) as database:
        rows = database.execute(
            """
            SELECT zoom_level, COUNT(*), MIN(LENGTH(tile_data)),
                   MAX(LENGTH(tile_data)), AVG(LENGTH(tile_data))
            FROM tiles
            GROUP BY zoom_level
            ORDER BY zoom_level
            """
        ).fetchall()
    return {
        str(zoom): {
            "tiles": count,
            "minimum_bytes": minimum,
            "maximum_bytes": maximum,
            "average_bytes": round(average, 1),
        }
        for zoom, count, minimum, maximum, average in rows
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--area", default="pilot-kustavi-inio-velkua")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    manifest = load_manifest()
    area_config(manifest, args.area)
    processing = manifest["processing"]
    source = manifest["sources"][processing["source_name"]]
    input_path = args.input or REPO_ROOT / "work" / "landcover" / f"{args.area}.geojson"
    output_path = args.output or REPO_ROOT / "tiles" / f"landcover-{args.area}.pmtiles"
    mbtiles_path = output_path.with_suffix(".mbtiles")

    if not input_path.exists():
        raise FileNotFoundError(f"{input_path} does not exist; run build_geojson.py first")
    existing = [path for path in (output_path, mbtiles_path) if path.exists()]
    if existing and not args.force:
        raise FileExistsError(f"Output already exists: {existing}; use --force to replace it")
    for path in existing:
        path.unlink()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    tippecanoe = require_command("tippecanoe")
    pmtiles = require_command("pmtiles")
    subprocess.run([
        tippecanoe,
        "--output", str(mbtiles_path),
        "--layer", processing["layer_name"],
        "--minimum-zoom", str(processing["tile_minzoom"]),
        "--maximum-zoom", str(processing["tile_maxzoom"]),
        "--coalesce-smallest-as-needed",
        "--attribution", source["attribution"],
        "--name", f"Complementary land cover: {args.area}",
        str(input_path),
    ], check=True)
    subprocess.run([pmtiles, "convert", str(mbtiles_path), str(output_path)], check=True)

    report_path = REPO_ROOT / "reports" / f"landcover-{args.area}.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    report["tiles"] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "output": str(output_path.relative_to(REPO_ROOT)),
        "output_bytes": output_path.stat().st_size,
        "layer_name": processing["layer_name"],
        "minimum_zoom": processing["tile_minzoom"],
        "maximum_zoom": processing["tile_maxzoom"],
        "zoom_statistics": tile_statistics(mbtiles_path),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    active_manifest = {
        "schema_version": 1,
        "generated_at": report["tiles"]["generated_at"],
        "area": args.area,
        "archive": output_path.name,
        "bytes": output_path.stat().st_size,
        "sha256": sha256(output_path),
        "bounds_wgs84": manifest["areas"][args.area]["bbox_wgs84"],
        "minimum_zoom": processing["tile_minzoom"],
        "maximum_zoom": processing["tile_maxzoom"],
        "layer_name": processing["layer_name"],
        "classes": sorted(set(source["class_mapping"].values())),
        "attribution": source["attribution"],
    }
    active_manifest_path = REPO_ROOT / "tiles" / "landcover.json"
    active_manifest_path.write_text(
        json.dumps(active_manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["tiles"], indent=2))


if __name__ == "__main__":
    main()
