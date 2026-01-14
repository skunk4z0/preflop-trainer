# juego_judge.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class JudgeResult:
    action: str                 # "FOLD" / "RAISE"
    correct: bool
    show_image: bool
    image_info: Optional[Dict[str, Any]]
    reason: str
    debug: Optional[Dict[str, Any]] = None


class JUEGOJudge:
    """
    UI非依存の判定クラス。
    - Controller から (position, hand, user_action, loose) を受ける
    - Repository 経由で Excel を参照して判定する
    """

    RANKS = "AKQJT98765432"  # 13x13 の並び

    def __init__(self, repo) -> None:
        self.repo = repo

    # =========================
    # OR 判定
    # =========================
    def judge_or(self, position: str, hand: str, user_action: str, loose: bool) -> JudgeResult:
        """
        position: "EP"/"MP"/"CO"/"BTN"
        hand: "AJs"/"T9o"/"77" 等（Controller側で生成済み前提）
        user_action: "FOLD" or "RAISE"
        loose: ルースプレイヤー有無
        """

        # --- 1) AA選別と top-left 確定 ---
        aa_row, aa_col = self.repo.find_aa_anchor("OR", position)
        top_r, top_c = self.repo.get_grid_top_left("OR", position)

        # --- 2) hand -> (r0,c0) へ変換（13x13 / suited上 / offsuit下）---
        r0, c0 = self._hand_to_grid_rc(hand)

        # --- 3) Excelセルの色を取得 ---
        ref = self.repo.get_ref_colors("OR", position)  # {"TIGHT": rgb, "LOOSE": rgb}
        cell_rgb = self.repo.get_cell_fill_rgb_at_grid("OR", position, r0, c0)

        # --- 4) タグ判定 ---
        tag = self._decide_tag_from_colors(cell_rgb, ref)

        # --- 5) 正解アクション決定 ---
        if tag == "FOLD":
            correct_action = "FOLD"
        elif tag == "TIGHT":
            correct_action = "RAISE"
        elif tag == "LOOSE":
            correct_action = "RAISE" if loose else "FOLD"
        else:
            # ここは基本通らない想定（_decide_tag... が FOLD/TIGHT/LOOSE しか返さない）
            correct_action = "FOLD"

        is_correct = (user_action == correct_action)

        # 不正解なら「参照表示をしたい」フラグを立てる（旧仕様互換）
        show_image = not is_correct
        image_info = None
        if show_image:
            image_info = {
                "type": "juego",
                "pos": f"{position}_{'L' if loose else 'N'}"
            }

        reason = self._make_reason(position, hand, tag, loose)

        debug = {
            "kind": "OR",
            "position": position,
            "hand": hand,
            "aa": (aa_row, aa_col),
            "top_left": (top_r, top_c),
            "grid_rc": (r0, c0),
            "ref_colors": ref,
            "cell_rgb": cell_rgb,
            "tag": tag,
            "user_action": user_action,
            "correct_action": correct_action,
            "loose": loose,
        }

        return JudgeResult(
            action=correct_action,
            correct=is_correct,
            show_image=show_image,
            image_info=image_info,
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

        if len(h) != 3:
            raise ValueError(f"Invalid hand format: {hand} (expected like 'AJs','T9o','77')")

        r1, r2, suited_flag = h[0], h[1], h[2].lower()
        if suited_flag not in ("s", "o"):
            raise ValueError(f"Invalid suited flag in hand: {hand} (must end with 's' or 'o')")

        i1 = self._rank_index(r1)
        i2 = self._rank_index(r2)

        # Controllerの_to_hand_keyは「強い方を先」にしている前提だが、
        # 万一逆でも安定するように整える（表記ゆれ対応ではなく安全策）
        hi_idx, lo_idx = (i1, i2) if i1 <= i2 else (i2, i1)

        if suited_flag == "s":
            # 上三角：row=hi, col=lo（hiの方が小さいindex＝強い＝上/左）
            return hi_idx, lo_idx
        else:
            # 下三角：row=lo, col=hi
            return lo_idx, hi_idx

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
