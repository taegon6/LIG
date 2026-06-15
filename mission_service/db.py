from __future__ import annotations

import os
import sqlite3
from math import log2
from pathlib import Path
from typing import Any

from core.event_schema import now_iso
from simulator.scenarios import SAFE_SCENARIOS


DB_PATH = Path(os.getenv("AEGIS_DB_PATH", "data/aegis_swarm.db"))


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                event_type TEXT NOT NULL,
                severity REAL NOT NULL,
                latency_ms INTEGER NOT NULL,
                status_code INTEGER NOT NULL,
                mission_status TEXT NOT NULL,
                sla_ok INTEGER NOT NULL,
                description TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY,
                timestamp TEXT NOT NULL,
                agent TEXT NOT NULL,
                action_type TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                confidence REAL NOT NULL,
                reason TEXT NOT NULL,
                expected_sla_impact TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY,
                timestamp TEXT NOT NULL,
                attack_score REAL NOT NULL,
                defense_score REAL NOT NULL,
                sla_score REAL NOT NULL,
                recovery_score REAL NOT NULL,
                false_positive_penalty REAL NOT NULL,
                total_utility REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS scenario_stats (
                event_type TEXT PRIMARY KEY,
                attempts INTEGER NOT NULL,
                red_success_count INTEGER NOT NULL,
                blue_success_count INTEGER NOT NULL,
                avg_sla_drop REAL NOT NULL,
                avg_recovery_delta REAL NOT NULL,
                false_positive_count INTEGER NOT NULL,
                most_effective_blue_action TEXT NOT NULL,
                last_seen_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS red_strategy_stats (
                objective TEXT PRIMARY KEY,
                attempts INTEGER NOT NULL,
                avg_red_success_score REAL NOT NULL,
                avg_sla_drop REAL NOT NULL,
                avg_blue_mismatch_rate REAL NOT NULL,
                avg_recovery_delta REAL NOT NULL,
                avg_total_utility_impact REAL NOT NULL,
                most_effective_event_type TEXT NOT NULL,
                last_seen_at TEXT NOT NULL
            );
            """
        )
        score_columns = {row["name"] for row in conn.execute("PRAGMA table_info(scores)").fetchall()}
        score_migrations = {
            "red_success_score": "ALTER TABLE scores ADD COLUMN red_success_score REAL NOT NULL DEFAULT 0",
            "blue_defense_score": "ALTER TABLE scores ADD COLUMN blue_defense_score REAL NOT NULL DEFAULT 0",
            "sla_preservation_score": "ALTER TABLE scores ADD COLUMN sla_preservation_score REAL NOT NULL DEFAULT 100",
            "action_cost": "ALTER TABLE scores ADD COLUMN action_cost REAL NOT NULL DEFAULT 0",
        }
        for column, statement in score_migrations.items():
            if column not in score_columns:
                conn.execute(statement)


def _rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        if "sla_ok" in item:
            item["sla_ok"] = bool(item["sla_ok"])
        result.append(item)
    return result


def insert_event(event: dict[str, Any]) -> dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO events (
                timestamp, source, event_type, severity, latency_ms, status_code,
                mission_status, sla_ok, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event["timestamp"],
                event["source"],
                event["event_type"],
                event["severity"],
                event["latency_ms"],
                event["status_code"],
                event["mission_status"],
                1 if event["sla_ok"] else 0,
                event["description"],
            ),
        )
        conn.commit()
        saved = dict(event)
        saved["id"] = cursor.lastrowid
        return saved


def recent_events(limit: int = 50) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return _rows_to_dicts(rows)


def insert_action(action: dict[str, Any]) -> dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO actions (
                timestamp, agent, action_type, risk_level, confidence, reason, expected_sla_impact
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action["timestamp"],
                action["agent"],
                action["action_type"],
                action["risk_level"],
                action["confidence"],
                action["reason"],
                action["expected_sla_impact"],
            ),
        )
        conn.commit()
        saved = dict(action)
        saved["id"] = cursor.lastrowid
        return saved


def recent_actions(limit: int = 50) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM actions ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return _rows_to_dicts(rows)


def insert_score(score: dict[str, Any]) -> dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO scores (
                timestamp, attack_score, defense_score, sla_score, recovery_score,
                false_positive_penalty, total_utility, red_success_score,
                blue_defense_score, sla_preservation_score, action_cost
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                score["timestamp"],
                score["attack_score"],
                score["defense_score"],
                score["sla_score"],
                score["recovery_score"],
                score["false_positive_penalty"],
                score["total_utility"],
                score.get("red_success_score", score["attack_score"]),
                score.get("blue_defense_score", score["defense_score"]),
                score.get("sla_preservation_score", score["sla_score"]),
                score.get("action_cost", 0.0),
            ),
        )
        conn.commit()
        saved = dict(score)
        saved["id"] = cursor.lastrowid
        return saved


def recent_scores(limit: int = 50) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM scores ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return _rows_to_dicts(rows)


def update_scenario_stats(
    event_type: str,
    blue_action: str,
    score: dict[str, Any],
    sla_drop: float,
    recovery_delta: float,
) -> dict[str, Any]:
    red_success = float(score.get("red_success_score", score.get("attack_score", 0.0))) >= 50.0
    blue_success = (
        float(score.get("blue_defense_score", score.get("defense_score", 0.0))) >= 70.0
        and float(score.get("red_success_score", score.get("attack_score", 0.0))) < 50.0
    )
    false_positive = float(score.get("false_positive_penalty", 0.0)) > 0.0
    timestamp = now_iso()

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT * FROM scenario_stats WHERE event_type = ?",
            (event_type,),
        ).fetchone()
        if existing is None:
            attempts = 1
            red_success_count = 1 if red_success else 0
            blue_success_count = 1 if blue_success else 0
            false_positive_count = 1 if false_positive else 0
            avg_sla_drop = round(max(0.0, sla_drop), 2)
            avg_recovery_delta = round(recovery_delta, 2)
            most_effective_blue_action = blue_action if blue_success else ""
            conn.execute(
                """
                INSERT INTO scenario_stats (
                    event_type, attempts, red_success_count, blue_success_count,
                    avg_sla_drop, avg_recovery_delta, false_positive_count,
                    most_effective_blue_action, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_type,
                    attempts,
                    red_success_count,
                    blue_success_count,
                    avg_sla_drop,
                    avg_recovery_delta,
                    false_positive_count,
                    most_effective_blue_action,
                    timestamp,
                ),
            )
        else:
            row = dict(existing)
            attempts = int(row["attempts"]) + 1
            red_success_count = int(row["red_success_count"]) + (1 if red_success else 0)
            blue_success_count = int(row["blue_success_count"]) + (1 if blue_success else 0)
            false_positive_count = int(row["false_positive_count"]) + (1 if false_positive else 0)
            avg_sla_drop = round(
                ((float(row["avg_sla_drop"]) * int(row["attempts"])) + max(0.0, sla_drop)) / attempts,
                2,
            )
            avg_recovery_delta = round(
                ((float(row["avg_recovery_delta"]) * int(row["attempts"])) + recovery_delta) / attempts,
                2,
            )
            most_effective_blue_action = (
                blue_action if blue_success else str(row["most_effective_blue_action"] or "")
            )
            conn.execute(
                """
                UPDATE scenario_stats
                SET attempts = ?,
                    red_success_count = ?,
                    blue_success_count = ?,
                    avg_sla_drop = ?,
                    avg_recovery_delta = ?,
                    false_positive_count = ?,
                    most_effective_blue_action = ?,
                    last_seen_at = ?
                WHERE event_type = ?
                """,
                (
                    attempts,
                    red_success_count,
                    blue_success_count,
                    avg_sla_drop,
                    avg_recovery_delta,
                    false_positive_count,
                    most_effective_blue_action,
                    timestamp,
                    event_type,
                ),
            )
        conn.commit()
        saved = conn.execute("SELECT * FROM scenario_stats WHERE event_type = ?", (event_type,)).fetchone()
    return dict(saved)


def scenario_stats() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM scenario_stats ORDER BY event_type").fetchall()
    return _rows_to_dicts(rows)


def scenario_stats_summary() -> dict[str, Any]:
    rows = scenario_stats()
    total_attempts = sum(int(row["attempts"]) for row in rows)
    attempted_types = {row["event_type"] for row in rows if int(row["attempts"]) > 0}
    coverage_score = round((len(attempted_types) / len(SAFE_SCENARIOS)) * 100.0, 2)

    if total_attempts <= 0:
        scenario_entropy = 0.0
    else:
        entropy = 0.0
        for row in rows:
            probability = int(row["attempts"]) / total_attempts
            if probability > 0:
                entropy -= probability * log2(probability)
        max_entropy = log2(len(SAFE_SCENARIOS))
        scenario_entropy = round((entropy / max_entropy) * 100.0, 2) if max_entropy else 0.0

    return {
        "scenario_stats": rows,
        "scenario_entropy": scenario_entropy,
        "coverage_score": coverage_score,
        "total_attempts": total_attempts,
    }


def update_red_strategy_stats(
    objective: str,
    event_type: str,
    score: dict[str, Any],
    sla_drop: float,
    blue_mismatch: bool,
    recovery_delta: float,
) -> dict[str, Any]:
    red_success_score = float(score.get("red_success_score", score.get("attack_score", 0.0)))
    total_utility = float(score.get("total_utility", 0.0))
    utility_impact = max(0.0, 100.0 - total_utility)
    timestamp = now_iso()

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT * FROM red_strategy_stats WHERE objective = ?",
            (objective,),
        ).fetchone()
        if existing is None:
            conn.execute(
                """
                INSERT INTO red_strategy_stats (
                    objective, attempts, avg_red_success_score, avg_sla_drop,
                    avg_blue_mismatch_rate, avg_recovery_delta,
                    avg_total_utility_impact, most_effective_event_type,
                    last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    objective,
                    1,
                    round(red_success_score, 2),
                    round(max(0.0, sla_drop), 2),
                    1.0 if blue_mismatch else 0.0,
                    round(recovery_delta, 2),
                    round(utility_impact, 2),
                    event_type,
                    timestamp,
                ),
            )
        else:
            row = dict(existing)
            previous_attempts = int(row["attempts"])
            attempts = previous_attempts + 1

            def rolling_average(column: str, value: float) -> float:
                return round(((float(row[column]) * previous_attempts) + value) / attempts, 2)

            avg_red_success_score = rolling_average("avg_red_success_score", red_success_score)
            avg_sla_drop = rolling_average("avg_sla_drop", max(0.0, sla_drop))
            avg_blue_mismatch_rate = rolling_average("avg_blue_mismatch_rate", 1.0 if blue_mismatch else 0.0)
            avg_recovery_delta = rolling_average("avg_recovery_delta", recovery_delta)
            avg_total_utility_impact = rolling_average("avg_total_utility_impact", utility_impact)
            most_effective_event_type = (
                event_type
                if red_success_score >= float(row["avg_red_success_score"])
                else str(row["most_effective_event_type"] or event_type)
            )
            conn.execute(
                """
                UPDATE red_strategy_stats
                SET attempts = ?,
                    avg_red_success_score = ?,
                    avg_sla_drop = ?,
                    avg_blue_mismatch_rate = ?,
                    avg_recovery_delta = ?,
                    avg_total_utility_impact = ?,
                    most_effective_event_type = ?,
                    last_seen_at = ?
                WHERE objective = ?
                """,
                (
                    attempts,
                    avg_red_success_score,
                    avg_sla_drop,
                    avg_blue_mismatch_rate,
                    avg_recovery_delta,
                    avg_total_utility_impact,
                    most_effective_event_type,
                    timestamp,
                    objective,
                ),
            )
        conn.commit()
        saved = conn.execute("SELECT * FROM red_strategy_stats WHERE objective = ?", (objective,)).fetchone()
    return dict(saved)


def red_strategy_stats() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM red_strategy_stats ORDER BY objective").fetchall()
    return _rows_to_dicts(rows)


def red_strategy_stats_summary() -> dict[str, Any]:
    rows = red_strategy_stats()
    total_attempts = sum(int(row["attempts"]) for row in rows)
    if not rows:
        return {
            "red_strategy_stats": [],
            "total_objective_attempts": 0,
            "most_effective_objective": "",
        }
    most_effective = max(
        rows,
        key=lambda row: (
            float(row["avg_red_success_score"]),
            float(row["avg_sla_drop"]),
            float(row["avg_total_utility_impact"]),
        ),
    )
    return {
        "red_strategy_stats": rows,
        "total_objective_attempts": total_attempts,
        "most_effective_objective": most_effective["objective"],
    }
