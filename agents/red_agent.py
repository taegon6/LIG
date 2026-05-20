from __future__ import annotations

from typing import Any

from core.event_schema import CommanderMode, SimulatedEvent
from simulator.event_generator import choose_scenario_for_mode, generate_event


class RedAgent:
    """Safe red simulator: it creates local synthetic anomaly events only."""

    def generate(
        self,
        commander_mode: CommanderMode,
        recent_scores: list[dict[str, Any]] | None = None,
        current_sla: float = 100.0,
    ) -> SimulatedEvent:
        scenario, intensity = choose_scenario_for_mode(commander_mode)
        if current_sla < 90:
            intensity = min(intensity, 0.35)
        if recent_scores:
            latest_utility = float(recent_scores[0].get("total_utility", 70.0))
            if latest_utility > 85 and commander_mode != "RECOVERY_FIRST":
                intensity = min(0.95, intensity + 0.1)
        return generate_event(scenario, intensity)
