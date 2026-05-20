from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseCompetitionAdapter(ABC):
    """Stable interface between Aegis-Swarm agents and a runtime environment."""

    adapter_mode: str

    @abstractmethod
    def get_mission_state(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def submit_blue_action(self, action: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_latest_scores(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def adapter_status(self) -> dict[str, Any]:
        raise NotImplementedError
