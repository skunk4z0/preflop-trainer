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
            requires_followup=True,
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

    return ExpectedAction(action=Action.FOLD)
