from __future__ import annotations

import csv
import shutil
from pathlib import Path

from scripts.run_hard_mode import HARD_ROUND_COLUMNS, SAFE_HARD_EVENTS, run_hard_mode


REQUIRED_ROUND_COLUMNS = {
    "round_id",
    "event_type",
    "blue_action",
    "pre_sla",
    "post_event_sla",
    "post_action_sla",
    "rolling_sla_10",
    "rolling_sla_50",
    "recovery_delta",
    "recovery_failed",
    "hard_mode_note",
}


def workspace_tmp(name: str) -> Path:
    root = Path("pytest-cache-files-hard-mode") / name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    return root


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_hard_mode_creates_round_and_summary_reports() -> None:
    workdir = workspace_tmp("creates_reports")
    reports_dir = workdir / "reports"

    summary = run_hard_mode(rounds=12, seed=42, reports_dir=reports_dir, db_path=workdir / "hard_mode.db")

    assert Path(summary["round_metrics"]).exists()
    assert Path(summary["summary"]).exists()


def test_hard_mode_round_metrics_include_required_columns() -> None:
    workdir = workspace_tmp("required_columns")
    reports_dir = workdir / "reports"

    run_hard_mode(rounds=12, seed=42, reports_dir=reports_dir, db_path=workdir / "hard_mode.db")
    rows = read_csv(reports_dir / "hard_mode_round_metrics.csv")

    assert list(rows[0].keys()) == HARD_ROUND_COLUMNS
    assert REQUIRED_ROUND_COLUMNS <= set(rows[0])


def test_hard_mode_has_at_least_one_non_perfect_condition() -> None:
    workdir = workspace_tmp("non_perfect")
    reports_dir = workdir / "reports"

    run_hard_mode(rounds=20, seed=42, reports_dir=reports_dir, db_path=workdir / "hard_mode.db")
    rows = read_csv(reports_dir / "hard_mode_round_metrics.csv")

    assert any(
        float(row["post_action_sla"]) < 100.0
        or float(row["rolling_sla_10"]) < 100.0
        or row["recovery_failed"] == "True"
        or float(row["red_success_score"]) > 0.0
        for row in rows
    )


def test_hard_mode_uses_only_safe_event_types() -> None:
    workdir = workspace_tmp("safe_events")
    reports_dir = workdir / "reports"

    run_hard_mode(rounds=20, seed=42, reports_dir=reports_dir, db_path=workdir / "hard_mode.db")
    rows = read_csv(reports_dir / "hard_mode_round_metrics.csv")

    assert all(row["event_type"] in SAFE_HARD_EVENTS for row in rows)


def test_hard_mode_notes_local_simulation_only() -> None:
    workdir = workspace_tmp("local_notes")
    reports_dir = workdir / "reports"

    run_hard_mode(rounds=12, seed=42, reports_dir=reports_dir, db_path=workdir / "hard_mode.db")
    rows = read_csv(reports_dir / "hard_mode_round_metrics.csv")

    assert all("local pressure=" in row["hard_mode_note"] for row in rows)
