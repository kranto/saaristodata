#!/usr/bin/env python3
"""Assign structural roles to calls in complete high-confidence AIS journeys.

The model intentionally describes what the observed sequence proves. In
particular, a pier seen once on a closed journey is not automatically declared
to be part of a ring route: it receives the role ``single_loop_call`` with
medium interpretation confidence.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("journeys", type=Path)
    parser.add_argument("journey_stops", type=Path)
    parser.add_argument("topology", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--compact-output", type=Path)
    return parser.parse_args()


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict], fallback_fields: list[str]) -> None:
    fields = list(rows[0]) if rows else fallback_fields
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def percentage(numerator: int, denominator: int) -> float:
    return round(100 * numerator / denominator, 2) if denominator else 0.0


def journey_shape(sequence: list[str], terminals: set[str]) -> str:
    if sequence[0] != sequence[-1]:
        if sequence[0] in terminals and sequence[-1] in terminals:
            return "terminal_to_terminal"
        return "different_endpoint"
    internal = sequence[1:-1]
    if not internal:
        return "empty_closed_journey"
    if len(internal) == 1:
        return "simple_turnaround"
    counts = Counter(internal)
    if any(count >= 2 for count in counts.values()):
        return "closed_with_repeated_pier"
    return "closed_with_single_calls"


def internal_role(
    sequence: list[str], index: int, positions: dict[str, list[int]], shape: str
) -> tuple[str, str, str]:
    pier = sequence[index]
    previous_pier = sequence[index - 1]
    next_pier = sequence[index + 1]
    if shape == "terminal_to_terminal":
        return "terminal_to_terminal", "high", "journey endpoints are configured terminals"
    if shape == "different_endpoint":
        return "terminal_to_terminal", "low", "journey endpoints differ but one is not a configured terminal"
    if previous_pier == next_pier:
        return "turnaround", "high", "observed exact A-B-A sequence"
    occurrences = positions[pier]
    if len(occurrences) >= 2:
        if index == occurrences[0]:
            return "outbound", "high", "first of repeated calls in the same closed journey"
        if index == occurrences[-1]:
            return "inbound", "high", "last of repeated calls in the same closed journey"
        return "repeated_middle", "medium", "additional repeated call between first and last calls"
    return (
        "single_loop_call",
        "medium",
        "called once in a closed journey; does not alone prove ring topology",
    )


def main() -> None:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    config = json.loads(args.topology.read_text(encoding="utf-8"))
    structures = config["routes"]

    journeys = {
        row["journey_id"]: row
        for row in read_csv(args.journeys)
        if row["route_id"] in structures
        and row["timing_confidence"] == "high"
        and row["complete"] == "1"
    }
    stops_by_journey: dict[str, list[dict]] = defaultdict(list)
    for row in read_csv(args.journey_stops):
        if row["journey_id"] in journeys and row["timing_confidence"] == "high":
            stops_by_journey[row["journey_id"]].append(row)
    for rows in stops_by_journey.values():
        rows.sort(key=lambda row: int(row["stop_index"]))

    events: list[dict] = []
    journey_rows: list[dict] = []
    route_shape_counts: dict[str, Counter] = defaultdict(Counter)
    route_role_counts: dict[str, Counter] = defaultdict(Counter)
    pier_role_counts: dict[tuple[str, str], Counter] = defaultdict(Counter)
    pier_journeys: dict[tuple[str, str], set[str]] = defaultdict(set)

    for journey_id, journey in journeys.items():
        calls = stops_by_journey.get(journey_id, [])
        sequence = [journey["start_pier"]] + [row["destination_pier"] for row in calls]
        if len(sequence) < 2:
            continue
        route_id = journey["route_id"]
        terminals = set(structures[route_id]["terminals"])
        shape = journey_shape(sequence, terminals)
        route_shape_counts[route_id][shape] += 1
        internal_sequence = sequence[1:-1] if sequence[-1] == sequence[0] else sequence[1:-1]
        journey_rows.append({
            "journey_id": journey_id,
            "route_id": route_id,
            "route_name": journey["route_name"],
            "mmsi": journey["mmsi"],
            "departure_utc": journey["departure_utc"],
            "start_pier": sequence[0],
            "end_pier": sequence[-1],
            "journey_shape": shape,
            "internal_calls": len(internal_sequence),
            "sequence": ">".join(sequence),
        })

        positions: dict[str, list[int]] = defaultdict(list)
        for index, pier in enumerate(sequence[1:-1], start=1):
            positions[pier].append(index)
        for index, row in enumerate(calls, start=1):
            pier = row["destination_pier"]
            is_endpoint = index == len(sequence) - 1
            if is_endpoint:
                role, confidence, basis = (
                    "journey_endpoint",
                    "high",
                    "final observed call closes or ends the journey",
                )
            else:
                role, confidence, basis = internal_role(sequence, index, positions, shape)
            event = {
                "journey_id": journey_id,
                "route_id": route_id,
                "route_name": journey["route_name"],
                "mmsi": journey["mmsi"],
                "departure_utc": journey["departure_utc"],
                "journey_shape": shape,
                "start_pier": sequence[0],
                "end_pier": sequence[-1],
                "call_index": index,
                "pier": pier,
                "call_role": role,
                "role_confidence": confidence,
                "role_basis": basis,
                "previous_pier": sequence[index - 1],
                "next_pier": sequence[index + 1] if index + 1 < len(sequence) else "",
                "driving_elapsed_seconds": row["driving_elapsed_seconds"],
                "prefix": row["prefix"],
            }
            events.append(event)
            route_role_counts[route_id][role] += 1
            pier_role_counts[(route_id, pier)][role] += 1
            pier_journeys[(route_id, pier)].add(journey_id)

    journey_summary_rows: list[dict] = []
    for route_id, structure in structures.items():
        counts = route_shape_counts[route_id]
        total = sum(counts.values())
        for shape, count in sorted(counts.items()):
            journey_summary_rows.append({
                "route_id": route_id,
                "topology": structure["topology"],
                "journey_shape": shape,
                "journeys": count,
                "share_percent": percentage(count, total),
            })

    pier_rows: list[dict] = []
    roles = [
        "outbound",
        "inbound",
        "single_loop_call",
        "turnaround",
        "terminal_to_terminal",
        "repeated_middle",
        "journey_endpoint",
    ]
    for (route_id, pier), counts in sorted(pier_role_counts.items()):
        calls = sum(counts.values())
        non_endpoint = calls - counts["journey_endpoint"]
        pier_rows.append({
            "route_id": route_id,
            "pier": pier,
            "journeys": len(pier_journeys[(route_id, pier)]),
            "calls": calls,
            "non_endpoint_calls": non_endpoint,
            **{f"{role}_calls": counts[role] for role in roles},
            "dominant_non_endpoint_role": max(
                roles[:-1], key=lambda role: counts[role]
            ) if non_endpoint else "journey_endpoint",
        })

    route_rows: list[dict] = []
    for route_id, structure in structures.items():
        route_journeys = sum(route_shape_counts[route_id].values())
        route_rows.append({
            "route_id": route_id,
            "terminals": "|".join(structure["terminals"]),
            "configured_topology": structure["topology"],
            "journeys": route_journeys,
            "closed_journeys": sum(
                count for shape, count in route_shape_counts[route_id].items()
                if shape.startswith("closed_") or shape == "simple_turnaround"
            ),
            "terminal_to_terminal_journeys": route_shape_counts[route_id]["terminal_to_terminal"],
            "single_loop_calls": route_role_counts[route_id]["single_loop_call"],
            "turnaround_calls": route_role_counts[route_id]["turnaround"],
            "outbound_calls": route_role_counts[route_id]["outbound"],
            "inbound_calls": route_role_counts[route_id]["inbound"],
            "terminal_to_terminal_calls": route_role_counts[route_id]["terminal_to_terminal"],
        })

    write_csv(args.output / "call-role-events.csv", events, ["journey_id"])
    write_csv(args.output / "journey-role-shapes.csv", journey_rows, ["journey_id"])
    write_csv(args.output / "journey-shape-summary.csv", journey_summary_rows, ["route_id"])
    write_csv(args.output / "pier-role-summary.csv", pier_rows, ["route_id"])
    write_csv(args.output / "route-topology-summary.csv", route_rows, ["route_id"])

    compact = {
        "schemaVersion": 1,
        "status": "draft",
        "modelVersion": "ais-call-roles-v1",
        "policy": {
            "basis": "complete high-confidence AIS journeys",
            "singleCallDoesNotProveRingTopology": True,
            "exactTurnaroundPattern": "A>B>A",
            "publishedApplicationDataModified": False,
        },
        "routes": [
            {
                "id": route_id,
                **structure,
                "journeyShapes": {
                    shape: count for shape, count in sorted(route_shape_counts[route_id].items())
                },
                "piers": [
                    {
                        "name": row["pier"],
                        "journeys": row["journeys"],
                        "roles": {
                            role: row[f"{role}_calls"]
                            for role in roles
                            if row[f"{role}_calls"]
                        },
                        "dominantNonEndpointRole": row["dominant_non_endpoint_role"],
                    }
                    for row in pier_rows if row["route_id"] == route_id
                ],
            }
            for route_id, structure in structures.items()
        ],
    }
    compact_path = args.compact_output or args.output / "call-role-model.json"
    compact_path.parent.mkdir(parents=True, exist_ok=True)
    compact_path.write_text(
        json.dumps(compact, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    summary = {
        "routes": len(structures),
        "completeHighConfidenceJourneys": len(journey_rows),
        "callEvents": len(events),
        "pierRows": len(pier_rows),
        "publishedApplicationDataModified": False,
    }
    (args.output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
