#!/usr/bin/env python3
"""Reclassify and vectorize a categorical land-cover GeoTIFF."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.features import shapes
from shapely import transform
from shapely.geometry import mapping, shape

from common import REPO_ROOT, area_config, load_manifest, source_config


DEFAULT_SOURCE = "syke-maanpeite-2022"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--area", default="pilot-kustavi-inio-velkua")
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--variant")
    parser.add_argument("--include-class", action="append", dest="included_classes")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    manifest = load_manifest()
    area_config(manifest, args.area)
    source = source_config(manifest, args.source)
    processing = manifest["processing"]
    suffix = f"-{args.variant}" if args.variant else ""
    source_path = args.input or (
        REPO_ROOT / "raw" / "landcover" / args.source / f"{args.area}{suffix}.tif"
    )
    output_path = args.output or (
        REPO_ROOT / "work" / "landcover" / f"{args.area}{suffix}.geojson"
    )

    class_mapping = {int(value): name for value, name in source["class_mapping"].items()}
    if args.included_classes:
        requested_classes = set(args.included_classes)
        available_classes = set(class_mapping.values())
        unknown_classes = requested_classes - available_classes
        if unknown_classes:
            raise ValueError(f"Unknown classes: {sorted(unknown_classes)}")
        class_mapping = {
            value: name for value, name in class_mapping.items()
            if name in requested_classes
        }
    class_names = sorted(set(class_mapping.values()))
    class_indexes = {name: index + 1 for index, name in enumerate(class_names)}
    reverse_indexes = {index: name for name, index in class_indexes.items()}
    minimum_areas = processing["minimum_area_square_metres"]
    simplify_tolerance = float(processing["simplify_tolerance_metres"])

    features = []
    source_counts = Counter()
    output_counts = Counter()
    output_areas = Counter()

    with rasterio.open(source_path) as dataset:
        if dataset.crs is None:
            raise ValueError(f"Input raster {source_path} has no CRS")
        values = dataset.read(1)
        valid = values != dataset.nodata if dataset.nodata is not None else np.ones(values.shape, bool)
        reclassified = np.zeros(values.shape, dtype=np.uint8)
        for source_value, class_name in class_mapping.items():
            mask = valid & (values == source_value)
            source_counts[str(source_value)] = int(mask.sum())
            reclassified[mask] = class_indexes[class_name]

        target_transformer = Transformer.from_crs(
            dataset.crs, processing["output_crs"], always_xy=True
        ).transform
        for geometry, class_index in shapes(
            reclassified, mask=reclassified > 0, transform=dataset.transform
        ):
            class_name = reverse_indexes[int(class_index)]
            polygon = shape(geometry)
            minimum_area = float(minimum_areas[class_name])
            if polygon.area < minimum_area:
                continue
            polygon = polygon.simplify(simplify_tolerance, preserve_topology=True)
            if polygon.is_empty or not polygon.is_valid:
                polygon = polygon.buffer(0)
            if polygon.is_empty:
                continue
            output_counts[class_name] += 1
            output_areas[class_name] += polygon.area
            projected = transform(polygon, target_transformer, interleaved=False)
            features.append({
                "type": "Feature",
                "properties": {
                    "class": class_name,
                    "source": args.source,
                    "source_date": "2022",
                },
                "geometry": mapping(projected),
            })

        raster_metadata = {
            "width": dataset.width,
            "height": dataset.height,
            "resolution": [abs(dataset.transform.a), abs(dataset.transform.e)],
            "crs": str(dataset.crs),
            "bounds": list(dataset.bounds),
            "nodata": dataset.nodata,
        }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    collection = {
        "type": "FeatureCollection",
        "name": processing["layer_name"],
        "features": features,
    }
    output_path.write_text(
        json.dumps(collection, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "area": args.area,
        "source": args.source,
        "variant": args.variant,
        "included_classes": sorted(set(class_mapping.values())),
        "input": str(source_path.relative_to(REPO_ROOT)),
        "output": str(output_path.relative_to(REPO_ROOT)),
        "output_bytes": output_path.stat().st_size,
        "raster": raster_metadata,
        "source_pixel_counts": dict(sorted(source_counts.items())),
        "feature_counts": dict(sorted(output_counts.items())),
        "area_square_metres": {
            key: round(value, 1) for key, value in sorted(output_areas.items())
        },
    }
    receipt_path = source_path.with_suffix(".receipt.json")
    if receipt_path.exists():
        report["download"] = json.loads(receipt_path.read_text(encoding="utf-8"))
    report_path = REPO_ROOT / "reports" / f"landcover-{args.area}{suffix}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

