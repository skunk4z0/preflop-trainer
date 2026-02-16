from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import FINAL_TAGS_JSON_PATH
from core.engine import PokerEngine
from core.models import Difficulty, ProblemType
from core.generator import JuegoProblemGenerator
from juego_judge import JUEGOJudge
from json_range_repository import JsonRangeRepository


MAX_TRIES = 200


def fail(msg: str) -> None:
    print(f"[SMOKE][FAIL] {msg}", file=sys.stderr)
    sys.exit(1)


def _pool_size(generator: object, attr_name: str) -> Optional[int]:
    pool = getattr(generator, attr_name, None)
    if pool is None:
        return None
    try:
        return len(pool)
    except TypeError:
        return None


def dump_engine_state(engine: PokerEngine, label: str) -> None:
    gen = getattr(engine, "generator", None)
    print(
        f"[SMOKE][DIAG] {label}: "
        f"difficulty={getattr(engine, 'difficulty', None)!r} "
        f"current_problem={getattr(engine, 'current_problem', None)!r} "
        f"context_is_none={getattr(engine, 'context', None) is None}"
    )
    print(
        f"[SMOKE][DIAG] {label}: generator={type(gen).__name__} "
        f"positions_3bet={_pool_size(gen, '_positions_3bet')} "
        f"pool_beginner={_pool_size(gen, '_pool_beginner')} "
        f"pool_intermediate={_pool_size(gen, '_pool_intermediate')} "
        f"pool_advanced={_pool_size(gen, '_pool_advanced')}"
    )


def main() -> None:
    print("[SMOKE] Starting runtime integration smoke for CC_3BET stage2...")

    # 1) final_tags.json existence check
    p = Path(FINAL_TAGS_JSON_PATH)
    if not p.exists():
        fail(f"final_tags.json not found: {p}. Run build to generate it.")

    # 2) Repo/Judge/Generator/Engine (same setup style as main.py)
    repo = JsonRangeRepository(FINAL_TAGS_JSON_PATH)
    judge = JUEGOJudge(repo)

    positions_3bet = repo.list_positions("CC_3BET")
    if not positions_3bet:
        fail("repo.list_positions('CC_3BET') returned empty list (no positions).")

    gen = JuegoProblemGenerator(
        rng=random.Random(),
        positions_3bet=positions_3bet,
    )
    engine = PokerEngine(generator=gen, juego_judge=judge, enable_debug=False)

    # 3) Start at difficulty where JUEGO_3BET can be generated.
    dump_engine_state(engine, "before start_juego(INTERMEDIATE)")
    engine.start_juego(Difficulty.INTERMEDIATE)
    dump_engine_state(engine, "after start_juego(INTERMEDIATE)")

    # 4) Try up to 200 questions to find a target CC_3BET stage2 case.
    none_count = 0
    saw_3bet = 0
    for i in range(1, MAX_TRIES + 1):
        q = engine.new_question()
        if q is None:
            none_count += 1
            dump_engine_state(engine, f"new_question returned None at try={i}")
            gen_obj = getattr(engine, "generator", None)
            fail(
                "engine.new_question() returned None. "
                f"difficulty_is_none={engine.difficulty is None} "
                f"current_problem_is_none={engine.current_problem is None} "
                f"pool_intermediate_empty={_pool_size(gen_obj, '_pool_intermediate') == 0} "
                f"positions_3bet_empty={_pool_size(gen_obj, '_positions_3bet') == 0}"
            )

        qtype = getattr(q, "problem_type", None) or getattr(engine, "current_problem", None)
        ctx = getattr(q, "ctx", None) or getattr(engine, "context", None)

        if qtype != ProblemType.JUEGO_3BET:
            continue
        saw_3bet += 1
        if ctx is None:
            continue

        position = getattr(ctx, "position", None)
        hand = getattr(ctx, "excel_hand_key", None) or getattr(ctx, "hand", None)
        loose = bool(getattr(ctx, "loose_player_exists", False))

        if not position or not hand:
            continue

        # 5) Inspect tag and expected action via judge; submit only on target.
        jr = judge.judge_3bet(position=position, hand=str(hand), user_action="CALL", loose=loose)
        dbg = getattr(jr, "debug", {}) or {}
        tag_u = str(dbg.get("tag_upper", "") or "")
        expected = str(dbg.get("expected_action", "") or "")

        if not tag_u.startswith("CALL_VS_OPEN_LE_"):
            continue
        if expected != "CALL":
            continue
        if not getattr(jr, "correct", False):
            continue

        res = engine.submit("CALL")
        if not getattr(res, "show_followup_buttons", False):
            fail(
                f"Found target 3BET (try={i}) tag={tag_u} expected={expected}, "
                "but engine did NOT enter followup (show_followup_buttons=False)."
            )

        fu = getattr(engine, "followup", None)
        if fu is None:
            fail("show_followup_buttons=True but engine.followup is None (inconsistent state).")

        expected_max = getattr(fu, "expected_max_bb", None)
        print(
            f"[SMOKE][PASS] CC_3BET stage2 followup started (try={i}/{MAX_TRIES}) "
            f"tag={tag_u} expected_max_bb={expected_max}"
        )
        sys.exit(0)

    fail(
        f"Did not find a CC_3BET CALL_VS_OPEN_LE_* question within {MAX_TRIES} tries. "
        f"none_count={none_count}, saw_3bet={saw_3bet}. "
        "This may mean your data has no such tags or generator never emits JUEGO_3BET at this difficulty."
    )


if __name__ == "__main__":
    main()
