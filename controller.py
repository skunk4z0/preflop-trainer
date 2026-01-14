import random
import itertools
from dataclasses import dataclass
from enum import Enum, auto
from typing import Tuple, Optional


class ProblemType(Enum):
    YOKOSAWA_OPEN = auto()
    JUEGO_OR = auto()


@dataclass(frozen=True)
class OpenRaiseProblemContext:
    hole_cards: Tuple[str, str]         # 例: ("Ks","Jc")
    position: str                       # "EP"/"MP"/"CO"/"BTN"
    open_size_bb: float                 # BTN=2.5, else=3.0
    loose_player_exists: bool           # True/False
    excel_hand_key: str                 # 例: "KJo"
    excel_position_key: str             # 今回は未使用（将来用）


class GameController:
    def __init__(self, ui, juego_judge, yokosawa_judge):
        self.ui = ui
        self.juego_judge = juego_judge
        self.yokosawa_judge = yokosawa_judge

        self.problem_type: Optional[ProblemType] = None
        self.context: Optional[OpenRaiseProblemContext] = None

        suits = ["s", "h", "d", "c"]
        ranks = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"]
        self.deck = [r + s for r, s in itertools.product(ranks, suits)]

    # =========================
    # 開始
    # =========================
    def start_yokosawa_open(self):
        self.problem_type = ProblemType.YOKOSAWA_OPEN
        self.new_question()

    def start_juego_beginner(self):
        print("[CTRL] start_juego_beginner clicked")
        self.problem_type = ProblemType.JUEGO_OR
        self.new_question()

    # =========================
    # 新しい問題
    # =========================
    def new_question(self):
        print("[CTRL] new_question called. problem_type=", self.problem_type)

        # Next は「回答後に表示」したいので、問題生成時点では隠す
        if hasattr(self.ui, "hide_next_button"):
            self.ui.hide_next_button()

        if self.problem_type == ProblemType.YOKOSAWA_OPEN:
            hole = tuple(random.sample(self.deck, 2))
            self.ui.deal_cards(hole)
            self.ui.show_text("【ヨコサワ式】オープン判断。あなたのアクションは？")
            return

        if self.problem_type == ProblemType.JUEGO_OR:
            self.context = self._generate_juego_open_raise_problem()
            self.ui.deal_cards(self.context.hole_cards)

            # UI 仕様に合わせて統一：set_entries -> set_hand_pos
            self.ui.set_hand_pos(
                hand=self.context.excel_hand_key,
                pos=self.context.position,
            )

            self.ui.show_text(
                f"【JUEGO】オープンレイズ判断｜"
                f"Pos: {self.context.position}｜"
                f"{self.context.open_size_bb}BB"
            )
            return

        # モード未選択など
        self.ui.show_text("モードを選択してください")

    # =========================
    # 回答
    # =========================
    def submit(self, hand, pos, user_action):
        """
        UI側に「回答ボタン」がある想定。
        UIから (hand, pos, user_action) を渡して呼ぶ。
        """
        result = None
        is_correct = False

        try:
            if self.problem_type is None:
                self.ui.show_text("モードを選択してください")
                return

            # -------------------------
            # ヨコサワ式
            # -------------------------
            if self.problem_type == ProblemType.YOKOSAWA_OPEN:
                if self.yokosawa_judge is None:
                    raise RuntimeError("yokosawa_judge is not set")

                result = self.yokosawa_judge.judge(pos=pos, hand=hand)
                is_correct = (user_action == result.action)

            # -------------------------
            # JUEGO OR
            # -------------------------
            elif self.problem_type == ProblemType.JUEGO_OR:
                if self.context is None:
                    raise RuntimeError("Context is missing")

                ctx = self.context
                result = self.juego_judge.judge_or(
                    position=ctx.position,
                    hand=ctx.excel_hand_key,
                    user_action=user_action,
                    loose=ctx.loose_player_exists,
                )

                # ===== DEBUG PRINT =====
                print("=== JUEGO DEBUG ===")
                print(getattr(result, "debug", "NO_DEBUG"))
                print("===================")

                is_correct = bool(getattr(result, "correct", False))

            else:
                self.ui.show_text("未対応のモードです")
                return

            # -------------------------
            # UI反映（統一：show_text）
            # -------------------------
            reason = getattr(result, "reason", "")
            if is_correct:
                self.ui.show_text(f"正解：{reason}")
            else:
                self.ui.show_text(f"不正解：{reason}")

        except Exception as e:
            self.ui.show_text(f"内部エラー：{e}")

        finally:
            # 次へは UI の Next ボタンに任せる（UI側の on_next が new_question() を呼ぶ想定）
            if hasattr(self.ui, "show_next_button"):
                self.ui.show_next_button()

    # =========================
    # 問題生成（JUEGO OR）
    # =========================
    def _generate_juego_open_raise_problem(self) -> OpenRaiseProblemContext:
        card1, card2 = random.sample(self.deck, 2)
        position = random.choice(["EP", "MP", "CO", "BTN"])
        loose = random.choice([True, False])
        open_size = 2.5 if position == "BTN" else 3.0

        hand_key = self._to_hand_key(card1, card2)

        return OpenRaiseProblemContext(
            hole_cards=(card1, card2),
            position=position,
            open_size_bb=open_size,
            loose_player_exists=loose,
            excel_hand_key=hand_key,
            excel_position_key=position,
        )

    def _to_hand_key(self, c1: str, c2: str) -> str:
        r1, s1 = c1[0], c1[1]
        r2, s2 = c2[0], c2[1]

        ranks = "AKQJT98765432"
        if ranks.index(r1) > ranks.index(r2):
            r1, r2 = r2, r1
            s1, s2 = s2, s1

        if r1 == r2:
            return r1 + r2
        if s1 == s2:
            return r1 + r2 + "s"
        return r1 + r2 + "o"
