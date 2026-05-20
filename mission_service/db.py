from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any


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
            """
        )


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
                false_positive_penalty, total_utility
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                score["timestamp"],
                score["attack_score"],
                score["defense_score"],
                score["sla_score"],
                score["recovery_score"],
                score["false_positive_penalty"],
                score["total_utility"],
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
