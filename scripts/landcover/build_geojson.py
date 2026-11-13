#!/usr/bin/env python3
"""Reclassify and vectorize a categorical land-cover GeoTIFF."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine
from pyproj import Transformer
from rasterio.features import bounds as feature_bounds, shapes
from rasterio.transform import array_bounds
from rasterio.windows import Window, from_bounds
from rasterio.warp import Resampling, reproject
from shapely import transform
from shapely.geometry import mapping, shape

from common import REPO_ROOT, area_config, load_manifest, source_config


DEFAULT_SOURCE = "syke-maanpeite-2022"


def box_blur(values: np.ndarray, radius: int) -> np.ndarray:
    if radius == 0:
        return values
    size = radius * 2 + 1
    padded = np.pad(values, radius, mode="edge")
    integral = np.pad(padded, ((1, 0), (1, 0)), mode="constant")
    integral = integral.cumsum(axis=0, dtype=np.float32).cumsum(axis=1, dtype=np.float32)
    totals = (
        integral[size:, size:]
        - integral[:-size, size:]
        - integral[size:, :-size]
        + integral[:-size, :-size]
    )
    return totals / (size * size)


def smoothed_shapes(
    values: np.ndarray,
    transform: Affine,
    crs: rasterio.crs.CRS,
    factor: int,
    radius: int,
    chunk_size: int = 512,
):
    """Yield a smoothed binary mask as polygons without allocating the full upsampled raster."""
    height, width = values.shape
    halo = max(2, math.ceil((radius + 1) / factor) + 1)
    scale = Affine.scale(1 / factor, 1 / factor)
    for row in range(0, height, chunk_size):
        core_height = min(chunk_size, height - row)
        source_row = max(0, row - halo)
        source_bottom = min(height, row + core_height + halo)
        for column in range(0, width, chunk_size):
            core_width = min(chunk_size, width - column)
            source_column = max(0, column - halo)
            source_right = min(width, column + core_width + halo)
            source_values = values[
                source_row:source_bottom,
                source_column:source_right,
            ].astype(np.float32)
            source_transform = transform * Affine.translation(source_column, source_row)
            destination = np.zeros(
                (source_values.shape[0] * factor, source_values.shape[1] * factor),
                dtype=np.float32,
            )
            reproject(
                source=source_values,
                destination=destination,
                src_transform=source_transform,
                src_crs=crs,
                dst_transform=source_transform * scale,
                dst_crs=crs,
                src_nodata=0,
                dst_nodata=0,
                resampling=Resampling.bilinear,
            )
            destination = box_blur(destination, radius)
            top = (row - source_row) * factor
            left = (column - source_column) * factor
            core = destination[
                top:top + core_height * factor,
                left:left + core_width * factor,
            ] >= 0.5
            core_transform = transform * Affine.translation(column, row) * scale
            core_bounds = array_bounds(core.shape[0], core.shape[1], core_transform)
            for geometry, value in shapes(
                core.astype(np.uint8), mask=core, transform=core_transform
            ):
                west, south, east, north = feature_bounds(geometry)
                touches_chunk_boundary = (
                    math.isclose(west, core_bounds[0], abs_tol=0.01)
                    or math.isclose(south, core_bounds[1], abs_tol=0.01)
                    or math.isclose(east, core_bounds[2], abs_tol=0.01)
                    or math.isclose(north, core_bounds[3], abs_tol=0.01)
                )
                yield geometry, value, touches_chunk_boundary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--area", default="pilot-kustavi-inio-velkua")
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--variant")
    parser.add_argument("--include-class", action="append", dest="included_classes")
    parser.add_argument("--clip-to-area", action="store_true")
    parser.add_argument(
        "--smooth-factor",
        type=int,
        default=1,
        help="Upsample a single-class mask before vectorizing (for example 4)",
    )
    parser.add_argument(
        "--smooth-radius-pixels",
        type=int,
        default=0,
        help="Box-filter radius after upsampling, in output pixels",
    )
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    manifest = load_manifest()
    area = area_config(manifest, args.area)
    source = source_config(manifest, args.source)
    processing = manifest["processing"]
    suffix = f"-{args.variant}" if args.variant else ""
    source_path = args.input.resolve() if args.input else (
        REPO_ROOT / "raw" / "landcover" / args.source / f"{args.area}{suffix}.tif"
    )
    output_path = args.output.resolve() if args.output else (
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
    if args.smooth_factor < 1:
        raise ValueError("--smooth-factor must be at least 1")
    if args.smooth_radius_pixels < 0:
        raise ValueError("--smooth-radius-pixels cannot be negative")
    if args.smooth_factor > 1 and len(class_names) != 1:
        raise ValueError("--smooth-factor requires exactly one included class")
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
        window = None
        if args.clip_to_area:
            if dataset.crs.to_epsg() != 3067:
                raise ValueError("--clip-to-area currently requires an EPSG:3067 source raster")
            window = from_bounds(*area["bbox_epsg3067"], transform=dataset.transform)
            window = window.round_offsets().round_lengths().intersection(
                Window(0, 0, dataset.width, dataset.height)
            )
        values = dataset.read(1, window=window)
        working_transform = dataset.window_transform(window) if window else dataset.transform
        valid = values != dataset.nodata if dataset.nodata is not None else np.ones(values.shape, bool)
        reclassified = np.zeros(values.shape, dtype=np.uint8)
        for source_value, class_name in class_mapping.items():
            mask = valid & (values == source_value)
            source_counts[str(source_value)] = int(mask.sum())
            reclassified[mask] = class_indexes[class_name]

        if args.smooth_factor > 1:
            geometry_iterator = smoothed_shapes(
                reclassified,
                working_transform,
                dataset.crs,
                args.smooth_factor,
                args.smooth_radius_pixels,
            )
            vectorization_transform = working_transform * Affine.scale(
                1 / args.smooth_factor,
                1 / args.smooth_factor,
            )
        else:
            geometry_iterator = (
                (geometry, class_index, False)
                for geometry, class_index in shapes(
                    reclassified,
                    mask=reclassified > 0,
                    transform=working_transform,
                )
            )
            vectorization_transform = working_transform

        target_transformer = Transformer.from_crs(
            dataset.crs, processing["output_crs"], always_xy=True
        ).transform
        for geometry, class_index, touches_chunk_boundary in geometry_iterator:
            class_name = reverse_indexes[int(class_index)]
            polygon = shape(geometry)
            minimum_area = float(minimum_areas[class_name])
            if polygon.area < minimum_area and not touches_chunk_boundary:
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
            "clipped_to_area": args.clip_to_area,
            "vectorization_resolution": [
                abs(vectorization_transform.a), abs(vectorization_transform.e)
            ],
            "smooth_factor": args.smooth_factor,
            "smooth_radius_pixels": args.smooth_radius_pixels,
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

