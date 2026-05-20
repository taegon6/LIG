from __future__ import annotations

from typing import Any

from core.event_schema import CommanderMode


class CommanderAgent:
    def decide_mode(
        self,
        sla_score: float,
        recent_scores: list[dict[str, Any]] | None = None,
        recent_actions: list[dict[str, Any]] | None = None,
    ) -> CommanderMode:
        recent_scores = recent_scores or []
        recent_actions = recent_actions or []

        if sla_score < 90:
            return "RECOVERY_FIRST"

        recent_blue_failures = sum(1 for score in recent_scores[:5] if float(score.get("defense_score", 100)) < 60)
        if recent_blue_failures > 2:
            return "DEFENSE_HARDENING"

        if recent_scores:
            red_success_rate = sum(float(score.get("attack_score", 0)) for score in recent_scores[:5]) / (100 * min(5, len(recent_scores)))
            if red_success_rate < 0.3:
                return "RED_EXPLORATION"

        return "BALANCED"
