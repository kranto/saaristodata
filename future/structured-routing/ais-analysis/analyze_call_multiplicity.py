#!/usr/bin/env python3
"""Describe whether connection-route piers are called once or twice per journey."""

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
    parser.add_argument("output", type=Path)
    parser.add_argument("--minimum-pier-journeys", type=int, default=3)
    return parser.parse_args()


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict], default_field: str) -> None:
    fields = list(rows[0]) if rows else [default_field]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def percentage(numerator: int, denominator: int) -> float:
    return round(100 * numerator / denominator, 2) if denominator else 0.0


def route_shape(same_share: float, repeated_share: float, retraced_share: float, mains: int) -> str:
    if same_share >= 75 and (repeated_share >= 20 or retraced_share >= 55):
        return "out_and_back_dominant"
    if same_share >= 75 and repeated_share < 10:
        return "ring_or_branched_loop_dominant"
    if same_share >= 75:
        return "mixed_loop_and_out_and_back"
    if mains >= 2 and same_share < 50:
        return "multi_terminal_or_point_to_point"
    return "mixed_or_insufficient_structure"


def main() -> None:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    journeys = {
        row["journey_id"]: row
        for row in read_csv(args.journeys)
        if row["timing_confidence"] == "high" and row["complete"] == "1"
    }
    stops: dict[str, list[dict]] = defaultdict(list)
    for row in read_csv(args.journey_stops):
        if row["journey_id"] in journeys and row["timing_confidence"] == "high":
            stops[row["journey_id"]].append(row)
    for rows in stops.values():
        rows.sort(key=lambda row: int(row["stop_index"]))

    route_journeys: dict[str, list[str]] = defaultdict(list)
    for journey_id, journey in journeys.items():
        route_journeys[journey["route_id"]].append(journey_id)

    route_rows = []
    pier_rows = []
    sequence_rows = []
    for route_id, journey_ids in sorted(route_journeys.items()):
        route_name = journeys[journey_ids[0]]["route_name"]
        main_piers = {journeys[journey_id]["start_pier"] for journey_id in journey_ids}
        same_endpoint = repeated_pier_journeys = retraced_edge_journeys = 0
        sequences = Counter()
        per_pier_counts: dict[str, Counter] = defaultdict(Counter)
        pier_turnarounds = Counter()
        pier_through_calls = Counter()
        pier_start_calls = Counter()
        pier_end_calls = Counter()

        for journey_id in journey_ids:
            journey = journeys[journey_id]
            sequence = [journey["start_pier"]] + [
                row["destination_pier"] for row in stops.get(journey_id, [])
            ]
            sequences[">".join(sequence)] += 1
            if sequence[-1] == sequence[0]:
                same_endpoint += 1
            internal = sequence[1:-1] if sequence[-1] in main_piers else sequence[1:]
            counts = Counter(internal)
            if any(count >= 2 for count in counts.values()):
                repeated_pier_journeys += 1
            for pier in set(internal):
                per_pier_counts[pier][counts[pier]] += 1
            directed_by_edge: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
            for origin, destination in zip(sequence, sequence[1:]):
                directed_by_edge[tuple(sorted((origin, destination)))].add((origin, destination))
            if any(len(directions) >= 2 for directions in directed_by_edge.values()):
                retraced_edge_journeys += 1
            for index, pier in enumerate(sequence):
                if index == 0:
                    pier_start_calls[pier] += 1
                elif index == len(sequence) - 1:
                    pier_end_calls[pier] += 1
                else:
                    if sequence[index - 1] == sequence[index + 1]:
                        pier_turnarounds[pier] += 1
                    else:
                        pier_through_calls[pier] += 1

        total = len(journey_ids)
        same_share = percentage(same_endpoint, total)
        repeated_share = percentage(repeated_pier_journeys, total)
        retraced_share = percentage(retraced_edge_journeys, total)
        route_rows.append({
            "route_id": route_id,
            "route_name": route_name,
            "complete_high_confidence_journeys": total,
            "main_or_endpoint_piers": "|".join(sorted(main_piers)),
            "same_start_and_end_journeys": same_endpoint,
            "same_start_and_end_percent": same_share,
            "journeys_with_repeated_intermediate_pier": repeated_pier_journeys,
            "journeys_with_repeated_intermediate_pier_percent": repeated_share,
            "journeys_with_retraced_observed_edge": retraced_edge_journeys,
            "journeys_with_retraced_observed_edge_percent": retraced_share,
            "observed_shape": route_shape(
                same_share, repeated_share, retraced_share, len(main_piers)
            ),
        })

        all_piers = set(per_pier_counts) | set(pier_start_calls) | set(pier_end_calls)
        for pier in sorted(all_piers):
            count_distribution = per_pier_counts[pier]
            visited = sum(count_distribution.values())
            once = count_distribution[1]
            repeated = sum(count for visits, count in count_distribution.items() if visits >= 2)
            if visited < args.minimum_pier_journeys and not (pier_start_calls[pier] or pier_end_calls[pier]):
                continue
            if pier_start_calls[pier] or pier_end_calls[pier]:
                evidence = "main_or_journey_endpoint"
            elif repeated >= 5:
                evidence = "both_directions_same_journey_observed"
            elif pier_turnarounds[pier] >= 5:
                evidence = "turnaround_call_observed"
            elif repeated == 0:
                evidence = "single_call_per_observed_journey"
            else:
                evidence = "mostly_single_with_rare_repeat"
            pier_rows.append({
                "route_id": route_id,
                "route_name": route_name,
                "pier": pier,
                "journeys": total,
                "journeys_visiting_as_intermediate": visited,
                "visits_once": once,
                "visits_twice_or_more": repeated,
                "repeat_percent_when_visited": percentage(repeated, visited),
                "maximum_visits_in_journey": max(count_distribution, default=0),
                "clear_immediate_turnaround_calls": pier_turnarounds[pier],
                "through_calls": pier_through_calls[pier],
                "journeys_starting_here": pier_start_calls[pier],
                "journeys_ending_here": pier_end_calls[pier],
                "evidence": evidence,
            })

        for sequence, count in sequences.most_common(20):
            sequence_rows.append({
                "route_id": route_id,
                "route_name": route_name,
                "sequence": sequence,
                "journeys": count,
                "share_percent": percentage(count, total),
            })

    write_csv(args.output / "route-call-shapes.csv", route_rows, "route_id")
    write_csv(args.output / "pier-call-multiplicity.csv", pier_rows, "route_id")
    write_csv(args.output / "common-complete-sequences.csv", sequence_rows, "route_id")
    summary = {
        "completeHighConfidenceJourneys": len(journeys),
        "routes": len(route_rows),
        "pierRows": len(pier_rows),
        "method": {
            "repeat": "same non-main pier at least twice in one complete journey",
            "retrace": "same observed pier-to-pier edge in both directions in one complete journey",
            "turnaround": "single pier call with identical previous and next observed pier",
        },
    }
    (args.output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
