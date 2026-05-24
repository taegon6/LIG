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


def test_blue_agent_public_interface_still_works_without_sla() -> None:
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

    decision = BlueAgent().decide(events)

    assert decision.selected_action == "OBSERVE_ONLY"
    assert decision.risk_score >= 0.0


def test_blue_agent_chooses_correct_action_for_main_scenarios() -> None:
    scenarios = [
        ("TRAFFIC_SPIKE", 0.75, 430, 200, "ACTIVE", True, "APPLY_RATE_LIMIT"),
        ("AUTH_ANOMALY", 0.85, 220, 200, "ACTIVE", True, "BLOCK_SUSPICIOUS_TOKEN"),
        ("TELEMETRY_INCONSISTENCY", 0.85, 460, 200, "ACTIVE", True, "ISOLATE_TELEMETRY_STREAM"),
        ("SERVICE_DEGRADATION", 0.9, 700, 503, "DEGRADED", False, "RESTART_SERVICE"),
        ("MISSION_COMMAND_ANOMALY", 0.9, 260, 200, "ACTIVE", True, "DEPLOY_DECOY"),
    ]

    for event_type, severity, latency, status_code, mission_status, sla_ok, expected_action in scenarios:
        decision = BlueAgent().decide(
            [
                {
                    "event_type": event_type,
                    "severity": severity,
                    "latency_ms": latency,
                    "status_code": status_code,
                    "mission_status": mission_status,
                    "sla_ok": sla_ok,
                }
            ],
            sla_score=95.0,
        )
        assert decision.selected_action == expected_action


def test_latest_active_event_wins_over_older_noisy_history() -> None:
    events = [
        {
            "event_type": "TRAFFIC_SPIKE",
            "severity": 0.5,
            "latency_ms": 260,
            "status_code": 200,
            "mission_status": "ACTIVE",
            "sla_ok": True,
        },
        {
            "event_type": "AUTH_ANOMALY",
            "severity": 0.95,
            "latency_ms": 180,
            "status_code": 200,
            "mission_status": "ACTIVE",
            "sla_ok": True,
        },
        {
            "event_type": "LOG_NOISE",
            "severity": 0.2,
            "latency_ms": 120,
            "status_code": 200,
            "mission_status": "ACTIVE",
            "sla_ok": True,
        },
    ]

    decision = BlueAgent().decide(events, sla_score=100.0)

    assert decision.selected_action == "APPLY_RATE_LIMIT"
    assert "traffic spike" in decision.reason.lower()


def test_traffic_spike_severity_half_selects_rate_limit() -> None:
    events = [
        {
            "event_type": "TRAFFIC_SPIKE",
            "severity": 0.5,
            "latency_ms": 210,
            "status_code": 200,
            "mission_status": "ACTIVE",
            "sla_ok": True,
        }
    ]

    decision = BlueAgent().decide(events, sla_score=100.0)

    assert decision.selected_action == "APPLY_RATE_LIMIT"


def test_auth_anomaly_selects_token_block() -> None:
    events = [
        {
            "event_type": "AUTH_ANOMALY",
            "severity": 0.45,
            "latency_ms": 170,
            "status_code": 200,
            "mission_status": "ACTIVE",
            "sla_ok": True,
        }
    ]

    decision = BlueAgent().decide(events, sla_score=100.0)

    assert decision.selected_action == "BLOCK_SUSPICIOUS_TOKEN"


def test_mission_command_anomaly_selects_deception_or_escalation() -> None:
    events = [
        {
            "event_type": "MISSION_COMMAND_ANOMALY",
            "severity": 0.55,
            "latency_ms": 190,
            "status_code": 200,
            "mission_status": "ACTIVE",
            "sla_ok": True,
        }
    ]

    decision = BlueAgent().decide(events, sla_score=100.0)

    assert decision.selected_action in {"DEPLOY_DECOY", "ESCALATE_ALERT"}
    assert decision.selected_action != "RESTART_SERVICE"


def test_log_noise_alone_still_observes() -> None:
    events = [
        {
            "event_type": "LOG_NOISE",
            "severity": 0.4,
            "latency_ms": 130,
            "status_code": 200,
            "mission_status": "ACTIVE",
            "sla_ok": True,
        }
    ]

    decision = BlueAgent().decide(events, sla_score=100.0)

    assert decision.selected_action == "OBSERVE_ONLY"


def test_recovery_health_check_stops_old_event_from_winning() -> None:
    events = [
        {
            "event_type": "LOG_NOISE",
            "severity": 0.4,
            "latency_ms": 130,
            "status_code": 200,
            "mission_status": "ACTIVE",
            "sla_ok": True,
        },
        {
            "event_type": "RECOVERY_HEALTH_CHECK",
            "severity": 0.0,
            "latency_ms": 150,
            "status_code": 200,
            "mission_status": "ACTIVE",
            "sla_ok": True,
        },
        {
            "event_type": "AUTH_ANOMALY",
            "severity": 0.95,
            "latency_ms": 180,
            "status_code": 200,
            "mission_status": "ACTIVE",
            "sla_ok": True,
        },
    ]

    decision = BlueAgent().decide(events, sla_score=100.0)

    assert decision.selected_action == "OBSERVE_ONLY"


def test_recent_failure_awareness_prioritizes_correct_response() -> None:
    scenario_stats = [
        {
            "event_type": "AUTH_ANOMALY",
            "attempts": 4,
            "red_success_count": 3,
            "blue_success_count": 1,
        }
    ]
    events = [
        {
            "event_type": "AUTH_ANOMALY",
            "severity": 0.55,
            "latency_ms": 170,
            "status_code": 200,
            "mission_status": "ACTIVE",
            "sla_ok": True,
        }
    ]

    baseline = BlueAgent().decide(events, sla_score=100.0)
    adapted = BlueAgent(scenario_stats=scenario_stats).decide(events, sla_score=100.0)

    assert baseline.selected_action == "BLOCK_SUSPICIOUS_TOKEN"
    assert adapted.selected_action == "BLOCK_SUSPICIOUS_TOKEN"
