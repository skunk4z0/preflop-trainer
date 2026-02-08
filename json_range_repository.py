from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _normalize_hand_to_key(hand: str) -> str:
    return (hand or "").strip().upper().replace(" ", "")

@dataclass(frozen=True)
    note: str = ""

class JsonRangeRepository:
    """
    final_tags.json を読み込み、
      ranges[kind][position][hand_key] -> tag
    を返す。
    欠損は ""（=FOLD扱い）を返す。
    """
    def __init__(self, json_path: str | Path) -> None:
        self.json_path = Path(json_path)
        if not self.json_path.exists():
            raise SystemExit(
                "[FATAL] final_tags.json not found.\n"
                f"Expected: {self.json_path}\n"
                "Run build first:\n"
                "  python -m tools.build_final_tags_json\n"
            )

        root = json.loads(self.json_path.read_text(encoding="utf-8"))

        if not isinstance(root, dict):
            raise ValueError("final_tags.json must be an object with keys: meta, ranges")

        ranges = root.get("ranges")
        if not isinstance(ranges, dict):
            raise ValueError("final_tags.json: 'ranges' must be a dict")

        # 正規化格納：UPPERで統一
        self._ranges: Dict[str, Dict[str, Dict[str, str]]] = {}
        for kind, pos_map in ranges.items():
            k = str(kind).strip().upper()
            if not isinstance(pos_map, dict):
                continue
            self._ranges[k] = {}
            for position, hand_map in pos_map.items():
                p = str(position).strip().upper()
                if not isinstance(hand_map, dict):
                    continue
                # hand_keyは既に "AKS" 等になってる前提だが、念のため正規化
                norm_hand_map: Dict[str, str] = {}
                for hk, tag in hand_map.items():
                    hh = _normalize_hand_to_key(str(hk))
                    norm_hand_map[hh] = str(tag).strip()
                self._ranges[k][p] = norm_hand_map
    

    def list_positions(self, kind: str) -> List[str]:
        k = (kind or "").strip().upper()
        return sorted(self._ranges.get(k, {}).keys())

    def get_tag_for_hand(self, kind: str, position: str, hand: str) -> Tuple[str, Dict[str, Any]]:
        k = (kind or "").strip().upper()
        p = (position or "").strip().upper()
        hand_key = _normalize_hand_to_key(hand)

        debug: Dict[str, Any] = {
            "kind": k,
            "position": p,
            "hand_in": hand,
            "hand_key": hand_key,
            "found_kind": k in self._ranges,
            "found_position": False,
        }

        pos_map = self._ranges.get(k)
        if not pos_map:
            return "", debug

        hand_map = pos_map.get(p)
        debug["found_position"] = hand_map is not None
        if not hand_map:
            return "", debug

        tag = hand_map.get(hand_key, "")
        return str(tag).strip(), debug
