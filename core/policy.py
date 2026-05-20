from __future__ import annotations

from collections import Counter
from typing import Any

from core.event_schema import ActionType, RiskLevel


def risk_level_for_score(risk_score: float) -> RiskLevel:
    if risk_score < 0.3:
        return "LOW"
    if risk_score < 0.6:
        return "MEDIUM"
    if risk_score < 0.8:
        return "HIGH"
    return "CRITICAL"


def dominant_event_type(events: list[dict[str, Any]]) -> str:
    relevant = [
        str(event.get("event_type", "NORMAL"))
        for event in events
        if str(event.get("event_type", "NORMAL")) not in {"NORMAL", "LOG_NOISE"}
    ]
    if not relevant:
        return "NORMAL"
    return Counter(relevant).most_common(1)[0][0]


def choose_action(risk_score: float, sla_score: float, events: list[dict[str, Any]]) -> tuple[ActionType, str]:
    dominant = dominant_event_type(events)

    if sla_score < 85:
        if dominant == "SERVICE_DEGRADATION":
            return "RESTART_SERVICE", "SLA is degraded; prioritizing service recovery."
        return "ROLLBACK_VERSION", "SLA is below threshold; prioritizing availability recovery."

    if risk_score < 0.3:
        return "OBSERVE_ONLY", "Risk is low and mission service is stable."

    if risk_score < 0.6 and sla_score >= 95:
        return "APPLY_RATE_LIMIT", "Moderate risk with healthy SLA; rate limiting has low mission impact."

    if risk_score < 0.8 and sla_score >= 90:
        if dominant == "AUTH_ANOMALY":
            return "BLOCK_SUSPICIOUS_TOKEN", "Authentication anomaly is the dominant signal."
        if dominant == "TELEMETRY_INCONSISTENCY":
            return "ISOLATE_TELEMETRY_STREAM", "Telemetry integrity risk is elevated; isolating the stream contains mission impact."
        if dominant == "TRAFFIC_SPIKE":
            return "APPLY_RATE_LIMIT", "Traffic spike detected while SLA is stable."
        return "DEPLOY_DECOY", "Elevated risk without a single blocking signal; deploying decoy for safe observation."

    if risk_score >= 0.8 and sla_score >= 85:
        if dominant == "TELEMETRY_INCONSISTENCY":
            return "ISOLATE_TELEMETRY_STREAM", "Critical telemetry anomaly; isolating the stream protects mission integrity."
        if dominant == "SERVICE_DEGRADATION":
            return "RESTART_SERVICE", "Critical service degradation; simulated restart supports recovery."
        return "ESCALATE_ALERT", "Critical risk requires commander visibility."

    return "OBSERVE_ONLY", "No policy branch required an active response."


def expected_sla_impact(action: ActionType) -> str:
    return {
        "OBSERVE_ONLY": "NONE",
        "APPLY_RATE_LIMIT": "LOW",
        "BLOCK_SUSPICIOUS_TOKEN": "LOW",
        "ISOLATE_TELEMETRY_STREAM": "MEDIUM",
        "RESTART_SERVICE": "MEDIUM",
        "ROLLBACK_VERSION": "MEDIUM",
        "DEPLOY_DECOY": "LOW",
        "ESCALATE_ALERT": "NONE",
    }[action]
