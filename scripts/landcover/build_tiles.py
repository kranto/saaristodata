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


def run_tippecanoe(
    command: str,
    output: Path,
    input_path: Path,
    layer_name: str,
    minimum_zoom: int,
    maximum_zoom: int,
    attribution: str,
    name: str,
    extra_args: list[str] | None = None,
) -> None:
    subprocess.run([
        command,
        "--output", str(output),
        "--layer", layer_name,
        "--minimum-zoom", str(minimum_zoom),
        "--maximum-zoom", str(maximum_zoom),
        *(extra_args or []),
        "--attribution", attribution,
        "--name", name,
        str(input_path),
    ], check=True)


def merge_overview_tiles(detail_mbtiles: Path, overview_mbtiles: Path, minimum_zoom: int) -> None:
    with sqlite3.connect(detail_mbtiles) as database:
        database.execute("ATTACH DATABASE ? AS overview", (str(overview_mbtiles),))
        database.execute("INSERT OR REPLACE INTO images SELECT * FROM overview.images")
        database.execute("INSERT OR REPLACE INTO map SELECT * FROM overview.map")
        database.commit()
        database.execute("DETACH DATABASE overview")

        database.execute("DELETE FROM metadata WHERE name = 'minzoom'")
        database.execute(
            "INSERT INTO metadata (name, value) VALUES ('minzoom', ?)",
            (str(minimum_zoom),),
        )
        metadata_row = database.execute(
            "SELECT value FROM metadata WHERE name = 'json'"
        ).fetchone()
        if metadata_row:
            metadata = json.loads(metadata_row[0])
            for layer in metadata.get("vector_layers", []):
                layer["minzoom"] = minimum_zoom
            database.execute(
                "UPDATE metadata SET value = ? WHERE name = 'json'",
                (json.dumps(metadata, separators=(",", ":")),),
            )
        database.commit()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--area", default="pilot-kustavi-inio-velkua")
    parser.add_argument("--source")
    parser.add_argument("--variant", help="Filename suffix, for example kmtk")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    manifest = load_manifest()
    area_config(manifest, args.area)
    processing = manifest["processing"]
    source_name = args.source or processing["source_name"]
    source = manifest["sources"][source_name]
    suffix = f"-{args.variant}" if args.variant else ""
    input_path = args.input or REPO_ROOT / "work" / "landcover" / f"{args.area}{suffix}.geojson"
    output_path = args.output or REPO_ROOT / "tiles" / f"landcover-{args.area}{suffix}.pmtiles"
    mbtiles_path = output_path.with_suffix(".mbtiles")
    overview_mbtiles_path = mbtiles_path.with_name(f"{mbtiles_path.stem}-overview.mbtiles")

    if not input_path.exists():
        raise FileNotFoundError(f"{input_path} does not exist; run build_geojson.py first")
    existing = [path for path in (output_path, mbtiles_path, overview_mbtiles_path) if path.exists()]
    if existing and not args.force:
        raise FileExistsError(f"Output already exists: {existing}; use --force to replace it")
    for path in existing:
        path.unlink()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    tippecanoe = require_command("tippecanoe")
    pmtiles = require_command("pmtiles")
    archive_name = f"Complementary land cover ({source_name}): {args.area}"
    detail_minzoom = processing.get("tile_detail_minzoom", processing["tile_minzoom"])
    run_tippecanoe(
        tippecanoe,
        mbtiles_path,
        input_path,
        processing["layer_name"],
        detail_minzoom,
        processing["tile_maxzoom"],
        source["attribution"],
        archive_name,
        ["--coalesce-smallest-as-needed"],
    )
    if processing["tile_minzoom"] < detail_minzoom:
        run_tippecanoe(
            tippecanoe,
            overview_mbtiles_path,
            input_path,
            processing["layer_name"],
            processing["tile_minzoom"],
            detail_minzoom - 1,
            source["attribution"],
            f"{archive_name} overview",
            [
                "--simplification", str(processing["tile_overview_simplification"]),
                "--include", "class",
                "--no-feature-limit",
                "--no-tile-size-limit",
            ],
        )
        merge_overview_tiles(mbtiles_path, overview_mbtiles_path, processing["tile_minzoom"])
        overview_mbtiles_path.unlink()
    subprocess.run([pmtiles, "convert", str(mbtiles_path), str(output_path)], check=True)

    report_path = REPO_ROOT / "reports" / f"landcover-{args.area}{suffix}.json"
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
        "source": source_name,
        "archive": output_path.name,
        "bytes": output_path.stat().st_size,
        "sha256": sha256(output_path),
        "bounds_wgs84": manifest["areas"][args.area]["bbox_wgs84"],
        "minimum_zoom": processing["tile_minzoom"],
        "maximum_zoom": processing["tile_maxzoom"],
        "layer_name": processing["layer_name"],
        "classes": report.get("included_classes") or sorted(set(
            source.get("class_mapping", source.get("collection_mapping", {})).values()
        )),
        "attribution": source["attribution"],
    }
    active_manifest_path = REPO_ROOT / "tiles" / f"landcover{suffix}.json"
    active_manifest_path.write_text(
        json.dumps(active_manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["tiles"], indent=2))


if __name__ == "__main__":
    main()
