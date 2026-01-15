# excel_range_repository.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from openpyxl.workbook.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet


@dataclass(frozen=True)
class AnchorMatch:
    aa_row: int
    aa_col: int
    aa_addr: str


class ExcelRangeRepository:
    """
    Excelレンジ表を AA 起点で参照する Repository。

    AA選別ルール（固定）:
    - "AA" セルが複数存在しうる
    - 正しいAAは以下が一致するもの
        * AA から 左1 上3 ＝ kind
        * AA から 右2 上3 ＝ pos
    - AA探索は kind ごとに指定した A1 範囲内のみ
    """

    def __init__(
        self,
        wb: Workbook,
        sheet_name: str,
        aa_search_ranges: Dict[str, str],
        grid_topleft_offset: Tuple[int, int],   # ← 単一オフセット
        ref_color_offsets: Optional[Dict[str, Dict[str, Tuple[int, int]]]] = None,
    ) -> None:
        if sheet_name not in wb.sheetnames:
            raise ValueError(f"Sheet not found: {sheet_name}. Available={wb.sheetnames}")

        self.wb: Workbook = wb
        self.ws: Worksheet = wb[sheet_name]

        self.aa_search_ranges = dict(aa_search_ranges)
        self.grid_topleft_offset = grid_topleft_offset
        self.ref_color_offsets = dict(ref_color_offsets or {})

        # (kind, pos) -> (aa_row, aa_col)
        self._anchor_cache: Dict[Tuple[str, str], Tuple[int, int]] = {}

    # =========================
    # Anchor (AA)
    # =========================

    def find_aa_anchor(self, kind: str, pos: str) -> Tuple[int, int]:
        cache_key = (kind, pos)
        if cache_key in self._anchor_cache:
            return self._anchor_cache[cache_key]

        if kind not in self.aa_search_ranges:
            raise KeyError(
                f"AA search range not defined for kind={kind}. "
                f"Defined kinds={list(self.aa_search_ranges.keys())}"
            )

        a1_range = self.aa_search_ranges[kind]
        matches: list[AnchorMatch] = []
        aa_candidates = 0

        for row in self.ws[a1_range]:
            for cell in row:
                if cell.value != "AA":
                    continue

                aa_candidates += 1
                r, c = cell.row, cell.column

                kind_cell = self.ws.cell(row=r - 3, column=c - 1).value
                pos_cell  = self.ws.cell(row=r - 3, column=c + 2).value

                if kind_cell == kind and pos_cell == pos:
                    matches.append(AnchorMatch(r, c, cell.coordinate))

        if not matches:
            raise ValueError(
                f"AA anchor not found in range={a1_range} for kind={kind}, pos={pos}. "
                f"AA candidates found={aa_candidates}"
            )

        matches.sort(key=lambda m: (m.aa_row, m.aa_col))
        chosen = matches[0]

        self._anchor_cache[cache_key] = (chosen.aa_row, chosen.aa_col)
        return self._anchor_cache[cache_key]

    # =========================
    # Grid addressing
    # =========================

    def get_grid_top_left(self, kind: str, pos: str) -> Tuple[int, int]:
        """
        AAアンカーからグリッド左上(top-left)の座標(row,col)を返す。
        GRID_TOPLEFT_OFFSET は全表共通。
        """
        aa_row, aa_col = self.find_aa_anchor(kind, pos)
        dr, dc = self.grid_topleft_offset
        return aa_row + dr, aa_col + dc

    def get_cell_value_at_grid(self, kind: str, pos: str, r0: int, c0: int) -> Any:
        top_r, top_c = self.get_grid_top_left(kind, pos)
        return self.ws.cell(row=top_r + r0, column=top_c + c0).value

    def get_cell_fill_rgb_at_grid(self, kind: str, pos: str, r0: int, c0: int) -> Optional[str]:
        top_r, top_c = self.get_grid_top_left(kind, pos)
        cell = self.ws.cell(row=top_r + r0, column=top_c + c0)
        return self._read_fill_rgb(cell)

    # =========================
    # Reference colors
    # =========================

    def get_ref_colors(self, kind: str, pos: str) -> Dict[str, Optional[str]]:
        if kind not in self.ref_color_offsets:
            raise KeyError(
                f"REF_COLOR_OFFSETS not defined for kind={kind}. "
                f"Defined kinds={list(self.ref_color_offsets.keys())}"
            )

        aa_row, aa_col = self.find_aa_anchor(kind, pos)
        result: Dict[str, Optional[str]] = {}

        for tag, (dr, dc) in self.ref_color_offsets[kind].items():
            cell = self.ws.cell(row=aa_row + dr, column=aa_col + dc)
            result[tag] = self._read_fill_rgb(cell)

        return result

    def get_tag_at_grid(self, kind: str, pos: str, r0: int, c0: int) -> str:
        """
        グリッド上セルの色を、AA起点の見本セル色と照合し、
        一致したタグを返す。
        一致なし/色なしは "FOLD"。
        """
        cell_rgb = self.get_cell_fill_rgb_at_grid(kind, pos, r0, c0)
        if cell_rgb is None:
            return "FOLD"

        ref = self.get_ref_colors(kind, pos)
        cell_rgb = str(cell_rgb).upper()

        for tag, ref_rgb in ref.items():
            if ref_rgb and cell_rgb == str(ref_rgb).upper():
                return tag

        return "FOLD"

    # =================
