#!/usr/bin/env python3
"""Download selected KMTK BETA polygon collections for a bounded pilot."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import urllib.parse
from datetime import UTC, datetime
from pathlib import Path

from common import REPO_ROOT, area_config, load_manifest, source_config


DEFAULT_SOURCE = "mml-kmtk-beta"
REQUEST_LIMIT = 10_000
INITIAL_SPLIT_DEPTHS = {
    # The full pilot contains enough rock polygons that asking for all of them
    # in one response is slow and frequently times out in the BETA service.
    "rock_area": 5,
}


def read_api_key(path: Path | None) -> str:
    if path:
        value = path.read_text(encoding="utf-8").strip()
    else:
        value = os.environ.get("MML_API_KEY", "").strip()
    if not value:
        raise ValueError("Set MML_API_KEY or provide --api-key-file")
    return value


def curl_config_value(value: str) -> str:
    if any(character in value for character in "\r\n"):
        raise ValueError("curl config values cannot contain line breaks")
    return value.replace("\\", "\\\\").replace('"', '\\"')


def request_json(url: str, api_key: str) -> dict:
    curl = shutil.which("curl")
    if curl is None:
        raise RuntimeError("curl is required to download KMTK data")
    # Pass credentials through stdin instead of process arguments so the API key
    # does not appear in process listings or logs.
    config = (
        f'user = "{curl_config_value(api_key)}:"\n'
        f'url = "{curl_config_value(url)}"\n'
    )
    result = subprocess.run(
        [
            curl,
            "--config", "-",
            "--silent",
            "--show-error",
            "--fail",
            "--retry", "4",
            "--retry-all-errors",
            "--connect-timeout", "30",
            "--max-time", "180",
            "--header", "Accept: application/geo+json, application/json",
            "--user-agent", "saaristolautat-landcover/1",
        ],
        input=config,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


def collection_url(service_url: str, collection: str, bbox: list[float]) -> str:
    query = urllib.parse.urlencode({
        "bbox": ",".join(str(value) for value in bbox),
        "limit": REQUEST_LIMIT,
        "f": "json",
    })
    return f"{service_url}/collections/{collection}/items?{query}"


def split_bbox(bbox: list[float]) -> tuple[list[float], list[float]]:
    west, south, east, north = bbox
    if east - west >= north - south:
        middle = (west + east) / 2
        return [west, south, middle, north], [middle, south, east, north]
    middle = (south + north) / 2
    return [west, south, east, middle], [west, middle, east, north]


def download_collection(
    service_url: str,
    collection: str,
    bbox: list[float],
    api_key: str,
    depth: int = 0,
    initial_split_depth: int = 0,
) -> list[dict]:
    if depth < initial_split_depth:
        first, second = split_bbox(bbox)
        return (
            download_collection(
                service_url, collection, first, api_key, depth + 1, initial_split_depth
            )
            + download_collection(
                service_url, collection, second, api_key, depth + 1, initial_split_depth
            )
        )
    result = request_json(collection_url(service_url, collection, bbox), api_key)
    features = result.get("features", [])
    if len(features) < REQUEST_LIMIT:
        return features
    if depth >= 8:
        raise RuntimeError(f"Collection {collection} still reaches the limit at {bbox}")
    first, second = split_bbox(bbox)
    return (
        download_collection(
            service_url, collection, first, api_key, depth + 1, initial_split_depth
        )
        + download_collection(
            service_url, collection, second, api_key, depth + 1, initial_split_depth
        )
    )


def feature_identifier(feature: dict) -> str:
    properties = feature.get("properties", {})
    return str(properties.get("kmtk_id") or feature.get("id") or hash(json.dumps(feature)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--area", default="pilot-archipelago-sea")
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--api-key-file", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    manifest = load_manifest()
    area = area_config(manifest, args.area)
    source = source_config(manifest, args.source)
    api_key = read_api_key(args.api_key_file)
    output = args.output or REPO_ROOT / "raw" / "landcover" / args.source / f"{args.area}.geojson"
    if output.exists() and not args.force:
        raise FileExistsError(f"{output} already exists; use --force to replace it")

    all_features = []
    counts = {}
    seen = set()
    for collection, normalized_class in source["collection_mapping"].items():
        features = download_collection(
            source["service_url"],
            collection,
            area["bbox_wgs84"],
            api_key,
            initial_split_depth=INITIAL_SPLIT_DEPTHS.get(collection, 0),
        )
        added = 0
        for feature in features:
            identifier = feature_identifier(feature)
            dedupe_key = (collection, identifier)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            properties = feature.setdefault("properties", {})
            properties["source_collection"] = collection
            properties["class"] = normalized_class
            all_features.append(feature)
            added += 1
        counts[collection] = added
        print(f"{collection}: {added}", flush=True)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({
        "type": "FeatureCollection",
        "name": "kmtk-landcover",
        "features": all_features,
    }, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    receipt = {
        "downloaded_at": datetime.now(UTC).isoformat(),
        "area": args.area,
        "source": args.source,
        "bbox_wgs84": area["bbox_wgs84"],
        "collections": counts,
        "features": len(all_features),
        "bytes": output.stat().st_size,
        "output": str(output.relative_to(REPO_ROOT)),
    }
    output.with_suffix(".receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
