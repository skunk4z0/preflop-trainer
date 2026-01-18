# excel_range_repository.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

from openpyxl.workbook.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet


# =========================
# Hand key -> grid (r0,c0)
# =========================

RANKS = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"]
RANK_TO_I = {r: i for i, r in enumerate(RANKS)}


def _rank_index(r: str) -> int:
    r = str(r).upper()
    if r == "10":
        r = "T"
    return RANK_TO_I[r]


def _normalize_hand_to_key(hand: str) -> str:
    """
    hand が "AKs"/"AKo"/"AA" などの既存キーの場合はそのまま。
    hand が "KsJc" / "AsKd" など2枚表記(4文字)の場合は "KJO" / "AKO" に正規化。

    NOTE:
    - 返り値は内部処理用に大文字化する（"S"/"O"）。
    """
    h = hand.strip()

    # 既に "AKs" / "KQo" / "AA" 形式っぽい
    if len(h) in (2, 3):
        return h.upper()

    # "KsJc" など（4文字想定: RankSuit + RankSuit）
    if len(h) == 4:
        r1, s1, r2, s2 = h[0].upper(), h[1].lower(), h[2].upper(), h[3].lower()

        # pair
        if r1 == r2:
            return f"{r1}{r2}"

        i1, i2 = _rank_index(r1), _rank_index(r2)
        hi, lo = (r1, r2) if i1 < i2 else (r2, r1)
        suited = (s1 == s2)
        return f"{hi}{lo}{'S' if suited else 'O'}"

    raise ValueError(f"Unrecognized hand format: {hand!r}")

def _expected_cell_label_from_hand_key(hand_key: str) -> str:
    """
    新Excelのセル内表示は末尾の s/o が無い想定。
    - "AKS"/"AKO" -> "AK"
    - "AA" -> "AA"
    """
    hk = hand_key.strip().upper()
    if len(hk) == 2:
        return hk
    if len(hk) == 3 and hk[2] in ("S", "O"):
        return hk[:2]
    raise ValueError(f"Unrecognized hand_key for label: {hand_key!r}")


def _hand_key_to_rc(hand_key: str) -> Tuple[int, int]:
    """
    hand_key: "AKS" / "AKO" / "AA"
    returns: (r0,c0) in [0..12]
      - diagonal: pair
      - upper triangle: suited
      - lower triangle: offsuit

    グリッド仕様:
      上三角 = suited, 下三角 = offsuit, 対角 = pair
    """
    hk = hand_key.strip().upper()

    # pair
    if len(hk) == 2:
        r = hk[0]
        i = _rank_index(r)
        return (i, i)

    # non-pair
    if len(hk) == 3 and hk[2] in ("S", "O"):
        r1, r2, so = hk[0], hk[1], hk[2]
        i1, i2 = _rank_index(r1), _rank_index(r2)

        # 強い方(小さい index)を hi
        hi_r, lo_r = (r1, r2) if i1 < i2 else (r2, r1)
        hi_i, lo_i = _rank_index(hi_r), _rank_index(lo_r)

        if so == "S":
            # 上三角
            return (hi_i, lo_i)
        else:
            # 下三角（suited 座標の転置）
            return (lo_i, hi_i)

    raise ValueError(f"Unrecognized hand_key: {hand_key!r}")


# =========================
# Anchor match model
# =========================

@dataclass(frozen=True)
class AnchorMatch:
    pos_cell_addr: str
    pos_row: int
    pos_col: int
    aa_row: int
    aa_col: int
    aa_addr: str


# =========================
# Repository
# =========================

class ExcelRangeRepository:
    """
    Excelレンジ表を参照する Repository（posセル起点）。

    仕様（以前の設計を優先）:
    1) AA_SEARCH_RANGES[kind] 内で pos名(EP/MP/CO/BTN...) を検索
    2) posセルから (down=+3, left=-2) のセルが "AA"
    3) AAセルから GRID_TOPLEFT_OFFSET で 13x13 グリッド左上を求める
    4) hand_key -> (r0,c0) に変換して、13x13 内の該当セルを直接参照
       - そのセル色を読み、見本色と照合しタグを返す
       - 無色/不一致は "FOLD"

    見本色:
    - kind ごとに config で固定セル番地を持つ（ref_color_cells[kind][tag] = "H25" など）
    """

    def __init__(
        self,
        wb: Workbook,
        sheet_name: str,
        aa_search_ranges: Dict[str, str],             # kind -> A1 range
        grid_topleft_offset: Tuple[int, int],         # AA -> grid top-left (dr, dc)
        ref_color_cells: Dict[str, Dict[str, str]],   # kind -> tag -> "H25"
        enable_debug: bool = False,
    ) -> None:
        if sheet_name not in wb.sheetnames:
            raise ValueError(f"Sheet not found: {sheet_name}. Available={wb.sheetnames}")

        self.wb: Workbook = wb
        self.ws: Worksheet = wb[sheet_name]

        self.aa_search_ranges = dict(aa_search_ranges)
        self.grid_topleft_offset = tuple(grid_topleft_offset)
        self.ref_color_cells = dict(ref_color_cells)
        self.enable_debug = enable_debug

        # (kind, pos) -> AnchorMatch
        self._anchor_cache: Dict[Tuple[str, str], AnchorMatch] = {}

        # kind -> tag -> rgb
        self._ref_color_cache: Dict[str, Dict[str, str]] = {}

    # =========================
    # Anchor (pos -> AA)
    # =========================

    def find_anchor_by_pos(self, kind: str, pos: str) -> AnchorMatch:
        cache_key = (kind, pos)

        if cache_key in self._anchor_cache:
            m = self._anchor_cache[cache_key]
            if self.enable_debug:
                print(
                    f"[REPO][ANCHOR] cached pos_cell={m.pos_cell_addr} -> AA={m.aa_addr} "
                    f"(kind={kind} pos={pos})",
                    flush=True,
                )
            return m

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
                f"[REPO][ANCHOR] chosen pos_cell={chosen.pos_cell_addr} -> AA={chosen.aa_addr} "
                f"(kind={kind} pos={pos})",
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
        kind ごとに定義された「固定セル番地」から見本色を読む（キャッシュあり）。
        """
        if kind in self._ref_color_cache:
            return self._ref_color_cache[kind]

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
                    f"patternType={getattr(cell.fill, 'patternType', None)} "
                    f"fg.type={getattr(fg, 'type', None)} fg.rgb={getattr(fg, 'rgb', None)} "
                    f"fg.theme={getattr(fg, 'theme', None)} fg.indexed={getattr(fg, 'indexed', None)} "
                    f"read_rgb={rgb}",
                    flush=True,
                )

        self._ref_color_cache[kind] = result
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
    # Main API: tag lookup
    # =========================

    def get_tag_for_hand(self, kind: str, position: str, hand: str) -> Tuple[str, Dict[str, Any]]:
        """
        hand_key -> (r0,c0) -> グリッド直接参照 -> fill色でタグ判定。
        追加仕様：
        - 「セル値（ハンド名）と色」が両方揃ったときだけ有効
        文字列のみ / 色のみ は “色なし” と同じ扱い（= FOLD）
        """
        debug: Dict[str, Any] = {"kind": kind, "position": position, "hand_in": hand}
        hand_key = _normalize_hand_to_key(hand)
        r0, c0 = _hand_key_to_rc(hand_key)
        expected_label = _expected_cell_label_from_hand_key(hand_key)
        debug.update({"hand_key": hand_key, "r0": r0, "c0": c0, "expected_label": expected_label})

    # 1) グリッド左上
        top_r, top_c = self.get_grid_top_left(kind, position)
        debug["grid_topleft"] = (top_r, top_c)

        target_row = top_r + r0
        target_col = top_c + c0
        cell = self.ws.cell(row=target_row, column=target_col)

        debug["target_cell_rc"] = (target_row, target_col)
        debug["target_cell_a1"] = cell.coordinate
        debug["cell_value"] = cell.value

    # ★追加：セル値チェック（色だけの凡例セルなどを除外）
        cell_text = "" if cell.value is None else str(cell.value).strip().upper()
        debug["cell_text_norm"] = cell_text

        if cell_text != expected_label:
            # 文字列のみ・色のみは「色なし」と同じ扱いにする
            debug["cell_rgb"] = ""  # 強制的に無色扱い
            ref = self.get_ref_colors(kind)
            debug["ref_colors"] = ref
            debug["tag"] = "FOLD"
            debug["rejected_reason"] = "cell_label_mismatch_or_blank"
            return "FOLD", debug

    # 2) 対象セルの色（ここまで来たら “文字＋色” の色を見る）
        rgb = self._read_fill_rgb(cell)
        debug["cell_rgb"] = rgb

    # 3) 見本色と照合
        ref = self.get_ref_colors(kind)  # tag -> rgb
        debug["ref_colors"] = ref

        if not rgb:
            debug["tag"] = "FOLD"
            debug["rejected_reason"] = "no_fill_color"
            return "FOLD", debug

        for tag, ref_rgb in ref.items():
            if rgb == ref_rgb and ref_rgb:
                debug["tag"] = tag
                return tag, debug

        debug["tag"] = "FOLD"
        debug["unmatched_rgb"] = rgb
        return "FOLD", debug

