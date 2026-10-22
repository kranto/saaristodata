#!/usr/bin/env python3

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from external_routing import concise_address_name  # noqa: E402


class ConciseAddressNameTests(unittest.TestCase):
    def test_finnish_street_address_uses_local_order_and_municipality(self) -> None:
        result = {
            "displayName": (
                "4, Lumikintie, Roihuvuori, Herttoniemi, Kaakkoinen suurpiiri, "
                "Helsinki, Helsingin seutukunta, Uusimaa, Manner-Suomi, 00820, Suomi"
            ),
            "address": {
                "house_number": "4",
                "road": "Lumikintie",
                "suburb": "Roihuvuori",
                "city": "Helsinki",
                "postcode": "00820",
                "country": "Suomi",
            },
        }

        self.assertEqual(concise_address_name(result), "Lumikintie 4, Helsinki")

    def test_city_query_stays_concise(self) -> None:
        result = {
            "displayName": "Tampere, Pirkanmaa, Manner-Suomi, Suomi",
            "address": {"city": "Tampere", "state": "Pirkanmaa"},
        }

        self.assertEqual(concise_address_name(result), "Tampere")

    def test_island_place_keeps_its_name_before_municipality(self) -> None:
        result = {
            "name": "Fiskö",
            "displayName": "Fiskö, Brändö, Åland, Suomi",
            "address": {"island": "Fiskö", "municipality": "Brändö"},
        }

        self.assertEqual(concise_address_name(result), "Fiskö, Brändö")

    def test_cached_place_can_use_canonical_first_display_name_part(self) -> None:
        result = {
            "displayName": "Fiskö, Brändö, Åland, Suomi",
            "address": {"municipality": "Brändö"},
        }

        self.assertEqual(concise_address_name(result), "Fiskö, Brändö")

    def test_municipality_is_used_when_city_is_absent(self) -> None:
        result = {
            "displayName": "Saaristotie 1, Parainen, Suomi",
            "address": {
                "house_number": "1",
                "road": "Saaristotie",
                "municipality": "Parainen",
            },
        }

        self.assertEqual(concise_address_name(result), "Saaristotie 1, Parainen")


if __name__ == "__main__":
    unittest.main()
