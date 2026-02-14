from __future__ import annotations

from .models import Action, ExpectedAction, ProblemContext


_OR_OPEN_SIZE_BY_POSITION = {
    "EP": 3.0,
    "MP": 3.0,
    "CO": 3.0,
    "BTN": 2.5,
    "SB": 3.0,
}

_SB_LIMP_THRESHOLD_BY_TAG = {
    "SB_LIMP_CALL_LE_3BB": 3.0,
    "SB_LIMP_CALL_LE_2_5BB": 2.5,
    "SB_LIMP_CALL_LE_2_25BB": 2.25,
    "SB_LIMP_CALL_LE_2BB": 2.0,
}


def resolve_expected_action(tag: str, ctx: ProblemContext) -> ExpectedAction:
    t = (tag or "").strip().upper()
    pos = (ctx.position or "").strip().upper()

    if t == "FOLD":
        return ExpectedAction(action=Action.FOLD)

    if t == "OPEN_RAISE":
        return ExpectedAction(
            action=Action.RAISE,
            size_bb=_OR_OPEN_SIZE_BY_POSITION.get(pos, 3.0),
        )
    if t == "OPEN_RAISE_IF_FISH":
        if ctx.loose_player_exists:
            return ExpectedAction(
                action=Action.RAISE,
                size_bb=_OR_OPEN_SIZE_BY_POSITION.get(pos, 3.0),
            )
        return ExpectedAction(action=Action.FOLD)
    if t == "OPEN_FOLD":
        return ExpectedAction(action=Action.FOLD)

    if t == "SB_OPEN_RAISE_3BB":
        return ExpectedAction(action=Action.RAISE, size_bb=3.0)
    if t in _SB_LIMP_THRESHOLD_BY_TAG:
        return ExpectedAction(
            action=Action.LIMP,
            size_bb=_SB_LIMP_THRESHOLD_BY_TAG[t],
            followup_required=True,
        )

    if t == "ROL_CALL":
        return ExpectedAction(action=Action.CALL)
    if t == "ROL_RAISE_4BB__BB_VS_SB":
        if ctx.bb_vs_sb:
            return ExpectedAction(action=Action.RAISE, size_bb=4.0)
        return ExpectedAction(action=Action.CALL)
    if t == "ROL_CALL__VS_FISH":
        if ctx.loose_player_exists:
            return ExpectedAction(action=Action.CALL)
        return ExpectedAction(action=Action.FOLD)
    if t == "ROL_FOLD__NO_FISH":
        return ExpectedAction(action=Action.FOLD)
    if t == "OVERLIMP_CALL":
        return ExpectedAction(action=Action.CALL)
    if t == "OVERLIMP_CHECK__BB_VS_SB":
        if ctx.bb_vs_sb:
            return ExpectedAction(action=Action.CHECK)
        return ExpectedAction(action=Action.CALL)

    # 3BET pipeline tag families (final_tags.json schema)
    # CC_3BET is modeled as:
    # - stage 1: open-facing decision (CALL / 3BET / FOLD)
    # - stage 2: only for 3BET_VS_4BET_* (reaction to 4bet)
    if t.startswith("3BET_VS_4BET_"):
        if t == "3BET_VS_4BET_SHOVE":
            return ExpectedAction(
                action=Action.RAISE,
                followup_expected_action=Action.RAISE,
                followup_required=True,
            )
        if t == "3BET_VS_4BET_CALL":
            return ExpectedAction(
                action=Action.RAISE,
                followup_expected_action=Action.CALL,
                followup_required=True,
            )
        if t == "3BET_VS_4BET_FOLD":
            return ExpectedAction(
                action=Action.RAISE,
                followup_expected_action=Action.FOLD,
                followup_required=True,
            )
        if t == "3BET_VS_4BET_CALL_SITUATIONAL":
            # TODO: support this with scenario-aware follow-up generation.
            return ExpectedAction(action=Action.RAISE)
        return ExpectedAction(action=Action.RAISE)

    if t.startswith("CALL_VS_OPEN_"):
        return ExpectedAction(action=Action.CALL)

    if t == "FOLD_VS_3BET":
        return ExpectedAction(action=Action.FOLD)
    if t.startswith("CALL_VS_3BET_"):
        return ExpectedAction(action=Action.CALL)
    if t == "4BET_VS_5BET_FOLD":
        return ExpectedAction(action=Action.FOLD)
    if t.startswith("4BET_VS_5BET_"):
        return ExpectedAction(action=Action.RAISE)
    if t.startswith("SHOVE_VS_"):
        return ExpectedAction(action=Action.RAISE)

    return ExpectedAction(action=Action.FOLD)
