# juego_judge.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass
class JudgeResult:
    action: str
    correct: bool
    reason: str
    debug: Dict[str, Any]
    show_image: bool = False
    image_info: Optional[Dict[str, Any]] = None


class JUEGOJudge:
    def __init__(self, repo) -> None:
        self.repo = repo

    def judge_or(self, position: str, hand: str, user_action: str, loose: bool) -> JudgeResult:
        """
        OR（EP/MP/CO/BTN）: タグ方式（TIGHT/LOOSE/FOLD）で判定

        ルール（確定）:
        - TIGHT: RAISE 正解 / FOLD 不正解
        - LOOSE: loose=Falseなら FOLD 正解、loose=Trueなら RAISE 正解
        - FOLD : FOLD 正解 / RAISE 不正解
        """
        kind = "OR"

        # デフォルト（未定義事故防止）
        correct_action = "FOLD"
        tag = "FOLD"

        # hand -> grid
        r0, c0 = self._hand_to_grid_rc(hand)

        # 色→タグ
        tag = self.repo.get_tag_at_grid(kind, position, r0, c0)

        # 正解アクション
        if tag == "TIGHT":
            correct_action = "RAISE"
        elif tag == "LOOSE":
            correct_action = "RAISE" if loose else "FOLD"
        else:
            correct_action = "FOLD"

        is_correct = (user_action == correct_action)

        # reason（学習向けに最低限の説明）
        reason = f"tag={tag} / loose={'Y' if loose else 'N'} → 正解={correct_action}"

        debug = {
            "kind": kind,
            "position": position,
            "hand": hand,
            "grid_rc": (r0, c0),
            "tag": tag,
            "loose": loose,
            "user_action": user_action,
            "correct_action": correct_action,
        }

        return JudgeResult(
            action=correct_action,
            correct=is_correct,
            reason=reason,
            debug=debug,
        )


    # =========================
    # hand -> grid 座標
    # =========================
    def _hand_to_grid_rc(self, hand: str) -> Tuple[int, int]:
        """
        13x13表の (row, col) を返す（0-based）。
        前提:
        - RANKS は A..2
        - ペア: 対角
        - suited: 対角より上（row < col）
        - offsuit: 対角より下（row > col）
        """
        h = hand.strip()

        if len(h) == 2:
            # ペア想定 "77"
            r1, r2 = h[0], h[1]
            if r1 != r2:
                raise ValueError(f"Invalid pair hand format: {hand}")

            idx = self._rank_index(r1)
            return idx, idx
        raise NotImplementedError("Implement _hand_to_grid_rc()")

    def _rank_index(self, r: str) -> int:
        r = r.upper()
        idx = self.RANKS.find(r)
        if idx == -1:
            raise ValueError(f"Invalid rank: {r} (hand rank must be in {self.RANKS})")
        return idx

        # =========================
        # 色 → タグ
        # =========================
    def _decide_tag_from_colors(self, cell_rgb: Optional[str], ref: Dict[str, Optional[str]]) -> str:
        """
        取得したセル色を、見本色と照合してタグ化する。
        - 一致: TIGHT / LOOSE
        - 不一致/取得不可: FOLD（安全側）
        """
        tight_rgb = ref.get("TIGHT")
        loose_rgb = ref.get("LOOSE")

        # 色が取得できないケース（条件付き書式など）は安全側でFOLDに倒す
        if not cell_rgb:
            return "FOLD"

        if tight_rgb and cell_rgb == tight_rgb:
            return "TIGHT"
        if loose_rgb and cell_rgb == loose_rgb:
            return "LOOSE"

        return "FOLD"

    # =========================
    # 理由文
    # =========================
    def _make_reason(self, position: str, hand: str, tag: str, loose: bool) -> str:
        if tag == "FOLD":
            return f"{position} の OR レンジでは {hand} はフォールドです"

        if tag == "TIGHT":
            return f"{position} のタイト OR レンジに {hand} は含まれています"

        if tag == "LOOSE":
            if loose:
                return f"{position} のルース OR レンジに {hand} は含まれています"
            else:
                return f"{position} のタイト OR レンジ外のためフォールドが正解です"

        return "判定不能"
