from __future__ import annotations

import re
from typing import Optional

from .models import ProblemType, SBLimpFollowUpContext

FOLLOWUP_CHOICES: list[float] = [2, 2.25, 2.5, 3]
FOLLOWUP_PROMPT = "追加問題：BBのオープンに対して、何BBまでコールしますか？"


def _parse_expected_max_bb(tag_upper: str) -> Optional[float]:
    if not tag_upper:
        return None

    tu = str(tag_upper).strip().upper().replace(" ", "")

    m = re.match(r"^LIMP_CALL_(\d+(?:_\d+)?)_BB$", tu)
    if m:
        try:
            return float(m.group(1).replace("_", "."))
        except ValueError:
            return None

    m = re.match(r"^LIMPCX\s*([0-9]+(?:\.[0-9]+)?)O?$", tu)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None

    m = re.match(r"^CALL_VS_OPEN_LE_(\d+(?:_\d+)?)X$", tu)
    if m:
        try:
            return float(m.group(1).replace("_", "."))
        except ValueError:
            return None

    return None


def maybe_create_followup(
    problem_kind: Optional[ProblemType],
    tag_upper: str,
    expected_action: str,
    stage1_correct: bool,
) -> Optional[SBLimpFollowUpContext]:
    if not stage1_correct:
        return None

    tag = str(tag_upper or "").strip()
    expected = str(expected_action or "").strip().upper()

    if problem_kind == ProblemType.JUEGO_OR_SB and expected == "LIMP_CALL":
        expected_max_bb = _parse_expected_max_bb(tag)
        if expected_max_bb is not None:
            return SBLimpFollowUpContext(
                hand_key="",
                expected_max_bb=expected_max_bb,
                source_tag=tag,
            )
        return None

    if (
        problem_kind == ProblemType.JUEGO_3BET
        and expected == "CALL"
        and tag.upper().startswith("CALL_VS_OPEN_LE_")
    ):
        expected_max_bb = _parse_expected_max_bb(tag)
        if expected_max_bb is not None:
            return SBLimpFollowUpContext(
                hand_key="",
                expected_max_bb=expected_max_bb,
                source_tag=tag,
            )

    return None
