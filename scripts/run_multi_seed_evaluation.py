from __future__ import annotations

import argparse
import csv
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_experiments import run_experiments


SUMMARY_METRICS = [
    "average_sla",
    "average_sla_drop",
    "average_recovery_delta",
    "average_utility",
    "false_positive_rate",
    "recovery_success_rate",
    "scenario_entropy",
    "coverage_score",
    "final_rolling_sla_10",
    "final_rolling_sla_50",
    "final_rolling_recovery_delta",
]

MULTI_SEED_SUMMARY_COLUMNS = [
    "metric",
    "mean",
    "std",
    "min",
    "max",
    "seeds",
    "rounds_per_seed",
]

MULTI_SEED_SCENARIO_COLUMNS = [
    "event_type",
    "seeds_observed",
    "total_attempts",
    "action_accuracy_mean",
    "action_accuracy_std",
    "average_sla_mean",
    "average_sla_std",
    "recovery_success_rate_mean",
    "recovery_success_rate_std",
    "false_positive_rate_mean",
    "false_positive_rate_std",
    "average_utility_mean",
    "average_utility_std",
]


def parse_seeds(value: str) -> list[int]:
    seeds = [int(part.strip()) for part in value.split(",") if part.strip()]
    if not seeds:
        raise argparse.ArgumentTypeError("at least one seed is required")
    return seeds


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def population(values: list[float]) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
    return {
        "mean": round(mean(values), 3),
        "std": round(stdev(values), 3) if len(values) > 1 else 0.0,
        "min": round(min(values), 3),
        "max": round(max(values), 3),
    }


def seed_summary_from_run(summary: dict[str, Any], round_rows: list[dict[str, str]]) -> dict[str, float]:
    final_row = round_rows[-1] if round_rows else {}
    return {
        **{metric: float(summary[metric]) for metric in SUMMARY_METRICS if metric in summary},
        "final_rolling_sla_10": float(final_row.get("rolling_sla_10", 0.0)),
        "final_rolling_sla_50": float(final_row.get("rolling_sla_50", 0.0)),
        "final_rolling_recovery_delta": float(final_row.get("rolling_recovery_delta", 0.0)),
    }


def summarize_seed_metrics(seed_summaries: list[dict[str, float]], seeds: list[int], rounds: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for metric in SUMMARY_METRICS:
        stats = population([float(summary.get(metric, 0.0)) for summary in seed_summaries])
        rows.append(
            {
                "metric": metric,
                **stats,
                "seeds": ",".join(str(seed) for seed in seeds),
                "rounds_per_seed": rounds,
            }
        )
    return rows


def summarize_scenarios(all_scenario_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in all_scenario_rows:
        grouped[row["event_type"]].append(row)

    output: list[dict[str, Any]] = []
    for event_type, rows in sorted(grouped.items()):
        action_accuracy = [float(row["action_accuracy"]) for row in rows]
        average_sla = [float(row["average_sla"]) for row in rows]
        recovery_success = [float(row["recovery_success_rate"]) for row in rows]
        false_positive = [float(row["false_positive_rate"]) for row in rows]
        average_utility = [float(row["average_utility"]) for row in rows]
        action_stats = population(action_accuracy)
        sla_stats = population(average_sla)
        recovery_stats = population(recovery_success)
        false_positive_stats = population(false_positive)
        utility_stats = population(average_utility)
        output.append(
            {
                "event_type": event_type,
                "seeds_observed": len(rows),
                "total_attempts": sum(int(row["attempts"]) for row in rows),
                "action_accuracy_mean": action_stats["mean"],
                "action_accuracy_std": action_stats["std"],
                "average_sla_mean": sla_stats["mean"],
                "average_sla_std": sla_stats["std"],
                "recovery_success_rate_mean": recovery_stats["mean"],
                "recovery_success_rate_std": recovery_stats["std"],
                "false_positive_rate_mean": false_positive_stats["mean"],
                "false_positive_rate_std": false_positive_stats["std"],
                "average_utility_mean": utility_stats["mean"],
                "average_utility_std": utility_stats["std"],
            }
        )
    return output


def run_multi_seed_evaluation(
    seeds: list[int],
    rounds: int,
    reports_dir: Path = Path("reports"),
) -> dict[str, Any]:
    if rounds < 1:
        raise ValueError("rounds must be at least 1")

    seed_summaries: list[dict[str, float]] = []
    scenario_rows: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory(prefix="aegis-multiseed-", ignore_cleanup_errors=True) as tmp:
        tmp_root = Path(tmp)
        for seed in seeds:
            seed_dir = tmp_root / f"seed_{seed}"
            summary = run_experiments(
                rounds=rounds,
                seed=seed,
                reports_dir=seed_dir,
                db_path=seed_dir / "experiment_state.db",
            )
            round_rows = read_csv(seed_dir / "round_metrics.csv")
            seed_summaries.append(seed_summary_from_run(summary, round_rows))
            for row in read_csv(seed_dir / "scenario_summary.csv"):
                row["seed"] = str(seed)
                scenario_rows.append(row)

    summary_rows = summarize_seed_metrics(seed_summaries, seeds, rounds)
    scenario_summary_rows = summarize_scenarios(scenario_rows)
    summary_path = reports_dir / "multi_seed_summary.csv"
    scenario_summary_path = reports_dir / "multi_seed_scenario_summary.csv"
    write_csv(summary_path, summary_rows, MULTI_SEED_SUMMARY_COLUMNS)
    write_csv(scenario_summary_path, scenario_summary_rows, MULTI_SEED_SCENARIO_COLUMNS)

    return {
        "seeds": seeds,
        "rounds_per_seed": rounds,
        "summary": str(summary_path),
        "scenario_summary": str(scenario_summary_path),
        "metric_rows": len(summary_rows),
        "scenario_rows": len(scenario_summary_rows),
    }


def print_summary(summary: dict[str, Any]) -> None:
    print(f"seeds: {','.join(str(seed) for seed in summary['seeds'])}")
    print(f"rounds per seed: {summary['rounds_per_seed']}")
    print(f"metric rows: {summary['metric_rows']}")
    print(f"scenario rows: {summary['scenario_rows']}")
    print(f"multi-seed summary CSV: {summary['summary']}")
    print(f"multi-seed scenario summary CSV: {summary['scenario_summary']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run safe local multi-seed Aegis-Swarm evaluation.")
    parser.add_argument("--seeds", type=parse_seeds, default=parse_seeds("1,2,3,4,5"), help="Comma-separated seeds.")
    parser.add_argument("--rounds", type=int, default=100, help="Rounds to run for each seed.")
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"), help="Directory for generated CSV reports.")
    args = parser.parse_args()
    summary = run_multi_seed_evaluation(args.seeds, args.rounds, args.reports_dir)
    print_summary(summary)


if __name__ == "__main__":
    main()
