#!/usr/bin/env python3
"""Build ferry-free pier-to-pier road transfers with a Valhalla router.

The component file is the maintained assertion. This script validates every
directed pair in every component for both car and bicycle and refuses to mark a
route usable if Valhalla reports that the path contains a ferry.
"""

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


ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT = Path(__file__).resolve().parents[1]
DEFAULT_PIERS = ROOT.parent / "saaristolautat" / "public" / "data" / "saaristo.json"
DEFAULT_COMPONENTS = EXPERIMENT / "road-components.json"
DEFAULT_OUTPUT = EXPERIMENT / "road-network.json"
DEFAULT_CACHE = EXPERIMENT / ".road-routing-cache.json"
DEFAULT_ROUTER = "https://valhalla1.openstreetmap.de/route"
PROFILES = ("auto", "bicycle")
ROUTING_ONLY_POINTS = {
    # A neutral mainland waypoint prevents the public Valhalla instance's
    # 150 km bicycle limit from forcing a detour through a coastal pier.
    "Salo": {"lat": 60.3833, "lon": 23.1333},
}
SSL_CONTEXT = ssl.create_default_context(cafile="/etc/ssl/cert.pem")


def load_piers(path: Path) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    piers = {}
    for feature in data["features"]:
        properties = feature.get("properties", {})
        if properties.get("stype") != "pier" or not properties.get("ref"):
            continue
        coordinates = feature.get("geometry", {}).get("coordinates")
        if not coordinates or len(coordinates) != 2:
            continue
        piers[properties["ref"]] = {
            "lon": coordinates[0],
            "lat": coordinates[1],
        }
    return piers


def request_route(router: str, profile: str, start: dict, end: dict, retries: int = 5) -> dict:
    payload = {
        "locations": [
            {
                "lat": start["lat"], "lon": start["lon"], "type": "break",
                "minimum_reachability": 0,
                "radius": 500,
                "search_filter": {"exclude_ferry": True},
            },
            {
                "lat": end["lat"], "lon": end["lon"], "type": "break",
                "minimum_reachability": 0,
                "radius": 500,
                "search_filter": {"exclude_ferry": True},
            },
        ],
        "costing": profile,
        "costing_options": {
            profile: {
                # The public server does not permit hard excludes. A zero
                # preference plus the maximum entry cost strongly selects a
                # road-only alternative when one exists; has_ferry is still
                # checked on every returned route.
                "use_ferry": 0,
                "ferry_cost": 43200,
            }
        },
        "directions_options": {"units": "kilometers", "directions_type": "none"},
    }
    url = router + "?" + urllib.parse.urlencode({"json": json.dumps(payload, separators=(",", ":"))})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=45, context=SSL_CONTEXT) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code == 400:
                return {
                    "routing_error": {
                        "httpStatus": exc.code,
                        "body": body,
                    }
                }
            if attempt + 1 == retries:
                raise RuntimeError(f"routing failed after {retries} attempts: {exc}") from exc
            time.sleep(1.5 * (2 ** attempt))
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt + 1 == retries:
                raise RuntimeError(f"routing failed after {retries} attempts: {exc}") from exc
            time.sleep(1.5 * (2 ** attempt))
    raise AssertionError("unreachable")


def route_key(profile: str, from_id: str, to_id: str, start: dict, end: dict) -> str:
    return "|".join([
        "local-road-snap-v3", profile, from_id, to_id,
        f'{start["lat"]:.7f},{start["lon"]:.7f}',
        f'{end["lat"]:.7f},{end["lon"]:.7f}',
    ])


def normalized_route(result: dict) -> dict:
    if "routing_error" in result:
        error = result["routing_error"]
        return {
            "status": "route_not_found",
            "httpStatus": error.get("httpStatus"),
            "error": error.get("body"),
        }
    trip = result["trip"]
    summary = trip["summary"]
    leg_summaries = [leg["summary"] for leg in trip.get("legs", [])]
    has_ferry = bool(summary.get("has_ferry") or any(item.get("has_ferry") for item in leg_summaries))
    seconds = float(summary["time"])
    distance_km = float(summary["length"])
    return {
        "status": "ferry_used_rejected" if has_ferry else "ok",
        "distanceMeters": round(distance_km * 1000),
        "durationSeconds": round(seconds),
        "displayMinutes": max(1, math.ceil(seconds / 60)),
        "hasHighway": bool(summary.get("has_highway")),
    }


def resolve_distance_limit_routes(
    transfers: list[dict], components: list[dict], piers: dict[str, dict],
    cache: dict, args: argparse.Namespace,
) -> int:
    """Join two successful legs when the public router rejects a long bicycle route.

    Valhalla's public instance caps bicycle paths at 150 km. Every stitched
    result remains a real, ferry-free routed path; the selected component pier
    is recorded so the small possible detour stays visible to reviewers.
    """
    results = {
        (transfer["componentId"], transfer["from"], transfer["to"], profile): result
        for transfer in transfers
        for profile, result in transfer["modes"].items()
    }
    component_piers = {component["id"]: component["piers"] for component in components}
    new_requests = 0

    def routed_leg(profile: str, from_id: str, to_id: str, start: dict, end: dict) -> dict:
        nonlocal new_requests
        key = route_key(profile, from_id, to_id, start, end)
        if key not in cache:
            cache[key] = request_route(args.router, profile, start, end)
            args.cache.write_text(json.dumps(cache, ensure_ascii=False))
            new_requests += 1
            if args.request_delay:
                time.sleep(args.request_delay)
        return normalized_route(cache[key])

    for transfer in transfers:
        component_id = transfer["componentId"]
        for profile, result in list(transfer["modes"].items()):
            if result.get("status") != "route_not_found" or '"error_code":154' not in result.get("error", ""):
                continue
            candidates = []
            for via, point in ROUTING_ONLY_POINTS.items():
                first = routed_leg(profile, transfer["from"], f"routing:{via}", piers[transfer["from"]], point)
                second = routed_leg(profile, f"routing:{via}", transfer["to"], point, piers[transfer["to"]])
                if first.get("status") == "ok" and second.get("status") == "ok":
                    candidates.append((first["durationSeconds"] + second["durationSeconds"], via, first, second))
            for via in component_piers[component_id]:
                if via in (transfer["from"], transfer["to"]):
                    continue
                first = results.get((component_id, transfer["from"], via, profile))
                second = results.get((component_id, via, transfer["to"], profile))
                if not first or not second or first.get("status") != "ok" or second.get("status") != "ok":
                    continue
                candidates.append((first["durationSeconds"] + second["durationSeconds"], via, first, second))
            if not candidates:
                continue
            seconds, via, first, second = min(candidates)
            stitched = {
                "status": "ok",
                "distanceMeters": first["distanceMeters"] + second["distanceMeters"],
                "durationSeconds": seconds,
                "displayMinutes": max(1, math.ceil(seconds / 60)),
                "hasHighway": bool(first.get("hasHighway") or second.get("hasHighway")),
                "routingVia": via,
                "routingNote": "two ferry-free routes joined because the router limits bicycle paths to 150 km",
            }
            transfer["modes"][profile] = stitched
            results[(component_id, transfer["from"], transfer["to"], profile)] = stitched
    return new_requests


def build(args: argparse.Namespace) -> dict:
    components_data = json.loads(args.components.read_text())
    piers = load_piers(args.piers)
    piers.update(components_data.get("additionalPiers", {}))
    routing_piers = {ref: dict(point) for ref, point in piers.items()}
    routing_piers.update(components_data.get("routingCoordinateOverrides", {}))
    cache = json.loads(args.cache.read_text()) if args.cache.exists() else {}
    requested = {pier for component in components_data["components"] for pier in component["piers"]}
    missing = sorted(requested - set(piers))
    if missing:
        raise SystemExit(f"pier coordinates missing: {', '.join(missing)}")

    transfers = []
    request_count = 0
    mode_result_count = 0
    for component in components_data["components"]:
        component_piers = component["piers"]
        component_profiles = tuple(component.get("modes", PROFILES))
        for from_id in component_piers:
            for to_id in component_piers:
                if from_id == to_id:
                    continue
                modes = {}
                for profile in component_profiles:
                    mode_result_count += 1
                    key = route_key(profile, from_id, to_id, routing_piers[from_id], routing_piers[to_id])
                    if key not in cache:
                        cache[key] = request_route(args.router, profile, routing_piers[from_id], routing_piers[to_id])
                        args.cache.write_text(json.dumps(cache, ensure_ascii=False))
                        request_count += 1
                        if request_count == 1 or request_count % 25 == 0:
                            print(
                                f"router requests: {request_count} "
                                f"({component['id']}: {from_id} -> {to_id}, {profile})",
                                flush=True,
                            )
                        if args.request_delay:
                            time.sleep(args.request_delay)
                    try:
                        modes[profile] = normalized_route(cache[key])
                    except (KeyError, TypeError, ValueError) as exc:
                        modes[profile] = {"status": "routing_response_invalid", "error": str(exc)}
                transfers.append({
                    "componentId": component["id"],
                    "from": from_id,
                    "to": to_id,
                    "modes": modes,
                })

    request_count += resolve_distance_limit_routes(
        transfers, components_data["components"], routing_piers, cache, args,
    )
    failures = [
        {
            "componentId": transfer["componentId"],
            "from": transfer["from"],
            "to": transfer["to"],
            "profile": profile,
            "result": result,
        }
        for transfer in transfers
        for profile, result in transfer["modes"].items()
        if result["status"] != "ok"
    ]

    return {
        "schemaVersion": 1,
        "status": "review_required" if failures else "routing_validated",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": {
            "pierCoordinates": str(args.piers),
            "roadData": "OpenStreetMap via configured Valhalla instance",
            "router": args.router,
            "ferryAvoidance": {"use_ferry": 0, "ferry_cost": 43200},
            "locationSearchFilter": {"exclude_ferry": True},
            "locationCorrelation": {"minimum_reachability": 0, "radius_metres": 500},
            "acceptanceRule": "trip.summary.has_ferry and every leg.summary.has_ferry must be false",
        },
        "components": components_data["components"],
        "preferredNames": components_data.get("preferredNames", {}),
        "pierCoordinates": {pier: piers[pier] for pier in sorted(requested)},
        "routingCoordinateOverrides": {
            pier: components_data["routingCoordinateOverrides"][pier]
            for pier in sorted(requested & set(components_data.get("routingCoordinateOverrides", {})))
        },
        "transfers": transfers,
        "failures": failures,
        "statistics": {
            "componentCount": len(components_data["components"]),
            "pierCount": len(requested),
            "directedTransferCount": len(transfers),
            "modeResultCount": mode_result_count,
            "failureCount": len(failures),
            "newRouterRequestCount": request_count,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--piers", type=Path, default=DEFAULT_PIERS)
    parser.add_argument("--components", type=Path, default=DEFAULT_COMPONENTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--router", default=DEFAULT_ROUTER)
    parser.add_argument("--request-delay", type=float, default=0.05)
    args = parser.parse_args()
    data = build(args)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(data["statistics"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
