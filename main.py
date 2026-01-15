# main.py
from __future__ import annotations

import os
import tkinter as tk
from tkinter import messagebox

from openpyxl import load_workbook

import config
from excel_range_repository import ExcelRangeRepository
from controller import GameController

# あなたの実装ファイル名に合わせて import 名を調整してください
# 例: juego_judge.py に class JUEGOJudge がある前提
from juego_judge import JUEGOJudge


class PokerTrainerUI:
    CARD_W = 280
    CARD_H = 380

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Poker Trainer")

        # -------------------------
        # Excel / Repository 初期化（新仕様）
        # -------------------------
        try:
            wb = load_workbook(config.EXCEL_PATH, data_only=True)
        except Exception as e:
            messagebox.showerror("Excel Error", f"Excelを開けません:\n{config.EXCEL_PATH}\n\n{e}")
            raise

        # ※あなたのExcelのシート名に合わせて変更
        sheet_name = "JUEGO"

        try:
            repo = ExcelRangeRepository(
                wb=wb,
                sheet_name=sheet_name,
                aa_search_ranges=config.AA_SEARCH_RANGES,
                grid_topleft_offset=config.GRID_TOPLEFT_OFFSET,
                ref_color_cells=config.REF_COLOR_CELLS,   # ★これ
                enable_debug=True,
            )

        except Exception as e:
            messagebox.showerror("Repository Error", f"Repository初期化に失敗:\n{e}")
            raise

        # -------------------------
        # Judges 初期化
        # -------------------------
        # JUEGOJudge が repo を受け取る想定（あなたの実装に合わせてOK）
        juego_judge = JUEGOJudge(repo)

        # Yokosawa はまだ未実装でも起動させるためのダミー
        # 後で本物に差し替えればOK
        yokosawa_judge = None

        # -------------------------
        # Controller 初期化（あなたの __init__ 仕様に合わせる）
        # -------------------------
        self.controller = GameController(self, juego_judge, yokosawa_judge)

        # -------------------------
        # UI
        # -------------------------
        top = tk.Frame(root)
        top.pack(padx=10, pady=10)

        self.btn_juego = tk.Button(top, text="JUEGO (Beginner)", command=self.start_juego)
        self.btn_juego.pack(side=tk.LEFT, padx=5)

        self.btn_next = tk.Button(top, text="Next", command=self.on_next)
        self.btn_next.pack(side=tk.LEFT, padx=5)
        self.btn_next.pack_forget()  # ←追加：初期状態は非表示

        # --- 追加：回答ボタン ---
        ans = tk.Frame(root)
        ans.pack(padx=10, pady=5)
    
        self.btn_fold  = tk.Button(ans, text="FOLD",  width=10,command=lambda: self.on_answer("FOLD"))
        self.btn_raise = tk.Button(ans, text="RAISE", width=12, command=lambda: self.on_answer("RAISE"))
        
        self.btn_fold.pack(side=tk.LEFT, padx=5)
        self.btn_raise.pack(side=tk.LEFT, padx=5)
        
        cards_frame = tk.Frame(root)
        cards_frame.pack(padx=10, pady=10)

        self.card_labels = [
            tk.Label(cards_frame, text="card1"),
            tk.Label(cards_frame, text="card2"),
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
    def start_juego(self) -> None:
        # 開始後に何度も押されるとややこしいので無効化
        self.btn_juego.configure(state=tk.DISABLED)
        self.controller.start_juego_beginner()

    def on_answer(self, action: str) -> None:
        hand = self.var_hand.get().strip()
        pos = self.var_pos.get().strip()
        self.controller.submit(hand=hand, pos=pos, user_action=action)
    

    def on_next(self) -> None:
        self.controller.new_question()

    # -------------------------
    # Controller -> UI
    # -------------------------
    def hide_next_button(self) -> None:
        """Controller から呼ばれる想定: Next ボタンを隠す"""
        # Nextボタンは pack で配置しているので pack_forget
        self.btn_next.pack_forget()

    def show_next_button(self) -> None:
        """Controller から呼ばれる想定: Next ボタンを表示"""
        # 既に表示されている場合もあるので、重複packを避けたいならwinfo_managerで判定してもよい
        if self.btn_next.winfo_manager() == "":
            self.btn_next.pack(side=tk.LEFT, padx=5)

    def deal_cards(self, hole_cards: list[str]) -> None:
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
    # Card image
    # -------------------------
    def _set_card_image(self, label: tk.Label, card_code: str) -> None:
        from PIL import Image, ImageTk  # Pillow 必須

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
        label.image = tk_img  # 参照保持


if __name__ == "__main__":
    root = tk.Tk()
    PokerTrainerUI(root)
    root.mainloop()
