from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import Any

from config import FINAL_TAGS_JSON_PATH
from core.engine import PokerEngine
from core.generator import JuegoProblemGenerator
from core.models import Difficulty, ProblemType
from juego_judge import JUEGOJudge
from json_range_repository import JsonRangeRepository


def _ensure_final_tags_exists() -> None:
    p = Path(FINAL_TAGS_JSON_PATH)
    if not p.exists():
        print(
            "[FATAL] final_tags.json not found. "
            f"Expected path: {p}",
            file=sys.stderr,
        )
        raise SystemExit(1)


def _new_question_for_kind(
    engine: PokerEngine,
    difficulty: Difficulty,
    expected_problem: ProblemType,
    max_tries: int = 64,
):
    engine.start_juego(difficulty)
    for _ in range(max_tries):
        q = engine.new_question()
        if q.problem_type == expected_problem:
            return q
    raise RuntimeError(
        f"Could not generate problem {expected_problem.name} after {max_tries} tries."
    )


def _judge_expected(kind: str, judge: JUEGOJudge, ctx: Any):
    if kind == "OR":
        return judge.judge_or(
            position=ctx.position,
            hand=ctx.excel_hand_key,
            user_action="FOLD",
            loose=ctx.loose_player_exists,
        )
    if kind == "OR_SB":
        return judge.judge_or_sb(
            position="SB",
            hand=ctx.excel_hand_key,
            user_action="FOLD",
            loose=False,
        )
    if kind == "ROL":
        return judge.judge_rol(
            position=ctx.position,
            hand=ctx.excel_hand_key,
            user_action="FOLD",
            loose=ctx.loose_player_exists,
        )
    if kind == "3BET":
        return judge.judge_3bet(
            position=ctx.position,
            hand=ctx.excel_hand_key,
            user_action="FOLD",
            loose=ctx.loose_player_exists,
        )
    raise ValueError(f"Unknown kind: {kind}")


def run_smoke(iterations: int = 200, seed: int = 20260213, verbose: bool = True) -> int:
    _ensure_final_tags_exists()

    repo = JsonRangeRepository(FINAL_TAGS_JSON_PATH)
    judge = JUEGOJudge(repo)
    gen = JuegoProblemGenerator(
        rng=random.Random(seed),
        positions_3bet=repo.list_positions("CC_3BET"),
    )
    engine = PokerEngine(generator=gen, juego_judge=judge, enable_debug=False)

    kind_order = ("OR", "OR_SB", "3BET", "ROL")
    kind_to_spec = {
        "OR": (Difficulty.BEGINNER, ProblemType.JUEGO_OR),
        "OR_SB": (Difficulty.INTERMEDIATE, ProblemType.JUEGO_OR_SB),
        "3BET": (Difficulty.INTERMEDIATE, ProblemType.JUEGO_3BET),
        "ROL": (Difficulty.ADVANCED, ProblemType.JUEGO_ROL),
    }

    counts = {"OR": 0, "OR_SB": 0, "3BET": 0, "ROL": 0}
    followup_count = 0
    failures: list[str] = []

    for i in range(iterations):
        kind = kind_order[i % len(kind_order)]
        diff, expected_problem = kind_to_spec[kind]

        try:
            _new_question_for_kind(engine, diff, expected_problem)
            ctx = engine.context
            if ctx is None:
                raise RuntimeError("engine.context is missing after new_question()")

            expected = _judge_expected(kind, judge, ctx)
            expected_action = str(expected.action).strip().upper()

            res = engine.submit(expected_action)
            dbg = getattr(expected, "debug", {}) or {}
            needs_followup = bool(dbg.get("requires_followup", False))

            if kind == "OR_SB" and needs_followup:
                if not bool(getattr(res, "show_followup_buttons", False)):
                    raise RuntimeError(
                        f"expected followup start, got show_followup_buttons={res.show_followup_buttons}"
                    )

                expected_max = dbg.get("followup_expected_max_bb")
                if not isinstance(expected_max, (int, float)):
                    raise RuntimeError(f"invalid followup_expected_max_bb={expected_max!r}")

                followup_res = engine.submit(str(float(expected_max)))
                if not bool(getattr(followup_res, "is_correct", False)):
                    raise RuntimeError(f"followup incorrect text={followup_res.text!r}")

                followup_count += 1
            else:
                if not bool(getattr(res, "is_correct", False)):
                    raise RuntimeError(f"first-stage incorrect text={res.text!r}")

            counts[kind] += 1
        except Exception as e:
            ctx = engine.context
            failures.append(
                f"i={i} kind={kind} pos={getattr(ctx, 'position', '?')} "
                f"hand={getattr(ctx, 'excel_hand_key', '?')} err={e}"
            )

    # Extra deterministic probe: ensure OR_SB follow-up path is exercised when available.
    followup_probe_hits = 0
    if followup_count == 0:
        diff, expected_problem = kind_to_spec["OR_SB"]
        for _ in range(180):
            try:
                _new_question_for_kind(engine, diff, expected_problem)
                ctx = engine.context
                if ctx is None:
                    break
                expected = _judge_expected("OR_SB", judge, ctx)
                dbg = getattr(expected, "debug", {}) or {}
                if not bool(dbg.get("requires_followup", False)):
                    continue
                followup_probe_hits += 1
                expected_action = str(expected.action).strip().upper()
                res = engine.submit(expected_action)
                if not bool(getattr(res, "show_followup_buttons", False)):
                    failures.append(
                        "followup_probe: expected followup start but show_followup_buttons was False"
                    )
                    break
                expected_max = dbg.get("followup_expected_max_bb")
                followup_res = engine.submit(str(float(expected_max)))
                if not bool(getattr(followup_res, "is_correct", False)):
                    failures.append(
                        f"followup_probe: followup incorrect text={followup_res.text!r}"
                    )
                else:
                    followup_count += 1
                break
            except Exception:
                continue

    if verbose:
        print(
            f"smoke_runtime summary: iterations={iterations} seed={seed} "
            f"OR={counts['OR']} OR_SB={counts['OR_SB']} 3BET={counts['3BET']} ROL={counts['ROL']} "
            f"OR_SB_followups={followup_count}"
        )
        if followup_probe_hits == 0 and followup_count == 0:
            print("note: no OR_SB follow-up tags observed in deterministic sample")
        if failures:
            print(f"failures={len(failures)}")
            for line in failures[:8]:
                print(f"- {line}")

    return 1 if failures else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Headless runtime smoke for OR / OR_SB / 3BET / ROL.")
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20260213)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    code = run_smoke(iterations=max(1, args.iterations), seed=args.seed, verbose=not args.quiet)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
