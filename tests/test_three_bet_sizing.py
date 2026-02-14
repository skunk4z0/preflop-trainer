from core.three_bet_sizing import get_3bet_size_range


def test_get_3bet_size_range_known_mappings():
    assert get_3bet_size_range("BB VS SB") == (8, 9)
    assert get_3bet_size_range("BB VS BTN") == (12, 12)
    assert get_3bet_size_range("SB VS CO") == (9, 10)
    assert get_3bet_size_range("BTN VS EP") == (8, 9)


def test_get_3bet_size_range_unknown_defaults_to_zeroes():
    assert get_3bet_size_range("HJ VS BTN") == (0, 0)
