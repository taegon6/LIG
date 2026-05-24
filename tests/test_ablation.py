from __future__ import annotations

import csv
import shutil
from pathlib import Path

from scripts.run_ablation import ABLATION_COLUMNS, ABLATION_VARIANTS, run_ablation


def workspace_tmp(name: str) -> Path:
    root = Path("pytest-cache-files-ablation") / name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    return root


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_ablation_generates_summary_csv() -> None:
    workdir = workspace_tmp("generates_summary")
    reports_dir = workdir / "reports"

    summary = run_ablation(rounds=5, seed=42, reports_dir=reports_dir)

    assert Path(summary["summary"]).exists()


def test_ablation_summary_includes_all_variants() -> None:
    workdir = workspace_tmp("variants")
    reports_dir = workdir / "reports"

    run_ablation(rounds=5, seed=42, reports_dir=reports_dir)
    rows = read_csv(reports_dir / "ablation_summary.csv")

    assert list(rows[0].keys()) == ABLATION_COLUMNS
    assert {row["variant"] for row in rows} == set(ABLATION_VARIANTS)
