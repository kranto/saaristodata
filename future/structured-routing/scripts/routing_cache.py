#!/usr/bin/env python3
"""Persistent JSON cache shared by the external routing adapters."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from pathlib import Path


class SQLiteJsonCache:
    """Store JSON-compatible values in a small, process-safe SQLite database."""

    def __init__(self, path: Path | str, *, default_ttl_seconds: int = 30 * 24 * 3600) -> None:
        self.path = Path(path)
        self.default_ttl_seconds = default_ttl_seconds
        self._initialization_lock = threading.Lock()
        self._initialized = False

    @staticmethod
    def cache_key(value: object) -> str:
        serialized = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _connect(self) -> sqlite3.Connection:
        self._initialize()
        connection = sqlite3.connect(self.path, timeout=30)
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    def _initialize(self) -> None:
        if self._initialized:
            return
        with self._initialization_lock:
            if self._initialized:
                return
            self.path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.path, timeout=30)
            try:
                connection.execute("PRAGMA busy_timeout = 30000")
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS json_cache (
                        namespace TEXT NOT NULL,
                        cache_key TEXT NOT NULL,
                        value_json TEXT NOT NULL,
                        created_at INTEGER NOT NULL,
                        expires_at INTEGER NOT NULL,
                        PRIMARY KEY (namespace, cache_key)
                    )
                    """
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS json_cache_expiry ON json_cache(expires_at)"
                )
                connection.commit()
            finally:
                connection.close()
            self._initialized = True

    def get(self, namespace: str, key_data: object) -> object | None:
        key = self.cache_key(key_data)
        now = round(time.time())
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT value_json FROM json_cache
                WHERE namespace = ? AND cache_key = ? AND expires_at > ?
                """,
                (namespace, key, now),
            ).fetchone()
            if row is None:
                connection.execute(
                    "DELETE FROM json_cache WHERE namespace = ? AND cache_key = ?",
                    (namespace, key),
                )
                return None
        return json.loads(row[0])

    def set(
        self,
        namespace: str,
        key_data: object,
        value: object,
        *,
        ttl_seconds: int | None = None,
    ) -> None:
        key = self.cache_key(key_data)
        now = round(time.time())
        expires = now + (
            self.default_ttl_seconds if ttl_seconds is None else ttl_seconds
        )
        serialized = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO json_cache (
                    namespace, cache_key, value_json, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(namespace, cache_key) DO UPDATE SET
                    value_json = excluded.value_json,
                    created_at = excluded.created_at,
                    expires_at = excluded.expires_at
                """,
                (namespace, key, serialized, now, expires),
            )

    def purge_expired(self) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM json_cache WHERE expires_at <= ?", (round(time.time()),)
            )
            return cursor.rowcount
