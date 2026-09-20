"""
SQLite audit trail — schema creation, turn logging, and history retrieval.

The database file path defaults to skyresolve_audit.db in the project root,
overridable via the DB_PATH environment variable.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def _db_path() -> str:
    return os.getenv("DB_PATH", str(Path(__file__).parent.parent / "skyresolve_audit.db"))


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they do not already exist."""
    with _get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversation_turns (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                pnr                   TEXT    NOT NULL,
                timestamp             TEXT    NOT NULL,
                customer_message      TEXT    NOT NULL,
                parsed_intent_json    TEXT,
                policy_decision_json  TEXT,
                agent_response        TEXT,
                actions_taken_json    TEXT,
                escalated             INTEGER NOT NULL DEFAULT 0,
                escalation_reason     TEXT,
                prompt_tokens         INTEGER,
                completion_tokens     INTEGER
            );

            CREATE TABLE IF NOT EXISTS policy_actions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                turn_id      INTEGER NOT NULL REFERENCES conversation_turns(id),
                action_type  TEXT    NOT NULL,
                action_detail TEXT,
                timestamp    TEXT    NOT NULL
            );
            """
        )


def log_turn(
    pnr: str,
    customer_message: str,
    parsed_intent: dict | None,
    policy_decision: dict | None,
    agent_response: str | None,
    actions_taken: list[str],
    escalated: bool,
    escalation_reason: str | None,
    prompt_tokens: int,
    completion_tokens: int,
) -> int:
    """Insert one conversation turn and its policy actions. Returns the turn id."""
    now = datetime.now(timezone.utc).isoformat()
    with _get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO conversation_turns
                (pnr, timestamp, customer_message, parsed_intent_json,
                 policy_decision_json, agent_response, actions_taken_json,
                 escalated, escalation_reason, prompt_tokens, completion_tokens)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pnr,
                now,
                customer_message,
                json.dumps(parsed_intent) if parsed_intent else None,
                json.dumps(policy_decision) if policy_decision else None,
                agent_response,
                json.dumps(actions_taken),
                int(escalated),
                escalation_reason,
                prompt_tokens,
                completion_tokens,
            ),
        )
        turn_id = cursor.lastrowid

        for action in actions_taken:
            conn.execute(
                """
                INSERT INTO policy_actions (turn_id, action_type, action_detail, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (turn_id, action, None, now),
            )

    return turn_id


def get_history(pnr: str) -> list[dict]:
    """Return all conversation turns for the given PNR, oldest first."""
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM conversation_turns WHERE pnr = ? ORDER BY id ASC",
            (pnr.upper(),),
        ).fetchall()

    result = []
    for row in rows:
        entry = dict(row)
        for key in ("parsed_intent_json", "policy_decision_json", "actions_taken_json"):
            if entry.get(key):
                entry[key] = json.loads(entry[key])
        entry["escalated"] = bool(entry["escalated"])
        result.append(entry)
    return result
