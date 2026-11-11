# Complementary land-cover pipeline

This directory contains the reproducible pilot pipeline described in
`docs/complementary-landcover-plan.md`.

## Current source decision

The active base source is Syke's **Maanpeite 2 m 2022** categorical raster.
It covers Finland, including Åland, is licensed under CC BY 4.0 and supports
bounded GeoTIFF downloads through WCS without an API key.

The old National Land Survey Topographic Database remains a possible
supplement for farmland, meadow, wetland and open-area polygons. It is not a
sufficient forest source: its forest vegetation classes are cartographic
points rather than polygons. Its open OGC API Features service also requires a
user-specific API key.

Source URLs, class mappings, pilot bounds and processing thresholds are kept
in `data-sources/landcover.yml`.

## Environment

Create a virtual environment outside the repository or in an ignored local
directory and install the pinned dependencies:

```sh
python3 -m venv /tmp/saaristolautat-landcover-venv
/tmp/saaristolautat-landcover-venv/bin/pip install \
  -r scripts/landcover/requirements.txt
```

## Download the pilot raster

```sh
/tmp/saaristolautat-landcover-venv/bin/python \
  scripts/landcover/download_syke.py \
  --area pilot-kustavi-inio-velkua
```

The command downloads a 10 m categorical GeoTIFF into the ignored
`raw/landcover/` directory. It also writes a receipt containing the exact WCS
request, timestamp, size and SHA-256 checksum. Existing files are not replaced
unless `--force` is supplied.

Use `--print-url` to inspect the request without downloading data.

## Build normalized GeoJSON

```sh
/tmp/saaristolautat-landcover-venv/bin/python \
  scripts/landcover/build_geojson.py \
  --area pilot-kustavi-inio-velkua
```

The builder reclassifies selected source pixels, removes polygons below the
class-specific area thresholds, simplifies geometries in EPSG:3067 and writes
WGS84 GeoJSON into the ignored `work/landcover/` directory. A small JSON report
with raster dimensions, class counts, output sizes and areas is written to the
tracked `reports/` directory.

## Build PMTiles

Install `tippecanoe` and the `pmtiles` CLI, then run:

```sh
/tmp/saaristolautat-landcover-venv/bin/python \
  scripts/landcover/build_tiles.py \
  --area pilot-kustavi-inio-velkua
```

The builder creates ignored MBTiles and PMTiles archives in `tiles/`. The
pilot begins at zoom 10 because a lower minimum zoom would require dropping
most of its detailed polygons. Per-zoom tile counts and sizes are added to the
tracked JSON report. It also writes the tracked `tiles/landcover.json` active
archive manifest with its checksum, bounds, zoom range and attribution.
Existing archives are preserved unless `--force` is used.

## Tests

```sh
/tmp/saaristolautat-landcover-venv/bin/python -m unittest discover \
  -s scripts/landcover/tests
```

