# ui.py
from __future__ import annotations

import os
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, Optional

import config

logger = logging.getLogger("poker_trainer.ui")


def _contrast_text_color(rgb: str) -> str:
    try:
        r = int(rgb[0:2], 16)
        g = int(rgb[2:4], 16)
        b = int(rgb[4:6], 16)
        y = (r * 299 + g * 587 + b * 114) / 1000
        return "black" if y >= 150 else "white"
    except (ValueError, TypeError):
        return "black"


class PokerTrainerUI:
    CARD_W = 280
    CARD_H = 380
    _ANSWER_LAYOUTS: dict[str, list[tuple[str, str, str]]] = {
        "OR": [
            ("btn_fold", "FOLD", "FOLD"),
            ("btn_raise", "RAISE", "RAISE"),
        ],
        "OR_SB": [
            ("btn_fold", "FOLD", "FOLD"),
            ("btn_raise", "RAISE", "RAISE"),
            ("btn_limp_call", "LIMP_CALL", "LIMP_CALL"),
        ],
        "3BET": [
            ("btn_fold", "FOLD", "FOLD"),
            ("btn_raise", "3BET", "RAISE"),
            ("btn_limp_call", "CALL", "CALL"),
        ],
        "ROL_BBVSSB": [
            ("btn_fold", "CHECK", "CHECK"),
            ("btn_raise", "RAISE", "RAISE"),
        ],
        "ROL_DEFAULT": [
            ("btn_fold", "FOLD", "FOLD"),
            ("btn_raise", "RAISE", "RAISE"),
            ("btn_limp_call", "CALL", "CALL"),
        ],
    }
    _SITUATION_KINDS: tuple[str, ...] = ("OR", "OR_SB", "ROL", "3BET")

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Poker Trainer")

        # 依存注入されるもの（main.pyでセット）
        self.controller: Optional[Any] = None

        # popup参照
        self._range_popup = None

        # -------------------------
        # UI
        # -------------------------
        self.top = tk.Frame(root)
        self.top.pack(padx=10, pady=10, fill=tk.X)

        self.nav_frame = tk.Frame(self.top)
        self.nav_frame.pack(fill=tk.X)
        self.btn_home = tk.Button(self.nav_frame, text="TOPへ戻る", command=self.go_to_start)
        self.btn_home.pack(side=tk.LEFT, padx=5)
        self.btn_next = tk.Button(self.nav_frame, text="Next", command=self.on_next)
        self.btn_next.pack(side=tk.LEFT, padx=5)
        self.btn_next.pack_forget()

        self.menu_container = tk.Frame(self.top)
        self.menu_container.pack(fill=tk.X, pady=(8, 0))

        # TOP画面
        self.top_screen_frame = tk.Frame(self.menu_container)
        self.btn_top_difficulty = tk.Button(
            self.top_screen_frame,
            text="難易度別で練習",
            command=self.open_difficulty_practice,
            width=24,
        )
        self.btn_top_situation = tk.Button(
            self.top_screen_frame,
            text="シチュエーション別で練習",
            command=self.open_situation_practice,
            width=24,
        )
        self.btn_top_difficulty.pack(side=tk.LEFT, padx=5)
        self.btn_top_situation.pack(side=tk.LEFT, padx=5)

        # 難易度選択画面
        self.difficulty_screen_frame = tk.Frame(self.menu_container)
        self.btn_juego_b = tk.Button(
            self.difficulty_screen_frame,
            text="初級",
            command=lambda: self.on_select_difficulty("BEGINNER"),
            width=12,
        )
        self.btn_juego_i = tk.Button(
            self.difficulty_screen_frame,
            text="中級",
            command=lambda: self.on_select_difficulty("INTERMEDIATE"),
            width=12,
        )
        self.btn_juego_a = tk.Button(
            self.difficulty_screen_frame,
            text="上級",
            command=lambda: self.on_select_difficulty("ADVANCED"),
            width=12,
        )
        self.btn_difficulty_back = tk.Button(
            self.difficulty_screen_frame,
            text="戻る",
            command=self.open_top,
            width=10,
        )
        self.btn_juego_b.pack(side=tk.LEFT, padx=5)
        self.btn_juego_i.pack(side=tk.LEFT, padx=5)
        self.btn_juego_a.pack(side=tk.LEFT, padx=5)
        self.btn_difficulty_back.pack(side=tk.LEFT, padx=5)

        # 難易度内容確認画面
        self.confirm_screen_frame = tk.Frame(self.menu_container)
        self.lbl_confirm_title = tk.Label(self.confirm_screen_frame, text="難易度の内容確認")
        self.lbl_confirm_title.pack(anchor="w")
        self.var_confirm_kinds = tk.StringVar(value="")
        self.lbl_confirm_kinds = tk.Label(
            self.confirm_screen_frame,
            textvariable=self.var_confirm_kinds,
            justify="left",
            anchor="w",
        )
        self.lbl_confirm_kinds.pack(anchor="w", pady=(4, 6))
        confirm_buttons = tk.Frame(self.confirm_screen_frame)
        confirm_buttons.pack(anchor="w")
        self.btn_confirm_start = tk.Button(confirm_buttons, text="Start", command=self.start_selected_kinds, width=10)
        self.btn_confirm_back = tk.Button(confirm_buttons, text="戻る", command=self.open_difficulty_practice, width=10)
        self.btn_confirm_start.pack(side=tk.LEFT, padx=5)
        self.btn_confirm_back.pack(side=tk.LEFT, padx=5)

        # シチュエーション別
        self.situation_screen_frame = tk.Frame(self.menu_container)
        self.lbl_situation_title = tk.Label(self.situation_screen_frame, text="kindを選んで開始")
        self.lbl_situation_title.pack(anchor="w")
        self.var_kind_checks: dict[str, tk.BooleanVar] = {}
        self.situation_checks_frame = tk.Frame(self.situation_screen_frame)
        self.situation_checks_frame.pack(anchor="w", pady=(4, 6))
        for kind in self._SITUATION_KINDS:
            var = tk.BooleanVar(value=False)
            self.var_kind_checks[kind] = var
            tk.Checkbutton(
                self.situation_checks_frame,
                text=config.kind_short_label(kind),
                variable=var,
                onvalue=True,
                offvalue=False,
                anchor="w",
            ).pack(anchor="w")
        situation_buttons = tk.Frame(self.situation_screen_frame)
        situation_buttons.pack(anchor="w")
        self.btn_situation_start = tk.Button(
            situation_buttons,
            text="Start",
            command=self.start_situation_kinds,
            width=10,
        )
        self.btn_situation_back = tk.Button(situation_buttons, text="戻る", command=self.open_top, width=10)
        self.btn_situation_start.pack(side=tk.LEFT, padx=5)
        self.btn_situation_back.pack(side=tk.LEFT, padx=5)

        # --- 回答ボタン（通常） ---
        self.ans_frame = tk.Frame(root)
        self.ans_frame.pack(padx=10, pady=5)

        self.btn_fold = tk.Button(self.ans_frame, text="FOLD", width=10, command=lambda: self.on_answer("FOLD"))
        self.btn_raise = tk.Button(self.ans_frame, text="RAISE", width=12, command=lambda: self.on_answer("RAISE"))
        self.btn_limp_call = tk.Button(
            self.ans_frame, text="LIMP_CALL", width=12, command=lambda: self.on_answer("LIMP_CALL")
        )
        self.btn_fold.pack(side=tk.LEFT, padx=5)
        self.btn_raise.pack(side=tk.LEFT, padx=5)
        self.btn_limp_call.pack(side=tk.LEFT, padx=5)

        # --- 2段目ボタン（Frameは作るが、最初は pack しない） ---
        self.followup_frame = tk.Frame(root)

        self.btn_bb2 = tk.Button(self.followup_frame, text="2", width=8, command=lambda: self.on_answer("2"))
        self.btn_bb225 = tk.Button(self.followup_frame, text="2.25", width=8, command=lambda: self.on_answer("2.25"))
        self.btn_bb25 = tk.Button(self.followup_frame, text="2.5", width=8, command=lambda: self.on_answer("2.5"))
        self.btn_bb3 = tk.Button(self.followup_frame, text="3", width=8, command=lambda: self.on_answer("3"))
        self.btn_bb2.pack(side=tk.LEFT, padx=5)
        self.btn_bb225.pack(side=tk.LEFT, padx=5)
        self.btn_bb25.pack(side=tk.LEFT, padx=5)
        self.btn_bb3.pack(side=tk.LEFT, padx=5)

        # Cards（follow-up frame pack before の基準にするので保持）
        self.cards_frame = tk.Frame(root)
        self.cards_frame.pack(padx=10, pady=10)

        self.card_labels = [
            tk.Label(self.cards_frame, text=""),
            tk.Label(self.cards_frame, text=""),
        ]
        self.card_labels[0].grid(row=0, column=0, padx=8)
        self.card_labels[1].grid(row=0, column=1, padx=8)

        info = tk.Frame(root)
        info.pack(padx=10, pady=10, fill=tk.X)

        tk.Label(info, text="Hand").grid(row=0, column=0, sticky="w")
        self.var_hand = tk.StringVar(value="")
        tk.Entry(info, textvariable=self.var_hand, width=20).grid(row=0, column=1, sticky="w", padx=6)

        tk.Label(info, text="Pos").grid(row=0, column=2, sticky="w")
        self.var_pos = tk.StringVar(value="")
        tk.Entry(info, textvariable=self.var_pos, width=20).grid(row=0, column=3, sticky="w", padx=6)

        self.txt = tk.Text(root, height=10, width=80)
        self.txt.pack(padx=10, pady=10)

        # 初期表示はスタート画面（controller未接続でも動くUI状態にする）
        self._apply_start_screen_ui()

    # -------------------------
    # 依存性注入（main.pyから呼ぶ）
    # -------------------------
    def attach_controller(self, controller: Any) -> None:
        self.controller = controller

    # -------------------------
    # 画面遷移（TOP/難易度/確認/シチュエーション）
    # -------------------------
    def _ensure_menu_visible(self) -> None:
        if self.menu_container.winfo_manager() == "":
            self._tk_call("show menu container", lambda: self.menu_container.pack(fill=tk.X, pady=(8, 0)))
        self._tk_call("hide ans_frame on menu", self.ans_frame.pack_forget)

    def _switch_menu_screen(self, frame: tk.Frame) -> None:
        self._ensure_menu_visible()
        for w in (
            self.top_screen_frame,
            self.difficulty_screen_frame,
            self.confirm_screen_frame,
            self.situation_screen_frame,
        ):
            self._tk_call("menu screen pack_forget", w.pack_forget)
        frame.pack(fill=tk.X)

    def _apply_start_screen_ui(self) -> None:
        # UIだけを「開始前」状態に戻す
        self.close_range_grid_popup()
        self.hide_next_button()
        self.hide_followup_size_buttons()
        self._tk_call("hide ans_frame on menu", self.ans_frame.pack_forget)
        self._switch_menu_screen(self.top_screen_frame)

        # カード/入力欄/説明をクリア
        for lbl in self.card_labels:
            lbl.configure(image="", text="")
            lbl.image = None

        self.var_hand.set("")
        self.var_pos.set("")
        self.show_text("練習モードを選択してください。")

    def show_top_screen(self) -> None:
        self._switch_menu_screen(self.top_screen_frame)
        self.show_text("練習モードを選択してください。")

    def show_difficulty_screen(self) -> None:
        self._switch_menu_screen(self.difficulty_screen_frame)
        self.show_text("難易度を選択してください（初級/中級/上級）")

    def show_difficulty_confirm_screen(self, difficulty_label: str, selected_kinds: list[str]) -> None:
        self._switch_menu_screen(self.confirm_screen_frame)
        self.lbl_confirm_title.configure(text=f"難易度の内容確認（{difficulty_label}）")
        lines = [f"・{config.kind_short_label(k)}" for k in selected_kinds]
        self.var_confirm_kinds.set("\n".join(lines) if lines else "・(kind未定義)")
        self.show_text("Start で開始できます。")

    def show_situation_screen(self) -> None:
        self._switch_menu_screen(self.situation_screen_frame)
        for kind, var in self.var_kind_checks.items():
            var.set(kind == "OR")
        self.show_text("kindを1つ以上選んで Start を押してください。")

    def show_quiz_screen(self) -> None:
        self._tk_call("menu screen hide", self.menu_container.pack_forget)
        if self.ans_frame.winfo_manager() == "":
            self._tk_call("show ans_frame on quiz", lambda: self.ans_frame.pack(padx=10, pady=5))
        if self.top.winfo_manager() == "":
            self.top.pack(padx=10, pady=10, fill=tk.X)

    def go_to_start(self) -> None:
        # Controller状態をリセット（あれば）
        if self.controller is not None and hasattr(self.controller, "reset_state"):
            self.controller.reset_state()
        if self.menu_container.winfo_manager() == "":
            self.menu_container.pack(fill=tk.X, pady=(8, 0))
        self._apply_start_screen_ui()

    # -------------------------
    # UI -> Controller
    # -------------------------
    def open_top(self) -> None:
        if self.controller is None:
            self.show_top_screen()
            return
        self.controller.open_top()

    def open_difficulty_practice(self) -> None:
        if self.controller is None:
            self.show_text("内部エラー：Controllerが未接続です")
            return
        self.controller.open_difficulty_practice()

    def open_situation_practice(self) -> None:
        if self.controller is None:
            self.show_text("内部エラー：Controllerが未接続です")
            return
        self.controller.open_situation_practice()

    def on_select_difficulty(self, difficulty_name: str) -> None:
        if self.controller is None:
            self.show_text("内部エラー：Controllerが未接続です")
            return
            
        from core.models import Difficulty

        enum_map = {
            "BEGINNER": Difficulty.BEGINNER,
            "INTERMEDIATE": Difficulty.INTERMEDIATE,
            "ADVANCED": Difficulty.ADVANCED,
        }
        key = str(difficulty_name or "").strip().upper()
        if key not in enum_map:
            self.show_text(f"未知の難易度です: {difficulty_name}")
            return
        self.show_text(f"{config.difficulty_short_label(key)}を選択しました。")
        self.controller.select_difficulty(enum_map[key])

    def start_selected_kinds(self) -> None:
        if self.controller is None:
            self.show_text("内部エラー：Controllerが未接続です")
            return
        self.controller.start_selected_kinds()

    def start_situation_kinds(self) -> None:
        if self.controller is None:
            self.show_text("内部エラー：Controllerが未接続です")
            return
        selected_kinds = [kind for kind, var in self.var_kind_checks.items() if var.get()]
        self.controller.start_juego_with_kinds(selected_kinds)

    def on_answer(self, action: str) -> None:
        if self.controller is None:
            self.show_text("内部エラー：Controllerが未接続です")
            return
        self.lock_all_answer_buttons()  # 押した瞬間にロック
        self.controller.submit(user_action=action)

    def on_next(self) -> None:
        if self.controller is None:
            self.show_text("内部エラー：Controllerが未接続です")
            return
        self.controller.new_question()

    # -------------------------
    # Answer mode（Controller -> UI）
    # -------------------------
    def set_answer_mode(self, mode: str) -> None:
        m = (mode or "").strip().upper()

        # まず必ず全ボタンを外す（前状態の影響を断つ）
        for b in (self.btn_fold, self.btn_raise, self.btn_limp_call):
            self._tk_call("pack_forget answer button", b.pack_forget)

        if m == "ROL":
            pos = (self.var_pos.get() or "").strip().upper()
            layout_key = "ROL_BBVSSB" if pos == "BBVSSB" else "ROL_DEFAULT"
        else:
            layout_key = m if m in self._ANSWER_LAYOUTS else "OR"

        for btn_attr, label, action in self._ANSWER_LAYOUTS[layout_key]:
            btn = getattr(self, btn_attr)
            btn.config(text=label, command=lambda act=action: self.on_answer(act))
            btn.pack(side=tk.LEFT, padx=5)

    # -------------------------
    # Tk call safe wrapper（例外安全化）
    # -------------------------
    def _tk_call(self, where: str, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except tk.TclError as e:
            logger.debug("[UI] %s (ignored TclError): %s", where, e)
            return None
        except Exception as e:
            logger.exception("[UI] %s failed: %s", where, e)
            return None

    # -------------------------
    # Controller -> UI
    # -------------------------
    def _is_quiz_screen_active(self) -> bool:
        return self.menu_container.winfo_manager() == ""

    def _set_button_state_if_exists(self, btn: tk.Widget, *, state: str) -> None:
        if int(btn.winfo_exists()) == 0:
            return
        btn.configure(state=state)

    def lock_all_answer_buttons(self) -> None:
        if not self._is_quiz_screen_active():
            return
        for b in (
            self.btn_fold,
            self.btn_raise,
            self.btn_limp_call,
            self.btn_bb2,
            self.btn_bb225,
            self.btn_bb25,
            self.btn_bb3,
        ):
            self._set_button_state_if_exists(b, state=tk.DISABLED)

    def unlock_all_answer_buttons(self) -> None:
        if not self._is_quiz_screen_active():
            return
        for b in (
            self.btn_fold,
            self.btn_raise,
            self.btn_limp_call,
            self.btn_bb2,
            self.btn_bb225,
            self.btn_bb25,
            self.btn_bb3,
        ):
            self._set_button_state_if_exists(b, state=tk.NORMAL)

    def hide_next_button(self) -> None:
        self.btn_next.pack_forget()

    def show_next_button(self) -> None:
        if self.btn_next.winfo_manager() == "":
            self.btn_next.pack(side=tk.LEFT, padx=5)

    def deal_cards(self, hole_cards: tuple[str, str]) -> None:
        c1, c2 = hole_cards
        self._set_card_image(self.card_labels[0], c1)
        self._set_card_image(self.card_labels[1], c2)

    def set_hand_pos(self, hand: str, pos: str) -> None:
        self.var_hand.set(hand)
        self.var_pos.set(pos)

    def show_text(self, s: str) -> None:
        self.txt.delete("1.0", tk.END)
        self.txt.insert(tk.END, s)

    # -------------------------
    # Follow-up buttons
    # -------------------------
    def show_followup_size_buttons(self, choices=None, prompt: str | None = None) -> None:
        """
        follow-up の選択肢（例: [2, 2.25, 2.5, 3]）を受け取り、ボタンを動的に生成して表示する。
        on_answer(str(value)) を通す（controller attach 済みが前提）。
        """
        if choices is None:
            choices = [2, 2.25, 2.5, 3]

        # 通常回答は無効のまま
        self.btn_fold.configure(state=tk.DISABLED)
        self.btn_raise.configure(state=tk.DISABLED)
        self.btn_limp_call.configure(state=tk.DISABLED)

        # followup_frame 内を一旦クリア（既存ボタン残骸防止）
        for w in self.followup_frame.winfo_children():
            w.destroy()

        # 任意：プロンプト表示
        if prompt:
            lbl = tk.Label(self.followup_frame, text=prompt, anchor="w", justify="left")
            lbl.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(0, 4))

        row = tk.Frame(self.followup_frame)
        row.pack(side=tk.TOP, fill=tk.X)

        ctrl_ready = self.controller is not None

        for v in choices:
            label = str(int(v)) if float(v).is_integer() else str(v)
            btn = tk.Button(
                row,
                text=label,
                command=(lambda val=v: self.on_answer(str(val))) if ctrl_ready else None,
            )
            btn.configure(state=tk.NORMAL if ctrl_ready else tk.DISABLED)
            btn.pack(side=tk.LEFT, padx=4, pady=2)

        # 表示位置：cards_frame の手前
        self.followup_frame.pack_forget()
        self.followup_frame.pack(before=self.cards_frame, padx=10, pady=5)

    def hide_followup_size_buttons(self) -> None:
        try:
            for w in self.followup_frame.winfo_children():
                w.destroy()
            self.followup_frame.pack_forget()
        except Exception:
            pass

    # -------------------------
    # Card image
    # -------------------------
    def _set_card_image(self, label: tk.Label, card_code: str) -> None:
        from PIL import Image, ImageTk

        rank = card_code[0].upper()
        suit = card_code[1].lower()

        suit_map = {"c": "club", "d": "diamond", "h": "heart", "s": "spade"}
        rank_str = "10" if rank == "T" else rank

        filename = f"{suit_map[suit]}_{rank_str}.png"
        path = os.path.join(config.CARD_IMAGE_DIR, filename)

        img = Image.open(path).convert("RGBA")
        img = img.resize((self.CARD_W, self.CARD_H), Image.Resampling.LANCZOS)

        tk_img = ImageTk.PhotoImage(img)
        label.configure(image=tk_img)
        label.image = tk_img

    # -------------------------
    # Range popup
    # -------------------------
    def close_range_grid_popup(self) -> None:
        win = getattr(self, "_range_popup", None)
        if win is not None:
            self._tk_call("range popup destroy", win.destroy)
        self._range_popup = None
