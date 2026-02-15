from __future__ import annotations

import sys
from types import SimpleNamespace

from core.engine import PokerEngine
from core.models import Difficulty, OpenRaiseProblemContext, ProblemType


class FakeGenerator:
    def __init__(self, problem_type: ProblemType) -> None:
        self.problem_type = problem_type

    def next_question(self, difficulty: Difficulty) -> SimpleNamespace:
        del difficulty
        position = "CO" if self.problem_type == ProblemType.JUEGO_3BET else "SB"
        ctx = OpenRaiseProblemContext(
            hole_cards=("As", "Kd"),
            position=position,
            open_size_bb=2.5,
            excel_hand_key="AKo",
            excel_position_key=position,
            loose_player_exists=False,
        )
        return SimpleNamespace(
            problem_type=self.problem_type,
            ctx=ctx,
            answer_mode="OR",
            header_text="smoke",
        )


class FakeJudge:
    def judge_or_sb(self, position: str, hand: str, user_action: str, loose: bool) -> SimpleNamespace:
        del position, hand, user_action, loose
        dbg = {"tag_upper": "LIMPCX2.5O", "expected_action": "LIMP_CALL"}
        return SimpleNamespace(correct=True, reason="ok", debug=dbg)

    def judge_or(self, position: str, hand: str, user_action: str, loose: bool) -> SimpleNamespace:
        del position, hand, user_action, loose
        dbg = {"tag_upper": "FOLD", "expected_action": "FOLD"}
        return SimpleNamespace(correct=True, reason="ok", debug=dbg)

    def judge_3bet(self, position: str, hand: str, user_action: str, loose: bool) -> SimpleNamespace:
        del position, hand, user_action, loose
        dbg = {"tag_upper": "CALL_VS_OPEN_LE_3X", "expected_action": "CALL"}
        return SimpleNamespace(correct=True, reason="ok", debug=dbg)


def _fail(msg: str) -> int:
    print(msg, file=sys.stderr)
    return 1


def main() -> int:
    engine = PokerEngine(
        generator=FakeGenerator(ProblemType.JUEGO_3BET),
        juego_judge=FakeJudge(),
        enable_debug=True,
    )
    engine.start_juego(Difficulty.BEGINNER)
    engine.new_question()
    result = engine.submit("CALL")

    if not result.show_followup_buttons:
        return _fail("followup did not start: show_followup_buttons=False")
    if engine.followup is None:
        return _fail("followup did not start: engine.followup is None")
    if abs(engine.followup.expected_max_bb - 3.0) > 1e-9:
        return _fail(f"unexpected expected_max_bb: {engine.followup.expected_max_bb}")

    print(
        "OK: followup started for CC_3BET stage2; "
        f"expected_max_bb={engine.followup.expected_max_bb}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
