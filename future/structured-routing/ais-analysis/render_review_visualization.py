#!/usr/bin/env python3
"""Render the route-review GeoJSON as an inline Codex visualization fragment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("review", type=Path)
    parser.add_argument("saaristo", type=Path)
    parser.add_argument("area", type=Path)
    parser.add_argument("coastline", type=Path)
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    review = json.loads(args.review.read_text(encoding="utf-8"))
    saaristo = json.loads(args.saaristo.read_text(encoding="utf-8-sig"))
    area = json.loads(args.area.read_text(encoding="utf-8"))
    coastline = json.loads(args.coastline.read_text(encoding="utf-8"))
    features = []
    for feature in review["features"]:
        features.append(feature)
    labels = []
    for feature in saaristo.get("features", []):
        properties = feature.get("properties", {})
        geometry = feature.get("geometry", {})
        if properties.get("stype") != "area" or properties.get("ssubtype") not in {"mun1", "mun2"}:
            continue
        if geometry.get("type") != "Point":
            continue
        lng, lat = geometry["coordinates"]
        if 19.8 <= lng <= 23.2 and 59.65 <= lat <= 60.8:
            labels.append({"name": properties.get("sname", "").replace("<br>", " "), "coordinates": [lng, lat]})
    payload = {"area": area, "coastline": coastline, "features": features, "labels": labels}

    fragment = r'''<div id="ais-route-review">
  <h2>Reittien ja pysähdysten katselmointi</h2>
  <div class="viz-controls" aria-label="Karttatasot">
    <label class="form-check form-switch"><input class="form-check-input" type="checkbox" data-layer="assigned_route" checked><span class="form-check-label">Reittiehdotukset</span></label>
    <label class="form-check form-switch"><input class="form-check-input" type="checkbox" data-layer="known_pier" checked><span class="form-check-label">Tunnetut laiturit</span></label>
    <label class="form-check form-switch"><input class="form-check-input" type="checkbox" data-layer="unknown_stop" checked><span class="form-check-label">Tuntemattomat pysähdykset</span></label>
    <button class="btn btn-ghost" type="button" data-zoom="in" aria-label="Lähennä karttaa">+</button>
    <button class="btn btn-ghost" type="button" data-zoom="out" aria-label="Loitonna karttaa">−</button>
    <button class="btn btn-ghost" type="button" data-zoom="reset">Näytä koko alue</button>
  </div>
  <div class="map-wrap">
    <svg role="img" aria-labelledby="ais-map-title ais-map-desc">
      <title id="ais-map-title">Saaristomeren reittiehdotukset ja pysähdyspaikat</title>
      <desc id="ais-map-desc">Viikkopäätelmillä tunnistetut reitit, käytetyt tunnetut laiturit ja 300 metrin klustereiksi yhdistetyt tuntemattomat pysähdyspaikat.</desc>
    </svg>
  </div>
  <div class="legend text-small" aria-label="Selite">
    <span><i class="route-mark"></i> Reittiehdotus</span>
    <span><i class="pier-mark"></i> Tunnettu laituri</span>
    <span><i class="unused-mark"></i> Ei AIS-käyntejä</span>
    <span><i class="unknown-mark"></i> Tuntematon pysähdys</span>
    <span>Rantaviiva © OpenStreetMapin tekijät</span>
  </div>
  <div class="card detail" aria-live="polite">Valitse reitti tai piste nähdäksesi tiedot.</div>
</div>
<style>
  #ais-route-review { color: var(--foreground); width: 100%; }
  #ais-route-review h2 { margin-bottom: 10px; }
  #ais-route-review .viz-controls { margin-bottom: 8px; }
  #ais-route-review .map-wrap { width: 100%; height: 72vh; min-height: 520px; max-height: 820px; }
  #ais-route-review svg { width: 100%; height: 100%; display: block; touch-action: none; }
  #ais-route-review .area { fill: color-mix(in srgb, var(--blue) 8%, transparent); stroke: var(--border); stroke-width: 1.2; }
  #ais-route-review .land { fill: color-mix(in srgb, var(--foreground) 10%, var(--background)); fill-rule: evenodd; pointer-events: none; }
  #ais-route-review .coastline { fill: none; stroke: color-mix(in srgb, var(--foreground) 35%, transparent); stroke-width: .8; vector-effect: non-scaling-stroke; pointer-events: none; }
  #ais-route-review .route { fill: none; stroke: var(--viz-series-1); stroke-width: 1.6; opacity: .55; vector-effect: non-scaling-stroke; }
  #ais-route-review .route.is-selected { stroke-width: 4; opacity: 1; }
  #ais-route-review .pier { fill: var(--foreground); opacity: .58; stroke: var(--background); stroke-width: 1; vector-effect: non-scaling-stroke; }
  #ais-route-review .pier-unused { fill: var(--background); opacity: 1; stroke: var(--muted-foreground); stroke-width: 1.5; }
  #ais-route-review .unknown { fill: var(--orange); opacity: .72; stroke: var(--background); stroke-width: 1.2; vector-effect: non-scaling-stroke; }
  #ais-route-review .map-label { fill: var(--muted-foreground); font-size: 11px; text-anchor: middle; pointer-events: none; }
  #ais-route-review .legend { display: flex; flex-wrap: wrap; gap: 14px; margin: 8px 0; color: var(--muted-foreground); }
  #ais-route-review .legend span { display: inline-flex; align-items: center; gap: 6px; }
  #ais-route-review .legend i { display: inline-block; flex: none; }
  #ais-route-review .route-mark { width: 22px; height: 2px; background: var(--viz-series-1); }
  #ais-route-review .pier-mark, #ais-route-review .unused-mark, #ais-route-review .unknown-mark { width: 9px; height: 9px; border-radius: 50%; }
  #ais-route-review .pier-mark { background: var(--foreground); opacity: .58; }
  #ais-route-review .unused-mark { border: 1.5px solid var(--muted-foreground); }
  #ais-route-review .unknown-mark { background: var(--orange); }
  #ais-route-review .detail { margin-top: 8px; min-height: 48px; }
  #ais-route-review .map-hit { fill: transparent; stroke: transparent; }
  @media (max-width: 520px) {
    #ais-route-review .map-wrap { min-height: 430px; }
    #ais-route-review svg { height: 100%; }
  }
</style>
<script src="https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js"></script>
<script>
(() => {
  const root = document.getElementById('ais-route-review');
  const data = __DATA__;
  const svg = d3.select(root.querySelector('svg'));
  const wrap = root.querySelector('.map-wrap');
  const detail = root.querySelector('.detail');
  const enabled = { assigned_route: true, known_pier: true, unknown_stop: true };
  let selected = null;
  let viewport = null;
  let transform = d3.zoomIdentity;

  const zoom = d3.zoom()
    .scaleExtent([1, 24])
    .on('zoom', event => {
      transform = event.transform;
      if (viewport) viewport.attr('transform', transform);
      if (viewport) {
        viewport.selectAll('[data-base-radius]').attr('r', function() {
          return Number(this.dataset.baseRadius) / transform.k;
        });
      }
    });

  const decodePolyline = encoded => {
    const coordinates = [];
    let index = 0;
    let lat = 0;
    let lon = 0;
    while (index < encoded.length) {
      const values = [];
      for (let axis = 0; axis < 2; axis += 1) {
        let result = 0;
        let shift = 0;
        let byte;
        do {
          byte = encoded.charCodeAt(index++) - 63;
          result |= (byte & 0x1f) << shift;
          shift += 5;
        } while (byte >= 0x20);
        values.push(result & 1 ? ~(result >> 1) : result >> 1);
      }
      lat += values[0];
      lon += values[1];
      coordinates.push([lon / 100000, lat / 100000]);
    }
    return coordinates;
  };
  const coastlines = data.coastline.lines.map(decodePolyline);

  const escapeHtml = value => String(value).replace(/[&<>"']/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[character]);
  const vesselLine = properties => properties.vessel_names
    ? `<br><span class="text-muted">Alukset: ${escapeHtml(properties.vessel_names.split(';').join(', '))}</span>`
    : '';

  const describe = feature => {
    const p = feature.properties;
    if (p.review_category === 'assigned_route') {
      return `<strong>${escapeHtml(p.route_name)}</strong><br><span class="text-muted">${p.assigned_weeks} pääteltyä alusviikkoa · ${p.vessels} alusta</span>${vesselLine(p)}`;
    }
    if (p.review_category === 'known_pier') {
      return `<strong>${escapeHtml(p.pier)}</strong><br><span class="text-muted">${p.calls.toLocaleString('fi-FI')} käyntiä · ${p.vessels} alusta</span>${vesselLine(p)}`;
    }
    return `<strong>Tuntematon pysähdysklusteri ${p.cluster_id}</strong><br><span class="text-muted">${p.active_days_max} aktiivista päivää · ${p.vessels} alusta · ${p.observations.toLocaleString('fi-FI')} havaintoa · ${p.distance_to_coast_m} m rannasta</span>${vesselLine(p)}`;
  };

  function draw() {
    const width = Math.max(320, wrap.clientWidth);
    const height = Math.max(width < 520 ? 430 : 520, wrap.clientHeight || 520);
    svg.attr('viewBox', `0 0 ${width} ${height}`);
    svg.selectAll('*:not(title):not(desc)').remove();
    const projection = d3.geoMercator().fitExtent([[20, 18], [width - 20, height - 18]], data.area);
    const path = d3.geoPath(projection);
    viewport = svg.append('g').attr('class', 'map-viewport').attr('transform', transform);
    viewport.append('path').datum(data.area).attr('class', 'area').attr('d', path);
    const projectedLine = coordinates => coordinates.map((coordinate, index) => {
      const [x, y] = projection(coordinate);
      return `${index ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`;
    }).join('');
    const closedCoastlines = coastlines.filter(line => {
      const first = line[0];
      const last = line[line.length - 1];
      return first && last && first[0] === last[0] && first[1] === last[1];
    });
    viewport.append('path')
      .attr('class', 'land')
      .attr('d', closedCoastlines.map(line => `${projectedLine(line)}Z`).join(''));
    viewport.append('path')
      .attr('class', 'coastline')
      .attr('d', coastlines.map(projectedLine).join(''));

    const routes = data.features.filter(d => d.properties.review_category === 'assigned_route');
    const routeLayer = viewport.append('g').attr('data-layer-group', 'assigned_route');
    routeLayer.selectAll('path').data(routes).join('path')
      .attr('class', d => `route cursor-interaction${selected === d ? ' is-selected' : ''}`)
      .attr('d', path)
      .attr('role', 'button')
      .attr('aria-label', d => `${d.properties.route_name}, ${d.properties.assigned_weeks} alusviikkoa`)
      .on('click', (_event, d) => { selected = d; detail.innerHTML = describe(d); draw(); });

    const pointLayer = viewport.append('g');
    for (const category of ['known_pier', 'unknown_stop']) {
      const points = data.features.filter(d => d.properties.review_category === category);
      const group = pointLayer.append('g').attr('data-layer-group', category);
      group.selectAll('circle.map-hit').data(points).join('circle')
        .attr('class', 'map-hit cursor-interaction')
        .attr('cx', d => projection(d.geometry.coordinates)[0])
        .attr('cy', d => projection(d.geometry.coordinates)[1])
        .attr('data-base-radius', 12)
        .attr('r', 12 / transform.k)
        .on('click', (_event, d) => { selected = d; detail.innerHTML = describe(d); draw(); });
      const circles = group.selectAll('circle.mark').data(points).join('circle')
        .attr('class', d => `${category === 'known_pier' ? `pier${d.properties.calls ? '' : ' pier-unused'}` : 'unknown'} mark cursor-interaction`)
        .attr('cx', d => projection(d.geometry.coordinates)[0])
        .attr('cy', d => projection(d.geometry.coordinates)[1])
        .attr('data-base-radius', d => {
          const radius = category === 'known_pier'
            ? Math.max(d.properties.calls ? 2.2 : 3.5, Math.min(7, 1.8 + Math.log10(1 + d.properties.calls)))
            : Math.max(3, Math.min(9, 2 + Math.log10(1 + d.properties.observations)));
          return radius + (selected === d ? 3 : 0);
        })
        .attr('r', function() { return Number(this.dataset.baseRadius) / transform.k; })
        .attr('role', 'button')
        .attr('aria-label', d => d.properties.pier || `Tuntematon pysähdys ${d.properties.cluster_id}`)
        .on('click', (_event, d) => { selected = d; detail.innerHTML = describe(d); draw(); });
    }

    viewport.append('g').selectAll('text').data(data.labels).join('text')
      .attr('class', 'map-label')
      .attr('x', d => projection(d.coordinates)[0])
      .attr('y', d => projection(d.coordinates)[1])
      .attr('dy', -7)
      .text(d => d.name);
    root.querySelectorAll('[data-layer-group]').forEach(group => {
      group.style.display = enabled[group.dataset.layerGroup] ? '' : 'none';
    });
    svg.call(zoom).call(zoom.transform, transform);
  }

  root.querySelectorAll('[data-layer]').forEach(input => {
    input.addEventListener('change', () => { enabled[input.dataset.layer] = input.checked; draw(); });
  });
  root.querySelector('[data-zoom="in"]').addEventListener('click', () => {
    svg.transition().duration(180).call(zoom.scaleBy, 1.8);
  });
  root.querySelector('[data-zoom="out"]').addEventListener('click', () => {
    svg.transition().duration(180).call(zoom.scaleBy, 1 / 1.8);
  });
  root.querySelector('[data-zoom="reset"]').addEventListener('click', () => {
    svg.transition().duration(220).call(zoom.transform, d3.zoomIdentity);
  });
  new ResizeObserver(draw).observe(wrap);
  draw();
})();
</script>'''
    fragment = fragment.replace("__DATA__", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(fragment, encoding="utf-8")
    print(f"Wrote {args.output} ({args.output.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
