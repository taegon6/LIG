from __future__ import annotations

from adapters.competition_stub import CompetitionStubAdapter
from adapters.local_simulator import LocalSimulatorAdapter


def test_local_simulator_adapter_reports_ready_state() -> None:
    adapter = LocalSimulatorAdapter(lambda: {"mission_id": "M-001", "mission_status": "ACTIVE"})

    status = adapter.adapter_status()

    assert status["adapter_mode"] == "local"
    assert status["ready"] is True
    assert status["external_access"] is False
    assert adapter.get_mission_state()["mission_id"] == "M-001"
    assert isinstance(adapter.get_recent_events(5), list)
    assert isinstance(adapter.get_latest_scores(), list)


def test_competition_stub_never_calls_external_systems() -> None:
    adapter = CompetitionStubAdapter()

    status = adapter.adapter_status()
    result = adapter.submit_blue_action({"selected_action": "OBSERVE_ONLY"})

    assert status["adapter_mode"] == "competition_stub"
    assert status["ready"] is False
    assert status["external_access"] is False
    assert result["accepted"] is False
    assert result["external_access"] is False
