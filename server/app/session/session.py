from __future__ import annotations

import asyncio
import time
import uuid
from collections import deque
from typing import Any

from ..browser.executor import Authorization, AuthorizationPurpose
from ..config import Settings, get_settings
from ..models.actions import ActionProposal
from ..models.approval import PendingApproval
from ..models.events import EventType, SentinelEvent, ev
from ..models.state import AgentStatus, BrowserStatus, DataClass, TrustLevel, Verdict
from ..models.threat import Threat
from ..policy.engine import Evaluation
from ..provenance.provenance import ProvenanceChain
from ..security.registry import DataRegistry


class Session:
    """Canonical runtime object for one browser session. Sanitized snapshots
    are what the frontend and audit see; raw secrets stay in self.registry."""

    def __init__(self, session_id: str, manager: "SessionManager") -> None:
        self.id = session_id
        self._mgr = manager
        self.settings: Settings = manager.settings
        self.generation = 1
        self.created = time.time()

        self.browser_status = BrowserStatus.STARTING
        self.agent_status = AgentStatus.IDLE

        self.current_url = ""
        self.host = ""
        self.title = ""
        self.page_trust = TrustLevel.PARTIAL
        self.page_class = "UNKNOWN"

        self.task = ""
        self.planner_name = "LOCAL PLANNER"
        self.human_control = False
        self.agent_flags: dict[str, Any] = {}

        self.registry = DataRegistry()
        self.events: deque[SentinelEvent] = deque(maxlen=self.settings.max_session_events)
        self._seq = 0
        self.threats: list[Threat] = []
        self.proposals_seen: list[str] = []
        self.executed_action_ids: list[str] = []

        self.current_proposal: ActionProposal | None = None
        self.current_decision: Evaluation | None = None
        self.current_chain: ProvenanceChain | None = None
        self.pending_approval: PendingApproval | None = None

        self.approval_event = asyncio.Event()
        self.approval_result: bool | None = None
        self.stop_requested = False
        self.resume_event = asyncio.Event()

        self.agent_task: asyncio.Task | None = None
        self.streamer_task: asyncio.Task | None = None

        self.last_error: dict[str, Any] | None = None
        self.planner_transcripts: list[dict[str, Any]] = []
        self.narrative = "SENTINEL is ready. Agent is idle."
        self.provider_name = "LOCAL PLANNER"

        self._auth_store: dict[str, Any] = {}

    # ------------------------------------------------------------ sequencing
    def next_seq(self) -> int:
        self._seq += 1
        return self._seq

    async def emit(self, event_type: EventType, data: dict[str, Any] | None = None, ref: str | None = None, stream_only: bool = False) -> SentinelEvent:
        event = ev(self.id, self.next_seq(), event_type, data, ref)
        event.data["seq"] = event.seq
        await self._mgr.dispatch(self, event, stream_only=stream_only)
        return event

    def note(self, text: str) -> None:
        self.narrative = text

    # ------------------------------------------------------------ authorization
    def issue_authorization(self, proposal: ActionProposal, purpose: str) -> Authorization:
        auth = Authorization(
            auth_id=f"auth_{uuid.uuid4().hex[:6]}",
            session_id=self.id,
            generation=proposal.generation,
            action_id=proposal.action_id,
            purpose=AuthorizationPurpose(purpose),
        )
        self._auth_store[auth.auth_id] = auth
        return auth

    def consume_authorization(self, auth_id: str, session_id: str, generation: int, action_id: str) -> bool:
        auth = self._auth_store.get(auth_id)
        if not auth:
            return False
        if auth.session_id != session_id or auth.generation != generation or auth.action_id != action_id:
            return False
        if auth.consumed:
            return False
        auth.consumed = True
        auth.consumed_at = time.time()
        return True

    # ------------------------------------------------------------ state snapshot (sanitized)
    def snapshot(self) -> dict[str, Any]:
        proposal = self.current_proposal
        decision = self.current_decision
        return {
            "session_id": self.id,
            "generation": self.generation,
            "created": self.created,
            "browser": {
                "status": self.browser_status.value,
                "url": self.current_url,
                "host": self.host,
                "title": self.title,
                "page_trust": self.page_trust.value,
                "page_class": self.page_class,
            },
            "agent": {
                "status": self.agent_status.value,
                "task": self.task,
                "planner": self.provider_name,
                "error": self.last_error,
            },
            "human_control": self.human_control,
            "narrative": self.narrative,
            "current_action": proposal.model_dump(exclude={"generation", "confidence"}) if proposal else None,
            "security": decision.to_ui() if decision else None,
            "pending_approval": self._approval_snapshot(),
            "provenance": self.current_chain.to_ui() if self.current_chain else None,
            "data": self.registry.to_public_dict(),
            "threats": [t.model_dump() for t in self.threats[-12:]],
            "audit_count": sum(1 for e in self.events if e.type != EventType.SCREENSHOT),
            "event_count": len(self.events),
            "executed_count": len(self.executed_action_ids),
            "proposal_count": len(self.proposals_seen),
        }

    def _approval_snapshot(self) -> dict[str, Any] | None:
        if not self.pending_approval:
            return None
        pa = self.pending_approval
        return {
            "action_id": pa.action_id,
            "exchange": "ONE-TIME",
            "expires_in": max(0, int(pa.expiry - time.time())),
            "proposal": pa.proposal,
            "decision": pa.decision,
            "provenance": pa.provenance,
        }

    def record_threat(self, threat: Threat) -> None:
        self.threats.append(threat)


class SessionManager:
    def __init__(self, settings: Settings, hub, browser, audit, policy_engine, provenance_builder, planner) -> None:
        self.settings = settings
        self.hub = hub
        self.browser = browser
        self.audit = audit
        self.policy = policy_engine
        self.provenance = provenance_builder
        self.planner = planner
        self.sessions: dict[str, Session] = {}
        self._lock = asyncio.Lock()

    async def create_session(self) -> Session:
        session_id = uuid.uuid4().hex[:8]
        session = Session(session_id, self)
        self.sessions[session_id] = session
        await session.emit(EventType.SESSION_STARTED, {"session_id": session_id, "planner": self.planner.provider_name, "viewport": [self.settings.viewport_width, self.settings.viewport_height]})
        await self._boot_browser(session)
        session.streamer_task = asyncio.create_task(self._streamer(session))
        return session

    async def _boot_browser(self, session: Session) -> None:
        session.browser_status = BrowserStatus.STARTING
        try:
            await self.browser.ensure_started(session.id)
            await self.browser.page_for(session.id)
            session.browser_status = BrowserStatus.READY
            await session.emit(EventType.BROWSER_STARTED, {"browser": "chromium"})
            await session.emit(EventType.BROWSER_CONNECTED, {"browser": "chromium", "viewport": [self.settings.viewport_width, self.settings.viewport_height]})
        except Exception as exc:
            session.browser_status = BrowserStatus.ERROR
            session.last_error = {"title": "BROWSER FAILED", "detail": str(exc), "suggested": ["RETRY", "RESET"]}
            await session.emit(EventType.BROWSER_ERROR, {"message": str(exc)}, ref=session.id)
        if session.browser_status not in {BrowserStatus.ERROR}:
            await self.navigate(session.id, self._home_url(), actor="system")

    def _home_url(self) -> str:
        return f"http://{self.settings.home_host}:{self.settings.port}/"

    async def dispatch(self, session: Session, event: SentinelEvent, stream_only: bool = False) -> None:
        if not stream_only:
            session.events.append(event)
        await self.hub.publish(event)
        if not stream_only:
            asyncio.get_running_loop().create_task(self._audit_safe(event))

    async def _audit_safe(self, event: SentinelEvent) -> None:
        try:
            await self.audit.record(event)
        except Exception:
            pass

    async def _streamer(self, session: Session) -> None:
        while True:
            try:
                if session.id in self.sessions and self.hub.subscriber_count(session.id) > 0 and session.browser_status not in {BrowserStatus.ERROR, BrowserStatus.DISCONNECTED, BrowserStatus.STOPPED}:
                    await self.browser.stream_screenshot(session.id)
            except Exception:
                pass
            await asyncio.sleep(self.settings.shot_interval_ms / 1000)

    # ------------------------------------------------------------ commands
    async def navigate(self, session_id: str, url: str, actor: str = "human") -> None:
        session = self.sessions[session_id]
        session.browser_status = BrowserStatus.NAVIGATING
        try:
            await self.browser.navigate(session_id, url)
            session.browser_status = BrowserStatus.LOADED
            session.current_url = url
            await session.emit(EventType.BROWSER_NAVIGATED, {"url": url, "actor": actor}, ref=session.id)
            await self._refresh_page_meta(session)
            await self.browser.stream_screenshot(session_id)
        except Exception as exc:
            session.browser_status = BrowserStatus.ERROR
            session.last_error = {"title": "NAVIGATION FAILED", "detail": str(exc)[:200], "suggested": ["RETRY", "RESET"]}
            await session.emit(EventType.BROWSER_ERROR, {"message": str(exc)[:200], "url": url}, ref=session.id)

    async def _refresh_page_meta(self, session: Session) -> None:
        from ..security.trust import page_trust_for_host, normalize_host

        obs = await self.browser.observe(session.id)
        host = normalize_host(obs.get("host"))
        session.host = host or session.host
        session.title = (obs.get("title") or "").strip() or session.title
        session.page_trust = page_trust_for_host(host, self.settings)
        if session.host:
            session.current_url = obs.get("url") or session.current_url

    async def run_agent(self, session_id: str, task: str, start_url: str | None = None, seed_canary: bool = False) -> None:
        session = self.sessions[session_id]
        if session.agent_status not in {AgentStatus.IDLE, AgentStatus.STOPPED, AgentStatus.COMPLETED, AgentStatus.BLOCKED, AgentStatus.FAILED}:
            raise RuntimeError(f"Agent is already busy ({session.agent_status.value}).")
        if start_url:
            await self.navigate(session_id, start_url, actor="system")
        if seed_canary and not session.registry.canary_ph:
            session.registry.add(self.settings.canary_seed, DataClass.CANARY, "vault.user.primary_token", "seeded canary secret")
        session.stop_requested = False
        session.approval_result = None
        session.last_error = None
        session.task = task
        session.provider_name = self.planner.provider_name
        await session.emit(EventType.AGENT_STATUS, {"status": AgentStatus.OBSERVING.value, "task": task})

        from ..agent.runner import AgentRunner

        runner = AgentRunner(self, session)
        session.agent_task = asyncio.create_task(runner.run())

    async def stop_agent(self, session_id: str) -> None:
        session = self.sessions[session_id]
        session.stop_requested = True
        task = session.agent_task
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        session.approval_event.set()
        if session.agent_status not in {AgentStatus.BLOCKED, AgentStatus.FAILED, AgentStatus.COMPLETED}:
            session.agent_status = AgentStatus.STOPPED
            await session.emit(EventType.AGENT_STATUS, {"status": AgentStatus.STOPPED.value, "reason": "stopped by user"})
        session.stop_requested = False

    async def respond_approval(self, session_id: str, action_id: str, decision: bool) -> None:
        session = self.sessions[session_id]
        pa = session.pending_approval
        if not pa or pa.action_id != action_id:
            raise RuntimeError("No approval is pending for that action.")
        if pa.expired:
            session.pending_approval = None
            await session.emit(EventType.APPROVAL_EXPIRED, {"action_id": action_id}, ref=action_id)
            raise RuntimeError("Approval request expired.")
        session.pending_approval = None
        session.approval_result = decision
        session.approval_event.set()
        if decision:
            await session.emit(EventType.APPROVAL_GRANTED, {"action_id": action_id, "exchange": "ONE-TIME"}, ref=action_id)
        else:
            await session.emit(EventType.APPROVAL_DENIED, {"action_id": action_id}, ref=action_id)

    async def take_control(self, session_id: str) -> None:
        session = self.sessions[session_id]
        session.human_control = True
        if session.agent_status in {AgentStatus.OBSERVING, AgentStatus.PLANNING, AgentStatus.PROPOSING, AgentStatus.WAITING_FOR_AUTHORIZATION, AgentStatus.WAITING_FOR_APPROVAL, AgentStatus.EXECUTING, AgentStatus.PAUSED}:
            session.agent_status = AgentStatus.PAUSED
            await session.emit(EventType.AGENT_STATUS, {"status": AgentStatus.PAUSED.value, "reason": "human took control"})
        await session.emit(EventType.HUMAN_CONTROL_CHANGED, {"control": True})

    async def release_control(self, session_id: str) -> None:
        session = self.sessions[session_id]
        session.human_control = False
        session.resume_event.set()
        await session.emit(EventType.HUMAN_CONTROL_CHANGED, {"control": False})

    async def reset_session(self, session_id: str) -> None:
        session = self.sessions[session_id]
        session.generation += 1
        session.registry = DataRegistry()
        session.events.clear()
        session.threats.clear()
        session.proposals_seen.clear()
        session.executed_action_ids.clear()
        session.current_proposal = None
        session.current_decision = None
        session.current_chain = None
        session.pending_approval = None
        session.approval_result = None
        session.stop_requested = False
        session.human_control = False
        session.agent_flags = {}
        session.last_error = None
        session.task = ""
        session.agent_status = AgentStatus.IDLE
        session.narrative = "Session reset. Agent is idle."
        session._auth_store.clear()
        await session.emit(EventType.SESSION_STARTED, {"session_id": session_id, "planner": self.planner.provider_name, "reset": True})
        await session.emit(EventType.AGENT_STATUS, {"status": AgentStatus.IDLE.value, "reason": "session reset"})
        await self.browser.stream_screenshot(session_id)

    async def wait_until_terminal(self, session_id: str, timeout: float = 60.0) -> dict[str, Any]:
        """Block until the agent reaches a terminal state (used by benchmark)."""
        deadline = time.time() + timeout
        session = self.sessions[session_id]
        terminal = {AgentStatus.COMPLETED, AgentStatus.BLOCKED, AgentStatus.FAILED, AgentStatus.STOPPED}
        while time.time() < deadline:
            if session.agent_status in terminal:
                return session.snapshot()
            await asyncio.sleep(0.1)
        return session.snapshot()

    async def delete_session(self, session_id: str) -> None:
        session = self.sessions.pop(session_id, None)
        if not session:
            return
        if session.agent_task and not session.agent_task.done():
            session.agent_task.cancel()
        if session.streamer_task and not session.streamer_task.done():
            session.streamer_task.cancel()
        await self.browser.close_session(session_id)
        try:
            await session.emit(EventType.SESSION_STOPPED, {"session_id": session_id})
        except Exception:
            pass

    async def shutdown(self) -> None:
        for sid in list(self.sessions.keys()):
            await self.delete_session(sid)
        await self.browser.shutdown()