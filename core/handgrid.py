# core/handgrid.py
from __future__ import annotations

RANKS = "AKQJT98765432"


def _idx(r: str) -> int:
    r = r.upper()
    if r not in RANKS:
        raise ValueError(f"bad rank: {r}")
    return RANKS.index(r)


def hand_key_to_rc(hand_key: str) -> tuple[int, int]:
    """
    0-based (row, col) in 13x13.
    - Pair: "AA" -> (A,A) diagonal
    - Suited: "AKS" -> upper triangle
    - Offsuit: "AKO" -> lower triangle
    """
    hk = hand_key.strip().upper()

    if len(hk) == 2:
        if hk[0] != hk[1]:
            raise ValueError(f"pair must be like AA: {hand_key}")
        i = _idx(hk[0])
        return (i, i)

    if len(hk) != 3:
        raise ValueError(f"bad hand_key: {hand_key}")

    r1, r2, t = hk[0], hk[1], hk[2]
    i1, i2 = _idx(r1), _idx(r2)
    if i1 == i2:
        raise ValueError(f"pair must be 2 chars: {hand_key}")

    hi = min(i1, i2)
    lo = max(i1, i2)

    if t == "S":
        return (hi, lo)  # upper
    if t == "O":
        return (lo, hi)  # lower
    raise ValueError(f"bad suitedness (S/O): {hand_key}")


def rc_to_hand_key(r: int, c: int) -> str:
    if not (0 <= r < 13 and 0 <= c < 13):
        raise ValueError(f"rc out of range: {(r, c)}")

    if r == c:
        rr = RANKS[r]
        return rr + rr

    hi = min(r, c)
    lo = max(r, c)
    r1, r2 = RANKS[hi], RANKS[lo]
    return f"{r1}{r2}{'S' if r < c else 'O'}"
