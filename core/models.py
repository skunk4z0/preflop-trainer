# core/models.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Tuple


class Difficulty(Enum):
    BEGINNER = auto()
    INTERMEDIATE = auto()
    ADVANCED = auto()


class ProblemType(Enum):
    YOKOSAWA_OPEN = auto()

    # JUEGO系
    JUEGO_OR = auto()        # 初級：EP/MP/CO/BTN の OR（ルース分岐あり）
    JUEGO_OR_SB = auto()     # 中級：SB の OR_SB（ルース分岐なし）
    JUEGO_ROL = auto()       # 上級：ROL（リンプインに対する対応）
    JUEGO_BB_ISO = auto()    # 別モード：BBアイソ（必要なら使う）
    JUEGO_3BET = auto()


@dataclass(frozen=True)
class SBLimpFollowUpContext:
    """
    2段目：SBでLimpCが正解だった場合に出す追加問題
    「BBのオープンに対して、何BBまでコールするか（閾値）」を選ばせる
    """
    hand_key: str
    expected_max_bb: float
    source_tag: str


@dataclass(frozen=True)
class OpenRaiseProblemContext:
    hole_cards: Tuple[str, str]
    # OR: "EP"/"MP"/"CO"/"BTN"
    # OR_SB: "SB"
    # ROL: "MP"/"CO"/"BTN"/"SB"/"BB_OOP"/"BBvsSB"
    position: str
    open_size_bb: float                 # 表示用（OR/OR_SBはopen size, ROLはraise size）
    loose_player_exists: bool           # OR/ROL用（OR_SBでは常にFalse）
    excel_hand_key: str
    excel_position_key: str
    limpers: int = 0


@dataclass(frozen=True)
class GeneratedQuestion:
    """
    generator.generate(difficulty) の返り値
    """
    problem_type: ProblemType
    ctx: OpenRaiseProblemContext
    answer_mode: str
    header_text: str


@dataclass(frozen=True)
class RangePopupSpec:
    """
    UI非依存の「レンジ表表示指示」。
    UI側は kind/pos で repo から grid を取り、hole_cards でハイライトし、info_text を表示する。
    """
    kind: str            # "OR" / "OR_SB" / "ROL"
    pos: str             # "EP" / "SB" / "BB_OOP" ...（repo側が理解できるキー）
    hole_cards: Tuple[str, str]
    info_text: str
