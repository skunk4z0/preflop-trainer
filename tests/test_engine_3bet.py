from pathlib import Path
from types import SimpleNamespace

import pytest

from core.engine import PokerEngine
from core.models import Difficulty, OpenRaiseProblemContext, ProblemType
from juego_judge import JUEGOJudge
from json_range_repository import JsonRangeRepository


class Fixed3BetGenerator:
    def __init__(self, ctx: OpenRaiseProblemContext):
        self._ctx = ctx

    def generate(self, difficulty):
        return SimpleNamespace(
            problem_type=ProblemType.JUEGO_3BET,
            ctx=self._ctx,
            answer_mode="3BET",
            header_text="test-3bet",
        )


@pytest.mark.parametrize(
    "hand,action,expected_tag_prefix",
    [
        ("22", "CALL", "CALL_VS_OPEN_"),
        ("77", "RAISE", "3BET_VS_4BET_"),
        ("32o", "FOLD", "FOLD"),
    ],
)
def test_engine_submit_juego_3bet_uses_cc_3bet_tags(hand, action, expected_tag_prefix):
    repo_path = Path(__file__).resolve().parents[1] / "data" / "final_tags.json"
    repo = JsonRangeRepository(repo_path)
    judge = JUEGOJudge(repo)

    ctx = OpenRaiseProblemContext(
        hole_cards=("As", "Kd"),
        position="BB VS BTN",
        open_size_bb=0.0,
        loose_player_exists=False,
        excel_hand_key=hand,
        excel_position_key="BB VS BTN",
        limpers=0,
    )
    gen = Fixed3BetGenerator(ctx)
    engine = PokerEngine(generator=gen, juego_judge=judge, enable_debug=False)
    engine.start_juego(Difficulty.INTERMEDIATE)
    engine.new_question()

    result = engine.submit(action)

    assert result.is_correct is True
    assert result.judge_result is not None
    dbg = result.judge_result.debug
    assert dbg["kind"] == "CC_3BET"
    assert dbg["repo"]["found_kind"] is True
    if expected_tag_prefix == "FOLD":
        assert dbg["detail_tag"] == "FOLD"
    else:
        assert dbg["detail_tag"].startswith(expected_tag_prefix)
