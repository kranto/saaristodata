#!/usr/bin/env python3
"""Write a human-readable review of the generated pier road network."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parents[1]


def pair_value(first: dict | None, second: dict | None, key: str, scale: float = 1) -> str:
    values = []
    for result in (first, second):
        if not result or result.get("status") != "ok":
            values.append("–")
        else:
            value = result[key] / scale
            values.append(f"{value:.1f}" if scale != 1 else str(result[key]))
    return values[0] if values[0] == values[1] else f"{values[0]} / {values[1]}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--network", type=Path, default=EXPERIMENT / "road-network.json")
    parser.add_argument("--audit", type=Path, default=EXPERIMENT / "road-network-audit.json")
    parser.add_argument("--output", type=Path, default=EXPERIMENT / "road-network-review.md")
    args = parser.parse_args()

    network = json.loads(args.network.read_text())
    audit = json.loads(args.audit.read_text()) if args.audit.exists() else None
    names = network.get("preferredNames", {})
    by_direction = {
        (item["componentId"], item["from"], item["to"]): item
        for item in network["transfers"]
    }

    lines = [
        "# Tieverkon tarkistuslista",
        "",
        "Tämä on generoitu katselmointinäkymä. Ajat ovat suuntaa-antavia ja sarakkeiden",
        "kaksi arvoa tarkoittavat suuntia A→B / B→A. Kaikki reitit on hyväksytty vain,",
        "jos reititin löysi tieyhteyden ilman lauttaosuutta.",
        "",
        f"- Tiealueita: {network['statistics']['componentCount']}",
        f"- Laitureita tiealueilla: {network['statistics']['pierCount']}",
        f"- Suunnattuja laiturivälejä: {network['statistics']['directedTransferCount']}",
        f"- Kulkutapakohtaisia tuloksia: {network['statistics']['modeResultCount']}",
        f"- Virheitä: {network['statistics']['failureCount']}",
        "",
        "## Tiealueet",
        "",
        "| Tunnus | Kulkutavat | Laiturit |",
        "|---|---|---|",
    ]
    for component in network["components"]:
        modes = ", ".join(component.get("modes", ["auto", "bicycle"]))
        piers = ", ".join(names.get(ref, ref) for ref in component["piers"])
        lines.append(f"| {component['id']} | {modes} | {piers} |")

    lines.extend(["", "## Laiturivälit", ""])
    for component in network["components"]:
        piers = component["piers"]
        lines.extend([
            f"### {component['id']}",
            "",
            "| A | B | km A→B / B→A | auto min A→B / B→A | pyörä min A→B / B→A |",
            "|---|---|---:|---:|---:|",
        ])
        for index, first_ref in enumerate(piers):
            for second_ref in piers[index + 1:]:
                forward = by_direction.get((component["id"], first_ref, second_ref), {}).get("modes", {})
                reverse = by_direction.get((component["id"], second_ref, first_ref), {}).get("modes", {})
                distance = pair_value(forward.get("auto") or forward.get("bicycle"), reverse.get("auto") or reverse.get("bicycle"), "distanceMeters", 1000)
                auto = pair_value(forward.get("auto"), reverse.get("auto"), "displayMinutes")
                bicycle = pair_value(forward.get("bicycle"), reverse.get("bicycle"), "displayMinutes")
                lines.append(
                    f"| {names.get(first_ref, first_ref)} | {names.get(second_ref, second_ref)} "
                    f"| {distance} | {auto} | {bicycle} |"
                )
        lines.append("")

    lines.extend(["## Auditoinnin mahdolliset puutteet", ""])
    if not audit:
        lines.append("Auditointia ei ollut vielä saatavilla.")
    else:
        possible = audit.get("possibleMissingConnections", [])
        lines.append(
            f"Auditointi tarkisti {audit['statistics']['candidatePairCount']} lähintä eri "
            f"tiealueiden välistä ehdokasparia. Mahdollisia puutteita: {len(possible)}."
        )
        lines.extend(["", "| A | Nykyinen alue | B | Nykyinen alue | Ilmaetäisyys km |", "|---|---|---|---|---:|"])
        for item in possible:
            lines.append(
                f"| {names.get(item['from'], item['from'])} | {item.get('fromComponent') or 'yksittäinen'} "
                f"| {names.get(item['to'], item['to'])} | {item.get('toComponent') or 'yksittäinen'} "
                f"| {item['airDistanceMeters'] / 1000:.1f} |"
            )
        if not possible:
            lines.append("| – | – | – | – | – |")

    args.output.write_text("\n".join(lines) + "\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
