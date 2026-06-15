from __future__ import annotations

from typing import Any

from core.red_action_schema import RedActionPlan, RedActionResult, RedActionType


class MockOfficialRuntime:
    """Local-only stand-in for authorized official runtime behavior."""

    def __init__(self) -> None:
        self._last_plan: RedActionPlan | None = None

    def observe_official_state(self) -> dict[str, Any]:
        return {
            "runtime": "mock_local",
            "external_access": False,
            "mission_status": "ACTIVE",
            "available_feedback": ["red_success_score", "sla_pressure", "coverage"],
        }

    def list_allowed_red_actions(self) -> list[RedActionType]:
        return [
            "OBSERVE_TARGET_STATE",
            "SELECT_ALLOWED_TARGET",
            "SUBMIT_ALLOWED_RED_ACTION",
            "REQUEST_SCORE_FEEDBACK",
            "PRESSURE_SLA_TARGET",
            "CONFUSE_DEFENSE_SIGNAL",
            "COVERAGE_PROBE",
        ]

    def submit_allowed_red_action(self, action: RedActionPlan | dict[str, Any]) -> RedActionResult:
        plan = action if isinstance(action, RedActionPlan) else RedActionPlan(**action)
        self._last_plan = plan
        accepted = plan.allowed_action_type in self.list_allowed_red_actions()
        feedback = self.get_red_feedback()
        return RedActionResult(
            accepted=accepted,
            allowed_action_type=plan.allowed_action_type,
            red_objective=plan.red_objective,
            result_note="Mock runtime accepted a local-only abstract Red action plan.",
            score_feedback=feedback,
        )

    def get_red_feedback(self) -> dict[str, float]:
        if self._last_plan is None:
            return {
                "red_success_score": 0.0,
                "sla_pressure": 0.0,
                "coverage": 0.0,
            }
        score_by_action = {
            "PRESSURE_SLA_TARGET": 35.0,
            "CONFUSE_DEFENSE_SIGNAL": 25.0,
            "COVERAGE_PROBE": 15.0,
            "REQUEST_SCORE_FEEDBACK": 5.0,
            "SELECT_ALLOWED_TARGET": 10.0,
            "OBSERVE_TARGET_STATE": 0.0,
            "SUBMIT_ALLOWED_RED_ACTION": 20.0,
        }
        return {
            "red_success_score": score_by_action[self._last_plan.allowed_action_type],
            "sla_pressure": 20.0 if self._last_plan.allowed_action_type == "PRESSURE_SLA_TARGET" else 0.0,
            "coverage": 20.0 if self._last_plan.allowed_action_type == "COVERAGE_PROBE" else 5.0,
        }
