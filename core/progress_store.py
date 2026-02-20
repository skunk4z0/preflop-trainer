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
                    expected_raise_size_bb REAL,
                    extra_json TEXT
                )
                """
            )
            con.commit()
        
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
            "expected_raise_size_bb",
            "extra_json",
        }
        missing = sorted(k for k in required if k not in record)
        if missing:
            raise ValueError(f"append_attempt missing required keys: {', '.join(missing)}")

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
                    expected_raise_size_bb,
                    extra_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    record["expected_raise_size_bb"],
                    record["extra_json"],
                ),
            )
            con.commit()
