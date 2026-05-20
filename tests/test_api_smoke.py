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
