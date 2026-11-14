#!/usr/bin/env python3
"""Build local MML contour and hillshade assets for the terrain-map prototype."""

from __future__ import annotations

import argparse
import base64
import io
import json
import math
import os
import re
import sqlite3
import subprocess
import time
import urllib.parse
import urllib.request
import zipfile
from collections.abc import Iterable
from pathlib import Path

import numpy as np
import rasterio
import shapefile
from PIL import Image
from pyproj import Transformer
from rasterio.merge import merge
from rasterio.transform import from_bounds
from rasterio.vrt import WarpedVRT
from rasterio.warp import Resampling, reproject


DEFAULT_BBOX = (19.0, 59.7, 23.0, 60.7)
WEB_MERCATOR_LIMIT = 20_037_508.342789244
HILLSHADE_FORMAT = "webp"
HILLSHADE_WEBP_QUALITY = 80
HILLSHADE_WEBP_METHOD = 4
HILLSHADE_GRAY_LEVELS = 64
HILLSHADE_TRANSPARENT_ALPHA_LIMIT = 8
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = REPO_ROOT / "raw" / "landcover" / "terrain-test"
FEATURES_URL = "https://avoin-paikkatieto.maanmittauslaitos.fi/maastotiedot/features/v1"
FILES_URL = "https://avoin-paikkatieto.maanmittauslaitos.fi/tiedostopalvelu/ogcproc/v1"
MAP_SHEET_PATTERN = re.compile(r"^[A-Z]\d{4}$")


def read_api_key(env_file: Path) -> str:
    key = os.environ.get("MML_API_KEY", "").strip()
    if key:
        return key
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, separator, value = line.partition("=")
            if separator and name.strip() == "MML_API_KEY":
                key = value.strip().strip("'\"")
                break
    if not key:
        raise SystemExit(f"MML_API_KEY is missing from the environment and {env_file}")
    return key


class MmlClient:
    def __init__(self, api_key: str) -> None:
        token = base64.b64encode(f"{api_key}:".encode()).decode()
        self.headers = {"Authorization": f"Basic {token}"}

    def request(self, url: str, *, data: dict | None = None) -> bytes:
        headers = dict(self.headers)
        body = None
        if data is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(data).encode()
        request = urllib.request.Request(url, data=body, headers=headers)
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.read()

    def json(self, url: str, *, data: dict | None = None) -> dict:
        return json.loads(self.request(url, data=data))

    def download(self, url: str, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(self.request(url))


def execute_process(client: MmlClient, process_id: str, inputs: dict) -> dict:
    response = client.json(
        f"{FILES_URL}/processes/{process_id}/execution",
        data={"id": process_id, "inputs": inputs},
    )
    job_url = next(link["href"] for link in response["links"] if link["rel"] == "self")
    while True:
        status = client.json(job_url)
        if status["status"] == "successful":
            results_url = next(
                (link["href"] for link in status.get("links", []) if "/results" in link.get("href", "")),
                f"{job_url.rstrip('/')}/results/",
            )
            return client.json(results_url)
        if status["status"] in {"failed", "dismissed"}:
            raise RuntimeError(f"MML job {status['status']}: {status.get('message', '')}")
        time.sleep(2)


def intersects(first: list[float], second: tuple[float, float, float, float]) -> bool:
    return not (first[2] < second[0] or first[0] > second[2] or first[3] < second[1] or first[1] > second[3])


def projected_bbox(bbox: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    west, south, east, north = bbox
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3067", always_xy=True)
    points = [transformer.transform(lon, lat) for lon in (west, east) for lat in (south, north)]
    xs, ys = zip(*points)
    return min(xs), min(ys), max(xs), max(ys)


def ensure_map_sheets(client: MmlClient, cache_dir: Path) -> list[Path]:
    extract_dir = cache_dir / "map-sheets"
    shapefiles = list(extract_dir.rglob("*.shp"))
    if shapefiles:
        return shapefiles
    result = execute_process(
        client,
        "karttalehtijako_koko_suomi",
        {"fileFormatInput": "ESRI shapefile", "dataSetInput": "kaikki"},
    )
    zip_url = next(item["zipPath"] for item in result["results"] if item.get("zipPath"))
    archive = cache_dir / "map-sheets.zip"
    client.download(zip_url, archive)
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zipped:
        zipped.extractall(extract_dir)
    for nested_archive in list(extract_dir.rglob("*.zip")):
        nested_dir = nested_archive.with_suffix("")
        nested_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(nested_archive) as zipped:
            zipped.extractall(nested_dir)
    return list(extract_dir.rglob("*.shp"))


def map_sheets_for_bbox(shapefiles: list[Path], bbox_3067: tuple[float, float, float, float]) -> list[str]:
    matches: set[str] = set()
    for path in shapefiles:
        reader = shapefile.Reader(str(path))
        field_names = [field[0] for field in reader.fields[1:]]
        for shape_record in reader.iterShapeRecords():
            if not intersects(shape_record.shape.bbox, bbox_3067):
                continue
            values = dict(zip(field_names, shape_record.record))
            for value in values.values():
                candidate = str(value).strip().upper()
                if MAP_SHEET_PATTERN.fullmatch(candidate):
                    matches.add(candidate)
    if not matches:
        raise RuntimeError("No 1:25 000 map sheets intersect the requested bbox")
    return sorted(matches)


def download_hillshade(client: MmlClient, sheets: list[str], raw_dir: Path) -> list[Path]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    missing = [sheet for sheet in sheets if not (raw_dir / f"{sheet}.tif").exists()]
    for start in range(0, len(missing), 100):
        batch = missing[start:start + 100]
        print(f"Requesting hillshade sheets {start + 1}-{start + len(batch)} of {len(missing)}", flush=True)
        result = execute_process(
            client,
            "rinnevarjoste_karttalehti",
            {"mapSheetInput": batch, "fileFormatInput": "TIFF", "dataSetInput": "rinnevarjoste_8m"},
        )
        for item in result["results"]:
            path = item.get("path", "")
            if not path.lower().endswith((".tif", ".tiff")):
                continue
            destination = raw_dir / Path(urllib.parse.urlparse(path).path).name
            client.download(path, destination)
    downloaded = [raw_dir / f"{sheet}.tif" for sheet in sheets if (raw_dir / f"{sheet}.tif").exists()]
    if not downloaded:
        raise RuntimeError("MML hillshade jobs returned no GeoTIFF files")
    return downloaded


def write_hillshade_png(
    paths: list[Path], bbox_wgs84: tuple[float, float, float, float], output: Path
) -> tuple[tuple[int, int], int]:
    bbox_3067 = projected_bbox(bbox_wgs84)
    datasets = [rasterio.open(path) for path in paths]
    try:
        mosaic, source_transform = merge(datasets, bounds=bbox_3067)
        source_crs = datasets[0].crs
        source_nodata = datasets[0].nodata
    finally:
        for dataset in datasets:
            dataset.close()

    west, south, east, north = bbox_wgs84
    centre_latitude = (south + north) / 2
    width_metres = (east - west) * 111_320 * math.cos(math.radians(centre_latitude))
    height_metres = (north - south) * 111_320
    width = max(1, math.ceil(width_metres / 8))
    height = max(1, math.ceil(height_metres / 8))
    target = np.zeros((height, width), dtype=np.uint8)
    reproject(
        source=mosaic[0],
        destination=target,
        src_transform=source_transform,
        src_crs=source_crs,
        src_nodata=source_nodata,
        dst_transform=from_bounds(west, south, east, north, width, height),
        dst_crs="EPSG:4326",
        dst_nodata=255,
        resampling=Resampling.bilinear,
    )
    neutral_gray = int(np.bincount(target.ravel(), minlength=256).argmax())
    deviation = np.abs(target.astype(np.int16) - neutral_gray)
    alpha = np.clip((deviation - 2) / 18 * 255, 0, 255).astype(np.uint8)
    rgba = np.dstack((target, target, target, alpha))
    Image.fromarray(rgba, mode="RGBA").save(output, optimize=True)
    return (width, height), neutral_gray


def merged_hillshade(
    paths: list[Path], bbox: tuple[float, float, float, float], output: Path
) -> Path:
    if output.exists():
        return output
    datasets = [rasterio.open(path) for path in paths]
    try:
        mosaic, transform = merge(
            datasets,
            bounds=projected_bbox(bbox),
            res=(8, 8),
            nodata=181,
            dtype="uint8",
        )
        crs = datasets[0].crs
    finally:
        for dataset in datasets:
            dataset.close()
    output.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        output,
        "w",
        driver="GTiff",
        width=mosaic.shape[2],
        height=mosaic.shape[1],
        count=1,
        dtype="uint8",
        crs=crs,
        transform=transform,
        nodata=181,
        tiled=True,
        blockxsize=512,
        blockysize=512,
        compress="deflate",
        predictor=2,
        BIGTIFF="YES",
    ) as dataset:
        dataset.write(mosaic)
    return output


def longitude_tile(lon: float, zoom: int) -> int:
    return math.floor((lon + 180) / 360 * (1 << zoom))


def latitude_tile(lat: float, zoom: int) -> int:
    latitude = math.radians(max(-85.05112878, min(85.05112878, lat)))
    return math.floor((1 - math.asinh(math.tan(latitude)) / math.pi) / 2 * (1 << zoom))


def web_mercator_tile_bounds(zoom: int, x: int, y: int) -> tuple[float, float, float, float]:
    tile_span = WEB_MERCATOR_LIMIT * 2 / (1 << zoom)
    left = -WEB_MERCATOR_LIMIT + x * tile_span
    top = WEB_MERCATOR_LIMIT - y * tile_span
    return left, top - tile_span, left + tile_span, top


def build_hillshade_pmtiles(
    source_path: Path,
    bbox: tuple[float, float, float, float],
    output: Path,
    minimum_zoom: int = 7,
    maximum_zoom: int = 13,
) -> dict:
    mbtiles = output.with_suffix(".mbtiles")
    mbtiles.unlink(missing_ok=True)
    database = sqlite3.connect(mbtiles)
    database.executescript("""
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        CREATE TABLE metadata (name TEXT, value TEXT);
        CREATE TABLE tiles (
            zoom_level INTEGER,
            tile_column INTEGER,
            tile_row INTEGER,
            tile_data BLOB,
            UNIQUE (zoom_level, tile_column, tile_row)
        );
    """)
    west, south, east, north = bbox
    database.executemany("INSERT INTO metadata VALUES (?, ?)", [
        ("name", "MML Rinnevarjoste 8 m"),
        ("type", "overlay"),
        ("version", "1"),
        ("description", "Maanmittauslaitos Rinnevarjoste 8 m, neutral sea transparent"),
        ("format", HILLSHADE_FORMAT),
        ("bounds", ",".join(map(str, bbox))),
        ("minzoom", str(minimum_zoom)),
        ("maxzoom", str(maximum_zoom)),
    ])
    tile_counts: dict[str, int] = {}
    try:
        with rasterio.open(source_path) as source, WarpedVRT(
            source,
            crs="EPSG:3857",
            nodata=181,
            resampling=Resampling.bilinear,
        ) as warped:
            for zoom in range(minimum_zoom, maximum_zoom + 1):
                x_min = longitude_tile(west, zoom)
                x_max = longitude_tile(math.nextafter(east, west), zoom)
                y_min = latitude_tile(north, zoom)
                y_max = latitude_tile(math.nextafter(south, north), zoom)
                count = 0
                for x in range(x_min, x_max + 1):
                    for y in range(y_min, y_max + 1):
                        bounds = web_mercator_tile_bounds(zoom, x, y)
                        gray = np.full((256, 256), 181, dtype=np.uint8)
                        reproject(
                            source=rasterio.band(warped, 1),
                            destination=gray,
                            src_transform=warped.transform,
                            src_crs=warped.crs,
                            src_nodata=181,
                            dst_transform=from_bounds(*bounds, 256, 256),
                            dst_crs="EPSG:3857",
                            dst_nodata=181,
                            resampling=Resampling.bilinear,
                        )
                        deviation = np.abs(gray.astype(np.int16) - 181)
                        alpha = np.clip((deviation - 2) / 18 * 255, 0, 255).astype(np.uint8)
                        alpha[alpha < HILLSHADE_TRANSPARENT_ALPHA_LIMIT] = 0
                        quantization_step = 256 // HILLSHADE_GRAY_LEVELS
                        signed_gray = gray.astype(np.int16) - 181
                        gray = np.clip(
                            181 + np.rint(signed_gray / quantization_step) * quantization_step,
                            0,
                            255,
                        ).astype(np.uint8)
                        gray[alpha == 0] = 181
                        if not alpha.any():
                            continue
                        rgba = np.dstack((gray, gray, gray, alpha))
                        encoded = io.BytesIO()
                        Image.fromarray(rgba, mode="RGBA").save(
                            encoded,
                            format="WEBP",
                            quality=HILLSHADE_WEBP_QUALITY,
                            method=HILLSHADE_WEBP_METHOD,
                        )
                        database.execute(
                            "INSERT INTO tiles VALUES (?, ?, ?, ?)",
                            (zoom, x, (1 << zoom) - 1 - y, encoded.getvalue()),
                        )
                        count += 1
                database.commit()
                tile_counts[str(zoom)] = count
                print(f"Hillshade zoom {zoom}: {count} non-empty tiles", flush=True)
    finally:
        database.close()
    output.unlink(missing_ok=True)
    subprocess.run(["pmtiles", "convert", str(mbtiles), str(output)], check=True)
    mbtiles.unlink()
    return {
        "minzoom": minimum_zoom,
        "maxzoom": maximum_zoom,
        "format": HILLSHADE_FORMAT,
        "quality": HILLSHADE_WEBP_QUALITY,
        "encoding_method": HILLSHADE_WEBP_METHOD,
        "gray_levels": HILLSHADE_GRAY_LEVELS,
        "tile_counts": tile_counts,
    }


def request_contours(client: MmlClient, bbox: tuple[float, float, float, float], limit: int = 10_000) -> list[dict]:
    params = urllib.parse.urlencode({"bbox": ",".join(map(str, bbox)), "limit": limit, "f": "json"})
    response = client.json(f"{FEATURES_URL}/collections/korkeuskayra/items?{params}")
    features = response.get("features", [])
    if len(features) < limit:
        return features
    west, south, east, north = bbox
    if east - west >= north - south:
        middle = (west + east) / 2
        parts = [(west, south, middle, north), (middle, south, east, north)]
    else:
        middle = (south + north) / 2
        parts = [(west, south, east, middle), (west, middle, east, north)]
    deduplicated: dict[str, dict] = {}
    for part in parts:
        for feature in request_contours(client, part, limit):
            key = str(feature.get("properties", {}).get("mtk_id") or feature.get("id"))
            deduplicated[key] = feature
    return list(deduplicated.values())


def iter_contours(
    client: MmlClient, bbox: tuple[float, float, float, float], chunk_degrees: float = 0.25
):
    west, south, east, north = bbox
    seen: set[str] = set()
    latitude = south
    while latitude < north:
        longitude = west
        chunk_north = min(north, latitude + chunk_degrees)
        while longitude < east:
            chunk_east = min(east, longitude + chunk_degrees)
            chunk = (longitude, latitude, chunk_east, chunk_north)
            features = request_contours(client, chunk)
            print(f"Contours {chunk}: {len(features)} source features", flush=True)
            for feature in features:
                key = str(feature.get("properties", {}).get("mtk_id") or feature.get("id"))
                if key not in seen:
                    seen.add(key)
                    yield feature
            longitude = chunk_east
        latitude = chunk_north


def write_contour_sequences(features: Iterable[dict], output_dir: Path) -> dict[str, int]:
    outputs = {
        5: (output_dir / "contours-5m.geojsonseq").open("w", encoding="utf-8"),
        10: (output_dir / "contours-10m.geojsonseq").open("w", encoding="utf-8"),
    }
    counts = {"5m": 0, "10m": 0}
    try:
        for feature in features:
            millimetres = int(feature.get("properties", {}).get("korkeusarvo", -1))
            if millimetres < 0 or millimetres % 5000:
                continue
            elevation = millimetres / 1000
            compact = {
                "type": "Feature",
                "properties": {"elevation": elevation},
                "geometry": feature["geometry"],
            }
            encoded = json.dumps(compact, separators=(",", ":"), ensure_ascii=False)
            outputs[5].write(encoded + "\n")
            counts["5m"] += 1
            if millimetres % 10_000 == 0:
                outputs[10].write(encoded + "\n")
                counts["10m"] += 1
    finally:
        for stream in outputs.values():
            stream.close()
    return counts


def build_pmtiles(sequence: Path, output: Path) -> None:
    mbtiles = output.with_suffix(".mbtiles")
    subprocess.run(
        [
            "tippecanoe", "--force", "--minimum-zoom=7", "--maximum-zoom=14",
            "--no-feature-limit", "--no-tile-size-limit", "--layer", "contours",
            "--output", str(mbtiles), str(sequence),
        ],
        check=True,
    )
    output.unlink(missing_ok=True)
    subprocess.run(["pmtiles", "convert", str(mbtiles), str(output)], check=True)
    mbtiles.unlink()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bbox", nargs=4, type=float, default=DEFAULT_BBOX, metavar=("W", "S", "E", "N"))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--env-file", type=Path, default=REPO_ROOT / ".env")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bbox = tuple(args.bbox)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    client = MmlClient(read_api_key(args.env_file))

    sheet_paths = ensure_map_sheets(client, output_dir / "cache")
    sheets = map_sheets_for_bbox(sheet_paths, projected_bbox(bbox))
    hillshade_tiffs = download_hillshade(client, sheets, output_dir / "source-hillshade")
    downloaded_sheets = {path.stem for path in hillshade_tiffs}
    hillshade_source = merged_hillshade(hillshade_tiffs, bbox, output_dir / "cache" / "hillshade-8m-merged.tif")
    hillshade = build_hillshade_pmtiles(hillshade_source, bbox, output_dir / "hillshade-8m-webp.pmtiles")

    contour_features = iter_contours(client, bbox)
    counts = write_contour_sequences(contour_features, output_dir)
    build_pmtiles(output_dir / "contours-5m.geojsonseq", output_dir / "contours-5m.pmtiles")
    build_pmtiles(output_dir / "contours-10m.geojsonseq", output_dir / "contours-10m.pmtiles")

    manifest = {
        "schema_version": 1,
        "source": "Maanmittauslaitos",
        "requested_bbox_wgs84": list(bbox),
        "hillshade": {
            "product": "Rinnevarjoste 8 m",
            "map_sheets": sheets,
            "source_file_count": len(hillshade_tiffs),
            "missing_map_sheets": sorted(set(sheets) - downloaded_sheets),
            **hillshade,
        },
        "contours": {"collection": "korkeuskayra", "feature_counts": counts},
        "assets": {
            "contours_5m": "contours-5m.pmtiles",
            "contours_10m": "contours-10m.pmtiles",
            "hillshade": "hillshade-8m-webp.pmtiles",
        },
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
