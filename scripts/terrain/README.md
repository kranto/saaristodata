# Local OpenFreeMap terrain prototype

This localhost-only prototype covers the same Archipelago Sea area as the KMTK
and Syke land-cover archives: `W 19.0 · S 59.7 · E 23.0 · N 60.7`. It is shown
only on the **OpenFreeMap maasto** base map.

The source data comes directly from Maanmittauslaitos:

- 5 m and 10 m contours from the `korkeuskayra` OGC API Features collection
- ready-made **Rinnevarjoste 8 m** GeoTIFF map sheets from the OGC API Processes
  file service

The hillshade raster tiles make MML's neutral gray transparent and feather
near-neutral pixels. Fully transparent pixels are normalized, the gray channel
is quantized to 64 levels, and the result is encoded as transparent WebP at
quality 80. This keeps the flat sea from darkening while retaining the light
and dark relief on land. The full 8 m raster is stored in a PMTiles archive, so
the browser loads only the tiles visible in the current viewport. Raster tiles
end at zoom 12 and are overzoomed beyond it to reduce requests and decoded
texture memory on mobile devices.

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
