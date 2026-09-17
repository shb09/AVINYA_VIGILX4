from __future__ import annotations

import asyncio
import json
import time
import uuid
from urllib.parse import urljoin, urlparse
from typing import Any

from ..browser.executor import Executor, ExecutionResult
from ..config import get_settings
from ..models.actions import ActionProposal, ActionType
from ..models.events import EventType
from ..models.state import AgentStatus, BrowserStatus, DataClass, TrustLevel, Verdict
from ..models.threat import Threat
from ..policy.engine import PolicyContext
from ..provenance.provenance import (
    DataRef,
    DestInfo,
    InstructionRef,
    PageInfo,
    ProvenanceBuilder,
)
from ..security.detector import (
    classify_field,
    detect_instructions,
)
from ..security.trust import (
    classify_destination,
    normalize_host,
    page_trust_for_host,
)
from .planner import (
    AgentContext,
    ElementSummary,
    FieldSummary,
    FormSummary,
    validate_action_shape,
)

_TRANSFER_ACTIONS = {ActionType.FILL, ActionType.SUBMIT, ActionType.NAVIGATE}


class AgentRunner:
    def __init__(self, manager, session) -> None:
        self.manager = manager
        self.session = session
        self.settings = manager.settings
        self.browser = manager.browser
        self.policy = manager.policy
        self.provenance = manager.provenance
        self.planner = manager.planner
        self._ctx: AgentContext | None = None
        self._step = 0

    # ============================================================ lifecycle
    async def run(self) -> None:
        session = self.session
        try:
            while not session.stop_requested:
                if session.human_control:
                    await self._hold_for_human()
                    if session.stop_requested:
                        break
                if self._step >= self.settings.agent_max_steps:
                    break

                await self._observe()

                if session.stop_requested:
                    break
                if session.human_control:
                    continue

                plan = await self._plan()
                emitted = await self._emit_planner_context()
                del emitted

                if session.stop_requested:
                    break
                if not plan.proposals or plan.done:
                    await self._finish(session)
                    return

                for proposal in plan.proposals[:1]:
                    broke = await self._handle_proposal(proposal)
                    if broke or session.stop_requested:
                        return

            if session.agent_status not in {AgentStatus.BLOCKED, AgentStatus.FAILED, AgentStatus.COMPLETED, AgentStatus.STOPPED}:
                await self._finish(session)
        except asyncio.CancelledError:
            session.agent_status = AgentStatus.STOPPED
            await session.emit(EventType.AGENT_STATUS, {"status": AgentStatus.STOPPED.value, "reason": "stopped by user"})
            session.narrative = "Agent stopped by the user."
            raise
        except Exception as exc:  # pragma: no cover - defensive
            session.agent_status = AgentStatus.FAILED
            session.last_error = {"title": "AGENT FAILED", "detail": str(exc)[:240], "suggested": ["STOP", "RESET"]}
            await session.emit(EventType.ACTION_BLOCKED, {"error": str(exc)[:240], "policy_ids": ["UNHANDLED_ERROR"]})
            await session.emit(EventType.BROWSER_ERROR, {"message": str(exc)[:240]})

    async def _hold_for_human(self) -> None:
        session = self.session
        if session.agent_status != AgentStatus.PAUSED:
            session.agent_status = AgentStatus.PAUSED
        while session.human_control and not session.stop_requested:
            try:
                await asyncio.wait_for(session.resume_event.wait(), timeout=120)
            except asyncio.TimeoutError:
                continue
            session.resume_event.clear()
            if not session.human_control:
                break

    async def _finish(self, session) -> None:
        if session.agent_status in {AgentStatus.BLOCKED, AgentStatus.FAILED, AgentStatus.STOPPED}:
            return
        session.agent_status = AgentStatus.COMPLETED
        session.narrative = "Task complete. Sentinel authorized every executed action."
        await session.emit(EventType.AGENT_STATUS, {"status": AgentStatus.COMPLETED.value})
        await session.emit(
            EventType.AGENT_COMPLETED,
            {"url": session.current_url, "executed": len(session.executed_action_ids), "proposed": len(session.proposals_seen)},
        )

    # ============================================================ observe
    async def _observe(self) -> None:
        session = self.session
        session.agent_status = AgentStatus.OBSERVING
        await session.emit(EventType.AGENT_STATUS, {"status": AgentStatus.OBSERVING.value})

        obs = await self.browser.observe(session.id)
        host = normalize_host(obs.get("host"))
        page_trust = page_trust_for_host(host or session.host, self.settings)
        raw_text = obs.get("text") or ""

        instruction_hits = detect_instructions(raw_text)
        sanitized_text, _ = session.registry.redact(raw_text, source=f"page:{host}")

        observed_refs: list[dict[str, Any]] = []
        elements: list[ElementSummary] = []
        for el in obs.get("elements", []):
            value = (el.get("value") or "").strip()
            if value:
                cls = classify_field(el.get("name") or "", el.get("type"), value)
                if cls != DataClass.PUBLIC and cls not in {DataClass.PERSONAL}:
                    ph = session.registry.add(value, cls, f"page:{host}", hint=el.get("label") or "")
                    observed_refs.append({"ph": ph, "data_class": cls.value, "source": f"page:{host}"})
            label, _ = session.registry.redact(el.get("label") or "", source=f"page:{host}:label")
            if el.get("ref"):
                elements.append(
                    ElementSummary(
                        ref=el.get("ref") or "",
                        label=(label or "").strip()[:60],
                        role=el.get("role") or "",
                        tag=el.get("tag") or "",
                        type=el.get("type") or "",
                        form_ref=el.get("form_ref") or "",
                    )
                )

        forms: list[FormSummary] = []
        for form in obs.get("forms", []):
            action_url = (form.get("action") or "").strip()
            if not action_url:
                action_url = obs.get("url") or ""
            resolved = urljoin(obs.get("url") or "", action_url)
            action_host = normalize_host(urlparse(resolved).hostname)
            dest_cls, _dest_trust = classify_destination(action_host, host, self.settings)
            fields = []
            submit_refs: list[str] = []
            for fld in form.get("fields", []):
                value = (fld.get("value") or "").strip()
                ph = ""
                if value:
                    cls = classify_field(fld.get("name") or "", fld.get("type"), value)
                    if cls != DataClass.PUBLIC:
                        ph = session.registry.add(value, cls, f"page:{host}:value", hint=fld.get("label") or "")
                val_display, _ = session.registry.redact(value, source=f"page:{host}:value")
                label, _ = session.registry.redact(fld.get("label") or "", source=f"page:{host}:label")
                fields.append(
                    {
                        "ref": fld.get("ref") or "",
                        "name": fld.get("name") or "",
                        "type": fld.get("type") or "text",
                        "label": (label or "").strip()[:50],
                        "value": ("••••" if fld.get("type") in {"password", "secret"} else val_display) if value else "",
                        "ph": ph,
                    }
                )
            forms.append(
                FormSummary(
                    ref=form.get("ref") or "",
                    action_url=resolved,
                    action_host=action_host,
                    external=dest_cls.value in {"EXTERNAL", "TRUSTED_VENDOR", "UNKNOWN"},
                    fields=[FieldSummary(**f) for f in fields],  # type: ignore[arg-type]
                )
            )

        instructions = []
        for inst in instruction_hits[:4]:
            clean, _ = session.registry.redact(inst.text, source=f"page:{host}:instruction")
            instructions.append({"text": clean[:220], "kind": inst.kind, "trusted": False})

        session.current_url = obs.get("url") or session.current_url
        session.host = host or session.host
        session.title = (obs.get("title") or "").strip()[:200] or session.title
        session.page_trust = page_trust
        session.browser_status = BrowserStatus.LOADED

        page_class = "malicious" if instructions else ("sensitive" if observed_refs else "ordinary")
        session.page_class = page_class

        await session.emit(
            EventType.PAGE_OBSERVED,
            {
                "url": session.current_url,
                "host": session.host,
                "title": session.title,
                "page_class": page_class,
                "trust": page_trust.value,
                "elements": len(elements),
                "forms": len(forms),
            },
        )
        await session.emit(EventType.CONTENT_CLASSIFIED, {"page_class": page_class, "trust": page_trust.value})
        if observed_refs:
            await session.emit(EventType.DATA_DETECTED, {"entries": observed_refs})
        await session.emit(EventType.DATA_REDACTED, {"count": len(observed_refs)})

        self._ctx = AgentContext(
            url=session.current_url,
            host=session.host,
            title=session.title,
            page_trust=page_trust,
            page_class=page_class,
            task=session.task,
            elements=elements,
            forms=forms,
            instructions=instructions,
            data_summary=[s.__dict__ for s in session.registry.summary()],
            memory=[s.__dict__ for s in session.registry.summary()],
        )

        await self.browser.stream_screenshot(session.id)

    # ============================================================ plan
    async def _plan(self):
        session = self.session
        session.agent_status = AgentStatus.PLANNING
        await session.emit(EventType.AGENT_STATUS, {"status": AgentStatus.PLANNING.value, "planner": self.planner.provider_name})
        await session.emit(EventType.AGENT_PLANNING, {"provider": self.planner.provider_name})
        ctx = self._ctx
        assert ctx is not None
        plan = await self.planner.propose(ctx, session)
        if plan.narrative:
            session.narrative = plan.narrative
        return plan

    async def _emit_planner_context(self) -> None:
        session = self.session
        assert self._ctx is not None
        dump = self._ctx.model_dump(mode="json")
        transcript = {"ts": time.time(), "task": session.task, "sanitized_context": dump}
        session.planner_transcripts.append(transcript)
        await session.emit(
            EventType.PLANNER_CONTEXT,
            {"provider": self.planner.provider_name, "task": session.task, "sanitized": dump},
        )

    # ============================================================ propose / decide
    async def _handle_proposal(self, proposal: ActionProposal) -> bool:
        session = self.session
        session.agent_status = AgentStatus.PROPOSING
        await session.emit(EventType.AGENT_STATUS, {"status": AgentStatus.PROPOSING.value})

        ok, errors = validate_action_shape(proposal)
        if not ok:
            return await self._block_invalid(proposal, errors)

        if proposal.action_id in session.executed_action_ids:
            return await self._block_duplicate(proposal)

        session.proposals_seen.append(proposal.action_id)
        self._step += 1

        ctx = self._ctx
        assert ctx is not None
        dest_host = self._derive_destination(proposal, ctx)
        dest_cls, dest_trust = classify_destination(dest_host, session.host, self.settings)
        proposal.destination = dest_host
        proposal.destination_class = dest_cls

        data_refs = self._data_refs(proposal, ctx)
        page_info = PageInfo(url=session.current_url, host=session.host, title=session.title, trust=session.page_trust, ob_class=session.page_class)
        inst_refs = [InstructionRef(text=i["text"], kind=i["kind"], trusted=i["trusted"]) for i in ctx.instructions]
        dest_info = DestInfo(host=dest_host, cls=dest_cls, trust=dest_trust)

        chain = self.provenance.build(
            action_id=proposal.action_id,
            action_label=proposal.action.label,
            page=page_info,
            data_refs=data_refs,
            destination=dest_info,
            instructions=inst_refs,
        )

        induced = any(not i.trusted for i in inst_refs)
        has_transfer = proposal.action.action_type in _TRANSFER_ACTIONS
        pctx = PolicyContext(
            action_type=proposal.action.action_type,
            action_label=proposal.action.label,
            destination=dest_cls,
            destination_host=dest_host or session.host,
            page_trust=session.page_trust,
            data=data_refs,
            induced=induced,
            has_transfer=has_transfer,
        )
        decision = self.policy.evaluate(pctx)

        session.current_proposal = proposal
        session.current_decision = decision
        session.current_chain = chain

        await session.emit(
            EventType.ACTION_PROPOSED,
            {
                "action_id": proposal.action_id,
                "action": proposal.action.model_dump(),
                "proposed_by": proposal.proposed_by,
                "destination": dest_host or session.host,
                "destination_class": dest_cls.value,
                "data": [d.ph for d in data_refs],
            },
            ref=proposal.action_id,
        )
        await session.emit(
            EventType.PROVENANCE_CREATED,
            {"chain_id": chain.chain_id, "nodes": [n.model_dump() for n in chain.nodes]},
            ref=chain.chain_id,
        )
        await session.emit(
            EventType.POLICY_EVALUATED,
            representation(decision),
            ref=proposal.action_id,
        )

        session.agent_status = AgentStatus.WAITING_FOR_AUTHORIZATION
        await session.emit(EventType.AGENT_STATUS, {"status": AgentStatus.WAITING_FOR_AUTHORIZATION.value})

        if decision.verdict == Verdict.BLOCK:
            await self._block(proposal, decision, chain, data_refs, induced)
            return True

        if decision.verdict == Verdict.APPROVAL:
            granted = await self._request_approval(proposal, decision, chain)
            if not granted:
                return True
            purpose = "APPROVED"
        else:
            purpose = "ALLOW"

        return not await self._execute(proposal, purpose)

    def _derive_destination(self, proposal: ActionProposal, ctx: AgentContext) -> str:
        sel = proposal.action.selector if hasattr(proposal.action, "selector") else ""
        if proposal.action.action_type == ActionType.NAVIGATE:
            return normalize_host(urlparse(proposal.action.url).hostname)
        for form in ctx.forms:
            if (form.ref and sel and form.ref == sel) or any(fld.ref == sel for fld in form.fields):
                return form.action_host or ctx.host
        return ctx.host

    def _data_refs(self, proposal: ActionProposal, ctx: AgentContext) -> list[DataRef]:
        by_ph = {s["ph"]: s for s in ctx.memory}
        refs: list[DataRef] = []

        if proposal.action.action_type == ActionType.FILL:
            ph = getattr(proposal.action, "placeholder_ref", None)
            if ph and ph in by_ph:
                refs.append(self._data_ref(by_ph[ph]))
            return refs

        if proposal.action.action_type == ActionType.SUBMIT:
            sel = proposal.action.selector
            form = next(
                (f for f in ctx.forms if (f.ref and f.ref == sel) or sel in {x.ref for x in f.fields}),
                None,
            )
            if form is None and sel:
                elem = next((e for e in ctx.elements if e.ref == sel), None)
                if elem and elem.form_ref:
                    form = next((f for f in ctx.forms if f.ref == elem.form_ref), None)
            if form:
                for fld in form.fields:
                    if fld.ph and fld.ph in by_ph:
                        refs.append(self._data_ref(by_ph[fld.ph]))
            return refs

        if proposal.action.action_type == ActionType.FILL and proposal.action.value:
            pass
        return refs

    def _data_ref(self, mem: dict[str, Any]) -> DataRef:
        source = mem.get("source", "")
        origin_host = ""
        trust = TrustLevel.TRUSTED
        if source.startswith("page:"):
            origin_host = source.split(":", 1)[1]
            trust = page_trust_for_host(origin_host, self.settings)
        elif source:
            trust = TrustLevel.TRUSTED
        return DataRef(ph=mem.get("ph", ""), data_class=DataClass(mem["data_class"]), origin_host=origin_host or "user.vault", origin_trust=trust)

    # ============================================================ execute
    async def _execute(self, proposal: ActionProposal, purpose: str) -> bool:
        session = self.session
        session.agent_status = AgentStatus.EXECUTING
        await session.emit(EventType.AGENT_STATUS, {"status": AgentStatus.EXECUTING.value})

        auth = session.issue_authorization(proposal, purpose)
        executor = Executor(self.browser, session.registry)
        try:
            result = await executor.execute(session.id, proposal, auth, consume_cb=session.consume_authorization)
        except Exception as exc:
            result = ExecutionResult(ok=False, error_code="UNKNOWN", note=str(exc)[:200])
            if "browser has been closed" in str(exc) or "context has been closed" in str(exc):
                result = ExecutionResult(ok=False, error_code="LOST_BROWSER", note="Browser disconnected during execution")

        if result.ok:
            session.executed_action_ids.append(proposal.action_id)
            if proposal.action.action_type == ActionType.SUBMIT:
                session.agent_flags["submitted"] = True
            session.narrative = result.note
            await session.emit(
                EventType.ACTION_EXECUTED,
                {"action_id": proposal.action_id, "action": proposal.action.action_type.value, "note": result.note, "url": result.url or session.current_url},
                ref=proposal.action_id,
            )
            await self.browser.stream_screenshot(session.id)
            return True

        session.agent_status = AgentStatus.FAILED
        session.last_error = {
            "title": "ACTION FAILED",
            "detail": result.note,
            "error_code": result.error_code,
            "action": proposal.action.action_type.value,
            "suggested": result.suggested,
        }
        await session.emit(
            EventType.ACTION_FAILED,
            {"action_id": proposal.action_id, "error_code": result.error_code, "note": result.note, "suggested": result.suggested},
            ref=proposal.action_id,
        )
        if result.error_code == "LOST_BROWSER":
            session.browser_status = BrowserStatus.DISCONNECTED
            await session.emit(EventType.BROWSER_ERROR, {"message": "Browser disconnected."})
        return False

    async def _request_approval(self, proposal: ActionProposal, decision, chain) -> bool:
        session = self.session
        session.approval_event.clear()
        session.approval_result = None
        expiry = time.time() + self.settings.approval_ttl_seconds
        from ..models.approval import PendingApproval

        session.pending_approval = PendingApproval(
            action_id=proposal.action_id,
            generation=proposal.generation,
            expiry=expiry,
            proposal=proposal.model_dump(),
            decision=decision.to_ui(),
            provenance=[n.model_dump() for n in chain.nodes],
        )
        session.agent_status = AgentStatus.WAITING_FOR_APPROVAL
        await session.emit(EventType.AGENT_STATUS, {"status": AgentStatus.WAITING_FOR_APPROVAL.value})
        await session.emit(
            EventType.APPROVAL_REQUIRED,
            {
                "action_id": proposal.action_id,
                "action": proposal.action.label,
                "action_type": proposal.action.action_type.value,
                "destination": proposal.destination or session.host,
                "expiry": expiry,
                "expires_in": self.settings.approval_ttl_seconds,
            },
            ref=proposal.action_id,
        )
        try:
            await asyncio.wait_for(session.approval_event.wait(), timeout=self.settings.approval_ttl_seconds)
        except asyncio.TimeoutError:
            session.pending_approval = None
            session.agent_status = AgentStatus.STOPPED
            session.narrative = "Approval request expired. No action was executed."
            await session.emit(EventType.APPROVAL_EXPIRED, {"action_id": proposal.action_id}, ref=proposal.action_id)
            return False

        if session.approval_result is False:
            session.agent_status = AgentStatus.STOPPED
            session.narrative = "The human denied the action. The browser did not execute it."
            return False

        session.narrative = "Action authorized by the human. Executing once."
        return True

    # ============================================================ blocks
    async def _block_invalid(self, proposal: ActionProposal, errors: list[str]) -> bool:
        session = self.session
        session.agent_status = AgentStatus.BLOCKED
        story = {
            "what_page_tried": "No page instruction involved.",
            "what_agent_proposed": f"{proposal.action.action_type.value} {proposal.action.label or ''}",
            "data_involved": [],
            "where_going": "UNKNOWN",
            "policy_stopped": ["INVALID_ACTION"],
            "what_happened": "Browser execution prevented.",
            "reason": "; ".join(errors),
        }
        threat = Threat(type="INVALID_ACTION", title="Agent proposed an invalid action", detail=story["reason"], severity="CRITICAL", story=story, action_id=proposal.action_id)
        session.record_threat(threat)
        await session.emit(EventType.THREAT_DETECTED, {"threat": threat.model_dump()}, ref=proposal.action_id)
        await session.emit(EventType.ACTION_BLOCKED, {"action_id": proposal.action_id, "reason": story["reason"]}, ref=proposal.action_id)
        await session.emit(EventType.EXECUTION_PREVENTED, {"action_id": proposal.action_id, "statement": "Browser execution prevented."}, ref=proposal.action_id)
        session.narrative = "Sentinel blocked the proposed action."
        return True

    async def _block_duplicate(self, proposal: ActionProposal) -> bool:
        session = self.session
        session.agent_status = AgentStatus.BLOCKED
        session.narrative = "Duplicate action rejected: this action already executed once."
        await session.emit(EventType.ACTION_BLOCKED, {"action_id": proposal.action_id, "reason": "Duplicate execution prevented."}, ref=proposal.action_id)
        return True

    async def _block(self, proposal: ActionProposal, decision, chain, data_refs: list[DataRef], induced: bool) -> None:
        session = self.session
        session.agent_status = AgentStatus.BLOCKED

        story = self._attack_story(proposal, decision, data_refs, induced)
        threat_types = []
        if induced:
            threat_types.append(("INDIRECT_PROMPT_INJECTION", "The page tried to override the user's task", "An untrusted instruction inside the page attempted to redirect the agent."))
        if any(d.data_class in {DataClass.SECRET, DataClass.CANARY, DataClass.CREDENTIAL, DataClass.CARD} for d in data_refs):
            threat_types.append(("SENSITIVE_DATA_FLOW", "Sensitive data would be transferred", "Secret-class data was about to move through this action."))
        if proposal.destination_class and proposal.destination_class.value in {"EXTERNAL", "TRUSTED_VENDOR", "UNKNOWN"}:
            threat_types.append(("UNTRUSTED_DESTINATION", f"Action would reach {proposal.destination}", "The destination lies outside the trusted boundary."))
        for ttype, title, detail in threat_types:
            threat = Threat(type=ttype, title=title, detail=detail, severity="CRITICAL", story=story, action_id=proposal.action_id)
            session.record_threat(threat)
            await session.emit(EventType.THREAT_DETECTED, {"threat": threat.model_dump()}, ref=proposal.action_id)

        await session.emit(
            EventType.ACTION_BLOCKED,
            {
                "action_id": proposal.action_id,
                "action": proposal.action.action_type.value,
                "policy_ids": decision.policy_ids,
                "reasons": decision.reasons,
                "destination": proposal.destination or session.host,
                "data": [d.ph for d in data_refs],
            },
            ref=proposal.action_id,
        )
        await session.emit(
            EventType.EXECUTION_PREVENTED,
            {"action_id": proposal.action_id, "statement": "Browser execution prevented."},
            ref=proposal.action_id,
        )
        session.narrative = "Sentinel blocked the proposed action. The browser did not execute it."

    def _attack_story(self, proposal: ActionProposal, decision, data_refs: list[DataRef], induced: bool) -> dict[str, Any]:
        ctx = self._ctx
        instruction_text = ""
        if ctx and ctx.instructions:
            instruction_text = ctx.instructions[0]["text"]
        return {
            "what_page_tried": instruction_text or "The page presented instructions that conflicted with the user's task.",
            "what_agent_proposed": f"{proposal.action.action_type.value} — {proposal.action.label}",
            "data_involved": [{"ph": d.ph, "class": d.data_class.value} for d in data_refs],
            "where_going": proposal.destination or "UNKNOWN",
            "policy_stopped": decision.policy_ids,
            "what_happened": "BROWSER EXECUTION PREVENTED",
            "induced": induced,
        }


def representation(evaluation) -> dict[str, Any]:
    return {
        "verdict": evaluation.verdict.value,
        "policy_ids": evaluation.policy_ids,
        "reasons": evaluation.reasons,
        "risk": evaluation.risk,
        "fail_closed": evaluation.fail_closed,
    }