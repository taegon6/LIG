from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from adapters.base import BaseCompetitionAdapter
from adapters.competition_stub import CompetitionStubAdapter
from adapters.local_simulator import LocalSimulatorAdapter


def get_adapter(mission_state_provider: Callable[[], dict[str, Any]] | None = None) -> BaseCompetitionAdapter:
    mode = os.getenv("AEGIS_ADAPTER", "local").strip().lower()
    if mode == "competition_stub":
        return CompetitionStubAdapter()
    return LocalSimulatorAdapter(mission_state_provider)
