from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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

# --- pack metadata（描画/移植を見据えた固定値） ---
RANKS = "AKQJT98765432"
GRID_RULE = "pair_diag_suited_upper_offsuit_lower"
DEFAULT_TAG = "FOLD"


def all_hand_keys_169() -> list[str]:
    """
    13x13=169 の hand_key を生成する（Excel/JSON共通）。
    - pair: AA, KK...
    - suited: AKS...
    - offsuit: AKO...
    """
    ranks = list(RANKS)
    out: list[str] = []
    for i, r1 in enumerate(ranks):
        for j, r2 in enumerate(ranks):
            if i == j:
                out.append(f"{r1}{r2}")
            elif i < j:
                out.append(f"{r1}{r2}S")
            else:
                out.append(f"{r2}{r1}O")
    return out


def _norm_rgb(rgb: str | None) -> str | None:
    """
    RGBを 6桁HEX(大文字) に正規化する。
    - None/"" -> None
    - "#AABBCC" -> "AABBCC"
    - "FFAABBCC"(ARGB) -> "AABBCC"
    """
    if rgb is None:
        return None
    s = str(rgb).strip()
    if s == "":
        return None
    s = s.lstrip("#").upper()
    if len(s) == 8:  # ARGB
        s = s[-6:]
    if len(s) != 6:
        raise ValueError(f"Bad RGB: {rgb!r}")
    return s


def _build_legend_by_kind(repo: ExcelRangeRepository, kinds_raw: list[str]) -> dict[str, dict[str, str | None]]:
    """
    kind別の legend(tag->rgb) を作る。
    - repo.get_ref_colors(kind) は「RGB直書き or セル番地」どちらでも解決済みの想定
    - DEFAULT_TAG(FOLD) は None で必ず入れる（“無色”の表現として使う）
    """
    legend_by_kind: dict[str, dict[str, str | None]] = {}

    for kind_raw in kinds_raw:
        kind_u = str(kind_raw).strip().upper()
        if not kind_u:
            continue

        ref = repo.get_ref_colors(kind_raw)  # tag -> "RRGGBB"
        legend: dict[str, str | None] = {}
        for tag, rgb in ref.items():
            legend[str(tag).strip()] = _norm_rgb(rgb)

        legend.setdefault(DEFAULT_TAG, None)
        legend_by_kind[kind_u] = legend

    return legend_by_kind


def _collect_positions_by_kind(repo: ExcelRangeRepository, kinds_raw: list[str]) -> dict[str, list[str]]:
    positions_by_kind: dict[str, list[str]] = {}
    for kind_raw in kinds_raw:
        kind_u = str(kind_raw).strip().upper()
        if not kind_u:
            continue
        positions = repo.list_positions(kind_raw) or []
        positions_by_kind[kind_u] = [str(p).strip().upper() for p in positions if str(p).strip()]
    return positions_by_kind


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    excel_path = Path(EXCEL_PATH)
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel not found: {excel_path}")

    # Excelを読む（ビルド時のみ）
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    repo = ExcelRangeRepository(
        wb=wb,
        sheet_name=SHEET_NAME,
        aa_search_ranges=AA_SEARCH_RANGES,
        grid_topleft_offset=GRID_TOPLEFT_OFFSET,
        ref_color_cells=REF_COLOR_CELLS,
    )

    # build対象 kind（configのキーを正とする）
    kinds_raw = [str(k).strip() for k in AA_SEARCH_RANGES.keys() if str(k).strip()]

    # ---- final_tags.json（実行時Repoが読む本体） ----
    now = datetime.now(timezone.utc).astimezone()
    final: dict[str, Any] = {
        "meta": {
            "generated_at": now.isoformat(timespec="seconds"),
            "source": str(excel_path),
            "sheet": SHEET_NAME,
        },
        "ranges": {},  # kind_u -> pos_u -> hand_key -> tag
    }

    hand_keys = all_hand_keys_169()

    for kind_raw in kinds_raw:
        kind_u = kind_raw.upper()

        positions = repo.list_positions(kind_raw) or []
        if not positions:
            continue

        final["ranges"][kind_u] = {}

        for pos in positions:
            pos_raw = str(pos).strip()
            if not pos_raw:
                continue
            pos_u = pos_raw.upper()

            hand_map: dict[str, str] = {}
            for hk in hand_keys:
                tag, _dbg = repo.get_tag_for_hand(kind_raw, pos_raw, hk)
                hand_map[hk] = str(tag or "").strip()

            final["ranges"][kind_u][pos_u] = hand_map

    out_path = Path(FINAL_TAGS_JSON_PATH)
    _write_json(out_path, final)
    print(f"OK: wrote {out_path}")

    # ---- ranges_pack.json（描画/移植用：legend + tags を同梱） ----
    legend_by_kind = _build_legend_by_kind(repo, kinds_raw)
    positions_by_kind = _collect_positions_by_kind(repo, kinds_raw)

    pack: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": now.isoformat(timespec="seconds"),
        "source": str(excel_path),
        "sheet": SHEET_NAME,
        "ranks": RANKS,
        "grid_rule": GRID_RULE,
        "default_tag": DEFAULT_TAG,
        "kinds": sorted(final["ranges"].keys()),
        "positions_by_kind": positions_by_kind,
        "legend_by_kind": legend_by_kind,
        "tags": final["ranges"],
    }

    pack_path = out_path.with_name("ranges_pack.json")
    _write_json(pack_path, pack)
    print(f"OK: wrote {pack_path}")

    # ---- 任意：タグ未定義を警告（止めない） ----
    try:
        known_tags = set()
        for _kind_u, legend in legend_by_kind.items():
            known_tags.update(legend.keys())

        used_tags = set()
        for _kind_u, pos_map in final["ranges"].items():
            for _pos_u, hand_map in pos_map.items():
                for _hk, t in hand_map.items():
                    used_tags.add(str(t).strip())

        unknown = sorted([t for t in used_tags if t and t not in known_tags and t != DEFAULT_TAG])
        if unknown:
            head = unknown[:50]
            tail = " ..." if len(unknown) > 50 else ""
            print(f"[WARN] tags used but not in legend: {head}{tail}")
    except Exception as e:
        print(f"[WARN] legend validation skipped due to error: {e}")


if __name__ == "__main__":
    main()
