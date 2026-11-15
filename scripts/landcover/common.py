#!/usr/bin/env python3
"""Shared helpers for the complementary land-cover pipeline."""

from __future__ import annotations

from pathlib import Path

from pyproj import Transformer
from shapely import transform
from shapely.geometry import box
from shapely.ops import unary_union
import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPO_ROOT / "data-sources" / "landcover.yml"


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        manifest = yaml.safe_load(stream)
    if manifest.get("schema_version") != 1:
        raise ValueError(f"Unsupported manifest schema in {path}")
    return manifest


def area_config(manifest: dict, area_id: str) -> dict:
    try:
        return manifest["areas"][area_id]
    except KeyError as error:
        choices = ", ".join(sorted(manifest.get("areas", {})))
        raise ValueError(f"Unknown area {area_id!r}; choose one of: {choices}") from error


def source_config(manifest: dict, source_id: str) -> dict:
    try:
        return manifest["sources"][source_id]
    except KeyError as error:
        choices = ", ".join(sorted(manifest.get("sources", {})))
        raise ValueError(f"Unknown source {source_id!r}; choose one of: {choices}") from error


def area_clip_geometry(area: dict, target_crs: str | int = "EPSG:4326"):
    """Return the configured non-rectangular target area in the requested CRS."""
    included = area.get("include_bboxes_wgs84", [area["bbox_wgs84"]])
    geometry = unary_union([box(*bounds) for bounds in included])
    north_limit = float(area.get("north_limit_wgs84", 90))
    geometry = geometry.intersection(box(-180, -90, 180, north_limit))
    excluded = area.get("exclude_bboxes_wgs84", [])
    if excluded:
        geometry = geometry.difference(unary_union([box(*bounds) for bounds in excluded]))
    if str(target_crs).upper() not in {"4326", "EPSG:4326"}:
        projector = Transformer.from_crs("EPSG:4326", target_crs, always_xy=True).transform
        geometry = transform(geometry, projector, interleaved=False)
    return geometry

