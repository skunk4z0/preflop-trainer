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
AA_SEARCH_RANGES = {
    "OR":  "F11:BL26",
    "ROL": "U28:BL43",
}


# =========================
# Grid Layout
# =========================
# AA 起点からレンジグリッド左上(top-left)へのオフセット
# (row_offset, col_offset)
GRID_TOPLEFT_OFFSETS = {
    "OR":  (-1, -1),
    "ROL": (-1, -1),
}


# =========================
# Reference Color Samples
# =========================
# AA 起点からの相対位置で色見本セルを読む
# ※「探索」はしない（AA選別後に直接参照）
REF_COLOR_OFFSETS = {
    "OR": {
        "TIGHT": (11, 1),
        "LOOSE": (12, 1),
    },
    # ROL で色判定を行う場合はここに追加
    # "ROL": {
    #     "TIGHT": (...),
    #     "LOOSE": (...),
    # },
}
