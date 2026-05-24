from __future__ import annotations

from typing import Any

from agents.blue.containment_policy import ContainmentPolicy
from agents.blue.deception_policy import DeceptionPolicy
from agents.blue.recovery_policy import RecoveryPolicy
from agents.blue.sla_governor import SLAGovernor
from agents.blue.triage_policy import TriagePolicy, dominant_event_type
from core.event_schema import ActionType, BlueDecision
from core.sla import calculate_sla


class BlueAgent:
    """SLA-aware defender that reasons only over local simulated events."""

    def __init__(self, scenario_stats: list[dict[str, Any]] | None = None) -> None:
        self.scenario_stats = scenario_stats or []
        self.triage = TriagePolicy()
        self.containment = ContainmentPolicy()
        self.recovery = RecoveryPolicy()
        self.deception = DeceptionPolicy()
        self.sla_governor = SLAGovernor()

    def decide(self, events: list[dict[str, Any]], sla_score: float | None = None) -> BlueDecision:
        if sla_score is None:
            sla_score = calculate_sla(events)

        component_scores = self.calculate_component_scores(events)
        risk_score = self.triage.risk_score(component_scores)
        risk_level = self.triage.risk_level(risk_score)
        dominant = dominant_event_type(events)
        action, reason = self.choose_action(dominant, risk_score, sla_score)
        confidence = round(min(0.95, 0.55 + abs(risk_score - 0.5) * 0.55 + len(events) * 0.01), 2)

        return BlueDecision(
            risk_score=risk_score,
            risk_level=risk_level,
            selected_action=action,
            confidence=confidence,
            reason=reason,
            expected_sla_impact=self.sla_governor.expected_sla_impact(action),
            component_scores={name: round(value, 3) for name, value in component_scores.items()},
        )

    def calculate_component_scores(self, events: list[dict[str, Any]]) -> dict[str, float]:
        return self.triage.calculate_component_scores(events)

    def choose_action(self, event_type: str, risk_score: float, sla_score: float) -> tuple[ActionType, str]:
        if self.sla_governor.failed_recently(event_type, self.scenario_stats):
            preferred = self.sla_governor.preferred_failure_actions(event_type)
            if event_type == "SERVICE_DEGRADATION":
                action, reason = self.recovery.action_for(event_type, sla_score)
            elif event_type in {"MISSION_COMMAND_ANOMALY"}:
                action, reason = self.deception.action_for(event_type, max(risk_score, 0.6))
            elif event_type in {"NORMAL", "LOG_NOISE"}:
                action, reason = "OBSERVE_ONLY", "Recent false pressure favors observation to avoid over-response."
            else:
                action, reason = self.containment.action_for(event_type)
                if action is None:
                    action, reason = preferred[0], "Recent Blue failures increased priority for the mapped response."
            if action in preferred:
                return action, f"Recent Blue failures on {event_type} increased priority. {reason}"

        if self.sla_governor.should_recover_first(sla_score):
            return self.recovery.action_for(event_type, sla_score)

        if risk_score < 0.3:
            return "OBSERVE_ONLY", "Risk is low and mission service is stable."

        if event_type == "SERVICE_DEGRADATION" and risk_score >= 0.3:
            return self.recovery.action_for(event_type, sla_score)

        if risk_score < 0.6 and sla_score >= 95:
            if event_type in {"NORMAL", "LOG_NOISE"}:
                return "OBSERVE_ONLY", "Low-impact noise with healthy SLA; observing avoids a false positive."
            if event_type == "MISSION_COMMAND_ANOMALY":
                return self.deception.action_for(event_type, risk_score)
            return "APPLY_RATE_LIMIT", "Moderate risk with healthy SLA; rate limiting has low mission impact."

        if risk_score < 0.8 and sla_score >= 90:
            action, reason = self.containment.action_for(event_type)
            if action is not None:
                return action, reason
            return self.deception.action_for(event_type, risk_score)

        if risk_score >= 0.8 and sla_score >= 85:
            if event_type == "SERVICE_DEGRADATION":
                return self.recovery.action_for(event_type, sla_score)
            action, reason = self.containment.action_for(event_type)
            if action is not None:
                return action, reason
            return self.deception.action_for(event_type, risk_score)

        return "OBSERVE_ONLY", "No policy branch required an active response."
