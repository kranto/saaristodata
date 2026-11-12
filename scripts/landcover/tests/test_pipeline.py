from __future__ import annotations

import sys
import unittest
import urllib.parse
from pathlib import Path

import numpy as np


SCRIPT_DIRECTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIRECTORY))

from common import area_config, load_manifest, source_config  # noqa: E402
from build_geojson import box_blur  # noqa: E402
from download_kmtk import collection_url, split_bbox  # noqa: E402
from download_syke import build_url  # noqa: E402


class PipelineConfigurationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = load_manifest()
        self.area = area_config(self.manifest, "pilot-kustavi-inio-velkua")
        self.source = source_config(self.manifest, "syke-maanpeite-2022")

    def test_wcs_url_contains_bounds_and_resampling(self) -> None:
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(build_url(self.source, self.area)).query)
        self.assertEqual(query["SCALEFACTOR"], ["0.2"])
        self.assertEqual(query["SUBSET"], ["N(6688000,6740000)", "E(170000,228000)"])
        self.assertEqual(query["coverageId"], ["Maanpeite2022Scalgo"])

    def test_wcs_url_accepts_coarser_forest_resolution(self) -> None:
        query = urllib.parse.parse_qs(
            urllib.parse.urlsplit(build_url(self.source, self.area, 20)).query
        )
        self.assertEqual(query["SCALEFACTOR"], ["0.1"])

    def test_selected_classes_are_normalized(self) -> None:
        self.assertEqual(
            set(self.source["class_mapping"].values()),
            {"bare", "farmland", "forest", "open", "rock"},
        )

    def test_tiles_begin_at_close_zoom(self) -> None:
        processing = self.manifest["processing"]
        self.assertEqual(processing["tile_minzoom"], 10)
        self.assertEqual(processing["tile_maxzoom"], 14)

    def test_kmtk_collections_cover_selected_polygon_classes(self) -> None:
        source = source_config(self.manifest, "mml-kmtk-beta")
        self.assertEqual(source["status"], "pilot-only")
        self.assertEqual(
            set(source["collection_mapping"].values()),
            {"bare", "farmland", "open", "rock", "sand", "urban", "wetland"},
        )
        self.assertNotIn("forest", source["collection_mapping"].values())

    def test_kmtk_collection_url_has_bounded_query(self) -> None:
        source = source_config(self.manifest, "mml-kmtk-beta")
        url = collection_url(source["service_url"], "rock_area", self.area["bbox_wgs84"])
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        self.assertEqual(query["bbox"], ["21.05,60.2,22.0,60.7"])
        self.assertEqual(query["limit"], ["10000"])

    def test_kmtk_bbox_split_preserves_extent(self) -> None:
        first, second = split_bbox(self.area["bbox_wgs84"])
        self.assertEqual(first[:2], [21.05, 60.2])
        self.assertEqual(second[2:], [22.0, 60.7])
        self.assertEqual(first[2], second[0])

    def test_expanded_kmtk_pilot_covers_full_route_area(self) -> None:
        expanded = area_config(self.manifest, "pilot-archipelago-sea")
        self.assertEqual(expanded["bbox_wgs84"], [19.0, 59.7, 23.0, 60.7])
        self.assertEqual(expanded["bbox_epsg3067"], [50000, 6624000, 282000, 6757000])

    def test_forest_smoothing_pilot_uses_kumlinge_seglinge_bounds(self) -> None:
        pilot = area_config(self.manifest, "pilot-kumlinge-seglinge")
        self.assertEqual(pilot["bbox_wgs84"], [20.54017, 60.18646, 20.98451, 60.31304])
        self.assertEqual(pilot["bbox_epsg3067"], [142000, 6687000, 168000, 6704000])

    def test_box_blur_preserves_shape_and_constant_values(self) -> None:
        values = np.full((5, 7), 0.75, dtype=np.float32)
        blurred = box_blur(values, radius=2)
        self.assertEqual(blurred.shape, values.shape)
        np.testing.assert_allclose(blurred, values, rtol=0, atol=1e-6)


if __name__ == "__main__":
    unittest.main()
