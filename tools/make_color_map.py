from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional

from config import FINAL_TAGS_JSON_PATH


def _default_pack_path() -> Path:
    # final_tags.json と同じ場所に ranges_pack.json がある前提
    return Path(FINAL_TAGS_JSON_PATH).with_name("ranges_pack.json")


def _load_pack(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"ranges_pack.json not found: {path}\n"
            "Build it first:\n"
            "  .\\.venv-build\\Scripts\\python -m tools.build_final_tags_json"
        )
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("ranges_pack.json must be a JSON object")
    return obj


def _get_legend(pack: Dict[str, Any], kind: str) -> Dict[str, Optional[str]]:
    legend_by_kind = pack.get("legend_by_kind")
    if not isinstance(legend_by_kind, dict):
        raise ValueError("ranges_pack.json missing 'legend_by_kind'")

    k = (kind or "").strip().upper()
    if not k:
        raise ValueError("kind is required")

    legend = legend_by_kind.get(k)
    if not isinstance(legend, dict):
        # kind一覧を出してわかりやすく落とす
        kinds = sorted([str(x) for x in legend_by_kind.keys()])
        raise KeyError(f"kind not found: {k}. Available: {kinds}")

    out: Dict[str, Optional[str]] = {}
    for tag, rgb in legend.items():
        t = str(tag).strip()
        if rgb is None:
            out[t] = None
        else:
            s = str(rgb).strip().lstrip("#").upper()
            # 念のため ARGB も吸収
            if len(s) == 8:
                s = s[-6:]
            out[t] = s
    return out


def _format_json(legend: Dict[str, Optional[str]]) -> str:
    # tag名ソートで安定出力
    ordered = {k: legend[k] for k in sorted(legend.keys())}
    return json.dumps(ordered, ensure_ascii=False, indent=2)


def _format_csv(legend: Dict[str, Optional[str]]) -> str:
    lines = ["tag,rgb"]
    for tag in sorted(legend.keys()):
        rgb = legend[tag] or ""
        lines.append(f"{tag},{rgb}")
    return "\n".join(lines) + "\n"


def _format_md(legend: Dict[str, Optional[str]]) -> str:
    lines = ["| tag | rgb |", "|---|---|"]
    for tag in sorted(legend.keys()):
        rgb = legend[tag]
        lines.append(f"| {tag} | {rgb or ''} |")
    return "\n".join(lines) + "\n"


def _write_or_print(text: str, out_path: Optional[Path]) -> None:
    if out_path is None:
        print(text)
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    print(f"OK: wrote {out_path}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Dump legend(tag->rgb) from data/ranges_pack.json (no Excel)."
    )
    ap.add_argument("--kind", help="Kind name (e.g., OR, OR_SB, ROL, CC_3BET).")
    ap.add_argument(
        "--pack",
        help="Path to ranges_pack.json (default: sibling of FINAL_TAGS_JSON_PATH).",
        default=None,
    )
    ap.add_argument(
        "--format",
        choices=["json", "csv", "md"],
        default="json",
        help="Output format.",
    )
    ap.add_argument(
        "--out",
        help="Output file path (omit to print to stdout).",
        default=None,
    )
    ap.add_argument(
        "--list-kinds",
        action="store_true",
        help="List available kinds and exit.",
    )
    args = ap.parse_args()

    pack_path = Path(args.pack) if args.pack else _default_pack_path()
    pack = _load_pack(pack_path)

    legend_by_kind = pack.get("legend_by_kind")
    if not isinstance(legend_by_kind, dict):
        raise ValueError("ranges_pack.json missing 'legend_by_kind'")

    if args.list_kinds:
        kinds = sorted([str(k) for k in legend_by_kind.keys()])
        print("\n".join(kinds))
        return

    if not args.kind:
        kinds = sorted([str(k) for k in legend_by_kind.keys()])
        raise SystemExit(
            "ERROR: --kind is required.\n"
            f"Available kinds: {kinds}\n"
            "Example:\n"
            "  python -m tools.make_color_map --kind OR --format md"
        )

    legend = _get_legend(pack, args.kind)

    if args.format == "json":
        text = _format_json(legend)
    elif args.format == "csv":
        text = _format_csv(legend)
    else:
        text = _format_md(legend)

    out_path = Path(args.out) if args.out else None
    _write_or_print(text, out_path)


if __name__ == "__main__":
    main()
