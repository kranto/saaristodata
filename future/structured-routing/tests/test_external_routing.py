#!/usr/bin/env python3

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from external_routing import NominatimGeocoder, concise_address_name  # noqa: E402


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

    def test_place_search_does_not_turn_into_nearest_road(self) -> None:
        result = {
            "name": "Hastersboda",
            "displayName": "Hastersboda, Föglövägen, Föglö, Åland, Suomi",
            "address": {
                "road": "Föglövägen",
                "village": "Hastersboda",
                "municipality": "Föglö",
            },
        }

        self.assertEqual(concise_address_name(result), "Hastersboda, Föglö")

    def test_cached_geocoder_result_prefers_feature_name_over_address_hierarchy(self) -> None:
        result = {
            "displayName": (
                "Hastersboda, Föglövägen, Brändö, Finholma, Föglö, "
                "Ahvenanmaan saaristo, Ahvenanmaa, Suomi"
            ),
            "address": {
                "highway": "Hastersboda",
                "road": "Föglövägen",
                "hamlet": "Brändö",
                "village": "Finholma",
                "town": "Föglö",
                "municipality": "Ahvenanmaan saaristo",
            },
        }

        self.assertEqual(concise_address_name(result), "Hastersboda, Föglö")

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

    def test_former_municipality_is_kept_in_place_hierarchy(self) -> None:
        result = {
            "name": "Näsby",
            "displayName": "Näsby, Houtskari, Parainen, Varsinais-Suomi, Suomi",
            "address": {
                "village": "Näsby",
                "region": "Houtskari",
                "municipality": "Parainen",
            },
        }

        self.assertEqual(concise_address_name(result), "Näsby, Houtskari, Parainen")

    def test_former_municipality_is_kept_in_street_address(self) -> None:
        result = {
            "displayName": "Kirkkotie 1, Rymättylä, Naantali, Suomi",
            "address": {
                "house_number": "1",
                "road": "Kirkkotie",
                "village": "Rymättylä",
                "city": "Naantali",
            },
        }

        self.assertEqual(
            concise_address_name(result),
            "Kirkkotie 1, Rymättylä, Naantali",
        )

    def test_swedish_area_name_is_normalized_for_finnish_ui(self) -> None:
        result = {
            "name": "Näsby",
            "displayName": "Näsby, Houtskär, Pargas, Finland",
            "address": {
                "village": "Näsby",
                "region": "Houtskär",
                "municipality": "Pargas",
            },
        }

        self.assertEqual(concise_address_name(result), "Näsby, Houtskari, Pargas")


class NominatimGeocoderTests(unittest.TestCase):
    def test_bare_historic_area_name_prefers_exact_named_hamlet(self) -> None:
        results = [
            {
                "lat": "60.3251466",
                "lon": "22.9252045",
                "name": "Angelniemi",
                "display_name": "Angelniemi, Salo, Varsinais-Suomi, Suomi",
                "category": "boundary",
                "type": "historic",
                "place_rank": 16,
                "address": {"historic": "Angelniemi", "town": "Salo"},
            },
            {
                "lat": "60.3008047",
                "lon": "22.9088870",
                "name": "Angelniemi",
                "display_name": "Angelniemi, Salo, Varsinais-Suomi, Suomi",
                "category": "place",
                "type": "hamlet",
                "place_rank": 20,
                "address": {"hamlet": "Angelniemi", "town": "Salo"},
            },
        ]

        with patch("external_routing._read_json", return_value=results):
            result = NominatimGeocoder(minimum_interval_seconds=0).geocode(
                "Angelniemi"
            )

        self.assertEqual(
            result["coordinates"],
            {"lat": 60.3008047, "lon": 22.908887},
        )

    def test_bare_municipality_prefers_central_locality_over_area_centroid(self) -> None:
        results = [
            {
                "lat": "60.2946985",
                "lon": "23.2696461",
                "name": "Salo",
                "display_name": "Salo, Varsinais-Suomi, Suomi",
                "category": "boundary",
                "type": "administrative",
                "place_rank": 16,
                "osm_type": "relation",
                "osm_id": 2373964,
                "extratags": {"admin_level": "8"},
                "address": {"city": "Salo"},
            },
            {
                "lat": "60.3879279",
                "lon": "23.1248648",
                "name": "Salo",
                "display_name": "Salo, Varsinais-Suomi, Suomi",
                "category": "boundary",
                "type": "administrative",
                "place_rank": 18,
                "address": {"city": "Salo"},
            },
            {
                "lat": "61.1916127",
                "lon": "25.6145954",
                "name": "Salo",
                "display_name": "Salo, Asikkala, Suomi",
                "category": "place",
                "type": "village",
                "place_rank": 19,
                "address": {"village": "Salo", "city": "Asikkala"},
            },
        ]

        relation = {
            "elements": [{
                "type": "relation",
                "id": 2373964,
                "members": [{"type": "node", "ref": 30969777, "role": "admin_centre"}],
            }],
        }
        centre = {
            "elements": [{
                "type": "node",
                "id": 30969777,
                "lat": 60.3879279,
                "lon": 23.1248648,
            }],
        }
        with patch(
            "external_routing._read_json",
            side_effect=[results, relation, centre],
        ):
            result = NominatimGeocoder(minimum_interval_seconds=0).geocode("Salo")

        self.assertEqual(
            result["coordinates"],
            {"lat": 60.3879279, "lon": 23.1248648},
        )

    def test_street_address_keeps_nominatim_first_result(self) -> None:
        results = [
            {
                "lat": "60.3900",
                "lon": "23.1200",
                "name": "Turuntie 1",
                "display_name": "Turuntie 1, Salo, Suomi",
                "place_rank": 30,
                "address": {"road": "Turuntie", "house_number": "1", "city": "Salo"},
            },
            {
                "lat": "60.3879279",
                "lon": "23.1248648",
                "name": "Salo",
                "display_name": "Salo, Varsinais-Suomi, Suomi",
                "place_rank": 18,
                "address": {"city": "Salo"},
            },
        ]

        with patch("external_routing._read_json", return_value=results):
            result = NominatimGeocoder(minimum_interval_seconds=0).geocode(
                "Turuntie 1, Salo"
            )

        self.assertEqual(result["coordinates"], {"lat": 60.39, "lon": 23.12})

    def test_municipality_admin_centre_may_have_a_different_name(self) -> None:
        results = [{
            "lat": "61.3402939",
            "lon": "22.9097256",
            "name": "Sastamala",
            "display_name": "Sastamala, Pirkanmaa, Suomi",
            "category": "boundary",
            "type": "administrative",
            "place_rank": 16,
            "osm_type": "relation",
            "osm_id": 2524088,
            "extratags": {"admin_level": "8"},
            "address": {"municipality": "Sastamala"},
        }]
        relation = {
            "elements": [{
                "type": "relation",
                "id": 2524088,
                "members": [{"type": "node", "ref": 4966130398, "role": "admin_centre"}],
            }],
        }
        centre = {
            "elements": [{
                "type": "node",
                "id": 4966130398,
                "lat": 61.3448335,
                "lon": 22.9057947,
                "tags": {"name": "Vammala", "place": "town"},
            }],
        }

        with patch(
            "external_routing._read_json",
            side_effect=[results, relation, centre],
        ):
            result = NominatimGeocoder(minimum_interval_seconds=0).geocode("Sastamala")

        self.assertEqual(
            result["coordinates"],
            {"lat": 61.3448335, "lon": 22.9057947},
        )
        self.assertEqual(result["displayName"], "Sastamala")


if __name__ == "__main__":
    unittest.main()
