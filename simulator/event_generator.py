from __future__ import annotations

import random

from core.event_schema import AttackEventType, CommanderMode, SimulatedEvent
from simulator.scenarios import SCENARIO_DESCRIPTIONS, SAFE_SCENARIOS


def generate_event(scenario: AttackEventType, intensity: float = 0.5) -> SimulatedEvent:
    intensity = max(0.0, min(1.0, intensity))
    base_latency = 110 + int(120 * intensity)
    status_code = 200
    mission_status = "ACTIVE"
    sla_ok = True

    if scenario == "TRAFFIC_SPIKE":
        latency_ms = base_latency + int(270 * intensity)
    elif scenario == "AUTH_ANOMALY":
        latency_ms = base_latency + int(80 * intensity)
    elif scenario == "TELEMETRY_INCONSISTENCY":
        latency_ms = base_latency + int(180 * intensity)
        sla_ok = intensity < 0.75
    elif scenario == "SERVICE_DEGRADATION":
        latency_ms = base_latency + int(500 * intensity)
        status_code = 503 if intensity >= 0.65 else 200
        mission_status = "DEGRADED" if intensity >= 0.6 else "ACTIVE"
        sla_ok = intensity < 0.6
    elif scenario == "MISSION_COMMAND_ANOMALY":
        latency_ms = base_latency + int(130 * intensity)
    else:
        latency_ms = base_latency
        intensity = min(intensity, 0.3)

    return SimulatedEvent(
        event_type=scenario,
        severity=round(intensity, 2),
        latency_ms=latency_ms,
        status_code=status_code,
        mission_status=mission_status,
        sla_ok=sla_ok,
        description=SCENARIO_DESCRIPTIONS[scenario],
    )


def choose_scenario_for_mode(mode: CommanderMode) -> tuple[AttackEventType, float]:
    if mode == "RECOVERY_FIRST":
        return random.choice(["LOG_NOISE", "TRAFFIC_SPIKE", "AUTH_ANOMALY"]), random.uniform(0.15, 0.35)
    if mode == "RED_EXPLORATION":
        return random.choice(SAFE_SCENARIOS), random.uniform(0.25, 0.75)
    if mode == "DEFENSE_HARDENING":
        return random.choice(["TELEMETRY_INCONSISTENCY", "SERVICE_DEGRADATION", "AUTH_ANOMALY"]), random.uniform(0.75, 0.95)
    return random.choice(SAFE_SCENARIOS), random.uniform(0.4, 0.65)
