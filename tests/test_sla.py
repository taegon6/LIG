from __future__ import annotations

from core.sla import calculate_sla


def test_sla_high_for_healthy_events() -> None:
    events = [
        {"status_code": 200, "latency_ms": 120, "mission_status": "ACTIVE", "sla_ok": True},
        {"status_code": 204, "latency_ms": 180, "mission_status": "ACTIVE", "sla_ok": True},
    ]

    assert calculate_sla(events) == 100.0


def test_sla_handles_empty_events() -> None:
    assert calculate_sla([]) == 100.0
