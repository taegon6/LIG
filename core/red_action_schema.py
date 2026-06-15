from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from agents.red_objectives import RedObjectiveName
from core.event_schema import now_iso


RedActionType = Literal[
    "OBSERVE_TARGET_STATE",
    "SELECT_ALLOWED_TARGET",
    "SUBMIT_ALLOWED_RED_ACTION",
    "REQUEST_SCORE_FEEDBACK",
    "PRESSURE_SLA_TARGET",
    "CONFUSE_DEFENSE_SIGNAL",
    "COVERAGE_PROBE",
]


class RedActionPlan(BaseModel):
    timestamp: str = Field(default_factory=now_iso)
    red_objective: RedObjectiveName
    allowed_action_type: RedActionType
    strategy_reason: str
    expected_effect: str
    estimated_score_effect: float = Field(default=0.0, ge=-100.0, le=100.0)
    safety_status: str = "SAFE_LOCAL_PLAN_ONLY"


class RedActionResult(BaseModel):
    timestamp: str = Field(default_factory=now_iso)
    accepted: bool
    allowed_action_type: RedActionType
    red_objective: RedObjectiveName
    safety_status: str = "SAFE_LOCAL_MOCK_ONLY"
    external_access: bool = False
    result_note: str
    score_feedback: dict[str, float] = Field(default_factory=dict)
