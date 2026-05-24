from __future__ import annotations

from core.event_schema import ActionType


CONTAINMENT_ACTIONS: dict[str, ActionType] = {
    "TRAFFIC_SPIKE": "APPLY_RATE_LIMIT",
    "AUTH_ANOMALY": "BLOCK_SUSPICIOUS_TOKEN",
    "TELEMETRY_INCONSISTENCY": "ISOLATE_TELEMETRY_STREAM",
}


class ContainmentPolicy:
    def action_for(self, event_type: str) -> tuple[ActionType | None, str]:
        action = CONTAINMENT_ACTIONS.get(event_type)
        if action == "APPLY_RATE_LIMIT":
            return action, "Traffic pressure is the dominant signal; applying a local simulated rate limit."
        if action == "BLOCK_SUSPICIOUS_TOKEN":
            return action, "Authentication anomaly is the dominant signal; blocking the simulated suspicious token."
        if action == "ISOLATE_TELEMETRY_STREAM":
            return action, "Telemetry integrity risk is elevated; isolating the stream contains mission impact."
        return None, "No containment action matches this event type."
