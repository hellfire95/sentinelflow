"""SQLite cache so the same IOC is never re-queried within TTL."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from ..config import DB_PATH

# Cache reputation for 7 days by default (free-tier friendly).
DEFAULT_TTL_SECONDS = 7 * 24 * 3600


class IntelCache:
    def __init__(self, db_path: str | None = None):
        path = db_path or DB_PATH
        # Keep cache alongside main DB, separate file for clarity.
        if path == DB_PATH:
            path = str(Path(path).with_name("threat_intel_cache.db"))
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS intel_cache (
                ioc_type TEXT NOT NULL,
                ioc_value TEXT NOT NULL,
                result_json TEXT NOT NULL,
                fetched_at REAL NOT NULL,
                PRIMARY KEY (ioc_type, ioc_value)
            )
            """
        )
        self.conn.commit()

    def get(self, ioc_type: str, ioc_value: str, ttl: int = DEFAULT_TTL_SECONDS) -> dict | None:
        row = self.conn.execute(
            "SELECT result_json, fetched_at FROM intel_cache WHERE ioc_type=? AND ioc_value=?",
            (ioc_type, ioc_value.lower()),
        ).fetchone()
        if not row:
            return None
        result_json, fetched_at = row
        if time.time() - fetched_at > ttl:
            return None
        data = json.loads(result_json)
        data["cached"] = True
        return data

    def put(self, ioc_type: str, ioc_value: str, result: dict) -> None:
        payload = dict(result)
        payload.pop("cached", None)
        self.conn.execute(
            "INSERT OR REPLACE INTO intel_cache VALUES (?, ?, ?, ?)",
            (ioc_type, ioc_value.lower(), json.dumps(payload), time.time()),
        )
        self.conn.commit()
