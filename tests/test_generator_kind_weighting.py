import random
from pathlib import Path

import pytest

import config
from core.generator import JuegoProblemGenerator
from core.models import ProblemType
from core.progress_store import ProgressStore


def _append_attempt(store: ProgressStore, *, idx: int, kind: str, is_correct: int) -> None:
    store.append_attempt(
        {
            "ts": f"2026-01-01T00:00:{idx:02d}Z",
            "session_id": "sess-kind-weight",
            "difficulty": "BEGINNER",
            "selected_kinds_json": '["OR", "ROL"]',
            "kind": kind,
            "position": "CO",
            "hand": "AJo",
            "user_action": "FOLD",
            "correct_action": "OPEN",
            "is_correct": is_correct,
            "expected_raise_size_bb": None,
            "extra_json": "{}",
        }
    )


def test_pick_problem_type_biases_to_weak_kind(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "ENABLE_WEAKNESS_WEIGHTING", True)
    monkeypatch.setattr(config, "WEAKNESS_RECENT_N", 20)
    monkeypatch.setattr(config, "WEAKNESS_RECENT_MIN_ATTEMPTS", 5)
    monkeypatch.setattr(config, "WEAKNESS_RECENT_TOP_K", 1)
    monkeypatch.setattr(config, "WEAKNESS_KIND_BOOST", 2.0)
    monkeypatch.setattr(config, "WEAKNESS_KIND_FLOOR", 0.8)

    db_path = tmp_path / "learning.db"
    store = ProgressStore(db_path)
    store.ensure_schema()

    idx = 0
    for _ in range(10):
        idx += 1
        _append_attempt(store, idx=idx, kind="OR", is_correct=0)
    for _ in range(10):
        idx += 1
        _append_attempt(store, idx=idx, kind="ROL", is_correct=1)

    gen = JuegoProblemGenerator(rng=random.Random(7), progress_db_path=db_path)
    counts = {"OR": 0, "ROL": 0}
    for _ in range(1000):
        kind = gen._pick_problem_type(["OR", "ROL"])
        if kind == ProblemType.JUEGO_OR:
            counts["OR"] += 1
        elif kind == ProblemType.JUEGO_ROL:
            counts["ROL"] += 1

    assert counts["OR"] > 650


def test_pick_problem_type_without_db_path_stays_compatible() -> None:
    gen = JuegoProblemGenerator(rng=random.Random(11), progress_db_path=None)
    counts = {"OR": 0, "ROL": 0}
    for _ in range(200):
        kind = gen._pick_problem_type(["OR", "ROL"])
        if kind == ProblemType.JUEGO_OR:
            counts["OR"] += 1
        elif kind == ProblemType.JUEGO_ROL:
            counts["ROL"] += 1

    assert counts["OR"] > 0
    assert counts["ROL"] > 0
