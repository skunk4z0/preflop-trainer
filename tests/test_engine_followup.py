import unittest
from types import SimpleNamespace

from core.engine import PokerEngine
from core.models import Difficulty, ProblemType, OpenRaiseProblemContext


class FakeGenerator:
    def __init__(self, problem_type):
        self.problem_type = problem_type

    def generate(self, difficulty):
        ctx = OpenRaiseProblemContext(
            hole_cards=("As", "Kd"),
            position="SB",
            open_size_bb=2.5,
            excel_hand_key="AKo",
            excel_position_key="SB",
            loose_player_exists=False,
        )
        return SimpleNamespace(problem_type=self.problem_type, ctx=ctx, answer_mode="OR", header_text="test")


class FakeJudge:
    def judge_or_sb(self, position, hand, user_action, loose):
        # LimpCx2.5o を正解扱いにする
        dbg = {"tag_upper": "LIMPCX2.5O"}
        return SimpleNamespace(correct=True, reason="ok", debug=dbg)

    def judge_or(self, position, hand, user_action, loose):
        dbg = {"tag_upper": "FOLD"}
        return SimpleNamespace(correct=True, reason="ok", debug=dbg)


class EngineFollowupTest(unittest.TestCase):
    def test_followup_enters_only_on_or_sb_limp(self):
        gen = FakeGenerator(ProblemType.JUEGO_OR_SB)
        eng = PokerEngine(generator=gen, juego_judge=FakeJudge(), enable_debug=True)
        eng.start_juego(Difficulty.BEGINNER)
        eng.new_question()

        res = eng.submit("LIMP_CALL")
        self.assertTrue(res.show_followup_buttons)
        self.assertIsNotNone(eng.followup)

    def test_no_followup_on_or(self):
        gen = FakeGenerator(ProblemType.JUEGO_OR)
        eng = PokerEngine(generator=gen, juego_judge=FakeJudge(), enable_debug=True)
        eng.start_juego(Difficulty.BEGINNER)
        eng.new_question()

        res = eng.submit("RAISE")
        self.assertFalse(res.show_followup_buttons)


if __name__ == "__main__":
    unittest.main()
