#!/usr/bin/env python3
"""Small HTTP adapters for geocoding and ferry-free road routing.

The routing orchestrator depends on the methods of these classes, not on the
public services themselves.  Tests can therefore inject deterministic fakes,
and production can later replace either provider without changing the
archipelago routing logic.
"""

from __future__ import annotations

import json
import os
import ssl
import threading
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from classify_external_route import classify, decode_polyline, distance_meters


DEFAULT_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
DEFAULT_PHOTON_URL = "https://photon.komoot.io/api/"
DEFAULT_OSM_API_URL = "https://api.openstreetmap.org/api/0.6"
DEFAULT_VALHALLA_URL = "https://valhalla1.openstreetmap.de"
DEFAULT_USER_AGENT = "Saaristolautat-route-prototype/1.0"

TRADITIONAL_ARCHIPELAGO_AREAS = {
    "houtskari": "Houtskari",
    "houtskär": "Houtskari",
    "korppoo": "Korppoo",
    "korpo": "Korppoo",
    "nauvo": "Nauvo",
    "nagu": "Nauvo",
    "parainen": "Parainen",
    "pargas": "Parainen",
    "iniö": "Iniö",
    "velkua": "Velkua",
    "rymättylä": "Rymättylä",
    "rimito": "Rymättylä",
}


IGNORED_SUGGESTION_CATEGORIES = {"natural"}


def _is_ignored_geocoding_result(item: dict) -> bool:
    category = str(item.get("category") or "").casefold()
    result_type = str(item.get("type") or "").casefold()
    return (
        category in IGNORED_SUGGESTION_CATEGORIES
        or (category == "boundary" and result_type == "historic")
    )


def _general_address_type(category: object, result_type: object) -> str:
    """Return a small, stable classification for address suggestion UI."""
    category_name = str(category or "").casefold()
    type_name = str(result_type or "").casefold()
    if category_name == "highway":
        return "street"
    if category_name == "building" or type_name in {"house", "house_number"}:
        return "house"
    if category_name == "place":
        if type_name == "country":
            return "country"
        if type_name in {"state", "region"}:
            return "state"
        if type_name in {"county"}:
            return "county"
        if type_name in {"city", "town"}:
            return "city"
        if type_name in {"suburb", "quarter", "neighbourhood"}:
            return "district"
        return "locality"
    if category_name == "boundary" and type_name == "administrative":
        return "district"
    return "point_of_interest"


def _suggestion_type_label(category: object, result_type: object) -> str:
    """Return a concise Finnish label for disambiguating equal place names."""
    category_name = str(category or "").casefold()
    type_name = str(result_type or "").casefold()
    exact_labels = {
        ("amenity", "ferry_terminal"): "lauttalaituri",
        ("boundary", "historic"): "historiallinen alue",
        ("place", "city"): "kaupunki",
        ("place", "town"): "taajama",
        ("place", "village"): "kylä",
        ("place", "hamlet"): "kylä",
        ("place", "suburb"): "kaupunginosa",
        ("place", "quarter"): "kaupunginosa",
        ("place", "neighbourhood"): "kaupunginosa",
        ("place", "locality"): "paikannimi",
        ("place", "isolated_dwelling"): "asutus",
        ("place", "island"): "saari",
        ("place", "islet"): "saari",
        ("railway", "station"): "rautatieasema",
        ("railway", "halt"): "rautatieasema",
        ("aeroway", "aerodrome"): "lentoasema",
        ("man_made", "lighthouse"): "majakka",
        ("man_made", "pier"): "laituri",
        ("leisure", "park"): "puisto",
    }
    if (category_name, type_name) in exact_labels:
        return exact_labels[(category_name, type_name)]
    category_labels = {
        "highway": "katu tai tie",
        "building": "rakennus",
        "place": "paikannimi",
        "boundary": "alue",
        "amenity": "kohde",
        "tourism": "kohde",
        "shop": "liike",
        "office": "toimipaikka",
        "railway": "rautatiekohde",
        "aeroway": "lentoliikennekohde",
        "historic": "historiallinen kohde",
        "man_made": "rakennelma",
        "leisure": "vapaa-ajan kohde",
    }
    return category_labels.get(category_name, "kohde")


def concise_suggestion_description(result: dict) -> str:
    """Drop Finnish hierarchy levels that do not help identify a result."""
    description = str(
        result.get("description") or result.get("displayName")
        or result.get("query") or ""
    )
    address = result.get("address") or {}
    hidden_values = {
        _normalized_name(address.get(key))
        for key in ("city_district", "municipality", "region", "country")
        if address.get(key)
    }
    return ", ".join(
        part.strip() for part in description.split(",")
        if part.strip() and _normalized_name(part) not in hidden_values
    )


def traditional_archipelago_area(result: dict) -> str | None:
    """Find a familiar former municipality in Nominatim's place hierarchy."""
    address = result.get("address") or {}
    values = [str(value).strip() for value in address.values() if value]
    values.extend(
        part.strip()
        for part in str(result.get("displayName") or "").split(",")
        if part.strip()
    )
    candidates = [
        TRADITIONAL_ARCHIPELAGO_AREAS[value.casefold()]
        for value in values
        if value.casefold() in TRADITIONAL_ARCHIPELAGO_AREAS
    ]
    return next(
        (candidate for candidate in candidates if candidate != "Parainen"),
        candidates[0] if candidates else None,
    )


def concise_address_name(result: dict) -> str:
    """Return the part of a Finnish address that is useful in an itinerary."""
    address = result.get("address") or {}
    street = next(
        (
            address.get(key)
            for key in ("road", "pedestrian", "residential", "footway", "path")
            if address.get(key)
        ),
        None,
    )
    house_number = address.get("house_number")
    municipality = next(
        (
            address.get(key)
            for key in ("city", "town", "municipality", "village")
            if address.get(key)
        ),
        None,
    )
    area = traditional_archipelago_area(result)

    def with_location_hierarchy(primary: str) -> str:
        parts = [primary]
        for value in (area, municipality):
            if value and all(
                str(value).casefold() != str(part).casefold() for part in parts
            ):
                parts.append(str(value))
        return ", ".join(parts)

    street_address = (
        f"{str(street).strip()} {str(house_number).strip()}"
        if street and house_number else ""
    )
    if street_address and municipality:
        return with_location_hierarchy(street_address)
    if street_address:
        return with_location_hierarchy(street_address)

    place = result.get("name")
    if not place and result.get("displayName"):
        place = str(result["displayName"]).split(",", 1)[0].strip()
    if not place:
        place = next(
            (
                address.get(key)
                for key in (
                    "island", "islet", "hamlet", "locality", "neighbourhood",
                    "suburb", "quarter", "village",
                )
                if address.get(key)
            ),
            None,
        )
    if not place and street:
        place = street
    if place:
        return with_location_hierarchy(str(place))
    if municipality:
        return str(municipality)
    return str(result.get("displayName") or result.get("query") or "")


def _normalize_geocoded_result(result: dict, query: str) -> dict:
    normalized = dict(result)
    normalized["query"] = query
    normalized["displayName"] = concise_address_name(normalized)
    if normalized.get("description"):
        normalized["description"] = concise_suggestion_description(normalized)
    return normalized


def _normalized_name(value: object) -> str:
    return " ".join(str(value or "").casefold().split())


def _best_nominatim_result(query: str, results: list[dict]) -> dict:
    """Prefer a named locality over an area centroid for a bare place name.

    Nominatim commonly returns the admin-level 8 municipality boundary first.
    For a bare municipality name it may also return a more precise city/town
    feature later in the result list. Street addresses and qualified searches
    retain Nominatim's original ordering.
    """
    stripped_query = query.strip()
    if not stripped_query or "," in stripped_query or any(
        character.isdigit() for character in stripped_query
    ):
        return results[0]

    normalized_query = _normalized_name(stripped_query)
    central_candidates = []
    for position, item in enumerate(results):
        if _normalized_name(item.get("name")) != normalized_query:
            continue
        address = item.get("address") or {}
        if not any(
            _normalized_name(address.get(key)) == normalized_query
            for key in ("city", "town", "municipality")
        ):
            continue
        central_candidates.append((int(item.get("place_rank") or 0), -position, item))
    if central_candidates:
        return max(central_candidates, key=lambda candidate: candidate[:2])[2]

    locality_types = {
        "city", "town", "village", "hamlet", "suburb", "quarter",
        "neighbourhood", "locality",
    }
    locality = next(
        (
            item for item in results
            if _normalized_name(item.get("name")) == normalized_query
            and item.get("category") == "place"
            and item.get("type") in locality_types
        ),
        None,
    )
    if locality:
        return locality
    return results[0]


def _municipality_boundary_result(query: str, results: list[dict]) -> dict | None:
    stripped_query = query.strip()
    if not stripped_query or "," in stripped_query or any(
        character.isdigit() for character in stripped_query
    ):
        return None
    normalized_query = _normalized_name(stripped_query)
    return next(
        (
            item for item in results
            if _normalized_name(item.get("name")) == normalized_query
            and item.get("category") == "boundary"
            and item.get("type") == "administrative"
            and str((item.get("extratags") or {}).get("admin_level")) == "8"
            and item.get("osm_type") == "relation"
            and item.get("osm_id")
        ),
        None,
    )


def _read_json(request: Request, timeout: float) -> object:
    default_paths = ssl.get_default_verify_paths()
    configured_cafile = os.environ.get(default_paths.openssl_cafile_env)
    cafile = next(
        (
            value for value in (
                configured_cafile,
                default_paths.cafile,
                "/etc/ssl/cert.pem",
            )
            if value and Path(value).is_file()
        ),
        None,
    )
    context = ssl.create_default_context(cafile=cafile)
    try:
        with urlopen(request, timeout=timeout, context=context) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"external service returned HTTP {error.code}: {detail[:500]}"
        ) from error
    except URLError as error:
        raise RuntimeError(f"external service request failed: {error.reason}") from error


def valhalla_costing(mode: str) -> str:
    values = {"car": "auto", "motorcycle": "motorcycle", "bicycle": "bicycle"}
    try:
        return values[mode]
    except KeyError as error:
        raise ValueError(f"unsupported external routing mode: {mode}") from error


class NominatimGeocoder:
    provider = "Nominatim"

    def __init__(
        self,
        endpoint: str = DEFAULT_NOMINATIM_URL,
        *,
        street_suggestion_endpoint: str | None = DEFAULT_PHOTON_URL,
        osm_api_endpoint: str = DEFAULT_OSM_API_URL,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = 30,
        minimum_interval_seconds: float = 1,
        cache=None,
    ) -> None:
        self.endpoint = endpoint
        self.street_suggestion_endpoint = street_suggestion_endpoint
        self.osm_api_endpoint = osm_api_endpoint.rstrip("/")
        self.user_agent = user_agent
        self.timeout = timeout
        self.minimum_interval_seconds = minimum_interval_seconds
        self.cache = cache
        self._last_request_at: float | None = None
        self._cache: dict[str, dict] = {}
        self._request_lock = threading.Lock()

    def suggest(self, query: str, *, limit: int = 10) -> list[dict]:
        """Return distinct Finnish geocoding candidates without choosing one."""
        normalized_query = " ".join(query.casefold().split())
        cache_key = {
            "endpoint": self.endpoint,
            "query": normalized_query,
            "limit": limit,
            "selection": "address-suggestions-v1",
        }
        cached = self.cache.get("nominatim:suggest", cache_key) if self.cache else None
        if cached is None:
            parameters = urlencode({
                "q": query,
                "format": "jsonv2",
                "addressdetails": 1,
                "extratags": 1,
                "limit": limit,
                "countrycodes": "fi",
                "accept-language": "fi,sv,en",
            })
            with self._request_lock:
                cached = self.cache.get("nominatim:suggest", cache_key) if self.cache else None
                if cached is None:
                    if self._last_request_at is not None:
                        wait = self.minimum_interval_seconds - (
                            time.monotonic() - self._last_request_at
                        )
                        if wait > 0:
                            time.sleep(wait)
                    request = Request(
                        f"{self.endpoint}?{parameters}",
                        headers={"User-Agent": self.user_agent, "Accept": "application/json"},
                    )
                    cached = _read_json(request, self.timeout)
                    self._last_request_at = time.monotonic()
                    if self.cache:
                        self.cache.set("nominatim:suggest", cache_key, cached)
        if not isinstance(cached, list):
            raise RuntimeError("geocoding provider returned an invalid suggestion response")
        if not cached:
            return []

        candidate_items = [
            item for item in cached
            if not _is_ignored_geocoding_result(item)
        ]
        if not candidate_items:
            return []
        coordinate_override = None
        stripped_query = query.strip()
        normalized_query_name = _normalized_name(stripped_query)
        cached_has_exact_street = any(
            item.get("category") == "highway"
            and normalized_query_name in {
                _normalized_name(item.get("name")),
                _normalized_name((item.get("address") or {}).get("road")),
            }
            for item in cached
        )
        if stripped_query and "," not in stripped_query and not any(
            character.isdigit() for character in stripped_query
        ):
            municipality = _municipality_boundary_result(query, cached)
            if municipality is not None and not cached_has_exact_street:
                candidate_items = [municipality]
                coordinate_override = self._admin_centre(municipality)
        exact_name_items = [
            item for item in candidate_items
            if normalized_query_name in {
                _normalized_name(item.get("name")),
                *(
                    _normalized_name((item.get("address") or {}).get(key))
                    for key in (
                        "road", "pedestrian", "residential", "footway", "path",
                        "city", "town", "municipality", "village", "hamlet",
                        "locality", "island",
                    )
                ),
            }
        ]
        if exact_name_items:
            candidate_items = exact_name_items
        has_exact_street = any(
            item.get("category") == "highway"
            and normalized_query_name in {
                _normalized_name(item.get("name")),
                _normalized_name((item.get("address") or {}).get("road")),
            }
            for item in candidate_items
        )
        supplementary_streets = (
            self._street_suggestions(query, limit=50)
            if has_exact_street and self.street_suggestion_endpoint else []
        )

        suggestions = []
        seen = set()
        seen_descriptions = set()
        seen_localities = set()
        for position, item in enumerate(candidate_items):
            if not isinstance(item, dict) or "lat" not in item or "lon" not in item:
                continue
            coordinates = coordinate_override or {
                "lat": float(item["lat"]), "lon": float(item["lon"]),
            }
            identifier = (
                f"nominatim:{item.get('osm_type')}:{item.get('osm_id')}"
                if item.get("osm_type") and item.get("osm_id")
                else f"nominatim:{coordinates['lat']:.7f}:{coordinates['lon']:.7f}:{position}"
            )
            candidate = _normalize_geocoded_result({
                "id": identifier,
                "name": item.get("name"),
                "displayName": item.get("display_name") or query,
                "description": item.get("display_name") or query,
                "coordinates": coordinates,
                "address": item.get("address"),
                "provider": "Nominatim",
                "attribution": "© OpenStreetMap contributors",
                "resultCategory": item.get("category"),
                "resultType": (
                    "street" if item.get("category") == "highway"
                    else item.get("type") or item.get("category") or "place"
                ),
                "addressType": _general_address_type(
                    item.get("category"), item.get("type"),
                ),
                "typeLabel": _suggestion_type_label(
                    item.get("category"), item.get("type"),
                ),
            }, query)
            duplicate_key = (
                _normalized_name(candidate["displayName"]),
                candidate["resultType"],
            )
            description_key = _normalized_name(candidate["description"])
            locality_key = (
                _normalized_name(candidate["displayName"])
                if item.get("category") in {"place", "boundary"} else None
            )
            if (
                duplicate_key in seen
                or description_key in seen_descriptions
                or (locality_key is not None and locality_key in seen_localities)
            ):
                continue
            seen.add(duplicate_key)
            seen_descriptions.add(description_key)
            if locality_key is not None:
                seen_localities.add(locality_key)
            suggestions.append(candidate)
        for candidate in supplementary_streets:
            duplicate_key = (
                _normalized_name(candidate["displayName"]),
                candidate["resultType"],
            )
            description_key = _normalized_name(candidate["description"])
            if duplicate_key in seen or description_key in seen_descriptions:
                continue
            seen.add(duplicate_key)
            seen_descriptions.add(description_key)
            suggestions.append(candidate)
        return suggestions

    def _street_suggestions(self, query: str, *, limit: int) -> list[dict]:
        cache_key = {
            "endpoint": self.street_suggestion_endpoint,
            "query": " ".join(query.casefold().split()),
            "limit": limit,
            "selection": "exact-finnish-streets-v1",
        }
        cached = self.cache.get("photon:street-suggest", cache_key) if self.cache else None
        if cached is None:
            parameters = urlencode({"q": query, "limit": limit})
            with self._request_lock:
                cached = self.cache.get("photon:street-suggest", cache_key) if self.cache else None
                if cached is None:
                    if self._last_request_at is not None:
                        wait = self.minimum_interval_seconds - (
                            time.monotonic() - self._last_request_at
                        )
                        if wait > 0:
                            time.sleep(wait)
                    request = Request(
                        f"{self.street_suggestion_endpoint}?{parameters}",
                        headers={"User-Agent": self.user_agent, "Accept": "application/json"},
                    )
                    cached = _read_json(request, self.timeout)
                    self._last_request_at = time.monotonic()
                    if self.cache:
                        self.cache.set("photon:street-suggest", cache_key, cached)
        features = cached.get("features") if isinstance(cached, dict) else None
        if not isinstance(features, list):
            return []
        normalized_query = _normalized_name(query)
        suggestions = []
        for feature in features:
            properties = feature.get("properties") or {}
            geometry = feature.get("geometry") or {}
            coordinates = geometry.get("coordinates") or []
            if (
                properties.get("countrycode") != "FI"
                or properties.get("type") != "street"
                or _normalized_name(properties.get("name")) != normalized_query
                or len(coordinates) < 2
            ):
                continue
            city = properties.get("city") or properties.get("county")
            address = {
                "road": properties.get("name"),
                "city": city,
                "suburb": properties.get("district"),
                "neighbourhood": properties.get("locality"),
                "state": properties.get("state"),
                "postcode": properties.get("postcode"),
                "country": properties.get("country"),
            }
            description = ", ".join(
                str(value) for value in (
                    properties.get("name"), properties.get("locality"),
                    properties.get("district"), city, properties.get("state"),
                    properties.get("postcode"), properties.get("country"),
                ) if value
            )
            suggestions.append(_normalize_geocoded_result({
                "id": f"photon:{properties.get('osm_type')}:{properties.get('osm_id')}",
                "name": properties.get("name"),
                "displayName": description,
                "description": description,
                "coordinates": {"lat": float(coordinates[1]), "lon": float(coordinates[0])},
                "address": address,
                "provider": "Photon",
                "attribution": "© OpenStreetMap contributors",
                "resultCategory": "highway",
                "resultType": "street",
                "addressType": "street",
                "typeLabel": "katu tai tie",
            }, query))
        return suggestions

    def geocode(self, query: str) -> dict:
        normalized_query = " ".join(query.casefold().split())
        if normalized_query in self._cache:
            result = _normalize_geocoded_result(self._cache[normalized_query], query)
            return result
        cache_key = {
            "endpoint": self.endpoint,
            "query": normalized_query,
            "selection": "named-locality-v3",
        }
        cached = self.cache.get("nominatim:search", cache_key) if self.cache else None
        if cached is not None:
            result = _normalize_geocoded_result(cached, query)
            self._cache[normalized_query] = result
            return dict(result)
        parameters = urlencode({
            "q": query,
            "format": "jsonv2",
            "addressdetails": 1,
            "extratags": 1,
            "limit": 5,
            "countrycodes": "fi",
            "accept-language": "fi,sv,en",
        })
        with self._request_lock:
            # Another request may have populated the cache while this thread
            # was waiting for the provider-wide rate-limit lock.
            cached = self.cache.get("nominatim:search", cache_key) if self.cache else None
            if cached is not None:
                result = _normalize_geocoded_result(cached, query)
                self._cache[normalized_query] = result
                return dict(result)
            if self._last_request_at is not None:
                wait = self.minimum_interval_seconds - (
                    time.monotonic() - self._last_request_at
                )
                if wait > 0:
                    time.sleep(wait)
            request = Request(
                f"{self.endpoint}?{parameters}",
                headers={"User-Agent": self.user_agent, "Accept": "application/json"},
            )
            results = _read_json(request, self.timeout)
            self._last_request_at = time.monotonic()
        if not isinstance(results, list) or not results:
            raise ValueError(f"address was not found: {query}")
        results = [
            item for item in results
            if isinstance(item, dict) and not _is_ignored_geocoding_result(item)
        ]
        if not results:
            raise ValueError(f"address was not found: {query}")
        item = _best_nominatim_result(query, results)
        municipality = _municipality_boundary_result(query, results)
        admin_centre = self._admin_centre(municipality) if municipality else None
        if municipality and admin_centre:
            item = municipality
        result = _normalize_geocoded_result({
            "query": query,
            "name": item.get("name"),
            "displayName": item["display_name"],
            "coordinates": admin_centre or {
                "lat": float(item["lat"]), "lon": float(item["lon"]),
            },
            "address": item.get("address"),
            "provider": "Nominatim",
            "attribution": "© OpenStreetMap contributors",
            "resultCategory": item.get("category"),
            "resultType": item.get("type") or item.get("category") or "place",
            "addressType": _general_address_type(
                item.get("category"), item.get("type"),
            ),
            "typeLabel": _suggestion_type_label(
                item.get("category"), item.get("type"),
            ),
        }, query)
        if self.cache:
            self.cache.set("nominatim:search", cache_key, result)
        self._cache[normalized_query] = result
        return dict(result)

    def _admin_centre(self, municipality: dict) -> dict | None:
        relation_id = int(municipality["osm_id"])
        cache_key = {"endpoint": self.osm_api_endpoint, "relationId": relation_id}
        cached = self.cache.get("osm:admin-centre", cache_key) if self.cache else None
        if cached is not None:
            return dict(cached)
        try:
            relation_request = Request(
                f"{self.osm_api_endpoint}/relation/{relation_id}.json",
                headers={"User-Agent": self.user_agent, "Accept": "application/json"},
            )
            relation_data = _read_json(relation_request, self.timeout)
            relation = next(
                item for item in relation_data["elements"]
                if item.get("type") == "relation" and item.get("id") == relation_id
            )
            centre_member = next(
                member for member in relation["members"]
                if member.get("type") == "node" and member.get("role") == "admin_centre"
            )
            node_id = int(centre_member["ref"])
            node_request = Request(
                f"{self.osm_api_endpoint}/node/{node_id}.json",
                headers={"User-Agent": self.user_agent, "Accept": "application/json"},
            )
            node_data = _read_json(node_request, self.timeout)
            node = next(
                item for item in node_data["elements"]
                if item.get("type") == "node" and item.get("id") == node_id
            )
            result = {"lat": float(node["lat"]), "lon": float(node["lon"])}
        except (KeyError, StopIteration, TypeError, ValueError, RuntimeError):
            return None
        if self.cache:
            self.cache.set("osm:admin-centre", cache_key, result)
        return result


class ValhallaRouter:
    provider = "Valhalla"

    def __init__(
        self,
        endpoint: str = DEFAULT_VALHALLA_URL,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = 60,
        cache=None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.user_agent = user_agent
        self.timeout = timeout
        self.cache = cache

    def _post(self, action: str, payload: dict) -> dict:
        cache_key = {"endpoint": self.endpoint, "payload": payload}
        cached = self.cache.get(f"valhalla:{action}", cache_key) if self.cache else None
        if cached is not None:
            return dict(cached)
        request = Request(
            f"{self.endpoint}/{action}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        result = _read_json(request, self.timeout)
        if not isinstance(result, dict):
            raise RuntimeError("external routing service returned a non-object response")
        if self.cache:
            self.cache.set(f"valhalla:{action}", cache_key, result)
        return result

    @staticmethod
    def _locations(locations: list[dict], *, exclude_ferries: bool) -> list[dict]:
        """Prepare Valhalla locations without mutating caller-owned points.

        Excluding ferry traversal in the costing model is not enough when a
        terminal coordinate correlates directly to the ferry edge.  In that
        case Valhalla cannot leave or reach the location at all.  Excluding
        ferry edges from location correlation makes the same coordinate snap
        to its road-side terminal approach instead.
        """
        prepared = []
        for location in locations:
            item = dict(location)
            if exclude_ferries:
                search_filter = dict(item.get("search_filter", {}))
                search_filter["exclude_ferry"] = True
                item["search_filter"] = search_filter
            prepared.append(item)
        return prepared

    def route(
        self, origin: dict, destination: dict, mode: str, *,
        exclude_ferries: bool = False,
    ) -> dict:
        costing = valhalla_costing(mode)
        options = (
            {"exclude_ferries": True}
            if exclude_ferries else {"use_ferry": 1}
        )
        return self._post("route", {
            "locations": self._locations(
                [origin, destination], exclude_ferries=exclude_ferries,
            ),
            "costing": costing,
            "costing_options": {costing: options},
            "directions_options": {"units": "kilometers"},
        })

    def measure_route(
        self, origin: dict, destination: dict, mode: str, *,
        exclude_ferries: bool = True,
    ) -> dict | None:
        response = self.route(
            origin, destination, mode, exclude_ferries=exclude_ferries
        )
        summary = (response.get("trip") or {}).get("summary") or {}
        if exclude_ferries and summary.get("has_ferry"):
            return None
        if summary.get("time") is None or summary.get("length") is None:
            return None
        return {
            "durationSeconds": max(0, round(float(summary["time"]))),
            "distanceMeters": max(0, round(float(summary["length"]) * 1000)),
        }

    def route_geometry(
        self, origin: dict, destination: dict, mode: str, *,
        exclude_ferries: bool = True,
    ) -> dict | None:
        response = self.route(
            origin, destination, mode, exclude_ferries=exclude_ferries,
        )
        trip = response.get("trip") or {}
        if exclude_ferries and (trip.get("summary") or {}).get("has_ferry"):
            return None
        coordinates = []
        for leg in trip.get("legs", []):
            shape = leg.get("shape")
            if not shape:
                continue
            for point in decode_polyline(shape):
                coordinate = [point["lon"], point["lat"]]
                if not coordinates or coordinates[-1] != coordinate:
                    coordinates.append(coordinate)
        if len(coordinates) < 2:
            return None
        return {"type": "LineString", "coordinates": coordinates}

    def matrix(
        self,
        sources: list[dict],
        targets: list[dict],
        mode: str,
        *,
        exclude_ferries: bool = True,
    ) -> list[dict]:
        costing = valhalla_costing(mode)
        response = self._post("sources_to_targets", {
            "sources": self._locations(sources, exclude_ferries=exclude_ferries),
            "targets": self._locations(targets, exclude_ferries=exclude_ferries),
            "costing": costing,
            "costing_options": {costing: {"exclude_ferries": exclude_ferries}},
            "units": "kilometers",
            "verbose": True,
        })
        values = response.get("sources_to_targets")
        if not isinstance(values, list):
            raise RuntimeError("Valhalla matrix response has no sources_to_targets list")
        if values and isinstance(values[0], list):
            values = [item for row in values for item in row]
        return values

    def infer_road_area(
        self,
        point: dict,
        index: dict,
        *,
        mode: str,
        anchor_stop_id: str | None = None,
    ) -> dict:
        anchor = (
            next(
                (item for item in index["stops"] if item["id"] == anchor_stop_id),
                None,
            )
            if anchor_stop_id
            else min(
                index["stops"],
                key=lambda item: distance_meters(point, item["coordinates"]),
            )
        )
        if anchor is None:
            raise ValueError(f"road-area anchor is not in the stop index: {anchor_stop_id}")
        response = self.route(
            point,
            anchor.get("routingCoordinates", anchor["coordinates"]),
            mode,
        )
        result = classify(
            response,
            index,
            anchor_road_area_id=anchor["roadAreaId"],
        )
        if result.get("roadArea") is None:
            raise ValueError(
                "the address is not connected to a recognized archipelago road area"
            )
        return result
