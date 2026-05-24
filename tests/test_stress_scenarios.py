from __future__ import annotations

import csv
import shutil
from pathlib import Path

from scripts.run_stress_scenarios import STRESS_SEQUENCES, STRESS_SUMMARY_COLUMNS, run_stress_scenarios


def workspace_tmp(name: str) -> Path:
    root = Path("pytest-cache-files-stress") / name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    return root


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_stress_scenarios_create_reports() -> None:
    workdir = workspace_tmp("creates_reports")
    reports_dir = workdir / "reports"

    summary = run_stress_scenarios(seed=42, reports_dir=reports_dir, db_path=workdir / "stress.db")

    assert Path(summary["round_metrics"]).exists()
    assert Path(summary["summary"]).exists()


def test_stress_summary_contains_all_sequences_and_required_columns() -> None:
    workdir = workspace_tmp("summary")
    reports_dir = workdir / "reports"

    run_stress_scenarios(seed=42, reports_dir=reports_dir, db_path=workdir / "stress.db")
    rows = read_csv(reports_dir / "stress_summary.csv")

    assert list(rows[0].keys()) == STRESS_SUMMARY_COLUMNS
    assert {row["sequence_name"] for row in rows} == set(STRESS_SEQUENCES)


def test_stress_rounds_use_existing_safe_events_only() -> None:
    workdir = workspace_tmp("safe_events")
    reports_dir = workdir / "reports"

    run_stress_scenarios(seed=42, reports_dir=reports_dir, db_path=workdir / "stress.db")
    rows = read_csv(reports_dir / "stress_round_metrics.csv")
    safe_events = {event_type for sequence in STRESS_SEQUENCES.values() for event_type, _ in sequence}

    assert all(row["event_type"] in safe_events for row in rows)
    assert len(rows) == sum(len(sequence) for sequence in STRESS_SEQUENCES.values())
