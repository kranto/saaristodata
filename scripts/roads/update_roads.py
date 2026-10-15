#!/usr/bin/env python3
"""Fetch/import selected road routes and merge them into roads.json.

Only Python's standard library is required. See scripts/roads/README.md for the workflow.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


DEFAULT_ROADS = Path(__file__).resolve().parents[2] / "roads.json"
DEFAULT_CACHE = Path(__file__).resolve().parent / ".cache"
OSRM_URL = "https://router.project-osrm.org"


class RoadImportError(RuntimeError):
    pass


def load_json(path: Path) -> Any:
    try:
        with path.open(encoding="utf-8-sig") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise RoadImportError(f"Cannot read JSON {path}: {error}") from error


def validate_route(route: dict[str, Any]) -> None:
    missing = [key for key in ("id", "name", "minZ", "maxZ", "source") if key not in route]
    if missing:
        raise RoadImportError(f"Route is missing fields {', '.join(missing)}: {route}")
    if not isinstance(route["id"], str) or not route["id"].strip():
        raise RoadImportError("Route id must be a non-empty string")
    if not isinstance(route["name"], str) or not route["name"].strip():
        raise RoadImportError(f"Route {route['id']}: name must be a non-empty string")
    if not isinstance(route["minZ"], int) or not isinstance(route["maxZ"], int):
        raise RoadImportError(f"Route {route['id']}: minZ and maxZ must be integers")
    if route["minZ"] > route["maxZ"]:
        raise RoadImportError(f"Route {route['id']}: minZ cannot exceed maxZ")
    source = route["source"]
    if not isinstance(source, dict) or source.get("type") not in ("osrm", "file"):
        raise RoadImportError(f"Route {route['id']}: source.type must be 'osrm' or 'file'")


def normalize_coordinate(value: Any, route_id: str) -> list[float]:
    if not isinstance(value, list) or len(value) < 2:
        raise RoadImportError(f"Route {route_id}: invalid coordinate {value!r}")
    try:
        first, second = float(value[0]), float(value[1])
    except (TypeError, ValueError) as error:
        raise RoadImportError(f"Route {route_id}: invalid coordinate {value!r}") from error
    if first < 40 < second:
        lon, lat = first, second
    elif second < 40 < first:
        lon, lat = second, first
    else:
        raise RoadImportError(
            f"Route {route_id}: cannot determine lat/lon order for {value!r}; "
            "one value must be below 40 (lon) and the other above 40 (lat)"
        )
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        raise RoadImportError(f"Route {route_id}: coordinate outside lon/lat bounds: {value!r}")
    return [round(lon, 6), round(lat, 6)]


def clean_coordinates(values: Any, route_id: str) -> list[list[float]]:
    if not isinstance(values, list):
        raise RoadImportError(f"Route {route_id}: coordinates must be an array")
    result: list[list[float]] = []
    for value in values:
        coordinate = normalize_coordinate(value, route_id)
        if not result or coordinate != result[-1]:
            result.append(coordinate)
    if len(result) < 2:
        raise RoadImportError(f"Route {route_id}: a road needs at least two distinct coordinates")
    return result


def read_geojson(path: Path, route_id: str) -> list[list[float]]:
    data = load_json(path)
    geometries: list[dict[str, Any]] = []
    if data.get("type") == "FeatureCollection":
        geometries = [item.get("geometry") or {} for item in data.get("features", [])]
    elif data.get("type") == "Feature":
        geometries = [data.get("geometry") or {}]
    elif data.get("type") in ("LineString", "MultiLineString"):
        geometries = [data]
    else:
        raise RoadImportError(f"Route {route_id}: unsupported GeoJSON root in {path}")

    lines: list[list[list[float]]] = []
    for geometry in geometries:
        if geometry.get("type") == "LineString":
            lines.append(clean_coordinates(geometry.get("coordinates"), route_id))
        elif geometry.get("type") == "MultiLineString":
            lines.extend(clean_coordinates(line, route_id) for line in geometry.get("coordinates", []))
    if not lines:
        raise RoadImportError(f"Route {route_id}: {path} contains no LineString geometry")
    return join_lines(lines, route_id)


def read_gpx(path: Path, route_id: str) -> list[list[float]]:
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as error:
        raise RoadImportError(f"Route {route_id}: cannot read GPX {path}: {error}") from error
    points = root.findall(".//{*}trkpt") or root.findall(".//{*}rtept")
    coordinates = [[point.attrib.get("lon"), point.attrib.get("lat")] for point in points]
    return clean_coordinates(coordinates, route_id)


def distance_squared(a: list[float], b: list[float]) -> float:
    latitude_scale = math.cos(math.radians((a[1] + b[1]) / 2))
    return ((a[0] - b[0]) * latitude_scale) ** 2 + (a[1] - b[1]) ** 2


def join_lines(lines: list[list[list[float]]], route_id: str) -> list[list[float]]:
    """Join route parts by the nearest remaining endpoint."""
    result = list(lines.pop(0))
    while lines:
        candidates: list[tuple[float, int, bool, bool]] = []
        for index, line in enumerate(lines):
            candidates.extend([
                (distance_squared(result[-1], line[0]), index, False, False),
                (distance_squared(result[-1], line[-1]), index, True, False),
                (distance_squared(result[0], line[-1]), index, False, True),
                (distance_squared(result[0], line[0]), index, True, True),
            ])
        _, index, reverse, prepend = min(candidates)
        line = lines.pop(index)
        if reverse:
            line.reverse()
        if prepend:
            result = line[:-1] + result if line[-1] == result[0] else line + result
        else:
            result.extend(line[1:] if result[-1] == line[0] else line)
    return clean_coordinates(result, route_id)


def fetch_osrm(route: dict[str, Any], cache_path: Path, base_url: str) -> list[list[float]]:
    route_id = route["id"]
    via = route["source"].get("via")
    if not isinstance(via, list) or len(via) < 2:
        raise RoadImportError(f"Route {route_id}: OSRM source needs at least two via coordinates")
    coordinates = [normalize_coordinate(value, route_id) for value in via]
    coordinate_path = ";".join(f"{lon},{lat}" for lon, lat in coordinates)
    query = urlencode({"overview": "full", "geometries": "geojson", "steps": "false"})
    url = f"{base_url.rstrip('/')}/route/v1/driving/{coordinate_path}?{query}"
    request = Request(url, headers={"User-Agent": "saaristolautat-road-import/1.0"})
    try:
        with urlopen(request, timeout=60) as response:
            payload = json.load(response)
    except HTTPError as error:
        raise RoadImportError(f"Route {route_id}: OSRM request failed: HTTP {error.code} {error.reason}") from error
    except URLError as error:
        if "CERTIFICATE_VERIFY_FAILED" not in str(error):
            raise RoadImportError(f"Route {route_id}: OSRM request failed: {error}") from error
        try:
            response = subprocess.run(
                [
                    "curl", "--fail", "--silent", "--show-error", "--location",
                    "--max-time", "60", "--user-agent", "saaristolautat-road-import/1.0", url
                ],
                check=True, capture_output=True, text=True
            )
            payload = json.loads(response.stdout)
            print(f"Route {route_id}: Python certificate check failed; used system curl instead")
        except FileNotFoundError as curl_error:
            raise RoadImportError(
                f"Route {route_id}: Python certificate check failed and curl is not installed"
            ) from curl_error
        except (subprocess.CalledProcessError, json.JSONDecodeError) as curl_error:
            details = getattr(curl_error, "stderr", "").strip()
            raise RoadImportError(f"Route {route_id}: curl fallback failed: {details or curl_error}") from curl_error
    except (TimeoutError, json.JSONDecodeError) as error:
        raise RoadImportError(f"Route {route_id}: OSRM request failed: {error}") from error
    if payload.get("code") != "Ok" or not payload.get("routes"):
        raise RoadImportError(f"Route {route_id}: OSRM returned {payload.get('code')}: {payload.get('message', '')}")
    geometry = payload["routes"][0].get("geometry") or {}
    result = clean_coordinates(geometry.get("coordinates"), route_id)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps({"type": "LineString", "coordinates": result}, ensure_ascii=False), encoding="utf-8")
    return result


def route_coordinates(route: dict[str, Any], manifest_dir: Path, cache_dir: Path, refresh: bool, base_url: str) -> list[list[float]]:
    source = route["source"]
    route_id = route["id"]
    if source["type"] == "file":
        if not source.get("path"):
            raise RoadImportError(f"Route {route_id}: file source needs path")
        path = (manifest_dir / source["path"]).resolve()
        if path.suffix.lower() == ".gpx":
            return read_gpx(path, route_id)
        return read_geojson(path, route_id)

    cache_path = cache_dir / f"{route_id}.geojson"
    if cache_path.exists() and not refresh:
        return read_geojson(cache_path, route_id)
    result = fetch_osrm(route, cache_path, base_url)
    time.sleep(1)
    return result


def feature_for(route: dict[str, Any], coordinates: list[list[float]]) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "sname": route["name"],
        "stype": "road",
        "minZ": route["minZ"],
        "maxZ": route["maxZ"],
        "roadImportId": route["id"],
    }
    identity = json.dumps([route["id"], coordinates], separators=(",", ":"), ensure_ascii=False)
    return {
        "type": "Feature",
        "properties": properties,
        "geometry": {"type": "LineString", "coordinates": coordinates},
        "id": hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32],
    }


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Road import manifest JSON")
    parser.add_argument("--roads", type=Path, default=DEFAULT_ROADS, help=f"roads.json path (default: {DEFAULT_ROADS})")
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE, help="OSRM response cache directory")
    parser.add_argument("--output", type=Path, help="Write a preview to this path instead of roads.json")
    parser.add_argument("--write", action="store_true", help="Update roads.json atomically")
    parser.add_argument("--refresh", action="store_true", help="Fetch OSRM routes again instead of using the cache")
    parser.add_argument("--only", action="append", default=[], help="Process only this route id (repeatable)")
    parser.add_argument("--osrm-url", default=OSRM_URL, help="OSRM server base URL")
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    if arguments.write and arguments.output:
        raise RoadImportError("Use either --write or --output, not both")
    manifest_path = arguments.manifest.resolve()
    manifest = load_json(manifest_path)
    routes = manifest.get("routes") if isinstance(manifest, dict) else None
    if not isinstance(routes, list):
        raise RoadImportError("Manifest root must contain a routes array")
    selected = []
    seen_ids: set[str] = set()
    for route in routes:
        if not isinstance(route, dict):
            raise RoadImportError(f"Invalid route entry: {route!r}")
        validate_route(route)
        if route["id"] in seen_ids:
            raise RoadImportError(f"Duplicate route id in manifest: {route['id']}")
        seen_ids.add(route["id"])
        if not arguments.only or route["id"] in arguments.only:
            selected.append(route)
    missing_only = sorted(set(arguments.only) - seen_ids)
    if missing_only:
        raise RoadImportError(f"Unknown --only route ids: {', '.join(missing_only)}")
    if not selected:
        raise RoadImportError("No routes selected")

    roads_path = arguments.roads.resolve()
    roads = load_json(roads_path)
    if roads.get("type") != "FeatureCollection" or not isinstance(roads.get("features"), list):
        raise RoadImportError(f"{roads_path} is not a GeoJSON FeatureCollection")

    imported = []
    for route in selected:
        coordinates = route_coordinates(route, manifest_path.parent, arguments.cache.resolve(), arguments.refresh, arguments.osrm_url)
        imported.append(feature_for(route, coordinates))
        print(f"Prepared {route['id']}: {route['name']} ({len(coordinates)} points, z{route['minZ']}–{route['maxZ']})")

    selected_ids = {route["id"] for route in selected}
    retained = [feature for feature in roads["features"] if feature.get("properties", {}).get("roadImportId") not in selected_ids]
    result = {**roads, "features": retained + imported}
    output_path = roads_path if arguments.write else (arguments.output or Path.cwd() / "roads.preview.json").resolve()
    write_json_atomic(output_path, result)
    action = "Updated" if arguments.write else "Wrote preview"
    print(f"{action}: {output_path}")
    print(f"Road features: {len(roads['features'])} -> {len(result['features'])}")
    if not arguments.write:
        print("Review the preview, then rerun with --write to update roads.json.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RoadImportError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2)
