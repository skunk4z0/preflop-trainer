import os
from dataclasses import dataclass
import config


# ==================================================
# JudgeResult（全判定共通の戻り値）
# ==================================================

@dataclass
class JudgeResult:
    action: str              # "RAISE" / "CALL" / "FOLD"
    reason: str              # 解説
    show_image: bool = False
    image_info: dict = None


# ==================================================
# ヨコサワ式 定義
# ==================================================

YOKOSAWA_HAND_MAP = { 
    "SS": ["AA", "AKs", "AKo", "KK", "QQ"],
    "S":  ["AQs", "AJs", "ATs", "KQs", "AQo", "JJ", "TT", "99"],
    "A":  ["KJs", "KQo", "QJs", "AJo", "JTs", "88", "77"],
    "B":  ["A9s", "A8s", "A7s", "A6s", "A5s", "A4s", "A3s", "A2s",
           "KTs", "K9s", "QTs", "KJo", "ATo", "T9s", "66", "55"],
    "C":  ["Q9s", "QJo", "J9s", "KTo", "JTo", "T8s", "A9o",
           "98s", "44", "33", "22"],
    "D":  ["K8s", "K7s", "K6s", "K5s", "K4s", "K3s", "K2s",
           "Q8s", "Q7s", "Q6s", "J8s", "J7s",
           "QTo", "K9o", "Q9o", "J9o", "T9o",
           "97s", "A8o", "87s", "A7o", "76s", "65s"],
    "E":  ["Q7s", "Q6s", "Q5s", "Q4s", "Q3s", "Q2s",
           "J7s", "J6s", "J5s", "J4s", "J3s", "J2s",
           "T7s", "T6s", "T5s", "T4s", "T3s", "T2s",
           "97s", "96s", "95s", "94s", "93s", "92s",
           "86s", "85s", "84s", "83s", "82s",
           "75s", "74s", "73s", "72s",
           "64s", "63s", "62s",
           "53s", "52s", "42s",
           "A6o", "A5o", "A4o", "A3o", "A2o",
           "K7o", "K6o", "K5o", "K4o", "K3o", "K2o",
           "Q7o", "Q6o", "Q5o", "Q4o", "Q3o", "Q2o",
           "J9o", "J8o", "J7o", "J6o", "J5o", "J4o", "J3o", "J2o",
           "T8o", "T7o", "T6o", "T5o", "T4o", "T3o", "T2o",
           "98o", "97o", "96o", "95o", "94o", "93o", "92o",
           "87o", "86o", "85o", "84o", "83o", "82o",
           "76o", "75o", "74o", "73o", "72o",
           "65o", "64o", "63o", "62o",
           "54o", "53o", "52o",
           "43o", "42o", "32o"]
}

RANK_VALUES = {"SS": 1, "S": 2, "A": 3, "B": 4, "C": 5, "D": 6, "E": 7}

YOKOSAWA_POS_LIMITS = {
    "EP": "A",
    "HJ": "B",
    "CO": "C",
    "BTN": "D",
    "SB": "C",
    "BB": "C"
}


# ==================================================
# ヨコサワ式 Judge
# ==================================================

class YokosawaJudge:

    def judge(self, pos, hand, situation="オープン", opponent_pos=None):
        self.pos_key = pos
        self.hand_str = hand
        self.situation = situation
        self.opponent_pos = opponent_pos

        action, reason = self.get_yokosawa_logic()

        return JudgeResult(
            action=action,
            reason=reason,
            show_image=True,
            image_info={
                "type": "yoko",
                "images": [
                    os.path.join(config.YOKOSAWA_IMAGE_DIR, "open1.png"),
                    os.path.join(config.YOKOSAWA_IMAGE_DIR, "open2.png"),
                ]
            }
        )

    def get_yokosawa_logic(self):
        my_rank = "E"
        for r, hands in YOKOSAWA_HAND_MAP.items():
            if self.hand_str in hands:
                my_rank = r
                break

        my_val = RANK_VALUES[my_rank]

        if self.situation == "オープン":
            limit_rank = YOKOSAWA_POS_LIMITS.get(self.pos_key, "A")
            limit_val = RANK_VALUES[limit_rank]
            ans = "RAISE" if my_val <= limit_val else "FOLD"
            reason = f"{self.pos_key}基準は{limit_rank}以上です。"
            return ans, reason

        # ディフェンス
        if self.pos_key == "BB":
            ans = "CALL" if my_val <= RANK_VALUES["C"] else "FOLD"
            return ans, "BBディフェンスはCランク以上で参加です。"

        opp_limit_val = RANK_VALUES[YOKOSAWA_POS_LIMITS[self.opponent_pos]]

        if my_val > opp_limit_val:
            return "FOLD", f"相手({self.opponent_pos})の基準以下です。"
        if my_val <= opp_limit_val - 2:
            return "RAISE", "相手基準より2ランク以上上なのでリレイズです。"
        if my_val == opp_limit_val - 1:
            return "CALL", "相手基準より1ランク上なのでコールです。"

        return "FOLD", "判断外です。"


# ==================================================
# JUEGO Judge
# ==================================================

class JuegoJudge:

    def __init__(self):
    pass

    # ---------- OR ----------
    def judge_or(self, pos, hand):
        action, reason = self.excel.judge_or(pos, hand)

        return JudgeResult(
            action=action,
            reason=reason,
            show_image=True,
            image_info={"type": "juego", "pos": pos}
        )

    # ---------- SB OPEN ----------
    def judge_sb_open(self, hand):
        action, reason = self.excel.judge_sb_open(hand)

        return JudgeResult(
            action=action,
            reason=reason,
            show_image=True,
            image_info={"type": "juego", "pos": "SB"}
        )

    # ---------- SB LIMP → BB RAISE ----------
    def judge_sb_limp_call(self, hand, bb_size):
        action, reason = self.excel.judge_sb_limp_call(hand, bb_size)

        return JudgeResult(
            action=action,
            reason=reason,
            show_image=True,
            image_info={"type": "juego", "pos": f"SB_{bb_size}"}
        )
