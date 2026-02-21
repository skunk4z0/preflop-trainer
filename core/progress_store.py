from __future__ import annotations

import sqlite3
from pathlib import Path


class ProgressStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)

    def ensure_schema(self) -> None:
        with sqlite3.connect(self.db_path) as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    difficulty TEXT,
                    selected_kinds_json TEXT,
                    kind TEXT NOT NULL,
                    position TEXT NOT NULL,
                    hand TEXT NOT NULL,
                    user_action TEXT NOT NULL,
                    correct_action TEXT NOT NULL,
                    is_correct INTEGER NOT NULL,
                    learning_mode TEXT NOT NULL DEFAULT 'UNLIMITED',
                    set_index INTEGER,
                    attempt_index_in_set INTEGER,
                    expected_raise_size_bb REAL,
                    extra_json TEXT
                )
                """
            )
            self._ensure_column(
                con,
                table="attempts",
                column="learning_mode",
                ddl="TEXT NOT NULL DEFAULT 'UNLIMITED'",
            )
            self._ensure_column(
                con,
                table="attempts",
                column="set_index",
                ddl="INTEGER",
            )
            self._ensure_column(
                con,
                table="attempts",
                column="attempt_index_in_set",
                ddl="INTEGER",
            )
            con.commit()

    @staticmethod
    def _ensure_column(con: sqlite3.Connection, *, table: str, column: str, ddl: str) -> None:
        cols = {str(row[1]) for row in con.execute(f"PRAGMA table_info({table})").fetchall()}
        if column in cols:
            return
        con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
        
    def append_attempt(self, record: dict) -> None:
        required = {
            "ts",
            "session_id",
            "difficulty",
            "selected_kinds_json",
            "kind",
            "position",
            "hand",
            "user_action",
            "correct_action",
            "is_correct",
        }
        missing = sorted(k for k in required if k not in record)
        if missing:
            raise ValueError(f"append_attempt missing required keys: {', '.join(missing)}")

        learning_mode = str(record.get("learning_mode", "UNLIMITED") or "UNLIMITED")
        set_index = record.get("set_index", None)
        attempt_index_in_set = record.get("attempt_index_in_set", None)
        expected_raise_size_bb = record.get("expected_raise_size_bb", None)
        extra_json = record.get("extra_json", "{}")

        with sqlite3.connect(self.db_path) as con:
            con.execute(
                """
                INSERT INTO attempts (
                    ts,
                    session_id,
                    difficulty,
                    selected_kinds_json,
                    kind,
                    position,
                    hand,
                    user_action,
                    correct_action,
                    is_correct,
                    learning_mode,
                    set_index,
                    attempt_index_in_set,
                    expected_raise_size_bb,
                    extra_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["ts"],
                    record["session_id"],
                    record["difficulty"],
                    record["selected_kinds_json"],
                    record["kind"],
                    record["position"],
                    record["hand"],
                    record["user_action"],
                    record["correct_action"],
                    record["is_correct"],
                    learning_mode,
                    set_index,
                    attempt_index_in_set,
                    expected_raise_size_bb,
                    extra_json,
                ),
            )
            con.commit()
