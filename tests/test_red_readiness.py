from __future__ import annotations

from fastapi.testclient import TestClient

from agents.red_agent import RedAgent
from agents.red_objectives import RED_OBJECTIVES, validate_objectives_safe_only
from mission_service.app import app
from simulator.scenarios import SAFE_SCENARIOS


def test_red_objectives_use_only_safe_events() -> None:
    assert set(RED_OBJECTIVES) == {
        "SLA_DROP",
        "BLUE_MISMATCH",
        "CONFUSION",
        "RECOVERY_PRESSURE",
        "COVERAGE",
    }
    assert validate_objectives_safe_only()
    for objective in RED_OBJECTIVES.values():
        assert set(objective.safe_events) <= set(SAFE_SCENARIOS)


def test_red_agent_plan_contains_strategy_metadata() -> None:
    plan = RedAgent(epsilon=0.0).generate_plan("BALANCED", [], 100.0, [])

    assert plan.event_type in SAFE_SCENARIOS
    assert plan.red_objective in RED_OBJECTIVES
    assert plan.strategy_reason
    assert plan.expected_effect
    assert plan.event.event_type == plan.event_type


def test_selfplay_round_includes_red_strategy_fields() -> None:
    client = TestClient(app)

    response = client.post("/selfplay/round")

    assert response.status_code == 200
    body = response.json()
    assert body["red_objective"] in RED_OBJECTIVES
    assert body["red_strategy_reason"]
    assert body["expected_effect"]
    assert "red_success_score" in body
    assert "red_strategy_stat" in body
    assert body["red_strategy_stat"]["objective"] == body["red_objective"]
    assert body["red_strategy"]["event_type"] in SAFE_SCENARIOS


def test_stats_red_endpoint_reports_objectives_and_memory() -> None:
    client = TestClient(app)

    response = client.get("/stats/red")

    assert response.status_code == 200
    body = response.json()
    assert body["local_only"] is True
    assert body["external_access"] is False
    assert set(body["red_objectives"]) == set(RED_OBJECTIVES)
    assert set(body["safe_event_types"]) == set(SAFE_SCENARIOS)
    assert "scenario_stats" in body
    assert "red_strategy_stats" in body
    assert "total_objective_attempts" in body
    assert "most_effective_objective" in body
    assert "coverage_score" in body
