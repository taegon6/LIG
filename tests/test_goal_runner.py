from __future__ import annotations

import json
from pathlib import Path

from scripts import goal_runner
from scripts.goal_runner import CheckResult, check_safety_boundaries, run_goal


def fake_command(command: list[str], timeout: int = 180) -> CheckResult:
    return CheckResult(" ".join(command), True, "fake command passed")


def test_goal_runner_writes_reports(monkeypatch) -> None:
    monkeypatch.setattr(goal_runner, "run_command", fake_command)

    result = run_goal(target_score=92.0, strict=True)

    assert result["passed"] is True
    assert result["total_score"] >= 92.0
    json_path = Path("reports/goal_score.json")
    markdown_path = Path("reports/goal_score.md")
    assert json_path.exists()
    assert markdown_path.exists()
    saved = json.loads(json_path.read_text(encoding="utf-8"))
    assert saved["total_score"] == result["total_score"]
    assert "Attack Scenario Design" in saved["categories"]
    assert "Hard gates passed" in markdown_path.read_text(encoding="utf-8")


def test_private_red_adapter_example_contains_no_disallowed_terms() -> None:
    text = Path("adapters/private_red_adapter.py.example").read_text(encoding="utf-8").lower()

    for term in ["http://", "https://", "token", "endpoint", "payload", "exploit", "scan"]:
        assert term not in text


def test_goal_runner_safety_boundary_check_passes() -> None:
    result, evidence = check_safety_boundaries()

    assert result.passed
    assert evidence["private_adapter_forbidden_hits"] == []
    assert evidence["source_hits"] == []
    assert evidence["default_adapter_local"] is True
