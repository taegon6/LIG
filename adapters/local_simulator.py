from __future__ import annotations

from collections.abc import Callable
from typing import Any

from adapters.base import BaseCompetitionAdapter
from mission_service import db


class LocalSimulatorAdapter(BaseCompetitionAdapter):
    """Adapter for the bundled SQLite-backed local simulation."""

    adapter_mode = "local"

    def __init__(self, mission_state_provider: Callable[[], dict[str, Any]] | None = None) -> None:
        self._mission_state_provider = mission_state_provider or (lambda: {})

    def get_mission_state(self) -> dict[str, Any]:
        return self._mission_state_provider()

    def get_recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        return db.recent_events(limit)

    def submit_blue_action(self, action: dict[str, Any]) -> dict[str, Any]:
        return {
            "accepted": True,
            "external_access": False,
            "action_type": action.get("action_type") or action.get("selected_action"),
            "description": "Blue action accepted by local simulator adapter.",
        }

    def get_latest_scores(self) -> list[dict[str, Any]]:
        return db.recent_scores(10)

    def adapter_status(self) -> dict[str, Any]:
        return {
            "adapter_mode": self.adapter_mode,
            "ready": True,
            "external_access": False,
            "description": "Local simulator adapter is active.",
        }
