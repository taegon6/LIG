from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from agents.red_objectives import RED_OBJECTIVES, RedObjectiveName, objective_for_event
from core.event_schema import AttackEventType, CommanderMode, SimulatedEvent
from simulator.event_generator import choose_scenario_for_mode, generate_event
from simulator.scenarios import SAFE_SCENARIOS


@dataclass(frozen=True)
class RedStrategyPlan:
    red_objective: RedObjectiveName
    event_type: AttackEventType
    intensity: float
    strategy_reason: str
    expected_effect: str
    event: SimulatedEvent

    def metadata(self) -> dict[str, Any]:
        return {
            "red_objective": self.red_objective,
            "event_type": self.event_type,
            "intensity": self.intensity,
            "strategy_reason": self.strategy_reason,
            "expected_effect": self.expected_effect,
        }


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
        red_strategy_stats: list[dict[str, Any]] | None = None,
    ) -> SimulatedEvent:
        return self.generate_plan(
            commander_mode,
            recent_scores,
            current_sla,
            scenario_stats,
            red_strategy_stats,
        ).event

    def generate_plan(
        self,
        commander_mode: CommanderMode,
        recent_scores: list[dict[str, Any]] | None = None,
        current_sla: float = 100.0,
        scenario_stats: list[dict[str, Any]] | None = None,
        red_strategy_stats: list[dict[str, Any]] | None = None,
    ) -> RedStrategyPlan:
        objective_name = self.choose_objective(
            commander_mode,
            recent_scores,
            current_sla,
            scenario_stats,
            red_strategy_stats,
        )
        scenario, intensity = self.choose_scenario_for_objective(
            objective_name,
            commander_mode,
            current_sla,
            scenario_stats,
            red_strategy_stats,
        )
        if current_sla < 90 or commander_mode == "RECOVERY_FIRST":
            intensity = min(intensity, 0.35)
        if recent_scores:
            latest_utility = float(recent_scores[0].get("total_utility", 70.0))
            if latest_utility > 85 and commander_mode != "RECOVERY_FIRST":
                intensity = min(0.95, intensity + 0.1)
        event = generate_event(scenario, intensity)
        objective = RED_OBJECTIVES[objective_name]
        return RedStrategyPlan(
            red_objective=objective.name,
            event_type=scenario,
            intensity=round(float(event.severity), 2),
            strategy_reason=objective.strategy_reason,
            expected_effect=objective.expected_effect,
            event=event,
        )

    def choose_objective(
        self,
        commander_mode: CommanderMode,
        recent_scores: list[dict[str, Any]] | None = None,
        current_sla: float = 100.0,
        scenario_stats: list[dict[str, Any]] | None = None,
        red_strategy_stats: list[dict[str, Any]] | None = None,
    ) -> RedObjectiveName:
        if commander_mode == "RED_EXPLORATION":
            return "COVERAGE"
        if commander_mode == "DEFENSE_HARDENING":
            return "RECOVERY_PRESSURE"
        if current_sla < 90 or commander_mode == "RECOVERY_FIRST":
            return "RECOVERY_PRESSURE"

        attempted = {str(row.get("event_type")) for row in scenario_stats or [] if int(row.get("attempts", 0)) > 0}
        if len(attempted) < len(SAFE_SCENARIOS):
            return "COVERAGE"

        score_window = recent_scores or []
        if score_window:
            avg_red_success = sum(float(row.get("red_success_score", row.get("attack_score", 0.0))) for row in score_window) / len(score_window)
            avg_blue_defense = sum(float(row.get("blue_defense_score", row.get("defense_score", 0.0))) for row in score_window) / len(score_window)
            avg_sla_score = sum(float(row.get("sla_score", 100.0)) for row in score_window) / len(score_window)
            false_positive_seen = any(float(row.get("false_positive_penalty", 0.0)) > 0.0 for row in score_window)
            if false_positive_seen:
                return "CONFUSION"
            if avg_sla_score < 95 or avg_red_success >= 45:
                return "RECOVERY_PRESSURE"
            if avg_blue_defense >= 90 and avg_red_success < 20:
                return "BLUE_MISMATCH"

        if red_strategy_stats:
            ranked = sorted(
                red_strategy_stats,
                key=lambda row: (
                    float(row.get("avg_red_success_score", 0.0)),
                    float(row.get("avg_sla_drop", 0.0)),
                    float(row.get("avg_total_utility_impact", 0.0)),
                ),
                reverse=True,
            )
            if ranked and int(ranked[0].get("attempts", 0)) > 0:
                return str(ranked[0]["objective"])  # type: ignore[return-value]

        return "SLA_DROP"

    def choose_scenario_for_objective(
        self,
        objective_name: RedObjectiveName,
        commander_mode: CommanderMode,
        current_sla: float = 100.0,
        scenario_stats: list[dict[str, Any]] | None = None,
        red_strategy_stats: list[dict[str, Any]] | None = None,
    ) -> tuple[AttackEventType, float]:
        objective = RED_OBJECTIVES[objective_name]
        if objective_name == "COVERAGE" and scenario_stats:
            attempts_by_event = {
                str(row.get("event_type")): int(row.get("attempts", 0))
                for row in scenario_stats
                if str(row.get("event_type")) in SAFE_SCENARIOS
            }
            least_seen = sorted(SAFE_SCENARIOS, key=lambda event: (attempts_by_event.get(event, 0), event))
            return least_seen[0], self.rng.uniform(0.25, 0.65)

        if red_strategy_stats:
            for row in red_strategy_stats:
                if str(row.get("objective")) == objective_name:
                    event_type = str(row.get("most_effective_event_type") or "")
                    if event_type in objective.safe_events:
                        return event_type, self._intensity_for_mode(commander_mode)

        if scenario_stats:
            ranked = sorted(
                (
                    row for row in scenario_stats
                    if str(row.get("event_type")) in objective.safe_events
                ),
                key=self._red_success_rank,
                reverse=True,
            )
            if ranked and int(ranked[0].get("attempts", 0)) > 0:
                return str(ranked[0]["event_type"]), self._intensity_for_mode(commander_mode)

        return self.rng.choice(objective.safe_events), self._intensity_for_mode(commander_mode)

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

    def _objective_for_choice(
        self,
        scenario: AttackEventType,
        commander_mode: CommanderMode,
        current_sla: float,
        scenario_stats: list[dict[str, Any]] | None,
    ) -> RedObjectiveName:
        if commander_mode == "RED_EXPLORATION":
            return "COVERAGE"
        if commander_mode == "DEFENSE_HARDENING":
            return "RECOVERY_PRESSURE"
        if current_sla < 90 or commander_mode == "RECOVERY_FIRST":
            return "CONFUSION" if scenario == "LOG_NOISE" else "RECOVERY_PRESSURE"
        if scenario_stats:
            attempted = {str(row.get("event_type")) for row in scenario_stats if int(row.get("attempts", 0)) > 0}
            if len(attempted) < len(SAFE_SCENARIOS):
                return "COVERAGE"
        return objective_for_event(scenario)

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
