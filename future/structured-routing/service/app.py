#!/usr/bin/env python3
"""FastAPI entry point for address-to-address archipelago routing."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time as runtime_clock
from contextlib import asynccontextmanager
from datetime import date, time
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.concurrency import run_in_threadpool


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from external_routing import (  # noqa: E402
    DEFAULT_NOMINATIM_URL,
    DEFAULT_USER_AGENT,
    DEFAULT_VALHALLA_URL,
    NominatimGeocoder,
    ValhallaRouter,
)
from query_address_routes import (  # noqa: E402
    DEFAULT_STOP_INDEX,
    known_stop,
    query_address_routes,
    routing_coordinates,
)
from route_itinerary import DEFAULT_GRAPH  # noqa: E402
from routing_cache import SQLiteJsonCache  # noqa: E402


SERVICE_VERSION = "0.4.81"
ROUTE_PREVIEW = ROOT / "service" / "route-preview.html"


class Coordinates(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lat: float = Field(ge=59, le=71)
    lon: float = Field(ge=19, le=32)


class GeocodeSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str = Field(min_length=1, max_length=300)
    display_name: str = Field(min_length=1, max_length=500, alias="displayName")
    coordinates: Coordinates
    provider: str = Field(min_length=1, max_length=100)
    attribution: str | None = Field(default=None, max_length=300)
    routing_stop_id: str | None = Field(
        default=None, max_length=300, alias="routingStopId",
    )


class RouteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origin: str = Field(min_length=2, max_length=300)
    destination: str = Field(min_length=2, max_length=300)
    date: date
    start_time: time = Field(default=time(0, 0), alias="startTime")
    mode: Literal["car", "motorcycle", "bicycle"] = "car"
    timing_profile: Literal["typical", "conservative"] = Field(
        default="typical", alias="timingProfile",
    )
    same_day: bool = Field(default=True, alias="sameDay")
    max_results: int = Field(default=12, ge=1, le=24, alias="maxResults")
    include_diagnostics: bool = Field(default=False, alias="includeDiagnostics")
    include_decision_graph: bool = Field(default=False, alias="includeDecisionGraph")
    include_geometry: bool = Field(default=True, alias="includeGeometry")
    origin_selection: GeocodeSelection | None = Field(
        default=None, alias="originSelection",
    )
    destination_selection: GeocodeSelection | None = Field(
        default=None, alias="destinationSelection",
    )

    @field_validator("start_time")
    @classmethod
    def start_time_is_a_local_minute(cls, value: time) -> time:
        if value.tzinfo is not None or value.second or value.microsecond:
            raise ValueError("startTime must be a local time with minute precision")
        return value


class SelectedEndpointGeocoder:
    def __init__(self, delegate, selections: dict[str, GeocodeSelection]) -> None:
        self.delegate = delegate
        self.selections = selections

    def geocode(self, query: str) -> dict:
        selection = self.selections.get(" ".join(query.casefold().split()))
        if selection is None:
            return self.delegate.geocode(query)
        result = selection.model_dump(exclude_none=True, by_alias=True)
        result["query"] = query
        return result


def environment_path(name: str, default: Path) -> Path:
    return Path(os.environ.get(name, default))


def configure_dependencies(app: FastAPI) -> None:
    cache = SQLiteJsonCache(
        environment_path("ROUTING_CACHE_PATH", Path("/var/cache/saaristolautat/routes.sqlite3")),
        default_ttl_seconds=int(os.environ.get("ROUTING_CACHE_TTL_SECONDS", 30 * 24 * 3600)),
    )
    user_agent = os.environ.get("ROUTING_USER_AGENT", DEFAULT_USER_AGENT)
    app.state.cache = cache
    app.state.geocoder = NominatimGeocoder(
        os.environ.get("NOMINATIM_URL", DEFAULT_NOMINATIM_URL),
        user_agent=user_agent,
        cache=cache,
    )
    app.state.router = ValhallaRouter(
        os.environ.get("VALHALLA_URL", DEFAULT_VALHALLA_URL),
        user_agent=user_agent,
        cache=cache,
    )
    app.state.graph_path = environment_path("ROUTING_GRAPH_PATH", DEFAULT_GRAPH)
    app.state.stop_index_path = environment_path(
        "ROUTING_STOP_INDEX_PATH", DEFAULT_STOP_INDEX,
    )
    graph_bytes = app.state.graph_path.read_bytes()
    stop_index_bytes = app.state.stop_index_path.read_bytes()
    app.state.graph_data = json.loads(graph_bytes)
    app.state.stop_index_data = json.loads(stop_index_bytes)
    app.state.data_version = hashlib.sha256(
        graph_bytes + b"\0" + stop_index_bytes
    ).hexdigest()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not hasattr(app.state, "geocoder"):
        configure_dependencies(app)
    app.state.cache.purge_expired()
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="Saaristolautat routing API",
        version=SERVICE_VERSION,
        lifespan=lifespan,
    )
    @application.get("/health")
    async def health() -> dict:
        return {"status": "ok", "version": SERVICE_VERSION}

    @application.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse(url="/route")

    @application.get("/route", response_class=HTMLResponse, include_in_schema=False)
    async def route_preview() -> HTMLResponse:
        return HTMLResponse(ROUTE_PREVIEW.read_text(encoding="utf-8"))

    @application.get("/geocode")
    async def geocode_suggestions(
        query: str = Query(min_length=2, max_length=300),
    ) -> dict:
        stop_index = getattr(application.state, "stop_index_data", None)
        if stop_index is None:
            stop_index = json.loads(application.state.stop_index_path.read_text())
        stop = known_stop(stop_index, query)
        if stop is not None:
            return {
                "query": query,
                "suggestions": [{
                    "id": f"stop:{stop['id']}",
                    "displayName": stop.get("name", stop["id"]),
                    "description": "Saaristolauttojen laituri",
                    "coordinates": routing_coordinates(stop),
                    "provider": "saaristolautat",
                    "routingStopId": stop["id"],
                    "resultCategory": "amenity",
                    "resultType": "ferry_terminal",
                    "addressType": "point_of_interest",
                    "typeLabel": "lauttalaituri",
                }],
            }
        try:
            suggestions = await run_in_threadpool(
                application.state.geocoder.suggest, query,
            )
            return {"query": query, "suggestions": suggestions}
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except RuntimeError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

    @application.post("/route")
    async def route(request: RouteRequest):
        request_started_at = runtime_clock.perf_counter()

        def response_with_runtime(payload: dict, *, cache_hit: bool) -> dict:
            response = dict(payload)
            runtime = dict(response.get("runtime") or {})
            runtime.update({
                "responseCacheHit": cache_hit,
                "requestMilliseconds": round(
                    (runtime_clock.perf_counter() - request_started_at) * 1000,
                    1,
                ),
            })
            response["runtime"] = runtime
            return response

        stop_index = getattr(application.state, "stop_index_data", None)
        if stop_index is None:
            stop_index = json.loads(application.state.stop_index_path.read_text())
        for field, query, selection in (
            ("origin", request.origin, request.origin_selection),
            ("destination", request.destination, request.destination_selection),
        ):
            if selection is not None or known_stop(stop_index, query) is not None:
                continue
            suggestions = await run_in_threadpool(
                application.state.geocoder.suggest, query,
            )
            if len(suggestions) > 1:
                field_label = "lähtöpaikka" if field == "origin" else "määränpää"
                return JSONResponse(status_code=409, content={
                    "detail": (
                        f"Valitse täsmällinen {field_label} avautuneesta "
                        "luettelosta ennen reititystä."
                    ),
                    "field": field,
                    "query": query,
                    "suggestions": suggestions,
                })

        response_cache_key = {
            "serviceVersion": SERVICE_VERSION,
            "dataVersion": getattr(application.state, "data_version", "injected"),
            "request": request.model_dump(mode="json", by_alias=True),
        }
        cached = application.state.cache.get("routing:response", response_cache_key)
        if cached is not None:
            return response_with_runtime(cached, cache_hit=True)
        try:
            routing_started_at = runtime_clock.perf_counter()
            selections = {
                " ".join(value.casefold().split()): selection
                for value, selection in (
                    (request.origin, request.origin_selection),
                    (request.destination, request.destination_selection),
                )
                if selection is not None
            }
            geocoder = (
                SelectedEndpointGeocoder(application.state.geocoder, selections)
                if selections else application.state.geocoder
            )
            result = await run_in_threadpool(
                query_address_routes,
                request.origin,
                request.destination,
                request.date,
                request.start_time,
                mode=request.mode,
                timing_profile=request.timing_profile,
                same_day=request.same_day,
                max_results=request.max_results,
                include_diagnostics=request.include_diagnostics,
                include_decision_graph=request.include_decision_graph,
                include_external_geometry=request.include_geometry,
                graph_path=application.state.graph_path,
                stop_index_path=application.state.stop_index_path,
                graph_data=getattr(application.state, "graph_data", None),
                stop_index_data=getattr(application.state, "stop_index_data", None),
                geocoder=geocoder,
                router=application.state.router,
            )
            cacheable_result = dict(result)
            cacheable_result["runtime"] = {
                "routingComputationMilliseconds": round(
                    (runtime_clock.perf_counter() - routing_started_at) * 1000,
                    1,
                ),
            }
            application.state.cache.set(
                "routing:response", response_cache_key, cacheable_result,
            )
            return response_with_runtime(cacheable_result, cache_hit=False)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except RuntimeError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

    return application


app = create_app()
