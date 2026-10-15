#!/usr/bin/env python3
"""Classify internal calls that still lack a published or historical time."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "connection-arrival-prediction-catalog.json"
DEFAULT_LINK_REPORT = ROOT / "connection-ais-estimate-link-report.json"
DEFAULT_OUTPUT = ROOT / "route-query-timing-audit.json"


def remediation(outcomes: dict) -> str:
    if outcomes.get("no_ais_source"):
        return "keep_unknown_no_ais_source"
    if outcomes.get("missing_departure_anchor"):
        return "add_or_recover_departure_anchor_before_matching"
    if outcomes.get("no_compatible_historical_path"):
        return "review_historical_path_compatibility"
    if outcomes.get("incompatible_with_next_published_time"):
        return "keep_unknown_due_to_published_time_constraint"
    return "review_source_and_matching"


def build_audit(catalog: dict, link_report: dict) -> dict:
    link_by_route = {item["routeId"]: item for item in link_report["routes"]}
    missing_by_route: dict[str, Counter] = {}
    service_kind_counts: dict[str, Counter] = {}
    for trip in catalog["trips"]:
        # The first call is the departure anchor. The user-facing coverage
        # question concerns later calls whose arrival/departure must be shown.
        for call in trip.get("calls", [])[1:]:
            if call.get("timing", {}).get("kind") != "unavailable":
                continue
            route_id = trip["routeId"]
            missing_by_route.setdefault(route_id, Counter())[call["stop"]] += 1
            service_kind_counts.setdefault(route_id, Counter())[trip["serviceKind"]] += 1

    routes = []
    for route_id, stops in missing_by_route.items():
        link = link_by_route.get(route_id, {})
        outcomes = link.get("outcomes", {})
        routes.append({
            "routeId": route_id,
            "unavailableInternalCalls": sum(stops.values()),
            "affectedStops": [
                {"stopId": stop, "calls": count}
                for stop, count in stops.most_common()
            ],
            "serviceKinds": dict(sorted(service_kind_counts[route_id].items())),
            "linkOutcomes": outcomes,
            "recommendedAction": remediation(outcomes),
        })
    routes.sort(key=lambda item: (-item["unavailableInternalCalls"], item["routeId"]))
    total = sum(item["unavailableInternalCalls"] for item in routes)
    known_no_ais = sum(
        item["unavailableInternalCalls"]
        for item in routes
        if item["recommendedAction"] == "keep_unknown_no_ais_source"
    )
    return {
        "status": "experimental_timing_coverage_audit",
        "scope": "internal calls after each trip departure anchor",
        "summary": {
            "unavailableInternalCalls": total,
            "knownNoAisSourceCalls": known_no_ais,
            "actionableOrReviewableCalls": total - known_no_ais,
            "affectedRoutes": len(routes),
        },
        "routes": routes,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--link-report", type=Path, default=DEFAULT_LINK_REPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    audit = build_audit(
        json.loads(args.catalog.read_text()),
        json.loads(args.link_report.read_text()),
    )
    args.output.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(audit["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
