from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from adapters.mock_official_runtime import MockOfficialRuntime
from agents.red_agent import RedAgent
from core.red_action_schema import RedActionPlan
from mission_service.app import app
from scripts.goal_runner import check_safety_boundaries


def test_red_action_plan_has_no_payload_field() -> None:
    assert "payload" not in RedActionPlan.model_fields
    assert "endpoint" not in RedActionPlan.model_fields
    assert "token" not in RedActionPlan.model_fields


def test_red_agent_plans_official_action_without_execution() -> None:
    plan = RedAgent(epsilon=0.0).plan_official_red_action(
        {
            "commander_mode": "BALANCED",
            "current_sla": 100.0,
            "allowed_actions": ["OBSERVE_TARGET_STATE", "COVERAGE_PROBE"],
        }
    )

    assert plan.allowed_action_type in {"OBSERVE_TARGET_STATE", "COVERAGE_PROBE"}
    assert plan.safety_status == "SAFE_LOCAL_PLAN_ONLY"
    assert plan.strategy_reason
    assert plan.expected_effect


def test_mock_official_runtime_uses_only_local_data() -> None:
    runtime = MockOfficialRuntime()
    state = runtime.observe_official_state()
    plan = RedAgent().plan_official_red_action({"allowed_actions": runtime.list_allowed_red_actions()})
    result = runtime.submit_allowed_red_action(plan)

    assert state["runtime"] == "mock_local"
    assert state["external_access"] is False
    assert result.external_access is False
    assert result.safety_status == "SAFE_LOCAL_MOCK_ONLY"
    assert result.score_feedback


def test_red_plan_endpoint_works() -> None:
    client = TestClient(app)

    response = client.post("/red/plan", json={"commander_mode": "RED_EXPLORATION"})

    assert response.status_code == 200
    body = response.json()
    assert body["red_objective"]
    assert body["allowed_action_type"]
    assert body["strategy_reason"]
    assert body["expected_effect"]
    assert body["safety_status"] == "SAFE_LOCAL_PLAN_ONLY"


def test_red_mock_execute_endpoint_works() -> None:
    client = TestClient(app)

    response = client.post("/red/mock/execute", json={"commander_mode": "DEFENSE_HARDENING"})

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    assert body["external_access"] is False
    assert body["safety_status"] == "SAFE_LOCAL_MOCK_ONLY"
    assert body["score_feedback"]


def test_private_red_adapter_example_has_no_disallowed_runtime_details() -> None:
    text = Path("adapters/private_red_adapter.py.example").read_text(encoding="utf-8").lower()

    for term in ["http://", "https://", "token", "endpoint", "payload", "exploit", "scan"]:
        assert term not in text
    for method_name in [
        "observe_official_state",
        "list_allowed_red_actions",
        "submit_allowed_red_action",
        "get_red_feedback",
        "adapter_status",
    ]:
        assert method_name in text


def test_no_unsafe_external_behavior_is_introduced() -> None:
    result, evidence = check_safety_boundaries()

    assert result.passed
    assert evidence["source_hits"] == []
