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
from agents.commander_agent import CommanderAgent
from agents.red_agent import RedAgent
from core.action_registry import apply_action_to_state, build_action_record
from core.event_schema import BlueDecision
from core.scoring import score_round
from core.sla import calculate_sla
from mission_service import db
from mission_service.app import build_post_action_health_event, update_mission_state_from_event
from mission_service.models import MissionState


ABLATION_VARIANTS = ("baseline_rule", "latest_event_only", "memory_only", "full_v2")

ABLATION_COLUMNS = [
    "variant",
    "rounds",
    "seed",
    "average_sla",
    "blue_success_rate",
    "red_success_rate",
    "recovery_success_rate",
    "false_positive_rate",
    "average_utility",
]


class GenericRuleBlueAgent(BlueAgent):
    """Ablation policy with optional latest-event and memory features.

    The generic rule intentionally lacks v2's exact event-to-action mappings
    unless scenario memory identifies repeated failures. This makes the
    ablation compare feature contributions rather than production behavior.
    """

    def __init__(
        self,
        scenario_stats: list[dict[str, Any]] | None = None,
        *,
        use_latest_event: bool = False,
        use_memory: bool = False,
    ) -> None:
        super().__init__(scenario_stats)
        self.use_latest_event = use_latest_event
        self.use_memory = use_memory

    def decide(self, events: list[dict[str, Any]], sla_score: float | None = None) -> BlueDecision:
        from agents.blue.triage_policy import dominant_event_type, latest_active_event_type

        if sla_score is None:
            sla_score = calculate_sla(events)

        component_scores = self.calculate_component_scores(events)
        risk_score = self.triage.risk_score(component_scores)
        risk_level = self.triage.risk_level(risk_score)
        event_type = latest_active_event_type(events) if self.use_latest_event else dominant_event_type(events)
        action, reason = self.choose_generic_action(event_type, risk_score, sla_score)
        confidence = round(min(0.95, 0.55 + abs(risk_score - 0.5) * 0.55 + len(events) * 0.01), 2)

        return BlueDecision(
            risk_score=risk_score,
            risk_level=risk_level,
            selected_action=action,
            confidence=confidence,
            reason=f"Ablation policy selected {event_type}. {reason}",
            expected_sla_impact=self.sla_governor.expected_sla_impact(action),
            component_scores={name: round(value, 3) for name, value in component_scores.items()},
        )

    def choose_generic_action(self, event_type: str, risk_score: float, sla_score: float) -> tuple[str, str]:
        if self.use_memory and self.memory_saw_miss(event_type):
            preferred = self.sla_governor.preferred_failure_actions(event_type)
            return preferred[0], "Scenario memory detected repeated misses and selected the preferred response."

        if self.sla_governor.should_recover_first(sla_score):
            return self.recovery.action_for(event_type, sla_score)

        if event_type in {"NORMAL", "LOG_NOISE", "RECOVERY_HEALTH_CHECK"}:
            return "OBSERVE_ONLY", "Generic rule observes benign or recovery events."

        if risk_score < 0.3:
            return "OBSERVE_ONLY", "Generic risk rule treats this as low risk."

        if risk_score < 0.8:
            return "APPLY_RATE_LIMIT", "Generic risk rule applies a low-impact rate limit."

        return "ESCALATE_ALERT", "Generic risk rule escalates critical risk."

    def memory_saw_miss(self, event_type: str) -> bool:
        for row in self.scenario_stats:
            if str(row.get("event_type")) != event_type:
                continue
            attempts = int(row.get("attempts", 0))
            blue_success = int(row.get("blue_success_count", 0))
            return attempts > 0 and blue_success < attempts
        return False


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


def make_blue_agent(variant: str, scenario_stats: list[dict[str, Any]]) -> BlueAgent:
    if variant == "baseline_rule":
        return GenericRuleBlueAgent()
    if variant == "latest_event_only":
        return GenericRuleBlueAgent(use_latest_event=True)
    if variant == "memory_only":
        return GenericRuleBlueAgent(scenario_stats=scenario_stats, use_memory=True)
    if variant == "full_v2":
        return BlueAgent(scenario_stats=scenario_stats)
    raise ValueError(f"Unknown ablation variant: {variant}")


def run_variant(variant: str, rounds: int, seed: int, db_path: Path) -> dict[str, Any]:
    if rounds < 1:
        raise ValueError("rounds must be at least 1")

    random.seed(seed)
    configure_database(db_path)

    import mission_service.app as app_module

    app_module.MISSION_STATE = MissionState()
    app_module.COMMANDER_MODE = "BALANCED"

    round_rows: list[dict[str, Any]] = []
    commander = CommanderAgent()
    red = RedAgent()
    for _ in range(rounds):
        pre_sla = calculate_sla(db.recent_events(50))
        recent_scores = db.recent_scores(10)
        recent_actions = db.recent_actions(10)
        mode = commander.decide_mode(pre_sla, recent_scores, recent_actions)
        app_module.COMMANDER_MODE = mode

        red_event = red.generate(mode, recent_scores, pre_sla, None)
        update_mission_state_from_event(red_event.model_dump())
        saved_event = db.insert_event(red_event.model_dump())
        post_event_sla = calculate_sla([saved_event])

        blue_stats = db.scenario_stats() if variant in {"memory_only", "full_v2"} else []
        blue_decision = make_blue_agent(variant, blue_stats).decide(db.recent_events(50), post_event_sla)
        db.insert_action(build_action_record(blue_decision).model_dump())
        action_result = apply_action_to_state(blue_decision, app_module.MISSION_STATE.model_dump())
        app_module.MISSION_STATE = MissionState(**action_result["mission_state"])

        recovery_event = build_post_action_health_event(
            saved_event,
            blue_decision,
            app_module.MISSION_STATE,
            action_result,
        )
        saved_recovery_event = db.insert_event(recovery_event.model_dump())
        post_action_sla = calculate_sla([saved_recovery_event])
        recovery_delta = round(post_action_sla - post_event_sla, 2)

        score = score_round(
            saved_event,
            blue_decision.model_dump(),
            post_action_sla,
            previous_sla_score=pre_sla,
            post_event_sla=post_event_sla,
            post_action_sla=post_action_sla,
        )
        saved_score = db.insert_score({"timestamp": saved_recovery_event["timestamp"], **score})
        db.update_scenario_stats(
            event_type=saved_event["event_type"],
            blue_action=blue_decision.selected_action,
            score=saved_score,
            sla_drop=round(pre_sla - post_event_sla, 2),
            recovery_delta=recovery_delta,
        )
        round_rows.append(
            {
                "post_action_sla": post_action_sla,
                "blue_success": float(score["blue_defense_score"]) >= 70.0,
                "red_success": float(score["red_success_score"]) > 0.0,
                "recovery_success": recovery_delta >= 0.0,
                "false_positive": float(score["false_positive_penalty"]) > 0.0,
                "total_utility": score["total_utility"],
            }
        )

    return {
        "variant": variant,
        "rounds": rounds,
        "seed": seed,
        "average_sla": round(mean(float(row["post_action_sla"]) for row in round_rows), 2),
        "blue_success_rate": round(sum(1 for row in round_rows if row["blue_success"]) / rounds, 3),
        "red_success_rate": round(sum(1 for row in round_rows if row["red_success"]) / rounds, 3),
        "recovery_success_rate": round(sum(1 for row in round_rows if row["recovery_success"]) / rounds, 3),
        "false_positive_rate": round(sum(1 for row in round_rows if row["false_positive"]) / rounds, 3),
        "average_utility": round(mean(float(row["total_utility"]) for row in round_rows), 2),
    }


def run_ablation(
    rounds: int = 100,
    seed: int = 42,
    reports_dir: Path = Path("reports"),
) -> dict[str, Any]:
    rows = [
        run_variant(variant, rounds, seed, reports_dir / f"ablation_{variant}.db")
        for variant in ABLATION_VARIANTS
    ]
    report_path = reports_dir / "ablation_summary.csv"
    write_csv(report_path, rows, ABLATION_COLUMNS)
    return {
        "rounds": rounds,
        "seed": seed,
        "variants": len(rows),
        "summary": str(report_path),
    }


def print_summary(summary: dict[str, Any]) -> None:
    print(f"rounds: {summary['rounds']}")
    print(f"seed: {summary['seed']}")
    print(f"variants: {summary['variants']}")
    print(f"ablation summary CSV: {summary['summary']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run safe local Aegis-Swarm policy ablation.")
    parser.add_argument("--rounds", type=int, default=100, help="Rounds per ablation variant.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for each variant.")
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"), help="Directory for generated CSV reports.")
    args = parser.parse_args()
    summary = run_ablation(rounds=args.rounds, seed=args.seed, reports_dir=args.reports_dir)
    print_summary(summary)


if __name__ == "__main__":
    main()
