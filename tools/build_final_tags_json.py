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

# --- pack metadata (スマホ描画/移植用に固定) ---
RANKS = "AKQJT98765432"
GRID_RULE = "pair_diag_suited_upper_offsuit_lower"
DEFAULT_TAG = "FOLD"


def all_hand_keys_169() -> list[str]:
    ranks = list(RANKS)
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


def _norm_rgb(rgb: str | None) -> str | None:
    """
    RGBを 6桁HEX(大文字) に正規化する。
    - None/"" -> None
    - "#AABBCC" -> "AABBCC"
    - "FFAABBCC"(ARGB) -> "AABBCC"
    - "000000" は有効（None扱いしない）
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
        raise ValueError(f"Bad RGB: {rgb}")
    return s


def _build_legend_by_kind(repo: ExcelRangeRepository, kinds_raw: list[str]) -> dict[str, dict[str, str | None]]:
    """
    kind別の legend(tag->rgb) を作る。
    repo.get_ref_colors(kind) が返す値を正規化し、FOLD を None で明示する（未定義なら追加）。
    """
    legend_by_kind: dict[str, dict[str, str | None]] = {}
    for kind_raw in kinds_raw:
        kind_u = kind_raw.upper()

        ref = repo.get_ref_colors(kind_raw)  # tag -> rgb/セル指定を内部で解決済み想定
        legend: dict[str, str | None] = {}
        for tag, rgb in ref.items():
            legend[str(tag).strip()] = _norm_rgb(rgb)

        # 「色なし=FOLD」をUI側で扱いやすくする（黒 000000 と衝突しない）
        legend.setdefault(DEFAULT_TAG, None)

        legend_by_kind[kind_u] = legend

    return legend_by_kind


def _collect_positions_by_kind(repo: ExcelRangeRepository, kinds_raw: list[str]) -> dict[str, list[str]]:
    positions_by_kind: dict[str, list[str]] = {}
    for kind_raw in kinds_raw:
        kind_u = kind_raw.upper()
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

    # Excelを読む（移行のための一回だけ）
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

    # 最終タグJSON（A案）を作る
    # JsonRangeRepositoryが読むのは root["ranges"]
    final: dict[str, Any] = {
        "meta": {
            "source": str(excel_path),
            "sheet": SHEET_NAME,
        },
        "ranges": {},  # kind_u -> pos_u -> hand_key -> tag
    }

    # kindごとにposition一覧を取り、169ハンド分のtagを作る
    for kind_raw in kinds_raw:
        kind_u = kind_raw.upper()

        positions = repo.list_positions(kind_raw)
        if not positions:
            continue

        final["ranges"][kind_u] = {}

        for pos in positions:
            pos_raw = str(pos).strip()
            if not pos_raw:
                continue
            pos_u = pos_raw.upper()

            final["ranges"][kind_u][pos_u] = {}

            for hk in all_hand_keys_169():
                tag, _dbg = repo.get_tag_for_hand(kind_raw, pos_raw, hk)
                final["ranges"][kind_u][pos_u][hk] = tag

    # --- 出力1: final_tags.json（既存仕様のまま） ---
    out_path = Path(FINAL_TAGS_JSON_PATH)
    _write_json(out_path, final)
    print(f"OK: wrote {out_path}")

    # --- 出力2: ranges_pack.json（スマホ描画/移植用パック） ---
    legend_by_kind = _build_legend_by_kind(repo, kinds_raw)
    positions_by_kind = _collect_positions_by_kind(repo, kinds_raw)

    now = datetime.now(timezone.utc).astimezone()
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

    # 任意：タグ未定義を警告（落とさない）
    try:
        known_tags = set()
        for kind_u, legend in legend_by_kind.items():
            for t in legend.keys():
                known_tags.add(t)

        used_tags = set()
        for kind_u, pos_map in final["ranges"].items():
            for _pos_u, hand_map in pos_map.items():
                for _hk, t in hand_map.items():
                    used_tags.add(str(t).strip())

        unknown = sorted([t for t in used_tags if t and t not in known_tags and t != DEFAULT_TAG])
        if unknown:
            print(f"[WARN] tags used but not in legend: {unknown[:50]}{' ...' if len(unknown) > 50 else ''}")
    except Exception as e:
        print(f"[WARN] legend validation skipped due to error: {e}")


if __name__ == "__main__":
    main()
