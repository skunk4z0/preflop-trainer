from __future__ import annotations


_THREE_BET_SIZE_BY_POSITION: dict[str, tuple[int, int]] = {
    "BB VS SB": (8, 9),
    "BB VS BTN": (12, 12),
    "BB VS CO": (12, 12),
    "BB VS EARLY": (12, 12),
    "SB VS BTN": (9, 10),
    "SB VS CO": (9, 10),
    "SB VS EARLY": (9, 10),
    "BTN VS CO": (8, 9),
    "BTN VS EARLY": (8, 9),
    "CO VS EARLY": (8, 9),
    "MP VS EARLY": (8, 9),
}

_ALIASES = {
    "EP": "EARLY",
    "UTG": "EARLY",
}


def _normalize_position(position: str) -> str:
    p = " ".join((position or "").strip().upper().split())
    for src, dst in _ALIASES.items():
        p = p.replace(src, dst)
    return p


def get_3bet_size_range(position: str) -> tuple[int, int]:
    """
    Display-only sizing helper for 3bet spots.
    Returns (0, 0) when no mapping exists.
    """
    return _THREE_BET_SIZE_BY_POSITION.get(_normalize_position(position), (0, 0))
