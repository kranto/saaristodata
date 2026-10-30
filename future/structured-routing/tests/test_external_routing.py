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
    def test_visually_identical_place_candidates_are_deduplicated(self) -> None:
        results = [
            {
                "lat": "61.5003", "lon": "23.7406", "name": "Amuri",
                "display_name": "Amuri, Tampere, Pirkanmaa, Suomi",
                "category": "place", "type": "suburb",
                "osm_type": "node", "osm_id": 1,
                "address": {"suburb": "Amuri", "city": "Tampere"},
            },
            {
                "lat": "61.5010", "lon": "23.7432", "name": "Amuri",
                "display_name": "Amuri, Tampere, Pirkanmaa, Suomi ilman postinumeroa",
                "category": "boundary", "type": "administrative",
                "osm_type": "relation", "osm_id": 2,
                "address": {"suburb": "Amuri", "city": "Tampere"},
            },
        ]
        with patch("external_routing._read_json", return_value=results):
            suggestions = NominatimGeocoder(
                minimum_interval_seconds=0,
                street_suggestion_endpoint=None,
            ).suggest("Amuri")
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0]["displayName"], "Amuri, Tampere")

    def test_bare_locality_name_returns_distinct_places_instead_of_one_best(self) -> None:
        results = [
            {
                "lat": "61.4977", "lon": "23.8073", "name": "Kaleva",
                "display_name": "Kaleva, Tampere, Suomi",
                "category": "boundary", "type": "administrative",
                "osm_type": "relation", "osm_id": 1,
                "extratags": {"admin_level": "10"},
                "address": {"suburb": "Kaleva", "city": "Tampere"},
            },
            {
                "lat": "60.4145", "lon": "25.0958", "name": "Kaleva",
                "display_name": "Kaleva, Kerava, Suomi",
                "category": "boundary", "type": "administrative",
                "osm_type": "relation", "osm_id": 2,
                "extratags": {"admin_level": "10"},
                "address": {"suburb": "Kaleva", "town": "Kerava"},
            },
            {
                "lat": "61.3151", "lon": "22.1258", "name": "Kaleva",
                "display_name": "Kaleva, Harjavalta, Suomi",
                "category": "place", "type": "suburb",
                "osm_type": "node", "osm_id": 3,
                "address": {"suburb": "Kaleva", "town": "Harjavalta"},
            },
        ]
        with patch("external_routing._read_json", return_value=results):
            suggestions = NominatimGeocoder(
                minimum_interval_seconds=0,
                street_suggestion_endpoint=None,
            ).suggest("Kaleva")

        self.assertEqual(
            [item["displayName"] for item in suggestions],
            ["Kaleva, Tampere", "Kaleva, Kerava", "Kaleva, Harjavalta"],
        )

    def test_empty_suggestion_response_stays_empty(self) -> None:
        with patch("external_routing._read_json", return_value=[]):
            suggestions = NominatimGeocoder(
                minimum_interval_seconds=0,
            ).suggest("Vimpe")
        self.assertEqual(suggestions, [])

    def test_exact_street_results_are_supplemented_without_dropping_places(self) -> None:
        nominatim = [
            {
                "lat": "60.1690", "lon": "24.9520", "name": "Hallituskatu",
                "display_name": "Hallituskatu, Helsinki, Suomi",
                "category": "highway", "type": "residential",
                "osm_type": "way", "osm_id": 1,
                "address": {"road": "Hallituskatu", "city": "Helsinki"},
            },
            {
                "lat": "62.0000", "lon": "25.0000", "name": "Hallituskatu",
                "display_name": "Hallituskatu, Esimerkkikunta, Suomi",
                "category": "place", "type": "hamlet",
                "osm_type": "node", "osm_id": 2,
                "address": {"hamlet": "Hallituskatu", "municipality": "Esimerkkikunta"},
            },
        ]
        photon = {
            "features": [{
                "type": "Feature",
                "properties": {
                    "osm_type": "W", "osm_id": 3, "type": "street",
                    "name": "Hallituskatu", "city": "Kuopio",
                    "state": "Pohjois-Savo", "country": "Suomi",
                    "countrycode": "FI",
                },
                "geometry": {"type": "Point", "coordinates": [27.69, 62.89]},
            }],
        }
        with patch("external_routing._read_json", side_effect=[nominatim, photon]):
            suggestions = NominatimGeocoder(
                minimum_interval_seconds=0,
            ).suggest("Hallituskatu")

        self.assertEqual(
            {(item["displayName"], item["resultType"]) for item in suggestions},
            {
                ("Hallituskatu, Helsinki", "street"),
                ("Hallituskatu, Esimerkkikunta", "hamlet"),
                ("Hallituskatu, Kuopio", "street"),
            },
        )

    def test_suggestions_keep_distinct_same_named_streets(self) -> None:
        results = [
            {
                "lat": "60.1690", "lon": "24.9520", "name": "Hallituskatu",
                "display_name": "Hallituskatu, Helsinki, Uusimaa, Suomi",
                "osm_type": "way", "osm_id": 1,
                "address": {"road": "Hallituskatu", "city": "Helsinki"},
            },
            {
                "lat": "60.1691", "lon": "24.9530", "name": "Hallituskatu",
                "display_name": "Hallituskatu, Helsinki, Uusimaa, Suomi",
                "osm_type": "way", "osm_id": 3,
                "address": {"road": "Hallituskatu", "city": "Helsinki"},
            },
            {
                "lat": "61.4980", "lon": "23.7600", "name": "Hallituskatu",
                "display_name": "Hallituskatu, Tampere, Pirkanmaa, Suomi",
                "osm_type": "way", "osm_id": 2,
                "address": {"road": "Hallituskatu", "city": "Tampere"},
            },
            {
                "lat": "60.1692", "lon": "24.9500", "name": "Yliopistonkatu",
                "display_name": "Yliopistonkatu, Helsinki, Uusimaa, Suomi",
                "osm_type": "way", "osm_id": 4,
                "address": {"road": "Yliopistonkatu", "city": "Helsinki"},
            },
        ]
        with patch("external_routing._read_json", return_value=results):
            suggestions = NominatimGeocoder(
                minimum_interval_seconds=0,
            ).suggest("Hallituskatu")

        self.assertEqual(
            [item["displayName"] for item in suggestions],
            ["Hallituskatu, Helsinki", "Hallituskatu, Tampere"],
        )
        self.assertEqual(suggestions[1]["id"], "nominatim:way:2")

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
        with patch("external_routing._read_json", return_value=results):
            suggestions = NominatimGeocoder(minimum_interval_seconds=0).suggest(
                "Angelniemi"
            )
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0]["resultCategory"], "place")
        self.assertEqual(suggestions[0]["resultType"], "hamlet")
        self.assertEqual(suggestions[0]["typeLabel"], "kylä")

    def test_suggestions_filter_natural_features_and_explain_equal_names(self) -> None:
        results = [
            {
                "lat": "60.3008047", "lon": "22.9088870",
                "name": "Angelniemi",
                "display_name": (
                    "Angelniemi, Halikko, Salo, Salon seutukunta, "
                    "Varsinais-Suomi, Manner-Suomi, 25230, Suomi"
                ),
                "category": "place", "type": "hamlet",
                "osm_type": "node", "osm_id": 1,
                "address": {
                    "hamlet": "Angelniemi", "town": "Halikko", "city": "Salo",
                    "municipality": "Salon seutukunta", "state": "Varsinais-Suomi",
                    "region": "Manner-Suomi", "postcode": "25230",
                    "country": "Suomi",
                },
            },
            {
                "lat": "60.3572099", "lon": "23.0328041",
                "name": "Angelniemi",
                "display_name": "Angelniemi, Kaninkola, Halikko, Salo, Suomi",
                "category": "natural", "type": "cliff",
                "osm_type": "way", "osm_id": 2,
                "address": {"cliff": "Angelniemi", "hamlet": "Kaninkola"},
            },
            {
                "lat": "60.3128597", "lon": "22.9439411",
                "name": "Angelniemi",
                "display_name": (
                    "Angelniemi, Kemiönsaarentie, Tammenpää, Kokkila, Halikko, "
                    "Salo, Salon seutukunta, Varsinais-Suomi, Manner-Suomi, 25570, Suomi"
                ),
                "category": "amenity", "type": "ferry_terminal",
                "osm_type": "node", "osm_id": 3,
                "address": {
                    "amenity": "Angelniemi", "road": "Kemiönsaarentie",
                    "hamlet": "Tammenpää", "village": "Kokkila",
                    "town": "Halikko", "city": "Salo",
                    "municipality": "Salon seutukunta", "state": "Varsinais-Suomi",
                    "region": "Manner-Suomi", "postcode": "25570",
                    "country": "Suomi",
                },
            },
        ]
        with patch("external_routing._read_json", return_value=results):
            suggestions = NominatimGeocoder(minimum_interval_seconds=0).suggest(
                "Angelniemi, Salo"
            )

        self.assertEqual(len(suggestions), 2)
        self.assertEqual(
            [(item["resultCategory"], item["resultType"], item["addressType"], item["typeLabel"])
             for item in suggestions],
            [
                ("place", "hamlet", "locality", "kylä"),
                ("amenity", "ferry_terminal", "point_of_interest", "lauttalaituri"),
            ],
        )
        for item in suggestions:
            self.assertNotIn("Salon seutukunta", item["description"])
            self.assertNotIn("Manner-Suomi", item["description"])
            self.assertNotIn(
                "Suomi", [part.strip() for part in item["description"].split(",")]
            )
            self.assertIn("Varsinais-Suomi", item["description"])

    def test_historic_boundary_is_never_a_route_endpoint(self) -> None:
        historic_boundary = [{
            "lat": "60.3251466", "lon": "22.9252045",
            "name": "Angelniemi",
            "display_name": "Angelniemi, Varsinais-Suomi, Suomi",
            "category": "boundary", "type": "historic",
            "osm_type": "relation", "osm_id": 17561240,
            "address": {"historic": "Angelniemi", "state": "Varsinais-Suomi"},
        }]
        with patch("external_routing._read_json", return_value=historic_boundary):
            suggestions = NominatimGeocoder(minimum_interval_seconds=0).suggest(
                "Angelniemi"
            )
        self.assertEqual(suggestions, [])

        with patch("external_routing._read_json", return_value=historic_boundary):
            with self.assertRaisesRegex(ValueError, "address was not found"):
                NominatimGeocoder(minimum_interval_seconds=0).geocode("Angelniemi")

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
