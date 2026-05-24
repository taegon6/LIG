from __future__ import annotations

import random
from typing import Any

from core.event_schema import AttackEventType, CommanderMode, SimulatedEvent
from simulator.event_generator import choose_scenario_for_mode, generate_event
from simulator.scenarios import SAFE_SCENARIOS


class RedAgent:
    """Safe red simulator: it creates local synthetic anomaly events only."""

    def __init__(self, epsilon: float = 0.2, rng: Any | None = None) -> None:
        self.epsilon = max(0.0, min(1.0, epsilon))
        self.rng = rng or random

    def generate(
        self,
        commander_mode: CommanderMode,
        recent_scores: list[dict[str, Any]] | None = None,
        current_sla: float = 100.0,
        scenario_stats: list[dict[str, Any]] | None = None,
    ) -> SimulatedEvent:
        scenario, intensity = self.choose_scenario(commander_mode, current_sla, scenario_stats)
        if current_sla < 90 or commander_mode == "RECOVERY_FIRST":
            intensity = min(intensity, 0.35)
        if recent_scores:
            latest_utility = float(recent_scores[0].get("total_utility", 70.0))
            if latest_utility > 85 and commander_mode != "RECOVERY_FIRST":
                intensity = min(0.95, intensity + 0.1)
        return generate_event(scenario, intensity)

    def choose_scenario(
        self,
        commander_mode: CommanderMode,
        current_sla: float = 100.0,
        scenario_stats: list[dict[str, Any]] | None = None,
    ) -> tuple[AttackEventType, float]:
        if current_sla < 85 or commander_mode == "RECOVERY_FIRST":
            scenario = self.rng.choice(["LOG_NOISE", "TRAFFIC_SPIKE", "AUTH_ANOMALY"])
            return scenario, self.rng.uniform(0.15, 0.35)

        if scenario_stats:
            roll = self.rng.random()
            if roll < self.epsilon:
                return self.rng.choice(SAFE_SCENARIOS), self.rng.uniform(0.25, 0.75)

            ranked = sorted(
                (row for row in scenario_stats if str(row.get("event_type")) in SAFE_SCENARIOS),
                key=self._red_success_rank,
                reverse=True,
            )
            if ranked and int(ranked[0].get("attempts", 0)) > 0:
                scenario = str(ranked[0]["event_type"])
                return scenario, self._intensity_for_mode(commander_mode)

        return choose_scenario_for_mode(commander_mode)

    def _red_success_rank(self, row: dict[str, Any]) -> tuple[float, float, int]:
        attempts = max(1, int(row.get("attempts", 0)))
        red_success_rate = float(row.get("red_success_count", 0)) / attempts
        avg_sla_drop = float(row.get("avg_sla_drop", 0.0))
        attempts_seen = int(row.get("attempts", 0))
        return red_success_rate, avg_sla_drop, attempts_seen

    def _intensity_for_mode(self, commander_mode: CommanderMode) -> float:
        if commander_mode == "DEFENSE_HARDENING":
            return self.rng.uniform(0.75, 0.95)
        if commander_mode == "RED_EXPLORATION":
            return self.rng.uniform(0.35, 0.75)
        return self.rng.uniform(0.45, 0.7)
