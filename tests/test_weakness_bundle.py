from pathlib import Path

import pytest

from core.progress_store import ProgressStore
from core.stats import compute_weakness_bundle


def _append_attempt(store: ProgressStore, *, idx: int, kind: str, position: str, is_correct: int) -> None:
    store.append_attempt(
        {
            "ts": f"2026-02-20T00:00:{idx:02d}+00:00",
            "session_id": "session-1",
            "difficulty": "BEGINNER",
            "selected_kinds_json": '["OR", "3BET", "ROL"]',
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


def test_compute_weakness_bundle_recent_and_all(tmp_path: Path) -> None:
    db_path = tmp_path / "learning.db"
    store = ProgressStore(db_path)
    store.ensure_schema()

    idx = 1

    # Older 10 attempts
    for _ in range(5):
        _append_attempt(store, idx=idx, kind="OR", position="CO", is_correct=1)
        idx += 1
    for correct in [1, 0, 0, 0, 0]:
        _append_attempt(store, idx=idx, kind="3BET", position="BB", is_correct=correct)
        idx += 1

    # Recent 20 attempts
    for correct in [0, 0, 0, 0, 0, 0, 0, 1]:
        _append_attempt(store, idx=idx, kind="ROL", position="SB", is_correct=correct)
        idx += 1
    for correct in [1, 1, 1, 1, 0, 0, 0]:
        _append_attempt(store, idx=idx, kind="OR", position="CO", is_correct=correct)
        idx += 1
    for correct in [1, 1, 1, 0, 0]:
        _append_attempt(store, idx=idx, kind="3BET", position="BB", is_correct=correct)
        idx += 1

    bundle = compute_weakness_bundle(
        db_path,
        recent_n=20,
        recent_min_attempts=5,
        recent_top_k=3,
        all_min_attempts=10,
        all_top_k=5,
    )

    assert set(bundle.keys()) == {"recent", "all"}

    recent = bundle["recent"]
    assert recent.scope == "recent"
    assert recent.recent_n == 20
    assert recent.min_attempts == 5
    assert recent.top_k == 3
    assert [item.key for item in recent.weak_kinds] == ["ROL", "OR", "3BET"]
    assert [item.key for item in recent.weak_positions] == ["SB", "CO", "BB"]
    assert recent.weak_kinds[0].accuracy == pytest.approx(1.0 / 8.0)
    assert recent.weak_kinds[1].accuracy == pytest.approx(4.0 / 7.0)
    assert recent.weak_kinds[2].accuracy == pytest.approx(3.0 / 5.0)

    all_time = bundle["all"]
    assert all_time.scope == "all"
    assert all_time.recent_n is None
    assert all_time.min_attempts == 10
    assert all_time.top_k == 5

    # ROL/SB are 8 attempts only, so filtered out by all_min_attempts=10.
    assert [item.key for item in all_time.weak_kinds] == ["3BET", "OR"]
    assert [item.key for item in all_time.weak_positions] == ["BB", "CO"]
    assert all_time.weak_kinds[0].accuracy == pytest.approx(4.0 / 10.0)
    assert all_time.weak_kinds[1].accuracy == pytest.approx(9.0 / 12.0)

    assert all_time.weak_kinds[0].accuracy <= all_time.weak_kinds[1].accuracy
    assert all_time.weak_positions[0].accuracy <= all_time.weak_positions[1].accuracy
