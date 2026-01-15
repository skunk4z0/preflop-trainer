# excel_range_repository.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from openpyxl.workbook.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet


@dataclass(frozen=True)
class AnchorMatch:
    pos_cell_addr: str
    pos_row: int
    pos_col: int
    aa_row: int
    aa_col: int
    aa_addr: str


class ExcelRangeRepository:
    """
    Excelレンジ表を参照する Repository（posセル起点）。

    仕様（あなたの説明どおり）:
    1) AA_SEARCH_RANGES[kind] 内で pos名(EP/MP/CO/BTN...) を検索
    2) posセルから (down=+3, left=-2) のセルが "AA"
    3) AAセルから GRID_TOPLEFT_OFFSET で 13x13 グリッド左上を求める
    4) 13x13 内で hand_key（例: A5o / 44）文字列検索
       - 見つからない → "FOLD"
       - 見つかる → そのセル色を読み、見本色と照合しタグを返す

    見本色:
    - kind ごとに config で固定セル番地を持つ（ref_color_cells[kind][tag] = "H25" など）
    """

    def __init__(
        self,
        wb: Workbook,
        sheet_name: str,
        aa_search_ranges: Dict[str, str],                    # kind -> A1 range
        grid_topleft_offset: Tuple[int, int],                # AA -> grid top-left (dr, dc)
        ref_color_cells: Dict[str, Dict[str, str]],          # kind -> tag -> "H25"
        enable_debug: bool = False,
    ) -> None:
        if sheet_name not in wb.sheetnames:
            raise ValueError(f"Sheet not found: {sheet_name}. Available={wb.sheetnames}")

        self.wb: Workbook = wb
        self.ws: Worksheet = wb[sheet_name]

        self.aa_search_ranges = dict(aa_search_ranges)
        self.grid_topleft_offset = grid_topleft_offset
        self.ref_color_cells = dict(ref_color_cells)
        self.enable_debug = enable_debug

        # (kind, pos) -> AnchorMatch
        self._anchor_cache: Dict[Tuple[str, str], AnchorMatch] = {}

    # =========================
    # Anchor (pos -> AA)
    # =========================

    def find_anchor_by_pos(self, kind: str, pos: str) -> AnchorMatch:
        cache_key = (kind, pos)

        if cache_key in self._anchor_cache:
            m = self._anchor_cache[cache_key]

            # debug 属性が無くても落ちない
            if getattr(self, "debug", False):
                self._log(
                    f"[REPO][ANCHOR] cached "
                    f"pos_cell={m.pos_cell} -> AA={m.aa_cell} "
                    f"(kind={kind} pos={pos})"
                )

            return m

    # 以下、既存の探索ロジック…


    # --- ② キャッシュミス（ここから探索） ---
    # ↓↓↓ 既存のアンカー探索ロジック（そのまま）


        if kind not in self.aa_search_ranges:
            raise KeyError(
                f"AA search range not defined for kind={kind}. "
                f"Defined kinds={list(self.aa_search_ranges.keys())}"
            )

        a1_range = self.aa_search_ranges[kind]
        candidates: list[AnchorMatch] = []

        for row in self.ws[a1_range]:
            for cell in row:
                if cell.value != pos:
                    continue

                pr, pc = cell.row, cell.column
                aa_r, aa_c = pr + 3, pc - 2
                aa_cell = self.ws.cell(row=aa_r, column=aa_c)

                if aa_cell.value != "AA":
                    if self.enable_debug:
                        print(
                            f"[REPO][ANCHOR] pos found at {cell.coordinate} but AA check failed "
                            f"(expected AA at {aa_cell.coordinate}, got {aa_cell.value!r})",
                            flush=True,
                        )
                    continue

                candidates.append(
                    AnchorMatch(
                        pos_cell_addr=cell.coordinate,
                        pos_row=pr,
                        pos_col=pc,
                        aa_row=aa_r,
                        aa_col=aa_c,
                        aa_addr=aa_cell.coordinate,
                    )
                )

        if not candidates:
            raise ValueError(
                f"Anchor not found for kind={kind}, pos={pos} within range={a1_range}. "
                f"(pos cell '{pos}' not found OR AA offset cell not 'AA')"
            )

        candidates.sort(key=lambda m: (m.pos_row, m.pos_col))
        chosen = candidates[0]
        self._anchor_cache[cache_key] = chosen

        if self.enable_debug:
            print(
                f"[REPO][ANCHOR] chosen pos_cell={chosen.pos_cell_addr} -> AA={chosen.aa_addr} (kind={kind} pos={pos})",
                flush=True,
            )

        return chosen

    # =========================
    # Grid addressing
    # =========================

    def get_grid_top_left(self, kind: str, pos: str) -> Tuple[int, int]:
        """
        AAアンカーからグリッド左上(top-left)の座標(row,col)を返す。
        """
        anchor = self.find_anchor_by_pos(kind, pos)
        dr, dc = self.grid_topleft_offset
        return anchor.aa_row + dr, anchor.aa_col + dc

    def get_cell_value_at_grid(self, kind: str, pos: str, r0: int, c0: int) -> Any:
        top_r, top_c = self.get_grid_top_left(kind, pos)
        return self.ws.cell(row=top_r + r0, column=top_c + c0).value

    def get_cell_fill_rgb_at_grid(self, kind: str, pos: str, r0: int, c0: int) -> str:
        top_r, top_c = self.get_grid_top_left(kind, pos)
        cell = self.ws.cell(row=top_r + r0, column=top_c + c0)
        return self._read_fill_rgb(cell)

    # =========================
    # Reference colors (fixed cells by kind)
    # =========================

    def get_ref_colors(self, kind: str) -> Dict[str, str]:
        """
        kind ごとに定義された「固定セル番地」から見本色を読む。
        """
        if kind not in self.ref_color_cells:
            raise KeyError(
                f"REF_COLOR_CELLS not defined for kind={kind}. "
                f"Defined kinds={list(self.ref_color_cells.keys())}"
            )

        result: Dict[str, str] = {}
        for tag, addr in self.ref_color_cells[kind].items():
            cell = self.ws[addr]
            rgb = self._read_fill_rgb(cell)
            result[tag] = rgb

            if self.enable_debug:
                fg = getattr(cell.fill, "fgColor", None)
                print(
                    f"[REPO][REF-FIXED] kind={kind} tag={tag} cell={cell.coordinate} "
                    f"patternType={getattr(cell.fill,'patternType',None)} "
                    f"fg.type={getattr(fg,'type',None)} fg.rgb={getattr(fg,'rgb',None)} "
                    f"fg.theme={getattr(fg,'theme',None)} fg.indexed={getattr(fg,'indexed',None)} "
                    f"read_rgb={rgb}",
                    flush=True,
                )

        return result

    # =========================
    # Color reader
    # =========================

    def _read_fill_rgb(self, cell) -> str:
        """
        openpyxl Cell の塗りつぶし色(RGB)を "RRGGBB" で返す。
        塗りつぶし無し/取得不能は ""。

        重要:
        - patternType が無い/none の場合は "" にする（無色の誤一致を防ぐ）
        - theme/indexed はまず "" 扱い（必要なら後で拡張）
        """
        fill = getattr(cell, "fill", None)
        if fill is None:
            return ""

        pattern = getattr(fill, "patternType", None)
        if pattern is None or str(pattern).lower() in ("none", "null"):
            return ""

        fg = getattr(fill, "fgColor", None)
        if fg is None:
            return ""

        fg_type = getattr(fg, "type", None)
        if fg_type not in (None, "rgb"):
            return ""

        rgb = getattr(fg, "rgb", None)
        if not rgb:
            return ""

        rgb = str(rgb).upper()
        if len(rgb) == 8:
            rgb = rgb[-6:]
        elif len(rgb) != 6:
            return ""

        if rgb == "000000":
            return ""

        return rgb

    # =========================
    # Tag decision (single implementation)
    # =========================

    def get_tag_for_hand(self, kind: str, pos: str, hand_key: str) -> Tuple[str, Dict[str, Any]]:
        """
        hand_key を 13x13 グリッド内で文字列検索してタグを返す。
        戻り値: (tag, repo_debug)
        """
        top_r, top_c = self.get_grid_top_left(kind, pos)

                # 13x13 内で hand_key を検索（空白除去 + "66+" などにも対応）
        found_cell = None
        found_rc = None

        for r0 in range(13):
            for c0 in range(13):
                cell = self.ws.cell(row=top_r + r0, column=top_c + c0)
                v = cell.value

                # 文字列なら空白除去して比較、None なら空文字
                v_norm = (v.strip() if isinstance(v, str) else ("" if v is None else str(v)))

                # 完全一致（いままで通り）
                if v_norm == hand_key:
                    found_cell = cell
                    found_rc = (r0, c0)
                    break

                # 追加： "66+" や "KJo+" のような表記も拾う
                if isinstance(v, str) and v_norm.startswith(hand_key):
                    found_cell = cell
                    found_rc = (r0, c0)
                    break

            if found_cell is not None:
                break
  

        if found_cell is None:
            if self.enable_debug:
                anchor = self.find_anchor_by_pos(kind, pos)
                print(
                    f"[REPO][FIND] hand={hand_key} NOT found "
                    f"(kind={kind} pos={pos} AA={anchor.aa_addr} grid_top_left=({top_r},{top_c}))",
                    flush=True,
                )
                # 先頭数セルをダンプ（ズレ確認用）
                for rr in range(3):
                    row_vals = []
                    for cc in range(6):
                        vv = self.ws.cell(row=top_r + rr, column=top_c + cc).value
                        row_vals.append("" if vv is None else str(vv))
                    print(f"[REPO][GRID] r{rr}: {row_vals}", flush=True)

            return "FOLD", {
                "kind": kind,
                "pos": pos,
                "hand": hand_key,
                "found": False,
                "reason": "hand_not_found_in_grid",
            }

        if self.enable_debug:
            print(
                f"[REPO][FIND] hand={hand_key} found at {found_cell.coordinate} "
                f"(r0={found_rc[0]} c0={found_rc[1]} kind={kind} pos={pos})",
                flush=True,
            )

        # 対象セル色
        cell_rgb = self._read_fill_rgb(found_cell)
        if self.enable_debug:
            fg = getattr(found_cell.fill, "fgColor", None)
            print(
                f"[REPO][TARGET] cell={found_cell.coordinate} value={found_cell.value!r} rc={found_rc} "
                f"patternType={getattr(found_cell.fill,'patternType',None)} "
                f"fg.type={getattr(fg,'type',None)} fg.rgb={getattr(fg,'rgb',None)} "
                f"read_rgb={cell_rgb}",
                flush=True,
            )

        # 見本色
        ref = self.get_ref_colors(kind)

        tag = "FOLD"
        if cell_rgb:
            cell_u = cell_rgb.upper()
            for t, ref_rgb in ref.items():
                if ref_rgb and cell_u == ref_rgb.upper():
                    tag = t
                    break

        dbg: Dict[str, Any] = {
            "kind": kind,
            "pos": pos,
            "hand": hand_key,
            "found": True,
            "cell": found_cell.coordinate,
            "grid_rc": found_rc,
            "cell_rgb": cell_rgb,
            "ref_colors": ref,
        }

        if tag == "FOLD" and cell_rgb:
            dbg["reason"] = "no_ref_match"
        elif tag == "FOLD":
            dbg["reason"] = "no_effective_fill"
        else:
            dbg["match"] = {"tag": tag, "ref_rgb": ref.get(tag, "")}

        return tag, dbg
