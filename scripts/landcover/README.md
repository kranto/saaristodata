# Complementary land-cover pipeline

This directory contains the reproducible land-cover pipeline described in
`docs/complementary-landcover-plan.md`.

## Current source decision

The terrain data uses the National Land Survey's **KMTK BETA** polygon
collections as its primary source. It provides explicit polygons for rock,
farmland, wetland, meadow, open woodland, sand, extraction areas and urban
areas. KMTK does not provide continuous forest polygons, so the first KMTK
variant intentionally leaves unclassified land to the OpenFreeMap base map.
This makes KMTK's actual coverage visible before Syke is used as a gap filler.

KMTK is still a BETA service and its data model can change before the final
release. Syke **Maanpeite 2 m 2022** supplies the smoothed forest fallback.
Both sources are licensed under CC BY 4.0.

Source URLs, class mappings, internal area bounds and processing thresholds are kept
in `data-sources/landcover.yml`.

## Environment

Create a virtual environment outside the repository or in an ignored local
directory and install the pinned dependencies:

```sh
python3 -m venv /tmp/saaristolautat-landcover-venv
/tmp/saaristolautat-landcover-venv/bin/pip install \
  -r scripts/landcover/requirements.txt
```

## Build the KMTK-primary dataset

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
  --variant kmtk \
  --output tiles/landcover-archipelago-sea-kmtk.pmtiles
```

The downloader reads all configured KMTK polygon collections, recursively
splits responses that reach the service limit and deduplicates features by
KMTK identifier. The API key is passed to `curl` through standard input so it
does not appear in process arguments or logs. Generated raw data, normalized
GeoJSON and PMTiles remain ignored; the processing report and
`tiles/landcover-kmtk.json` manifest are tracked.

Build the compact urban-area archive used by the application's default map
from the same downloaded KMTK data and with the same processing and tile
settings:

```sh
/tmp/saaristolautat-landcover-venv/bin/python \
  scripts/landcover/build_kmtk_geojson.py \
  --area pilot-archipelago-sea \
  --include-collection urban_area \
  --variant kmtk-urban

/tmp/saaristolautat-landcover-venv/bin/python \
  scripts/landcover/build_tiles.py \
  --area pilot-archipelago-sea \
  --source mml-kmtk-beta \
  --variant kmtk-urban \
  --output tiles/landcover-archipelago-sea-kmtk-urban.pmtiles
```

The full KMTK archive remains the terrain map's source. The smaller urban
archive contains only features originating from KMTK's `urban_area`
collection and is used for the simplified default map.

## Tile generation

Install `tippecanoe` and the `pmtiles` CLI before running the build commands.
The builder creates the ignored PMTiles archive at the requested output path
and keeps its MBTiles intermediate under `work/landcover/`. The archives begin
at zoom 8. Zooms 8 and 9 are built in a separate overview pass
with stronger Tippecanoe simplification and only the renderable `class`
attribute. No overview features are dropped to meet a tile-size limit. The
unchanged detail pass covers zooms 10 through 14, and the two passes are merged
before PMTiles conversion. Per-zoom tile counts and sizes are added to the
tracked JSON report and the variant-specific active archive manifest with its
checksum, bounds, zoom range and attribution. Existing archives are preserved
unless `--force` is used.

## Build the smoothed Syke forest fallback

KMTK has no continuous forest polygon collection. Download a forest-only Syke
source raster at 20 metre resolution to fill missing OpenStreetMap forest
cover underneath the more specific KMTK polygons:

```sh
/tmp/saaristolautat-landcover-venv/bin/python \
  scripts/landcover/download_syke.py \
  --area pilot-archipelago-sea \
  --variant syke-forest \
  --output-resolution-metres 20

```

The smoother upsamples the downloaded 20 metre forest mask to a 5 metre working
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
  --output tiles/landcover-archipelago-sea-syke-forest-smoothed.pmtiles \
  --force
```

The smoothed archive is the application's only forest fallback. The source
raster is retained for reproducibility; an unsmoothed vector-tile variant is
not built or published.

## Published archives

Only the three archives listed in `tiles/published-landcover.json` and in the
`published_archives` section of `data-sources/landcover.yml` are release data.
Their public names intentionally omit the internal `pilot` area prefix. Verify
file sizes and SHA-256 checksums against the publication manifest before
copying the archives to a server.

## Tests

```sh
/tmp/saaristolautat-landcover-venv/bin/python -m unittest discover \
  -s scripts/landcover/tests
```

