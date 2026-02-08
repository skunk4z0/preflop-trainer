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
        r = int(rgb[0:2], 16); g = int(rgb[2:4], 16); b = int(rgb[4:6], 16)
        y = (r * 299 + g * 587 + b * 114) / 1000
        return "black" if y >= 150 else "white"
    except (ValueError, TypeError):
        return "black"


class PokerTrainerUI:
    CARD_W = 280
    CARD_H = 380

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
        top = tk.Frame(root)
        top.pack(padx=10, pady=10)

        # ★追加：スタートへ戻る
        self.btn_home = tk.Button(top, text="Startへ戻る", command=self.go_to_start)
        self.btn_home.pack(side=tk.LEFT, padx=5)

        self.btn_juego_b = tk.Button(top, text="JUEGO 初級(OR)", command=self.start_juego_beginner)
        self.btn_juego_i = tk.Button(top, text="JUEGO 中級(OR_SB)", command=self.start_juego_intermediate)
        self.btn_juego_a = tk.Button(top, text="JUEGO 上級(ROL)", command=self.start_juego_advanced)
        self.btn_juego_b.pack(side=tk.LEFT, padx=5)
        self.btn_juego_i.pack(side=tk.LEFT, padx=5)
        self.btn_juego_a.pack(side=tk.LEFT, padx=5)

        self.btn_next = tk.Button(top, text="Next", command=self.on_next)
        self.btn_next.pack(side=tk.LEFT, padx=5)
        self.btn_next.pack_forget()

        # --- 回答ボタン（通常） ---
        self.ans_frame = tk.Frame(root)
        self.ans_frame.pack(padx=10, pady=5)

        self.btn_fold = tk.Button(self.ans_frame, text="FOLD", width=10, command=lambda: self.on_answer("FOLD"))
        self.btn_raise = tk.Button(self.ans_frame, text="RAISE", width=12, command=lambda: self.on_answer("RAISE"))
        self.btn_limp_call = tk.Button(self.ans_frame, text="LIMP_CALL", width=12, command=lambda: self.on_answer("LIMP_CALL"))
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
    # Start画面（戻る）関連
    # -------------------------
    def _unlock_difficulty_buttons(self) -> None:
        self.btn_juego_b.configure(state=tk.NORMAL)
        self.btn_juego_i.configure(state=tk.NORMAL)
        self.btn_juego_a.configure(state=tk.NORMAL)

    def _lock_difficulty_buttons(self) -> None:
        self.btn_juego_b.configure(state=tk.DISABLED)
        self.btn_juego_i.configure(state=tk.DISABLED)
        self.btn_juego_a.configure(state=tk.DISABLED)

    def _apply_start_screen_ui(self) -> None:
        # UIだけを「開始前」状態に戻す
        self.close_range_grid_popup()
        self.hide_next_button()
        self.hide_followup_size_buttons()
        self._unlock_difficulty_buttons()

        # カード/入力欄/説明をクリア
        for lbl in self.card_labels:
            lbl.configure(image="", text="")
            lbl.image = None

        self.var_hand.set("")
        self.var_pos.set("")
        self.show_text("難易度を選択してください（初級/中級/上級）")

        # 回答は開始まで禁止
        self.lock_all_answer_buttons()

    def go_to_start(self) -> None:
        # Controller状態をリセット（あれば）
        if self.controller is not None and hasattr(self.controller, "reset_state"):
            self.controller.reset_state()
        self._apply_start_screen_ui()

    # -------------------------
    # UI -> Controller
    # -------------------------
    def start_juego_beginner(self) -> None:
        if self.controller is None:
            self.show_text("内部エラー：Controllerが未接続です")
            return
        self._lock_difficulty_buttons()
        self.controller.start_juego_beginner()

    def start_juego_intermediate(self) -> None:
        if self.controller is None:
            self.show_text("内部エラー：Controllerが未接続です")
            return
        self._lock_difficulty_buttons()
        self.controller.start_juego_intermediate()

    def start_juego_advanced(self) -> None:
        if self.controller is None:
            self.show_text("内部エラー：Controllerが未接続です")
            return
        self._lock_difficulty_buttons()
        self.controller.start_juego_advanced()

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

        if m in ("OR", "OR_SB"):
            self.btn_fold.config(text="FOLD", command=lambda: self.on_answer("FOLD"))
            self.btn_raise.config(text="RAISE", command=lambda: self.on_answer("RAISE"))
            self.btn_limp_call.config(text="LIMP/CALL", command=lambda: self.on_answer("LIMP_CALL"))

            self.btn_fold.pack(side=tk.LEFT, padx=5)
            self.btn_raise.pack(side=tk.LEFT, padx=5)
            self.btn_limp_call.pack(side=tk.LEFT, padx=5)

        elif m == "3BET":
            # ★追加：3BET用
            self.btn_fold.config(text="FOLD", command=lambda: self.on_answer("FOLD"))
            self.btn_raise.config(text="3BET", command=lambda: self.on_answer("RAISE"))  # 表示だけ3BET
            self.btn_limp_call.config(text="CALL", command=lambda: self.on_answer("CALL"))

            self.btn_fold.pack(side=tk.LEFT, padx=5)
            self.btn_raise.pack(side=tk.LEFT, padx=5)
            self.btn_limp_call.pack(side=tk.LEFT, padx=5)

        elif m == "ROL_NONBB":
            self.btn_fold.config(text="FOLD", command=lambda: self.on_answer("FOLD"))
            self.btn_raise.config(text="RAISE", command=lambda: self.on_answer("RAISE"))
            self.btn_limp_call.config(text="CALL", command=lambda: self.on_answer("CALL"))

            self.btn_fold.pack(side=tk.LEFT, padx=5)
            self.btn_raise.pack(side=tk.LEFT, padx=5)
            self.btn_limp_call.pack(side=tk.LEFT, padx=5)

        elif m == "ROL_BB_OOP":
            self.btn_fold.config(text="FOLD", command=lambda: self.on_answer("FOLD"))
            self.btn_limp_call.config(text="CALL", command=lambda: self.on_answer("CALL"))
            self.btn_raise.config(text="RAISE", command=lambda: self.on_answer("RAISE"))

            self.btn_fold.pack(side=tk.LEFT, padx=5)
            self.btn_limp_call.pack(side=tk.LEFT, padx=5)
            self.btn_raise.pack(side=tk.LEFT, padx=5)

        elif m == "ROL_BBVS_SB":
            self.btn_fold.config(text="CHECK", command=lambda: self.on_answer("CHECK"))
            self.btn_raise.config(text="RAISE", command=lambda: self.on_answer("RAISE"))

            self.btn_fold.pack(side=tk.LEFT, padx=5)
            self.btn_raise.pack(side=tk.LEFT, padx=5)

        else:
            # 想定外は安全側でORに戻す
            self.btn_fold.config(text="FOLD", command=lambda: self.on_answer("FOLD"))
            self.btn_raise.config(text="RAISE", command=lambda: self.on_answer("RAISE"))
            self.btn_limp_call.config(text="LIMP_CALL", command=lambda: self.on_answer("LIMP_CALL"))

            self.btn_fold.pack(side=tk.LEFT, padx=5)
            self.btn_raise.pack(side=tk.LEFT, padx=5)
            self.btn_limp_call.pack(side=tk.LEFT, padx=5)

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
    def lock_all_answer_buttons(self) -> None:
        for b in (self.btn_fold, self.btn_raise, self.btn_limp_call,
                  self.btn_bb2, self.btn_bb225, self.btn_bb25, self.btn_bb3):
            self._tk_call("disable answer button", b.configure, state=tk.DISABLED)

    def unlock_all_answer_buttons(self) -> None:
        for b in (self.btn_fold, self.btn_raise, self.btn_limp_call,
                  self.btn_bb2, self.btn_bb225, self.btn_bb25, self.btn_bb3):
            self._tk_call("enable answer button", b.configure, state=tk.NORMAL)

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
        controller.submit(str(value)) を呼ぶ前提（self.controller が attach 済みであること）。
        """
        # 既定（互換）
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

        # ボタン生成（横並び）
        row = tk.Frame(self.followup_frame)
        row.pack(side=tk.TOP, fill=tk.X)

        # controller への接続チェック（落とさない）
        ctrl = getattr(self, "controller", None)

        for v in choices:
            # 表示は 2 / 2.25 / 2.5 / 3 のように綺麗に
            label = str(int(v)) if float(v).is_integer() else str(v)

            btn = tk.Button(
                row,
                text=label,
                command=(lambda val=v: ctrl.submit(str(val))) if ctrl else None,
            )
            btn.configure(state=tk.NORMAL if ctrl else tk.DISABLED)
            btn.pack(side=tk.LEFT, padx=4, pady=2)

        # 表示位置：cards_frame の手前
        self.followup_frame.pack_forget()
        self.followup_frame.pack(before=self.cards_frame, padx=10, pady=5)


    def hide_followup_size_buttons(self) -> None:
        # followup_frame 内をクリアして隠す
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
    def show_range_grid_popup(
        self,
        title: str,
        grid_cells,
        highlight_rc=None,
        info_text: str = "",
        on_next=None,
    ) -> None:
        # 既に開いていたら閉じる（多重ポップアップ防止）
        self.close_range_grid_popup()

        win = tk.Toplevel(self.root)
        self._range_popup = win

        def _on_close():
            self._range_popup = None
            self._tk_call("range popup destroy", win.destroy)

        win.protocol("WM_DELETE_WINDOW", _on_close)
        win.title(title)

        # ===== スケール（70%） =====
        SCALE = 0.7
        cell_size = max(18, int(46 * SCALE))
        pad = max(1, int(2 * SCALE))
        cell_font_size = max(7, int(9 * SCALE))

        grid_px = 13 * cell_size  # 表のピクセルサイズ（正方形）

        # Header
        header = ttk.Frame(win)
        header.pack(fill="x", padx=10, pady=10)

        topbar = ttk.Frame(header)
        topbar.pack(fill="x")

        ttk.Label(topbar, text=title, font=("", 12, "bold")).pack(side="left", anchor="w")

        btns = ttk.Frame(topbar)
        btns.pack(side="right")

        if callable(on_next):
            def _next_and_close():
                _on_close()
                try:
                    on_next()
                except Exception as e:
                    logger.exception("[UI] on_next failed: %s", e)
                    try:
                        messagebox.showerror("Error", f"Next処理でエラーが発生しました:\n{e}")
                    except tk.TclError:
                        pass

            ttk.Button(btns, text="Next", command=_next_and_close).pack(side="right", padx=(6, 0))

        if info_text:
            ttk.Label(header, text=info_text, wraplength=620, justify="left").pack(anchor="w", pady=(8, 0))

        # Body（Canvas）
        body = ttk.Frame(win)
        body.pack(padx=10, pady=10)

        canvas = tk.Canvas(body, width=grid_px, height=grid_px, highlightthickness=0, bg="#f0f0f0")
        canvas.pack()

        for r in range(13):
            for c in range(13):
                cell = grid_cells[r][c]
                x0 = c * cell_size
                y0 = r * cell_size
                x1 = x0 + cell_size
                y1 = y0 + cell_size

                fill = f"#{cell.bg_rgb}"
                canvas.create_rectangle(
                    x0 + pad, y0 + pad, x1 - pad, y1 - pad,
                    fill=fill, outline="#c0c0c0"
                )

                label = (cell.label or "").strip()
                if label:
                    fg = _contrast_text_color(cell.bg_rgb)
                    canvas.create_text(
                        (x0 + x1) / 2, (y0 + y1) / 2,
                        text=label, fill=fg, font=("", cell_font_size)
                    )

        if highlight_rc is not None:
            hr, hc = highlight_rc
            x0 = hc * cell_size
            y0 = hr * cell_size
            x1 = x0 + cell_size
            y1 = y0 + cell_size
            canvas.create_rectangle(x0 + 1, y0 + 1, x1 - 1, y1 - 1, outline="#ff0000", width=3)

        # ウィンドウサイズ確定（表サイズに追従）
        win.update_idletasks()
        req_w = win.winfo_reqwidth()
        req_h = win.winfo_reqheight()

        # 画面外にはみ出さない位置にクランプ
        try:
            self.root.update_idletasks()
            rx = self.root.winfo_x()
            ry = self.root.winfo_y()
            rw = self.root.winfo_width()
        except tk.TclError as e:
            logger.debug("[UI] root geometry not available: %s", e)
            rx, ry, rw = 0, 0, 0

        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()

        x = rx + rw + 10  # まず右側狙い
        if x + req_w > sw:
            x = max(0, sw - req_w - 10)

        y = ry
        if y + req_h > sh:
            y = max(0, sh - req_h - 60)

        win.geometry(f"{req_w}x{req_h}+{x}+{y}")

        try:
            win.lift()
            win.attributes("-topmost", True)
            win.after(200, lambda: win.attributes("-topmost", False))
        except tk.TclError as e:
            logger.debug("[UI] lift/topmost failed: %s", e)

    def close_range_grid_popup(self) -> None:
        win = getattr(self, "_range_popup", None)
        if win is not None:
            self._tk_call("range popup destroy", win.destroy)
        self._range_popup = None
