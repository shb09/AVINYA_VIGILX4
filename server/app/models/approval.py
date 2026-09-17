from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, Field


class PendingApproval(BaseModel):
    action_id: str
    generation: int
    expiry: float
    proposal: dict[str, Any] = Field(default_factory=dict)
    decision: dict[str, Any] = Field(default_factory=dict)
    provenance: list[dict[str, Any]] = Field(default_factory=list)

    @property
    def expired(self) -> bool:
        return time.time() > self.expiry