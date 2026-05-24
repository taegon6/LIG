from __future__ import annotations

from typing import Any

from core.event_schema import ActionType


FAILURE_RESPONSE_CLASS: dict[str, tuple[ActionType, ...]] = {
    "TRAFFIC_SPIKE": ("APPLY_RATE_LIMIT",),
    "AUTH_ANOMALY": ("BLOCK_SUSPICIOUS_TOKEN",),
    "TELEMETRY_INCONSISTENCY": ("ISOLATE_TELEMETRY_STREAM",),
    "SERVICE_DEGRADATION": ("RESTART_SERVICE", "ROLLBACK_VERSION"),
    "MISSION_COMMAND_ANOMALY": ("DEPLOY_DECOY", "ESCALATE_ALERT"),
    "LOG_NOISE": ("OBSERVE_ONLY",),
    "NORMAL": ("OBSERVE_ONLY",),
}


class SLAGovernor:
    def expected_sla_impact(self, action: ActionType) -> str:
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

    def should_recover_first(self, sla_score: float) -> bool:
        return sla_score < 85

    def failed_recently(self, event_type: str, scenario_stats: list[dict[str, Any]]) -> bool:
        for row in scenario_stats:
            if str(row.get("event_type")) != event_type:
                continue
            red_success = int(row.get("red_success_count", 0))
            blue_success = int(row.get("blue_success_count", 0))
            attempts = int(row.get("attempts", 0))
            return attempts > 0 and red_success > blue_success
        return False

    def preferred_failure_actions(self, event_type: str) -> tuple[ActionType, ...]:
        return FAILURE_RESPONSE_CLASS.get(event_type, ("ESCALATE_ALERT",))
