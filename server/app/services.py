from __future__ import annotations

from .audit.logger import AuditLogger
from .agent.planner import build_planner
from .browser.manager import BrowserManager
from .config import get_settings
from .policy.engine import PolicyEngine
from .provenance.provenance import ProvenanceBuilder
from .session.hub import EventHub
from .session.session import SessionManager


class Services:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.hub = EventHub()
        self.audit = AuditLogger(self.settings)
        self.browser = BrowserManager(self.settings, emit=self.hub.publish)
        self.policy = PolicyEngine()
        self.provenance = ProvenanceBuilder()
        self.planner = build_planner(self.settings)
        self.sessions = SessionManager(
            self.settings,
            self.hub,
            self.browser,
            self.audit,
            self.policy,
            self.provenance,
            self.planner,
        )

    async def shutdown(self) -> None:
        await self.sessions.shutdown()
        if hasattr(self.planner, "close"):
            try:
                await self.planner.close()
            except Exception:
                pass