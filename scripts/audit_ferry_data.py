#!/usr/bin/env python3
"""Audit saaristodata/data.json for structural and freshness problems."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


def iter_timetables(route: dict):
    for timetable in route.get("timetables", []):
        yield timetable


def localized_name(item: dict) -> str:
    return item.get("name_fi") or item.get("name") or item.get("id") or "(nimetön)"


def audit(data: dict, today: date) -> dict:
    routes = data.get("routes", {})
    global_timetables = data.get("timetables", {})
    problems: list[dict] = []
    domain_counts: Counter[str] = Counter()
    operator_counts: Counter[str] = Counter()

    def add(route_id: str, severity: str, category: str, message: str) -> None:
        problems.append({
            "route": route_id,
            "severity": severity,
            "category": category,
            "message": message,
        })

    for route_id, route in routes.items():
        if route.get("obsolete"):
            continue
        if route.get("id") != route_id:
            add(route_id, "error", "structure", f"id on {route.get('id')!r}, avaimen pitäisi olla {route_id!r}")
        if not route.get("piers"):
            add(route_id, "error", "route", "reitiltä puuttuvat laiturit")
        if len(route.get("piers", [])) == 1:
            add(route_id, "warning", "route", "reitillä on vain yksi laituri")
        if not route.get("vessels"):
            add(route_id, "warning", "vessel", "reitiltä puuttuvat alukset")
        if not route.get("operator"):
            add(route_id, "warning", "operator", "reitiltä puuttuu operaattori")

        for operator in route.get("operator", []):
            operator_counts[operator.get("name", "(nimetön)")] += 1
            contact = operator.get("contact", {})
            if not contact.get("www"):
                add(route_id, "warning", "contact", f"operaattorilta {operator.get('name')} puuttuu verkkosivu")
            if not (contact.get("phones") or contact.get("email")):
                add(route_id, "warning", "contact", f"operaattorilta {operator.get('name')} puuttuu puhelin ja sähköposti")

        if not route.get("timetables"):
            add(route_id, "error", "timetable", "reitiltä puuttuu aikataulu ja aikataululinkki")
        for timetable in iter_timetables(route):
            timetable_id = timetable.get("id")
            if not timetable_id:
                add(route_id, "error", "structure", "aikataululta puuttuu id")
            elif timetable_id not in global_timetables:
                add(route_id, "error", "structure", f"aikataulu {timetable_id!r} puuttuu globaalista hakemistosta")

            link = timetable.get("link")
            if not link:
                add(route_id, "error", "timetable", f"aikataululta {timetable_id!r} puuttuu lähdelinkki")
            else:
                parsed = urlparse(link)
                domain_counts[parsed.netloc.lower()] += 1
                if parsed.scheme != "https":
                    add(route_id, "warning", "link", f"aikataululinkki ei käytä HTTPS:ää: {link}")

            tables = timetable.get("tables") or []
            current = []
            future = []
            for table in tables:
                valid_from = table.get("validFrom")
                valid_to = table.get("validTo")
                try:
                    start = date.fromisoformat(valid_from) if valid_from else None
                    end = date.fromisoformat(valid_to) if valid_to else None
                except ValueError:
                    add(route_id, "error", "timetable", f"virheellinen päivämäärä aikataulussa {timetable_id!r}: {valid_from!r}–{valid_to!r}")
                    continue
                if start and end and start > end:
                    add(route_id, "error", "timetable", f"alkupäivä on loppupäivän jälkeen aikataulussa {timetable_id!r}")
                if (not start or start <= today) and (not end or end >= today):
                    current.append(table)
                elif start and start > today:
                    future.append(table)
            if not current:
                status = "tuleva jakso löytyy" if future else "ulkoinen linkki arvioitava reittikohtaisesti"
                add(route_id, "warning", "timetable", f"ei voimassa olevaa paikallista aikataulua ({status})")

    severity_order = {"error": 0, "warning": 1, "info": 2}
    problems.sort(key=lambda item: (severity_order[item["severity"]], item["route"], item["category"], item["message"]))
    return {
        "checkedAt": today.isoformat(),
        "counts": {
            "routes": len(routes),
            "activeRoutes": sum(not route.get("obsolete") for route in routes.values()),
            "obsoleteRoutes": sum(bool(route.get("obsolete")) for route in routes.values()),
            "piers": len(data.get("piers", {})),
            "ferries": len(data.get("ferries", {})),
            "timetables": len(global_timetables),
            "operators": len(data.get("operators", {})),
            "longDistanceRoutes": len(data.get("lauttaRoutes", [])),
        },
        "problemCounts": dict(Counter(problem["category"] for problem in problems)),
        "severityCounts": dict(Counter(problem["severity"] for problem in problems)),
        "operatorRouteCounts": dict(operator_counts.most_common()),
        "timetableDomains": dict(domain_counts.most_common()),
        "problems": problems,
    }


def markdown(report: dict, data: dict) -> str:
    counts = report["counts"]
    lines = [
        f"# Saaristolauttojen data-auditointi {report['checkedAt']}",
        "",
        "Tämä tiedosto on tuotettu komennolla `python3 scripts/audit_ferry_data.py`. "
        "Tarkastus löytää rakenteelliset ja ajalliset ongelmat; se ei yksin vahvista tietoja virallisista lähteistä.",
        "",
        "## Yhteenveto",
        "",
        f"- Reittejä: {counts['routes']}",
        f"- Aktiivisia reittejä: {counts['activeRoutes']}",
        f"- Vanhentuneiksi merkittyjä reittejä: {counts['obsoleteRoutes']}",
        f"- Laitureita: {counts['piers']}",
        f"- Aluksia: {counts['ferries']}",
        f"- Aikataulukokonaisuuksia: {counts['timetables']}",
        f"- Kaukoliikenteen reittejä: {counts['longDistanceRoutes']}",
        f"- Virheitä: {report['severityCounts'].get('error', 0)}",
        f"- Varoituksia: {report['severityCounts'].get('warning', 0)}",
        "",
        "## Reittikohtaiset havainnot",
        "",
        "| Reitti | Nimi | Taso | Luokka | Havainto |",
        "|---|---|---|---|---|",
    ]
    routes = data.get("routes", {})
    for problem in report["problems"]:
        route = routes.get(problem["route"], {})
        values = [problem["route"], localized_name(route), problem["severity"], problem["category"], problem["message"]]
        lines.append("| " + " | ".join(str(value).replace("|", "\\|") for value in values) + " |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("data", type=Path, help="Polku saaristodata/data.json-tiedostoon")
    parser.add_argument("--date", default=date.today().isoformat(), help="Tarkastuspäivä muodossa YYYY-MM-DD")
    parser.add_argument("--json", type=Path, help="Kirjoita koneluettava raportti")
    parser.add_argument("--markdown", type=Path, help="Kirjoita Markdown-raportti")
    args = parser.parse_args()

    data = json.loads(args.data.read_text(encoding="utf-8"))
    report = audit(data, date.fromisoformat(args.date))
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.json:
        args.json.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    if args.markdown:
        args.markdown.write_text(markdown(report, data), encoding="utf-8")


if __name__ == "__main__":
    main()
