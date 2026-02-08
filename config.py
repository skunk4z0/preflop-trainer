# config.py
from __future__ import annotations
from pathlib import Path

EXCEL_PATH = r"C:\MyPokerApp\data_src\PREFLOP_GAME_FOR_BEGINNERS-INTERMEDIATE.xlsx"

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = (BASE_DIR / "data").resolve()

JSON_PATH = (DATA_DIR / "datasheet_ranges.json").resolve()
FINAL_TAGS_JSON_PATH = (DATA_DIR / "final_tags.json").resolve()



"""
Poker Trainer / JUEGO 設定

用語メモ（注釈）
- kind: 表の種類キー（例: "OR", "OR_SB", "ROL"）
- AA_SEARCH_RANGES: kind ごとに「posセル」を探索する範囲（A1表記）
- GRID_TOPLEFT_OFFSET: AAアンカーセルから 13×13 グリッド左上へ移動するオフセット (row_offset, col_offset)
- REF_COLOR_CELLS: 色見本セル（凡例）の定義。Repository がここを読んで tag を返す
"""
# =========================
# Paths
# =========================
SHEET_NAME = "Datasheet"
CARD_IMAGE_DIR = r"C:\MyPokerApp\cards"

# =========================
# AA Anchor Search Ranges
# =========================
# posセルから (down=+3, left=-2) が "AA" アンカー
AA_SEARCH_RANGES = {
    "OR":               "B2:BH17",     # EP〜BTN
    "ROL":              "B19:CL34",
    "OR_SB":            "BJ2:BW17",    # SB 用（特殊）
    "CC_3BET":          "B36:FI51",
    "3BET_VS_COLD4BET": "B53:BW68",
    "CALL_3BET_4BET":   "B70:EE85",
    "CC_3BET_MULTI":    "B87:ET102",
}

# =========================
# Grid Layout
# =========================
GRID_TOPLEFT_OFFSET = (0, 0)


# REF_COLOR_CELLS 運用ルール:
# - 基本はRGB直書き: "f4cccc" / "#f4cccc" / "FFf4cccc"（最終的に6桁RGBへ正規化される）
# - 例外としてセル番地(A1)も許可: "D144" など（黒/テーマ色などExcel依存の回避用）
# - ビルド時に get_ref_colors() が正規化・検証し、読めない場合は例外で停止する（静かに壊さない）
# - 黒("000000")も有効色として扱う（無色扱いしない）


REF_COLOR_CELLS = {
    # ========= OR =========
    "OR": {
        # 旧: TIGHT / LOOSE
        "OPEN_TIGHT": "9fc5e8",
        "OPEN_LOOSE": "f4cccc",
    },

    # ========= OR_SB =========
    "OR_SB": {
        # 旧: RAISE_3BB
        "OPEN_3_BB":         "f4cccc",
        # 旧: LimpCx*o
        "LIMP_CALL_3_BB":    "6aa84f",
        "LIMP_CALL_2_5_BB":  "b6d7a8",
        "LIMP_CALL_2_25_BB": "d9d2e9",
        "LIMP_CALL_2_BB":    "ffe599",
    },

    # ========= ROL =========
    "ROL": {
        # 旧: AlwaysROL / ROLvsFISH / OLvsFISH
        "ROL_ALWAYS":       "9fc5e8",
        "ROL_VS_FISH":      "f4cccc",
        "OVERLIMP_VS_FISH": "d9ead3",
    },

    # ========= CC_3BET =========
    # 3bet後の4bet対応 + オープンサイズ別コール
    "CC_3BET": {
        # 旧: 3bet/5Bet / 3bet/Fold4bet / 3bet/C4bet / C4bet_Situacional
        "3BET_VS_4BET_SHOVE":            "660000",
        "3BET_VS_4BET_FOLD":             "cc0000",
        "3BET_VS_4BET_CALL":             "1c4587",
        "3BET_VS_4BET_CALL_SITUATIONAL": "a4c2f4",

        # 旧: CCvs3.5x など（定義: “X以下ならコール”）
        "CALL_VS_OPEN_LE_3_5X": "38761d",
        "CALL_VS_OPEN_LE_3X":   "6aa84f",
        "CALL_VS_OPEN_LE_2_5X": "b6d7a8",
        "CALL_VS_OPEN_LE_2_25X":"d9d2e9",
        "CALL_VS_OPEN_EQ_2X":   "ffe599",
    },

    # ========= 3BET_VS_COLD4BET =========
    "3BET_VS_COLD4BET": {
        "3BET_VS_4BET_SHOVE":            "660000",
        "3BET_VS_4BET_FOLD":             "cc0000",
        "3BET_VS_4BET_CALL":             "1c4587",
        "3BET_VS_4BET_CALL_SITUATIONAL": "a4c2f4",
    },

    # ========= CALL_3BET_4BET =========
    "CALL_3BET_4BET": {
        # 旧: 4BetCallvsAI / 4Bet/Fold5bet
        "4BET_VS_5BET_CALL": "660000",
        "4BET_VS_5BET_FOLD": "cc0000",

        # 旧: AIvs12bbs/4Bet_C(IP) / AIvs13.5bbs/4Bet_C(IP)
        # NOTE: ここは “IP/OOP の分岐” を後で入れる（色は同じでも意味が変わり得る）
        "SHOVE_VS_3BET_GE_12BB_IP":   "000000",
        "SHOVE_VS_3BET_GE_13_5BB_IP": "000000",

        # 旧: Call_3B_12bbs, Call_3B_9.5bbs, ...
        "CALL_VS_3BET_LE_12BB":  "1c4587",
        "CALL_VS_3BET_LE_9_5BB": "38761d",
        "CALL_VS_3BET_LE_8BB":   "6aa84f",
        "CALL_VS_3BET_LE_7BB":   "b6d7a8",
        "CALL_VS_3BET_LE_6BB":   "d9d2e9",
        "CALL_VS_3BET_LE_5BB":   "ffe599",

        # 旧: Fold（ピンク）
        "FOLD_VS_3BET": "e6b8af",
    },

    # ========= CC_3BET_MULTI =========
    # 旧configは同一キーの重複で壊れてた（最後の1個しか残らない）ので修正
    "CC_3BET_MULTI": {
        "3BET_VS_4BET_SHOVE": "660000",
        "3BET_VS_4BET_FOLD":  "cc0000",

        "CALL_VS_OPEN_LE_3_5X":  "38761d",
        "CALL_VS_OPEN_LE_3X":    "6aa84f",
        "CALL_VS_OPEN_LE_2_5X":  "b6d7a8",
        "CALL_VS_OPEN_LE_2_25X": "d9d2e9",
        "CALL_VS_OPEN_EQ_2X":    "ffe599",
    },
}
