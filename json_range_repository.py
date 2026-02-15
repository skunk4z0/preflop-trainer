from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from core.handgrid import hand_key_to_rc, rc_to_hand_key


def _normalize_hand_to_key(hand: str) -> str:
    return (hand or "").strip().upper().replace(" ", "")


# 位置キーの揺れ吸収（"BBvsSB" / "BB_VS_SB" / "BB vs SB" など）
_POS_SAN_RE = re.compile(r"[^A-Z0-9]+")


def _pos_sanitize(pos: str) -> str:
    return _POS_SAN_RE.sub("", (pos or "").strip().upper())


@dataclass(frozen=True)
class RangeCellView:
    label: str      # 表示（例: "AK" / "AA"）
    bg_rgb: str     # "RRGGBB"（"#"なし）


@dataclass(frozen=True)
class RangeGridView:
    kind: str
    pos: str
    sheet_name: str
    cells: List[List[RangeCellView]]  # 13x13


class JsonRangeRepository:
    """
    実行時Repo（Excel非依存）

    入力:
      - final_tags.json: ranges[kind][position][hand_key] -> tag
      - ranges_pack.json: legend_by_kind[tag]->rgb を含む（RangePopup描画用）

    提供:
      - get_tag_for_hand(kind, pos, hand_key) -> (tag, debug)
      - list_positions(kind) -> [pos...]
      - get_range_grid_view(kind, pos) -> RangeGridView  (popup用)
      - hand_to_grid_rc(card1, card2) -> (r,c)           (popupハイライト用)
    """

    def __init__(
        self,
        final_tags_json_path: str | Path,
        ranges_pack_json_path: str | Path | None = None,
    ) -> None:
        self.final_tags_path = Path(final_tags_json_path)

        if not self.final_tags_path.exists():
            raise SystemExit(
                "[FATAL] final_tags.json not found.\n"
                f"Expected: {self.final_tags_path}\n"
                "Run build first:\n"
                "  .\\.venv-build\\Scripts\\python -m tools.build_final_tags_json\n"
            )

        root = json.loads(self.final_tags_path.read_text(encoding="utf-8"))
        if not isinstance(root, dict):
            raise ValueError("final_tags.json must be an object with keys: meta, ranges")

        ranges = root.get("ranges")
        if not isinstance(ranges, dict):
            raise ValueError("final_tags.json: 'ranges' must be a dict")

        # 正規化格納：kind/pos/hand_key は UPPER 統一
        self._ranges: Dict[str, Dict[str, Dict[str, str]]] = {}
        # kindごとの position エイリアス（入力揺れ吸収）
        self._pos_alias: Dict[str, Dict[str, str]] = {}

        for kind, pos_map in ranges.items():
            k = str(kind).strip().upper()
            if not isinstance(pos_map, dict):
                continue

            self._ranges[k] = {}
            self._pos_alias[k] = {}

            for position, hand_map in pos_map.items():
                p = str(position).strip().upper()
                if not isinstance(hand_map, dict):
                    continue

                norm_hand_map: Dict[str, str] = {}
                for hk, tag in hand_map.items():
                    hh = _normalize_hand_to_key(str(hk))
                    norm_hand_map[hh] = str(tag).strip()

                self._ranges[k][p] = norm_hand_map

                # alias: "BB_OOP" / "BBOOP" の両方を同じposへ
                self._pos_alias[k][p] = p
                self._pos_alias[k][_pos_sanitize(p)] = p

        # ---- RangePopup用 pack（任意） ----
        if ranges_pack_json_path is None:
            # 同じフォルダに ranges_pack.json がある想定（build_final_tags_json.py がそう出す）
            ranges_pack_json_path = self.final_tags_path.with_name("ranges_pack.json")

        self.pack_path = Path(ranges_pack_json_path)
        self._pack_sheet: str = ""
        self._legend_by_kind: Dict[str, Dict[str, str | None]] = {}
        self._tags_by_kind: Dict[str, Dict[str, Dict[str, str]]] = {}
        self._default_tag: str = "FOLD"

        if self.pack_path.exists():
            pack = json.loads(self.pack_path.read_text(encoding="utf-8"))
            if isinstance(pack, dict):
                self._pack_sheet = str(pack.get("sheet") or "")
                self._default_tag = str(pack.get("default_tag") or "FOLD").strip() or "FOLD"

                legend = pack.get("legend_by_kind")
                tags = pack.get("tags")

                if isinstance(legend, dict):
                    # kind/pos/tag は JSON 側で大体正規化済みだが、念のため kind を UPPER
                    for k_raw, v in legend.items():
                        k = str(k_raw).strip().upper()
                        if isinstance(v, dict):
                            # tag -> rgb or None
                            self._legend_by_kind[k] = {str(t).strip(): (None if rgb is None else str(rgb).strip().upper()) for t, rgb in v.items()}

                if isinstance(tags, dict):
                    for k_raw, pos_map in tags.items():
                        k = str(k_raw).strip().upper()
                        if isinstance(pos_map, dict):
                            self._tags_by_kind[k] = {}
                            for p_raw, hand_map in pos_map.items():
                                p = str(p_raw).strip().upper()
                                if isinstance(hand_map, dict):
                                    self._tags_by_kind[k][p] = {str(hk).strip().upper(): str(t).strip() for hk, t in hand_map.items()}

        # pack は無くても tag 判定はできる（popupだけ死ぬ）
        # ここで落とさず、get_range_grid_view で必要時に明示的に例外を出す

    # -------------------------
    # Public
    # -------------------------
    def list_positions(self, kind: str) -> List[str]:
        k = (kind or "").strip().upper()
        return sorted(self._ranges.get(k, {}).keys())

    def get_tag_for_hand(self, kind: str, position: str, hand: str) -> Tuple[str, Dict[str, Any]]:
        k_in = (kind or "").strip().upper()
        p_in = (position or "").strip().upper()
        hand_key = _normalize_hand_to_key(hand)

        debug: Dict[str, Any] = {
            "kind": k_in,
            "position": p_in,
            "hand_in": hand,
            "hand_key": hand_key,
            "found_kind": False,
            "found_position": False,
            "position_resolved": "",
        }

        pos_map = self._ranges.get(k_in)
        if not pos_map:
            return "", debug

        debug["found_kind"] = True

        # position alias 解決（"BB_VS_SB" なども通す）
        p_resolved = self._resolve_position(kind=k_in, position=p_in)
        debug["position_resolved"] = p_resolved

        hand_map = pos_map.get(p_resolved)
        debug["found_position"] = hand_map is not None
        if not hand_map:
            return "", debug

        tag = hand_map.get(hand_key, "")
        return str(tag).strip(), debug

    def get_range_grid_view(self, kind: str, pos: str, size: int = 13) -> RangeGridView:
        """
        popup表示用：13x13 の (label, bg_rgb) を返す。
        ranges_pack.json が無いと色が作れないので例外。
        """
        k = (kind or "").strip().upper()
        p_in = (pos or "").strip().upper()
        p = self._resolve_position(kind=k, position=p_in)

        if not self._legend_by_kind or not self._tags_by_kind:
            raise RuntimeError(
                "[RANGE_POPUP] ranges_pack.json is missing or invalid.\n"
                f"Expected: {self.pack_path}\n"
                "Run build:\n"
                "  .\\.venv-build\\Scripts\\python -m tools.build_final_tags_json\n"
            )

        tag_map = (self._tags_by_kind.get(k) or {}).get(p)
        if tag_map is None:
            raise KeyError(f"[RANGE_POPUP] kind/pos not found in pack: kind={k} pos={p}")

        legend = self._legend_by_kind.get(k, {})
        sheet = self._pack_sheet or "Datasheet"

        cells: List[List[RangeCellView]] = []
        for r in range(size):
            row: List[RangeCellView] = []
            for c in range(size):
                hk = rc_to_hand_key(r, c)  # "AKS"/"AKO"/"AA"
                tag = (tag_map.get(hk) or self._default_tag).strip() or self._default_tag

                rgb = legend.get(tag)
                bg = (rgb or "FFFFFF").upper()  # None -> white

                # 表示ラベルはExcelと同じく末尾の s/o を出さない
                label = hk if len(hk) == 2 else hk[:2]

                row.append(RangeCellView(label=label, bg_rgb=bg))
            cells.append(row)

        return RangeGridView(kind=k, pos=p, sheet_name=sheet, cells=cells)

    def hand_to_grid_rc(self, card1: str, card2: str) -> tuple[int, int]:
        """
        hole cards（例: "Ks","Jc"）から 13x13 の (row,col) を返す（0-based）
        """
        hk = self._cards_to_hand_key(card1, card2)
        return hand_key_to_rc(hk)

    # -------------------------
    # Internal helpers
    # -------------------------
    def _resolve_position(self, kind: str, position: str) -> str:
        k = (kind or "").strip().upper()
        p = (position or "").strip().upper()
        alias = self._pos_alias.get(k) or {}

        # 1) そのまま
        if p in alias:
            return alias[p]

        # 2) sanitize（記号/空白/_ を除去）
        ps = _pos_sanitize(p)
        if ps in alias:
            return alias[ps]

        # 3) 最後は入力を返す（後段で not found 扱い）
        return p

    def _cards_to_hand_key(self, c1: str, c2: str) -> str:
        """
        "Ks","Jc" -> "KJO" / "AKS" / "AA"
        """
        a = (c1 or "").strip()
        b = (c2 or "").strip()

        if len(a) == 4 and len(b) == 0:
            # "KsJc" 形式が来た場合
            a, b = a[:2], a[2:]

        if len(a) != 2 or len(b) != 2:
            raise ValueError(f"bad cards: {c1!r}, {c2!r}")

        r1, s1 = a[0].upper(), a[1].lower()
        r2, s2 = b[0].upper(), b[1].lower()

        # pair
        if r1 == r2:
            return r1 + r2

        suited = (s1 == s2)

        # 強いランクが先（AK...）
        order = "AKQJT98765432"
        i1 = order.index(r1)
        i2 = order.index(r2)
        hi, lo = (r1, r2) if i1 < i2 else (r2, r1)

        return f"{hi}{lo}{'S' if suited else 'O'}"
