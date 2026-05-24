from __future__ import annotations

from fastapi.testclient import TestClient

from mission_service.app import app


def test_health_smoke() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "sla_score" in body
    assert body["mission_status"]["mission_id"] == "M-001"


def test_adapter_status_smoke() -> None:
    client = TestClient(app)

    response = client.get("/adapter/status")

    assert response.status_code == 200
    body = response.json()
    assert body["adapter_mode"] == "local"
    assert body["ready"] is True
    assert body["external_access"] is False


def test_selfplay_round_includes_dah_fields() -> None:
    client = TestClient(app)

    response = client.post("/selfplay/round")

    assert response.status_code == 200
    body = response.json()
    assert body["adapter_mode"] == "local"
    assert "dah_scores" in body
    assert "strategy_notes" in body
    assert "attack_score" in body["dah_scores"]
    assert "red_success_score" in body["dah_scores"]
    assert "blue_defense_score" in body["dah_scores"]
    assert "pre_sla" in body
    assert "post_event_sla" in body
    assert "post_action_sla" in body
    assert "sla_delta" in body
    assert "recovery_delta" in body
    assert "recovery_event" in body
    assert body["recovery_event"]["event_type"] == "RECOVERY_HEALTH_CHECK"
    assert "knowledge_mapping" in body
    assert "red_event" in body["knowledge_mapping"]
    assert "blue_action" in body["knowledge_mapping"]
