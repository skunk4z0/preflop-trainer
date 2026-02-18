# core/generator.py
from __future__ import annotations

import itertools
import logging
import random
from typing import Optional

import config

from .models import Difficulty, GeneratedQuestion, OpenRaiseProblemContext, ProblemType


logger = logging.getLogger("poker_trainer.core.generator")


class JuegoProblemGenerator:
    """
    controller.py から「デッキ」「問題生成」「表示用文言/モード決定」を移植したもの。
    - UI 依存は禁止（Tkinter を知らない）
    - Repo 依存も持たない（positions など必要情報は init で注入）
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

        # main.py で repo.list_positions("CC_3BET") を渡す想定（=最終JSONのposキー）
        self._positions_3bet = positions_3bet or []

    # -------------------------
    # Public
    # -------------------------
    def generate(self, selected_kinds: list[str]) -> GeneratedQuestion:
        problem_type = self._pick_problem_type(selected_kinds)
        ctx = self._generate_context(problem_type)
        answer_mode = self._answer_mode(problem_type, ctx)
        header_text = self._header_text(problem_type, ctx)
        return GeneratedQuestion(
            problem_type=problem_type,
            ctx=ctx,
            answer_mode=answer_mode,
            header_text=header_text,
        )

    # 互換：旧Engineが next_question(difficulty) を呼ぶ前提のため残す
    def next_question(
        self,
        difficulty: Difficulty | None = None,
        selected_kinds: Optional[list[str]] = None,
    ) -> GeneratedQuestion:
        pool_state = "None" if selected_kinds is None else ("empty" if len(selected_kinds) == 0 else f"len={len(selected_kinds)}")
        logger.debug(
            "next_question: difficulty=%r selected_kinds=%r pool=%s",
            difficulty,
            selected_kinds,
            pool_state,
        )
        normalized_kinds = [str(k or "").strip().upper() for k in (selected_kinds or []) if str(k or "").strip()]
        normalized_pool_state = "empty" if not normalized_kinds else f"len={len(normalized_kinds)}"
        logger.debug(
            "next_question: normalized selected_kinds=%r pool=%s",
            normalized_kinds,
            normalized_pool_state,
        )
        if not normalized_kinds:
            difficulty_name = getattr(difficulty, "name", "") if difficulty is not None else ""
            fallback_kinds = [str(k).strip().upper() for k in config.kinds_for_difficulty(difficulty_name) if str(k).strip()]
            logger.debug(
                "next_question: config fallback difficulty_name=%r kinds=%r pool=%s",
                difficulty_name,
                fallback_kinds,
                "empty" if not fallback_kinds else f"len={len(fallback_kinds)}",
            )
            normalized_kinds = fallback_kinds or ["OR"]
            logger.debug(
                "next_question: final fallback kinds=%r pool=%s",
                normalized_kinds,
                "empty" if not normalized_kinds else f"len={len(normalized_kinds)}",
            )

        return self.generate(normalized_kinds)


    # -------------------------
    # Internal
    # -------------------------
    def _pick_problem_type(self, selected_kinds: list[str]) -> ProblemType:
        logger.debug("pick_problem_type: selected_kinds_in=%r", selected_kinds)
        kinds = [str(k or "").strip().upper() for k in selected_kinds if str(k or "").strip()]
        logger.debug(
            "pick_problem_type: normalized_candidates=%r state=%s",
            kinds,
            "empty" if not kinds else f"len={len(kinds)}",
        )
        if not kinds:
            logger.debug("pick_problem_type: candidates empty -> fallback JUEGO_OR")
            return ProblemType.JUEGO_OR
        kind = self._rng.choice(kinds)
        logger.debug("pick_problem_type: chosen_kind=%r", kind)
        return self._kind_to_problem_type(kind)

    @staticmethod
    def _kind_to_problem_type(kind: str) -> ProblemType:
        if kind == "OR":
            return ProblemType.JUEGO_OR
        if kind == "OR_SB":
            return ProblemType.JUEGO_OR_SB
        if kind in {"3BET", "CC_3BET"}:
            return ProblemType.JUEGO_3BET
        if kind == "ROL":
            return ProblemType.JUEGO_ROL
        return ProblemType.JUEGO_OR

    def _generate_context(self, problem_type: ProblemType) -> OpenRaiseProblemContext:
        if problem_type == ProblemType.JUEGO_OR:
            return self._generate_or_problem_beginner()
        if problem_type == ProblemType.JUEGO_OR_SB:
            return self._generate_or_sb_problem_intermediate()
        if problem_type == ProblemType.JUEGO_ROL:
            return self._generate_rol_problem()
        if problem_type == ProblemType.JUEGO_3BET:
            return self._generate_3bet_problem()

        # 想定外の fallback（安全に空コンテキスト）
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

        # 3BET系：repo.list_positions("CC_3BET") 等から注入される position を使う
        pos = self._rng.choice(self._positions_3bet) if self._positions_3bet else "BB_VS_SB"

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
            return "ROL"
        if problem_type == ProblemType.JUEGO_3BET:
            return "3BET"
        return "OR"

    def _header_text(self, problem_type: ProblemType, ctx: OpenRaiseProblemContext) -> str:
        if problem_type == ProblemType.JUEGO_OR:
            loose_msg = "｜ルースなplayerがいます" if ctx.loose_player_exists else ""
            return (
                "【JUEGO】オープンレイズ判断（OR）｜"
                f"Pos: {ctx.position}｜"
                f"{ctx.open_size_bb}BB"
                f"{loose_msg}"
            )

        if problem_type == ProblemType.JUEGO_OR_SB:
            return (
                "【JUEGO】SBオープン判断（OR_SB）｜"
                "Pos: SB｜"
                f"{ctx.open_size_bb}BB"
            )

        if problem_type == ProblemType.JUEGO_ROL:
            fish_msg = "｜ルースなplayerがいます" if ctx.loose_player_exists else ""
            return (
                "【JUEGO】リンプインへの対応（ROL）｜"
                f"Pos: {ctx.position}｜"
                f"Raise={ctx.open_size_bb}BB"
                f"{fish_msg}"
            )

        if problem_type == ProblemType.JUEGO_3BET:
            return "【JUEGO】3BET判断（簡易）｜" f"Pos: {ctx.position}"

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
