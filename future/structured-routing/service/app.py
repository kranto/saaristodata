#!/usr/bin/env python3
"""FastAPI entry point for address-to-address archipelago routing."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from contextlib import asynccontextmanager
from datetime import date, time
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
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
from query_address_routes import DEFAULT_STOP_INDEX, query_address_routes  # noqa: E402
from route_itinerary import DEFAULT_GRAPH  # noqa: E402
from routing_cache import SQLiteJsonCache  # noqa: E402


SERVICE_VERSION = "0.4.11"
ROUTE_PREVIEW = ROOT / "service" / "route-preview.html"


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

    @field_validator("start_time")
    @classmethod
    def start_time_is_a_local_minute(cls, value: time) -> time:
        if value.tzinfo is not None or value.second or value.microsecond:
            raise ValueError("startTime must be a local time with minute precision")
        return value


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

    @application.post("/route")
    async def route(request: RouteRequest) -> dict:
        response_cache_key = {
            "serviceVersion": SERVICE_VERSION,
            "dataVersion": getattr(application.state, "data_version", "injected"),
            "request": request.model_dump(mode="json", by_alias=True),
        }
        cached = application.state.cache.get("routing:response", response_cache_key)
        if cached is not None:
            return cached
        try:
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
                geocoder=application.state.geocoder,
                router=application.state.router,
            )
            application.state.cache.set("routing:response", response_cache_key, result)
            return result
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except RuntimeError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

    return application


app = create_app()
