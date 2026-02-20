import sqlite3

from core.progress_store import ProgressStore


def test_progress_store_append_attempt(tmp_path):
    db_path = tmp_path / "learning.db"
    store = ProgressStore(db_path)
    store.ensure_schema()

    record = {
        "ts": "2026-02-20T00:00:00+00:00",
        "session_id": "session-1",
        "difficulty": "BEGINNER",
        "selected_kinds_json": '["OR"]',
        "kind": "OR",
        "position": "CO",
        "hand": "AKo",
        "user_action": "RAISE",
        "correct_action": "RAISE",
        "is_correct": 1,
        "expected_raise_size_bb": 3.0,
        "extra_json": "{}",
    }
    store.append_attempt(record)

    with sqlite3.connect(db_path) as con:
        count = con.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
    assert count == 1
