from __future__ import annotations

import asyncio
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from ..config import Settings, get_settings
from ..models.events import SentinelEvent


class AuditLogger:
    """Append-only redacted audit trail. Never contains raw values — every
    payload is built from sanitized events only."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.settings.ensure_dirs()
        self._lock = threading.Lock()
        self._jsonl = self.settings.audit_dir / "audit.jsonl"
        self._conn = sqlite3.connect(str(self.settings.db_path), check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                seq INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                ts REAL NOT NULL,
                ref TEXT,
                payload TEXT NOT NULL
            )
            """
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_log(session_id)")
        self._conn.commit()

    async def record(self, event: SentinelEvent) -> None:
        payload = json.dumps(event.data, ensure_ascii=False, default=str)
        row = (event.session_id, event.seq, event.type.value, event.ts, event.ref, payload)
        await asyncio.to_thread(self._write, row)

    def _write(self, row: tuple[Any, ...]) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO audit_log (session_id, seq, event_type, ts, ref, payload) VALUES (?,?,?,?,?,?)",
                row,
            )
            self._conn.commit()
            with self._jsonl.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"session_id": row[0], "seq": row[1], "event_type": row[2], "ts": row[3], "ref": row[4], "payload": json.loads(row[5])}, ensure_ascii=False) + "\n")

    async def recent(self, limit: int = 100, session_id: str | None = None) -> list[dict[str, Any]]:
        def _q() -> list[dict[str, Any]]:
            with self._lock:
                if session_id:
                    rows = self._conn.execute(
                        "SELECT id, session_id, seq, event_type, ts, ref, payload FROM audit_log WHERE session_id=? ORDER BY id DESC LIMIT ?",
                        (session_id, limit),
                    ).fetchall()
                else:
                    rows = self._conn.execute(
                        "SELECT id, session_id, seq, event_type, ts, ref, payload FROM audit_log ORDER BY id DESC LIMIT ?",
                        (limit,),
                    ).fetchall()
            out = []
            for r in rows:
                out.append(
                    {
                        "id": r[0],
                        "session_id": r[1],
                        "seq": r[2],
                        "event_type": r[3],
                        "ts": r[4],
                        "ref": r[5],
                        "payload": json.loads(r[6]),
                    }
                )
            return out

        return await asyncio.to_thread(_q)

    async def one(self, record_id: int) -> dict[str, Any] | None:
        def _q() -> tuple[Any, ...] | None:
            with self._lock:
                r = self._conn.execute(
                    "SELECT id, session_id, seq, event_type, ts, ref, payload FROM audit_log WHERE id=?",
                    (record_id,),
                ).fetchone()
            return r

        r = await asyncio.to_thread(_q)
        if not r:
            return None
        return {"id": r[0], "session_id": r[1], "seq": r[2], "event_type": r[3], "ts": r[4], "ref": r[5], "payload": json.loads(r[6])}

    async def count(self) -> int:
        def _q() -> int:
            with self._lock:
                row = self._conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()
            return int(row[0]) if row else 0

        return await asyncio.to_thread(_q)

    async def scan_for(self, needle: str) -> list[dict[str, Any]]:
        """Security helper: find any audit record containing a raw substring."""

        def _q() -> list[dict[str, Any]]:
            found = []
            with self._lock:
                rows = self._conn.execute("SELECT id, session_id, seq, event_type, ts, ref, payload FROM audit_log").fetchall()
                for r in rows:
                    if needle in r[6]:
                        found.append({"id": r[0], "session_id": r[1], "seq": r[2], "event_type": r[3], "ts": r[4], "ref": r[5], "payload": r[6]})
            return found

        return await asyncio.to_thread(_q)