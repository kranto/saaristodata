#!/usr/bin/env python3

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from routing_cache import SQLiteJsonCache  # noqa: E402


class SQLiteJsonCacheTests(unittest.TestCase):
    def test_value_survives_a_new_cache_instance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cache.sqlite3"
            first = SQLiteJsonCache(path)
            first.set("test", {"query": "Åva"}, {"result": 42})
            second = SQLiteJsonCache(path)
            self.assertEqual(
                second.get("test", {"query": "Åva"}), {"result": 42},
            )

    def test_expired_value_is_not_returned(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache = SQLiteJsonCache(Path(directory) / "cache.sqlite3")
            cache.set("test", "key", {"result": 42}, ttl_seconds=-1)
            self.assertIsNone(cache.get("test", "key"))


if __name__ == "__main__":
    unittest.main()
