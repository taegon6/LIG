from __future__ import annotations

SCENARIO_DESCRIPTIONS = {
    "TRAFFIC_SPIKE": "Simulated traffic spike event",
    "AUTH_ANOMALY": "Simulated authentication anomaly event",
    "TELEMETRY_INCONSISTENCY": "Simulated telemetry inconsistency event",
    "SERVICE_DEGRADATION": "Simulated service degradation event",
    "MISSION_COMMAND_ANOMALY": "Simulated mission command anomaly event",
    "LOG_NOISE": "Simulated benign log noise event",
}

SAFE_SCENARIOS = tuple(SCENARIO_DESCRIPTIONS.keys())
