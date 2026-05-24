from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.blue_agent import BlueAgent
from core.action_registry import apply_action_to_state, build_action_record
from core.scoring import action_matches_event, score_round
from core.sla import calculate_sla
from mission_service import db
from mission_service.app import build_post_action_health_event, update_mission_state_from_event
from mission_service.models import MissionState
from scripts.evaluation_metrics import ROLLING_COLUMNS, add_rolling_metrics
from simulator.event_generator import generate_event
from simulator.scenarios import SAFE_SCENARIOS


BALANCED_SCENARIOS = (
    "TRAFFIC_SPIKE",
    "AUTH_ANOMALY",
    "TELEMETRY_INCONSISTENCY",
    "SERVICE_DEGRADATION",
    "MISSION_COMMAND_ANOMALY",
    "LOG_NOISE",
)

BALANCED_ROUND_COLUMNS = [
    "round_id",
    "event_type",
    "severity",
    "blue_action",
    "pre_sla",
    "post_event_sla",
    "post_action_sla",
    "recovery_delta",
    "red_success_score",
    "blue_defense_score",
    "total_utility",
    "action_match",
    "false_positive",
    *ROLLING_COLUMNS,
]

BALANCED_SCENARIO_COLUMNS = [
    "event_type",
    "attempts",
    "action_accuracy",
    "average_sla",
    "average_sla_drop",
    "average_recovery_delta",
    "average_utility",
    "false_positive_rate",
    "recovery_success_rate",
]


def configure_database(db_path: Path) -> None:
    if db_path.exists():
        db_path.unlink()
    db.DB_PATH = db_path
    db.init_db()


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def intensity_for_scenario(event_type: str) -> float:
    if event_type == "LOG_NOISE":
        return random.uniform(0.1, 0.3)
    if event_type == "SERVICE_DEGRADATION":
        return random.uniform(0.75, 0.95)
    return random.uniform(0.45, 0.85)


def summarize_by_scenario(round_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in round_rows:
        grouped[str(row["event_type"])].append(row)

    summary_rows: list[dict[str, Any]] = []
    for event_type in BALANCED_SCENARIOS:
        rows = grouped[event_type]
        attempts = len(rows)
        if attempts == 0:
            continue
        summary_rows.append(
            {
                "event_type": event_type,
                "attempts": attempts,
                "action_accuracy": round(sum(1 for row in rows if row["action_match"]) / attempts, 3),
                "average_sla": round(mean(float(row["post_action_sla"]) for row in rows), 2),
                "average_sla_drop": round(mean(max(0.0, float(row["pre_sla"]) - float(row["post_event_sla"])) for row in rows), 2),
                "average_recovery_delta": round(mean(float(row["recovery_delta"]) for row in rows), 2),
                "average_utility": round(mean(float(row["total_utility"]) for row in rows), 2),
                "false_positive_rate": round(sum(1 for row in rows if row["false_positive"]) / attempts, 3),
                "recovery_success_rate": round(
                    sum(1 for row in rows if float(row["recovery_delta"]) >= 0.0) / attempts,
                    3,
                ),
            }
        )
    return summary_rows


def run_balanced_evaluation(
    rounds_per_scenario: int,
    seed: int,
    reports_dir: Path = Path("reports"),
    db_path: Path | None = None,
) -> dict[str, Any]:
    if rounds_per_scenario < 1:
        raise ValueError("rounds_per_scenario must be at least 1")

    missing = set(BALANCED_SCENARIOS) - set(SAFE_SCENARIOS)
    if missing:
        raise RuntimeError(f"Balanced scenarios are not all registered as safe scenarios: {sorted(missing)}")

    random.seed(seed)
    if db_path is None:
        db_path = reports_dir / "balanced_evaluation_state.db"
    configure_database(db_path)

    import mission_service.app as app_module

    app_module.MISSION_STATE = MissionState()
    app_module.COMMANDER_MODE = "BALANCED"

    round_rows: list[dict[str, Any]] = []
    round_id = 1
    for event_type in BALANCED_SCENARIOS:
        for _ in range(rounds_per_scenario):
            pre_sla = calculate_sla(db.recent_events(50))
            event = generate_event(event_type, intensity_for_scenario(event_type))
            update_mission_state_from_event(event.model_dump())
            saved_event = db.insert_event(event.model_dump())
            post_event_sla = calculate_sla([saved_event])

            decision = BlueAgent(db.scenario_stats()).decide(db.recent_events(50), post_event_sla)
            db.insert_action(build_action_record(decision).model_dump())
            action_result = apply_action_to_state(decision, app_module.MISSION_STATE.model_dump())
            app_module.MISSION_STATE = MissionState(**action_result["mission_state"])

            recovery_event = build_post_action_health_event(
                saved_event,
                decision,
                app_module.MISSION_STATE,
                action_result,
            )
            saved_recovery_event = db.insert_event(recovery_event.model_dump())
            post_action_sla = calculate_sla([saved_recovery_event])
            recovery_delta = round(post_action_sla - post_event_sla, 2)

            score = score_round(
                saved_event,
                decision.model_dump(),
                post_action_sla,
                previous_sla_score=pre_sla,
                post_event_sla=post_event_sla,
                post_action_sla=post_action_sla,
            )
            saved_score = db.insert_score({"timestamp": saved_recovery_event["timestamp"], **score})
            db.update_scenario_stats(
                event_type=saved_event["event_type"],
                blue_action=decision.selected_action,
                score=saved_score,
                sla_drop=round(pre_sla - post_event_sla, 2),
                recovery_delta=recovery_delta,
            )

            matched = action_matches_event(saved_event, decision.model_dump())
            false_positive = bool(score["false_positive_penalty"] > 0.0)
            round_rows.append(
                {
                    "round_id": round_id,
                    "event_type": saved_event["event_type"],
                    "severity": saved_event["severity"],
                    "blue_action": decision.selected_action,
                    "pre_sla": pre_sla,
                    "post_event_sla": post_event_sla,
                    "post_action_sla": post_action_sla,
                    "recovery_delta": recovery_delta,
                    "red_success_score": score["red_success_score"],
                    "blue_defense_score": score["blue_defense_score"],
                    "total_utility": score["total_utility"],
                    "action_match": matched,
                    "false_positive": false_positive,
                }
            )
            round_id += 1

    round_rows = add_rolling_metrics(round_rows)
    scenario_rows = summarize_by_scenario(round_rows)
    reports_dir.mkdir(parents=True, exist_ok=True)
    round_metrics_path = reports_dir / "balanced_round_metrics.csv"
    scenario_summary_path = reports_dir / "balanced_scenario_summary.csv"
    write_csv(round_metrics_path, round_rows, BALANCED_ROUND_COLUMNS)
    write_csv(scenario_summary_path, scenario_rows, BALANCED_SCENARIO_COLUMNS)

    return {
        "rounds_per_scenario": rounds_per_scenario,
        "seed": seed,
        "total_rounds": len(round_rows),
        "round_metrics": str(round_metrics_path),
        "scenario_summary": str(scenario_summary_path),
        "average_sla": round(mean(float(row["post_action_sla"]) for row in round_rows), 2),
        "average_utility": round(mean(float(row["total_utility"]) for row in round_rows), 2),
        "false_positive_rate": round(sum(1 for row in round_rows if row["false_positive"]) / len(round_rows), 3),
        "recovery_success_rate": round(
            sum(1 for row in round_rows if float(row["recovery_delta"]) >= 0.0) / len(round_rows),
            3,
        ),
    }


def print_summary(summary: dict[str, Any]) -> None:
    print(f"rounds per scenario: {summary['rounds_per_scenario']}")
    print(f"seed: {summary['seed']}")
    print(f"total rounds: {summary['total_rounds']}")
    print(f"average SLA: {summary['average_sla']}")
    print(f"average utility: {summary['average_utility']}")
    print(f"false positive rate: {summary['false_positive_rate']}")
    print(f"recovery success rate: {summary['recovery_success_rate']}")
    print(f"balanced round metrics CSV: {summary['round_metrics']}")
    print(f"balanced scenario summary CSV: {summary['scenario_summary']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run safe balanced Aegis-Swarm scenario evaluation.")
    parser.add_argument("--rounds-per-scenario", type=int, default=20, help="Rounds to run for each safe scenario.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic balanced evaluation.")
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"), help="Directory for generated CSV reports.")
    parser.add_argument("--db-path", type=Path, default=None, help="Optional SQLite DB path for isolated runs.")
    args = parser.parse_args()
    summary = run_balanced_evaluation(args.rounds_per_scenario, args.seed, args.reports_dir, args.db_path)
    print_summary(summary)


if __name__ == "__main__":
    main()
