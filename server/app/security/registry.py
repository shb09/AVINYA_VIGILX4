from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from ..models.state import DataClass
from .detector import RawHit, detect_raw

_PH_PREFIX: dict[DataClass, str] = {
    DataClass.SECRET: "SECRET",
    DataClass.CANARY: "CANARY",
    DataClass.CREDENTIAL: "CRED",
    DataClass.CARD: "CARD",
    DataClass.EMAIL: "EMAIL",
    DataClass.PII: "PII",
    DataClass.LOCATION: "LOCATION",
    DataClass.PERSONAL: "PERSONAL",
    DataClass.SENSITIVE: "SENSITIVE",
    DataClass.PUBLIC: "PUBLIC",
}


@dataclass
class RawEntry:
    ph: str
    raw: str
    data_class: DataClass
    source: str
    ts: float
    hint: str = ""


@dataclass
class RedactedHit:
    ph: str
    data_class: DataClass
    hint: str
    source: str


@dataclass
class EntrySummary:
    ph: str
    data_class: DataClass
    source: str
    ts: float
    hint: str = ""


class DataRegistry:
    """The raw-data boundary. Raw values live ONLY here, inside the server
    process, keyed by stable [PLACEHOLDER] tokens. Everything that crosses a
    serialization boundary (API, WS, audit, planner context) uses placeholders.
    """

    def __init__(self, canary_seed: str | None = None) -> None:
        self._entries: dict[str, RawEntry] = {}
        self._by_raw: dict[str, str] = {}
        self._counter = 0
        self.canary_ph: str | None = None
        if canary_seed:
            self.add(canary_seed, DataClass.CANARY, "vault.user.primary_token", "seeded canary secret")

    def add(self, raw: str, data_class: DataClass, source: str, hint: str = "") -> str:
        existing = self._by_raw.get(raw)
        if existing:
            return existing
        self._counter += 1
        ph = f"[{_PH_PREFIX.get(data_class, 'DATA')}_{self._counter}]"
        entry = RawEntry(ph=ph, raw=raw, data_class=data_class, source=source, ts=time.time(), hint=hint)
        self._entries[ph] = entry
        self._by_raw[raw] = ph
        if data_class == DataClass.CANARY and self.canary_ph is None:
            self.canary_ph = ph
        return ph

    def resolve(self, ph: str) -> str | None:
        entry = self._entries.get(ph)
        return entry.raw if entry else None

    def summary(self) -> list[EntrySummary]:
        out = []
        for entry in self._entries.values():
            out.append(
                EntrySummary(ph=entry.ph, data_class=entry.data_class, source=entry.source, ts=entry.ts, hint=entry.hint)
            )
        return list(sorted(out, key=lambda e: e.ph))

    def redact(self, text: str, source: str = "page", field_hint: str = "") -> tuple[str, list[RedactedHit]]:
        if not text:
            return text, []
        out = text
        hits: list[RedactedHit] = []
        replacements: list[tuple[str, str]] = []

        known = sorted(self._entries.values(), key=lambda e: len(e.raw), reverse=True)
        for entry in known:
            if entry.raw and entry.raw in out:
                replacements.append((entry.raw, entry.ph))
                hits.append(RedactedHit(entry.ph, entry.data_class, field_hint or entry.hint, source))
        for raw, ph in replacements:
            out = out.replace(raw, ph)

        for hit in detect_raw(out, None):
            ph = self.add(hit.raw, hit.data_class, source, hit.hint)
            if hit.raw in out:
                out = out.replace(hit.raw, ph)
                hits.append(RedactedHit(ph, hit.data_class, field_hint or hit.hint, source))

        return out, hits

    def classify(self, raw: str) -> DataClass:
        hits = detect_raw(raw, None)
        if hits:
            return max(hits, key=lambda h: _sensitivity(h.data_class)).data_class
        return DataClass.PUBLIC

    def to_public_dict(self) -> dict[str, Any]:
        return {"entries": [s.__dict__ for s in self.summary()], "canary": self.canary_ph}


def _sensitivity(cls: DataClass) -> int:
    return {
        DataClass.PUBLIC: 0,
        DataClass.PERSONAL: 1,
        DataClass.EMAIL: 2,
        DataClass.PII: 3,
        DataClass.LOCATION: 3,
        DataClass.SENSITIVE: 4,
        DataClass.CREDENTIAL: 5,
        DataClass.CARD: 6,
        DataClass.SECRET: 7,
        DataClass.CANARY: 8,
    }.get(cls, 0)