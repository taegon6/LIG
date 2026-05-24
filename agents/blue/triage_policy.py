from __future__ import annotations

from collections import Counter
from typing import Any

from core.event_schema import RiskLevel
from core.policy import risk_level_for_score


COMPONENT_ZERO = {
    "auth_failure_score": 0.0,
    "traffic_spike_score": 0.0,
    "latency_score": 0.0,
    "telemetry_inconsistency_score": 0.0,
    "error_rate_score": 0.0,
}


def dominant_event_type(events: list[dict[str, Any]]) -> str:
    relevant = [
        str(event.get("event_type", "NORMAL"))
        for event in events
        if str(event.get("event_type", "NORMAL")) not in {"NORMAL", "RECOVERY_HEALTH_CHECK"}
    ]
    if not relevant:
        return "NORMAL"
    return Counter(relevant).most_common(1)[0][0]


class TriagePolicy:
    def calculate_component_scores(self, events: list[dict[str, Any]]) -> dict[str, float]:
        if not events:
            return dict(COMPONENT_ZERO)

        auth = 0.0
        traffic = 0.0
        latency = 0.0
        telemetry = 0.0
        errors = 0.0

        for event in events:
            event_type = str(event.get("event_type", "NORMAL"))
            severity = float(event.get("severity", 0.0))
            latency_ms = int(event.get("latency_ms", 0))
            status_code = int(event.get("status_code", 200))
            mission_status = str(event.get("mission_status", "ACTIVE"))
            sla_ok = bool(event.get("sla_ok", True))

            latency = max(latency, max(0.0, (latency_ms - 180) / 520))

            if event_type == "AUTH_ANOMALY":
                auth = max(auth, severity * 2.2)
                errors = max(errors, 0.3 * severity)
            elif event_type == "TRAFFIC_SPIKE":
                traffic = max(traffic, severity * 2.0)
                latency = max(latency, severity * 0.9)
            elif event_type == "TELEMETRY_INCONSISTENCY":
                telemetry = max(telemetry, severity * 3.0)
                latency = max(latency, severity * 0.9)
                errors = max(errors, 0.4 + 0.5 * severity)
            elif event_type == "SERVICE_DEGRADATION":
                latency = max(latency, severity * 1.8)
                errors = max(errors, severity * 1.8)
            elif event_type == "MISSION_COMMAND_ANOMALY":
                auth = max(auth, severity * 0.7)
                telemetry = max(telemetry, severity * 0.8)

            if status_code >= 500:
                errors = max(errors, 1.5)
            if mission_status != "ACTIVE":
                errors = max(errors, 1.2)
            if not sla_ok:
                errors = max(errors, 1.0)

        return {
            "auth_failure_score": min(auth, 3.0),
            "traffic_spike_score": min(traffic, 3.0),
            "latency_score": min(latency, 3.0),
            "telemetry_inconsistency_score": min(telemetry, 3.0),
            "error_rate_score": min(errors, 3.0),
        }

    def risk_score(self, component_scores: dict[str, float]) -> float:
        raw_risk_score = (
            0.3 * component_scores["auth_failure_score"]
            + 0.2 * component_scores["traffic_spike_score"]
            + 0.2 * component_scores["latency_score"]
            + 0.2 * component_scores["telemetry_inconsistency_score"]
            + 0.1 * component_scores["error_rate_score"]
        )
        return round(max(0.0, min(1.0, raw_risk_score)), 3)

    def risk_level(self, risk_score: float) -> RiskLevel:
        return risk_level_for_score(risk_score)
