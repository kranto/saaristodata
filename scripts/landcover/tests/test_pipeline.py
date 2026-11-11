from __future__ import annotations

import sys
import unittest
import urllib.parse
from pathlib import Path


SCRIPT_DIRECTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIRECTORY))

from common import area_config, load_manifest, source_config  # noqa: E402
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


if __name__ == "__main__":
    unittest.main()
