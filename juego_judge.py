# juego_judge.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


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

    # -------------------------
    # small helpers
    # -------------------------
    def _repo_get_tag(self, kind: str, position: str, hand: str):
        """
        repo.get_tag_for_hand が
          - tag だけ返す
          - (tag, repo_dbg) を返す
        どちらでも動くようにする。
        """
        res = self.repo.get_tag_for_hand(kind, position, hand)
        if isinstance(res, tuple) and len(res) == 2:
            tag, repo_dbg = res
        else:
            tag, repo_dbg = res, {}
        return tag, repo_dbg

    def _parse_limp_tag_to_max_bb(self, tag: str) -> Optional[float]:
        """
        "LimpCx2o" / "LimpCx2.25o" / "LimpCx2.5o" / "LimpCx3o"
        から 2.0 / 2.25 / 2.5 / 3.0 を取り出す。
        """
        if not tag:
            return None
        t = str(tag).strip()
        if not t.upper().startswith("LIMPCX"):
            return None

        # "LimpCx" の後〜末尾の "o"/"O" の前を数値として読む
        body = t[len("LimpCx") :].strip()
        if body.lower().endswith("o"):
            body = body[:-1]

        try:
            return float(body)
        except Exception:
            return None

    # -------------------------
    # OR (EP/MP/CO/BTN)
    # ※あなたの既存挙動を壊さないため、必要最小限の形
    # -------------------------
    def judge_or(self, position: str, hand: str, user_action: str, loose: bool) -> JudgeResult:
        kind = "OR"
        tag, repo_dbg = self._repo_get_tag(kind, position, hand)

        t = (tag or "").strip().upper()
        ua = (user_action or "").strip().upper()

        # 既存仕様（サマリー準拠）
        # 通常：TIGHT=RAISE、LOOSE/FOLD=FOLD
        # ルースあり：TIGHT/LOOSE=RAISE、FOLD=FOLD
        if loose:
            correct_action = "RAISE" if t in {"TIGHT", "LOOSE"} else "FOLD"
        else:
            correct_action = "RAISE" if t == "TIGHT" else "FOLD"

        correct = (ua == correct_action)
        reason = f"Tag={tag} -> {correct_action}"

        debug = {
            "kind": kind,
            "position": position,
            "hand": hand,
            "tag": tag,
            "tag_upper": t,
            "loose": loose,
            "user_action": ua,
            "correct_action": correct_action,
            "repo": repo_dbg,
        }

        return JudgeResult(action=correct_action, correct=correct, reason=reason, debug=debug)

    # -------------------------
    # OR_SB (SB)
    # 重要：detail_tag を debug に必ず残す（2段目に必要）
    # -------------------------
    def judge_or_sb(self, position: str, hand: str, user_action: str, loose: bool) -> JudgeResult:
        kind = "OR_SB"

        # ★ここを統一：repoの返り値が tag単体でも (tag,dbg) でも動く
        tag, repo_dbg = self._repo_get_tag(kind, position, hand)

        # 正規化（空白除去）
        tag_norm = (tag or "").strip()
        t = tag_norm.upper()

        if t == "RAISE_3BB":
            correct_action = "RAISE"
        elif t.startswith("LIMPC"):
            correct_action = "LIMP_CALL"
        else:
            correct_action = "FOLD"

        ua = (user_action or "").strip().upper()
        is_correct = (ua == correct_action)

        # ★未定義関数を使わない（まず落ちないことを優先）
        reason = f"Tag={tag_norm} -> {correct_action}"

        debug = {
            "kind": kind,
            "position": position,
            "hand": hand,

            # ★ここが2段目に必要（すでに正しい）
            "detail_tag": tag_norm,  # 例: "LimpCx2.25o"

            "tag": tag,
            "tag_upper": t,
            "loose": loose,  # OR_SBでは未使用だが保持は可
            "user_action": ua,
            "correct_action": correct_action,
            "repo": repo_dbg,
            "followup_expected_max_bb": self._parse_limp_tag_to_max_bb(tag_norm),

        }

        return JudgeResult(
            action=correct_action,
            correct=is_correct,
            reason=reason,
            debug=debug,
        )


    # -------------------------
    # BB_ISO（別モード用：コール/リンプ後のBB判断）
    # ※ controller が呼ぶので最低限用意
    # -------------------------
    def judge_bb_iso(self, position: str, hand: str, user_action: str, limpers: int, loose: bool) -> JudgeResult:
        kind = "BB_ISO"
        tag, repo_dbg = self._repo_get_tag(kind, position, hand)

        t = (tag or "").strip().upper()
        ua = (user_action or "").strip().upper()

        # 表のタグ仕様に合わせて調整してください（最小の仮置き）
        # - tag が "RAISE_*" 系なら RAISE
        # - それ以外は CHECK
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
