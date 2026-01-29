# controller.py
from __future__ import annotations

import itertools
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Optional, Tuple


class Difficulty(Enum):
    BEGINNER = auto()
    INTERMEDIATE = auto()
    ADVANCED = auto()


class ProblemType(Enum):
    YOKOSAWA_OPEN = auto()

    # JUEGO系（難易度で出題プールを作る）
    JUEGO_OR = auto()        # 初級：EP/MP/CO/BTN の OR（ルース分岐あり）
    JUEGO_OR_SB = auto()     # 中級：SB の OR_SB（ルース分岐なし）
    JUEGO_ROL = auto()       # 中級：将来追加（未実装）
    JUEGO_BB_ISO = auto()    # 別モード：BBアイソ（必要なら使う）


@dataclass(frozen=True)
class SBLimpFollowUpContext:
    """
    2段目：SBでLimpCが正解だった場合に出す追加問題
    「BBのオープンに対して、何BBまでコールするか（閾値）」を選ばせる
    """
    hand_key: str                # 例: "AKo"
    expected_max_bb: float       # 例: 2.25
    source_tag: str              # 例: "LimpCx2.25o"


@dataclass(frozen=True)
class OpenRaiseProblemContext:
    hole_cards: Tuple[str, str]
    position: str                       # "EP"/"MP"/"CO"/"BTN"/"SB"/"BB"
    open_size_bb: float                 # 表示用
    loose_player_exists: bool           # OR用（OR_SBでは常にFalse）
    excel_hand_key: str                 # "AKs" / "AKo" / "AA"
    excel_position_key: str
    limpers: int = 0


class GameController:
    def __init__(self, ui, juego_judge, yokosawa_judge, enable_debug: bool = False):
        self.ui = ui
        self.juego_judge = juego_judge
        self.yokosawa_judge = yokosawa_judge
        self.enable_debug = bool(enable_debug)

        self.difficulty: Optional[Difficulty] = None
        self.current_problem: Optional[ProblemType] = None
        self.context: Optional[OpenRaiseProblemContext] = None
        self.followup: Optional[SBLimpFollowUpContext] = None

        suits = ["s", "h", "d", "c"]
        ranks = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"]
        self.deck = [r + s for r, s in itertools.product(ranks, suits)]

        # 出題プール（将来ここに追加していくだけで拡張できる）
        self.pool_beginner = [ProblemType.JUEGO_OR]
        self.pool_intermediate = [ProblemType.JUEGO_OR_SB]   # 将来: + [ProblemType.JUEGO_ROL]
        self.pool_advanced: list[ProblemType] = []           # 将来追加

    # =========================
    # 内部ログ
    # =========================
    def _log(self, msg: str) -> None:
        if not self.enable_debug:
            return
        try:
            print(msg, flush=True)
        except Exception:
            pass

    # =========================
    # 開始（難易度選択）
    # =========================
    def start_yokosawa_open(self) -> None:
        self.difficulty = None
        self.current_problem = ProblemType.YOKOSAWA_OPEN
        self.new_question()

    def start_juego_beginner(self) -> None:
        self.difficulty = Difficulty.BEGINNER
        self.new_question()

    def start_juego_intermediate(self) -> None:
        self.difficulty = Difficulty.INTERMEDIATE
        self.new_question()

    def start_juego_advanced(self) -> None:
        self.difficulty = Difficulty.ADVANCED
        self.new_question()

    # =========================
    # 次の問題
    # =========================
    def new_question(self) -> None:
        # 新しい問題の開始時は followup を必ず解除
        self.followup = None

        if hasattr(self.ui, "hide_next_button"):
            try:
                self.ui.hide_next_button()
            except Exception:
                pass

        if hasattr(self.ui, "hide_followup_size_buttons"):
            try:
                self.ui.hide_followup_size_buttons()
            except Exception:
                pass

        # ヨコサワ（未実装扱い）
        if self.current_problem == ProblemType.YOKOSAWA_OPEN:
            self.context = None
            self.ui.show_text("【ヨコサワ式】オープンレイズ問題（未実装/既存実装に合わせてください）")
            return

        # 難易度未選択
        if self.difficulty is None:
            self.ui.show_text("難易度を選択してください（初級/中級/上級）")
            return

        # 難易度ごとの出題プールから問題タイプを選ぶ
        if self.difficulty == Difficulty.BEGINNER:
            pool = self.pool_beginner
        elif self.difficulty == Difficulty.INTERMEDIATE:
            pool = self.pool_intermediate
        else:
            pool = self.pool_advanced

        if not pool:
            self.ui.show_text("この難易度は未実装です（問題がまだ登録されていません）")
            return

        self.current_problem = random.choice(pool)

        # -------------------------
        # 初級：OR（EP/MP/CO/BTN）
        # -------------------------
        if self.current_problem == ProblemType.JUEGO_OR:
            self.context = self._generate_or_problem_beginner()
            ctx = self.context

            self.ui.deal_cards(ctx.hole_cards)
            if hasattr(self.ui, "set_hand_pos"):
                try:
                    self.ui.set_hand_pos(hand=ctx.excel_hand_key, pos=ctx.position)
                except Exception:
                    pass

            # ORはルース分岐あり（表示とフラグ一致）
            loose_msg = "｜ルースなplayerがいます" if ctx.loose_player_exists else ""

            self.ui.show_text(
                "【JUEGO 初級】オープンレイズ判断（OR）｜"
                f"Pos: {ctx.position}｜"
                f"{ctx.open_size_bb}BB"
                f"{loose_msg}"
            )
            return

        # -------------------------
        # 中級：OR_SB（SBのみ・ルース分岐なし）
        # -------------------------
        if self.current_problem == ProblemType.JUEGO_OR_SB:
            self.context = self._generate_or_sb_problem_intermediate()
            ctx = self.context

            self.ui.deal_cards(ctx.hole_cards)
            if hasattr(self.ui, "set_hand_pos"):
                try:
                    self.ui.set_hand_pos(hand=ctx.excel_hand_key, pos=ctx.position)
                except Exception:
                    pass

            # OR_SBはルース分岐不要 → 表示しない
            self.ui.show_text(
                "【JUEGO 中級】SBオープン判断（OR_SB）｜"
                "Pos: SB｜"
                f"{ctx.open_size_bb}BB"
            )
            return

        # -------------------------
        # 中級：ROL（将来追加）
        # -------------------------
        if self.current_problem == ProblemType.JUEGO_ROL:
            self.context = None
            self.ui.show_text("【JUEGO 中級】ROL は未実装です（後で追加します）")
            return

        # -------------------------
        # その他
        # -------------------------
        self.ui.show_text("内部：未知の問題タイプです")
        return

    # =========================
    # Follow-up helpers
    # =========================
    def _parse_limp_tag_to_max_bb(self, tag: str) -> Optional[float]:
        """
        "LimpCx2o" / "LimpCx2.25o" / "LimpCx2.5o" / "LimpCx3o"
        から 2.0 / 2.25 / 2.5 / 3.0 を取り出す。
        """
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
        except Exception:
            return None

    def _enter_sb_limp_followup(self, hand_key: str, tag: str) -> bool:
        """
        OR_SBのLimpC正解後に2段目へ遷移して問題文を表示する。
        """
        max_bb = self._parse_limp_tag_to_max_bb(tag)
        if max_bb is None:
            return False

        self.followup = SBLimpFollowUpContext(
            hand_key=hand_key,
            expected_max_bb=max_bb,
            source_tag=tag,
        )

        # Nextは出さない（まだ2段目が残っている）
        if hasattr(self.ui, "hide_next_button"):
            try:
                self.ui.hide_next_button()
            except Exception:
                pass

        # 2段目ボタンを表示（UI側が実装済みの場合）
        if hasattr(self.ui, "show_followup_size_buttons"):
            try:
                self.ui.show_followup_size_buttons()
            except Exception as e:
                # 握りつぶさない：原因を画面に出す
                self.ui.show_text(f"UIエラー：show_followup_size_buttons に失敗: {e}")
                return False
        else:
            self.ui.show_text("UIエラー：show_followup_size_buttons が見つかりません")
            return False


    # =========================
    # 回答
    # =========================
    def submit(self, user_action: Optional[str] = None) -> None:
        if user_action is None:
            self.ui.show_text("アクションが未指定です")
            return

        ua = (user_action or "").strip().upper()

        # -------------------------
        # 2段目待ちなら、ここで2段目を採点して終了
        # -------------------------
        if self.followup is not None:
            try:
                chosen = float(ua)
            except Exception:
                self.ui.show_text(f"数値を選択してください（2 / 2.25 / 2.5 / 3）。入力={ua}")
                return

            expected = self.followup.expected_max_bb
            ok = (abs(chosen - expected) < 1e-9)

            src = self.followup.source_tag
            self.followup = None

            if hasattr(self.ui, "hide_followup_size_buttons"):
                try:
                    self.ui.hide_followup_size_buttons()
                except Exception:
                    pass

            if hasattr(self.ui, "show_next_button"):
                try:
                    self.ui.show_next_button()
                except Exception:
                    pass

            if ok:
                self.ui.show_text(f"正解：{expected}BBまでコール（元タグ: {src}）")
            else:
                self.ui.show_text(f"不正解：正解は {expected}BB（あなた={chosen}BB、元タグ: {src}）")
            return

        # -------------------------
        # 通常回答の許可集合
        # -------------------------
        allowed = {"FOLD", "RAISE", "LIMP_CALL"}
        if ua not in allowed:
            self.ui.show_text(f"不正なアクションです: {ua}")
            return

        if self.current_problem is None:
            self.ui.show_text("難易度を選択してください（初級/中級/上級）")
            return

        if self.context is None:
            self.ui.show_text("内部エラー：Context is missing")
            return

        result: Any = None
        is_correct = False
        reason = ""

        try:
            ctx = self.context

            # -------------------------
            # 初級：OR
            # -------------------------
            if self.current_problem == ProblemType.JUEGO_OR:
                result = self.juego_judge.judge_or(
                    position=ctx.position,
                    hand=ctx.excel_hand_key,
                    user_action=ua,
                    loose=ctx.loose_player_exists,
                )

            # -------------------------
            # 中級：OR_SB（ルース分岐なし＝looseは常にFalse固定）
            # -------------------------
            elif self.current_problem == ProblemType.JUEGO_OR_SB:
                result = self.juego_judge.judge_or_sb(
                    position="SB",
                    hand=ctx.excel_hand_key,
                    user_action=ua,
                    loose=False,  # 明示：OR_SBでは不要
                )

            # -------------------------
            # 将来
            # -------------------------
            elif self.current_problem == ProblemType.JUEGO_ROL:
                self.ui.show_text("ROLは未実装です")
                return
            else:
                self.ui.show_text("内部：未知の問題タイプです")
                return

            is_correct = bool(getattr(result, "correct", False))
            reason = str(getattr(result, "reason", ""))

            dbg = getattr(result, "debug", None)
            if dbg is not None:
                self._log("=== JUEGO DEBUG ===")
                self._log(str(dbg))
                self._log("===================")

            # -------------------------
            # OR_SBで LimpC 正解なら 2段目へ
            # -------------------------
            # OR_SBで LimpC 正解なら 2段目へ（judgeが計算したmax_bbを優先）
            if self.current_problem == ProblemType.JUEGO_OR_SB and is_correct:
                dbg2 = getattr(result, "debug", {}) or {}

                detail_tag = str(dbg2.get("detail_tag") or dbg2.get("tag") or "").strip()
                max_bb = dbg2.get("followup_expected_max_bb", None)

                # ここで状況をログに出す（enable_debug=True のときのみ）
                self._log(f"[CTRL] followup check: detail_tag={detail_tag!r} max_bb={max_bb!r}")

                if detail_tag.upper().startswith("LIMPC"):
                    # max_bb が取れていればそれを使って確実に遷移
                    if isinstance(max_bb, (int, float)) and max_bb > 0:
                        self.followup = SBLimpFollowUpContext(
                            hand_key=ctx.excel_hand_key,
                            expected_max_bb=float(max_bb),
                            source_tag=detail_tag,
                        )
                        if hasattr(self.ui, "hide_next_button"):
                            self.ui.hide_next_button()
                        if hasattr(self.ui, "show_followup_size_buttons"):
                            self.ui.show_followup_size_buttons()

                        self.ui.show_text(
                            "正解（リンプイン）。追加問題：\n"
                            "BBのオープンに対して、何BBまでコールしますか？\n"
                            "選択肢：2 / 2.25 / 2.5 / 3"
                        )
                        return

                    # max_bb が無い場合は従来どおりパースして遷移（保険）
                    if self._enter_sb_limp_followup(hand_key=ctx.excel_hand_key, tag=detail_tag):
                        return  # 2段目待ちなので Next は出さない


        except Exception as e:
            self.ui.show_text(f"内部エラー：{e}")
            self._log(f"[CTRL] Exception in submit: {e}")
            return

        # 採点が完了した場合のみ Next
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
    # Problem generation
    # =========================
    def _generate_or_problem_beginner(self) -> OpenRaiseProblemContext:
        card1, card2 = random.sample(self.deck, 2)
        position = random.choice(["EP", "MP", "CO", "BTN"])   # ← SBは初級ORから除外
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
            limpers=0,
        )

    def _generate_or_sb_problem_intermediate(self) -> OpenRaiseProblemContext:
        card1, card2 = random.sample(self.deck, 2)
        hand_key = self._to_hand_key(card1, card2)

        return OpenRaiseProblemContext(
            hole_cards=(card1, card2),
            position="SB",
            open_size_bb=3.0,                 # 表が3BB想定なら固定でOK
            loose_player_exists=False,         # ← 明示：OR_SBでは不要
            excel_hand_key=hand_key,
            excel_position_key="SB",
            limpers=0,
        )

    def _to_hand_key(self, c1: str, c2: str) -> str:
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
