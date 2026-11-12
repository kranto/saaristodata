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
  --area pilot-archipelago-sea \
  --api-key-file /path/to/mml-api-key

/tmp/saaristolautat-landcover-venv/bin/python \
  scripts/landcover/build_kmtk_geojson.py \
  --area pilot-archipelago-sea

/tmp/saaristolautat-landcover-venv/bin/python \
  scripts/landcover/build_tiles.py \
  --area pilot-archipelago-sea \
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
archives begin at zoom 8. Zooms 8 and 9 are built in a separate overview pass
with stronger Tippecanoe simplification and only the renderable `class`
attribute. No overview features are dropped to meet a tile-size limit. The
unchanged detail pass covers zooms 10 through 14, and the two passes are merged
before PMTiles conversion. Per-zoom tile counts and sizes are added to the
tracked JSON report. It also writes the tracked
`tiles/landcover.json` active archive manifest with its checksum, bounds, zoom
range and attribution. Existing archives are preserved unless `--force` is
used.

In the development and test application the KMTK variant is the default.
Append `?landcover=syke` to compare it with the earlier raster variant, or
`?landcover=0` to disable the complementary layer. Production builds do not
enable either pilot.

## Build the Syke forest fallback

KMTK has no continuous forest polygon collection. Build a forest-only Syke
variant at 20 metre resolution to fill missing OpenStreetMap forest cover
underneath the more specific KMTK polygons:

```sh
/tmp/saaristolautat-landcover-venv/bin/python \
  scripts/landcover/download_syke.py \
  --area pilot-archipelago-sea \
  --variant syke-forest \
  --output-resolution-metres 20

/tmp/saaristolautat-landcover-venv/bin/python \
  scripts/landcover/build_geojson.py \
  --area pilot-archipelago-sea \
  --variant syke-forest \
  --include-class forest

/tmp/saaristolautat-landcover-venv/bin/python \
  scripts/landcover/build_tiles.py \
  --area pilot-archipelago-sea \
  --source syke-maanpeite-2022 \
  --variant syke-forest
```

### Smoothed forest polygons

The smoother upsamples the existing 20 metre forest mask to a 5 metre working
grid, applies a conservative 10 metre box-filter radius and vectorizes the 50%
contour. Large rasters are processed in overlapping chunks to keep memory use
bounded. This is cartographic smoothing; it does not increase source accuracy.

```sh
/tmp/saaristolautat-landcover-venv/bin/python \
  scripts/landcover/build_geojson.py \
  --area pilot-archipelago-sea \
  --variant syke-forest-smoothed \
  --include-class forest \
  --input raw/landcover/syke-maanpeite-2022/pilot-archipelago-sea-syke-forest.tif \
  --clip-to-area \
  --smooth-factor 4 \
  --smooth-radius-pixels 2

/tmp/saaristolautat-landcover-venv/bin/python \
  scripts/landcover/build_tiles.py \
  --area pilot-archipelago-sea \
  --source syke-maanpeite-2022 \
  --variant syke-forest-smoothed \
  --force
```

The smoothed archive is the application's default forest fallback. Compare it
with the retained original using the local application:

- smoothed: `?screenshotCenter=20.76234,60.24975&screenshotZoom=13`
- original: `?forest=original&screenshotCenter=20.76234,60.24975&screenshotZoom=13`

## Tests

```sh
/tmp/saaristolautat-landcover-venv/bin/python -m unittest discover \
  -s scripts/landcover/tests
```

