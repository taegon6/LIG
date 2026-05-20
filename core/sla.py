from __future__ import annotations

from typing import Any


def event_is_sla_healthy(event: dict[str, Any]) -> bool:
    return (
        int(event.get("status_code", 200)) < 500
        and int(event.get("latency_ms", 0)) < 500
        and event.get("mission_status", "ACTIVE") == "ACTIVE"
        and bool(event.get("sla_ok", True))
    )


def calculate_sla(events: list[dict[str, Any]]) -> float:
    if not events:
        return 100.0
    healthy = sum(1 for event in events if event_is_sla_healthy(event))
    return round((healthy / len(events)) * 100.0, 2)
