from __future__ import annotations

import random

from fastapi.testclient import TestClient

from agents.red_agent import RedAgent
from mission_service import db
from mission_service.app import app
from simulator.scenarios import SAFE_SCENARIOS


def test_scenario_stats_updates_after_one_selfplay_round() -> None:
    db.init_db()
    before = db.scenario_stats_summary()["total_attempts"]
    client = TestClient(app)

    response = client.post("/selfplay/round")

    assert response.status_code == 200
    body = response.json()
    after = db.scenario_stats_summary()
    assert after["total_attempts"] == before + 1
    assert body["scenario_stat"]["event_type"] == body["red_event"]["event_type"]
    assert body["scenario_stat"]["attempts"] >= 1


def test_stats_scenarios_endpoint_returns_entropy_and_coverage() -> None:
    client = TestClient(app)

    response = client.get("/stats/scenarios")

    assert response.status_code == 200
    body = response.json()
    assert "scenario_stats" in body
    assert "scenario_entropy" in body
    assert "coverage_score" in body
    assert "total_attempts" in body
    assert 0.0 <= body["scenario_entropy"] <= 100.0
    assert 0.0 <= body["coverage_score"] <= 100.0


def test_red_agent_exploits_high_red_success_scenario() -> None:
    stats = [
        {
            "event_type": "AUTH_ANOMALY",
            "attempts": 10,
            "red_success_count": 9,
            "avg_sla_drop": 12.0,
        },
        {
            "event_type": "TRAFFIC_SPIKE",
            "attempts": 10,
            "red_success_count": 1,
            "avg_sla_drop": 2.0,
        },
    ]
    agent = RedAgent(epsilon=0.0, rng=random.Random(7))

    scenario, intensity = agent.choose_scenario("BALANCED", 100.0, stats)

    assert scenario == "AUTH_ANOMALY"
    assert 0.45 <= intensity <= 0.7


def test_red_agent_can_explore_random_safe_scenarios() -> None:
    stats = [
        {
            "event_type": "AUTH_ANOMALY",
            "attempts": 10,
            "red_success_count": 9,
            "avg_sla_drop": 12.0,
        }
    ]
    agent = RedAgent(epsilon=1.0, rng=random.Random(3))

    scenario, intensity = agent.choose_scenario("BALANCED", 100.0, stats)

    assert scenario in SAFE_SCENARIOS
    assert scenario != "AUTH_ANOMALY"
    assert 0.25 <= intensity <= 0.75
