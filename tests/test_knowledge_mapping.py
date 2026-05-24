from __future__ import annotations

from core.knowledge_mapping import action_knowledge, event_knowledge


def test_event_knowledge_mapping_returns_labels_for_all_event_types() -> None:
    event_types = [
        "NORMAL",
        "TRAFFIC_SPIKE",
        "AUTH_ANOMALY",
        "TELEMETRY_INCONSISTENCY",
        "SERVICE_DEGRADATION",
        "MISSION_COMMAND_ANOMALY",
        "LOG_NOISE",
        "RECOVERY_HEALTH_CHECK",
    ]

    for event_type in event_types:
        mapping = event_knowledge(event_type)
        assert mapping["framework"] == "ATT&CK-style"
        assert mapping["tactic"]
        assert mapping["technique"]


def test_action_knowledge_mapping_returns_labels_for_all_action_types() -> None:
    action_types = [
        "OBSERVE_ONLY",
        "APPLY_RATE_LIMIT",
        "BLOCK_SUSPICIOUS_TOKEN",
        "ISOLATE_TELEMETRY_STREAM",
        "RESTART_SERVICE",
        "ROLLBACK_VERSION",
        "DEPLOY_DECOY",
        "ESCALATE_ALERT",
    ]

    for action_type in action_types:
        mapping = action_knowledge(action_type)
        assert mapping["framework"] == "D3FEND-style"
        assert mapping["category"]
