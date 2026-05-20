from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


EventType = Literal[
    "NORMAL",
    "TRAFFIC_SPIKE",
    "AUTH_ANOMALY",
    "TELEMETRY_INCONSISTENCY",
    "SERVICE_DEGRADATION",
    "MISSION_COMMAND_ANOMALY",
    "LOG_NOISE",
]

AttackEventType = Literal[
    "TRAFFIC_SPIKE",
    "AUTH_ANOMALY",
    "TELEMETRY_INCONSISTENCY",
    "SERVICE_DEGRADATION",
    "MISSION_COMMAND_ANOMALY",
    "LOG_NOISE",
]

ActionType = Literal[
    "OBSERVE_ONLY",
    "APPLY_RATE_LIMIT",
    "BLOCK_SUSPICIOUS_TOKEN",
    "ISOLATE_TELEMETRY_STREAM",
    "RESTART_SERVICE",
    "ROLLBACK_VERSION",
    "DEPLOY_DECOY",
    "ESCALATE_ALERT",
]

RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
CommanderMode = Literal["BALANCED", "RECOVERY_FIRST", "DEFENSE_HARDENING", "RED_EXPLORATION"]


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


class SimulatedEvent(BaseModel):
    timestamp: str = Field(default_factory=now_iso)
    source: str = "simulator"
    event_type: EventType = "NORMAL"
    severity: float = Field(default=0.0, ge=0.0, le=1.0)
    latency_ms: int = Field(default=120, ge=0)
    status_code: int = Field(default=200, ge=100, le=599)
    mission_status: str = "ACTIVE"
    sla_ok: bool = True
    description: str = "Simulated normal event"


class SimulateEventRequest(BaseModel):
    scenario: AttackEventType
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)


class VehicleCommandRequest(BaseModel):
    command: str = Field(..., min_length=1, max_length=80)
    target_x: float | None = None
    target_y: float | None = None


class BlueDecision(BaseModel):
    risk_score: float
    risk_level: RiskLevel
    selected_action: ActionType
    confidence: float
    reason: str
    expected_sla_impact: str
    component_scores: dict[str, float] = Field(default_factory=dict)


class ActionRecord(BaseModel):
    timestamp: str = Field(default_factory=now_iso)
    agent: str = "blue"
    action_type: ActionType
    risk_level: RiskLevel
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    expected_sla_impact: str
