from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentMemory:
    recent_events: list[dict[str, Any]] = field(default_factory=list)
    recent_decisions: list[dict[str, Any]] = field(default_factory=list)
    recent_scores: list[dict[str, Any]] = field(default_factory=list)

    def remember_event(self, event: dict[str, Any]) -> None:
        self.recent_events = [event, *self.recent_events][:100]

    def remember_decision(self, decision: dict[str, Any]) -> None:
        self.recent_decisions = [decision, *self.recent_decisions][:100]

    def remember_score(self, score: dict[str, Any]) -> None:
        self.recent_scores = [score, *self.recent_scores][:100]
