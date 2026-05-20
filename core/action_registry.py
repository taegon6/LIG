from __future__ import annotations

from typing import Any

from core.event_schema import ActionRecord, BlueDecision, now_iso


ACTION_EFFECTS: dict[str, dict[str, Any]] = {
    "OBSERVE_ONLY": {"latency_delta": 0, "sla_bonus": 0, "note": "Observation only."},
    "APPLY_RATE_LIMIT": {"latency_delta": -40, "sla_bonus": 2, "note": "Future traffic impact is reduced in simulation."},
    "BLOCK_SUSPICIOUS_TOKEN": {"latency_delta": 0, "sla_bonus": 1, "note": "Suspicious simulated token is contained."},
    "ISOLATE_TELEMETRY_STREAM": {"latency_delta": 10, "sla_bonus": 0, "note": "Telemetry anomaly is marked contained."},
    "RESTART_SERVICE": {"latency_delta": -120, "sla_bonus": 5, "note": "Service health is improved by simulated restart."},
    "ROLLBACK_VERSION": {"latency_delta": -90, "sla_bonus": 4, "note": "Latency is improved by simulated rollback."},
    "DEPLOY_DECOY": {"latency_delta": 0, "sla_bonus": 0, "note": "Decoy deployment is logged only."},
    "ESCALATE_ALERT": {"latency_delta": 0, "sla_bonus": 0, "note": "Alert escalation is logged only."},
}


def build_action_record(decision: BlueDecision, agent: str = "blue") -> ActionRecord:
    return ActionRecord(
        timestamp=now_iso(),
        agent=agent,
        action_type=decision.selected_action,
        risk_level=decision.risk_level,
        confidence=decision.confidence,
        reason=decision.reason,
        expected_sla_impact=decision.expected_sla_impact,
    )


def apply_action_to_state(decision: BlueDecision, mission_state: dict[str, Any]) -> dict[str, Any]:
    effect = ACTION_EFFECTS[decision.selected_action]
    state = dict(mission_state)
    state["last_updated"] = now_iso()

    if decision.selected_action in {"RESTART_SERVICE", "ROLLBACK_VERSION"}:
        state["comm_status"] = "NORMAL"
        state["mission_status"] = "ACTIVE"
        state["sla_ok"] = True
    elif decision.selected_action == "ISOLATE_TELEMETRY_STREAM":
        state["comm_status"] = "DEGRADED_BUT_CONTAINED"
    elif decision.selected_action == "APPLY_RATE_LIMIT":
        state["comm_status"] = "RATE_LIMITED"

    return {
        "action_type": decision.selected_action,
        "effect": effect,
        "mission_state": state,
    }
