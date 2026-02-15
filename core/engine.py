# core/engine.py
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from .followup_policy import FOLLOWUP_CHOICES, FOLLOWUP_PROMPT, maybe_create_followup
from .models import Difficulty, ProblemType, OpenRaiseProblemContext, SBLimpFollowUpContext

logger = logging.getLogger("poker_trainer.core.engine")


@dataclass(frozen=True)
class SubmitResult:
    """
    Controller(UI) に返す「UI操作の指示」＋「必要なら judge 結果」。
    UIはcoreに置かないので、ここは “旗” と “文言” だけ返す。
    """
    text: str
    is_correct: Optional[bool]          # followup開始など「採点未確定」は None
    show_next_button: bool
    show_followup_buttons: bool
    hide_followup_buttons: bool
    judge_result: Optional[Any] = None  # レンジ表ポップアップ等に使う

    followup_choices: Optional[list[float]] = None
    followup_prompt: Optional[str] = None


class PokerEngine:
    """
    core の状態と状態遷移を持つ。
    - UI(Tkinter)は知らない
    - controller は Adapter として engine を呼び、返り値に従ってUI更新する
    """

    def __init__(self, generator, juego_judge, enable_debug: bool = False) -> None:
        self.generator = generator
        self.juego_judge = juego_judge
        self.enable_debug = bool(enable_debug)

        self.difficulty: Optional[Difficulty] = None
        self.current_problem: Optional[ProblemType] = None
        self.context: Optional[OpenRaiseProblemContext] = None

        # follow-up（OR_SBのLIMP_CALLの2段目）
        self.followup: Optional[SBLimpFollowUpContext] = None

        # follow-up不正解時にレンジ表を出す用
        self._last_judge_result: Optional[Any] = None

    def _log(self, msg: str) -> None:
        if self.enable_debug:
            logger.info(msg)

    # -------------------------
    # Start / Reset
    # -------------------------
    def start_yokosawa_open(self) -> None:
        self.current_problem = ProblemType.YOKOSAWA_OPEN
        self.context = None
        self.followup = None
        self._last_judge_result = None

    def start_juego(self, difficulty: Difficulty) -> None:
        self.difficulty = difficulty
        self.current_problem = None
        self.context = None
        self.followup = None
        self._last_judge_result = None

    def reset_state(self) -> None:
        self.difficulty = None
        self.current_problem = None
        self.context = None
        self.followup = None
        self._last_judge_result = None

    # -------------------------
    # Next question
    # -------------------------
    def new_question(self) -> SubmitResult:
        if self.difficulty is None:
            return SubmitResult(
                text="難易度を選択してください（初級/中級/上級）",
                is_correct=None,
                show_next_button=False,
                show_followup_buttons=False,
                hide_followup_buttons=False,
                judge_result=None,
            )

        q = self.generator.next_question(self.difficulty)
        self.current_problem = q.problem_type
        self.context = q.ctx
        self.followup = None

        return SubmitResult(
            text=q.header_text,
            is_correct=None,
            show_next_button=False,
            show_followup_buttons=False,
            hide_followup_buttons=True,
            judge_result=None,
        )

    # -------------------------
    # Submit
    # -------------------------
    def submit(self, user_action: Optional[str]) -> SubmitResult:
        if user_action is None:
            return SubmitResult(
                text="アクションが未指定です",
                is_correct=None,
                show_next_button=False,
                show_followup_buttons=False,
                hide_followup_buttons=False,
                judge_result=None,
            )

        ua_raw = str(user_action).strip().upper()
        self._log(f"[ENGINE] submit qtype={self.current_problem} followup={'Y' if self.followup else 'N'} action={user_action!r}")

        # -------------------------
        # followup採点（2段目）
        # -------------------------
        if self.followup is not None:
            self._log(
                f"[ENGINE] followup-phase ENTER expected={self.followup.expected_max_bb} "
                f"tag={self.followup.source_tag} action={user_action!r}"
            )

            try:
                chosen = float(ua_raw)
            except ValueError:
                self._log(f"[ENGINE] followup-phase PARSE_FAIL ua_raw={ua_raw!r}")
                return SubmitResult(
                    text=f"数値を選択してください（2 / 2.25 / 2.5 / 3）。入力={ua_raw}",
                    is_correct=None,
                    show_next_button=False,
                    show_followup_buttons=True,
                    hide_followup_buttons=False,
                    judge_result=self._last_judge_result,
                    followup_choices=FOLLOWUP_CHOICES,
                    followup_prompt=FOLLOWUP_PROMPT,
                )

            expected = self.followup.expected_max_bb
            ok = (abs(chosen - expected) < 1e-9)
            src = self.followup.source_tag

            self._log(f"[ENGINE] followup-phase GRADE chosen={chosen} expected={expected} ok={ok}")

            self.followup = None

            msg = (
                f"正解：{expected}BBまでコール（元タグ: {src}）"
                if ok
                else f"不正解：正解は {expected}BB（あなた={chosen}BB、元タグ: {src}）"
            )

            return SubmitResult(
                text=msg,
                is_correct=ok,
                show_next_button=True,
                show_followup_buttons=False,
                hide_followup_buttons=True,
                judge_result=self._last_judge_result,
            )

        # -------------------------
        # 通常採点（1段目）
        # -------------------------
        if self.current_problem is None:
            return SubmitResult(
                text="難易度を選択してください（初級/中級/上級）",
                is_correct=None,
                show_next_button=False,
                show_followup_buttons=False,
                hide_followup_buttons=False,
                judge_result=None,
            )

        if self.context is None:
            return SubmitResult(
                text="内部エラー：Context is missing",
                is_correct=None,
                show_next_button=False,
                show_followup_buttons=False,
                hide_followup_buttons=False,
                judge_result=None,
            )

        if self.current_problem == ProblemType.JUEGO_ROL:
            allowed = {"FOLD", "RAISE", "CALL", "CHECK", "LIMP_CALL"}  # 互換
        elif self.current_problem == ProblemType.JUEGO_3BET:
            allowed = {"FOLD", "RAISE", "CALL"}
        else:
            allowed = {"FOLD", "RAISE", "LIMP_CALL"}

        if ua_raw not in allowed:
            return SubmitResult(
                text=f"不正なアクションです: {ua_raw}",
                is_correct=None,
                show_next_button=False,
                show_followup_buttons=False,
                hide_followup_buttons=False,
                judge_result=None,
            )

        ua = "CALL" if (self.current_problem == ProblemType.JUEGO_ROL and ua_raw == "LIMP_CALL") else ua_raw

        ctx = self.context
        result: Any

        try:
            if self.current_problem == ProblemType.JUEGO_OR:
                result = self.juego_judge.judge_or(
                    position=ctx.position,
                    hand=ctx.excel_hand_key,
                    user_action=ua,
                    loose=ctx.loose_player_exists,
                )

            elif self.current_problem == ProblemType.JUEGO_OR_SB:
                result = self.juego_judge.judge_or_sb(
                    position="SB",
                    hand=ctx.excel_hand_key,
                    user_action=ua,
                    loose=False,
                )

            elif self.current_problem == ProblemType.JUEGO_3BET:
                result = self.juego_judge.judge_3bet(
                    position=ctx.position,
                    hand=ctx.excel_hand_key,
                    user_action=ua,
                    loose=ctx.loose_player_exists,
                )

            elif self.current_problem == ProblemType.JUEGO_ROL:
                if not hasattr(self.juego_judge, "judge_rol"):
                    return SubmitResult(
                        text="内部エラー：judge_rol が未実装です（juego_judge.py に追加してください）",
                        is_correct=None,
                        show_next_button=False,
                        show_followup_buttons=False,
                        hide_followup_buttons=False,
                        judge_result=None,
                    )

                result = self.juego_judge.judge_rol(
                    position=ctx.position,
                    hand=ctx.excel_hand_key,
                    user_action=ua,
                    loose=ctx.loose_player_exists,
                )

            else:
                return SubmitResult(
                    text="内部：未知の問題タイプです",
                    is_correct=None,
                    show_next_button=False,
                    show_followup_buttons=False,
                    hide_followup_buttons=False,
                    judge_result=None,
                )

        except Exception as e:
            logger.error("[ENGINE] Exception in submit: %s", e, exc_info=True)
            return SubmitResult(
                text=f"内部エラー：{e}",
                is_correct=None,
                show_next_button=False,
                show_followup_buttons=False,
                hide_followup_buttons=False,
                judge_result=None,
            )

        self._last_judge_result = result

        is_correct = bool(getattr(result, "correct", False))
        reason = str(getattr(result, "reason", ""))

        dbg = getattr(result, "debug", None)
        if dbg is not None and (not is_correct):
            self._log("=== JUEGO DEBUG ===")
            self._log(str(dbg))
            self._log("===================")

        # -------------------------
        # follow-up 開始判定（policy集約）
        # -------------------------
        tag_upper = ""
        expected_action = ""
        if isinstance(dbg, dict):
            tag_upper = str(dbg.get("tag_upper") or "")
            expected_action = str(dbg.get("expected_action") or dbg.get("correct_action") or "")

        followup_ctx = maybe_create_followup(
            problem_kind=self.current_problem,
            tag_upper=tag_upper,
            expected_action=expected_action,
            stage1_correct=is_correct,
        )
        if followup_ctx is not None:
            self.followup = SBLimpFollowUpContext(
                hand_key=ctx.excel_hand_key,
                expected_max_bb=followup_ctx.expected_max_bb,
                source_tag=followup_ctx.source_tag,
            )
            return SubmitResult(
                text=(
                    "正解（リンプイン）。追加問題：\n"
                    "BBのオープンに対して、何BBまでコールしますか？"
                ),
                is_correct=None,
                show_next_button=False,
                show_followup_buttons=True,
                hide_followup_buttons=False,
                judge_result=result,
                followup_choices=FOLLOWUP_CHOICES,
                followup_prompt=FOLLOWUP_PROMPT,
            )

        msg = "正解！" if is_correct else f"不正解… {reason}"

        return SubmitResult(
            text=msg,
            is_correct=is_correct,
            show_next_button=True,
            show_followup_buttons=False,
            hide_followup_buttons=True,
            judge_result=result,
        )

