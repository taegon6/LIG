from __future__ import annotations

import argparse
import csv
import random
import sys
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
from simulator.event_generator import generate_event


STRESS_SEQUENCES: dict[str, tuple[tuple[str, float], ...]] = {
    "MIXED_TRAFFIC_AUTH": (
        ("TRAFFIC_SPIKE", 0.62),
        ("AUTH_ANOMALY", 0.58),
        ("TRAFFIC_SPIKE", 0.72),
        ("AUTH_ANOMALY", 0.66),
    ),
    "SLOW_BURN_DEGRADATION": (
        ("SERVICE_DEGRADATION", 0.48),
        ("SERVICE_DEGRADATION", 0.58),
        ("SERVICE_DEGRADATION", 0.72),
        ("SERVICE_DEGRADATION", 0.86),
    ),
    "TELEMETRY_DRIFT": (
        ("TELEMETRY_INCONSISTENCY", 0.42),
        ("TELEMETRY_INCONSISTENCY", 0.56),
        ("TELEMETRY_INCONSISTENCY", 0.70),
        ("TELEMETRY_INCONSISTENCY", 0.84),
    ),
    "COMMAND_BURST": (
        ("MISSION_COMMAND_ANOMALY", 0.52),
        ("MISSION_COMMAND_ANOMALY", 0.62),
        ("MISSION_COMMAND_ANOMALY", 0.72),
        ("MISSION_COMMAND_ANOMALY", 0.82),
    ),
    "NOISE_THEN_ATTACK": (
        ("LOG_NOISE", 0.18),
        ("LOG_NOISE", 0.22),
        ("TRAFFIC_SPIKE", 0.68),
        ("AUTH_ANOMALY", 0.72),
    ),
}

STRESS_ROUND_COLUMNS = [
    "round_id",
    "sequence_name",
    "step_id",
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
]

STRESS_SUMMARY_COLUMNS = [
    "sequence_name",
    "event_count",
    "final_sla",
    "min_sla",
    "recovery_success",
    "blue_action_accuracy",
    "false_positive_rate",
    "total_utility",
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


def jitter_intensity(base: float) -> float:
    return round(max(0.0, min(1.0, base + random.uniform(-0.03, 0.03))), 2)


def run_stress_scenarios(
    seed: int = 42,
    reports_dir: Path = Path("reports"),
    db_path: Path | None = None,
) -> dict[str, Any]:
    random.seed(seed)
    if db_path is None:
        db_path = reports_dir / "stress_scenario_state.db"
    configure_database(db_path)

    import mission_service.app as app_module

    app_module.MISSION_STATE = MissionState()
    app_module.COMMANDER_MODE = "BALANCED"

    round_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    round_id = 1

    for sequence_name, sequence in STRESS_SEQUENCES.items():
        sequence_rows: list[dict[str, Any]] = []
        for step_id, (event_type, base_intensity) in enumerate(sequence, start=1):
            pre_sla = calculate_sla(db.recent_events(50))
            event = generate_event(event_type, jitter_intensity(base_intensity))
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
            row = {
                "round_id": round_id,
                "sequence_name": sequence_name,
                "step_id": step_id,
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
            round_rows.append(row)
            sequence_rows.append(row)
            round_id += 1

        event_count = len(sequence_rows)
        final_sla = float(sequence_rows[-1]["post_action_sla"])
        min_sla = min(float(row["post_event_sla"]) for row in sequence_rows)
        recovery_success_rate = sum(1 for row in sequence_rows if float(row["recovery_delta"]) >= 0.0) / event_count
        action_accuracy = sum(1 for row in sequence_rows if row["action_match"]) / event_count
        false_positive_rate = sum(1 for row in sequence_rows if row["false_positive"]) / event_count
        summary_rows.append(
            {
                "sequence_name": sequence_name,
                "event_count": event_count,
                "final_sla": round(final_sla, 2),
                "min_sla": round(min_sla, 2),
                "recovery_success": round(recovery_success_rate, 3),
                "blue_action_accuracy": round(action_accuracy, 3),
                "false_positive_rate": round(false_positive_rate, 3),
                "total_utility": round(mean(float(row["total_utility"]) for row in sequence_rows), 2),
            }
        )

    reports_dir.mkdir(parents=True, exist_ok=True)
    round_metrics_path = reports_dir / "stress_round_metrics.csv"
    summary_path = reports_dir / "stress_summary.csv"
    write_csv(round_metrics_path, round_rows, STRESS_ROUND_COLUMNS)
    write_csv(summary_path, summary_rows, STRESS_SUMMARY_COLUMNS)

    return {
        "seed": seed,
        "sequences": len(STRESS_SEQUENCES),
        "total_events": len(round_rows),
        "round_metrics": str(round_metrics_path),
        "summary": str(summary_path),
        "average_final_sla": round(mean(float(row["final_sla"]) for row in summary_rows), 2),
        "average_action_accuracy": round(mean(float(row["blue_action_accuracy"]) for row in summary_rows), 3),
        "average_false_positive_rate": round(mean(float(row["false_positive_rate"]) for row in summary_rows), 3),
    }


def print_summary(summary: dict[str, Any]) -> None:
    print(f"seed: {summary['seed']}")
    print(f"stress sequences: {summary['sequences']}")
    print(f"total events: {summary['total_events']}")
    print(f"average final SLA: {summary['average_final_sla']}")
    print(f"average action accuracy: {summary['average_action_accuracy']}")
    print(f"average false positive rate: {summary['average_false_positive_rate']}")
    print(f"stress round metrics CSV: {summary['round_metrics']}")
    print(f"stress summary CSV: {summary['summary']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run safe local Aegis-Swarm stress scenario sequences.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic stress scenario jitter.")
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"), help="Directory for generated CSV reports.")
    parser.add_argument("--db-path", type=Path, default=None, help="Optional SQLite DB path for isolated runs.")
    args = parser.parse_args()
    summary = run_stress_scenarios(seed=args.seed, reports_dir=args.reports_dir, db_path=args.db_path)
    print_summary(summary)


if __name__ == "__main__":
    main()
