from __future__ import annotations


EVENT_KNOWLEDGE_MAP = {
    "TRAFFIC_SPIKE": {
        "framework": "ATT&CK-style",
        "tactic": "Impact",
        "technique": "Resource Exhaustion",
    },
    "AUTH_ANOMALY": {
        "framework": "ATT&CK-style",
        "tactic": "Credential Access",
        "technique": "Valid Account Abuse",
    },
    "TELEMETRY_INCONSISTENCY": {
        "framework": "ATT&CK-style",
        "tactic": "Collection",
        "technique": "Data Manipulation",
    },
    "SERVICE_DEGRADATION": {
        "framework": "ATT&CK-style",
        "tactic": "Impact",
        "technique": "Service Stop",
    },
    "MISSION_COMMAND_ANOMALY": {
        "framework": "ATT&CK-style",
        "tactic": "Command and Control",
        "technique": "Unauthorized Command",
    },
    "LOG_NOISE": {
        "framework": "ATT&CK-style",
        "tactic": "Defense Evasion",
        "technique": "Noise Injection",
    },
    "NORMAL": {
        "framework": "ATT&CK-style",
        "tactic": "Benign Activity",
        "technique": "Normal Operation",
    },
    "RECOVERY_HEALTH_CHECK": {
        "framework": "ATT&CK-style",
        "tactic": "Benign Activity",
        "technique": "Recovery Health Check",
    },
}


ACTION_KNOWLEDGE_MAP = {
    "APPLY_RATE_LIMIT": {
        "framework": "D3FEND-style",
        "category": "Network Traffic Filtering",
    },
    "BLOCK_SUSPICIOUS_TOKEN": {
        "framework": "D3FEND-style",
        "category": "Credential or Session Eviction",
    },
    "ISOLATE_TELEMETRY_STREAM": {
        "framework": "D3FEND-style",
        "category": "Isolation / Containment",
    },
    "RESTART_SERVICE": {
        "framework": "D3FEND-style",
        "category": "Restore / Host Reboot",
    },
    "ROLLBACK_VERSION": {
        "framework": "D3FEND-style",
        "category": "Restore Software / Restore Configuration",
    },
    "DEPLOY_DECOY": {
        "framework": "D3FEND-style",
        "category": "Deceive / Decoy Environment",
    },
    "ESCALATE_ALERT": {
        "framework": "D3FEND-style",
        "category": "Human-in-the-loop Response",
    },
    "OBSERVE_ONLY": {
        "framework": "D3FEND-style",
        "category": "Monitoring / Observation",
    },
}


def event_knowledge(event_type: str) -> dict[str, str]:
    return EVENT_KNOWLEDGE_MAP.get(
        event_type,
        {
            "framework": "ATT&CK-style",
            "tactic": "Unknown Simulated Activity",
            "technique": "Unmapped",
        },
    )


def action_knowledge(action_type: str) -> dict[str, str]:
    return ACTION_KNOWLEDGE_MAP.get(
        action_type,
        {
            "framework": "D3FEND-style",
            "category": "Unmapped Defensive Action",
        },
    )


def round_knowledge_mapping(event_type: str, action_type: str) -> dict[str, dict[str, str]]:
    return {
        "red_event": event_knowledge(event_type),
        "blue_action": action_knowledge(action_type),
    }
