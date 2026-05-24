from __future__ import annotations

from typing import Any


PASSIVE_ACTIONS = {"OBSERVE_ONLY"}
ACTIVE_ACTIONS = {
    "APPLY_RATE_LIMIT",
    "BLOCK_SUSPICIOUS_TOKEN",
    "ISOLATE_TELEMETRY_STREAM",
    "RESTART_SERVICE",
    "ROLLBACK_VERSION",
    "DEPLOY_DECOY",
    "ESCALATE_ALERT",
}

ACTION_COSTS = {
    "OBSERVE_ONLY": 0.0,
    "APPLY_RATE_LIMIT": 6.0,
    "BLOCK_SUSPICIOUS_TOKEN": 7.0,
    "ISOLATE_TELEMETRY_STREAM": 10.0,
    "RESTART_SERVICE": 14.0,
    "ROLLBACK_VERSION": 16.0,
    "DEPLOY_DECOY": 8.0,
    "ESCALATE_ALERT": 5.0,
}


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def ideal_actions_for_event(event_type: str) -> set[str]:
    if event_type in {"NORMAL", "LOG_NOISE", "RECOVERY_HEALTH_CHECK"}:
        return {"OBSERVE_ONLY"}
    if event_type == "TRAFFIC_SPIKE":
        return {"APPLY_RATE_LIMIT", "DEPLOY_DECOY", "ESCALATE_ALERT"}
    if event_type == "AUTH_ANOMALY":
        return {"BLOCK_SUSPICIOUS_TOKEN", "DEPLOY_DECOY", "ESCALATE_ALERT"}
    if event_type == "TELEMETRY_INCONSISTENCY":
        return {"ISOLATE_TELEMETRY_STREAM", "ESCALATE_ALERT"}
    if event_type == "SERVICE_DEGRADATION":
        return {"RESTART_SERVICE", "ROLLBACK_VERSION", "ESCALATE_ALERT"}
    if event_type == "MISSION_COMMAND_ANOMALY":
        return {"DEPLOY_DECOY", "ESCALATE_ALERT", "OBSERVE_ONLY"}
    return {"ESCALATE_ALERT"}


def action_matches_event(event: dict[str, Any], decision: dict[str, Any]) -> bool:
    event_type = str(event.get("event_type", "NORMAL"))
    action = str(decision.get("selected_action", "OBSERVE_ONLY"))
    return action in ideal_actions_for_event(event_type)


def calculate_total_utility(
    blue_defense_score: float | None = None,
    red_success_score: float | None = None,
    sla_preservation_score: float | None = None,
    recovery_score: float = 0.0,
    false_positive_penalty: float = 0.0,
    action_cost: float = 0.0,
    *,
    defense_score: float | None = None,
    attack_score: float | None = None,
    sla_score: float | None = None,
) -> float:
    """Weighted utility where Red success and unnecessary action cost reduce value.

    The keyword aliases keep the old public helper usable for existing tests and
    callers while the model moves to v2 score names.
    """

    blue = blue_defense_score if blue_defense_score is not None else float(defense_score or 0.0)
    red = red_success_score if red_success_score is not None else float(attack_score or 0.0)
    sla = sla_preservation_score if sla_preservation_score is not None else float(sla_score or 0.0)

    total = (
        0.35 * blue
        - 0.25 * red
        + 0.25 * sla
        + 0.15 * recovery_score
        - 0.20 * false_positive_penalty
        - 0.10 * action_cost
    )
    return round(clamp(total), 2)


def score_round(
    event: dict[str, Any],
    decision: dict[str, Any],
    sla_score: float,
    previous_sla_score: float | None = None,
    post_event_sla: float | None = None,
    post_action_sla: float | None = None,
) -> dict[str, float]:
    event_type = str(event.get("event_type", "NORMAL"))
    action = str(decision.get("selected_action", "OBSERVE_ONLY"))
    risk_score = float(decision.get("risk_score", 0.0))
    severity = float(event.get("severity", 0.0))

    pre_sla = float(previous_sla_score if previous_sla_score is not None else sla_score)
    event_sla = float(post_event_sla if post_event_sla is not None else sla_score)
    action_sla = float(post_action_sla if post_action_sla is not None else sla_score)
    event_sla_drop = max(0.0, pre_sla - event_sla)
    unrecovered_drop = max(0.0, pre_sla - action_sla)
    recovery_delta = action_sla - event_sla
    sla_preservation_score = round(clamp(100.0 - unrecovered_drop * 4.0), 2)

    matched = action_matches_event(event, decision)
    false_positive_penalty = (
        35.0
        if event_type in {"NORMAL", "LOG_NOISE", "RECOVERY_HEALTH_CHECK"} and action in ACTIVE_ACTIONS
        else 0.0
    )
    action_cost = ACTION_COSTS.get(action, 10.0)
    mission_degraded = str(event.get("mission_status", "ACTIVE")) != "ACTIVE"
    recovery_failed = action_sla < event_sla or action_sla < 85.0

    red_success_score = 0.0
    if not matched:
        red_success_score += 35.0
    if event_sla_drop >= 10.0:
        red_success_score += min(25.0, event_sla_drop * 1.5)
    if mission_degraded:
        red_success_score += 20.0
    if recovery_failed:
        red_success_score += 20.0
    if not matched and severity >= 0.75:
        red_success_score += 10.0
    red_success_score = round(clamp(red_success_score), 2)

    recovery_score = 70.0 + max(-30.0, min(30.0, recovery_delta * 3.0))
    if action_sla >= pre_sla:
        recovery_score += 10.0
    recovery_score = round(clamp(recovery_score), 2)

    blue_defense_score = 35.0
    if matched:
        blue_defense_score += 35.0
    if action_sla >= event_sla:
        blue_defense_score += 15.0
    if action_sla >= 95.0:
        blue_defense_score += 10.0
    if false_positive_penalty == 0.0:
        blue_defense_score += 5.0
    blue_defense_score += min(5.0, risk_score * 5.0)
    blue_defense_score = round(clamp(blue_defense_score - action_cost * 0.25), 2)

    total_utility = calculate_total_utility(
        blue_defense_score=blue_defense_score,
        red_success_score=red_success_score,
        sla_preservation_score=sla_preservation_score,
        recovery_score=recovery_score,
        false_positive_penalty=false_positive_penalty,
        action_cost=action_cost,
    )
    return {
        "red_success_score": red_success_score,
        "blue_defense_score": blue_defense_score,
        "sla_preservation_score": sla_preservation_score,
        "recovery_score": recovery_score,
        "false_positive_penalty": false_positive_penalty,
        "action_cost": action_cost,
        "total_utility": total_utility,
        "attack_score": red_success_score,
        "defense_score": blue_defense_score,
        "sla_score": round(action_sla, 2),
    }
