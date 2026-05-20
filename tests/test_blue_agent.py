from __future__ import annotations

from agents.blue_agent import BlueAgent


def test_blue_agent_observe_only_for_low_risk_logs() -> None:
    events = [
        {
            "event_type": "NORMAL",
            "severity": 0.05,
            "latency_ms": 120,
            "status_code": 200,
            "mission_status": "ACTIVE",
            "sla_ok": True,
        }
    ]

    decision = BlueAgent().decide(events, sla_score=100.0)

    assert decision.risk_level == "LOW"
    assert decision.selected_action == "OBSERVE_ONLY"


def test_blue_agent_rate_limits_traffic_spike_with_good_sla() -> None:
    events = [
        {
            "event_type": "TRAFFIC_SPIKE",
            "severity": 0.75,
            "latency_ms": 430,
            "status_code": 200,
            "mission_status": "ACTIVE",
            "sla_ok": True,
        }
    ]

    decision = BlueAgent().decide(events, sla_score=100.0)

    assert decision.risk_level == "MEDIUM"
    assert decision.selected_action == "APPLY_RATE_LIMIT"


def test_blue_agent_isolates_telemetry_inconsistency() -> None:
    events = [
        {
            "event_type": "TELEMETRY_INCONSISTENCY",
            "severity": 0.9,
            "latency_ms": 460,
            "status_code": 200,
            "mission_status": "ACTIVE",
            "sla_ok": True,
        }
    ]

    decision = BlueAgent().decide(events, sla_score=95.0)

    assert decision.risk_level in {"HIGH", "CRITICAL"}
    assert decision.selected_action == "ISOLATE_TELEMETRY_STREAM"
