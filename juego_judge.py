# juego_judge.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class JudgeResult:
    action: str                 # "FOLD" or "RAISE" or "LIMP_CALL"(必要なら)
    correct: bool
    reason: str
    debug: Dict[str, Any]
    show_image: bool = False
    image_info: Optional[Dict[str, Any]] = None


class JUEGOJudge:
    def __init__(self, repo) -> None:
        self.repo = repo

    # =========================
    # OR（EP/MP/CO/BTN）
    # =========================
    def judge_or(self, position: str, hand: str, user_action: str, loose: bool) -> JudgeResult:
        """
        OR（EP/MP/CO/BTN）:
        - repo が返す tag は config の REF_COLOR_CELLS["OR"] に合わせる想定
          例: "TIGHT" / "LOOSE" / (不一致は repo 側で "FOLD")
        """
        kind = "OR"

        tag, repo_dbg = self.repo.get_tag_for_hand(kind, position, hand)

        # 正解アクション決定
        if tag == "TIGHT":
            correct_action = "RAISE"
        elif tag == "LOOSE":
            correct_action = "RAISE" if loose else "FOLD"
        else:
            correct_action = "FOLD"

        ua = (user_action or "").strip().upper()
        is_correct = (ua == correct_action)
        reason = self._make_reason_or(position, hand, tag, loose)

        debug = {
            "kind": kind,
            "position": position,
            "hand": hand,
            "tag": tag,
            "loose": loose,
            "user_action": ua,
            "correct_action": correct_action,
            "repo": repo_dbg,   # 根拠はすべてここ（grid座標/色/参照色）
        }

        return JudgeResult(
            action=correct_action,
            correct=is_correct,
            reason=reason,
            debug=debug,
        )

    # =========================
    # OR_SB（SB）
    # =========================
    def judge_or_sb(self, position: str, hand: str, user_action: str, loose: bool) -> JudgeResult:
        """
        OR_SB（SB）:
        - repo が返す tag は config の REF_COLOR_CELLS["OR_SB"] に合わせる想定
          例: "RAISE_3BB", "LimpCx3o", ... / (不一致は "FOLD")
        - 以前仕様優先＝色タグをそのまま「正解アクション」に写像する
        """
        kind = "OR_SB"

        tag, repo_dbg = self.repo.get_tag_for_hand(kind, position, hand)

        # 正解アクション決定（最小：タグ→アクション）
        # ここは UI のボタン仕様に合わせて返す文字列を合わせる必要あり
        # ひとまず:
        # - "RAISE_3BB" は RAISE
        # - "LimpC..." は LIMP_CALL（= limpcall）
        # - それ以外/不一致は FOLD
        if tag == "RAISE_3BB":
            correct_action = "RAISE"
        elif tag.startswith("LIMPC"):
            correct_action = "LIMP_CALL"
        else:
            correct_action = "FOLD"

        ua = (user_action or "").strip().upper()
        is_correct = (ua == correct_action)
        reason = self._make_reason_or_sb(position, hand, tag)

        debug = {
            "kind": kind,
            "position": position,
            "hand": hand,
            "tag": tag,
            "loose": loose,  # 現時点では SB 判定に未使用（将来拡張用に保持）
            "user_action": ua,
            "correct_action": correct_action,
            "repo": repo_dbg,
        }

        return JudgeResult(
            action=correct_action,
            correct=is_correct,
            reason=reason,
            debug=debug,
        )

    # =========================
    # 理由文
    # =========================
    def _make_reason_or(self, position: str, hand: str, tag: str, loose: bool) -> str:
        if tag == "FOLD":
            return f"{position} のORレンジでは {hand} はFOLD"

        if tag == "TIGHT":
            return f"{position} のTIGHTレンジに {hand} は含まれる → RAISE"

        if tag == "LOOSE":
            if loose:
                return f"{position} のLOOSEレンジに {hand} は含まれる（ルースあり）→ RAISE"
            return f"{position} のLOOSEレンジだが（ルースなし）→ FOLD"

        return f"判定不能（tag={tag}）"

    def _make_reason_or_sb(self, position: str, hand: str, tag: str) -> str:
        if tag == "FOLD":
            return f"{position}（SB）のORレンジでは {hand} はFOLD"

        if tag == "RAISE_3BB":
            return f"{position}（SB）のレンジでは {hand} はRAISE（3BB）"

        if tag.upper().startswith("LIMPC"):
            return f"{position}（SB）のレンジでは {hand} はLimp/Call（tag={tag}）"

        return f"判定不能（tag={tag}）"
