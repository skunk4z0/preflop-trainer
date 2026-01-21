# main.py
from __future__ import annotations

import os
import tkinter as tk
from tkinter import messagebox

from openpyxl import load_workbook

import config
from controller import GameController
from excel_range_repository import ExcelRangeRepository
from juego_judge import JUEGOJudge


class PokerTrainerUI:
    CARD_W = 280
    CARD_H = 380

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Poker Trainer")

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
                enable_debug=True,
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
        self.btn_juego_i = tk.Button(top, text="JUEGO 中級(OR_SB/ROL)", command=self.start_juego_intermediate)
        self.btn_juego_a = tk.Button(top, text="JUEGO 上級(未)", command=self.start_juego_advanced)
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
        self.controller.submit(user_action=action)

    def on_next(self) -> None:
        self.controller.new_question()

    # -------------------------
    # Controller -> UI
    # -------------------------
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
        self.btn_fold.configure(state=tk.DISABLED)
        self.btn_raise.configure(state=tk.DISABLED)
        self.btn_limp_call.configure(state=tk.DISABLED)

        # ★ cards_frame の直前に差し込む（これで必ず見える位置に出る）
        self.followup_frame.pack(before=self.cards_frame, padx=10, pady=5)

    def hide_followup_size_buttons(self) -> None:
        self.btn_fold.configure(state=tk.NORMAL)
        self.btn_raise.configure(state=tk.NORMAL)
        self.btn_limp_call.configure(state=tk.NORMAL)
        self.followup_frame.pack_forget()

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


if __name__ == "__main__":
    root = tk.Tk()
    PokerTrainerUI(root)
    root.mainloop()
