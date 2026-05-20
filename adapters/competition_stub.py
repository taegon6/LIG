from __future__ import annotations

from typing import Any

from adapters.base import BaseCompetitionAdapter


class CompetitionStubAdapter(BaseCompetitionAdapter):
    """Placeholder for future DAH runtime APIs. It never calls external systems."""

    adapter_mode = "competition_stub"

    def get_mission_state(self) -> dict[str, Any]:
        return {"configured": False, "mission_status": "UNKNOWN"}

    def get_recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        return []

    def submit_blue_action(self, action: dict[str, Any]) -> dict[str, Any]:
        return {
            "accepted": False,
            "external_access": False,
            "action_type": action.get("action_type") or action.get("selected_action"),
            "description": "Competition adapter is not configured; no external call was made.",
        }

    def get_latest_scores(self) -> list[dict[str, Any]]:
        return []

    def adapter_status(self) -> dict[str, Any]:
        return {
            "adapter_mode": self.adapter_mode,
            "ready": False,
            "external_access": False,
            "description": "Competition API adapter stub is present but not configured.",
        }
