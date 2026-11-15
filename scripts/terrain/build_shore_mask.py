#!/usr/bin/env python3
"""Mask hillshade and smoothed Syke forest to MML's shoreline."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.parse
from pathlib import Path

from shapely import make_valid
from shapely.geometry import box, mapping, shape
from shapely.ops import clip_by_rect, unary_union


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from build_test_terrain import (  # noqa: E402
    DEFAULT_AREA,
    FEATURES_URL,
    MmlClient,
    REPO_ROOT,
    area_clip_geometry,
    area_config,
    build_hillshade_pmtiles,
    load_manifest,
    read_api_key,
)


PILOT_BBOX = (21.75108, 60.08997, 21.83418, 60.11763)
RAW_DIR = REPO_ROOT / "raw" / "landcover" / "shore-mask"
FOREST_SOURCE = (
    REPO_ROOT / "work" / "landcover"
    / "pilot-archipelago-sea-syke-forest-smoothed.geojson"
)
FOREST_OUTPUT = (
    REPO_ROOT / "tiles"
    / "landcover-archipelago-sea-syke-forest-shore-masked.pmtiles"
)
HILLSHADE_SOURCE = (
    REPO_ROOT / "raw" / "landcover" / "terrain-test" / "cache"
    / "hillshade-8m-merged-region-v2.tif"
)
HILLSHADE_OUTPUT = (
    REPO_ROOT / "raw" / "landcover" / "terrain-test"
    / "hillshade-8m-webp-z12-shore-masked.pmtiles"
)


def download_sea(client: MmlClient, bbox: tuple[float, float, float, float]) -> dict:
    params = urllib.parse.urlencode({
        "bbox": ",".join(map(str, bbox)),
        "limit": 10_000,
        "f": "json",
    })
    url = f"{FEATURES_URL}/collections/meri/items?{params}"
    features: list[dict] = []
    number_matched = None
    while url:
        page = client.json(url)
        features.extend(page.get("features", []))
        number_matched = page.get("numberMatched", number_matched)
        url = next(
            (link.get("href") for link in page.get("links", []) if link.get("rel") == "next"),
            None,
        )
    return {
        "type": "FeatureCollection",
        "numberMatched": number_matched,
        "numberReturned": len(features),
        "features": features,
    }


def build_forest(clip_geometry, sea_geometry, output: Path) -> int:
    source = json.loads(FOREST_SOURCE.read_text(encoding="utf-8"))
    sequence = RAW_DIR / "syke-forest-shore-masked.geojsonseq"
    count = 0
    with sequence.open("w", encoding="utf-8") as stream:
        for feature in source["features"]:
            geometry = shape(feature["geometry"])
            if not geometry.intersects(clip_geometry):
                continue
            geometry = make_valid(geometry).intersection(clip_geometry)
            if geometry.is_empty:
                continue
            local_sea = clip_by_rect(sea_geometry, *geometry.bounds)
            if not local_sea.is_empty:
                geometry = make_valid(geometry.difference(local_sea))
            if geometry.is_empty:
                continue
            stream.write(json.dumps({
                "type": "Feature",
                "properties": feature["properties"],
                "geometry": mapping(geometry),
            }, ensure_ascii=False, separators=(",", ":")) + "\n")
            count += 1

    mbtiles = REPO_ROOT / "work" / "landcover" / f"{output.stem}.mbtiles"
    overview = mbtiles.with_name(f"{mbtiles.stem}-overview.mbtiles")
    for path in (mbtiles, overview, output):
        path.unlink(missing_ok=True)
    attribution = "Lähde: Syke, Maanpeite 2 m 2022 (CC BY 4.0), kartografisesti pehmennetty"
    name = "Complementary land cover (Syke): shoreline masked forest"
    subprocess.run([
        "tippecanoe", "--output", str(mbtiles), "--layer", "landcover",
        "--minimum-zoom", "10", "--maximum-zoom", "14",
        "--coalesce-smallest-as-needed", "--attribution", attribution,
        "--name", name, str(sequence),
    ], check=True)
    subprocess.run([
        "tippecanoe", "--output", str(overview), "--layer", "landcover",
        "--minimum-zoom", "8", "--maximum-zoom", "9",
        "--simplification", "20", "--include", "class",
        "--no-feature-limit", "--no-tile-size-limit", "--attribution", attribution,
        "--name", f"{name} overview", str(sequence),
    ], check=True)

    sys.path.insert(0, str(REPO_ROOT / "scripts" / "landcover"))
    from build_tiles import merge_overview_tiles  # noqa: E402

    merge_overview_tiles(mbtiles, overview, 8)
    overview.unlink()
    subprocess.run(["pmtiles", "convert", str(mbtiles), str(output)], check=True)
    mbtiles.unlink()
    return count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pilot",
        action="store_true",
        help="Build only the original shoreline-mask comparison area",
    )
    parser.add_argument(
        "--hillshade-only",
        action="store_true",
        help="Reuse the already generated masked forest and only rebuild hillshade",
    )
    parser.add_argument("--env-file", type=Path, default=REPO_ROOT / ".env")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if args.pilot:
        bbox = PILOT_BBOX
        clip_geometry = box(*bbox)
        suffix = "-pilot"
    else:
        area_definition = area_config(load_manifest(), DEFAULT_AREA)
        clip_geometry = area_clip_geometry(area_definition)
        bbox = tuple(clip_geometry.bounds)
        suffix = ""

    sea_path = RAW_DIR / f"mml-sea{suffix}.geojson"
    if sea_path.exists():
        sea_collection = json.loads(sea_path.read_text(encoding="utf-8"))
    else:
        client = MmlClient(read_api_key(args.env_file))
        sea_collection = download_sea(client, bbox)
        sea_path.write_text(
            json.dumps(sea_collection, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
    sea_parts = []
    for feature in sea_collection.get("features", []):
        geometry = shape(feature["geometry"])
        if not geometry.intersects(clip_geometry):
            continue
        clipped = geometry.intersection(clip_geometry)
        if not clipped.is_empty:
            sea_parts.append(make_valid(clipped))
    sea_geometry = unary_union(sea_parts)
    forest_output = (
        FOREST_OUTPUT.with_name(f"{FOREST_OUTPUT.stem}-pilot.pmtiles")
        if args.pilot else FOREST_OUTPUT
    )
    hillshade_output = (
        HILLSHADE_OUTPUT.with_name(f"{HILLSHADE_OUTPUT.stem}-pilot.pmtiles")
        if args.pilot else HILLSHADE_OUTPUT
    )
    if args.hillshade_only:
        sequence = RAW_DIR / "syke-forest-shore-masked.geojsonseq"
        forest_count = sum(1 for _ in sequence.open(encoding="utf-8"))
    else:
        forest_count = build_forest(clip_geometry, sea_geometry, forest_output)
    hillshade = build_hillshade_pmtiles(
        HILLSHADE_SOURCE,
        bbox,
        clip_geometry,
        hillshade_output,
        water_geometry=sea_geometry,
    )
    manifest = {
        "bbox_wgs84": list(bbox),
        "sea_features": len(sea_collection.get("features", [])),
        "forest_features": forest_count,
        "hillshade": hillshade,
        "assets": {
            "sea": str(sea_path.relative_to(REPO_ROOT)),
            "forest": str(forest_output.relative_to(REPO_ROOT)),
            "hillshade": str(hillshade_output.relative_to(REPO_ROOT)),
        },
    }
    (RAW_DIR / f"manifest{suffix}.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
