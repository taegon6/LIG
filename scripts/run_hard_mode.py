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
from agents.red_objectives import RED_OBJECTIVES, objective_for_event
from core.action_registry import apply_action_to_state, build_action_record
from core.scoring import ACTION_COSTS, action_matches_event, score_round
from core.sla import calculate_sla
from mission_service import db
from mission_service.app import build_post_action_health_event, update_mission_state_from_event
from mission_service.models import MissionState
from simulator.event_generator import generate_event


SAFE_HARD_EVENTS = (
    "TRAFFIC_SPIKE",
    "AUTH_ANOMALY",
    "TELEMETRY_INCONSISTENCY",
    "SERVICE_DEGRADATION",
    "MISSION_COMMAND_ANOMALY",
    "LOG_NOISE",
)

HARD_PATTERNS: tuple[tuple[str, tuple[tuple[str, float], ...]], ...] = (
    (
        "REPEATED_SERVICE_DEGRADATION",
        (
            ("SERVICE_DEGRADATION", 0.82),
            ("SERVICE_DEGRADATION", 0.90),
            ("SERVICE_DEGRADATION", 0.76),
        ),
    ),
    (
        "TELEMETRY_DRIFT",
        (
            ("TELEMETRY_INCONSISTENCY", 0.72),
            ("TELEMETRY_INCONSISTENCY", 0.86),
            ("TELEMETRY_INCONSISTENCY", 0.78),
        ),
    ),
    (
        "MIXED_SAFE_SEQUENCE",
        (
            ("TRAFFIC_SPIKE", 0.78),
            ("AUTH_ANOMALY", 0.72),
            ("MISSION_COMMAND_ANOMALY", 0.70),
            ("SERVICE_DEGRADATION", 0.74),
        ),
    ),
    (
        "NOISE_THEN_PRESSURE",
        (
            ("LOG_NOISE", 0.20),
            ("LOG_NOISE", 0.25),
            ("TRAFFIC_SPIKE", 0.84),
            ("TELEMETRY_INCONSISTENCY", 0.82),
        ),
    ),
)

HARD_ACTION_COSTS = {
    "RESTART_SERVICE": 26.0,
    "ROLLBACK_VERSION": 30.0,
    "ISOLATE_TELEMETRY_STREAM": 22.0,
}

HARD_ROUND_COLUMNS = [
    "round_id",
    "sequence_name",
    "event_type",
    "severity",
    "red_objective",
    "red_strategy_reason",
    "expected_effect",
    "blue_action",
    "blue_mismatch",
    "pre_sla",
    "post_event_sla",
    "post_action_sla",
    "rolling_sla_10",
    "rolling_sla_50",
    "recovery_delta",
    "red_success_score",
    "blue_defense_score",
    "total_utility",
    "action_match",
    "false_positive",
    "recovery_failed",
    "hard_mode_note",
]

HARD_SUMMARY_COLUMNS = [
    "average_sla",
    "min_rolling_sla_10",
    "min_rolling_sla_50",
    "average_recovery_delta",
    "recovery_failure_rate",
    "blue_success_rate",
    "red_success_rate",
    "false_positive_rate",
    "average_utility",
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


def hard_schedule(rounds: int) -> list[tuple[str, str, float]]:
    schedule: list[tuple[str, str, float]] = []
    pattern_index = 0
    while len(schedule) < rounds:
        pattern_name, events = HARD_PATTERNS[pattern_index % len(HARD_PATTERNS)]
        for event_type, intensity in events:
            schedule.append((pattern_name, event_type, intensity))
            if len(schedule) >= rounds:
                break
        pattern_index += 1
    return schedule


def jitter_intensity(base: float) -> float:
    return round(max(0.0, min(1.0, base + random.uniform(-0.04, 0.04))), 2)


def update_pressure(previous: int, event_type: str) -> int:
    if event_type in {"SERVICE_DEGRADATION", "TELEMETRY_INCONSISTENCY", "TRAFFIC_SPIKE"}:
        return min(5, previous + 1)
    if event_type == "LOG_NOISE":
        return max(0, previous - 1)
    return max(0, previous)


def harden_event_payload(event: dict[str, Any], pressure_level: int) -> dict[str, Any]:
    hardened = dict(event)
    event_type = str(hardened["event_type"])
    if pressure_level >= 3 and event_type in {"SERVICE_DEGRADATION", "TELEMETRY_INCONSISTENCY"}:
        hardened["latency_ms"] = max(int(hardened["latency_ms"]), 560 + pressure_level * 25)
        hardened["sla_ok"] = False
    if pressure_level >= 4 and event_type == "TRAFFIC_SPIKE":
        hardened["latency_ms"] = max(int(hardened["latency_ms"]), 520)
        hardened["sla_ok"] = False
    return hardened


def harden_recovery_payload(
    recovery_event: dict[str, Any],
    event_type: str,
    action_type: str,
    pressure_level: int,
) -> tuple[dict[str, Any], bool]:
    hardened = dict(recovery_event)
    partial_recovery = False
    expensive_recovery = action_type in {"RESTART_SERVICE", "ROLLBACK_VERSION", "ISOLATE_TELEMETRY_STREAM"}
    repeated_degradation = event_type in {"SERVICE_DEGRADATION", "TELEMETRY_INCONSISTENCY"} and pressure_level >= 2
    if expensive_recovery and repeated_degradation:
        partial_recovery = True
        hardened["latency_ms"] = max(int(hardened["latency_ms"]), 520 + pressure_level * 20)
        hardened["sla_ok"] = False
        hardened["description"] = f"{hardened['description']} Hard mode partial recovery under repeated local pressure."
    elif pressure_level >= 3 and event_type == "TRAFFIC_SPIKE" and action_type == "APPLY_RATE_LIMIT":
        partial_recovery = True
        hardened["latency_ms"] = max(int(hardened["latency_ms"]), 505)
        hardened["sla_ok"] = False
        hardened["description"] = f"{hardened['description']} Hard mode delayed rate-limit recovery."
    return hardened, partial_recovery


def hard_mode_note(event_type: str, action_type: str, pressure_level: int, partial_recovery: bool) -> str:
    notes = [f"local pressure={pressure_level}"]
    if event_type in {"SERVICE_DEGRADATION", "TELEMETRY_INCONSISTENCY"}:
        notes.append("repeated anomaly pressure")
    if action_type in HARD_ACTION_COSTS:
        notes.append(f"higher simulated action cost={HARD_ACTION_COSTS[action_type]}")
    if partial_recovery:
        notes.append("partial/delayed recovery")
    return "; ".join(notes)


def hard_action_cost(action_type: str) -> float:
    return HARD_ACTION_COSTS.get(action_type, ACTION_COSTS.get(action_type, 10.0))


def adjusted_utility(score: dict[str, Any], action_type: str) -> float:
    extra_cost = max(0.0, hard_action_cost(action_type) - ACTION_COSTS.get(action_type, 10.0))
    return round(max(0.0, float(score["total_utility"]) - extra_cost * 0.2), 2)


def run_hard_mode(
    rounds: int,
    seed: int,
    reports_dir: Path = Path("reports"),
    db_path: Path | None = None,
) -> dict[str, Any]:
    if rounds < 1:
        raise ValueError("rounds must be at least 1")

    random.seed(seed)
    if db_path is None:
        db_path = reports_dir / "hard_mode_state.db"
    configure_database(db_path)

    import mission_service.app as app_module

    app_module.MISSION_STATE = MissionState()
    app_module.COMMANDER_MODE = "DEFENSE_HARDENING"

    pressure_level = 0
    sla_history: list[float] = []
    rows: list[dict[str, Any]] = []
    for round_id, (pattern_name, event_type, intensity) in enumerate(hard_schedule(rounds), start=1):
        pre_sla = calculate_sla(db.recent_events(50))
        pressure_level = update_pressure(pressure_level, event_type)
        event = generate_event(event_type, jitter_intensity(intensity)).model_dump()
        event = harden_event_payload(event, pressure_level)
        update_mission_state_from_event(event)
        saved_event = db.insert_event(event)
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
        ).model_dump()
        recovery_event, partial_recovery = harden_recovery_payload(
            recovery_event,
            str(saved_event["event_type"]),
            decision.selected_action,
            pressure_level,
        )
        saved_recovery_event = db.insert_event(recovery_event)
        post_action_sla = calculate_sla([saved_recovery_event])
        sla_history.append(post_action_sla)
        rolling_sla_10 = round(mean(sla_history[-10:]), 2)
        rolling_sla_50 = round(mean(sla_history[-50:]), 2)
        recovery_delta = round(post_action_sla - post_event_sla, 2)

        score = score_round(
            saved_event,
            decision.model_dump(),
            post_action_sla,
            previous_sla_score=pre_sla,
            post_event_sla=post_event_sla,
            post_action_sla=post_action_sla,
        )
        total_utility = adjusted_utility(score, decision.selected_action)
        recovery_failed = post_action_sla < post_event_sla or post_action_sla < 85.0
        red_objective = objective_for_event(str(saved_event["event_type"]))
        objective = RED_OBJECTIVES[red_objective]
        blue_mismatch = not action_matches_event(saved_event, decision.model_dump())
        saved_score = db.insert_score({"timestamp": saved_recovery_event["timestamp"], **score, "total_utility": total_utility})
        db.update_scenario_stats(
            event_type=saved_event["event_type"],
            blue_action=decision.selected_action,
            score=saved_score,
            sla_drop=round(pre_sla - post_event_sla, 2),
            recovery_delta=recovery_delta,
        )
        db.update_red_strategy_stats(
            objective=red_objective,
            event_type=saved_event["event_type"],
            score=saved_score,
            sla_drop=round(pre_sla - post_event_sla, 2),
            blue_mismatch=blue_mismatch,
            recovery_delta=recovery_delta,
        )

        rows.append(
            {
                "round_id": round_id,
                "sequence_name": pattern_name,
                "event_type": saved_event["event_type"],
                "severity": saved_event["severity"],
                "red_objective": red_objective,
                "red_strategy_reason": objective.strategy_reason,
                "expected_effect": objective.expected_effect,
                "blue_action": decision.selected_action,
                "blue_mismatch": blue_mismatch,
                "pre_sla": pre_sla,
                "post_event_sla": post_event_sla,
                "post_action_sla": post_action_sla,
                "rolling_sla_10": rolling_sla_10,
                "rolling_sla_50": rolling_sla_50,
                "recovery_delta": recovery_delta,
                "red_success_score": score["red_success_score"],
                "blue_defense_score": score["blue_defense_score"],
                "total_utility": total_utility,
                "action_match": not blue_mismatch,
                "false_positive": bool(score["false_positive_penalty"] > 0.0),
                "recovery_failed": recovery_failed,
                "hard_mode_note": hard_mode_note(
                    str(saved_event["event_type"]),
                    decision.selected_action,
                    pressure_level,
                    partial_recovery,
                ),
            }
        )

    reports_dir.mkdir(parents=True, exist_ok=True)
    round_metrics_path = reports_dir / "hard_mode_round_metrics.csv"
    summary_path = reports_dir / "hard_mode_summary.csv"
    write_csv(round_metrics_path, rows, HARD_ROUND_COLUMNS)

    summary_row = {
        "average_sla": round(mean(float(row["post_action_sla"]) for row in rows), 2),
        "min_rolling_sla_10": round(min(float(row["rolling_sla_10"]) for row in rows), 2),
        "min_rolling_sla_50": round(min(float(row["rolling_sla_50"]) for row in rows), 2),
        "average_recovery_delta": round(mean(float(row["recovery_delta"]) for row in rows), 2),
        "recovery_failure_rate": round(sum(1 for row in rows if row["recovery_failed"]) / rounds, 3),
        "blue_success_rate": round(sum(1 for row in rows if float(row["blue_defense_score"]) >= 70.0) / rounds, 3),
        "red_success_rate": round(sum(1 for row in rows if float(row["red_success_score"]) > 0.0) / rounds, 3),
        "false_positive_rate": round(sum(1 for row in rows if row["false_positive"]) / rounds, 3),
        "average_utility": round(mean(float(row["total_utility"]) for row in rows), 2),
    }
    write_csv(summary_path, [summary_row], HARD_SUMMARY_COLUMNS)

    return {
        "rounds": rounds,
        "seed": seed,
        "round_metrics": str(round_metrics_path),
        "summary": str(summary_path),
        **summary_row,
    }


def print_summary(summary: dict[str, Any]) -> None:
    print(f"rounds: {summary['rounds']}")
    print(f"seed: {summary['seed']}")
    print(f"average SLA: {summary['average_sla']}")
    print(f"min rolling SLA 10: {summary['min_rolling_sla_10']}")
    print(f"min rolling SLA 50: {summary['min_rolling_sla_50']}")
    print(f"average recovery delta: {summary['average_recovery_delta']}")
    print(f"recovery failure rate: {summary['recovery_failure_rate']}")
    print(f"blue success rate: {summary['blue_success_rate']}")
    print(f"red success rate: {summary['red_success_rate']}")
    print(f"false positive rate: {summary['false_positive_rate']}")
    print(f"average utility: {summary['average_utility']}")
    print(f"hard mode round metrics CSV: {summary['round_metrics']}")
    print(f"hard mode summary CSV: {summary['summary']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run safe local Aegis-Swarm hard mode evaluation.")
    parser.add_argument("--rounds", type=int, default=100, help="Number of hard mode rounds to run.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic hard mode schedule.")
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"), help="Directory for generated CSV reports.")
    parser.add_argument("--db-path", type=Path, default=None, help="Optional SQLite DB path for isolated runs.")
    args = parser.parse_args()
    summary = run_hard_mode(args.rounds, args.seed, args.reports_dir, args.db_path)
    print_summary(summary)


if __name__ == "__main__":
    main()
