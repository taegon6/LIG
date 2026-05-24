from __future__ import annotations

import csv
import shutil
from collections import Counter
from pathlib import Path

from scripts.run_balanced_evaluation import BALANCED_ROUND_COLUMNS, BALANCED_SCENARIOS, run_balanced_evaluation


def workspace_tmp(name: str) -> Path:
    root = Path("pytest-cache-files-balanced") / name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    return root


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_balanced_evaluation_creates_both_csv_files() -> None:
    workdir = workspace_tmp("creates_csv_files")
    reports_dir = workdir / "reports"

    summary = run_balanced_evaluation(
        rounds_per_scenario=2,
        seed=42,
        reports_dir=reports_dir,
        db_path=workdir / "balanced.db",
    )

    assert Path(summary["round_metrics"]).exists()
    assert Path(summary["scenario_summary"]).exists()


def test_balanced_round_metrics_include_rolling_sla_columns() -> None:
    workdir = workspace_tmp("rolling_columns")
    reports_dir = workdir / "reports"

    run_balanced_evaluation(
        rounds_per_scenario=1,
        seed=42,
        reports_dir=reports_dir,
        db_path=workdir / "balanced.db",
    )

    assert list(read_csv(reports_dir / "balanced_round_metrics.csv")[0].keys()) == BALANCED_ROUND_COLUMNS


def test_balanced_evaluation_includes_every_safe_scenario() -> None:
    workdir = workspace_tmp("includes_every_scenario")
    reports_dir = workdir / "reports"

    run_balanced_evaluation(
        rounds_per_scenario=2,
        seed=42,
        reports_dir=reports_dir,
        db_path=workdir / "balanced.db",
    )
    rows = read_csv(reports_dir / "balanced_round_metrics.csv")

    assert set(row["event_type"] for row in rows) == set(BALANCED_SCENARIOS)


def test_balanced_evaluation_uses_requested_attempt_count() -> None:
    workdir = workspace_tmp("attempt_count")
    reports_dir = workdir / "reports"

    run_balanced_evaluation(
        rounds_per_scenario=3,
        seed=7,
        reports_dir=reports_dir,
        db_path=workdir / "balanced.db",
    )
    counts = Counter(row["event_type"] for row in read_csv(reports_dir / "balanced_round_metrics.csv"))

    assert counts == {scenario: 3 for scenario in BALANCED_SCENARIOS}


def test_balanced_traffic_spike_accuracy_is_high() -> None:
    workdir = workspace_tmp("traffic_spike_accuracy")
    reports_dir = workdir / "reports"

    run_balanced_evaluation(
        rounds_per_scenario=5,
        seed=42,
        reports_dir=reports_dir,
        db_path=workdir / "balanced.db",
    )
    rows = read_csv(reports_dir / "balanced_scenario_summary.csv")
    traffic_row = next(row for row in rows if row["event_type"] == "TRAFFIC_SPIKE")

    assert float(traffic_row["action_accuracy"]) >= 0.8


def test_balanced_log_noise_false_positive_rate_is_zero() -> None:
    workdir = workspace_tmp("log_noise_false_positive")
    reports_dir = workdir / "reports"

    run_balanced_evaluation(
        rounds_per_scenario=5,
        seed=42,
        reports_dir=reports_dir,
        db_path=workdir / "balanced.db",
    )
    rows = read_csv(reports_dir / "balanced_scenario_summary.csv")
    log_noise_row = next(row for row in rows if row["event_type"] == "LOG_NOISE")

    assert float(log_noise_row["false_positive_rate"]) == 0.0
