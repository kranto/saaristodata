#!/usr/bin/env python3
"""Normalize KMTK BETA polygon collections for the land-cover pilot."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from pyproj import Transformer
from shapely import make_valid, transform
from shapely.geometry import box, mapping, shape

from common import REPO_ROOT, area_config, load_manifest, source_config


DEFAULT_SOURCE = "mml-kmtk-beta"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--area", default="pilot-archipelago-sea")
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    manifest = load_manifest()
    area = area_config(manifest, args.area)
    source = source_config(manifest, args.source)
    processing = manifest["processing"]
    input_path = args.input or REPO_ROOT / "raw" / "landcover" / args.source / f"{args.area}.geojson"
    output_path = args.output or REPO_ROOT / "work" / "landcover" / f"{args.area}-kmtk.geojson"
    raw = json.loads(input_path.read_text(encoding="utf-8"))

    to_projected = Transformer.from_crs(4326, 3067, always_xy=True).transform
    to_wgs84 = Transformer.from_crs(3067, 4326, always_xy=True).transform
    west, south, east, north = area["bbox_epsg3067"]
    clip = box(west, south, east, north)
    minimum_areas = processing["kmtk_minimum_area_square_metres"]
    tolerance = float(processing["simplify_tolerance_metres"])
    counts = Counter()
    areas = Counter()
    collection_counts = Counter()
    features = []

    for feature in raw.get("features", []):
        properties = feature.get("properties", {})
        class_name = properties["class"]
        geometry = transform(shape(feature["geometry"]), to_projected, interleaved=False)
        geometry = make_valid(geometry).intersection(clip)
        if geometry.is_empty or geometry.area < float(minimum_areas[class_name]):
            continue
        geometry = geometry.simplify(tolerance, preserve_topology=True)
        if geometry.is_empty:
            continue
        counts[class_name] += 1
        areas[class_name] += geometry.area
        collection_counts[properties["source_collection"]] += 1
        features.append({
            "type": "Feature",
            "properties": {
                "class": class_name,
                "source": args.source,
                "source_collection": properties["source_collection"],
                "source_date": "2026-beta",
            },
            "geometry": mapping(transform(geometry, to_wgs84, interleaved=False)),
        })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({
        "type": "FeatureCollection",
        "name": processing["layer_name"],
        "features": features,
    }, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "area": args.area,
        "source": args.source,
        "input": str(input_path.relative_to(REPO_ROOT)),
        "output": str(output_path.relative_to(REPO_ROOT)),
        "output_bytes": output_path.stat().st_size,
        "feature_counts": dict(sorted(counts.items())),
        "source_collection_counts": dict(sorted(collection_counts.items())),
        "area_square_metres": {key: round(value, 1) for key, value in sorted(areas.items())},
    }
    receipt_path = input_path.with_suffix(".receipt.json")
    if receipt_path.exists():
        report["download"] = json.loads(receipt_path.read_text(encoding="utf-8"))
    report_path = REPO_ROOT / "reports" / f"landcover-{args.area}-kmtk.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
