# config.py
from __future__ import annotations

"""
Poker Trainer / JUEGO 設定

用語メモ（注釈）
- kind: 表の種類キー（例: "OR", "OR_SB", "ROL"）
- AA_SEARCH_RANGES: kind ごとに「pos文字列（EP/MP/CO/BTN/SB 等）」を探す範囲（A1表記）
- GRID_TOPLEFT_OFFSET: AAアンカーセルから 13×13 グリッド左上へ移動するオフセット (row_offset, col_offset)
- REF_COLOR_CELLS: 色見本セルの場所。Repository がここを読んで tag を決める
"""

# =========================
# Paths
# =========================

# Excel（JUEGO レンジ表）
# NOTE:
# ここは必ず実ファイルに合わせて更新してください。
# 例: r"C:\MyPokerApp\PREFLOP_GAME_FOR_BEGINNERS-INTERMEDIATE.xlsx"
EXCEL_PATH = r"C:\MyPokerApp\PREFLOP_GAME_FOR_BEGINNERS-INTERMEDIATE.xlsx"

# 参照するシート名（Workbook 内のシート名と一致させる）
# NOTE: 新Excelでシート名が違う場合はここを更新
SHEET_NAME = "zeros_range"

# カード画像フォルダ
CARD_IMAGE_DIR = r"C:\MyPokerApp\cards"


# =========================
# AA Anchor Search Ranges
# =========================
# 問題種別ごとに「posセル」を探索する範囲（A1表記）
# posセルから (down=+3, left=-2) が "AA" アンカー
AA_SEARCH_RANGES = {
    "OR":    "F11:BL26",     # EP〜BTN
    "ROL":   "U28:DE43",
    "OR_SB": "CC11:CP26",    # SB 用（特殊）
    "3BET":  "C54:BK98",
}


# =========================
# Grid Layout
# =========================
# AA 起点からレンジグリッド左上(top-left)へのオフセット
# (row_offset, col_offset)
#
# NOTE:
# - ここがズレると (r0,c0) の参照セルが全てズレます。
# - enable_debug=True にして repo_dbg の "grid_topleft" と "cell_rgb" を見て検証してください。
GRID_TOPLEFT_OFFSET = (0, 0)
    

# =========================
# Reference Color Cells (Fixed)
# =========================
# kind -> tag -> "A1セル番地"
#
# 注釈：
# - Repository は、このセルの塗りつぶし色(RGB)を読み取って「見本色」とする
# - ハンドセルの色(RGB)と一致した tag を返す
# - 無色/不一致は "FOLD" 扱い（Repository 側ロジック）
REF_COLOR_CELLS = {
    "OR": {
        "TIGHT": "H25",
        "LOOSE": "H26",
    },

    # SB（特殊）
    # - OR_SB は複数タグを扱う
    "OR_SB": {
        "RAISE_3BB":   "CF24",
        "LimpCx3o":    "CF25",
        "LimpCx2.5o":  "CF26",
        "LimpCx2.25o": "CJ25",
        "LimpCx2o":    "CJ26",
    },

    "ROL": {
        "AlwaysROL": "J41",
        "ROLvsFISH": "J42",
        "OLvsFISH":  "J43",
    },

    "3BET": {
        "3bet/5Bet": "F49",
        "3bet/Fold4bet": "F50",
        "3bet/C4bet": "F51",
        "C4bet_Situacional": "F52",
        "CCvs3.5x": "L49",
        "CCvs3x": "L50",
        "CCvs2.5x": "L51",
        "CCvs2.25x": "Q49",
        "CCvs2x": "Q50",
        },

}
