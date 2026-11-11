# Complementary land-cover pipeline

This directory contains the reproducible pilot pipeline described in
`docs/complementary-landcover-plan.md`.

## Current source decision

The comparison pilot uses the National Land Survey's **KMTK BETA** polygon
collections as its primary source. It provides explicit polygons for rock,
farmland, wetland, meadow, open woodland, sand, extraction areas and urban
areas. KMTK does not provide continuous forest polygons, so the first KMTK
variant intentionally leaves unclassified land to the OpenFreeMap base map.
This makes KMTK's actual coverage visible before Syke is used as a gap filler.

KMTK BETA is for testing only and must not be enabled in production. The
earlier Syke **Maanpeite 2 m 2022** raster pilot remains available as a
comparison and as a candidate for later filling of genuinely unclassified
areas. Both sources are licensed under CC BY 4.0.

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

## Build the KMTK-primary pilot

Create an MML API key and either export it as `MML_API_KEY` or store it in a
local file outside the repository. Then run:

```sh
/tmp/saaristolautat-landcover-venv/bin/python \
  scripts/landcover/download_kmtk.py \
  --area pilot-kustavi-inio-velkua \
  --api-key-file /path/to/mml-api-key

/tmp/saaristolautat-landcover-venv/bin/python \
  scripts/landcover/build_kmtk_geojson.py \
  --area pilot-kustavi-inio-velkua

/tmp/saaristolautat-landcover-venv/bin/python \
  scripts/landcover/build_tiles.py \
  --area pilot-kustavi-inio-velkua \
  --source mml-kmtk-beta \
  --variant kmtk
```

The downloader reads all configured KMTK polygon collections, recursively
splits responses that reach the service limit and deduplicates features by
KMTK identifier. The API key is passed to `curl` through standard input so it
does not appear in process arguments or logs. Generated raw data, normalized
GeoJSON and PMTiles remain ignored; the processing report and
`tiles/landcover-kmtk.json` manifest are tracked.

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

In the development and test application the KMTK variant is the default.
Append `?landcover=syke` to compare it with the earlier raster variant, or
`?landcover=0` to disable the complementary layer. Production builds do not
enable either pilot.

## Tests

```sh
/tmp/saaristolautat-landcover-venv/bin/python -m unittest discover \
  -s scripts/landcover/tests
```

