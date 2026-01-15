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


# config.py
REF_COLOR_CELLS = {
"OR": {
"TIGHT": "H25",
"LOOSE": "H26",
},
"OR_SB": {
"RAISE_3BB": "CF24", 
"LimpCx3o": "CF25",    
"LimpCx2.5o": "CF26",  
"LimpCx2.25o": "CJ25", 
"LimpCx2o": "CJ26",    
},
"ROL": {
"AlwaysROL": "J41",  
"ROLvsFISH": "J42",
"OLvsFISH": "J43",  
},
}
