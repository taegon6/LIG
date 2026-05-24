from __future__ import annotations

import csv
import shutil
from pathlib import Path

from scripts.run_multi_seed_evaluation import (
    MULTI_SEED_SCENARIO_COLUMNS,
    MULTI_SEED_SUMMARY_COLUMNS,
    run_multi_seed_evaluation,
)


def workspace_tmp(name: str) -> Path:
    root = Path("pytest-cache-files-multiseed") / name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    return root


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_multi_seed_evaluation_creates_reports() -> None:
    workdir = workspace_tmp("creates_reports")
    reports_dir = workdir / "reports"

    summary = run_multi_seed_evaluation(seeds=[1, 2], rounds=5, reports_dir=reports_dir)

    assert Path(summary["summary"]).exists()
    assert Path(summary["scenario_summary"]).exists()


def test_multi_seed_report_columns_and_rolling_metrics() -> None:
    workdir = workspace_tmp("columns")
    reports_dir = workdir / "reports"

    run_multi_seed_evaluation(seeds=[1, 2], rounds=5, reports_dir=reports_dir)
    summary_rows = read_csv(reports_dir / "multi_seed_summary.csv")
    scenario_rows = read_csv(reports_dir / "multi_seed_scenario_summary.csv")

    assert list(summary_rows[0].keys()) == MULTI_SEED_SUMMARY_COLUMNS
    assert list(scenario_rows[0].keys()) == MULTI_SEED_SCENARIO_COLUMNS
    assert {"final_rolling_sla_10", "final_rolling_sla_50", "final_rolling_recovery_delta"} <= {
        row["metric"] for row in summary_rows
    }
