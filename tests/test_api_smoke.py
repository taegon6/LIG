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
