# juego_judge.py
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


# =========================
# Public result type
# =========================
@dataclass(frozen=True)
class JudgeResult:
    """
    Judgeは「採点」だけを返す。
    UI操作（ボタン表示など）やログ保存は controller / engine / telemetry の責務。
    """
    action: str                 # 正解の“正規化アクション”（例: RAISE / FOLD / CALL / LIMP_CALL / CHECK）
    correct: bool
    reason: str
    debug: Dict[str, Any]
    show_image: bool = False
    image_info: Optional[Dict[str, Any]] = None


# =========================
# Action vocabulary (normalized)
# =========================
A_FOLD = "FOLD"
A_RAISE = "RAISE"
A_CALL = "CALL"
A_LIMP_CALL = "LIMP_CALL"
A_CHECK = "CHECK"


def _norm_ws(s: str) -> str:
    # NBSP等を潰して強制的に比較可能にする
    return (s or "").replace("\u00A0", " ").strip()


def _norm_tag(tag: str) -> str:
    return _norm_ws(tag).upper()


def _norm_user_action(user_action: str, *, kind: str) -> str:
    """
    UI/旧コード由来の表記揺れを、採点用の最小語彙へ正規化する。
    - 3BET / OPEN_* / RAISE_* は全部 RAISE
    - OR_SB の “CALL” は互換で LIMP_CALL 扱い（UIがCALLを返した過去があるため）
    - 3BET の “LIMP_CALL” は CALL 扱い（互換）
    """
    ua = _norm_ws(user_action).upper()
    if ua in ("", A_FOLD):
        return A_FOLD

    if ua.startswith("OPEN") or ua.startswith("RAISE") or ua.startswith("3BET") or ua.startswith("4BET") or ua.startswith("SHOVE"):
        return A_RAISE

    if ua in ("CALL", "CHECK_CALL", "LIMP", A_LIMP_CALL):
        if kind == "OR_SB":
            return A_LIMP_CALL
        if kind in ("CC_3BET", "3BET_VS_COLD4BET", "CALL_3BET_4BET", "CC_3BET_MULTI"):
            return A_CALL
        # ROL等はCALLで評価する
        return A_CALL

    if ua == A_CHECK:
        return A_CHECK

    return ua


def _parse_bb_from_tag(tag_upper: str) -> Optional[float]:
    """
    例:
      OPEN_3_BB            -> 3.0
      LIMP_CALL_2_25_BB    -> 2.25
      CALL_VS_3BET_LE_9_5BB-> 9.5
    """
    t = tag_upper or ""
    # _BB / BB どちらも許可。小数は "_" を "." と解釈。
    m = re.search(r"([0-9]+(?:_[0-9]+)?)\s*_?BB\b", t)
    if not m:
        return None
    num = m.group(1).replace("_", ".")
    try:
        return float(num)
    except ValueError:
        return None


# =========================
# Tag -> expected action mapping (centralized)
# =========================
def _expected_action_or(*, tag_upper: str, loose: bool) -> str:
    # OR: OPEN_TIGHT / OPEN_LOOSE / FOLD
    if loose:
        return A_RAISE if tag_upper in ("OPEN_TIGHT", "OPEN_LOOSE") else A_FOLD
    return A_RAISE if tag_upper == "OPEN_TIGHT" else A_FOLD


def _expected_action_or_sb(*, tag_upper: str) -> str:
    # OR_SB: OPEN_3_BB / LIMP_CALL_* / FOLD
    if tag_upper.startswith("OPEN_"):
        return A_RAISE
    if tag_upper.startswith("LIMP_CALL_"):
        return A_LIMP_CALL
    return A_FOLD


def _expected_action_3bet(*, tag_upper: str) -> str:
    """
    現状UIの3BETモードは「FOLD / 3BET(=RAISE) / CALL」の3択。
    range側は詳細タグが多いので、いったん“1段目アクション”へ落とす。

    CALL系:
      - CALL_VS_OPEN_...
      - CALL_VS_3BET_...
    それ以外の 3BET/4BET/SHOVE/… は「攻撃的=RAISE」扱い（将来follow-upで分岐可能）
    """
    t = tag_upper or ""
    if t.startswith("CALL_VS_OPEN") or t.startswith("CALL_VS_3BET") or t.startswith("CALL_"):
        return A_CALL
    if t.startswith("FOLD"):
        return A_FOLD
    if "3BET" in t or "4BET" in t or "SHOVE" in t:
        return A_RAISE
    return A_FOLD


def _expected_action_rol(*, position: str, tag_upper: str, loose: bool) -> Tuple[str, Optional[float]]:
    """
    ROL: tagは
      - ROL_ALWAYS
      - ROL_VS_FISH
      - OVERLIMP_VS_FISH
      - FOLD（無色など）

    返り値: (expected_action, expected_raise_size_bb)
    """
    pos = _norm_ws(position)

    # BBvsSB 特例：ROL_ALWAYS(=4BB) 以外は CHECK
    if pos == "BBvsSB":
        if tag_upper == "ROL_ALWAYS":
            return A_RAISE, 4.0
        return A_CHECK, None

    # 通常：Alwaysは5BB
    if tag_upper == "ROL_ALWAYS":
        return A_RAISE, 5.0

    # Overlimpは常にCALL
    if tag_upper == "OVERLIMP_VS_FISH":
        return A_CALL, None

    # ROL_VS_FISH は loose でCALL / tightでFOLD
    if tag_upper == "ROL_VS_FISH":
        return (A_CALL, None) if loose else (A_FOLD, None)

    return A_FOLD, None


# =========================
# Judge
# =========================
class JUEGOJudge:
    def __init__(self, repo) -> None:
        self.repo = repo

    def _repo_get_tag(self, kind: str, position: str, hand: str) -> Tuple[str, Dict[str, Any]]:
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
        return str(tag or ""), (repo_dbg or {})

    # -------------------------
    # OR
    # -------------------------
    def judge_or(self, position: str, hand: str, user_action: str, loose: bool) -> JudgeResult:
        kind = "OR"
        tag, repo_dbg = self._repo_get_tag(kind, position, hand)
        tag_u = _norm_tag(tag)

        expected = _expected_action_or(tag_upper=tag_u, loose=bool(loose))
        ua = _norm_user_action(user_action, kind=kind)
        ok = (ua == expected)
        reason = f"Tag={tag_u} -> {expected}"

        debug = {
            "kind": kind,
            "position": position,
            "hand": hand,
            "tag": tag,
            "detail_tag": tag,          # engineが拾うキー
            "expected_tag": tag,        # engineが拾うキー
            "tag_upper": tag_u,
            "loose": bool(loose),
            "user_action_raw": user_action,
            "user_action": ua,
            "expected_action": expected,
            "correct_action": expected,  # 旧互換キー
            "repo": repo_dbg,
        }
        return JudgeResult(action=expected, correct=ok, reason=reason, debug=debug)

    # -------------------------
    # OR_SB
    # -------------------------
    def judge_or_sb(self, position: str, hand: str, user_action: str, loose: bool) -> JudgeResult:
        kind = "OR_SB"
        tag, repo_dbg = self._repo_get_tag(kind, position, hand)
        tag_u = _norm_tag(tag)

        expected = _expected_action_or_sb(tag_upper=tag_u)
        ua = _norm_user_action(user_action, kind=kind)
        ok = (ua == expected)
        reason = f"Tag={tag_u} -> {expected}"

        debug = {
            "kind": kind,
            "position": position,
            "hand": hand,
            "tag": tag,
            "detail_tag": tag,
            "expected_tag": tag,
            "tag_upper": tag_u,
            "loose": bool(loose),
            "user_action_raw": user_action,
            "user_action": ua,
            "expected_action": expected,
            "correct_action": expected,  # 旧互換キー
            "expected_raise_size_bb": _parse_bb_from_tag(tag_u) if expected == A_RAISE else None,
            # follow-up（LIMP_CALL_*）の閾値BBも取れる形にしておく（engine側で使ってもOK）
            "followup_expected_max_bb": _parse_bb_from_tag(tag_u) if expected == A_LIMP_CALL else None,
            "repo": repo_dbg,
        }
        return JudgeResult(action=expected, correct=ok, reason=reason, debug=debug)

    # -------------------------
    # 3BET（現状は CC_3BET を採点対象にする）
    # -------------------------
    def judge_3bet(self, position: str, hand: str, user_action: str, loose: bool) -> JudgeResult:
        # 重要：config / repo 側の kind は "CC_3BET"（"3BET" では remind できない）
        kind = "CC_3BET"
        tag, repo_dbg = self._repo_get_tag(kind, position, hand)
        tag_u = _norm_tag(tag)

        expected = _expected_action_3bet(tag_upper=tag_u)
        ua = _norm_user_action(user_action, kind=kind)
        ok = (ua == expected)
        reason = f"Tag={tag_u} -> {expected}"

        debug = {
            "kind": kind,
            "position": position,
            "hand": hand,
            "tag": tag,
            "detail_tag": tag,
            "expected_tag": tag,
            "tag_upper": tag_u,
            "loose": bool(loose),
            "user_action_raw": user_action,
            "user_action": ua,
            "expected_action": expected,
            "correct_action": expected,  # 旧互換キー
            "repo": repo_dbg,
        }
        return JudgeResult(action=expected, correct=ok, reason=reason, debug=debug)

    # -------------------------
    # ROL
    # -------------------------
    def judge_rol(self, position: str, hand: str, user_action: str, loose: bool) -> JudgeResult:
        kind = "ROL"
        tag, repo_dbg = self._repo_get_tag(kind, position, hand)
        tag_u = _norm_tag(tag)

        expected_action, expected_bb = _expected_action_rol(position=position, tag_upper=tag_u, loose=bool(loose))
        ua = _norm_user_action(user_action, kind=kind)

        # ROLは「LIMP_CALL」互換も CALL 扱い（古いUI互換）
        if ua == A_LIMP_CALL:
            ua = A_CALL

        ok = (ua == expected_action)
        reason = f"Tag={tag_u} -> {expected_action}" + (f" ({expected_bb}BB)" if expected_bb else "")

        debug = {
            "kind": kind,
            "position": position,
            "hand": hand,
            "tag": tag,
            "detail_tag": tag,
            "expected_tag": tag,
            "tag_upper": tag_u,
            "loose": bool(loose),
            "user_action_raw": user_action,
            "user_action": ua,
            "expected_action": expected_action,
            "correct_action": expected_action,  # 旧互換キー
            "expected_raise_size_bb": expected_bb,
            "repo": repo_dbg,
        }
        return JudgeResult(action=expected_action, correct=ok, reason=reason, debug=debug)

    # -------------------------
    # (任意) BB_ISO：未使用でも controller が呼ぶ可能性があるなら残す
    # -------------------------
    def judge_bb_iso(self, position: str, hand: str, user_action: str, limpers: int, loose: bool) -> JudgeResult:
        kind = "BB_ISO"
        tag, repo_dbg = self._repo_get_tag(kind, position, hand)
        tag_u = _norm_tag(tag)

        # ここはあなたの表仕様が固まってないので “安全な仮実装” のまま（明示）
        expected = A_RAISE if ("RAISE" in tag_u or tag_u.startswith("ISO")) else A_CHECK
        ua = _norm_user_action(user_action, kind=kind)
        ok = (ua == expected)
        reason = f"Tag={tag_u} -> {expected}"

        debug = {
            "kind": kind,
            "position": position,
            "hand": hand,
            "tag": tag,
            "detail_tag": tag,
            "expected_tag": tag,
            "tag_upper": tag_u,
            "limpers": int(limpers),
            "loose": bool(loose),
            "user_action_raw": user_action,
            "user_action": ua,
            "expected_action": expected,
            "correct_action": expected,
            "repo": repo_dbg,
        }
        return JudgeResult(action=expected, correct=ok, reason=reason, debug=debug)
