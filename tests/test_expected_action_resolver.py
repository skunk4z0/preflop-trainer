import pytest

from core.expected_action import resolve_expected_action
from core.models import Action, ProblemContext


def _ctx(position="EP", loose=False, bb_vs_sb=False, open_size=3.0):
    return ProblemContext(
        position=position,
        loose_player_exists=loose,
        bb_vs_sb=bb_vs_sb,
        open_size_bb=open_size,
    )


@pytest.mark.parametrize(
    "tag,ctx,exp_action,exp_size,exp_followup",
    [
        ("OPEN_RAISE", _ctx("EP"), Action.RAISE, 3.0, False),
        ("OPEN_RAISE", _ctx("MP"), Action.RAISE, 3.0, False),
        ("OPEN_RAISE", _ctx("CO"), Action.RAISE, 3.0, False),
        ("OPEN_RAISE", _ctx("BTN"), Action.RAISE, 2.5, False),
        ("OPEN_RAISE", _ctx("SB"), Action.RAISE, 3.0, False),
        ("OPEN_RAISE_IF_FISH", _ctx("EP", loose=True), Action.RAISE, 3.0, False),
        ("OPEN_RAISE_IF_FISH", _ctx("BTN", loose=True), Action.RAISE, 2.5, False),
        ("OPEN_RAISE_IF_FISH", _ctx("CO", loose=False), Action.FOLD, None, False),
        ("OPEN_RAISE_IF_FISH", _ctx("SB", loose=False), Action.FOLD, None, False),
        ("OPEN_FOLD", _ctx("EP"), Action.FOLD, None, False),
        ("OPEN_FOLD", _ctx("BTN", loose=True), Action.FOLD, None, False),
        ("OPEN_RAISE", _ctx("UNKNOWN"), Action.RAISE, 3.0, False),
        ("SB_OPEN_RAISE_3BB", _ctx("SB"), Action.RAISE, 3.0, False),
        ("SB_LIMP_CALL_LE_3BB", _ctx("SB"), Action.LIMP, 3.0, True),
        ("SB_LIMP_CALL_LE_2_5BB", _ctx("SB"), Action.LIMP, 2.5, True),
        ("SB_LIMP_CALL_LE_2_25BB", _ctx("SB"), Action.LIMP, 2.25, True),
        ("SB_LIMP_CALL_LE_2BB", _ctx("SB"), Action.LIMP, 2.0, True),
        ("SB_LIMP_CALL_LE_3BB", _ctx("SB", open_size=2.0), Action.LIMP, 3.0, True),
        ("SB_LIMP_CALL_LE_2_5BB", _ctx("SB", open_size=3.0), Action.LIMP, 2.5, True),
        ("SB_LIMP_CALL_LE_2_25BB", _ctx("SB", open_size=2.25), Action.LIMP, 2.25, True),
        ("SB_LIMP_CALL_LE_2BB", _ctx("SB", open_size=2.5), Action.LIMP, 2.0, True),
        ("SB_OPEN_RAISE_3BB", _ctx("BTN"), Action.RAISE, 3.0, False),
        ("SB_LIMP_CALL_LE_2_5BB", _ctx("BTN"), Action.LIMP, 2.5, True),
        ("ROL_CALL", _ctx("CO"), Action.CALL, None, False),
        ("ROL_CALL", _ctx("BBvsSB", bb_vs_sb=True), Action.CALL, None, False),
        ("ROL_RAISE_4BB__BB_VS_SB", _ctx("BBvsSB", bb_vs_sb=True), Action.RAISE, 4.0, False),
        ("ROL_RAISE_4BB__BB_VS_SB", _ctx("BB_OOP", bb_vs_sb=False), Action.CALL, None, False),
        ("ROL_RAISE_4BB__BB_VS_SB", _ctx("CO", bb_vs_sb=False), Action.CALL, None, False),
        ("ROL_CALL__VS_FISH", _ctx("BTN", loose=True), Action.CALL, None, False),
        ("ROL_CALL__VS_FISH", _ctx("BTN", loose=False), Action.FOLD, None, False),
        ("ROL_CALL__VS_FISH", _ctx("BBvsSB", loose=True, bb_vs_sb=True), Action.CALL, None, False),
        ("ROL_CALL__VS_FISH", _ctx("BBvsSB", loose=False, bb_vs_sb=True), Action.FOLD, None, False),
        ("ROL_FOLD__NO_FISH", _ctx("SB"), Action.FOLD, None, False),
        ("OVERLIMP_CALL", _ctx("MP"), Action.CALL, None, False),
        ("OVERLIMP_CALL", _ctx("BBvsSB", bb_vs_sb=True), Action.CALL, None, False),
        ("OVERLIMP_CHECK__BB_VS_SB", _ctx("BBvsSB", bb_vs_sb=True), Action.CHECK, None, False),
        ("OVERLIMP_CHECK__BB_VS_SB", _ctx("BTN", bb_vs_sb=False), Action.CALL, None, False),
        ("FOLD_VS_3BET", _ctx("CO"), Action.FOLD, None, False),
        ("CALL_VS_OPEN_LE_3_5X", _ctx("BB VS BTN"), Action.CALL, None, False),
        ("CALL_VS_3BET_LE_8BB", _ctx("BTN"), Action.CALL, None, False),
        ("3BET_VS_4BET_CALL", _ctx("SB VS CO"), Action.RAISE, None, False),
        ("3BET_VS_4BET_SHOVE", _ctx("SB VS CO"), Action.RAISE, None, False),
        ("4BET_VS_5BET_CALL", _ctx("BTN"), Action.RAISE, None, False),
        ("4BET_VS_5BET_FOLD", _ctx("BTN"), Action.RAISE, None, False),
        ("SHOVE_VS_3BET_GE_12BB_IP", _ctx("CO"), Action.RAISE, None, False),
        ("UNKNOWN_TAG", _ctx("CO"), Action.FOLD, None, False),
    ],
)
def test_resolve_expected_action(tag, ctx, exp_action, exp_size, exp_followup):
    got = resolve_expected_action(tag, ctx)
    assert got.action == exp_action
    assert got.size_bb == exp_size
    assert got.requires_followup is exp_followup


@pytest.mark.parametrize(
    "ctx",
    [
        _ctx("CO"),  # OR context
        _ctx("BBvsSB", bb_vs_sb=True),  # ROL context
    ],
)
def test_resolve_expected_action_fold_current_schema(ctx):
    got = resolve_expected_action("FOLD", ctx)
    assert got.action == Action.FOLD
