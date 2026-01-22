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

    # JUEGO系
    JUEGO_OR = auto()        # 初級：EP/MP/CO/BTN の OR（ルース分岐あり）
    JUEGO_OR_SB = auto()     # 中級：SB の OR_SB（ルース分岐なし）
    JUEGO_ROL = auto()       # 上級：ROL（リンプインに対する対応）
    JUEGO_BB_ISO = auto()    # 別モード：BBアイソ（必要なら使う）


@dataclass(frozen=True)
class SBLimpFollowUpContext:
    """
    2段目：SBでLimpCが正解だった場合に出す追加問題
    「BBのオープンに対して、何BBまでコールするか（閾値）」を選ばせる
    """
    hand_key: str
    expected_max_bb: float
    source_tag: str


@dataclass(frozen=True)
class OpenRaiseProblemContext:
    hole_cards: Tuple[str, str]
    # OR: "EP"/"MP"/"CO"/"BTN"
    # OR_SB: "SB"
    # ROL: "MP"/"CO"/"BTN"/"SB"/"BB_OOP"/"BBvsSB"
    position: str
    open_size_bb: float                 # 表示用（OR/OR_SBはopen size, ROLはraise size）
    loose_player_exists: bool           # OR/ROL用（OR_SBでは常にFalse）
    excel_hand_key: str
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

        # 出題プール
        self.pool_beginner = [ProblemType.JUEGO_OR]
        self.pool_intermediate = [ProblemType.JUEGO_OR_SB]     # 中級はOR_SB固定
        self.pool_advanced = [ProblemType.JUEGO_ROL]           # 上級はROL（現状はこれだけ）

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
    # 追加：不正解時にレンジ表を表示（B-1）
    # =========================
    def _try_show_range_grid_on_incorrect(self, ctx: OpenRaiseProblemContext, result: Any) -> None:
        """
        不正解時にだけ、参照しているレンジ表をポップアップで表示する。
        - UIに show_range_grid_popup が無ければ何もしない
        - Repoが見つからなければ何もしない
        - 例外は握りつぶして本体は落とさない（安全側）
        """
        try:
            # UI側の関数が無ければ終了
            if not hasattr(self.ui, "show_range_grid_popup"):
                return

            dbg = getattr(result, "debug", None) or {}

            # kind/pos は debug 優先（judge が実際に参照した kind/pos が入っている想定）
            kind = (dbg.get("kind") or "").strip()
            pos = (dbg.get("position") or dbg.get("pos") or "").strip()

            # debug に無ければ current_problem / ctx から復元
            if not kind:
                if self.current_problem == ProblemType.JUEGO_OR:
                    kind = "OR"
                elif self.current_problem == ProblemType.JUEGO_OR_SB:
                    kind = "OR_SB"
                elif self.current_problem == ProblemType.JUEGO_ROL:
                    kind = "ROL"

            if not pos:
                # OR_SB はSB固定
                if self.current_problem == ProblemType.JUEGO_OR_SB:
                    pos = "SB"
                else:
                    pos = ctx.excel_position_key or ctx.position

            if not kind or not pos:
                return

            # repo の取り出し（構成差を吸収）
            repo = None
            if hasattr(self.ui, "repo"):
                repo = getattr(self.ui, "repo")
            if repo is None and hasattr(self.juego_judge, "repo"):
                repo = getattr(self.juego_judge, "repo")
            if repo is None and hasattr(self.juego_judge, "_repo"):
                repo = getattr(self.juego_judge, "_repo")

            if repo is None:
                return

            # Repoに表示用APIが無ければ終了
            if not hasattr(repo, "get_range_grid_view"):
                return

            grid_view = repo.get_range_grid_view(kind, pos)

            # ハイライト対象（今回のハンド）
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
            reason = str(getattr(result, "reason", "") or "").strip()
            if reason:
                info += reason
            if hasattr(self.ui, "hide_next_button"):
                self.ui.hide_next_button()
           
            title = f"{grid_view.kind} / {grid_view.pos}  [sheet={grid_view.sheet_name}]"

            self.ui.show_range_grid_popup(
                title=title,
                grid_cells=grid_view.cells,
                highlight_rc=highlight_rc,
                info_text=info,
                on_next=self.new_question,# ★追加
            )

        except Exception as e:
            self._log(f"[CTRL][WARN] show_range_grid_popup failed: {e}")

    # =========================
    # 開始（難易度選択）
    # =========================
    def start_yokosawa_open(self) -> None:
        self.difficulty = None
        self.current_problem = ProblemType.YOKOSAWA_OPEN
        self.new_question()

    def start_juego_beginner(self) -> None:
        self.difficulty = Difficulty.BEGINNER
        self.current_problem = None   # ★追加
        self.new_question()

    def start_juego_intermediate(self) -> None:
        self.difficulty = Difficulty.INTERMEDIATE
        self.current_problem = None   # ★追加
        self.new_question()

    def start_juego_advanced(self) -> None:
        self.difficulty = Difficulty.ADVANCED
        self.current_problem = None   # ★追加
        self.new_question()

    # =========================
    # 次の問題
    # =========================
    def new_question(self) -> None:
        # ★追加：次の問題開始で回答ボタンを解除
        if hasattr(self.ui, "unlock_all_answer_buttons"):
            try:
                self.ui.unlock_all_answer_buttons()
            except Exception:
                pass

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

            self._apply_answer_mode("OR")

            self.ui.deal_cards(ctx.hole_cards)
            if hasattr(self.ui, "set_hand_pos"):
                try:
                    self.ui.set_hand_pos(hand=ctx.excel_hand_key, pos=ctx.position)
                except Exception:
                    pass

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

            self._apply_answer_mode("OR_SB")

            self.ui.deal_cards(ctx.hole_cards)
            if hasattr(self.ui, "set_hand_pos"):
                try:
                    self.ui.set_hand_pos(hand=ctx.excel_hand_key, pos=ctx.position)
                except Exception:
                    pass

            self.ui.show_text(
                "【JUEGO 中級】SBオープン判断（OR_SB）｜"
                "Pos: SB｜"
                f"{ctx.open_size_bb}BB"
            )
            return

        # -------------------------
        # 上級：ROL
        # -------------------------
        if self.current_problem == ProblemType.JUEGO_ROL:
            self.context = self._generate_rol_problem()
            ctx = self.context

            # 位置でボタンモードを切替（UIが対応していれば）
            if ctx.position == "BBvsSB":
                self._apply_answer_mode("ROL_BBVS_SB")   # CHECK / RAISE
            elif ctx.position == "BB_OOP":
                self._apply_answer_mode("ROL_BB_OOP")    # FOLD / CALL / RAISE
            else:
                self._apply_answer_mode("ROL_NONBB")     # FOLD / RAISE / CALL

            self.ui.deal_cards(ctx.hole_cards)
            if hasattr(self.ui, "set_hand_pos"):
                try:
                    self.ui.set_hand_pos(hand=ctx.excel_hand_key, pos=ctx.position)
                except Exception:
                    pass

            fish_msg = "｜ルースなplayerがいます" if ctx.loose_player_exists else ""
            self.ui.show_text(
                "【JUEGO 上級】リンプインへの対応（ROL）｜"
                f"Pos: {ctx.position}｜"
                f"Raise={ctx.open_size_bb}BB"
                f"{fish_msg}"
            )
            return

        # -------------------------
        # その他
        # -------------------------
        self.ui.show_text("内部：未知の問題タイプです")
        return

    def _apply_answer_mode(self, mode: str) -> None:
        """
        UI側が対応していれば、回答ボタンの表示・意味をモードで切り替える。
        UI未実装でも落ちないようにガード。
        - OR / OR_SB: FOLD, RAISE, LIMP_CALL
        - ROL_NONBB: FOLD, RAISE, CALL
        - ROL_BB: CHECK, RAISE
        """
        if hasattr(self.ui, "set_answer_mode"):
            try:
                self.ui.set_answer_mode(mode)
            except Exception:
                pass

    # =========================
    # Follow-up helpers
    # =========================
    def _parse_limp_tag_to_max_bb(self, tag: str) -> Optional[float]:
        if not tag:
            return None
        t = str(tag).strip()
        if not t.upper().startswith("LIMPCX"):
            return None

        body = t[len("LimpCx"):].strip()
        if body.lower().endswith("o"):
            body = body[:-1]

        try:
            return float(body)
        except Exception:
            return None

    def _enter_sb_limp_followup(self, hand_key: str, tag: str) -> bool:
        max_bb = self._parse_limp_tag_to_max_bb(tag)
        if max_bb is None:
            return False

        self.followup = SBLimpFollowUpContext(
            hand_key=hand_key,
            expected_max_bb=max_bb,
            source_tag=tag,
        )

        if hasattr(self.ui, "hide_next_button"):
            try:
                self.ui.hide_next_button()
            except Exception:
                pass

        if hasattr(self.ui, "show_followup_size_buttons"):
            try:
                self.ui.show_followup_size_buttons()
            except Exception as e:
                self.ui.show_text(f"UIエラー：show_followup_size_buttons に失敗: {e}")
                return False
        else:
            self.ui.show_text("UIエラー：show_followup_size_buttons が見つかりません")
            return False

        return True

    # =========================
    # Problem generation
    # =========================
    def _generate_or_problem_beginner(self) -> OpenRaiseProblemContext:
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
            limpers=0,
        )

    def _generate_or_sb_problem_intermediate(self) -> OpenRaiseProblemContext:
        card1, card2 = random.sample(self.deck, 2)
        hand_key = self._to_hand_key(card1, card2)

        return OpenRaiseProblemContext(
            hole_cards=(card1, card2),
            position="SB",
            open_size_bb=3.0,
            loose_player_exists=False,
            excel_hand_key=hand_key,
            excel_position_key="SB",
            limpers=0,
        )

    def _generate_rol_problem(self) -> OpenRaiseProblemContext:
        card1, card2 = random.sample(self.deck, 2)
        position = random.choice(["MP", "CO", "BTN", "SB", "BB_OOP", "BBvsSB"])
        loose = random.choice([True, False])  # ROLvsFISH のため
        raise_size = 4.0 if position == "BBvsSB" else 5.0
        hand_key = self._to_hand_key(card1, card2)

        return OpenRaiseProblemContext(
            hole_cards=(card1, card2),
            position=position,
            open_size_bb=raise_size,          # 表示用（ROLのレイズ額）
            loose_player_exists=loose,
            excel_hand_key=hand_key,
            excel_position_key=position,
            limpers=1,
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

    # =========================
    # 回答
    # =========================
    def submit(self, user_action: Optional[str] = None) -> None:
        if user_action is None:
            self.ui.show_text("アクションが未指定です")
            return

        ua_raw = (user_action or "").strip().upper()

        # -------------------------
        # 2段目待ちなら、ここで2段目を採点して終了
        # -------------------------
        if self.followup is not None:
            try:
                chosen = float(ua_raw)
            except Exception:
                self.ui.show_text(f"数値を選択してください（2 / 2.25 / 2.5 / 3）。入力={ua_raw}")
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

        if self.current_problem is None:
            self.ui.show_text("難易度を選択してください（初級/中級/上級）")
            return

        if self.context is None:
            self.ui.show_text("内部エラー：Context is missing")
            return

        # -------------------------
        # 通常回答の許可集合（問題タイプで切替）
        # -------------------------
        if self.current_problem == ProblemType.JUEGO_ROL:
            allowed = {"FOLD", "RAISE", "CALL", "CHECK", "LIMP_CALL"}  # LIMP_CALLは互換
        else:
            allowed = {"FOLD", "RAISE", "LIMP_CALL"}

        if ua_raw not in allowed:
            self.ui.show_text(f"不正なアクションです: {ua_raw}")
            return

        # ROL互換：LIMP_CALL を CALL と同義に扱う
        ua = "CALL" if (self.current_problem == ProblemType.JUEGO_ROL and ua_raw == "LIMP_CALL") else ua_raw

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
            # 中級：OR_SB（ルース分岐なし）
            # -------------------------
            elif self.current_problem == ProblemType.JUEGO_OR_SB:
                result = self.juego_judge.judge_or_sb(
                    position="SB",
                    hand=ctx.excel_hand_key,
                    user_action=ua,
                    loose=False,
                )

            # -------------------------
            # 上級：ROL
            # -------------------------
            elif self.current_problem == ProblemType.JUEGO_ROL:
                if not hasattr(self.juego_judge, "judge_rol"):
                    self.ui.show_text("内部エラー：judge_rol が未実装です（juego_judge.py に追加してください）")
                    return

                result = self.juego_judge.judge_rol(
                    position=ctx.position,
                    hand=ctx.excel_hand_key,
                    user_action=ua,
                    loose=ctx.loose_player_exists,
                )

            else:
                self.ui.show_text("内部：未知の問題タイプです")
                return

            is_correct = bool(getattr(result, "correct", False))
            reason = str(getattr(result, "reason", ""))

            dbg = getattr(result, "debug", None)
            if dbg is not None and (not is_correct):
                self._log("=== JUEGO DEBUG ===")
                self._log(str(dbg))
                self._log("===================")


            # -------------------------
            # OR_SBで LimpC 正解なら 2段目へ（この場合は採点完了ではないので return）
            # -------------------------
            if self.current_problem == ProblemType.JUEGO_OR_SB and is_correct:
                dbg2 = getattr(result, "debug", {}) or {}
                detail_tag = str(dbg2.get("detail_tag") or dbg2.get("tag") or "").strip()
                max_bb = dbg2.get("followup_expected_max_bb", None)

                self._log(f"[CTRL] followup check: detail_tag={detail_tag!r} max_bb={max_bb!r}")

                if detail_tag.upper().startswith("LIMPC"):
                    # judgeが計算したmax_bbを優先
                    if isinstance(max_bb, (int, float)) and max_bb > 0:
                        self.followup = SBLimpFollowUpContext(
                            hand_key=ctx.excel_hand_key,
                            expected_max_bb=float(max_bb),
                            source_tag=detail_tag,
                        )
                        if hasattr(self.ui, "hide_next_button"):
                            try:
                                self.ui.hide_next_button()
                            except Exception:
                                pass
                        if hasattr(self.ui, "show_followup_size_buttons"):
                            try:
                                self.ui.show_followup_size_buttons()
                            except Exception:
                                pass

                        self.ui.show_text(
                            "正解（リンプイン）。追加問題：\n"
                            "BBのオープンに対して、何BBまでコールしますか？\n"
                            "選択肢：2 / 2.25 / 2.5 / 3"
                        )
                        return

                    # 保険：max_bbが取れない場合はパースで遷移
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
            # ★追加：不正解時だけレンジ表ポップアップ
            self._try_show_range_grid_on_incorrect(ctx=self.context, result=result)
