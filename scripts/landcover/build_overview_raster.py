#!/usr/bin/env python3
"""Render the low-zoom terrain land-cover vectors into one raster archive."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import sqlite3
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image
from pyproj import Transformer
from rasterio.features import rasterize
from rasterio.transform import from_bounds
from shapely import transform
from shapely.geometry import mapping, shape

from common import REPO_ROOT, area_config, load_manifest


MIN_ZOOM = 8
MAX_ZOOM = 10
SUPERSAMPLING = 2
WEBP_QUALITY = {8: 70, 9: 75, 10: 85}
WEBP_METHOD = 4
OPACITY_CAP_RATIO = 0.825
SOURCE_ARCHIVES = (
    ("fill", REPO_ROOT / "tiles" / "terrain-landcover-fill-r1.pmtiles"),
    ("kmtk", REPO_ROOT / "tiles" / "terrain-landcover-r1.pmtiles"),
)
DEFAULT_OUTPUT = REPO_ROOT / "tiles" / "terrain-landcover-overview-r1.pmtiles"
DEFAULT_REPORT = REPO_ROOT / "tiles" / "landcover-overview-raster.json"
CLASS_STYLES = {
    "forest": ("#72c10b", 0.45),
    "farmland": ("#f7e469", 0.80),
    "rock": ("#d9d8cf", 1.00),
    "open": ("#c9d4b1", 1.00),
    "wetland": ("#8497d2", 0.65),
    "sand": ("#ffd875", 1.00),
    "bare": ("#d1c4ae", 1.00),
    "urban": ("#cdb9a8", 1.00),
}
WEB_MERCATOR_LIMIT = 20_037_508.342789244


def longitude_tile(lon: float, zoom: int) -> int:
    return math.floor((lon + 180) / 360 * (1 << zoom))


def latitude_tile(lat: float, zoom: int) -> int:
    latitude = math.radians(max(-85.05112878, min(85.05112878, lat)))
    return math.floor((1 - math.asinh(math.tan(latitude)) / math.pi) / 2 * (1 << zoom))


def tile_bounds(zoom: int, x: int, y: int) -> tuple[float, float, float, float]:
    tile_span = WEB_MERCATOR_LIMIT * 2 / (1 << zoom)
    left = -WEB_MERCATOR_LIMIT + x * tile_span
    top = WEB_MERCATOR_LIMIT - y * tile_span
    return left, top - tile_span, left + tile_span, top


def tile_range(bounds: list[float], zoom: int):
    west, south, east, north = bounds
    return (
        range(longitude_tile(west, zoom), longitude_tile(math.nextafter(east, west), zoom) + 1),
        range(latitude_tile(north, zoom), latitude_tile(math.nextafter(south, north), zoom) + 1),
    )


def fetch_tile(archive: Path, zoom: int, x: int, y: int) -> bytes | None:
    tile = subprocess.run(
        ["pmtiles", "tile", str(archive), str(zoom), str(x), str(y)],
        capture_output=True,
    )
    if tile.returncode != 0 or not tile.stdout.startswith(b"\x1f\x8b"):
        return None
    return tile.stdout


def build_decode_mbtiles(archive: Path, output: Path, bounds: list[float]) -> tuple[set, dict]:
    database = sqlite3.connect(output)
    database.executescript("""
        CREATE TABLE metadata (name TEXT, value TEXT);
        CREATE TABLE tiles (
            zoom_level INTEGER,
            tile_column INTEGER,
            tile_row INTEGER,
            tile_data BLOB,
            UNIQUE (zoom_level, tile_column, tile_row)
        );
    """)
    database.executemany("INSERT INTO metadata VALUES (?, ?)", [
        ("name", archive.stem),
        ("format", "pbf"),
        ("minzoom", str(MIN_ZOOM)),
        ("maxzoom", str(MAX_ZOOM)),
        ("bounds", ",".join(map(str, bounds))),
    ])
    available = set()
    byte_counts = {}
    try:
        for zoom in range(MIN_ZOOM, MAX_ZOOM + 1):
            byte_count = 0
            xs, ys = tile_range(bounds, zoom)
            for x in xs:
                for y in ys:
                    tile = fetch_tile(archive, zoom, x, y)
                    if tile is None:
                        continue
                    database.execute(
                        "INSERT INTO tiles VALUES (?, ?, ?, ?)",
                        (zoom, x, (1 << zoom) - 1 - y, tile),
                    )
                    available.add((zoom, x, y))
                    byte_count += len(tile)
            database.commit()
            byte_counts[str(zoom)] = byte_count
    finally:
        database.close()
    return available, byte_counts


def decode_features(mbtiles: Path, zoom: int, x: int, y: int) -> list[dict]:
    decoded = subprocess.run(
        ["tippecanoe-decode", str(mbtiles), str(zoom), str(x), str(y)],
        check=True,
        capture_output=True,
        text=True,
    )
    root = json.loads(decoded.stdout)
    features = []
    for layer in root.get("features", []):
        if layer.get("properties", {}).get("layer") == "landcover":
            features.extend(layer.get("features", []))
    return features


def hex_color(value: str) -> tuple[int, int, int]:
    return tuple(int(value[index:index + 2], 16) for index in (1, 3, 5))


def render_source(
    features: list[dict],
    bounds: tuple[float, float, float, float],
    transformer: Transformer,
) -> Image.Image:
    size = 256 * SUPERSAMPLING
    class_indexes = {name: index + 1 for index, name in enumerate(CLASS_STYLES)}
    shapes = []
    for feature in features:
        class_name = feature.get("properties", {}).get("class")
        if class_name not in class_indexes or not feature.get("geometry"):
            continue
        geometry = transform(
            shape(feature["geometry"]),
            transformer.transform,
            interleaved=False,
        )
        if not geometry.is_empty:
            shapes.append((mapping(geometry), class_indexes[class_name]))
    classes = rasterize(
        shapes,
        out_shape=(size, size),
        transform=from_bounds(*bounds, size, size),
        fill=0,
        dtype=np.uint8,
    ) if shapes else np.zeros((size, size), dtype=np.uint8)
    rgba = np.zeros((size, size, 4), dtype=np.uint8)
    for class_name, class_index in class_indexes.items():
        color, opacity = CLASS_STYLES[class_name]
        mask = classes == class_index
        rgba[mask, :3] = hex_color(color)
        rgba[mask, 3] = round(255 * opacity * OPACITY_CAP_RATIO)
    return Image.fromarray(rgba, mode="RGBA")


def encode_tile(image: Image.Image, zoom: int) -> bytes:
    image = image.resize((256, 256), Image.Resampling.LANCZOS)
    encoded = io.BytesIO()
    image.save(encoded, format="WEBP", quality=WEBP_QUALITY[zoom], method=WEBP_METHOD)
    return encoded.getvalue()


def build_raster(
    decode_sources: list[tuple[Path, set]],
    output: Path,
    bounds: list[float],
) -> dict:
    database = sqlite3.connect(output)
    database.executescript("""
        CREATE TABLE metadata (name TEXT, value TEXT);
        CREATE TABLE tiles (
            zoom_level INTEGER,
            tile_column INTEGER,
            tile_row INTEGER,
            tile_data BLOB,
            UNIQUE (zoom_level, tile_column, tile_row)
        );
    """)
    database.executemany("INSERT INTO metadata VALUES (?, ?)", [
        ("name", "Terrain land-cover overview"),
        ("type", "overlay"),
        ("version", "1"),
        ("format", "webp"),
        ("minzoom", str(MIN_ZOOM)),
        ("maxzoom", str(MAX_ZOOM)),
        ("bounds", ",".join(map(str, bounds))),
        ("attribution", "Lähde: Maanmittauslaitos KMTK BETA ja Syke Maanpeite 2 m 2022"),
    ])
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    stats = {}
    try:
        for zoom in range(MIN_ZOOM, MAX_ZOOM + 1):
            count = 0
            byte_count = 0
            xs, ys = tile_range(bounds, zoom)
            for x in xs:
                for y in ys:
                    tile_key = (zoom, x, y)
                    canvas = Image.new("RGBA", (256 * SUPERSAMPLING, 256 * SUPERSAMPLING))
                    for mbtiles, available in decode_sources:
                        if tile_key not in available:
                            continue
                        features = decode_features(mbtiles, zoom, x, y)
                        layer = render_source(features, tile_bounds(zoom, x, y), transformer)
                        canvas = Image.alpha_composite(canvas, layer)
                    if not np.asarray(canvas)[:, :, 3].any():
                        continue
                    encoded = encode_tile(canvas, zoom)
                    database.execute(
                        "INSERT INTO tiles VALUES (?, ?, ?, ?)",
                        (zoom, x, (1 << zoom) - 1 - y, encoded),
                    )
                    count += 1
                    byte_count += len(encoded)
            database.commit()
            stats[str(zoom)] = {"tiles": count, "bytes": byte_count}
    finally:
        database.close()
    return stats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--area", default="pilot-archipelago-sea")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    bounds = area_config(load_manifest(), args.area)["bbox_wgs84"]

    with tempfile.TemporaryDirectory(prefix="landcover-overview-") as temporary:
        temporary_dir = Path(temporary)
        decode_sources = []
        source_bytes = {}
        for name, archive in SOURCE_ARCHIVES:
            mbtiles = temporary_dir / f"{name}.mbtiles"
            available, byte_counts = build_decode_mbtiles(archive, mbtiles, bounds)
            decode_sources.append((mbtiles, available))
            source_bytes[name] = byte_counts
        raster_mbtiles = temporary_dir / "overview.mbtiles"
        raster_pmtiles = temporary_dir / "overview.pmtiles"
        stats = build_raster(decode_sources, raster_mbtiles, bounds)
        subprocess.run(["pmtiles", "convert", str(raster_mbtiles), str(raster_pmtiles)], check=True)
        subprocess.run(["pmtiles", "verify", str(raster_pmtiles)], check=True)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        raster_pmtiles.replace(args.output)

    report = {
        "schema_version": 1,
        "archive": args.output.name,
        "bounds": bounds,
        "minzoom": MIN_ZOOM,
        "maxzoom": MAX_ZOOM,
        "webp_quality_by_zoom": WEBP_QUALITY,
        "supersampling": SUPERSAMPLING,
        "opacity_cap_ratio": OPACITY_CAP_RATIO,
        "source_bytes": source_bytes,
        "raster": stats,
        "bytes": args.output.stat().st_size,
        "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
