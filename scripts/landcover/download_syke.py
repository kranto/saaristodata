#!/usr/bin/env python3
"""Download a bounded, resampled Syke land-cover GeoTIFF via WCS."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from common import REPO_ROOT, area_config, load_manifest, source_config


DEFAULT_SOURCE = "syke-maanpeite-2022"


def build_url(source: dict, area: dict) -> str:
    west, south, east, north = area["bbox_epsg3067"]
    native_resolution = float(source["native_resolution_metres"])
    output_resolution = float(area["output_resolution_metres"])
    scale_factor = native_resolution / output_resolution
    query = {
        "service": "WCS",
        "version": "2.0.1",
        "request": "GetCoverage",
        "coverageId": source["coverage_id"],
        "SUBSET": [f"N({south},{north})", f"E({west},{east})"],
        "subsettingcrs": "http://www.opengis.net/def/crs/EPSG/0/3067",
        "format": "image/tiff",
        "SCALEFACTOR": f"{scale_factor:.12g}",
    }
    return f"{source['service_url']}?{urllib.parse.urlencode(query, doseq=True)}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--area", default="pilot-kustavi-inio-velkua")
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--print-url", action="store_true")
    args = parser.parse_args()

    manifest = load_manifest()
    area = area_config(manifest, args.area)
    source = source_config(manifest, args.source)
    if source.get("status") != "active":
        raise ValueError(f"Source {args.source!r} is not active")

    output = args.output or (
        REPO_ROOT / "raw" / "landcover" / args.source / f"{args.area}.tif"
    )
    url = build_url(source, area)
    if args.print_url:
        print(url)
        return
    if output.exists() and not args.force:
        raise FileExistsError(f"{output} already exists; use --force to replace it")

    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=output.name, dir=output.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "saaristolautat-landcover/1"})
        with urllib.request.urlopen(request, timeout=300) as response, temporary.open("wb") as stream:
            while chunk := response.read(1024 * 1024):
                stream.write(chunk)
        if temporary.stat().st_size < 1024:
            raise RuntimeError("WCS response is unexpectedly small")
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)

    receipt = {
        "area": args.area,
        "source": args.source,
        "downloaded_at": datetime.now(UTC).isoformat(),
        "request_url": url,
        "bytes": output.stat().st_size,
        "sha256": sha256(output),
        "output": str(output.relative_to(REPO_ROOT)),
    }
    receipt_path = output.with_suffix(".receipt.json")
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()

