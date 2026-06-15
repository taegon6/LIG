from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from core.event_schema import AttackEventType
from simulator.scenarios import SAFE_SCENARIOS


RedObjectiveName = Literal[
    "SLA_DROP",
    "BLUE_MISMATCH",
    "CONFUSION",
    "RECOVERY_PRESSURE",
    "COVERAGE",
]


@dataclass(frozen=True)
class RedObjective:
    name: RedObjectiveName
    safe_events: tuple[AttackEventType, ...]
    expected_effect: str
    strategy_reason: str


RED_OBJECTIVES: dict[RedObjectiveName, RedObjective] = {
    "SLA_DROP": RedObjective(
        name="SLA_DROP",
        safe_events=("SERVICE_DEGRADATION", "TRAFFIC_SPIKE", "TELEMETRY_INCONSISTENCY"),
        expected_effect="Attempt to reduce simulated event SLA while remaining local-only.",
        strategy_reason="Prioritize safe events that can stress latency, status, or telemetry health.",
    ),
    "BLUE_MISMATCH": RedObjective(
        name="BLUE_MISMATCH",
        safe_events=("AUTH_ANOMALY", "MISSION_COMMAND_ANOMALY", "TELEMETRY_INCONSISTENCY"),
        expected_effect="Check whether Blue maps the latest safe anomaly to the correct response.",
        strategy_reason="Use event types that require distinct containment, decoy, or isolation actions.",
    ),
    "CONFUSION": RedObjective(
        name="CONFUSION",
        safe_events=("LOG_NOISE", "MISSION_COMMAND_ANOMALY", "AUTH_ANOMALY"),
        expected_effect="Measure whether harmless noise causes unnecessary Blue action.",
        strategy_reason="Mix benign log noise with safe command/auth anomalies to test false positives.",
    ),
    "RECOVERY_PRESSURE": RedObjective(
        name="RECOVERY_PRESSURE",
        safe_events=("SERVICE_DEGRADATION", "TELEMETRY_INCONSISTENCY", "TRAFFIC_SPIKE"),
        expected_effect="Exercise post-action recovery and rolling SLA under repeated local pressure.",
        strategy_reason="Select events that can make recovery incomplete in stress and hard-mode runs.",
    ),
    "COVERAGE": RedObjective(
        name="COVERAGE",
        safe_events=tuple(SAFE_SCENARIOS),  # type: ignore[arg-type]
        expected_effect="Improve scenario coverage across the complete safe event set.",
        strategy_reason="Prefer under-sampled safe scenarios to avoid overfitting the self-play loop.",
    ),
}


def objective_for_event(event_type: str) -> RedObjectiveName:
    if event_type == "SERVICE_DEGRADATION":
        return "SLA_DROP"
    if event_type in {"AUTH_ANOMALY", "MISSION_COMMAND_ANOMALY"}:
        return "BLUE_MISMATCH"
    if event_type == "LOG_NOISE":
        return "CONFUSION"
    if event_type in {"TELEMETRY_INCONSISTENCY", "TRAFFIC_SPIKE"}:
        return "RECOVERY_PRESSURE"
    return "COVERAGE"


def validate_objectives_safe_only() -> bool:
    safe = set(SAFE_SCENARIOS)
    return all(set(objective.safe_events) <= safe for objective in RED_OBJECTIVES.values())
