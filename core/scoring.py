from __future__ import annotations

from typing import Any


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def calculate_total_utility(
    defense_score: float,
    attack_score: float,
    sla_score: float,
    recovery_score: float,
    false_positive_penalty: float,
) -> float:
    total = (
        0.35 * defense_score
        + 0.25 * attack_score
        + 0.30 * sla_score
        + 0.10 * recovery_score
        - 0.20 * false_positive_penalty
    )
    return round(total, 2)


def score_round(
    event: dict[str, Any],
    decision: dict[str, Any],
    sla_score: float,
    previous_sla_score: float | None = None,
) -> dict[str, float]:
    severity = float(event.get("severity", 0.0))
    event_type = str(event.get("event_type", "NORMAL"))
    action = str(decision.get("selected_action", "OBSERVE_ONLY"))
    risk_score = float(decision.get("risk_score", 0.0))

    attack_score = round(clamp(severity * 100.0), 2)
    if event_type in {"NORMAL", "LOG_NOISE"}:
        ideal_actions = {"OBSERVE_ONLY"}
    elif event_type == "TRAFFIC_SPIKE":
        ideal_actions = {"APPLY_RATE_LIMIT", "DEPLOY_DECOY", "ESCALATE_ALERT"}
    elif event_type == "AUTH_ANOMALY":
        ideal_actions = {"BLOCK_SUSPICIOUS_TOKEN", "DEPLOY_DECOY", "ESCALATE_ALERT"}
    elif event_type == "TELEMETRY_INCONSISTENCY":
        ideal_actions = {"ISOLATE_TELEMETRY_STREAM", "ESCALATE_ALERT"}
    elif event_type == "SERVICE_DEGRADATION":
        ideal_actions = {"RESTART_SERVICE", "ROLLBACK_VERSION", "ESCALATE_ALERT"}
    else:
        ideal_actions = {"DEPLOY_DECOY", "ESCALATE_ALERT", "OBSERVE_ONLY"}

    defense_score = 85.0 if action in ideal_actions else 45.0
    defense_score += min(15.0, risk_score * 10.0)
    defense_score = round(clamp(defense_score), 2)

    if previous_sla_score is None:
        recovery_score = 75.0 if sla_score >= 95 else sla_score
    else:
        recovery_score = 70.0 + max(-20.0, min(30.0, sla_score - previous_sla_score))
    recovery_score = round(clamp(recovery_score), 2)

    false_positive_penalty = 30.0 if event_type in {"NORMAL", "LOG_NOISE"} and action != "OBSERVE_ONLY" else 0.0
    total_utility = calculate_total_utility(
        defense_score=defense_score,
        attack_score=attack_score,
        sla_score=sla_score,
        recovery_score=recovery_score,
        false_positive_penalty=false_positive_penalty,
    )
    return {
        "attack_score": attack_score,
        "defense_score": defense_score,
        "sla_score": round(sla_score, 2),
        "recovery_score": recovery_score,
        "false_positive_penalty": false_positive_penalty,
        "total_utility": total_utility,
    }
