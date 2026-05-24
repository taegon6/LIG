from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.evaluation_metrics import ROLLING_COLUMNS, add_rolling_metrics

ROUND_COLUMNS = [
    "round_id",
    "event_type",
    "severity",
    "commander_mode",
    "blue_action",
    "pre_sla",
    "post_event_sla",
    "post_action_sla",
    "sla_delta",
    "recovery_delta",
    "red_success_score",
    "blue_defense_score",
    "sla_preservation_score",
    "recovery_score",
    "false_positive_penalty",
    "action_cost",
    "total_utility",
    *ROLLING_COLUMNS,
]

SCENARIO_COLUMNS = [
    "event_type",
    "attempts",
    "average_sla",
    "average_sla_drop",
    "average_recovery_delta",
    "average_utility",
    "action_accuracy",
    "false_positive_rate",
    "recovery_success_rate",
]


def configure_database(db_path: Path) -> None:
    if db_path is None:
        return
    from mission_service import db

    if db_path.exists():
        db_path.unlink()
    db.DB_PATH = db_path
    db.init_db()


def round_to_metric(round_id: int, body: dict[str, Any]) -> dict[str, Any]:
    red_event = body["red_event"]
    blue_decision = body["blue_decision"]
    score = body["score"]
    return {
        "round_id": round_id,
        "event_type": red_event["event_type"],
        "severity": red_event["severity"],
        "commander_mode": body["commander_mode"],
        "blue_action": blue_decision["selected_action"],
        "pre_sla": body["pre_sla"],
        "post_event_sla": body["post_event_sla"],
        "post_action_sla": body["post_action_sla"],
        "sla_delta": body["sla_delta"],
        "recovery_delta": body["recovery_delta"],
        "red_success_score": score["red_success_score"],
        "blue_defense_score": score["blue_defense_score"],
        "sla_preservation_score": score["sla_preservation_score"],
        "recovery_score": score["recovery_score"],
        "false_positive_penalty": score["false_positive_penalty"],
        "action_cost": score["action_cost"],
        "total_utility": score["total_utility"],
    }


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def summarize_by_scenario(round_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in round_rows:
        grouped[str(row["event_type"])].append(row)

    summary_rows: list[dict[str, Any]] = []
    for event_type, rows in sorted(grouped.items()):
        attempts = len(rows)
        summary_rows.append(
            {
                "event_type": event_type,
                "attempts": attempts,
                "average_sla": round(mean(float(row["post_action_sla"]) for row in rows), 2),
                "average_sla_drop": round(mean(max(0.0, float(row["pre_sla"]) - float(row["post_event_sla"])) for row in rows), 2),
                "average_recovery_delta": round(mean(float(row["recovery_delta"]) for row in rows), 2),
                "average_utility": round(mean(float(row["total_utility"]) for row in rows), 2),
                "action_accuracy": round(
                    sum(1 for row in rows if float(row["blue_defense_score"]) >= 70.0) / attempts,
                    3,
                ),
                "false_positive_rate": round(
                    sum(1 for row in rows if float(row["false_positive_penalty"]) > 0.0) / attempts,
                    3,
                ),
                "recovery_success_rate": round(
                    sum(1 for row in rows if float(row["recovery_delta"]) >= 0.0) / attempts,
                    3,
                ),
            }
        )
    return summary_rows


def aggregate_summary(round_rows: list[dict[str, Any]], scenario_stats: dict[str, Any]) -> dict[str, float]:
    if not round_rows:
        return {
            "average_sla": 0.0,
            "average_sla_drop": 0.0,
            "average_recovery_delta": 0.0,
            "average_utility": 0.0,
            "false_positive_rate": 0.0,
            "recovery_success_rate": 0.0,
            "scenario_entropy": float(scenario_stats.get("scenario_entropy", 0.0)),
            "coverage_score": float(scenario_stats.get("coverage_score", 0.0)),
        }

    total = len(round_rows)
    return {
        "average_sla": round(mean(float(row["post_action_sla"]) for row in round_rows), 2),
        "average_sla_drop": round(mean(max(0.0, float(row["pre_sla"]) - float(row["post_event_sla"])) for row in round_rows), 2),
        "average_recovery_delta": round(mean(float(row["recovery_delta"]) for row in round_rows), 2),
        "average_utility": round(mean(float(row["total_utility"]) for row in round_rows), 2),
        "false_positive_rate": round(sum(1 for row in round_rows if float(row["false_positive_penalty"]) > 0.0) / total, 3),
        "recovery_success_rate": round(sum(1 for row in round_rows if float(row["recovery_delta"]) >= 0.0) / total, 3),
        "scenario_entropy": float(scenario_stats.get("scenario_entropy", 0.0)),
        "coverage_score": float(scenario_stats.get("coverage_score", 0.0)),
    }


def run_experiments(
    rounds: int,
    seed: int,
    reports_dir: Path = Path("reports"),
    db_path: Path | None = None,
) -> dict[str, Any]:
    random.seed(seed)
    if db_path is None:
        db_path = reports_dir / "experiment_state.db"
    configure_database(db_path)

    import mission_service.app as app_module
    from mission_service.models import MissionState

    app_module.MISSION_STATE = MissionState()
    app_module.COMMANDER_MODE = "BALANCED"
    app = app_module.app

    client = TestClient(app)
    round_rows: list[dict[str, Any]] = []
    for round_id in range(1, rounds + 1):
        response = client.post("/selfplay/round")
        response.raise_for_status()
        round_rows.append(round_to_metric(round_id, response.json()))

    round_rows = add_rolling_metrics(round_rows)
    scenario_stats = client.get("/stats/scenarios").json()
    scenario_rows = summarize_by_scenario(round_rows)
    reports_dir.mkdir(parents=True, exist_ok=True)
    write_csv(reports_dir / "round_metrics.csv", round_rows, ROUND_COLUMNS)
    write_csv(reports_dir / "scenario_summary.csv", scenario_rows, SCENARIO_COLUMNS)
    summary = aggregate_summary(round_rows, scenario_stats)
    return {
        "rounds": rounds,
        "seed": seed,
        "reports_dir": str(reports_dir),
        "round_metrics": str(reports_dir / "round_metrics.csv"),
        "scenario_summary": str(reports_dir / "scenario_summary.csv"),
        **summary,
    }


def print_summary(summary: dict[str, Any]) -> None:
    print(f"rounds: {summary['rounds']}")
    print(f"seed: {summary['seed']}")
    print(f"average SLA: {summary['average_sla']}")
    print(f"average SLA drop: {summary['average_sla_drop']}")
    print(f"average recovery delta: {summary['average_recovery_delta']}")
    print(f"average utility: {summary['average_utility']}")
    print(f"false positive rate: {summary['false_positive_rate']}")
    print(f"recovery success rate: {summary['recovery_success_rate']}")
    print(f"scenario entropy: {summary['scenario_entropy']}")
    print(f"coverage score: {summary['coverage_score']}")
    print(f"round metrics CSV: {summary['round_metrics']}")
    print(f"scenario summary CSV: {summary['scenario_summary']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run safe local Aegis-Swarm self-play experiments.")
    parser.add_argument("--rounds", type=int, default=100, help="Number of self-play rounds to run.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic scenario selection.")
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"), help="Directory for generated CSV reports.")
    parser.add_argument("--db-path", type=Path, default=None, help="Optional SQLite DB path for isolated runs.")
    args = parser.parse_args()
    if args.rounds < 1:
        raise SystemExit("--rounds must be at least 1")
    summary = run_experiments(args.rounds, args.seed, args.reports_dir, args.db_path)
    print_summary(summary)


if __name__ == "__main__":
    main()
