# core/generator.py
from __future__ import annotations

import itertools
import random
from typing import Optional

from .models import Difficulty, GeneratedQuestion, OpenRaiseProblemContext, ProblemType


class JuegoProblemGenerator:
    """
    controller.py から「デッキ」「プール」「問題生成」「表示用文言/モード決定」を移植する。
    UI 依存は禁止（Tkinterを知らない）。
    """

    def __init__(
        self,
        rng: Optional[random.Random] = None,
        positions_3bet: Optional[list[str]] = None,
    ) -> None:
        self._rng = rng or random.Random()

        suits = ["s", "h", "d", "c"]
        ranks = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"]
        self._deck = [r + s for r, s in itertools.product(ranks, suits)]

        self._positions_3bet = positions_3bet or []

        self._pool_beginner = [ProblemType.JUEGO_OR]
        self._pool_intermediate = [ProblemType.JUEGO_OR_SB, ProblemType.JUEGO_3BET]
        self._pool_advanced = [ProblemType.JUEGO_ROL]


    # -------------------------
    # Public
    # -------------------------
    def generate(self, difficulty: Difficulty) -> GeneratedQuestion:
        problem_type = self._pick_problem_type(difficulty)
        ctx = self._generate_context(problem_type)
        answer_mode = self._answer_mode(problem_type, ctx)
        header_text = self._header_text(problem_type, ctx)
        return GeneratedQuestion(problem_type=problem_type, ctx=ctx, answer_mode=answer_mode, header_text=header_text)

    # -------------------------
    # Internal
    # -------------------------
    def _pick_problem_type(self, difficulty: Difficulty) -> ProblemType:
        if difficulty == Difficulty.BEGINNER:
            pool = self._pool_beginner
        elif difficulty == Difficulty.INTERMEDIATE:
            pool = self._pool_intermediate
        else:
            pool = self._pool_advanced

        if not pool:
            return ProblemType.JUEGO_BB_ISO  # ダミー（未使用想定）
        return self._rng.choice(pool)

    def _generate_context(self, problem_type: ProblemType) -> OpenRaiseProblemContext:
        if problem_type == ProblemType.JUEGO_OR:
            return self._generate_or_problem_beginner()
        if problem_type == ProblemType.JUEGO_OR_SB:
            return self._generate_or_sb_problem_intermediate()
        if problem_type == ProblemType.JUEGO_ROL:
            return self._generate_rol_problem()
        if problem_type == ProblemType.JUEGO_3BET:
            return self._generate_3bet_problem()


        card1, card2 = self._rng.sample(self._deck, 2)
        hand_key = self.to_hand_key(card1, card2)
        return OpenRaiseProblemContext(
            hole_cards=(card1, card2),
            position="",
            open_size_bb=0.0,
            loose_player_exists=False,
            excel_hand_key=hand_key,
            excel_position_key="",
            limpers=0,
        )

    def _generate_or_problem_beginner(self) -> OpenRaiseProblemContext:
        card1, card2 = self._rng.sample(self._deck, 2)
        position = self._rng.choice(["EP", "MP", "CO", "BTN"])
        loose = self._rng.choice([True, False])

        open_size = 2.5 if position == "BTN" else 3.0
        hand_key = self.to_hand_key(card1, card2)

        return OpenRaiseProblemContext(
            hole_cards=(card1, card2),
            position=position,
            open_size_bb=open_size,
            loose_player_exists=loose,
            excel_hand_key=hand_key,
            excel_position_key=position,
            limpers=0,
        )

    def _generate_or_sb_problem_intermediate(self) -> OpenRaiseProblemContext:
        card1, card2 = self._rng.sample(self._deck, 2)
        hand_key = self.to_hand_key(card1, card2)

        return OpenRaiseProblemContext(
            hole_cards=(card1, card2),
            position="SB",
            open_size_bb=3.0,
            loose_player_exists=False,
            excel_hand_key=hand_key,
            excel_position_key="SB",
            limpers=0,
        )

    def _generate_3bet_problem(self) -> OpenRaiseProblemContext:
        card1, card2 = self._rng.sample(self._deck, 2)
        hand_key = self.to_hand_key(card1, card2)

        # Excelのpos文字列に合わせる：repo.list_positions("3BET") から注入する想定
        pos = self._rng.choice(self._positions_3bet) if self._positions_3bet else "BB vs SB"

        return OpenRaiseProblemContext(
            hole_cards=(card1, card2),
            position=pos,
            open_size_bb=0.0,
            loose_player_exists=False,
            excel_hand_key=hand_key,
            excel_position_key=pos,
            limpers=0,
        )


    def _generate_rol_problem(self) -> OpenRaiseProblemContext:
        card1, card2 = self._rng.sample(self._deck, 2)
        position = self._rng.choice(["MP", "CO", "BTN", "SB", "BB_OOP", "BBvsSB"])
        loose = self._rng.choice([True, False])  # ROLvsFISH のため
        raise_size = 4.0 if position == "BBvsSB" else 5.0
        hand_key = self.to_hand_key(card1, card2)

        return OpenRaiseProblemContext(
            hole_cards=(card1, card2),
            position=position,
            open_size_bb=raise_size,
            loose_player_exists=loose,
            excel_hand_key=hand_key,
            excel_position_key=position,
            limpers=1,
        )

    def _answer_mode(self, problem_type: ProblemType, ctx: OpenRaiseProblemContext) -> str:
        if problem_type == ProblemType.JUEGO_OR:
            return "OR"
        if problem_type == ProblemType.JUEGO_OR_SB:
            return "OR_SB"
        if problem_type == ProblemType.JUEGO_ROL:
            if ctx.position == "BBvsSB":
                return "ROL_BBVS_SB"
            if ctx.position == "BB_OOP":
                return "ROL_BB_OOP"
            return "ROL_NONBB"
        if problem_type == ProblemType.JUEGO_3BET:
            return "3BET"
        return "OR"

    def _header_text(self, problem_type: ProblemType, ctx: OpenRaiseProblemContext) -> str:
        if problem_type == ProblemType.JUEGO_OR:
            loose_msg = "｜ルースなplayerがいます" if ctx.loose_player_exists else ""
            return (
                "【JUEGO 初級】オープンレイズ判断（OR）｜"
                f"Pos: {ctx.position}｜"
                f"{ctx.open_size_bb}BB"
                f"{loose_msg}"
            )

        if problem_type == ProblemType.JUEGO_OR_SB:
            return (
                "【JUEGO 中級】SBオープン判断（OR_SB）｜"
                "Pos: SB｜"
                f"{ctx.open_size_bb}BB"
            )

        if problem_type == ProblemType.JUEGO_ROL:
            fish_msg = "｜ルースなplayerがいます" if ctx.loose_player_exists else ""
            return (
                "【JUEGO 上級】リンプインへの対応（ROL）｜"
                f"Pos: {ctx.position}｜"
                f"Raise={ctx.open_size_bb}BB"
                f"{fish_msg}"
            )
        if problem_type == ProblemType.JUEGO_3BET:
            return (
                "【JUEGO 中級】3BET判断（簡易）｜"
                f"Pos: {ctx.position}"
            )    

        return "内部：未知の問題タイプです"

    # -------------------------
    # Utilities (pure)
    # -------------------------
    @staticmethod
    def to_hand_key(c1: str, c2: str) -> str:
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

    @staticmethod
    def parse_limp_tag_to_max_bb(tag: str) -> Optional[float]:
        if not tag:
            return None
        t = str(tag).strip()
        if not t.upper().startswith("LIMPCX"):
            return None

        body = t[len("LimpCx") :].strip()
        if body.lower().endswith("o"):
            body = body[:-1]

        try:
            return float(body)
        except (ValueError, TypeError):
            return None
