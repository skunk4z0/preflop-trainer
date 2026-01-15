# config.py
from __future__ import annotations

# =========================
# Paths
# =========================

# Excel（JUEGO レンジ表）
EXCEL_PATH = r"C:\MyPokerApp\juego_ranges.xlsx"

# カード画像フォルダ
CARD_IMAGE_DIR = r"C:\MyPokerApp\cards"


# =========================
# AA Anchor Search Ranges
# =========================
# 問題種別ごとに AA セルを探索する範囲（A1表記）
# ※キーはコード側で扱いやすいように "OR/SB" -> "OR_SB" に統一
AA_SEARCH_RANGES = {
    "OR":    "F11:BL26",     # EP〜BTN
    "ROL":   "U28:BL43",
    "OR_SB": "CC11:CP26",    # SB 用（特殊）
}


# =========================
# Grid Layout
# =========================
# AA 起点からレンジグリッド左上(top-left)へのオフセット
# (row_offset, col_offset)
# ※どの表でも同じなら単一でOK
GRID_TOPLEFT_OFFSET = (-1, -1)


# =========================
# Reference Color Samples
# =========================
# AA 起点からの相対位置で「見本セル」を読む
# ※AA選別後に直接参照（探索しない）
#
# 重要:
# - ここに書いたキー（Action名）が、そのまま判定ロジック側のラベルになります
# - OR は "TIGHT/LOOSE" など「色クラス」
# - OR_SB / ROL は「アクションごとに見本セルが別」なので、アクション名をキーにします
REF_COLOR_OFFSETS = {
    # -------------------------
    # OR (EP〜BTN)
    # -------------------------
    "OR": {
        "TIGHT": (11, 1),
        "LOOSE": (12, 1),
    },

    # -------------------------
    # OR_SB (SB特殊：アクション別に見本セルがある)
    # -------------------------
    "OR_SB": {
        "RAISE_3BB":   (11, 2),
        "LimpCx3o":    (12, 2),
        "LimpCx2.5o":  (13, 2),
        "LimpCx2.25o": (11, 6),
        "LimpCx2o":    (12, 6),
    },

    # -------------------------
    # ROL（アクション別に見本セルがある前提）
    # -------------------------
    "ROL": {
        "AlwaysROL":  (10, -12),
        "ROLvsFISH":  (11, -12),
        "OLvsFISH":   (12, -12),
    },
}
