from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from core.expected_action import resolve_expected_action
from core.models import Action, ProblemContext


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

    def _repo_get_tag(self, kind: str, position: str, hand: str):
        res = self.repo.get_tag_for_hand(kind, position, hand)
        if isinstance(res, tuple) and len(res) == 2:
            tag, repo_dbg = res
        else:
            tag, repo_dbg = res, {}
        return tag, repo_dbg

    @staticmethod
    def _norm_user_action(user_action: str) -> str:
        ua = (user_action or "").replace("\u00A0", " ").strip().upper()
        if ua.startswith("OPEN") or ua.startswith("RAISE") or ua.startswith("3BET"):
            return "RAISE"
        if ua in ("LIMP_CALL", "LIMP"):
            return "LIMP"
        if ua in ("CALL", "CHECK_CALL"):
            return "CALL"
        if ua in ("FOLD", "CHECK"):
            return ua
        return ua

    @staticmethod
    def _context(position: str, loose: bool) -> ProblemContext:
        pos = (position or "").strip()
        return ProblemContext(
            position=pos,
            loose_player_exists=bool(loose),
            bb_vs_sb=(pos.upper() == "BBVSSB"),
            open_size_bb=0.0,
        )

    @staticmethod
    def _judge(kind: str, position: str, hand: str, user_action: str, loose: bool, tag: str, repo_dbg: Dict[str, Any]) -> JudgeResult:
        ctx = JUEGOJudge._context(position, loose)
        expected = resolve_expected_action(tag, ctx)
        expected_action = expected.action.value

        ua = JUEGOJudge._norm_user_action(user_action)
        if kind == "ROL" and ua == "LIMP":
            ua = "CALL"
        if kind == "OR_SB" and ua == "CALL":
            ua = "LIMP"

        correct = (ua == expected_action)
        reason = f"Tag={tag!r} -> {expected_action}"
        if expected.size_bb is not None:
            reason += f" ({expected.size_bb}BB)"

        debug = {
            "kind": kind,
            "position": position,
            "hand": hand,
            "detail_tag": (tag or "").strip(),
            "tag_upper": (tag or "").strip().upper(),
            "loose": bool(loose),
            "user_action": ua,
            "correct_action": expected_action,
            "expected_raise_size_bb": expected.size_bb if expected.action == Action.RAISE else None,
            "requires_followup": expected.requires_followup,
            "followup_expected_max_bb": expected.size_bb if expected.requires_followup else None,
            "repo": repo_dbg,
        }
        return JudgeResult(action=expected_action, correct=correct, reason=reason, debug=debug)

    def judge_or(self, position: str, hand: str, user_action: str, loose: bool) -> JudgeResult:
        kind = "OR"
        tag, repo_dbg = self._repo_get_tag(kind, position, hand)
        return self._judge(kind, position, hand, user_action, loose, tag, repo_dbg)

    def judge_or_sb(self, position: str, hand: str, user_action: str, loose: bool) -> JudgeResult:
        kind = "OR_SB"
        tag, repo_dbg = self._repo_get_tag(kind, position, hand)
        return self._judge(kind, position, hand, user_action, loose, tag, repo_dbg)

    def judge_3bet(self, position: str, hand: str, user_action: str, loose: bool) -> JudgeResult:
        kind = "CC_3BET"
        tag, repo_dbg = self._repo_get_tag(kind, position, hand)
        return self._judge(kind, position, hand, user_action, loose, tag, repo_dbg)

    def judge_bb_iso(self, position: str, hand: str, user_action: str, limpers: int, loose: bool) -> JudgeResult:
        kind = "BB_ISO"
        tag, repo_dbg = self._repo_get_tag(kind, position, hand)
        t = (tag or "").strip().upper()
        ua = (user_action or "").strip().upper()
        correct_action = "RAISE" if t.startswith("RAISE") else "CHECK"
        correct = (ua == correct_action)
        reason = f"Tag={tag} -> {correct_action}"
        debug = {
            "kind": kind,
            "position": position,
            "hand": hand,
            "tag": tag,
            "tag_upper": t,
            "limpers": limpers,
            "loose": loose,
            "user_action": ua,
            "correct_action": correct_action,
            "repo": repo_dbg,
        }
        return JudgeResult(action=correct_action, correct=correct, reason=reason, debug=debug)

    def judge_rol(self, position: str, hand: str, user_action: str, loose: bool) -> JudgeResult:
        kind = "ROL"
        tag, repo_dbg = self._repo_get_tag(kind, position, hand)
        return self._judge(kind, position, hand, user_action, loose, tag, repo_dbg)
