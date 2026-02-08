# controller.py
from __future__ import annotations

import logging
import traceback
from types import SimpleNamespace
from typing import Any, Optional

from pathlib import Path
from core.telemetry import Telemetry

from core.engine import PokerEngine, SubmitResult
from core.models import Difficulty, ProblemType, OpenRaiseProblemContext

logger = logging.getLogger("poker_trainer.controller")


class GameController:
    """
    UI(Tkinter) ⇄ core(engine) の配線役。
    - 状態は engine が持つ
    - controller は UI更新 + レンジ表ポップアップ描画
    """

    def __init__(self, ui, engine: PokerEngine, enable_debug: bool = False):
        self.ui = ui
        self.engine = engine
        self.enable_debug = bool(enable_debug)

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
        # __init__ を触らずに遅延生成（最小差分）
        if not hasattr(self, "_telemetry_obj") or self._telemetry_obj is None:
            # controller.py がプロジェクト直下にある前提で project_root を推定
            project_root = Path(__file__).resolve().parent
            self._telemetry_obj = Telemetry(project_root=project_root)
        return self._telemetry_obj
        


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

        # -------------------------
        # Next question
        # -------------------------
    def new_question(self) -> None:
        self._ui_call("close_range_grid_popup")
        self._ui_call("unlock_all_answer_buttons")

        self._ui_call("hide_next_button")
        self._ui_call("hide_followup_size_buttons")

        if self.engine.current_problem == ProblemType.YOKOSAWA_OPEN:
            self.ui.show_text("【ヨコサワ式】オープンレイズ問題（未実装/既存実装に合わせてください）")
            return

        if self.engine.difficulty is None:
            self.ui.show_text("難易度を選択してください（初級/中級/上級）")
            return

        try:
            generated = self.engine.new_question()
        except Exception as e:
            self.ui.show_text(f"内部エラー：問題生成に失敗しました: {e}")
            logger.error("[CTRL] engine.new_question failed: %s", e, exc_info=True)
            return

        # ★ここに追加：表示ラベルは “生成結果” に従う（最も安全）
        mode = getattr(generated, "answer_mode", "")     

        self._ui_call("set_answer_mode", getattr(generated, "answer_mode", ""))

        ctx = generated.ctx
        self._ui_call("deal_cards", ctx.hole_cards)
        self._ui_call("set_hand_pos", hand=ctx.excel_hand_key, pos=ctx.position)

        self.ui.show_text(generated.header_text)

        # --- Telemetry: question_shown ---
        try:
            self._telemetry().on_question_shown(
                engine=self.engine,
                ctx=ctx,
                answer_mode=getattr(generated, "answer_mode", "") or "",
                header_text=generated.header_text or "",
            )
        except Exception as e:
            logger.warning("[CTRL] telemetry question_shown failed: %s", e, exc_info=True)

        # -------------------------
        # Submit
        # -------------------------
    def submit(self, user_action: Optional[str] = None) -> None:
        res: SubmitResult = self.engine.submit(user_action)
        # --- Telemetry: answer_submitted ---
        try:
            ctx = getattr(self.engine, "context", None)  # 直近問題のctx（あなたの設計だとここが正）
            if ctx is not None:
                # answer_mode は「直近表示のgenerated」から取るのが理想だが、
                # 最小実装として engine 側/ctx 側に無いなら空でOK
                answer_mode = ""
                self._telemetry().on_answer_submitted(
                    engine=self.engine,
                    ctx=ctx,
                    answer_mode=answer_mode,
                    user_action=user_action or "",
                    res=res,
                )
        except Exception as e:
            logger.warning("[CTRL] telemetry answer_submitted failed: %s", e, exc_info=True)


        if res is None:
            self.ui.show_text("[BUG] engine.submit() returned None. Check engine.submit() return paths.")
            return

        # 1) 結果テキスト
        self.ui.show_text(res.text)

        # 2) follow-up UI の掃除（必要なときだけ）
        if getattr(res, "hide_followup_buttons", False):
            self._ui_call("hide_followup_size_buttons")

        # 3) follow-up 表示が最優先：このとき Next は必ず隠して終了
        if getattr(res, "show_followup_buttons", False):
            self._ui_call("hide_next_button")
            choices = res.followup_choices or [2, 2.25, 2.5, 3]
            self._ui_call(
                "show_followup_size_buttons",
                choices=choices,
                prompt=res.followup_prompt,
            )
            return

        # 4) Next
        if getattr(res, "show_next_button", False):
            self._ui_call("show_next_button")
        else:
            self._ui_call("hide_next_button")

        # 5) 不正解ならレンジ表（follow-up不正解も含む）
        if res.is_correct is False and self.engine.context is not None:
            jr = res.judge_result
            if jr is None:
                jr = SimpleNamespace(reason=res.text, debug={})

            if getattr(jr, "correct", None) is True:
                dbg = getattr(jr, "debug", None) or {}
                jr = SimpleNamespace(reason=getattr(jr, "reason", ""), debug=dbg)

            self._try_show_range_grid_on_incorrect(
                ctx=self.engine.context,
                result=jr,
                override_reason=res.text,
            )
        # -------------------------
        # Range popup
        # -------------------------
    def _try_show_range_grid_on_incorrect(self, ctx: OpenRaiseProblemContext, result: Any, override_reason: str | None = None) -> None:
        """
        不正解時にだけ、参照しているレンジ表をポップアップで表示する。
        follow-up不正解のときは override_reason に follow-up文言を渡す。
        """
        try:
            if not hasattr(self.ui, "show_range_grid_popup"):
                return

            dbg = getattr(result, "debug", None) or {}

            kind = (dbg.get("kind") or "").strip()
            pos = (dbg.get("position") or dbg.get("pos") or "").strip()

            # debug に無ければ engine.current_problem / ctx から復元
            if not kind:
                cp = self.engine.current_problem
                if cp == ProblemType.JUEGO_OR:
                    kind = "OR"
                elif cp == ProblemType.JUEGO_OR_SB:
                    kind = "OR_SB"
                elif cp == ProblemType.JUEGO_ROL:
                    kind = "ROL"

            if not pos:
                cp = self.engine.current_problem
                if cp == ProblemType.JUEGO_OR_SB:
                    pos = "SB"
                else:
                    pos = ctx.excel_position_key or ctx.position

            if not kind or not pos:
                return

            # repo の取り出し（ui.repo / judge.repo / judge._repo）
            repo = None
            if hasattr(self.ui, "repo"):
                repo = getattr(self.ui, "repo")
            if repo is None and hasattr(self.engine.juego_judge, "repo"):
                repo = getattr(self.engine.juego_judge, "repo")
            if repo is None and hasattr(self.engine.juego_judge, "_repo"):
                repo = getattr(self.engine.juego_judge, "_repo")

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

            # reason（follow-up不正解なら差し替える）
            reason = (override_reason or str(getattr(result, "reason", "") or "")).strip()
            if reason:
                info += reason

            title = f"{grid_view.kind} / {grid_view.pos}  [sheet={grid_view.sheet_name}]"

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




