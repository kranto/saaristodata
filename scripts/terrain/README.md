# Local OpenFreeMap terrain prototype

This localhost-only prototype uses the same non-rectangular Archipelago Sea
target area as the KMTK and Syke land-cover archives. Its download envelope is
`W 19.0 · S 59.7 · E 23.58061 · N 60.75826`; the exact include and exclude
rectangles are defined in `data-sources/landcover.yml`. It is shown
only on the **OpenFreeMap maasto** base map.

The source data comes directly from Maanmittauslaitos:

- 5 m and 10 m contours from the `korkeuskayra` OGC API Features collection
- ready-made **Rinnevarjoste 8 m** GeoTIFF map sheets from the OGC API Processes
  file service

The hillshade raster tiles make MML's neutral gray transparent and feather
near-neutral pixels. Fully transparent pixels are normalized and the result is
encoded as transparent WebP. Zooms 7-9 are progressively rendered at lower
internal resolutions and lower WebP quality; zoom 10 onwards retains the full
256 px, 64-level, quality-80 rendering. At zooms 7-8 the shoreline alpha is
simplified together with the relief because exact small-island edges are not
visible at overview scale. Zoom 9 retains the exact shoreline alpha while
simplifying the relief. This keeps the small-zoom overview light without
requiring a separate hillshade archive. Raster tiles end at zoom 12
and are overzoomed beyond it to reduce requests and decoded texture memory on
mobile devices.

The API key is read from `saaristodata/.env`. It is used only by the build
script and is never sent to the browser. Generated test files stay in the
ignored `raw/landcover/terrain-test/` directory, exposed by the development app
through its existing `public/data` symlink.

Build with the existing land-cover virtual environment:

```sh
/tmp/saaristolautat-landcover-venv/bin/pip install \
  pillow==12.0.0 pyshp==2.3.1

/tmp/saaristolautat-landcover-venv/bin/python \
  scripts/terrain/build_test_terrain.py
```

The app's localhost controls can independently select 5 m or 10 m contours,
enable the hillshade, and tune their zoom ranges, colour and opacity.

An already generated hillshade archive can be optimized without touching the
source rasters or rebuilding the shoreline mask. This simplifies the complete
RGBA image at zooms 7-9 and copies zooms 10-12 unchanged:

```sh
/tmp/saaristolautat-landcover-venv/bin/python \
  scripts/terrain/optimize_hillshade.py \
  raw/landcover/terrain-test/terrain-hillshade-r1.pmtiles
```
