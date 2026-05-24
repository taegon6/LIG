from __future__ import annotations

from core.event_schema import ActionType


class DeceptionPolicy:
    def action_for(self, event_type: str, risk_score: float) -> tuple[ActionType, str]:
        if event_type == "MISSION_COMMAND_ANOMALY":
            if risk_score >= 0.8:
                return "ESCALATE_ALERT", "Mission command anomaly is critical; escalating for commander visibility."
            return "DEPLOY_DECOY", "Mission command anomaly is elevated; deploying a safe decoy for observation."
        if risk_score >= 0.8:
            return "ESCALATE_ALERT", "Critical risk without a safer exact response; escalating alert."
        return "DEPLOY_DECOY", "Elevated risk without a single blocking signal; deploying decoy for safe observation."
