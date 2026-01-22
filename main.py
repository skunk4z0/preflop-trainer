# main.py（PokerTrainerUI内に追記）
from __future__ import annotations

import re
import os
import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from openpyxl import load_workbook
import config

from openpyxl.workbook.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from excel_range_repository import ExcelRangeRepository
from juego_judge import JUEGOJudge
from controller import GameController


def _contrast_text_color(rgb: str) -> str:
    try:
        r = int(rgb[0:2], 16); g = int(rgb[2:4], 16); b = int(rgb[4:6], 16)
        y = (r*299 + g*587 + b*114) / 1000
        return "black" if y >= 150 else "white"
    except Exception:
        return "black"

class PokerTrainerUI:
    CARD_W = 280
    CARD_H = 380

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Poker Trainer")
        self._range_popup = None

        # -------------------------
        # Excel / Repository 初期化
        # -------------------------
        try:
            wb = load_workbook(config.EXCEL_PATH, data_only=True)
        except Exception as e:
            messagebox.showerror("Excel Error", f"Excelを開けません:\n{config.EXCEL_PATH}\n\n{e}")
            raise

        try:
            repo = ExcelRangeRepository(
                wb=wb,
                sheet_name=config.SHEET_NAME,
                aa_search_ranges=config.AA_SEARCH_RANGES,
                grid_topleft_offset=config.GRID_TOPLEFT_OFFSET,
                ref_color_cells=config.REF_COLOR_CELLS,
                enable_debug=False,
            )
        except Exception as e:
            messagebox.showerror("Repository Error", f"Repository初期化に失敗:\n{e}")
            raise

        juego_judge = JUEGOJudge(repo)
        yokosawa_judge = None

        self.controller = GameController(self, juego_judge, yokosawa_judge, enable_debug=True)

        # -------------------------
        # UI
        # -------------------------
        top = tk.Frame(root)
        top.pack(padx=10, pady=10)

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

        # Cards（ここを before=... の基準にするので、self に保持）
        self.cards_frame = tk.Frame(root)
        self.cards_frame.pack(padx=10, pady=10)

        self.card_labels = [
            tk.Label(self.cards_frame, text="card1"),
            tk.Label(self.cards_frame, text="card2"),
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
    # -------------------------
    # UI -> Controller
    # -------------------------
    def set_answer_mode(self, mode: str) -> None:
        """
        mode:
          - "OR" / "OR_SB"      : FOLD / RAISE / LIMP_CALL
          - "ROL_NONBB"         : FOLD / RAISE / CALL
          - "ROL_BB_OOP"        : FOLD / CHECK / RAISE
          - "ROL_BBVS_SB"       : CHECK / RAISE
        """
        m = (mode or "").strip().upper()

        # まず必ず全ボタンを外す（前状態の影響を断つ）
        for b in (self.btn_fold, self.btn_raise, self.btn_limp_call):
            try:
                b.pack_forget()
            except Exception:
                pass

        if m in ("OR", "OR_SB"):
            self.btn_fold.config(text="FOLD", command=lambda: self.on_answer("FOLD"))
            self.btn_raise.config(text="RAISE", command=lambda: self.on_answer("RAISE"))
            self.btn_limp_call.config(text="LIMP_CALL", command=lambda: self.on_answer("LIMP_CALL"))

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
            # BB_OOP は FOLD / CALL / RAISE（CHECKは出さない）
            self.btn_fold.config(text="FOLD", command=lambda: self.on_answer("FOLD"))
            self.btn_limp_call.config(text="CALL", command=lambda: self.on_answer("CALL"))
            self.btn_raise.config(text="RAISE", command=lambda: self.on_answer("RAISE"))

            self.btn_fold.pack(side=tk.LEFT, padx=5)
            self.btn_limp_call.pack(side=tk.LEFT, padx=5)
            self.btn_raise.pack(side=tk.LEFT, padx=5)


        elif m == "ROL_BBVS_SB":
            # CHECK / RAISE の2択
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


    def _lock_difficulty_buttons(self) -> None:
        self.btn_juego_b.configure(state=tk.DISABLED)
        self.btn_juego_i.configure(state=tk.DISABLED)
        self.btn_juego_a.configure(state=tk.DISABLED)

    def start_juego_beginner(self) -> None:
        self._lock_difficulty_buttons()
        self.controller.start_juego_beginner()

    def start_juego_intermediate(self) -> None:
        self._lock_difficulty_buttons()
        self.controller.start_juego_intermediate()

    def start_juego_advanced(self) -> None:
        self._lock_difficulty_buttons()
        self.controller.start_juego_advanced()

    def on_answer(self, action: str) -> None:
        self.lock_all_answer_buttons()         # ★追加：押した瞬間にロック
        self.controller.submit(user_action=action)

    def on_next(self) -> None:
        self.controller.new_question()

    # -------------------------
    # Controller -> UI
    # -------------------------
    def lock_all_answer_buttons(self) -> None:
        """回答を1回に制限するため、回答系ボタンをすべて無効化"""
        for b in (self.btn_fold, self.btn_raise, self.btn_limp_call,
                  self.btn_bb2, self.btn_bb225, self.btn_bb25, self.btn_bb3):
            try:
                b.configure(state=tk.DISABLED)
            except Exception:
                pass

    def unlock_all_answer_buttons(self) -> None:
        """次の問題開始時に回答ボタンを再び有効化"""
        for b in (self.btn_fold, self.btn_raise, self.btn_limp_call,
                  self.btn_bb2, self.btn_bb225, self.btn_bb25, self.btn_bb3):
            try:
                b.configure(state=tk.NORMAL)
            except Exception:
                pass
    
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
    def show_followup_size_buttons(self) -> None:
        # 通常回答は無効のまま
        self.btn_fold.configure(state=tk.DISABLED)
        self.btn_raise.configure(state=tk.DISABLED)
        self.btn_limp_call.configure(state=tk.DISABLED)

        # ★follow-up選択肢は有効化（on_answerで一旦ロックされるので、ここで復活させる）
        for b in (self.btn_bb2, self.btn_bb225, self.btn_bb25, self.btn_bb3):
            b.configure(state=tk.NORMAL)

        self.followup_frame.pack_forget()
        self.followup_frame.pack(before=self.cards_frame, padx=10, pady=5)



    def hide_followup_size_buttons(self) -> None:
        # ★ここで通常回答ボタンをNORMALに戻さない（次の問題開始までロック維持）
        self.followup_frame.pack_forget()

        # 念のためfollow-up側は無効化しておく（表示されないが事故防止）
        for b in (self.btn_bb2, self.btn_bb225, self.btn_bb25, self.btn_bb3):
            b.configure(state=tk.DISABLED)


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
            try:
                win.destroy()
            except Exception:
                pass

        win.protocol("WM_DELETE_WINDOW", _on_close)
        win.title(title)

        # ===== スケール（70%） =====
        SCALE = 0.7
        cell_size = max(18, int(46 * SCALE))
        pad = max(1, int(2 * SCALE))
        cell_font_size = max(7, int(9 * SCALE))

        grid_px = 13 * cell_size  # 表のピクセルサイズ（正方形）

        # -------------------------
        # Header（上部にNext/閉じる）
        # -------------------------
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
                except Exception:
                    pass
            ttk.Button(btns, text="Next", command=_next_and_close).pack(side="right", padx=(6, 0))

        if info_text:
            ttk.Label(header, text=info_text, wraplength=620, justify="left").pack(anchor="w", pady=(8, 0))

        # -------------------------
        # Body（Canvas）
        # -------------------------
        body = ttk.Frame(win)
        body.pack(padx=10, pady=10)

        # ★ここが重要：Canvas に「表サイズ」を指定して、ウィンドウの自然サイズを表に合わせる
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

        # ===== ウィンドウサイズ確定（表サイズに追従） =====
        win.update_idletasks()
        req_w = win.winfo_reqwidth()
        req_h = win.winfo_reqheight()

        # ===== 画面外にはみ出さない位置にクランプ =====
        try:
            self.root.update_idletasks()
            rx = self.root.winfo_x()
            ry = self.root.winfo_y()
            rw = self.root.winfo_width()
        except Exception:
            rx, ry, rw = 0, 0, 0

        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()

        x = rx + rw + 10  # まず右側狙い
        if x + req_w > sw:
            x = max(0, sw - req_w - 10)  # 右端に収まるように戻す

        y = ry
        if y + req_h > sh:
            y = max(0, sh - req_h - 60)  # 下端に収まるように調整（タスクバー分60px程度）

        win.geometry(f"{req_w}x{req_h}+{x}+{y}")

        # （任意）サイズ固定にするなら
        # win.resizable(False, False)   
        try:
            win.lift()
            win.attributes("-topmost", True)
            win.after(200, lambda: win.attributes("-topmost", False))  # ずっと固定せず、表示直後だけ
        except Exception:
            pass

    def close_range_grid_popup(self) -> None:
        win = getattr(self, "_range_popup", None)
        if win is not None:
            try:
                win.destroy()
            except Exception:
                pass
        self._range_popup = None


if __name__ == "__main__":
    root = tk.Tk()
    PokerTrainerUI(root)
    root.mainloop()
