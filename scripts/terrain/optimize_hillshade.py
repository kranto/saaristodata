#!/usr/bin/env python3
"""Simplify low zooms of an existing hillshade PMTiles archive."""

from __future__ import annotations

import argparse
import io
import json
import math
import sqlite3
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image


ZOOM_PROFILES = {
    7: {"render_size": 32, "quality": 35, "preserve_alpha": False},
    8: {"render_size": 64, "quality": 45, "preserve_alpha": False},
    9: {"render_size": 128, "quality": 60, "preserve_alpha": True},
}
WEBP_METHOD = 4


def longitude_tile(lon: float, zoom: int) -> int:
    return math.floor((lon + 180) / 360 * (1 << zoom))


def latitude_tile(lat: float, zoom: int) -> int:
    latitude = math.radians(max(-85.05112878, min(85.05112878, lat)))
    return math.floor((1 - math.asinh(math.tan(latitude)) / math.pi) / 2 * (1 << zoom))


def pmtiles_json(source: Path, flag: str) -> dict:
    result = subprocess.run(
        ["pmtiles", "show", flag, str(source)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def simplify_tile(
    data: bytes,
    render_size: int,
    quality: int,
    preserve_alpha: bool,
) -> bytes:
    original = np.asarray(Image.open(io.BytesIO(data)).convert("RGBA")).copy()
    if preserve_alpha:
        rgb = Image.fromarray(original[:, :, :3], mode="RGB")
        rgb = rgb.resize((render_size, render_size), Image.Resampling.BILINEAR)
        rgb = rgb.resize((256, 256), Image.Resampling.BILINEAR)
        alpha = original[:, :, 3]
        simplified = np.dstack((np.asarray(rgb), alpha))
    else:
        rgba = Image.fromarray(original, mode="RGBA")
        rgba = rgba.resize((render_size, render_size), Image.Resampling.BILINEAR)
        rgba = rgba.resize((256, 256), Image.Resampling.NEAREST)
        simplified = np.asarray(rgba).copy()
        alpha = simplified[:, :, 3]
        alpha[alpha < 8] = 0
        simplified[:, :, 3] = alpha
    simplified[alpha == 0, :3] = 181
    encoded = io.BytesIO()
    Image.fromarray(simplified, mode="RGBA").save(
        encoded,
        format="WEBP",
        quality=quality,
        method=WEBP_METHOD,
    )
    return encoded.getvalue()


def fetch_tile(source: Path, zoom: int, x: int, y: int) -> bytes | None:
    tile = subprocess.run(
        ["pmtiles", "tile", str(source), str(zoom), str(x), str(y)],
        capture_output=True,
    )
    if tile.returncode != 0 or not tile.stdout.startswith(b"RIFF"):
        return None
    return tile.stdout


def create_low_zoom_mbtiles(source: Path, output: Path, header: dict, metadata: dict) -> dict:
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
    low_metadata = dict(metadata)
    low_metadata["minzoom"] = str(min(ZOOM_PROFILES))
    low_metadata["maxzoom"] = str(header["maxzoom"])
    low_metadata["bounds"] = ",".join(map(str, header["bounds"]))
    database.executemany(
        "INSERT INTO metadata VALUES (?, ?)",
        [(key, str(value)) for key, value in low_metadata.items()],
    )

    west, south, east, north = header["bounds"]
    stats = {}
    try:
        for zoom, profile in ZOOM_PROFILES.items():
            x_min = longitude_tile(west, zoom)
            x_max = longitude_tile(math.nextafter(east, west), zoom)
            y_min = latitude_tile(north, zoom)
            y_max = latitude_tile(math.nextafter(south, north), zoom)
            before = 0
            after = 0
            count = 0
            for x in range(x_min, x_max + 1):
                for y in range(y_min, y_max + 1):
                    tile = fetch_tile(source, zoom, x, y)
                    if tile is None:
                        continue
                    optimized = simplify_tile(tile, **profile)
                    database.execute(
                        "INSERT INTO tiles VALUES (?, ?, ?, ?)",
                        (zoom, x, (1 << zoom) - 1 - y, optimized),
                    )
                    before += len(tile)
                    after += len(optimized)
                    count += 1
            database.commit()
            stats[str(zoom)] = {
                "tiles": count,
                "before_bytes": before,
                "after_bytes": after,
                **profile,
            }
    finally:
        database.close()
    return stats


def verify_low_zoom_tiles(source: Path, rebuilt: Path, bounds: list[float]) -> None:
    west, south, east, north = bounds
    for zoom in ZOOM_PROFILES:
        x_min = longitude_tile(west, zoom)
        x_max = longitude_tile(math.nextafter(east, west), zoom)
        y_min = latitude_tile(north, zoom)
        y_max = latitude_tile(math.nextafter(south, north), zoom)
        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                original = fetch_tile(source, zoom, x, y)
                optimized = fetch_tile(rebuilt, zoom, x, y)
                if original is None and optimized is None:
                    continue
                if original is None or optimized is None:
                    raise RuntimeError(f"Tile coverage changed at {zoom}/{x}/{y}")
                optimized_image = Image.open(io.BytesIO(optimized)).convert("RGBA")
                if optimized_image.size != (256, 256):
                    raise RuntimeError(f"Unexpected tile size at {zoom}/{x}/{y}")
                if not np.asarray(optimized_image)[:, :, 3].any():
                    raise RuntimeError(f"Tile became fully transparent at {zoom}/{x}/{y}")


def optimize(source: Path, output: Path) -> dict:
    header = pmtiles_json(source, "--header-json")
    metadata = pmtiles_json(source, "--metadata")
    with tempfile.TemporaryDirectory(prefix="hillshade-optimize-") as temporary:
        temporary_dir = Path(temporary)
        low_mbtiles = temporary_dir / "low.mbtiles"
        low_pmtiles = temporary_dir / "low.pmtiles"
        high_pmtiles = temporary_dir / "high.pmtiles"
        rebuilt = temporary_dir / "rebuilt.pmtiles"
        stats = create_low_zoom_mbtiles(source, low_mbtiles, header, metadata)
        subprocess.run(["pmtiles", "convert", str(low_mbtiles), str(low_pmtiles)], check=True)
        subprocess.run([
            "pmtiles", "extract", str(source), str(high_pmtiles),
            "--minzoom", str(max(ZOOM_PROFILES) + 1),
            "--maxzoom", str(header["maxzoom"]),
        ], check=True)
        subprocess.run(
            ["pmtiles", "merge", str(low_pmtiles), str(high_pmtiles), str(rebuilt)],
            check=True,
        )
        subprocess.run(["pmtiles", "verify", str(rebuilt)], check=True)
        verify_low_zoom_tiles(source, rebuilt, header["bounds"])
        output.parent.mkdir(parents=True, exist_ok=True)
        rebuilt.replace(output)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path, nargs="?")
    args = parser.parse_args()
    output = args.output or args.source
    stats = optimize(args.source, output)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
