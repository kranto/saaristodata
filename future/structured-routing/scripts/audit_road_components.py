#!/usr/bin/env python3
"""Find likely missing road-component memberships near known pier points."""

from __future__ import annotations

import argparse
import json
import math
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from build_road_network import (
    DEFAULT_CACHE,
    DEFAULT_COMPONENTS,
    DEFAULT_PIERS,
    DEFAULT_ROUTER,
    SSL_CONTEXT,
    load_piers,
    normalized_route,
    request_route,
    route_key,
)


EXPERIMENT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = EXPERIMENT / "road-network-audit.json"
DEFAULT_LOCATE_CACHE = EXPERIMENT / ".road-locate-cache.json"


def haversine_m(a: dict, b: dict) -> float:
    lat1, lat2 = math.radians(a["lat"]), math.radians(b["lat"])
    d_lat = lat2 - lat1
    d_lon = math.radians(b["lon"] - a["lon"])
    value = math.sin(d_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(d_lon / 2) ** 2
    return 12_742_000 * math.asin(math.sqrt(value))


def locate(router: str, locations: list[dict]) -> list[dict]:
    payload = {
        "locations": [
            {
                "lat": item["lat"], "lon": item["lon"],
                "minimum_reachability": 0,
                "radius": 500,
                "search_filter": {"exclude_ferry": True},
            }
            for item in locations
        ],
        "costing": "auto",
        "verbose": False,
    }
    url = router.replace("/route", "/locate") + "?" + urllib.parse.urlencode(
        {"json": json.dumps(payload, separators=(",", ":"))}
    )
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=45, context=SSL_CONTEXT) as response:
                return json.load(response)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            if attempt == 4:
                raise RuntimeError(f"locate failed: {exc}") from exc
            time.sleep(1.5 * (2 ** attempt))
    raise AssertionError("unreachable")


def snap_distance_m(point: dict, locate_result: dict) -> int | None:
    distances = []
    for edge in locate_result.get("edges", []):
        correlated = {"lat": edge.get("correlated_lat"), "lon": edge.get("correlated_lon")}
        if correlated["lat"] is not None and correlated["lon"] is not None:
            distances.append(haversine_m(point, correlated))
    for node in locate_result.get("nodes", []):
        if node.get("lat") is not None and node.get("lon") is not None:
            distances.append(haversine_m(point, node))
    return round(min(distances)) if distances else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--piers", type=Path, default=DEFAULT_PIERS)
    parser.add_argument("--components", type=Path, default=DEFAULT_COMPONENTS)
    parser.add_argument("--route-cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--locate-cache", type=Path, default=DEFAULT_LOCATE_CACHE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--router", default=DEFAULT_ROUTER)
    parser.add_argument("--nearest", type=int, default=3)
    parser.add_argument("--max-air-distance-km", type=float, default=10)
    parser.add_argument("--max-snap-distance-m", type=float, default=250)
    parser.add_argument("--request-delay", type=float, default=0.02)
    args = parser.parse_args()

    piers = load_piers(args.piers)
    components_data = json.loads(args.components.read_text())
    piers.update(components_data.get("additionalPiers", {}))
    component_by_pier = {
        pier: component["id"]
        for component in components_data["components"]
        for pier in component["piers"]
    }

    locate_cache = json.loads(args.locate_cache.read_text()) if args.locate_cache.exists() else {}
    missing_locates = [ref for ref in sorted(piers) if ref not in locate_cache]
    for offset in range(0, len(missing_locates), 25):
        refs = missing_locates[offset:offset + 25]
        results = locate(args.router, [piers[ref] for ref in refs])
        for ref, result in zip(refs, results):
            locate_cache[ref] = result
        args.locate_cache.write_text(json.dumps(locate_cache, ensure_ascii=False))
        print(f"located road snaps: {min(offset + len(refs), len(missing_locates))}/{len(missing_locates)}", flush=True)
        time.sleep(args.request_delay)

    def component_key(ref: str) -> str:
        return component_by_pier.get(ref, f"singleton:{ref}")

    pairs: set[tuple[str, str]] = set()
    for ref, point in piers.items():
        candidates = sorted(
            (haversine_m(point, other_point), other_ref)
            for other_ref, other_point in piers.items()
            if other_ref != ref and component_key(other_ref) != component_key(ref)
        )[:args.nearest]
        for distance_m, other_ref in candidates:
            if distance_m <= args.max_air_distance_km * 1000:
                pairs.add(tuple(sorted((ref, other_ref))))

    route_cache = json.loads(args.route_cache.read_text()) if args.route_cache.exists() else {}
    checks = []
    new_requests = 0
    for index, (from_id, to_id) in enumerate(sorted(pairs), start=1):
        key = route_key("auto", from_id, to_id, piers[from_id], piers[to_id])
        if key not in route_cache:
            route_cache[key] = request_route(args.router, "auto", piers[from_id], piers[to_id])
            args.route_cache.write_text(json.dumps(route_cache, ensure_ascii=False))
            new_requests += 1
            if new_requests == 1 or new_requests % 25 == 0:
                print(f"audit routes: {new_requests} new; pair {index}/{len(pairs)}", flush=True)
            time.sleep(args.request_delay)
        result = normalized_route(route_cache[key])
        from_snap = snap_distance_m(piers[from_id], locate_cache[from_id])
        to_snap = snap_distance_m(piers[to_id], locate_cache[to_id])
        if result["status"] != "ok":
            classification = "not_connected_without_ferry"
        elif from_snap is None or to_snap is None:
            classification = "uncertain_missing_road_snap"
        elif max(from_snap, to_snap) > args.max_snap_distance_m:
            classification = "uncertain_far_road_snap"
        else:
            classification = "possible_missing_same_road_component"
        checks.append({
            "from": from_id,
            "to": to_id,
            "fromComponent": component_by_pier.get(from_id),
            "toComponent": component_by_pier.get(to_id),
            "airDistanceMeters": round(haversine_m(piers[from_id], piers[to_id])),
            "fromRoadSnapDistanceMeters": from_snap,
            "toRoadSnapDistanceMeters": to_snap,
            "classification": classification,
            "route": result,
        })

    possible = [item for item in checks if item["classification"] == "possible_missing_same_road_component"]
    uncertain = [item for item in checks if item["classification"].startswith("uncertain_")]
    output = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "method": {
            "candidateRule": f"{args.nearest} nearest piers outside asserted component, max {args.max_air_distance_km:g} km",
            "routeRule": "auto route with ferry edges excluded both when snapping endpoints and on the route",
            "snapRule": f"both pier points must be within {args.max_snap_distance_m:g} m of an auto-routable non-ferry edge",
            "warning": "Candidates are leads for review, not automatic component merges.",
        },
        "statistics": {
            "pierCount": len(piers),
            "assertedComponentPierCount": len(component_by_pier),
            "singletonPierCount": len(piers) - len(component_by_pier),
            "candidatePairCount": len(checks),
            "possibleMissingConnectionCount": len(possible),
            "uncertainCount": len(uncertain),
            "newRouterRequestCount": new_requests,
        },
        "possibleMissingConnections": possible,
        "uncertainConnections": uncertain,
        "checks": checks,
    }
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(output["statistics"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
