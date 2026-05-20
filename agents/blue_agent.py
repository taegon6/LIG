from __future__ import annotations

from typing import Any

from core.event_schema import BlueDecision
from core.policy import choose_action, expected_sla_impact, risk_level_for_score
from core.sla import calculate_sla


class BlueAgent:
    """SLA-aware defender that reasons only over local simulated events."""

    def decide(self, events: list[dict[str, Any]], sla_score: float | None = None) -> BlueDecision:
        if sla_score is None:
            sla_score = calculate_sla(events)

        component_scores = self.calculate_component_scores(events)
        raw_risk_score = (
            0.3 * component_scores["auth_failure_score"]
            + 0.2 * component_scores["traffic_spike_score"]
            + 0.2 * component_scores["latency_score"]
            + 0.2 * component_scores["telemetry_inconsistency_score"]
            + 0.1 * component_scores["error_rate_score"]
        )
        risk_score = round(max(0.0, min(1.0, raw_risk_score)), 3)
        risk_level = risk_level_for_score(risk_score)
        action, reason = choose_action(risk_score, sla_score, events)
        confidence = round(min(0.95, 0.55 + abs(risk_score - 0.5) * 0.55 + len(events) * 0.01), 2)

        return BlueDecision(
            risk_score=risk_score,
            risk_level=risk_level,
            selected_action=action,
            confidence=confidence,
            reason=reason,
            expected_sla_impact=expected_sla_impact(action),
            component_scores={name: round(value, 3) for name, value in component_scores.items()},
        )

    def calculate_component_scores(self, events: list[dict[str, Any]]) -> dict[str, float]:
        if not events:
            return {
                "auth_failure_score": 0.0,
                "traffic_spike_score": 0.0,
                "latency_score": 0.0,
                "telemetry_inconsistency_score": 0.0,
                "error_rate_score": 0.0,
            }

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
