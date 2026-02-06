from __future__ import annotations

import json
from pathlib import Path

import openpyxl

from config import (
    EXCEL_PATH,
    SHEET_NAME,
    AA_SEARCH_RANGES,
    GRID_TOPLEFT_OFFSET,
    REF_COLOR_CELLS,
    FINAL_TAGS_JSON_PATH,
)
from excel_range_repository import ExcelRangeRepository

def all_hand_keys_169() -> list[str]:
    ranks = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"]
    out: list[str] = []
    for i, r1 in enumerate(ranks):
        for j, r2 in enumerate(ranks):
            if i == j:
                out.append(f"{r1}{r2}")      # AA, KK...
            elif i < j:
                out.append(f"{r1}{r2}S")     # AKS, AQS...
            else:
                out.append(f"{r2}{r1}O")     # AKo, AQo...
    return out



def main() -> None:
    excel_path = Path(EXCEL_PATH)
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel not found: {excel_path}")

    # Excelを読む（移行のための一回だけ）
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    repo = ExcelRangeRepository(
        wb=wb,
        sheet_name=SHEET_NAME,
        aa_search_ranges=AA_SEARCH_RANGES,
        grid_topleft_offset=GRID_TOPLEFT_OFFSET,
        ref_color_cells=REF_COLOR_CELLS,
    )

    # 最終タグJSON（A案）を作る
    # JsonRangeRepositoryが読むのは root["ranges"]
    final: dict = {
        "meta": {
            "source": str(excel_path),
            "sheet": SHEET_NAME,
        },
        "ranges": {},
    }

    # kindごとにposition一覧を取り、169ハンド分のtagを作る
    for kind in AA_SEARCH_RANGES.keys():
        kind_raw = str(kind).strip()
        kind_u = kind_raw.upper()

        positions = repo.list_positions(kind_raw)
        if not positions:
            continue

        final["ranges"][kind_u] = {}

        for pos in positions:
            pos_raw = str(pos).strip()
            pos_u = pos_raw.upper()

            final["ranges"][kind_u][pos_u] = {}

            for hk in all_hand_keys_169():
                tag, _dbg = repo.get_tag_for_hand(kind_raw, pos_raw, hk)
                final["ranges"][kind_u][pos_u][hk] = tag




    # 出力
    out_path = Path(FINAL_TAGS_JSON_PATH)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: wrote {out_path}")





if __name__ == "__main__":
    main()
