from __future__ import annotations

from core.event_schema import ActionType


class RecoveryPolicy:
    def action_for(self, event_type: str, sla_score: float) -> tuple[ActionType, str]:
        if event_type == "SERVICE_DEGRADATION":
            return "RESTART_SERVICE", "Service degradation is dominant; simulated restart supports recovery."
        if sla_score < 85:
            return "ROLLBACK_VERSION", "SLA is below threshold; prioritizing availability recovery."
        return "RESTART_SERVICE", "Recovery response selected to preserve mission availability."
