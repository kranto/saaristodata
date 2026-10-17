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
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from classify_external_route import classify, distance_meters


DEFAULT_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
DEFAULT_VALHALLA_URL = "https://valhalla1.openstreetmap.de"
DEFAULT_USER_AGENT = "Saaristolautat-route-prototype/1.0"


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
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = 30,
        minimum_interval_seconds: float = 1,
    ) -> None:
        self.endpoint = endpoint
        self.user_agent = user_agent
        self.timeout = timeout
        self.minimum_interval_seconds = minimum_interval_seconds
        self._last_request_at: float | None = None
        self._cache: dict[str, dict] = {}

    def geocode(self, query: str) -> dict:
        if query in self._cache:
            return dict(self._cache[query])
        if self._last_request_at is not None:
            wait = self.minimum_interval_seconds - (time.monotonic() - self._last_request_at)
            if wait > 0:
                time.sleep(wait)
        parameters = urlencode({
            "q": query,
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": 5,
            "countrycodes": "fi",
            "accept-language": "fi,sv,en",
        })
        request = Request(
            f"{self.endpoint}?{parameters}",
            headers={"User-Agent": self.user_agent, "Accept": "application/json"},
        )
        results = _read_json(request, self.timeout)
        self._last_request_at = time.monotonic()
        if not isinstance(results, list) or not results:
            raise ValueError(f"address was not found: {query}")
        item = results[0]
        result = {
            "query": query,
            "displayName": item["display_name"],
            "coordinates": {"lat": float(item["lat"]), "lon": float(item["lon"])},
            "address": item.get("address"),
            "provider": "Nominatim",
            "attribution": "© OpenStreetMap contributors",
        }
        self._cache[query] = result
        return dict(result)


class ValhallaRouter:
    provider = "Valhalla"

    def __init__(
        self,
        endpoint: str = DEFAULT_VALHALLA_URL,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = 60,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.user_agent = user_agent
        self.timeout = timeout

    def _post(self, action: str, payload: dict) -> dict:
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
        return result

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
            "locations": [origin, destination],
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
            "sources": sources,
            "targets": targets,
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
        response = self.route(point, anchor["coordinates"], mode)
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
