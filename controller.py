# controller.py
from __future__ import annotations

import itertools
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Optional, Tuple


class ProblemType(Enum):
    YOKOSAWA_OPEN = auto()
    JUEGO_OR = auto()  # EP/MP/CO/BTN + SB(OR_SB) まで含めて扱う


@dataclass(frozen=True)
class OpenRaiseProblemContext:
    hole_cards: Tuple[str, str]         # 例: ("Ks","Jc")
    position: str                       # "EP"/"MP"/"CO"/"BTN"/"SB"
    open_size_bb: float                 # BTN=2.5, else=3.0（SBも3.0）
    loose_player_exists: bool           # True/False（SBでは現状未使用だが将来用に保持）
    excel_hand_key: str                 # 例: "AKs" / "AKo" / "AA"
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
    # 内部ログ（見える環境でだけ print、基本は UI 出力）
    # =========================
    def _log(self, msg: str) -> None:
        try:
            print(msg, flush=True)
        except Exception:
            pass

        try:
            if hasattr(self.ui, "show_text"):
                self.ui.show_text(msg)
        except Exception:
            pass

    # =========================
    # 開始（モード選択）
    # =========================
    def start_yokosawa_open(self) -> None:
        self.problem_type = ProblemType.YOKOSAWA_OPEN
        self.new_question()

    def start_juego_or(self) -> None:
        """
        JUEGO Open Raise（OR）を開始。
        出題対象は EP/MP/CO/BTN に加え、SB（OR_SB）も含む。
        """
        self.problem_type = ProblemType.JUEGO_OR
        self.new_question()

    # =========================
    # 次の問題
    # =========================
    def new_question(self) -> None:
        # 前の問題で表示された Next ボタンを、次の問題開始時に必ず隠す
        if hasattr(self.ui, "hide_next_button"):
            try:
                self.ui.hide_next_button()
            except Exception:
                pass

        if self.problem_type is None:
            self.ui.show_text("モードを選択してください")
            return

        if self.problem_type == ProblemType.YOKOSAWA_OPEN:
            self.context = None
            self.ui.show_text("【ヨコサワ式】オープンレイズ問題（未実装/既存実装に合わせてください）")
            return

        if self.problem_type == ProblemType.JUEGO_OR:
            self.context = self._generate_juego_open_raise_problem()

            # UI表示
            self.ui.deal_cards(self.context.hole_cards)

            if hasattr(self.ui, "set_hand_pos"):
                self.ui.set_hand_pos(
                    hand=self.context.excel_hand_key,
                    pos=self.context.position,
                )

            extra = "（相手はルース）" if self.context.loose_player_exists else ""

            # 表示文言（SB のときだけ明示）
            if self.context.position == "SB":
                title = "【JUEGO】SBオープン判断（OR_SB）｜"
            else:
                title = "【JUEGO】オープンレイズ判断（OR）｜"

            self.ui.show_text(
                f"{title}"
                f"Pos: {self.context.position}｜"
                f"{self.context.open_size_bb}BB"
                f"{extra}"
            )
            return

    # =========================
    # 回答
    # =========================
    def submit(self, user_action: Optional[str] = None) -> None:
        """
        UI からボタン押下で呼ばれる想定。
        user_action は "FOLD" / "RAISE" / "LIMP_CALL"
        """
        if self.problem_type is None:
            self.ui.show_text("モードを選択してください")
            return

        if user_action is None:
            self.ui.show_text("アクションが未指定です")
            return

        ua = (user_action or "").strip().upper()
        result: Any = None
        is_correct = False
        reason = ""

        try:
            # -------------------------
            # ヨコサワ式
            # -------------------------
            if self.problem_type == ProblemType.YOKOSAWA_OPEN:
                if self.yokosawa_judge is None:
                    raise RuntimeError("yokosawa_judge is not set")
                raise NotImplementedError("YOKOSAWA_OPEN submit is not wired yet")

            # -------------------------
            # JUEGO OR / OR_SB
            # -------------------------
            if self.problem_type == ProblemType.JUEGO_OR:
                if self.context is None:
                    raise RuntimeError("Context is missing")

                ctx = self.context

                # ★SB は OR_SB に分岐
                if ctx.position == "SB":
                    result = self.juego_judge.judge_or_sb(
                        position=ctx.position,
                        hand=ctx.excel_hand_key,
                        user_action=ua,
                        loose=ctx.loose_player_exists,
                    )
                else:
                    result = self.juego_judge.judge_or(
                        position=ctx.position,
                        hand=ctx.excel_hand_key,
                        user_action=ua,
                        loose=ctx.loose_player_exists,
                    )

                is_correct = bool(getattr(result, "correct", False))
                reason = str(getattr(result, "reason", ""))

                dbg = getattr(result, "debug", None)
                if dbg is not None:
                    self._log("=== JUEGO DEBUG ===")
                    self._log(str(dbg))
                    self._log("===================")

        except Exception as e:
            self.ui.show_text(f"内部エラー：{e}")
            self._log(f"[CTRL] Exception in submit: {e}")
            return

        finally:
            if hasattr(self.ui, "show_next_button"):
                try:
                    self.ui.show_next_button()
                except Exception as e:
                    self._log(f"[CTRL] show_next_button failed: {e}")

        if is_correct:
            self.ui.show_text(f"正解：{reason}")
        else:
            self.ui.show_text(f"不正解：{reason}")

    # =========================
    # 問題生成（JUEGO OR + SB）
    # =========================
    def _generate_juego_open_raise_problem(self) -> OpenRaiseProblemContext:
        card1, card2 = random.sample(self.deck, 2)

        # ★SB を追加
        position = random.choice(["EP", "MP", "CO", "BTN", "SB"])

        loose = random.choice([True, False])

        # open size：BTN=2.5、それ以外=3.0（SBも表が3BB想定なので3.0）
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
        """
        2枚カード（例 "Ks","Jc"）を "AA" / "AKs" / "AKo" 形式に変換。
        """
        r1, s1 = c1[0].upper(), c1[1].lower()
        r2, s2 = c2[0].upper(), c2[1].lower()

        order = "AKQJT98765432"
        if order.index(r1) > order.index(r2):
            r1, r2 = r2, r1
            s1, s2 = s2, s1

        if r1 == r2:
            return r1 + r2

        suited = (s1 == s2)
        return r1 + r2 + ("s" if suited else "o")
