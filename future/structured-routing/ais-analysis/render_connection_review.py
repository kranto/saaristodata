#!/usr/bin/env python3
"""Render a compact interactive review map for connection-vessel AIS analysis."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("voyages", type=Path)
    parser.add_argument("review", type=Path)
    parser.add_argument("classifications", type=Path)
    parser.add_argument("regimes", type=Path)
    parser.add_argument("patterns", type=Path)
    parser.add_argument("raw_database", type=Path)
    parser.add_argument("saaristo", type=Path)
    parser.add_argument("data", type=Path)
    parser.add_argument("area", type=Path)
    parser.add_argument("coastline", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--tracks-per-vessel-week", type=int, default=1)
    parser.add_argument("--simplification-tolerance-m", type=float, default=10)
    parser.add_argument("--outside-days-per-vessel", type=int, default=8)
    parser.add_argument("--outside-segments-per-day", type=int, default=2)
    parser.add_argument("--maximum-track-gap-seconds", type=int, default=90)
    parser.add_argument("--maximum-implied-speed-knots", type=float, default=20)
    return parser.parse_args()


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as file:
        return list(csv.DictReader(file))


def sample_indexes(count: int, maximum: int) -> list[int]:
    if count <= maximum:
        return list(range(count))
    if maximum <= 1:
        return [count // 2]
    return sorted({round(index * (count - 1) / (maximum - 1)) for index in range(maximum)})


def encode_polyline(coordinates: list[tuple[float, float]]) -> str:
    output = []
    previous_lat = 0
    previous_lng = 0
    for lng, lat in coordinates:
        lat_value = round(lat * 100_000)
        lng_value = round(lng * 100_000)
        for value in (lat_value - previous_lat, lng_value - previous_lng):
            value = ~(value << 1) if value < 0 else value << 1
            while value >= 0x20:
                output.append(chr((0x20 | (value & 0x1F)) + 63))
                value >>= 5
            output.append(chr(value + 63))
        previous_lat = lat_value
        previous_lng = lng_value
    return "".join(output)


def distance_m(first: tuple, second: tuple) -> float:
    first_lng, first_lat = first[:2]
    second_lng, second_lat = second[:2]
    first_lat_r = math.radians(first_lat)
    second_lat_r = math.radians(second_lat)
    dlat = second_lat_r - first_lat_r
    dlng = math.radians(second_lng - first_lng)
    value = math.sin(dlat / 2) ** 2 + math.cos(first_lat_r) * math.cos(second_lat_r) * math.sin(dlng / 2) ** 2
    return 2 * 6_371_000 * math.asin(math.sqrt(value))


def perpendicular_distance_m(point: tuple, start: tuple, end: tuple) -> float:
    latitude_scale = 110_540
    longitude_scale = 111_320 * math.cos(math.radians((start[1] + end[1]) / 2))
    px = (point[0] - start[0]) * longitude_scale
    py = (point[1] - start[1]) * latitude_scale
    ex = (end[0] - start[0]) * longitude_scale
    ey = (end[1] - start[1]) * latitude_scale
    length_squared = ex * ex + ey * ey
    if not length_squared:
        return math.hypot(px, py)
    fraction = min(1.0, max(0.0, (px * ex + py * ey) / length_squared))
    return math.hypot(px - fraction * ex, py - fraction * ey)


def simplify_coordinates(coordinates: list[tuple[float, float]], tolerance_m: float):
    if len(coordinates) <= 2:
        return coordinates
    maximum_distance = -1.0
    maximum_index = 0
    for index in range(1, len(coordinates) - 1):
        distance = perpendicular_distance_m(
            coordinates[index], coordinates[0], coordinates[-1]
        )
        if distance > maximum_distance:
            maximum_distance = distance
            maximum_index = index
    if maximum_distance <= tolerance_m:
        return [coordinates[0], coordinates[-1]]
    first = simplify_coordinates(coordinates[: maximum_index + 1], tolerance_m)
    second = simplify_coordinates(coordinates[maximum_index:], tolerance_m)
    return first[:-1] + second


def split_discontinuities(
    rows: list[tuple], timestamp_index: int, maximum_gap_ms: int, maximum_speed_knots: float
) -> list[list[tuple]]:
    segments = []
    current = []
    previous_timestamp = None
    for row in rows:
        timestamp = row[timestamp_index]
        gap_ms = timestamp - previous_timestamp if previous_timestamp is not None else None
        implied_speed = (
            distance_m(current[-1], row) / (gap_ms / 1000) * 1.943844
            if current and gap_ms and gap_ms > 0
            else 0
        )
        if previous_timestamp is not None and (
            gap_ms <= 0 or gap_ms > maximum_gap_ms or implied_speed > maximum_speed_knots
        ):
            if len(current) >= 2:
                segments.append(current)
            current = []
        current.append(row)
        previous_timestamp = timestamp
    if len(current) >= 2:
        segments.append(current)
    return segments


def line_geometries(feature: dict) -> list[list[list[float]]]:
    output = []
    geometry = feature.get("geometry", {})
    if geometry.get("type") == "LineString":
        output.append(geometry["coordinates"])
    elif geometry.get("type") == "MultiLineString":
        output.extend(geometry["coordinates"])
    for child in feature.get("features", []):
        output.extend(line_geometries(child))
    return output


def main() -> None:
    args = parse_args()
    classifications = {int(row["mmsi"]): row for row in read_csv(args.classifications)}
    regimes = read_csv(args.regimes)
    patterns = read_csv(args.patterns)
    review = json.loads(args.review.read_text(encoding="utf-8"))
    saaristo = json.loads(args.saaristo.read_text(encoding="utf-8-sig"))
    data_json = json.loads(args.data.read_text(encoding="utf-8-sig"))

    connection = sqlite3.connect(f"file:{args.voyages}?mode=ro", uri=True)
    connection.execute("PRAGMA query_only=ON")
    voyage_rows = connection.execute(
        """
        SELECT voyage_id, mmsi, route_id, route_name, origin_pier, destination_pier,
               departure_utc, departure_ms, duration_seconds, accepted_points,
               maximum_collection_gap_seconds
        FROM voyages
        WHERE quality IN ('good', 'usable')
        ORDER BY route_id, mmsi, departure_ms
        """
    ).fetchall()
    regimes_by_vessel_route = defaultdict(list)
    for regime in regimes:
        regimes_by_vessel_route[(int(regime["mmsi"]), regime["route_id"])].append(regime)
    grouped = defaultdict(list)
    for row in voyage_rows:
        week = datetime.fromtimestamp(row[7] / 1000, UTC).date()
        week = week - timedelta(days=week.weekday())
        week_value = week.isoformat()
        regime = next(
            (
                candidate
                for candidate in regimes_by_vessel_route[(row[1], row[2])]
                if candidate["first_week"] <= week_value <= candidate["last_week"]
            ),
            None,
        )
        if regime:
            grouped[(
                row[2], row[1], regime["first_week"], regime["last_week"], row[4], row[5]
            )].append(row)

    route_payload = defaultdict(lambda: {
        "name": "", "tracks": [], "reference": [], "piers": [], "periods": [], "patterns": []
    })
    pier_calls = Counter()
    pier_vessels = defaultdict(set)
    for (route_id, mmsi, _regime_first, _regime_last, origin, destination), rows in grouped.items():
        route_payload[route_id]["name"] = rows[0][3]
        ranked_rows = sorted(rows, key=lambda row: (row[10] or 999_999, -row[9]))
        for row in ranked_rows[:args.tracks_per_vessel_week]:
            week = datetime.fromtimestamp(row[7] / 1000, UTC).date()
            week = (week - timedelta(days=week.weekday())).isoformat()
            point_rows = connection.execute(
                "SELECT lng, lat, collection_ms FROM voyage_points WHERE voyage_id=? ORDER BY sequence",
                (row[0],),
            ).fetchall()
            for segment in split_discontinuities(
                point_rows, 2, args.maximum_track_gap_seconds * 1000,
                args.maximum_implied_speed_knots,
            ):
                coordinates = [(point[0], point[1]) for point in segment]
                coordinates = simplify_coordinates(
                    coordinates, args.simplification_tolerance_m
                )
                route_payload[route_id]["tracks"].append([
                    encode_polyline(coordinates), mmsi, week, origin, destination, row[6], row[8]
                ])
        for row in rows:
            pier_calls[(route_id, row[4])] += 1
            pier_calls[(route_id, row[5])] += 1
            pier_vessels[(route_id, row[4])].add(mmsi)
            pier_vessels[(route_id, row[5])].add(mmsi)

    route_ids = set(route_payload)
    pier_coordinates = {}
    for feature in saaristo.get("features", []):
        properties = feature.get("properties", {})
        if properties.get("stype") == "pier" and feature.get("geometry", {}).get("type") == "Point":
            pier_coordinates[properties.get("ref")] = feature["geometry"]["coordinates"]
        elif properties.get("stype") == "connection" and properties.get("ref") in route_ids:
            route_payload[properties["ref"]]["reference"] = [
                encode_polyline(line) for line in line_geometries(feature)
            ]
    for route_id in route_ids:
        route = data_json["routes"].get(route_id, {})
        for pier in route.get("piers", []):
            pier_id = pier.get("id") or pier.get("name")
            if pier_id in pier_coordinates:
                route_payload[route_id]["piers"].append([
                    pier_id,
                    *pier_coordinates[pier_id],
                    pier_calls[(route_id, pier_id)],
                    len(pier_vessels[(route_id, pier_id)]),
                    str(pier.get("type")) == "1",
                ])

    for regime in regimes:
        route_id = regime["route_id"]
        if route_id not in route_ids:
            continue
        route_payload[route_id]["periods"].append([
            int(regime["mmsi"]), regime["vessel_name"] or regime["mmsi"],
            regime["first_week"], regime["last_week"], int(regime["weeks"]),
            round(float(regime["average_score"]), 2),
        ])
    for pattern in patterns:
        route_id = pattern["route_id"]
        if route_id not in route_ids:
            continue
        route_payload[route_id]["patterns"].append([
            pattern["sequence"], int(pattern["journeys"]), pattern["first_departure_utc"][:10],
            pattern["last_departure_utc"][:10],
        ])
    for payload in route_payload.values():
        payload["patterns"].sort(key=lambda item: -item[1])
        payload["patterns"] = payload["patterns"][:12]
        payload["periods"].sort(key=lambda item: (item[2], item[0]))

    unknown_stops = []
    for feature in review.get("features", []):
        properties = feature.get("properties", {})
        if properties.get("review_category") != "unknown_stop":
            continue
        mmsis = [int(value) for value in str(properties.get("mmsis", "")).split(";") if value]
        classes = {classifications.get(mmsi, {}).get("classification", "unmatched") for mmsi in mmsis}
        category = "relevant" if "relevant" in classes else "possible" if "possible" in classes else "unmatched"
        unknown_stops.append([
            properties["cluster_id"], *feature["geometry"]["coordinates"],
            round(float(properties.get("distance_to_coast_m", 0))), category,
            properties.get("vessel_names", ""), int(properties.get("observations", 0)),
        ])

    raw = sqlite3.connect(f"file:{args.raw_database}?mode=ro", uri=True)
    raw.execute("PRAGMA query_only=ON")
    outside_tracks = []
    for mmsi, vessel in classifications.items():
        if vessel["classification"] == "relevant":
            continue
        days = [row[0] for row in raw.execute(
            """
            SELECT date(ais_timestamp / 1000, 'unixepoch')
            FROM observations WHERE mmsi=?
            GROUP BY date(ais_timestamp / 1000, 'unixepoch')
            ORDER BY 1
            """, (mmsi,)
        )]
        for day_index in sample_indexes(len(days), args.outside_days_per_vessel):
            day = days[day_index]
            start_ms = round(datetime.fromisoformat(day).replace(tzinfo=UTC).timestamp() * 1000)
            point_rows = raw.execute(
                """
                SELECT lng, lat, first_collection_ms FROM observations
                WHERE mmsi=? AND ais_timestamp>=? AND ais_timestamp<?
                  AND age_at_first_ms BETWEEN -60000 AND 300000
                ORDER BY ais_timestamp
                """, (mmsi, start_ms, start_ms + 86_400_000)
            ).fetchall()
            segments = split_discontinuities(
                point_rows, 2, args.maximum_track_gap_seconds * 1000,
                args.maximum_implied_speed_knots,
            )
            segments.sort(key=len, reverse=True)
            for segment in segments[:args.outside_segments_per_day]:
                coordinates = [(point[0], point[1]) for point in segment]
                coordinates = simplify_coordinates(
                    coordinates, args.simplification_tolerance_m
                )
                outside_tracks.append([
                    encode_polyline(coordinates), mmsi, vessel["vessel_name"] or str(mmsi),
                    vessel["classification"], day,
                ])

    routes = []
    for route_id, payload in route_payload.items():
        payload["id"] = route_id
        routes.append(payload)
    routes.sort(key=lambda item: item["name"])
    coastline = json.loads(args.coastline.read_text(encoding="utf-8"))
    payload = {
        "area": json.loads(args.area.read_text(encoding="utf-8")),
        "coastline": coastline["lines"],
        "routes": routes,
        "unknown": unknown_stops,
        "outsideTracks": outside_tracks,
    }

    fragment = r'''<div id="connection-route-review">
  <h2>Yhteysalusreittien AIS-katselmointi</h2>
  <div class="viz-controls">
    <label class="form-label">Reitti<select class="form-select" data-route></select></label>
    <label class="form-label">Alusjakso<select class="form-select" data-period></select></label>
    <label class="form-check form-switch"><input class="form-check-input" type="checkbox" data-toggle="tracks" checked><span class="form-check-label">AIS-ajourat</span></label>
    <label class="form-check form-switch"><input class="form-check-input" type="checkbox" data-toggle="reference" checked><span class="form-check-label">Sovellusreitti</span></label>
    <label class="form-check form-switch"><input class="form-check-input" type="checkbox" data-toggle="unknown" checked><span class="form-check-label">Tuntemattomat pysähdykset</span></label>
    <label class="form-check form-switch"><input class="form-check-input" type="checkbox" data-toggle="outside"><span class="form-check-label">Epävarmat ja ulkopuoliset</span></label>
    <button class="btn btn-ghost" type="button" data-zoom="in">+</button>
    <button class="btn btn-ghost" type="button" data-zoom="out">−</button>
    <button class="btn btn-ghost" type="button" data-zoom="reset">Koko alue</button>
  </div>
  <div class="map-wrap"><svg role="img" aria-label="Yhteysalusten toteutuneet ajourat, laiturit ja pysähdykset"></svg></div>
  <div class="legend text-small">
    <span><i class="actual"></i>Toteutunut AIS-ura</span><span><i class="reference"></i>Sovellusreitti</span>
    <span><i class="main-pier"></i>Päälaituri</span><span><i class="pier"></i>Muu laituri</span>
    <span><i class="unknown"></i>Tuntematon pysähdys</span><span><i class="outside"></i>Epävarma/ulkopuolinen ura</span>
  </div>
  <div class="card detail" aria-live="polite"></div>
</div>
<style>
#connection-route-review{width:100%;color:var(--foreground)}
#connection-route-review h2{margin-bottom:10px}
#connection-route-review .viz-controls{margin-bottom:8px}
#connection-route-review .map-wrap{width:100%;height:650px;min-height:430px}
#connection-route-review svg{width:100%;height:100%;display:block;touch-action:none}
#connection-route-review .land{fill:color-mix(in srgb,var(--foreground) 10%,var(--background));fill-rule:evenodd;pointer-events:none}
#connection-route-review .coast{fill:none;stroke:color-mix(in srgb,var(--foreground) 34%,transparent);stroke-width:.7;vector-effect:non-scaling-stroke;pointer-events:none}
#connection-route-review .actual-line{fill:none;stroke:var(--viz-series-1);stroke-width:1.4;opacity:.38;vector-effect:non-scaling-stroke}
#connection-route-review .reference-line{fill:none;stroke:var(--muted-foreground);stroke-width:2;stroke-dasharray:6 5;opacity:.65;vector-effect:non-scaling-stroke}
#connection-route-review .outside-line{fill:none;stroke:var(--viz-series-4);stroke-width:1.2;opacity:.35;vector-effect:non-scaling-stroke}
#connection-route-review .pier-mark{fill:var(--foreground);stroke:var(--background);stroke-width:1;vector-effect:non-scaling-stroke}
#connection-route-review .main-pier-mark{fill:var(--viz-series-2)}
#connection-route-review .unknown-mark{fill:var(--orange);stroke:var(--background);stroke-width:1;vector-effect:non-scaling-stroke}
#connection-route-review .unknown-mark.possible{fill:var(--purple)}
#connection-route-review .unknown-mark.unmatched{fill:var(--red)}
#connection-route-review .hit{fill:none;stroke:transparent;stroke-width:14;vector-effect:non-scaling-stroke}
#connection-route-review .point-hit{fill:transparent}
#connection-route-review .legend{display:flex;flex-wrap:wrap;gap:14px;margin:8px 0;color:var(--muted-foreground)}
#connection-route-review .legend span{display:inline-flex;align-items:center;gap:6px}
#connection-route-review .legend i{display:inline-block;width:20px;height:3px}
#connection-route-review .legend .actual{background:var(--viz-series-1)}
#connection-route-review .legend .reference{border-top:2px dashed var(--muted-foreground)}
#connection-route-review .legend .outside{background:var(--viz-series-4)}
#connection-route-review .legend .main-pier,#connection-route-review .legend .pier,#connection-route-review .legend .unknown{width:9px;height:9px;border-radius:50%}
#connection-route-review .legend .main-pier{background:var(--viz-series-2)}
#connection-route-review .legend .pier{background:var(--foreground)}
#connection-route-review .legend .unknown{background:var(--orange)}
#connection-route-review .detail{margin-top:8px;min-height:56px}
@media(max-width:520px){#connection-route-review .map-wrap{height:470px}}
</style>
<script src="https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js"></script>
<script>
(()=>{
const root=document.getElementById('connection-route-review'),data=__DATA__,svg=d3.select(root.querySelector('svg'));
const wrap=root.querySelector('.map-wrap'),routeSelect=root.querySelector('[data-route]'),periodSelect=root.querySelector('[data-period]'),detail=root.querySelector('.detail');
const enabled={tracks:true,reference:true,unknown:true,outside:false};let routeId=data.routes[0]?.id||'',period='all',transform=d3.zoomIdentity,viewport;
const decode=e=>{let i=0,lat=0,lng=0,o=[];while(i<e.length){let v=[];for(let a=0;a<2;a++){let r=0,s=0,b;do{b=e.charCodeAt(i++)-63;r|=(b&31)<<s;s+=5}while(b>=32);v.push(r&1?~(r>>1):r>>1)}lat+=v[0];lng+=v[1];o.push([lng/1e5,lat/1e5])}return o};
const coast=data.coastline.map(decode),esc=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
data.routes.forEach(r=>{r.decoded=r.tracks.map(t=>[decode(t[0]),...t.slice(1)]);r.ref=r.reference.map(decode)});data.outsideTracks=data.outsideTracks.map(t=>[decode(t[0]),...t.slice(1)]);
data.routes.forEach(r=>routeSelect.add(new Option(`${r.name} (${r.tracks.length} otosta)`,r.id)));
function selectedRoute(){return data.routes.find(r=>r.id===routeId)}
function refreshPeriods(){periodSelect.innerHTML='';periodSelect.add(new Option('Kaikki luotettavat viikot','all'));const r=selectedRoute();for(const p of r.periods){periodSelect.add(new Option(`${p[1]} · ${p[2]}–${p[3]} (${p[4]} vk)`,`${p[0]}|${p[2]}|${p[3]}`))}period='all'}
function pathText(coords,proj){return coords.map((c,i)=>{const p=proj(c);return`${i?'L':'M'}${p[0].toFixed(1)},${p[1].toFixed(1)}`}).join('')}
function selectedTracks(r){if(period==='all')return r.decoded;const [m,first,last]=period.split('|');return r.decoded.filter(t=>String(t[1])===m&&t[2]>=first&&t[2]<=last)}
function routeSummary(r){const pats=r.patterns.slice(0,5).map(p=>`${esc(p[0].replaceAll('>',' → '))} (${p[1]})`).join('<br>');return`<strong>${esc(r.name)}</strong><br><span class="text-muted">${selectedTracks(r).length} näytettyä AIS-uraa · ${r.periods.length} liikennöintijaksoa</span>${pats?`<hr>${pats}`:''}`}
const zoom=d3.zoom().scaleExtent([1,32]).on('zoom',e=>{transform=e.transform;if(viewport)viewport.attr('transform',transform);if(viewport)viewport.selectAll('[data-r]').attr('r',function(){return Number(this.dataset.r)/transform.k})});
function draw(){const width=Math.max(320,wrap.clientWidth),height=Math.max(430,wrap.clientHeight);svg.attr('viewBox',`0 0 ${width} ${height}`);svg.selectAll('*').remove();const proj=d3.geoMercator().fitExtent([[18,16],[width-18,height-16]],data.area);viewport=svg.append('g').attr('transform',transform);
const closed=coast.filter(l=>l[0]&&l.at(-1)&&l[0][0]===l.at(-1)[0]&&l[0][1]===l.at(-1)[1]);viewport.append('path').attr('class','land').attr('d',closed.map(l=>pathText(l,proj)+'Z').join(''));viewport.append('path').attr('class','coast').attr('d',coast.map(l=>pathText(l,proj)).join(''));
const r=selectedRoute(),actual=selectedTracks(r);if(enabled.reference)viewport.append('g').selectAll('path').data(r.ref).join('path').attr('class','reference-line').attr('d',d=>pathText(d,proj));
if(enabled.tracks){const g=viewport.append('g');g.selectAll('path.actual-line').data(actual).join('path').attr('class','actual-line').attr('d',d=>pathText(d[0],proj));g.selectAll('path.hit').data(actual).join('path').attr('class','hit cursor-interaction').attr('d',d=>pathText(d[0],proj)).on('click',(_,d)=>{detail.innerHTML=`<strong>${esc(d[3])} → ${esc(d[4])}</strong><br><span class="text-muted">MMSI ${d[1]} · viikko ${d[2]} · lähtö ${esc(d[5])} · ${Math.round(d[6]/60)} min</span>`})}
const pg=viewport.append('g');pg.selectAll('circle.point-hit').data(r.piers).join('circle').attr('class','point-hit cursor-interaction').attr('cx',d=>proj([d[1],d[2]])[0]).attr('cy',d=>proj([d[1],d[2]])[1]).attr('data-r',12).attr('r',12/transform.k).on('click',(_,d)=>{detail.innerHTML=`<strong>${esc(d[0])}</strong><br><span class="text-muted">${d[3].toLocaleString('fi-FI')} tunnistettua matkan päätepistettä · ${d[4]} alusta${d[5]?' · päälaituri':''}</span>`});pg.selectAll('circle.pier-mark').data(r.piers).join('circle').attr('class',d=>`pier-mark${d[5]?' main-pier-mark':''}`).attr('cx',d=>proj([d[1],d[2]])[0]).attr('cy',d=>proj([d[1],d[2]])[1]).attr('data-r',d=>d[5]?5:3.3).attr('r',function(){return Number(this.dataset.r)/transform.k});
if(enabled.unknown){const ug=viewport.append('g');ug.selectAll('circle').data(data.unknown).join('circle').attr('class',d=>`unknown-mark ${d[4]} cursor-interaction`).attr('cx',d=>proj([d[1],d[2]])[0]).attr('cy',d=>proj([d[1],d[2]])[1]).attr('data-r',5).attr('r',5/transform.k).on('click',(_,d)=>{detail.innerHTML=`<strong>Tuntematon pysähdys ${d[0]}</strong><br><span class="text-muted">${d[3]} m rannasta · ${esc(d[4])} · ${d[6].toLocaleString('fi-FI')} havaintoa<br>${esc(d[5].replaceAll(';',', '))}</span>`})}
if(enabled.outside){const og=viewport.append('g');og.selectAll('path.outside-line').data(data.outsideTracks).join('path').attr('class','outside-line').attr('d',d=>pathText(d[0],proj));og.selectAll('path.hit').data(data.outsideTracks).join('path').attr('class','hit cursor-interaction').attr('d',d=>pathText(d[0],proj)).on('click',(_,d)=>{detail.innerHTML=`<strong>${esc(d[2])}</strong><br><span class="text-muted">MMSI ${d[1]} · ${esc(d[3])} · ${d[4]}</span>`})}
svg.call(zoom).call(zoom.transform,transform);if(!detail.dataset.selected)detail.innerHTML=routeSummary(r)}
routeSelect.addEventListener('change',()=>{routeId=routeSelect.value;refreshPeriods();transform=d3.zoomIdentity;detail.dataset.selected='';draw()});periodSelect.addEventListener('change',()=>{period=periodSelect.value;detail.dataset.selected='';draw()});root.querySelectorAll('[data-toggle]').forEach(i=>i.addEventListener('change',()=>{enabled[i.dataset.toggle]=i.checked;draw()}));root.querySelector('[data-zoom="in"]').onclick=()=>svg.transition().duration(150).call(zoom.scaleBy,1.8);root.querySelector('[data-zoom="out"]').onclick=()=>svg.transition().duration(150).call(zoom.scaleBy,1/1.8);root.querySelector('[data-zoom="reset"]').onclick=()=>svg.transition().duration(180).call(zoom.transform,d3.zoomIdentity);new ResizeObserver(draw).observe(wrap);refreshPeriods();draw();
})();
</script>'''
    fragment = fragment.replace("__DATA__", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(fragment, encoding="utf-8")
    print(json.dumps({
        "routes": len(routes),
        "sampled_connection_tracks": sum(len(route["tracks"]) for route in routes),
        "outside_tracks": len(outside_tracks),
        "unknown_stops": len(unknown_stops),
        "maximum_track_gap_seconds": args.maximum_track_gap_seconds,
        "maximum_implied_speed_knots": args.maximum_implied_speed_knots,
        "simplification_tolerance_m": args.simplification_tolerance_m,
        "bytes": args.output.stat().st_size,
        "output": str(args.output),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
