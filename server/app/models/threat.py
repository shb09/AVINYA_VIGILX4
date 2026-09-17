from __future__ import annotations

import time
import uuid
from typing import Any

from pydantic import BaseModel, Field

from .state import ThreatType


class Threat(BaseModel):
    id: str = Field(default_factory=lambda: f"thr_{uuid.uuid4().hex[:6]}")
    type: ThreatType
    title: str
    detail: str
    severity: str = "HIGH"
    ts: float = Field(default_factory=time.time)
    action_id: str | None = None
    story: dict[str, Any] | None = None