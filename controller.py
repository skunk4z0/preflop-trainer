import itertools
import random
import sys
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Tuple, Any


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
    # 内部ログ（print が見えない環境でも UI に出す）
    # =========================
    def _log(self, msg: str) -> None:
        try:
            print(msg, flush=True)
            try:
                sys.stdout.flush()
            except Exception:
                pass
        except Exception:
            pass

        # UI にも出す（最低限、見える）
        try:
            if hasattr(self.ui, "show_text"):
                self.ui.show_text(msg)
        except Exception:
            pass

    # =========================
    # 開始（メニュー等から呼ぶ）
    # =========================
    def start_yokosawa_open(self):
        self._log("[CTRL] start_yokosawa_open clicked")
        self.problem_type = ProblemType.YOKOSAWA_OPEN
        self.new_question()

    def start_juego_beginner(self):
        self._log("[CTRL] start_juego_beginner clicked")
        self.problem_type = ProblemType.JUEGO_OR
        self.new_question()

    # =========================
    # 新しい問題
    # =========================
    def new_question(self):
        self._log(f"[CTRL] new_question called. problem_type={self.problem_type}")

        # Next は「回答後に表示」したいので、問題生成時点では隠す
        if hasattr(self.ui, "hide_next_button"):
            try:
                self.ui.hide_next_button()
            except Exception as e:
                self._log(f"[CTRL] hide_next_button failed: {e}")

        if self.problem_type == ProblemType.YOKOSAWA_OPEN:
            hole = tuple(random.sample(self.deck, 2))
            self.ui.deal_cards(hole)
            self.ui.show_text("【ヨコサワ式】オープン判断。あなたのアクションは？")
            return

        if self.problem_type == ProblemType.JUEGO_OR:
            self.context = self._generate_juego_open_raise_problem()
            self.ui.deal_cards(self.context.hole_cards)

            # UI 仕様に合わせて統一：set_hand_pos
            if hasattr(self.ui, "set_hand_pos"):
                self.ui.set_hand_pos(
                    hand=self.context.excel_hand_key,
                    pos=self.context.position,
                )

            # ルース時だけ文言を変える（判定タグは表示しない）
            extra = "（相手はルース）" if self.context.loose_player_exists else ""

            self.ui.show_text(
                f"【JUEGO】オープンレイズ判断｜"
                f"Pos: {self.context.position}｜"
                f"{self.context.open_size_bb}BB"
                f"{extra}"
            )
            return

        # モード未選択など
        self.ui.show_text("モードを選択してください")

    # =========================
    # 回答
    # =========================
    def submit(self, hand: Optional[str] = None, pos: Optional[str] = None, user_action: Optional[str] = None):
        self._log(f">>> SUBMIT CALLED hand={hand} pos={pos} user_action={user_action}")

        try:
            if self.problem_type is None:
                self.ui.show_text("モードを選択してください")
                return

            # UI から hand/pos を取れる設計なら補完（切り分け用）
            if (hand is None or pos is None) and hasattr(self.ui, "get_hand_pos"):
                try:
                    hp = self.ui.get_hand_pos()
                    if isinstance(hp, tuple) and len(hp) >= 2:
                        hand = hand or hp[0]
                        pos = pos or hp[1]
                    elif isinstance(hp, dict):
                        hand = hand or hp.get("hand")
                        pos = pos or hp.get("pos")
                except Exception as e:
                    self._log(f"[CTRL] get_hand_pos failed: {e}")

            # -------------------------
            # ヨコサワ式
            # -------------------------
            if self.problem_type == ProblemType.YOKOSAWA_OPEN:
                if self.yokosawa_judge is None:
                    raise RuntimeError("yokosawa_judge is not set")
                if hand is None or pos is None or user_action is None:
                    raise RuntimeError(f"Missing args for YOKOSAWA_OPEN: hand={hand}, pos={pos}, action={user_action}")

                result = self.yokosawa_judge.judge(pos=pos, hand=hand)
                is_correct = (user_action == getattr(result, "action", None))
                reason = getattr(result, "reason", "")

                self.ui.show_text(f"{'正解' if is_correct else '不正解'}：{reason}")
                return

            # -------------------------
            # JUEGO OR
            # -------------------------
            if self.problem_type == ProblemType.JUEGO_OR:
                if self.context is None:
                    raise RuntimeError("Context is missing")
                if user_action is None:
                    raise RuntimeError("user_action is missing")

                ctx = self.context

                self._log("[CTRL] about to call juego_judge.judge_or()")
                result = self.juego_judge.judge_or(
                    position=ctx.position,
                    hand=ctx.excel_hand_key,
                    user_action=user_action,
                    loose=ctx.loose_player_exists,
                )

                # debug 表示（既存仕様）
                debug_obj = getattr(result, "debug", None)
                self._log("=== JUEGO DEBUG ===")
                self._log(str(debug_obj) if debug_obj is not None else "NO_DEBUG")
                self._log("===================")

                is_correct = bool(getattr(result, "correct", False))
                reason = getattr(result, "reason", "")
                self.ui.show_text(f"{'正解' if is_correct else '不正解'}：{reason}")
                return

            # 万一ここに来たら
            self.ui.show_text("未対応のモードです")
            return

        except Exception as e:
            self.ui.show_text(f"内部エラー：{e}")
            self._log(f"[CTRL] Exception in submit: {e}")
            raise

        finally:
            # 次へは UI の Next ボタンに任せる
            if hasattr(self.ui, "show_next_button"):
                try:
                    self.ui.show_next_button()
                except Exception as e:
                    self._log(f"[CTRL] show_next_button failed: {e}")

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

        # 強いランクを先に（AKQ... が先）
        if ranks.index(r1) > ranks.index(r2):
            r1, r2 = r2, r1
            s1, s2 = s2, s1

        # ペア
        if r1 == r2:
            return r1 + r2

        # suited / offsuit
        if s1 == s2:
            return r1 + r2 + "s"
        return r1 + r2 + "o"
