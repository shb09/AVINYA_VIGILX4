from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, Field

from ..models.actions import ActionType
from ..models.state import (
    DATA_SENSITIVITY,
    DataClass,
    DestinationClass,
    TrustLevel,
    Verdict,
)
from ..provenance.provenance import DataRef


class PolicyContext(BaseModel):
    action_type: ActionType
    action_label: str = ""
    destination: DestinationClass = DestinationClass.UNKNOWN
    destination_host: str | None = None
    page_trust: TrustLevel = TrustLevel.PARTIAL
    data: list[DataRef] = Field(default_factory=list)
    induced: bool = False
    has_transfer: bool = False


class Evaluation(BaseModel):
    verdict: Verdict
    policy_ids: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    risk: str = "UNKNOWN"
    fail_closed: bool = False
    evaluated_at: float = Field(default_factory=time.time)

    def to_ui(self) -> dict[str, Any]:
        return self.model_dump(exclude={"evaluated_at"}) | {"evaluated_at": self.evaluated_at}


class PolicyEngine:
    """Deterministic policy evaluation. Precedence: BLOCK > APPROVAL > ALLOW.
    If nothing explicitly authorizes, the system fails closed (BLOCK)."""

    def evaluate(self, ctx: PolicyContext) -> Evaluation:
        reasons: list[str] = []
        policies: list[str] = []

        data = ctx.data
        sensitivity = max([DATA_SENSITIVITY[d.data_class] for d in data], default=0)
        classes = {d.data_class for d in data}

        block_reasons = self._blocks(ctx, sensitivity, classes)
        for name, reason in block_reasons:
            policies.append(name)
            reasons.append(reason)

        # ------------------------------------------------ BLOCK
        if ctx.destination == DestinationClass.UNKNOWN:
            return self._decide(Verdict.BLOCK, ["UNKNOWN_DESTINATION"] + policies, reasons + ["Destination cannot be established."], risk="CRITICAL", fail_closed=True)

        if policies:
            return self._decide(Verdict.BLOCK, policies, reasons, risk="CRITICAL")

        # ------------------------------------------------ APPROVAL
        approval_rules: list[str] = []
        if ctx.action_type == ActionType.SUBMIT and sensitivity >= DATA_SENSITIVITY[DataClass.PERSONAL] and ctx.destination in {
            DestinationClass.SAME_ORIGIN,
            DestinationClass.INTERNAL,
            DestinationClass.TRUSTED_VENDOR,
        }:
            approval_rules.append("SENSITIVE_SUBMISSION")
        if ctx.action_type in {ActionType.FILL, ActionType.SUBMIT} and sensitivity >= DATA_SENSITIVITY[DataClass.SENSITIVE]:
            approval_rules.append("SENSITIVE_DATA_FLOW")
        if ctx.action_type == ActionType.NAVIGATE and ctx.destination in {
            DestinationClass.EXTERNAL,
            DestinationClass.TRUSTED_VENDOR,
            DestinationClass.UNKNOWN,
        }:
            approval_rules.append("EXTERNAL_NAVIGATION")
        if ctx.has_transfer and sensitivity >= 1 and ctx.destination in {
            DestinationClass.EXTERNAL,
            DestinationClass.TRUSTED_VENDOR,
        }:
            approval_rules.append("CROSS_BOUNDARY_TRANSFER")

        if approval_rules:
            return self._decide(
                Verdict.APPROVAL,
                approval_rules,
                reasons + self._approval_reasons(ctx, sensitivity),
                risk="HIGH" if sensitivity >= 4 else "MEDIUM",
            )

        # ------------------------------------------------ ALLOW
        if ctx.action_type == ActionType.CLICK and ctx.destination in {DestinationClass.SAME_ORIGIN, DestinationClass.INTERNAL} and sensitivity == 0:
            return self._decide(Verdict.ALLOW, ["ORDINARY_CLICK"], reasons + ["Public content within the same origin."], risk="LOW")

        if ctx.action_type in {ActionType.EXTRACT, ActionType.WAIT} and sensitivity <= DATA_SENSITIVITY[DataClass.PERSONAL]:
            return self._decide(Verdict.ALLOW, ["ORDINARY_READ"], reasons + ["Reading public page content."], risk="LOW")

        if ctx.action_type == ActionType.NAVIGATE and ctx.destination in {DestinationClass.SAME_ORIGIN, DestinationClass.INTERNAL}:
            return self._decide(Verdict.ALLOW, ["ORDINARY_NAVIGATE"], reasons + ["Navigation within the trusted application."], risk="LOW")

        if ctx.action_type == ActionType.FILL and ctx.destination in {DestinationClass.SAME_ORIGIN, DestinationClass.INTERNAL} and sensitivity <= DATA_SENSITIVITY[DataClass.EMAIL]:
            return self._decide(Verdict.ALLOW, ["ORDINARY_FILL"], reasons + ["Filling a form field on the trusted page."], risk="LOW")

        if ctx.action_type == ActionType.SUBMIT and ctx.destination in {DestinationClass.SAME_ORIGIN, DestinationClass.INTERNAL} and sensitivity < DATA_SENSITIVITY[DataClass.PERSONAL]:
            return self._decide(Verdict.ALLOW, ["PUBLIC_SUBMIT"], reasons + ["Submitting non-sensitive form data."], risk="LOW")

        # ------------------------------------------------ fail closed
        return self._decide(
            Verdict.BLOCK,
            ["UNVERIFIED_AUTHORIZATION"],
            reasons + ["No policy authorized this action; failing closed."],
            risk="CRITICAL",
            fail_closed=True,
        )

    def _blocks(self, ctx: PolicyContext, sensitivity: int, classes: set[DataClass]) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []

        if ctx.destination == DestinationClass.UNKNOWN:
            return out  # handled separately to mark fail_closed

        if classes & {DataClass.SECRET, DataClass.CANARY, DataClass.CREDENTIAL} and ctx.destination in {
            DestinationClass.EXTERNAL,
            DestinationClass.TRUSTED_VENDOR,
        }:
            out.append(("SECRET_EXTERNAL_TRANSFER", "Secret-class data would leave the trusted boundary."))

        if classes & {DataClass.SECRET, DataClass.CANARY} and ctx.has_transfer:
            out.append(("CLASSIFIED_TRANSFER", "Secret-class data is being moved by this action."))

        if ctx.induced and sensitivity >= DATA_SENSITIVITY[DataClass.SENSITIVE] and (ctx.has_transfer or ctx.destination in {
            DestinationClass.EXTERNAL,
            DestinationClass.TRUSTED_VENDOR,
            DestinationClass.UNKNOWN,
        }):
            out.append(("INDUCED_EXFILTRATION", "Action follows an untrusted instruction and moves sensitive data."))

        if sensitivity >= DATA_SENSITIVITY[DataClass.SENSITIVE] and ctx.destination in {DestinationClass.EXTERNAL, DestinationClass.TRUSTED_VENDOR}:
            out.append(("SENSITIVE_EXTERNAL_FLOW", "Sensitive data would reach an external destination."))

        if ctx.action_type in {ActionType.FILL, ActionType.SUBMIT} and classes & {DataClass.CREDENTIAL, DataClass.CARD} and ctx.destination not in {
            DestinationClass.SAME_ORIGIN,
            DestinationClass.INTERNAL,
        }:
            out.append(("CREDENTIAL_EXFILTRATION", "Credentials would leave the trusted origin."))

        # A page the planner cannot trust may not write data anywhere it requests.
        if ctx.page_trust == TrustLevel.UNTRUSTED and (ctx.has_transfer or ctx.destination != DestinationClass.UNKNOWN) and sensitivity >= 1:
            out.append(("UNTRUSTED_PAGE_FLOW", "An untrusted page is driving a data-moving action."))

        return out

    def _approval_reasons(self, ctx: PolicyContext, sensitivity: int) -> list[str]:
        top = max(ctx.data, key=lambda d: DATA_SENSITIVITY[d.data_class], default=None)
        if top:
            return [f"{top.data_class.value} data ({top.ph}) is involved; a human should confirm."]
        return ["A human should confirm this action."]

    def _decide(self, verdict: Verdict, policies: list[str], reasons: list[str], risk: str, fail_closed: bool = False) -> Evaluation:
        seen: list[str] = []
        unique_policies: list[str] = []
        for p in policies:
            if p not in seen:
                seen.append(p)
                unique_policies.append(p)
        return Evaluation(
            verdict=verdict,
            policy_ids=unique_policies,
            reasons=reasons[:8],
            risk=risk,
            fail_closed=fail_closed,
        )