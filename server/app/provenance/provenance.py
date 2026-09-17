from __future__ import annotations

import time
import uuid
from typing import Any

from pydantic import BaseModel, Field

from ..models.state import DataClass, DestinationClass, TrustLevel, Verdict


class PageInfo(BaseModel):
    url: str = ""
    host: str = ""
    title: str = ""
    trust: TrustLevel = TrustLevel.PARTIAL
    ob_class: str = "UNKNOWN"  # ordinary | sensitive | malicious | untrusted


class DestInfo(BaseModel):
    host: str = ""
    cls: DestinationClass = DestinationClass.UNKNOWN
    trust: TrustLevel = TrustLevel.UNTRUSTED


class DataRef(BaseModel):
    ph: str
    data_class: DataClass
    origin_host: str | None = None
    origin_trust: TrustLevel = TrustLevel.PARTIAL


class InstructionRef(BaseModel):
    text: str  # sanitized text (no raw values)
    kind: str
    trusted: bool = False


class ProvenanceNode(BaseModel):
    node_id: str
    kind: str  # SOURCE | DATA | INSTRUCTION | ACTION | DESTINATION | DECISION
    label: str
    detail: str | None = None
    data_class: DataClass | None = None
    trust: TrustLevel | None = None
    origin: str | None = None
    ts: float = Field(default_factory=time.time)
    action_id: str | None = None


class ProvenanceChain(BaseModel):
    chain_id: str
    action_id: str
    nodes: list[ProvenanceNode] = Field(default_factory=list)

    def to_ui(self) -> dict[str, Any]:
        return {"chain_id": self.chain_id, "action_id": self.action_id, "nodes": [n.model_dump() for n in self.nodes]}


class ProvenanceBuilder:
    def build(
        self,
        *,
        action_id: str,
        action_label: str,
        page: PageInfo,
        data_refs: list[DataRef],
        destination: DestInfo,
        instructions: list[InstructionRef],
        decision: Verdict | None = None,
        policy_ids: list[str] | None = None,
    ) -> ProvenanceChain:
        chain_id = f"chain_{uuid.uuid4().hex[:8]}"
        nodes: list[ProvenanceNode] = []
        ts = time.time()

        nodes.append(
            ProvenanceNode(
                node_id=f"src_{len(nodes)}",
                kind="SOURCE",
                label=(page.host or "PAGE").upper(),
                detail=f"Observed source page · trust {page.trust.value}",
                trust=page.trust,
                origin=page.host,
                ts=ts,
                action_id=action_id,
            )
        )

        for ref in data_refs:
            nodes.append(
                ProvenanceNode(
                    node_id=f"data_{len(nodes)}",
                    kind="DATA",
                    label=ref.data_class.value,
                    detail=f"{ref.ph} · origin {ref.origin_host or page.host}",
                    data_class=ref.data_class,
                    trust=ref.origin_trust,
                    origin=ref.origin_host or page.host,
                    ts=ts,
                    action_id=action_id,
                )
            )

        if instructions:
            for inst in instructions[:3]:
                nodes.append(
                    ProvenanceNode(
                        node_id=f"instr_{len(nodes)}",
                        kind="INSTRUCTION",
                        label="UNTRUSTED INSTRUCTION" if not inst.trusted else "INSTRUCTION",
                        detail=inst.text[:160] if inst.text else "",
                        trust=TrustLevel.UNTRUSTED if not inst.trusted else TrustLevel.TRUSTED,
                        origin=page.host,
                        ts=ts,
                        action_id=action_id,
                    )
                )

        nodes.append(
            ProvenanceNode(
                node_id=f"act_{len(nodes)}",
                kind="ACTION",
                label=action_label or "ACTION",
                trust=TrustLevel.PARTIAL,
                origin=page.host,
                ts=ts,
                action_id=action_id,
            )
        )

        nodes.append(
            ProvenanceNode(
                node_id=f"dst_{len(nodes)}",
                kind="DESTINATION",
                label=(destination.host or "UNKNOWN").upper(),
                detail=f"{destination.cls.value} · trust {destination.trust.value}",
                trust=destination.trust,
                origin=destination.host,
                ts=ts,
                action_id=action_id,
            )
        )

        if decision is not None:
            nodes.append(
                ProvenanceNode(
                    node_id=f"dec_{len(nodes)}",
                    kind="DECISION",
                    label=decision.value,
                    detail=", ".join(policy_ids or []),
                    trust=None,
                    ts=ts,
                    action_id=action_id,
                )
            )

        return ProvenanceChain(chain_id=chain_id, action_id=action_id, nodes=nodes)