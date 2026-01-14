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
    Excelレンジ表を AA 起点で参照する Repository（表記ゆれ非対応・完全一致前提の最小構成）。

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
        grid_topleft_offsets: Dict[str, Tuple[int, int]],
        ref_color_offsets: Optional[Dict[str, Dict[str, Tuple[int, int]]]] = None,
    ) -> None:
        if sheet_name not in wb.sheetnames:
            raise ValueError(f"Sheet not found: {sheet_name}. Available={wb.sheetnames}")

        self.wb: Workbook = wb
        self.ws: Worksheet = wb[sheet_name]

        # config側で統一されている前提のため、ここで勝手に正規化しない
        self.aa_search_ranges: Dict[str, str] = dict(aa_search_ranges)
        self.grid_topleft_offsets: Dict[str, Tuple[int, int]] = dict(grid_topleft_offsets)
        self.ref_color_offsets: Dict[str, Dict[str, Tuple[int, int]]] = dict(ref_color_offsets or {})

        # (kind, pos) -> (aa_row, aa_col)
        self._anchor_cache: Dict[Tuple[str, str], Tuple[int, int]] = {}

    # -------------------------
    # Anchor (AA)
    # -------------------------

    def find_aa_anchor(self, kind: str, pos: str) -> Tuple[int, int]:
        """
        指定(kind,pos)に一致する AA アンカー座標(row,col)を返す。
        見つからない場合は ValueError。
        """
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

                # ルール：AAから左1上3＝種別、右2上3＝Pos
                kind_cell = self.ws.cell(row=r - 3, column=c - 1).value
                pos_cell  = self.ws.cell(row=r - 3, column=c + 2).value

                if kind_cell == kind and pos_cell == pos:
                    matches.append(AnchorMatch(aa_row=r, aa_col=c, aa_addr=cell.coordinate))

        if not matches:
            raise ValueError(
                f"AA anchor not found in range={a1_range} for kind={kind}, pos={pos}. "
                f"AA candidates found in range={aa_candidates}. "
                f"Check labels at (AA row-3,col-1)=kind and (AA row-3,col+2)=pos."
            )

        # 複数一致は「上→左」で決定（決定的）
        matches.sort(key=lambda m: (m.aa_row, m.aa_col))
        chosen = matches[0]
    
        result = (chosen.aa_row, chosen.aa_col)
        self._anchor_cache[cache_key] = result
        return result

    # -------------------------
    # Grid addressing
    # -------------------------

    def get_grid_top_left(self, kind: str, pos: str) -> Tuple[int, int]:
        """
        AAアンカーからグリッド左上(top-left)の座標(row,col)を返す。
        """
        if kind not in self.grid_topleft_offsets:
            raise KeyError(
                f"GRID_TOPLEFT offset not defined for kind={kind}. "
                f"Defined kinds={list(self.grid_topleft_offsets.keys())}"
            )

        aa_row, aa_col = self.find_aa_anchor(kind, pos)
        dr, dc = self.grid_topleft_offsets[kind]
        return (aa_row + dr, aa_col + dc)

    def get_cell_value_at_grid(self, kind: str, pos: str, r0: int, c0: int) -> Any:
        """
        グリッド左上を(0,0)とした相対座標(r0,c0)のセル値を返す。
        """
        top_r, top_c = self.get_grid_top_left(kind, pos)
        return self.ws.cell(row=top_r + r0, column=top_c + c0).value

    def get_cell_fill_rgb_at_grid(self, kind: str, pos: str, r0: int, c0: int) -> Optional[str]:
        """
        グリッド左上を(0,0)とした相対座標(r0,c0)のセル塗りつぶしRGBを返す。
        取得不可/未設定は None。

        注意：条件付き書式の見た目色は openpyxl では取得できないことがあります。
        """
        top_r, top_c = self.get_grid_top_left(kind, pos)
        cell = self.ws.cell(row=top_r + r0, column=top_c + c0)
        return self._read_fill_rgb(cell)

    # -------------------------
    # Reference colors (optional)
    # -------------------------

    def get_ref_colors(self, kind: str, pos: str) -> Dict[str, Optional[str]]:
        """
        AA起点の色見本セル（config: ref_color_offsets）から RGB を取得して返す。
        例: {"TIGHT": "FFxxxxxx", "LOOSE": "FFyyyyyy"}
        """
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

    # -------------------------
    # Maintenance
    # -------------------------

    def clear_cache(self) -> None:
        self._anchor_cache.clear()

    # -------------------------
    # Internal
    # -------------------------

    @staticmethod
    def _read_fill_rgb(cell) -> Optional[str]:
        """
        cell.fill.fgColor.rgb を可能な範囲で返す。
        Returns: 'FFRRGGBB' 等 / 取得不可は None
        """
        fill = getattr(cell, "fill", None)
        if fill is None or getattr(fill, "patternType", None) is None:
            return None

        color = getattr(fill, "fgColor", None)
        if color is None:
            return None

        rgb = getattr(color, "rgb", None)
        if rgb:
            return str(rgb)

        # theme/indexed などはここでは扱わない（必要になったら拡張）
        return None
