#!/usr/bin/env python3
"""Shared helpers for the complementary land-cover pipeline."""

from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPO_ROOT / "data-sources" / "landcover.yml"


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        manifest = yaml.safe_load(stream)
    if manifest.get("schema_version") != 1:
        raise ValueError(f"Unsupported manifest schema in {path}")
    return manifest


def area_config(manifest: dict, area_id: str) -> dict:
    try:
        return manifest["areas"][area_id]
    except KeyError as error:
        choices = ", ".join(sorted(manifest.get("areas", {})))
        raise ValueError(f"Unknown area {area_id!r}; choose one of: {choices}") from error


def source_config(manifest: dict, source_id: str) -> dict:
    try:
        return manifest["sources"][source_id]
    except KeyError as error:
        choices = ", ".join(sorted(manifest.get("sources", {})))
        raise ValueError(f"Unknown source {source_id!r}; choose one of: {choices}") from error

