import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk  # 画像処理ライブラリ
import random
import os

# --- 設定：画像のフォルダパス ---
# あなたの環境に合わせてパスを調整しています
IMAGE_DIR = r"C:\Users\user\Desktop\cards"

# --- データの定義 (スプレッドシートに基づく抜粋) ---
RANGES = {
    "Early Position (UTG)": ["AA", "KK", "QQ", "JJ", "TT", "AKs", "AQs", "AJs", "ATs", "AKo", "AQo"],
    "Button (BTN)": ["AA", "KK", "QQ", "JJ", "TT", "AKs", "AQs", "A5s", "KQs", "JTs", "54s", "AKo", "KQo", "JTo"]
}
# フォルダ内にある画像ファイル名からハンドのリストを自動作成（拡張子を除く）
ALL_HANDS = [f.split('.')[0] for f in os.listdir(IMAGE_DIR) if f.endswith(('.png', '.jpg'))]

class PokerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Poker Training Tool")
        self.root.geometry("500x700")
        self.root.configure(bg="#2c3e50") # 背景色を少しカッコよく

        self.current_pos = ""
        self.current_hand = ""

        # ポジション表示
        self.label_pos = tk.Label(root, text="", font=("MS Gothic", 20, "bold"), fg="white", bg="#2c3e50")
        self.label_pos.pack(pady=20)

        # 画像表示エリア
        self.image_label = tk.Label(root, bg="#2c3e50")
        self.image_label.pack(pady=20)

        # ボタンフレーム
        btn_frame = tk.Frame(root, bg="#2c3e50")
        btn_frame.pack(pady=30)

        # RAISEボタン (赤)
        self.btn_raise = tk.Button(btn_frame, text="RAISE", bg="#e74c3c", fg="white", 
                                   font=("Arial", 14, "bold"), width=12, height=2,
                                   command=lambda: self.check_answer("r"))
        self.btn_raise.grid(row=0, column=0, padx=20)

        # FOLDボタン (青)
        self.btn_fold = tk.Button(btn_frame, text="FOLD", bg="#3498db", fg="white", 
                                  font=("Arial", 14, "bold"), width=12, height=2,
                                  command=lambda: self.check_answer("f"))
        self.btn_fold.grid(row=0, column=1, padx=20)

        self.next_question()

    def next_question(self):
        # ランダムに出題
        self.current_pos = random.choice(list(RANGES.keys()))
        self.current_hand = random.choice(ALL_HANDS)

        # ポジションテキスト更新
        self.label_pos.config(text=f"Position: {self.current_pos}")

        # 画像の読み込み
        img_path = os.path.join(IMAGE_DIR, f"{self.current_hand}.png")
        if os.path.exists(img_path):
            img = Image.open(img_path)
            img = img.resize((300, 400), Image.LANCZOS) # サイズを調整
            self.photo = ImageTk.PhotoImage(img)
            self.image_label.config(image=self.photo)
        else:
            self.image_label.config(image='', text=f"画像なし\n({self.current_hand})", fg="yellow", font=("Arial", 20))

    def check_answer(self, user_choice):
        is_raise = self.current_hand in RANGES.get(self.current_pos, [])
        correct_key = "r" if is_raise else "f"

        if user_choice == correct_key:
            messagebox.showinfo("Result", "Nice Hand! (正解)")
        else:
            action = "RAISE" if is_raise else "FOLD"
            messagebox.showerror("Result", f"Incorrect...\nCorrect action: {action}")
        
        self.next_question()

if __name__ == "__main__":
    # もしPillowがない場合は pip install Pillow を実行してください
    root = tk.Tk()
    app = PokerGUI(root)
    root.mainloop()
