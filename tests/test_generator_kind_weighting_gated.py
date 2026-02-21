import random

import config
from core.generator import JuegoProblemGenerator
from core.models import ProblemType


def test_kind_weighting_is_fully_gated_off_when_not_pro(monkeypatch) -> None:
    monkeypatch.setattr(config, "ENABLE_WEAKNESS_WEIGHTING", True)

    gen = JuegoProblemGenerator(rng=random.Random(5), progress_db_path="__missing__.db", is_pro=False)

    def _should_not_call():
        raise AssertionError("_get_cached_weak_kinds should not be called when is_pro=False")

    gen._get_cached_weak_kinds = _should_not_call  # type: ignore[method-assign]
    kinds = [gen._pick_problem_type(["OR", "ROL"]) for _ in range(200)]
    assert ProblemType.JUEGO_OR in kinds
    assert ProblemType.JUEGO_ROL in kinds


def test_kind_weighting_runs_when_pro_enabled(monkeypatch) -> None:
    monkeypatch.setattr(config, "ENABLE_WEAKNESS_WEIGHTING", True)
    monkeypatch.setattr(config, "WEAKNESS_KIND_BOOST", 2.0)
    monkeypatch.setattr(config, "WEAKNESS_KIND_FLOOR", 0.8)

    gen = JuegoProblemGenerator(rng=random.Random(7), is_pro=True)
    gen._get_cached_weak_kinds = lambda: {"OR"}  # type: ignore[method-assign]

    or_count = 0
    rol_count = 0
    for _ in range(1000):
        ptype = gen._pick_problem_type(["OR", "ROL"])
        if ptype == ProblemType.JUEGO_OR:
            or_count += 1
        elif ptype == ProblemType.JUEGO_ROL:
            rol_count += 1

    assert or_count > 650
    assert or_count > rol_count
