from __future__ import annotations

from agents.blue_agent import BlueAgent
from core.action_registry import apply_action_to_state
from core.scoring import calculate_total_utility, score_round
from core.sla import calculate_sla
from mission_service.app import build_post_action_health_event
from mission_service.models import MissionState


def test_scoring_utility_formula() -> None:
    total = calculate_total_utility(
        blue_defense_score=80,
        red_success_score=20,
        sla_preservation_score=95,
        recovery_score=70,
        false_positive_penalty=10,
        action_cost=5,
    )

    assert total == 54.75


def test_recovery_action_preserves_or_improves_post_action_sla() -> None:
    event = {
        "event_type": "SERVICE_DEGRADATION",
        "severity": 0.9,
        "latency_ms": 720,
        "status_code": 503,
        "mission_status": "DEGRADED",
        "sla_ok": False,
    }
    post_event_sla = calculate_sla([event])
    decision = BlueAgent().decide([event], post_event_sla)
    action_result = apply_action_to_state(decision, MissionState(mission_status="DEGRADED", sla_ok=False).model_dump())
    mission_state = MissionState(**action_result["mission_state"])

    recovery_event = build_post_action_health_event(event, decision, mission_state, action_result)
    post_action_sla = calculate_sla([recovery_event.model_dump(), event])

    assert decision.selected_action in {"RESTART_SERVICE", "ROLLBACK_VERSION"}
    assert post_action_sla >= post_event_sla


def test_high_severity_correct_action_does_not_create_high_red_success() -> None:
    event = {
        "event_type": "TRAFFIC_SPIKE",
        "severity": 0.95,
        "latency_ms": 650,
        "status_code": 200,
        "mission_status": "ACTIVE",
        "sla_ok": False,
    }
    decision = {"selected_action": "APPLY_RATE_LIMIT", "risk_score": 0.9}

    score = score_round(
        event,
        decision,
        sla_score=100.0,
        previous_sla_score=100.0,
        post_event_sla=80.0,
        post_action_sla=100.0,
    )

    assert score["red_success_score"] < 40.0
    assert score["blue_defense_score"] >= 80.0


def test_false_positive_penalty_for_unnecessary_active_defense() -> None:
    event = {
        "event_type": "LOG_NOISE",
        "severity": 0.2,
        "latency_ms": 120,
        "status_code": 200,
        "mission_status": "ACTIVE",
        "sla_ok": True,
    }
    decision = {"selected_action": "RESTART_SERVICE", "risk_score": 0.2}

    score = score_round(
        event,
        decision,
        sla_score=100.0,
        previous_sla_score=100.0,
        post_event_sla=100.0,
        post_action_sla=100.0,
    )

    assert score["false_positive_penalty"] > 0.0
    assert score["action_cost"] > 0.0
    assert score["red_success_score"] > 0.0
