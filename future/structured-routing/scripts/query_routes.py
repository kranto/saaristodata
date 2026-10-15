#!/usr/bin/env python3
"""Public JSON query interface for the experimental archipelago router."""

from __future__ import annotations

import argparse
import json
from datetime import date, time
from pathlib import Path

from route_itineraries import find_itineraries
from route_itinerary import DEFAULT_GRAPH, parse_clock


SCHEMA_VERSION = "1.0"


def timing_basis(itinerary: dict) -> dict:
    """Summarize whether an itinerary contains estimates or unknown call times."""
    historical = False
    conservative = False
    unknown_calls = []
    for leg in itinerary.get("legs", []):
        timing_objects = [leg.get("departureTiming"), leg.get("arrivalTiming")]
        timing_objects.extend(
            stop.get("timing") for stop in leg.get("intermediateStops", [])
        )
        for timing in timing_objects:
            status = (timing or {}).get("status")
            historical |= status == "historical_estimate"
            conservative |= status == "historical_range_only"
        for stop in leg.get("intermediateStops", []):
            if stop.get("timing") is None:
                unknown_calls.append(stop["id"])
    return {
        "usesHistoricalEstimate": historical,
        "usesConservativeHistoricalRange": conservative,
        "unknownIntermediateStopTimes": list(dict.fromkeys(unknown_calls)),
    }


def public_response(internal: dict, *, include_diagnostics: bool = False) -> dict:
    """Convert the search result into the stable application-facing contract."""
    itineraries = internal["results"]
    for itinerary in itineraries:
        itinerary["timingBasis"] = timing_basis(itinerary)
    response = {
        "schemaVersion": SCHEMA_VERSION,
        "status": internal["status"],
        "query": {
            "origin": internal["origin"],
            "destination": internal["destination"],
            "departureNotBefore": internal["departureNotBefore"],
            "arrivalDeadline": internal["arrivalDeadline"],
            "mode": internal["mode"],
            "timingProfile": internal["timingProfile"],
            "timeZone": "Europe/Helsinki",
        },
        "resultCount": len(itineraries),
        "itineraries": itineraries,
    }
    if not itineraries:
        response["outcomeReason"] = "no_itinerary_for_query"
    if include_diagnostics:
        response["diagnostics"] = internal["diagnostics"]
    return response


def query_routes(
    origin: str,
    destination: str,
    travel_date: date,
    start_time: time = time(0, 0),
    *,
    mode: str = "car",
    timing_profile: str = "typical",
    same_day: bool = False,
    max_results: int = 12,
    include_diagnostics: bool = False,
    graph_path: Path = DEFAULT_GRAPH,
) -> dict:
    internal = find_itineraries(
        origin,
        destination,
        travel_date,
        start_time,
        mode=mode,
        timing_profile=timing_profile,
        same_day=same_day,
        max_results=max_results,
        graph_path=graph_path,
    )
    return public_response(internal, include_diagnostics=include_diagnostics)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("origin")
    parser.add_argument("destination")
    parser.add_argument("travel_date", type=date.fromisoformat)
    parser.add_argument("start_time", type=parse_clock, nargs="?", default=time(0, 0))
    parser.add_argument("--mode", choices=("car", "motorcycle", "bicycle"), default="car")
    parser.add_argument("--timing-profile", choices=("typical", "conservative"), default="typical")
    parser.add_argument("--same-day", action="store_true")
    parser.add_argument("--max-results", type=int, default=12)
    parser.add_argument("--include-diagnostics", action="store_true")
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    args = parser.parse_args()
    try:
        response = query_routes(
            args.origin,
            args.destination,
            args.travel_date,
            args.start_time,
            mode=args.mode,
            timing_profile=args.timing_profile,
            same_day=args.same_day,
            max_results=args.max_results,
            include_diagnostics=args.include_diagnostics,
            graph_path=args.graph,
        )
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(response, ensure_ascii=False, indent=2))
    return 0 if response["status"] == "routes_found" else 2


if __name__ == "__main__":
    raise SystemExit(main())
