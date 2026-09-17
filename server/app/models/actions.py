from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, field_validator

from .state import DestinationClass


class ActionType(str, Enum):
    CLICK = "CLICK"
    FILL = "FILL"
    NAVIGATE = "NAVIGATE"
    SUBMIT = "SUBMIT"
    EXTRACT = "EXTRACT"
    WAIT = "WAIT"
    SELECT = "SELECT"
    CHECK = "CHECK"
    UNCHECK = "UNCHECK"
    SCROLL = "SCROLL"
    PRESS = "PRESS"
    BACK = "BACK"


class ActionBase(BaseModel):
    action_type: ActionType
    label: str
    rationale: str = ""
    source_ref: str | None = None

    @field_validator("action_type", mode="after")
    @classmethod
    def _normalize_action_type(cls, v: str | ActionType) -> ActionType:
        return ActionType(v) if isinstance(v, str) else v


class ClickAction(ActionBase):
    action_type: Literal["CLICK"]
    selector: str

    @field_validator("action_type", mode="after")
    @classmethod
    def _normalize_click(cls, v: str | ActionType) -> ActionType:
        return ActionType.CLICK


class FillAction(ActionBase):
    action_type: Literal["FILL"]
    selector: str
    value: str | None = None
    placeholder_ref: str | None = None
    context_label: str | None = None

    @field_validator("action_type", mode="after")
    @classmethod
    def _normalize_fill(cls, v: str | ActionType) -> ActionType:
        return ActionType.FILL

    @field_validator("value", "placeholder_ref")
    @classmethod
    def one_of_value_or_ref(cls, v: str | None, info):  # pragma: no cover - pydantic hint
        return v


class NavigateAction(ActionBase):
    action_type: Literal["NAVIGATE"]
    url: str

    @field_validator("action_type", mode="after")
    @classmethod
    def _normalize_navigate(cls, v: str | ActionType) -> ActionType:
        return ActionType.NAVIGATE


class SubmitAction(ActionBase):
    action_type: Literal["SUBMIT"]
    selector: str
    form_label: str = ""

    @field_validator("action_type", mode="after")
    @classmethod
    def _normalize_submit(cls, v: str | ActionType) -> ActionType:
        return ActionType.SUBMIT


class ExtractAction(ActionBase):
    action_type: Literal["EXTRACT"]
    selector: str
    purpose: str = ""

    @field_validator("action_type", mode="after")
    @classmethod
    def _normalize_extract(cls, v: str | ActionType) -> ActionType:
        return ActionType.EXTRACT


class WaitAction(ActionBase):
    action_type: Literal["WAIT"]
    duration_ms: int = 400

    @field_validator("action_type", mode="after")
    @classmethod
    def _normalize_wait(cls, v: str | ActionType) -> ActionType:
        return ActionType.WAIT


class SelectAction(ActionBase):
    action_type: Literal["SELECT"]
    selector: str
    option: str = ""

    @field_validator("action_type", mode="after")
    @classmethod
    def _normalize_select(cls, v: str | ActionType) -> ActionType:
        return ActionType.SELECT


class CheckAction(ActionBase):
    action_type: Literal["CHECK"]
    selector: str

    @field_validator("action_type", mode="after")
    @classmethod
    def _normalize_check(cls, v: str | ActionType) -> ActionType:
        return ActionType.CHECK


class UncheckAction(ActionBase):
    action_type: Literal["UNCHECK"]
    selector: str

    @field_validator("action_type", mode="after")
    @classmethod
    def _normalize_uncheck(cls, v: str | ActionType) -> ActionType:
        return ActionType.UNCHECK


class ScrollAction(ActionBase):
    action_type: Literal["SCROLL"]
    duration_ms: int = 400

    @field_validator("action_type", mode="after")
    @classmethod
    def _normalize_scroll(cls, v: str | ActionType) -> ActionType:
        return ActionType.SCROLL


class PressAction(ActionBase):
    action_type: Literal["PRESS"]
    key: str

    @field_validator("action_type", mode="after")
    @classmethod
    def _normalize_press(cls, v: str | ActionType) -> ActionType:
        return ActionType.PRESS


class BackAction(ActionBase):
    action_type: Literal["BACK"]

    @field_validator("action_type", mode="after")
    @classmethod
    def _normalize_back(cls, v: str | ActionType) -> ActionType:
        return ActionType.BACK


ActionPayload = Annotated[
    Union[
        ClickAction,
        FillAction,
        NavigateAction,
        SubmitAction,
        ExtractAction,
        WaitAction,
        SelectAction,
        CheckAction,
        UncheckAction,
        ScrollAction,
        PressAction,
        BackAction,
    ],
    Field(discriminator="action_type"),
]

SUPPORTED_ACTION_TYPES = frozenset(ActionType)


class ActionProposal(BaseModel):
    action_id: str
    generation: int
    proposed_by: str
    action: ActionPayload
    destination: str | None = None
    destination_class: DestinationClass | None = None
    confidence: float = 0.0
    plan_done: bool = False
    rationale: str = ""

    def action_name(self) -> str:
        return self.action.action_type.value