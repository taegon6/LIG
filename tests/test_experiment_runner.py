from __future__ import annotations

import csv
import shutil
from pathlib import Path

from scripts.run_experiments import ROUND_COLUMNS, SCENARIO_COLUMNS, run_experiments


def workspace_tmp(name: str) -> Path:
    root = Path("pytest-cache-files-experiments") / name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    return root


def read_header(path: Path) -> list[str]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        return next(reader)


def test_experiment_runner_creates_reports_directory() -> None:
    workdir = workspace_tmp("creates_reports_directory")
    reports_dir = workdir / "reports"

    run_experiments(rounds=5, seed=42, reports_dir=reports_dir, db_path=workdir / "experiments.db")

    assert reports_dir.exists()
    assert reports_dir.is_dir()


def test_experiment_runner_creates_csv_files() -> None:
    workdir = workspace_tmp("creates_csv_files")
    reports_dir = workdir / "reports"

    summary = run_experiments(rounds=5, seed=42, reports_dir=reports_dir, db_path=workdir / "experiments.db")

    assert Path(summary["round_metrics"]).exists()
    assert Path(summary["scenario_summary"]).exists()


def test_experiment_csv_files_contain_required_columns() -> None:
    workdir = workspace_tmp("required_columns")
    reports_dir = workdir / "reports"

    run_experiments(rounds=5, seed=42, reports_dir=reports_dir, db_path=workdir / "experiments.db")

    assert read_header(reports_dir / "round_metrics.csv") == ROUND_COLUMNS
    assert read_header(reports_dir / "scenario_summary.csv") == SCENARIO_COLUMNS


def test_small_experiment_completes_without_external_access() -> None:
    workdir = workspace_tmp("small_no_external")
    reports_dir = workdir / "reports"

    summary = run_experiments(rounds=5, seed=7, reports_dir=reports_dir, db_path=workdir / "experiments.db")

    assert summary["rounds"] == 5
    assert 0.0 <= summary["average_sla"] <= 100.0
    assert 0.0 <= summary["scenario_entropy"] <= 100.0
    assert 0.0 <= summary["coverage_score"] <= 100.0
