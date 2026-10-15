#!/usr/bin/env python3
"""Render one route's filtered AIS tracks as a map-free standalone HTML page."""

from __future__ import annotations

import argparse
import html
import json
import math
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("review_map", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--route", required=True)
    return parser.parse_args()


def extract_payload(path: Path) -> dict:
    source = path.read_text(encoding="utf-8")
    marker = ",data={&quot;"
    start = source.find(marker)
    if start < 0:
        raise ValueError(f"Embedded review payload not found in {path}")
    payload, _ = json.JSONDecoder().raw_decode(html.unescape(source[start + len(",data=") :]))
    return payload


def decode_polyline(encoded: str) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []
    index = latitude = longitude = 0
    while index < len(encoded):
        deltas = []
        for _ in range(2):
            value = shift = 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                value |= (byte & 31) << shift
                shift += 5
                if byte < 32:
                    break
            deltas.append(~(value >> 1) if value & 1 else value >> 1)
        latitude += deltas[0]
        longitude += deltas[1]
        result.append((longitude / 100_000, latitude / 100_000))
    return result


def mercator(point: tuple[float, float]) -> tuple[float, float]:
    longitude, latitude = point
    x = math.radians(longitude)
    y = math.log(math.tan(math.pi / 4 + math.radians(latitude) / 2))
    return x, -y


def main() -> None:
    args = parse_args()
    payload = extract_payload(args.review_map)
    route = next((item for item in payload["routes"] if item["name"] == args.route), None)
    if route is None:
        raise ValueError(f"Route not found: {args.route}")

    tracks = [decode_polyline(track[0]) for track in route["tracks"]]
    projected = [[mercator(point) for point in track] for track in tracks if len(track) > 1]
    all_points = [point for track in projected for point in track]
    min_x = min(point[0] for point in all_points)
    max_x = max(point[0] for point in all_points)
    min_y = min(point[1] for point in all_points)
    max_y = max(point[1] for point in all_points)

    width, height, margin = 1600, 1000, 24
    scale = min((width - 2 * margin) / (max_x - min_x), (height - 2 * margin) / (max_y - min_y))
    offset_x = (width - (max_x - min_x) * scale) / 2
    offset_y = (height - (max_y - min_y) * scale) / 2

    def screen(point: tuple[float, float]) -> tuple[float, float]:
        return offset_x + (point[0] - min_x) * scale, offset_y + (point[1] - min_y) * scale

    paths = []
    for track in projected:
        coordinates = [screen(point) for point in track]
        commands = [f"M{coordinates[0][0]:.2f},{coordinates[0][1]:.2f}"]
        commands.extend(f"L{x:.2f},{y:.2f}" for x, y in coordinates[1:])
        paths.append(f'<path d="{"".join(commands)}"/>')

    document = f'''<!doctype html>
<html lang="fi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(route["name"])} – suodatetut AIS-ajourat</title>
<style>
html,body,svg{{width:100%;height:100%;margin:0;overflow:hidden;background:#fff}}
svg{{display:block;touch-action:none;cursor:grab}}
svg.dragging{{cursor:grabbing}}
path{{fill:none;stroke:#168cff;stroke-width:1.15;stroke-opacity:.34;vector-effect:non-scaling-stroke}}
</style>
</head>
<body>
<svg viewBox="0 0 {width} {height}" role="img" aria-label="Houtskarin ja Iniön suodatetut AIS-ajourat">
<g>{''.join(paths)}</g>
</svg>
<script>
const svg=document.querySelector('svg');
let box={{x:0,y:0,w:{width},h:{height}}},drag=null;
const apply=()=>svg.setAttribute('viewBox',`${{box.x}} ${{box.y}} ${{box.w}} ${{box.h}}`);
svg.addEventListener('wheel',event=>{{
  event.preventDefault();
  const rect=svg.getBoundingClientRect(),factor=Math.exp(event.deltaY*.0012);
  const x=box.x+(event.clientX-rect.left)/rect.width*box.w;
  const y=box.y+(event.clientY-rect.top)/rect.height*box.h;
  box.x=x-(x-box.x)*factor;box.y=y-(y-box.y)*factor;box.w*=factor;box.h*=factor;apply();
}},{{passive:false}});
svg.addEventListener('pointerdown',event=>{{drag={{x:event.clientX,y:event.clientY,bx:box.x,by:box.y}};svg.setPointerCapture(event.pointerId);svg.classList.add('dragging')}});
svg.addEventListener('pointermove',event=>{{if(!drag)return;const r=svg.getBoundingClientRect();box.x=drag.bx-(event.clientX-drag.x)*box.w/r.width;box.y=drag.by-(event.clientY-drag.y)*box.h/r.height;apply()}});
svg.addEventListener('pointerup',()=>{{drag=null;svg.classList.remove('dragging')}});
svg.addEventListener('dblclick',()=>{{box={{x:0,y:0,w:{width},h:{height}}};apply()}});
</script>
</body>
</html>'''
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(document, encoding="utf-8")
    print(json.dumps({"route": route["name"], "tracks": len(projected), "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
