from __future__ import annotations

from enum import Enum
from typing import Awaitable, Callable

from pydantic import BaseModel, Field

from ..models.actions import ActionProposal, ActionType


class AuthorizationPurpose(str, Enum):
    ALLOW = "ALLOW"
    APPROVED = "APPROVED"


class Authorization(BaseModel):
    auth_id: str
    session_id: str
    generation: int
    action_id: str
    purpose: AuthorizationPurpose
    issued_at: float = Field(default_factory=__import__("time").time)
    consumed: bool = False
    consumed_at: float | None = None


class ExecutionError:
    SELECTOR_NOT_FOUND = "SELECTOR_NOT_FOUND"
    SELECTOR_AMBIGUOUS = "SELECTOR_AMBIGUOUS"
    NOT_VISIBLE = "NOT_VISIBLE"
    NAVIGATION_FAILED = "NAVIGATION_FAILED"
    TIMEOUT = "TIMEOUT"
    LOST_BROWSER = "LOST_BROWSER"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"

    SUGGESTIONS: dict[str, list[str]] = {
        SELECTOR_NOT_FOUND: ["RE-OBSERVE"],
        SELECTOR_AMBIGUOUS: ["RE-OBSERVE"],
        NOT_VISIBLE: ["WAIT", "RE-OBSERVE"],
        NAVIGATION_FAILED: ["RETRY", "STOP"],
        TIMEOUT: ["RETRY", "STOP"],
        LOST_BROWSER: ["STOP", "RESET"],
        REJECTED: ["STOP"],
        UNKNOWN: ["RETRY", "STOP"],
    }


class ExecutionResult(BaseModel):
    ok: bool = True
    error_code: str | None = None
    note: str = ""
    url: str = ""
    title: str = ""
    suggested: list[str] = Field(default_factory=list)

    def fail(self, code: str, note: str) -> "ExecutionResult":
        self.ok = False
        self.error_code = code
        self.note = note
        self.suggested = ExecutionError.SUGGESTIONS.get(code, ["RETRY", "STOP"])
        return self


class Executor:
    """Executes typed actions against the real page. Only consents to execute
    when a fresh, unconsumed Authorization matches the exact action and session
    generation. There is no arbitrary page.evaluate path exposed to the agent."""

    def __init__(self, browser, registry, log: Callable[[str], None] | None = None) -> None:
        self._browser = browser
        self._registry = registry
        self._log = log or (lambda s: None)

    async def execute(
        self,
        session_id: str,
        proposal: ActionProposal,
        auth: Authorization,
        consume_cb: Callable[[str, str, int, str], bool] | None = None,
    ) -> ExecutionResult:
        res = ExecutionResult(url="", title="")
        if proposal.generation != auth.generation:
            return res.fail(ExecutionError.REJECTED, "The action is stale for this session generation.")
        if proposal.action_id != auth.action_id:
            return res.fail(ExecutionError.REJECTED, "Authorization does not match this action.")
        if auth.consumed:
            return res.fail(ExecutionError.REJECTED, "This authorization has already been consumed.")
        if consume_cb and not consume_cb(auth.auth_id, auth.session_id, auth.generation, auth.action_id):
            return res.fail(ExecutionError.REJECTED, "This authorization has already been spent.")

        page = await self._browser.page_for(session_id)
        action = proposal.action
        label = action.label
        try:
            if action.action_type == ActionType.CLICK:
                await self._locator(page, proposal).click()
                res.note = f"Clicked {label}."
            elif action.action_type == ActionType.FILL:
                value = action.value
                if action.placeholder_ref:
                    raw = self._registry.resolve(action.placeholder_ref)
                    if raw is None:
                        return res.fail(ExecutionError.REJECTED, f"Value {action.placeholder_ref} is not available locally.")
                    value = raw
                if value is None:
                    return res.fail(ExecutionError.REJECTED, "FILL requires a value or placeholder ref.")
                await self._locator(page, proposal).fill(value)
                res.note = f"Filled {label}."
            elif action.action_type == ActionType.SUBMIT:
                loc = self._locator(page, proposal)
                await loc.click(timeout=8000)
                res.note = f"Submitted {label}."
            elif action.action_type == ActionType.NAVIGATE:
                await page.goto(action.url, timeout=self._browser.settings.nav_timeout_ms, wait_until="domcontentloaded")
                res.note = f"Navigated to {action.url}."
            elif action.action_type == ActionType.EXTRACT:
                text = await self._locator(page, proposal).inner_text(timeout=8000)
                res.note = f"Extracted content from {action.selector}."
                res.__dict__["extracted"] = text[:800]
            elif action.action_type == ActionType.WAIT:
                self._log("wait")
                await page.wait_for_timeout(action.duration_ms)
                res.note = f"Waited {action.duration_ms}ms."
            else:
                return res.fail(ExecutionError.UNKNOWN, f"Unsupported action type {action.action_type}.")
        except Exception as exc:
            return self._classify(page, exc, action.action_type.value)

        try:
            res.url = page.url
            res.title = await page.title()
        except Exception:
            pass
        return res

    def _locator(self, page, proposal, **_):
        from playwright.async_api import async_playwright  # noqa: F401 (type stability)

        selector = proposal.action.selector
        return page.locator(selector).first

    def _classify(self, page, exc: Exception, action_name: str) -> ExecutionResult:
        msg = str(exc)
        from ..models.actions import ActionType  # noqa: F401

        if "Timeout" in msg or "waiting for" in msg:
            return ExecutionResult(ok=False, error_code=ExecutionError.TIMEOUT, note=f"{action_name} timed out.", suggested=ExecutionError.SUGGESTIONS[ExecutionError.TIMEOUT])
        if "strict mode violation" in msg:
            return ExecutionResult(ok=False, error_code=ExecutionError.SELECTOR_AMBIGUOUS, note=f"Target resolved to multiple elements.", suggested=ExecutionError.SUGGESTIONS[ExecutionError.SELECTOR_AMBIGUOUS])
        if "Cannot find" in msg or "waiting for selector" in msg:
            return ExecutionResult(ok=False, error_code=ExecutionError.SELECTOR_NOT_FOUND, note=f"Target no longer exists.", suggested=ExecutionError.SUGGESTIONS[ExecutionError.SELECTOR_NOT_FOUND])
        if "is not visible" in msg or "not visible" in msg:
            return ExecutionResult(ok=False, error_code=ExecutionError.NOT_VISIBLE, note=f"Target is not visible.", suggested=ExecutionError.SUGGESTIONS[ExecutionError.NOT_VISIBLE])
        if "Navigation failed" in msg or "net::" in msg:
            return ExecutionResult(ok=False, error_code=ExecutionError.NAVIGATION_FAILED, note=msg[:160], suggested=ExecutionError.SUGGESTIONS[ExecutionError.NAVIGATION_FAILED])
        if "Target page, context or browser has been closed" in msg or "browser has been closed" in msg:
            return ExecutionResult(ok=False, error_code=ExecutionError.LOST_BROWSER, note=f"Browser disconnected during execution.", suggested=ExecutionError.SUGGESTIONS[ExecutionError.LOST_BROWSER])
        return ExecutionResult(ok=False, error_code=ExecutionError.UNKNOWN, note=msg[:160], suggested=ExecutionError.SUGGESTIONS[ExecutionError.UNKNOWN])