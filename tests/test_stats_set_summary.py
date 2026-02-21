from pathlib import Path

import pytest

from core.progress_store import ProgressStore
from core.stats import compute_set_summary


def _append_attempt(
    store: ProgressStore,
    *,
    idx: int,
    session_id: str,
    set_index: int,
    kind: str,
    position: str,
    is_correct: int,
) -> None:
    store.append_attempt(
        {
            "ts": f"2026-02-20T00:00:{idx:02d}+00:00",
            "session_id": session_id,
            "difficulty": "BEGINNER",
            "selected_kinds_json": '["OR","ROL"]',
            "kind": kind,
            "position": position,
            "hand": "AKo",
            "user_action": "RAISE",
            "correct_action": "RAISE",
            "is_correct": is_correct,
            "learning_mode": "SET_20",
            "set_index": set_index,
            "attempt_index_in_set": idx,
            "expected_raise_size_bb": 3.0,
            "extra_json": "{}",
        }
    )


def test_compute_set_summary_scoped_by_session_and_set_index(tmp_path: Path) -> None:
    db_path = tmp_path / "learning.db"
    store = ProgressStore(db_path)
    store.ensure_schema()

    _append_attempt(store, idx=0, session_id="s1", set_index=0, kind="OR", position="CO", is_correct=1)
    _append_attempt(store, idx=1, session_id="s1", set_index=0, kind="OR", position="CO", is_correct=0)
    _append_attempt(store, idx=2, session_id="s1", set_index=0, kind="ROL", position="SB", is_correct=1)

    _append_attempt(store, idx=3, session_id="s1", set_index=1, kind="OR", position="CO", is_correct=1)
    _append_attempt(store, idx=4, session_id="s2", set_index=0, kind="ROL", position="SB", is_correct=0)

    summary = compute_set_summary(db_path=db_path, session_id="s1", set_index=0)
    assert summary.total_attempts == 3
    assert summary.total_correct == 2
    assert summary.total_accuracy == pytest.approx(2.0 / 3.0)

    by_kind = {item.key: item for item in summary.by_kind}
    assert by_kind["OR"].attempts == 2
    assert by_kind["OR"].correct == 1
    assert by_kind["ROL"].attempts == 1
    assert by_kind["ROL"].correct == 1

    by_position = {item.key: item for item in summary.by_position}
    assert by_position["CO"].attempts == 2
    assert by_position["SB"].attempts == 1


def test_compute_set_summary_empty_for_missing_set(tmp_path: Path) -> None:
    db_path = tmp_path / "learning.db"
    store = ProgressStore(db_path)
    store.ensure_schema()

    summary = compute_set_summary(db_path=db_path, session_id="missing", set_index=9)
    assert summary.total_attempts == 0
    assert summary.total_correct == 0
    assert summary.total_accuracy == pytest.approx(0.0)
    assert summary.by_kind == []
    assert summary.by_position == []
