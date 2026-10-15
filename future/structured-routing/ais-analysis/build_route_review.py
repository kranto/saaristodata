#!/usr/bin/env python3
"""Build weekly route assignments, operating regimes, and review GeoJSON."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path


EARTH_RADIUS_M = 6_371_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("calls", type=Path, help="pier-calls.csv")
    parser.add_argument("unknown_cells", type=Path, help="unknown-stop-cells.csv")
    parser.add_argument("vessels", type=Path, help="MMSI summary CSV from prepare_ais.py")
    parser.add_argument("saaristo", type=Path, help="saaristo.json")
    parser.add_argument("data", type=Path, help="data.json")
    parser.add_argument("output", type=Path)
    parser.add_argument("--duplicate-call-minutes", type=int, default=30)
    parser.add_argument("--unknown-cluster-radius-m", type=float, default=300)
    parser.add_argument("--minimum-active-days", type=int, default=60)
    parser.add_argument("--livedata", type=Path)
    parser.add_argument("--route-ids", type=Path, help="JSON file with a routes array to retain")
    parser.add_argument("--vessel-names", type=Path, help="JSON object of MMSI-to-name overrides")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_vessel_names(path: Path | None) -> dict[int, str]:
    if not path:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    names = {}
    for feature in data.get("features", []):
        properties = feature.get("properties", {})
        vessel = properties.get("vessel") or {}
        mmsi = feature.get("mmsi") or properties.get("mmsi") or vessel.get("mmsi")
        name = str(vessel.get("name") or "").strip()
        if mmsi and name:
            names[int(mmsi)] = name
    return names


def load_name_overrides(path: Path | None) -> dict[int, str]:
    if not path:
        return {}
    return {
        int(mmsi): str(name).strip()
        for mmsi, name in json.loads(path.read_text(encoding="utf-8")).items()
        if str(name).strip()
    }


def vessel_labels(mmsis: set[int], names: dict[int, str]) -> str:
    return ";".join(sorted(names.get(mmsi, str(mmsi)) for mmsi in mmsis))


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def week_start(value: datetime) -> date:
    return value.date() - timedelta(days=value.weekday())


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    lat1r = math.radians(lat1)
    lat2r = math.radians(lat2)
    dlat = lat2r - lat1r
    dlng = math.radians(lng2 - lng1)
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1r) * math.cos(lat2r) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(value))


def load_reference(saaristo_path: Path, data_path: Path, retained_route_ids: set[str] | None):
    saaristo = json.loads(saaristo_path.read_text(encoding="utf-8-sig"))
    data = json.loads(data_path.read_text(encoding="utf-8-sig"))
    piers = {}
    connection_features = {}
    for feature in saaristo.get("features", []):
        properties = feature.get("properties", {})
        if properties.get("stype") == "pier" and feature.get("geometry", {}).get("type") == "Point":
            pier_id = properties.get("ref") or properties.get("sname")
            if pier_id:
                piers[pier_id] = feature
        if properties.get("stype") == "connection":
            route_id = properties.get("ref")
            if route_id:
                connection_features[route_id] = feature
    routes = {}
    for route_id, route in data.get("routes", {}).items():
        if route.get("obsolete"):
            continue
        if retained_route_ids is not None and route_id not in retained_route_ids:
            continue
        pier_ids = []
        for pier in route.get("piers", []):
            pier_id = pier.get("id") or pier.get("name")
            if pier_id in piers and pier_id not in pier_ids:
                pier_ids.append(pier_id)
        routes[route_id] = {
            "id": route_id,
            "name": route.get("name_fi") or route.get("name") or route_id,
            "piers": pier_ids,
        }
    return piers, routes, connection_features


def accepted_and_collapsed_calls(
    path: Path, duplicate_minutes: int, retained_mmsis: set[int]
) -> list[dict]:
    rows = [
        row
        for row in read_csv(path)
        if row.get("operational") == "1" and int(row["mmsi"]) in retained_mmsis
    ]
    rows.sort(key=lambda row: (int(row["mmsi"]), row["arrival_utc"]))
    collapsed = []
    maximum_gap = duplicate_minutes * 60
    for row in rows:
        row = dict(row)
        row["mmsi"] = int(row["mmsi"])
        row["arrival"] = parse_utc(row["arrival_utc"])
        row["departure"] = parse_utc(row["departure_utc"])
        if collapsed:
            previous = collapsed[-1]
            gap = (row["arrival"] - previous["departure"]).total_seconds()
            if row["mmsi"] == previous["mmsi"] and row["pier"] == previous["pier"] and 0 <= gap <= maximum_gap:
                previous["departure"] = max(previous["departure"], row["departure"])
                previous["departure_utc"] = previous["departure"].isoformat().replace("+00:00", "Z")
                previous["merged_calls"] += 1
                continue
        row["merged_calls"] = 1
        collapsed.append(row)
    return collapsed


def route_candidates(
    calls: list[dict], routes: dict[str, dict], names: dict[int, str]
) -> tuple[list[dict], dict]:
    grouped: dict[tuple[int, date], list[dict]] = defaultdict(list)
    for call in calls:
        grouped[(call["mmsi"], week_start(call["arrival"]))].append(call)
    output = []
    top_by_week = {}
    for (mmsi, week), week_calls in sorted(grouped.items()):
        pier_counts = Counter(call["pier"] for call in week_calls)
        observed_piers = set(pier_counts)
        transitions = Counter(
            (first["pier"], second["pier"])
            for first, second in zip(week_calls, week_calls[1:])
            if first["pier"] != second["pier"]
        )
        total_calls = sum(pier_counts.values())
        total_transitions = sum(transitions.values())
        candidates = []
        for route in routes.values():
            route_piers = set(route["piers"])
            matched_piers = route_piers & observed_piers
            if len(route_piers) < 2 or len(matched_piers) < 2:
                continue
            matched_calls = sum(pier_counts[pier] for pier in matched_piers)
            matched_transitions = sum(
                count for (first, second), count in transitions.items()
                if first in route_piers and second in route_piers
            )
            call_precision = matched_calls / total_calls
            transition_share = matched_transitions / total_transitions if total_transitions else 0
            route_coverage = len(matched_piers) / len(route_piers)
            score = 0.45 * call_precision + 0.35 * transition_share + 0.20 * route_coverage
            candidates.append(
                {
                    "mmsi": mmsi,
                    "vessel_name": names.get(mmsi, ""),
                    "week_start": week.isoformat(),
                    "route_id": route["id"],
                    "route_name": route["name"],
                    "score": round(score, 4),
                    "matched_calls": matched_calls,
                    "total_calls": total_calls,
                    "matched_transitions": matched_transitions,
                    "total_transitions": total_transitions,
                    "matched_piers": len(matched_piers),
                    "route_piers": len(route_piers),
                    "observed_piers": ";".join(
                        f"{pier}:{count}" for pier, count in pier_counts.most_common()
                    ),
                }
            )
        candidates.sort(key=lambda item: (item["score"], item["matched_calls"]), reverse=True)
        for rank, candidate in enumerate(candidates[:3], start=1):
            candidate["rank"] = rank
            second_score = candidates[1]["score"] if len(candidates) > 1 else 0
            candidate["margin"] = round(candidate["score"] - second_score, 4) if rank == 1 else ""
            output.append(candidate)
        if candidates:
            best = dict(candidates[0])
            second_score = candidates[1]["score"] if len(candidates) > 1 else 0
            best["margin"] = round(best["score"] - second_score, 4)
            best["confidence"] = (
                "high"
                if best["score"] >= 0.65 and best["margin"] >= 0.08
                else "probable"
                if best["score"] >= 0.50 and best["margin"] >= 0.03
                else "ambiguous"
            )
            top_by_week[(mmsi, week)] = best
    return output, top_by_week


def build_regimes(top_by_week: dict) -> list[dict]:
    by_vessel: dict[int, list[tuple[date, dict]]] = defaultdict(list)
    for (mmsi, week), candidate in top_by_week.items():
        if candidate["confidence"] != "ambiguous":
            by_vessel[mmsi].append((week, candidate))
    regimes = []
    for mmsi, assignments in by_vessel.items():
        assignments.sort()
        current = None
        for week, candidate in assignments:
            consecutive = current and (week - current["last_week"]).days <= 14
            if current and consecutive and current["route_id"] == candidate["route_id"]:
                current["last_week"] = week
                current["weeks"] += 1
                current["score_sum"] += candidate["score"]
                current["minimum_score"] = min(current["minimum_score"], candidate["score"])
                current["calls"] += candidate["total_calls"]
            else:
                if current:
                    regimes.append(current)
                current = {
                    "mmsi": mmsi,
                    "vessel_name": candidate.get("vessel_name", ""),
                    "route_id": candidate["route_id"],
                    "route_name": candidate["route_name"],
                    "first_week": week,
                    "last_week": week,
                    "weeks": 1,
                    "score_sum": candidate["score"],
                    "minimum_score": candidate["score"],
                    "calls": candidate["total_calls"],
                }
        if current:
            regimes.append(current)
    rows = []
    for regime in regimes:
        rows.append(
            {
                "mmsi": regime["mmsi"],
                "vessel_name": regime["vessel_name"],
                "route_id": regime["route_id"],
                "route_name": regime["route_name"],
                "first_week": regime["first_week"].isoformat(),
                "last_week": regime["last_week"].isoformat(),
                "weeks": regime["weeks"],
                "average_score": round(regime["score_sum"] / regime["weeks"], 4),
                "minimum_score": regime["minimum_score"],
                "calls": regime["calls"],
            }
        )
    return rows


def cluster_unknown_cells(rows: list[dict], radius_m: float, names: dict[int, str]) -> list[dict]:
    points = [
        {
            **row,
            "lat": float(row["lat"]),
            "lng": float(row["lng"]),
            "observations": int(row["observations"]),
            "polls": int(row["polls"]),
            "active_days": int(row["active_days"]),
            "mmsi_values": {int(value) for value in row["mmsis"].split(";") if value},
        }
        for row in rows
    ]
    parents = list(range(len(points)))

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(first: int, second: int) -> None:
        first_root = find(first)
        second_root = find(second)
        if first_root != second_root:
            parents[second_root] = first_root

    for first in range(len(points)):
        for second in range(first + 1, len(points)):
            if haversine_m(
                points[first]["lat"], points[first]["lng"], points[second]["lat"], points[second]["lng"]
            ) <= radius_m:
                union(first, second)
    groups: dict[int, list[dict]] = defaultdict(list)
    for index, point in enumerate(points):
        groups[find(index)].append(point)
    clusters = []
    for cluster_id, group in enumerate(groups.values(), start=1):
        weight = sum(point["observations"] for point in group)
        mmsis = set().union(*(point["mmsi_values"] for point in group))
        clusters.append(
            {
                "cluster_id": cluster_id,
                "lat": round(sum(point["lat"] * point["observations"] for point in group) / weight, 6),
                "lng": round(sum(point["lng"] * point["observations"] for point in group) / weight, 6),
                "cells": len(group),
                "observations": weight,
                "polls": sum(point["polls"] for point in group),
                "vessels": len(mmsis),
                "active_days_max": max(point["active_days"] for point in group),
                "mmsis": ";".join(str(value) for value in sorted(mmsis)),
                "vessel_names": vessel_labels(mmsis, names),
            }
        )
    clusters.sort(key=lambda item: (item["active_days_max"], item["observations"]), reverse=True)
    return clusters


def line_features(feature: dict, route_id: str, properties: dict) -> list[dict]:
    output = []
    if feature.get("type") == "Feature" and feature.get("geometry"):
        geometry = feature["geometry"]
        if geometry.get("type") in {"LineString", "MultiLineString"}:
            output.append({"type": "Feature", "properties": properties, "geometry": geometry})
    for child in feature.get("features", []):
        output.extend(line_features(child, route_id, properties))
    return output


def main() -> None:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    retained_route_ids = None
    if args.route_ids:
        retained_route_ids = set(json.loads(args.route_ids.read_text(encoding="utf-8"))["routes"])
    piers, routes, connection_features = load_reference(
        args.saaristo, args.data, retained_route_ids
    )
    all_source_vessels = {int(row["mmsi"]): row for row in read_csv(args.vessels)}
    all_vessels = {
        mmsi: row
        for mmsi, row in all_source_vessels.items()
        if int(row["active_days"]) >= args.minimum_active_days
    }
    vessel_names = load_vessel_names(args.livedata)
    vessel_names.update(load_name_overrides(args.vessel_names))
    calls = accepted_and_collapsed_calls(
        args.calls, args.duplicate_call_minutes, set(all_vessels)
    )
    candidates, top_by_week = route_candidates(calls, routes, vessel_names)
    regimes = build_regimes(top_by_week)
    clusters = cluster_unknown_cells(
        read_csv(args.unknown_cells), args.unknown_cluster_radius_m, vessel_names
    )

    candidate_fields = [
        "mmsi", "vessel_name", "week_start", "rank", "route_id", "route_name", "score", "margin",
        "matched_calls", "total_calls", "matched_transitions", "total_transitions",
        "matched_piers", "route_piers", "observed_piers",
    ]
    write_csv(args.output / "weekly-route-candidates.csv", candidate_fields, candidates)
    regime_fields = [
        "mmsi", "vessel_name", "route_id", "route_name", "first_week", "last_week", "weeks",
        "average_score", "minimum_score", "calls",
    ]
    write_csv(args.output / "route-regimes.csv", regime_fields, regimes)
    cluster_fields = [
        "cluster_id", "lat", "lng", "cells", "observations", "polls", "vessels",
        "active_days_max", "mmsis", "vessel_names",
    ]
    write_csv(args.output / "unknown-stop-clusters.csv", cluster_fields, clusters)

    operational_calls = Counter(call["mmsi"] for call in calls)
    operational_piers: dict[int, set[str]] = defaultdict(set)
    for call in calls:
        operational_piers[call["mmsi"]].add(call["pier"])
    assigned_weeks = Counter()
    high_weeks = Counter()
    assigned_routes: dict[int, set[str]] = defaultdict(set)
    for (mmsi, _week), candidate in top_by_week.items():
        if candidate["confidence"] != "ambiguous":
            assigned_weeks[mmsi] += 1
            assigned_routes[mmsi].add(candidate["route_id"])
        if candidate["confidence"] == "high":
            high_weeks[mmsi] += 1
    vessel_rows = []
    for mmsi, source in sorted(all_vessels.items()):
        classification = (
            "relevant"
            if assigned_weeks[mmsi] >= 2
            else "possible"
            if operational_calls[mmsi] or assigned_weeks[mmsi]
            else "unmatched"
        )
        vessel_rows.append(
            {
                "mmsi": mmsi,
                "vessel_name": vessel_names.get(mmsi, ""),
                "classification": classification,
                "operational_calls": operational_calls[mmsi],
                "known_piers": len(operational_piers[mmsi]),
                "assigned_weeks": assigned_weeks[mmsi],
                "high_confidence_weeks": high_weeks[mmsi],
                "assigned_routes": ";".join(sorted(assigned_routes[mmsi])),
                "active_days": source["active_days"],
                "first_utc": source["first_utc"],
                "last_utc": source["last_utc"],
            }
        )
    vessel_fields = [
        "mmsi", "vessel_name", "classification", "operational_calls", "known_piers", "assigned_weeks",
        "high_confidence_weeks", "assigned_routes", "active_days", "first_utc", "last_utc",
    ]
    write_csv(args.output / "vessel-classification.csv", vessel_fields, vessel_rows)

    pier_calls = Counter(call["pier"] for call in calls)
    pier_vessels: dict[str, set[int]] = defaultdict(set)
    for call in calls:
        pier_vessels[call["pier"]].add(call["mmsi"])
    review_features = []
    for pier_id, feature in piers.items():
        review_features.append(
            {
                "type": "Feature",
                "properties": {
                    "review_category": "known_pier",
                    "pier": pier_id,
                    "calls": pier_calls[pier_id],
                    "vessels": len(pier_vessels[pier_id]),
                    "vessel_names": vessel_labels(pier_vessels[pier_id], vessel_names),
                },
                "geometry": feature["geometry"],
            }
        )
    for cluster in clusters:
        review_features.append(
            {
                "type": "Feature",
                "properties": {"review_category": "unknown_stop", **cluster},
                "geometry": {"type": "Point", "coordinates": [cluster["lng"], cluster["lat"]]},
            }
        )
    route_weeks = Counter()
    route_vessels: dict[str, set[int]] = defaultdict(set)
    for (mmsi, _week), candidate in top_by_week.items():
        if candidate["confidence"] != "ambiguous":
            route_weeks[candidate["route_id"]] += 1
            route_vessels[candidate["route_id"]].add(mmsi)
    for route_id, weeks in route_weeks.items():
        source_feature = connection_features.get(route_id)
        if not source_feature:
            continue
        properties = {
            "review_category": "assigned_route",
            "route_id": route_id,
            "route_name": routes[route_id]["name"],
            "assigned_weeks": weeks,
            "vessels": len(route_vessels[route_id]),
            "vessel_names": vessel_labels(route_vessels[route_id], vessel_names),
        }
        review_features.extend(line_features(source_feature, route_id, properties))
    (args.output / "review.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": review_features}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    classifications = Counter(row["classification"] for row in vessel_rows)
    confidence_counts = Counter(candidate["confidence"] for candidate in top_by_week.values())
    summary = {
        "accepted_calls_before_collapsing": sum(1 for row in read_csv(args.calls) if row.get("operational") == "1"),
        "calls_after_collapsing_short_same_pier_duplicates": len(calls),
        "weekly_candidate_rows": len(candidates),
        "weeks_with_top_candidate": len(top_by_week),
        "confidence": dict(confidence_counts),
        "route_regimes": len(regimes),
        "vessel_classification": dict(classifications),
        "source_vessels": len(all_source_vessels),
        "retained_vessels": len(all_vessels),
        "excluded_short_stay_vessels": len(all_source_vessels) - len(all_vessels),
        "retained_vessels_with_names": sum(mmsi in vessel_names for mmsi in all_vessels),
        "unknown_input_cells": len(read_csv(args.unknown_cells)),
        "unknown_clusters": len(clusters),
        "review_features": len(review_features),
        "parameters": {
            "duplicate_call_minutes": args.duplicate_call_minutes,
            "unknown_cluster_radius_m": args.unknown_cluster_radius_m,
            "minimum_active_days": args.minimum_active_days,
            "retained_route_ids": sorted(routes),
        },
    }
    (args.output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
