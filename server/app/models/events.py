from __future__ import annotations

import time
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EventType(str, Enum):
    SESSION_STARTED = "SESSION_STARTED"
    BROWSER_STARTED = "BROWSER_STARTED"
    BROWSER_CONNECTED = "BROWSER_CONNECTED"
    BROWSER_NAVIGATED = "BROWSER_NAVIGATED"
    PAGE_OBSERVED = "PAGE_OBSERVED"
    CONTENT_CLASSIFIED = "CONTENT_CLASSIFIED"
    DATA_DETECTED = "DATA_DETECTED"
    DATA_REDACTED = "DATA_REDACTED"
    AGENT_PLANNING = "AGENT_PLANNING"
    PLANNER_CONTEXT = "PLANNER_CONTEXT"
    ACTION_PROPOSED = "ACTION_PROPOSED"
    PROVENANCE_CREATED = "PROVENANCE_CREATED"
    POLICY_EVALUATED = "POLICY_EVALUATED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVAL_GRANTED = "APPROVAL_GRANTED"
    APPROVAL_DENIED = "APPROVAL_DENIED"
    APPROVAL_EXPIRED = "APPROVAL_EXPIRED"
    ACTION_EXECUTED = "ACTION_EXECUTED"
    ACTION_FAILED = "ACTION_FAILED"
    ACTION_BLOCKED = "ACTION_BLOCKED"
    EXECUTION_PREVENTED = "EXECUTION_PREVENTED"
    THREAT_DETECTED = "THREAT_DETECTED"
    AGENT_STATUS = "AGENT_STATUS"
    BROWSER_STATUS = "BROWSER_STATUS"
    HUMAN_CONTROL_CHANGED = "HUMAN_CONTROL_CHANGED"
    BROWSER_ERROR = "BROWSER_ERROR"
    STATE_SNAPSHOT = "STATE_SNAPSHOT"
    SCREENSHOT = "SCREENSHOT"
    AGENT_COMPLETED = "AGENT_COMPLETED"
    SESSION_STOPPED = "SESSION_STOPPED"
    AUDIT_RECORDED = "AUDIT_RECORDED"


class SentinelEvent(BaseModel):
    seq: int
    session_id: str
    type: EventType
    ts: float = Field(default_factory=time.time)
    data: dict[str, Any] = Field(default_factory=dict)
    ref: str | None = None  # action_id / provenance chain id / threat id


def ev(session_id: str, seq: int, event_type: EventType, data: dict[str, Any] | None = None, ref: str | None = None) -> SentinelEvent:
    return SentinelEvent(
        seq=seq,
        session_id=session_id,
        type=event_type,
        data=data or {},
        ref=ref,
    )