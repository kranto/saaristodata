#!/usr/bin/env python3
"""Build the stop-coordinate lookup used with an external road router.

The public application data still calls these objects ``pier`` features.  The
structured-routing experiment uses the more general word ``stop`` because a
boarding place may physically be a ramp, quay, terminal, pier, or shoreline.

Maintained road components contain groups of stops connected without a ferry.
A known stop outside those groups forms a singleton road area of its own.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT = Path(__file__).resolve().parents[1]
DEFAULT_STOPS = ROOT.parent / "saaristolautat" / "public" / "data" / "saaristo.json"
DEFAULT_COMPONENTS = EXPERIMENT / "road-components.json"
DEFAULT_OUTPUT = EXPERIMENT / "external-routing-stop-index.json"


def load_known_stops(path: Path) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    stops = {}
    for feature in data["features"]:
        properties = feature.get("properties", {})
        coordinates = feature.get("geometry", {}).get("coordinates")
        if properties.get("stype") != "pier" or not properties.get("ref"):
            continue
        if not coordinates or len(coordinates) != 2:
            continue
        stop_id = properties["ref"]
        stops[stop_id] = {
            "id": stop_id,
            "coordinates": {"lon": coordinates[0], "lat": coordinates[1]},
            "coordinateSource": "saaristolautat/public/data/saaristo.json",
        }
    return stops


def build(stops_path: Path, components_path: Path) -> dict:
    components_data = json.loads(components_path.read_text())
    stops = load_known_stops(stops_path)
    preferred_names = components_data.get("preferredNames", {})

    for stop_id, point in components_data.get("additionalPiers", {}).items():
        stops[stop_id] = {
            "id": stop_id,
            "coordinates": {"lon": point["lon"], "lat": point["lat"]},
            "coordinateSource": point.get("source", "road-components.json additional stop"),
        }

    component_by_stop: dict[str, str] = {}
    for component in components_data["components"]:
        for stop_id in component["piers"]:
            previous = component_by_stop.get(stop_id)
            if previous and previous != component["id"]:
                raise ValueError(
                    f"stop {stop_id} belongs to multiple road components: "
                    f"{previous}, {component['id']}"
                )
            component_by_stop[stop_id] = component["id"]

    missing_coordinates = sorted(set(component_by_stop) - set(stops))
    if missing_coordinates:
        raise ValueError(
            "road component stops without coordinates: " + ", ".join(missing_coordinates)
        )

    for stop_id, stop in stops.items():
        stop["name"] = preferred_names.get(stop_id, stop_id)
        component_id = component_by_stop.get(stop_id)
        if component_id:
            stop["roadAreaId"] = component_id
            stop["roadAreaKind"] = "maintained_component"
        else:
            stop["roadAreaId"] = f"stop:{stop_id}"
            stop["roadAreaKind"] = "singleton_stop"

    return {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "description": (
            "Known water-transport stops used to map external-router ferry "
            "boarding coordinates to the internal ferry-free road areas."
        ),
        "matchingPolicy": {
            "method": "nearest_known_stop",
            "maximumDistanceMeters": 500,
            "roadAreaDetection": (
                "scan ferry boardings from the query origin and use the first "
                "boarding whose nearest known stop is within the maximum distance"
            ),
            "unknownEarlierFerries": "ignored",
            "arrivalStopRequired": False,
        },
        "stops": sorted(stops.values(), key=lambda item: item["id"]),
        "statistics": {
            "stopCount": len(stops),
            "maintainedComponentStopCount": sum(
                stop["roadAreaKind"] == "maintained_component" for stop in stops.values()
            ),
            "singletonStopCount": sum(
                stop["roadAreaKind"] == "singleton_stop" for stop in stops.values()
            ),
            "maintainedRoadAreaCount": len(components_data["components"]),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stops", type=Path, default=DEFAULT_STOPS)
    parser.add_argument("--components", type=Path, default=DEFAULT_COMPONENTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    result = build(args.stops, args.components)
    if args.check:
        existing = json.loads(args.output.read_text())
        result["generatedAt"] = existing.get("generatedAt")
        if result != existing:
            raise SystemExit(f"out of date: {args.output}")
        return 0

    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        f"wrote {args.output}: {result['statistics']['stopCount']} stops, "
        f"{result['statistics']['maintainedRoadAreaCount']} maintained road areas"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
