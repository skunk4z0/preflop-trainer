# juego_judge.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass
class JudgeResult:
    action: str                 # "FOLD" or "RAISE"
    correct: bool
    reason: str
    debug: Dict[str, Any]
    show_image: bool = False
    image_info: Optional[Dict[str, Any]] = None


class JUEGOJudge:
    # 13x13表の並び（強い→弱い）
    RANKS = "AKQJT98765432"

    def __init__(self, repo) -> None:
        self.repo = repo

    # =========================
    # OR（EP/MP/CO/BTN）
    # =========================
    def judge_or(self, position: str, hand: str, user_action: str, loose: bool) -> JudgeResult:
    
    # OR（EP/MP/CO/BTN）: タグ方式（TIGHT/LOOSE/FOLD）で判定
    
        kind = "OR"

    # repo が hand を検索してタグを返す（新仕様）
        tag, repo_dbg = self.repo.get_tag_for_hand(kind, position, hand)

    # 正解アクション決定
        if tag == "TIGHT":
            correct_action = "RAISE"
        elif tag == "LOOSE":
            correct_action = "RAISE" if loose else "FOLD"
        else:
            correct_action = "FOLD"

        is_correct = (user_action == correct_action)
        reason = self._make_reason(position, hand, tag, loose)

        debug = {
            "kind": kind,
            "position": position,
            "hand": hand,
            "tag": tag,
            "loose": loose,
            "user_action": user_action,
            "correct_action": correct_action,
            "repo": repo_dbg,   # ★根拠はすべてここ
        }

        return JudgeResult(
            action=correct_action,
            correct=is_correct,
            reason=reason,
            debug=debug,
        )


    def _rank_index(self, r: str) -> int:
        r = r.upper()
        idx = self.RANKS.find(r)
        if idx == -1:
            raise ValueError(f"Invalid rank: {r} (rank must be in {self.RANKS})")
        return idx

    # =========================
    # 理由文
    # =========================
    def _make_reason(self, position: str, hand: str, tag: str, loose: bool) -> str:
        if tag == "FOLD":
            return f"{position} のORレンジでは {hand} はFOLD"

        if tag == "TIGHT":
            return f"{position} のTIGHTレンジに {hand} は含まれる → RAISE"

        if tag == "LOOSE":
            if loose:
                return f"{position} のLOOSEレンジに {hand} は含まれる（ルースあり）→ RAISE"
            return f"{position} のLOOSEレンジだが（ルースなし）→ FOLD"

        return f"判定不能（tag={tag}）"
