# controller.py
from __future__ import annotations

import logging
import traceback
from pathlib import Path
from typing import Any, Optional

from core.engine import PokerEngine, SubmitResult
from core.models import Difficulty, ProblemType, OpenRaiseProblemContext
from core.telemetry import Telemetry

logger = logging.getLogger("poker_trainer.controller")


class GameController:
    """
    UI(Tkinter) ⇄ core(engine) の配線役。

    Controllerの責務：
    - engine の開始/次問/submit を呼ぶ
    - engine の返り値（SubmitResult）に従って UI を更新する
    - 不正解時にだけ、参照レンジ表ポップアップを表示する（repo.get_range_grid_view を使用）
    - Telemetry の呼び出し（ログ保存の実体は core/telemetry.py）

    やらないこと：
    - 採点ロジック（= juego_judge の責務）
    - データアクセス（= repo の責務）
    """

    def __init__(self, ui, engine: PokerEngine, enable_debug: bool = False):
        self.ui = ui
        self.engine = engine
        self.enable_debug = bool(enable_debug)

        # telemetry用：直近の表示状態
        self._last_answer_mode: str = ""
        self._last_header_text: str = ""

        # 遅延生成（init差分を小さくする）
        self._telemetry_obj: Optional[Telemetry] = None

    # -------------------------
    # Small helpers
    # -------------------------
    def _ui_call(self, name: str, *args, **kwargs):
        fn = getattr(self.ui, name, None)
        if not callable(fn):
            return None
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            logger.warning("[CTRL] ui.%s failed: %s", name, e)
            if self.enable_debug:
                logger.debug("Traceback:\n%s", traceback.format_exc())
            return None

    def _telemetry(self) -> Telemetry:
        """
        controller は project_root を MyPokerApp/ として渡す（data/ の基準）。
        """
        if self._telemetry_obj is None:
            project_root = Path(__file__).resolve().parent
            self._telemetry_obj = Telemetry(project_root=project_root)
        return self._telemetry_obj

    def _safe_getattr(self, obj: Any, name: str, default: Any = None) -> Any:
        try:
            return getattr(obj, name, default)
        except Exception as e:
            logger.warning("[CTRL] failed to getattr(%r, %s): %s", obj, name, e)
            return default

    # -------------------------
    # Start / Reset
    # -------------------------
    def start_yokosawa_open(self) -> None:
        self.engine.start_yokosawa_open()
        self.new_question()

    def start_juego_beginner(self) -> None:
        self.engine.start_juego(Difficulty.BEGINNER)
        self.new_question()

    def start_juego_intermediate(self) -> None:
        self.engine.start_juego(Difficulty.INTERMEDIATE)
        self.new_question()

    def start_juego_advanced(self) -> None:
        self.engine.start_juego(Difficulty.ADVANCED)
        self.new_question()

    def reset_state(self) -> None:
        self.engine.reset_state()
        self._last_answer_mode = ""
        self._last_header_text = ""

    def _infer_problem_type_from_ctx(
        self,
        ctx: Any,
        answer_mode: str,
    ) -> Optional[ProblemType]:
        if ctx is None:
            return None
        am = str(answer_mode or "").upper()
        if am == "OR":
            return ProblemType.JUEGO_OR
        if am == "OR_SB":
            return ProblemType.JUEGO_OR_SB
        if am in {"3BET", "THREE_BET"}:
            return ProblemType.JUEGO_3BET
        if am.startswith("ROL"):
            return ProblemType.JUEGO_ROL

        pos = str(getattr(ctx, "position", "") or "").upper()
        limpers = int(getattr(ctx, "limpers", 0) or 0)
        if pos in {"BB_OOP", "BBVSSB"}:
            return ProblemType.JUEGO_ROL
        if limpers > 0:
            return ProblemType.JUEGO_ROL
        if pos in {"EP", "MP", "CO", "BTN"}:
            return ProblemType.JUEGO_OR
        if pos == "SB":
            return ProblemType.JUEGO_OR_SB
        return None

    def _extract_ctx(self, ret: Any) -> Any:
        return self._safe_getattr(ret, "ctx", None) or self._safe_getattr(self.engine, "context", None)

    def _extract_problem_type(self, ret: Any, ctx: Any) -> Optional[ProblemType]:
        ptype = self._safe_getattr(ret, "problem_type", None) or self._safe_getattr(self.engine, "current_problem", None)
        if ptype is not None:
            return ptype
        return self._infer_problem_type_from_ctx(
            ctx=ctx,
            answer_mode=str(self._safe_getattr(ret, "answer_mode", "") or ""),
        )

    def _resolve_answer_mode(self, ret: Any, problem_type: Optional[ProblemType], ctx: Any) -> str:
        answer_mode = str(self._safe_getattr(ret, "answer_mode", "") or "")
        if answer_mode:
            return answer_mode
        if problem_type == ProblemType.JUEGO_OR:
            return "OR"
        if problem_type == ProblemType.JUEGO_OR_SB:
            return "OR_SB"
        if problem_type == ProblemType.JUEGO_3BET:
            return "3BET"
        if problem_type == ProblemType.JUEGO_ROL:
            return "ROL"
        return "OR"

    def _resolve_header_text(self, ret: Any) -> str:
        header = (
            self._safe_getattr(ret, "header_text", None)
            or self._safe_getattr(ret, "text", None)
            or ""
        )
        return str(header) if header else "次の問題です。アクションを選択してください。"

    def _apply_context_to_ui(self, ctx: Any) -> None:
        if ctx is None:
            return
        hole_cards = self._safe_getattr(ctx, "hole_cards", None)
        if isinstance(hole_cards, (tuple, list)) and len(hole_cards) == 2:
            self._ui_call("deal_cards", tuple(hole_cards))
        hand = self._safe_getattr(ctx, "excel_hand_key", None)
        pos = self._safe_getattr(ctx, "position", None)
        if hand is not None or pos is not None:
            self._ui_call("set_hand_pos", hand=hand or "?", pos=pos or "?")

    # -------------------------
    # Next question
    # -------------------------
    def new_question(self) -> None:
        # 前回のレンジ表ポップアップが残っていたら閉じる
        self._ui_call("close_range_grid_popup")

        # 直前のロックやfollow-up UI残骸を掃除
        self._ui_call("unlock_all_answer_buttons")
        self._ui_call("hide_next_button")
        self._ui_call("hide_followup_size_buttons")

        # ヨコサワ（未実装扱い）
        if self.engine.current_problem == ProblemType.YOKOSAWA_OPEN:
            self._ui_call("show_text", "【ヨコサワ式】オープンレイズ問題（未実装）")
            return

        if self.engine.difficulty is None:
            self._ui_call("show_text", "難易度を選択してください（初級/中級/上級）")
            return

        try:
            ret = self.engine.new_question()
        except Exception as e:
            self._ui_call("show_text", f"内部エラー：問題生成に失敗しました: {e}")
            logger.error("[CTRL] engine.new_question failed: %s", e, exc_info=True)
            return

        # 1) normalize return payload (GeneratedQuestion / SubmitResult 両対応)
        ctx = self._extract_ctx(ret)
        problem_type = self._extract_problem_type(ret, ctx)
        self._last_answer_mode = self._resolve_answer_mode(ret, problem_type, ctx)
        self._last_header_text = self._resolve_header_text(ret)

        # 2) apply normalized data to UI
        self._apply_context_to_ui(ctx)
        self._ui_call("set_answer_mode", self._last_answer_mode)
        self._ui_call("show_text", self._last_header_text)

        # Telemetry: question_shown
        try:
            if ctx is not None:
                self._telemetry().on_question_shown(
                    engine=self.engine,
                    ctx=ctx,
                    answer_mode=self._last_answer_mode,
                    header_text=self._last_header_text,
                )
        except Exception as e:
            logger.warning("[CTRL] telemetry question_shown failed: %s", e, exc_info=True)

    # -------------------------
    # Submit
    # -------------------------
    def submit(self, user_action: Optional[str] = None) -> None:
        try:
            res: SubmitResult = self.engine.submit(user_action)
        except Exception as e:
            self._ui_call("show_text", f"内部エラー：submitで例外が発生しました: {e}")
            logger.error("[CTRL] engine.submit failed: %s", e, exc_info=True)
            return

        if res is None:
            self._ui_call("show_text", "[BUG] engine.submit() returned None. Check engine.submit() return paths.")
            return

        # Telemetry: answer_submitted（follow-upも含めて記録）
        try:
            ctx = getattr(self.engine, "context", None)
            if ctx is not None:
                self._telemetry().on_answer_submitted(
                    engine=self.engine,
                    ctx=ctx,
                    answer_mode=self._last_answer_mode,
                    user_action=user_action or "",
                    res=res,
                )
        except Exception as e:
            logger.warning("[CTRL] telemetry answer_submitted failed: %s", e, exc_info=True)

        # 1) 結果テキスト
        self._ui_call("show_text", res.text)

        # 2) follow-up UIの掃除（必要なときだけ）
        if getattr(res, "hide_followup_buttons", False):
            self._ui_call("hide_followup_size_buttons")

        # 3) follow-up 表示が最優先（このとき Next は出さない）
        if getattr(res, "show_followup_buttons", False):
            self._ui_call("hide_next_button")
            choices = res.followup_choices or [2, 2.25, 2.5, 3]
            self._ui_call(
                "show_followup_size_buttons",
                choices=choices,
                prompt=res.followup_prompt,
            )
            return

        # 4) Next表示
        if getattr(res, "show_next_button", False):
            self._ui_call("show_next_button")
        else:
            self._ui_call("hide_next_button")

        # 5) 不正解ならレンジ表（follow-up不正解も含む）
        if res.is_correct is False and self.engine.context is not None:
            jr = res.judge_result
            self._try_show_range_grid_on_incorrect(
                ctx=self.engine.context,
                judge_result=jr,
                override_reason=res.text,
            )

    # -------------------------
    # Range popup (incorrect only)
    # -------------------------
    def _try_show_range_grid_on_incorrect(
        self,
        ctx: OpenRaiseProblemContext,
        judge_result: Any,
        override_reason: str | None = None,
    ) -> None:
        """
        不正解時にだけ、参照しているレンジ表をポップアップ表示する。
        follow-up不正解のときは override_reason に res.text を渡す。
        """
        try:
            if not hasattr(self.ui, "show_range_grid_popup"):
                return
            if judge_result is None:
                return

            dbg = getattr(judge_result, "debug", None) or {}
            if not isinstance(dbg, dict):
                dbg = {}

            # kind / pos（最優先はdebug）
            kind = (dbg.get("kind") or "").strip()
            pos = (dbg.get("position") or dbg.get("pos") or "").strip()

            # debugに無い場合の復元（最低限）
            if not kind:
                cp = self.engine.current_problem
                if cp == ProblemType.JUEGO_OR:
                    kind = "OR"
                elif cp == ProblemType.JUEGO_OR_SB:
                    kind = "OR_SB"
                elif cp == ProblemType.JUEGO_ROL:
                    kind = "ROL"
                elif cp == ProblemType.JUEGO_3BET:
                    kind = "CC_3BET"  # repo側のkindと揃える
            if not pos:
                cp = self.engine.current_problem
                if cp == ProblemType.JUEGO_OR_SB:
                    pos = "SB"
                else:
                    pos = ctx.excel_position_key or ctx.position

            if not kind or not pos:
                return

            # repo（ここは engine -> judge -> repo が正ルート）
            repo = getattr(self.engine.juego_judge, "repo", None)
            if repo is None or not hasattr(repo, "get_range_grid_view"):
                return

            grid_view = repo.get_range_grid_view(kind, pos)

            highlight_rc = None
            if hasattr(repo, "hand_to_grid_rc"):
                c1, c2 = ctx.hole_cards
                highlight_rc = repo.hand_to_grid_rc(c1, c2)

            expected = str(dbg.get("expected_action") or dbg.get("expected") or "").strip()
            exp_size = dbg.get("expected_raise_size_bb", None)

            info = ""
            if expected:
                info = f"Expected: {expected}"
                if isinstance(exp_size, (int, float)):
                    info += f"  (size={float(exp_size)}bb)"
                info += "\n"

            reason = (override_reason or str(getattr(judge_result, "reason", "") or "")).strip()
            if reason:
                info += reason

            sheet_name = getattr(grid_view, "sheet_name", "")
            title = f"{grid_view.kind} / {grid_view.pos}" + (f"  [sheet={sheet_name}]" if sheet_name else "")

            self._ui_call(
                "show_range_grid_popup",
                title=title,
                grid_cells=grid_view.cells,
                highlight_rc=highlight_rc,
                info_text=info,
                on_next=self.new_question,
            )

        except Exception as e:
            logger.warning("[CTRL] show_range_grid_popup failed: %s", e)
            if self.enable_debug:
                logger.debug("Traceback:\n%s", traceback.format_exc())
