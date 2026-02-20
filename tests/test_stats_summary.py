from pathlib import Path

import pytest

from core.progress_store import ProgressStore
from core.stats import compute_summary


def _append_attempt(store: ProgressStore, *, idx: int, kind: str, position: str, is_correct: int) -> None:
    store.append_attempt(
        {
            "ts": f"2026-02-20T00:00:0{idx}+00:00",
            "session_id": "session-1",
            "difficulty": "BEGINNER",
            "selected_kinds_json": '["OR", "3BET"]',
            "kind": kind,
            "position": position,
            "hand": "AKo",
            "user_action": "RAISE",
            "correct_action": "RAISE",
            "is_correct": is_correct,
            "expected_raise_size_bb": 3.0,
            "extra_json": "{}",
        }
    )


def test_compute_summary_basic(tmp_path: Path) -> None:
    db_path = tmp_path / "learning.db"
    store = ProgressStore(db_path)
    store.ensure_schema()

    _append_attempt(store, idx=1, kind="OR", position="CO", is_correct=1)
    _append_attempt(store, idx=2, kind="OR", position="CO", is_correct=0)
    _append_attempt(store, idx=3, kind="3BET", position="BTN", is_correct=1)
    _append_attempt(store, idx=4, kind="3BET", position="SB", is_correct=1)

    summary = compute_summary(db_path, recent_n=3)

    assert summary.total_attempts == 4
    assert summary.total_correct == 3
    assert summary.total_accuracy == pytest.approx(0.75)

    by_kind = {item.key: item for item in summary.by_kind}
    assert by_kind["OR"].attempts == 2
    assert by_kind["OR"].correct == 1
    assert by_kind["OR"].accuracy == pytest.approx(0.5)
    assert by_kind["3BET"].attempts == 2
    assert by_kind["3BET"].correct == 2
    assert by_kind["3BET"].accuracy == pytest.approx(1.0)

    by_position = {item.key: item for item in summary.by_position}
    assert by_position["CO"].attempts == 2
    assert by_position["CO"].correct == 1
    assert by_position["CO"].accuracy == pytest.approx(0.5)
    assert by_position["BTN"].attempts == 1
    assert by_position["BTN"].correct == 1
    assert by_position["SB"].attempts == 1
    assert by_position["SB"].correct == 1

    assert summary.recent.recent_n == 3
    assert summary.recent.attempts == 3
    assert summary.recent.correct == 2
    assert summary.recent.accuracy == pytest.approx(2.0 / 3.0)


def test_compute_summary_empty(tmp_path: Path) -> None:
    db_path = tmp_path / "learning.db"
    store = ProgressStore(db_path)
    store.ensure_schema()

    summary = compute_summary(db_path, recent_n=10)

    assert summary.total_attempts == 0
    assert summary.total_correct == 0
    assert summary.total_accuracy == pytest.approx(0.0)
    assert summary.by_kind == []
    assert summary.by_position == []
    assert summary.recent.recent_n == 10
    assert summary.recent.attempts == 0
    assert summary.recent.correct == 0
    assert summary.recent.accuracy == pytest.approx(0.0)
