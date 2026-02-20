from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RateByKey:
    key: str
    attempts: int
    correct: int
    accuracy: float


@dataclass(frozen=True)
class RecentTrend:
    recent_n: int
    attempts: int
    correct: int
    accuracy: float


@dataclass(frozen=True)
class StatsSummary:
    total_attempts: int
    total_correct: int
    total_accuracy: float
    by_kind: list[RateByKey]
    by_position: list[RateByKey]
    recent: RecentTrend

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_attempts": self.total_attempts,
            "total_correct": self.total_correct,
            "total_accuracy": self.total_accuracy,
            "by_kind": [asdict(item) for item in self.by_kind],
            "by_position": [asdict(item) for item in self.by_position],
            "recent_n": self.recent.recent_n,
            "recent_accuracy": self.recent.accuracy,
            "recent": asdict(self.recent),
        }


@dataclass(frozen=True)
class WeaknessReport:
    scope: str
    recent_n: int | None
    min_attempts: int
    top_k: int
    weak_kinds: list[RateByKey]
    weak_positions: list[RateByKey]


def _safe_accuracy(correct: int, attempts: int) -> float:
    return float(correct) / float(attempts) if attempts > 0 else 0.0


def _row_to_rate(key: str, attempts: int, correct: int) -> RateByKey:
    return RateByKey(
        key=key,
        attempts=int(attempts),
        correct=int(correct),
        accuracy=_safe_accuracy(int(correct), int(attempts)),
    )


def compute_summary(db_path: Path, recent_n: int = 50) -> StatsSummary:
    db_path_str = str(Path(db_path))
    recent_n = int(recent_n)
    if recent_n < 1:
        recent_n = 1

    with sqlite3.connect(db_path_str) as con:
        total_attempts_raw, total_correct_raw = con.execute(
            "SELECT COUNT(*), COALESCE(SUM(is_correct), 0) FROM attempts"
        ).fetchone()
        total_attempts = int(total_attempts_raw or 0)
        total_correct = int(total_correct_raw or 0)

        by_kind_rows = con.execute(
            """
            SELECT kind, COUNT(*), COALESCE(SUM(is_correct), 0)
            FROM attempts
            GROUP BY kind
            ORDER BY COUNT(*) DESC
            """
        ).fetchall()
        by_kind = [_row_to_rate(str(kind), int(attempts), int(correct)) for kind, attempts, correct in by_kind_rows]

        by_position_rows = con.execute(
            """
            SELECT position, COUNT(*), COALESCE(SUM(is_correct), 0)
            FROM attempts
            GROUP BY position
            ORDER BY COUNT(*) DESC
            """
        ).fetchall()
        by_position = [
            _row_to_rate(str(position), int(attempts), int(correct))
            for position, attempts, correct in by_position_rows
        ]

        recent_attempts_raw, recent_correct_raw = con.execute(
            """
            SELECT COUNT(*), COALESCE(SUM(is_correct), 0)
            FROM (
                SELECT is_correct
                FROM attempts
                ORDER BY id DESC
                LIMIT ?
            )
            """,
            (recent_n,),
        ).fetchone()
        recent_attempts = int(recent_attempts_raw or 0)
        recent_correct = int(recent_correct_raw or 0)

    recent = RecentTrend(
        recent_n=recent_n,
        attempts=recent_attempts,
        correct=recent_correct,
        accuracy=_safe_accuracy(recent_correct, recent_attempts),
    )

    return StatsSummary(
        total_attempts=total_attempts,
        total_correct=total_correct,
        total_accuracy=_safe_accuracy(total_correct, total_attempts),
        by_kind=by_kind,
        by_position=by_position,
        recent=recent,
    )


def compute_summary_dict(db_path: Path, recent_n: int = 50) -> dict[str, Any]:
    return compute_summary(db_path=db_path, recent_n=recent_n).to_dict()


def compute_weakness_report(
    db_path: Path,
    *,
    scope: str,
    recent_n: int = 20,
    min_attempts: int = 5,
    top_k: int = 3,
) -> WeaknessReport:
    db_path_str = str(Path(db_path))
    recent_n = max(1, int(recent_n))
    min_attempts = max(1, int(min_attempts))
    top_k = max(1, int(top_k))

    if scope not in {"recent", "all"}:
        raise ValueError("scope must be 'recent' or 'all'")

    if scope == "recent":
        kind_sql = """
            SELECT kind, COUNT(*), COALESCE(SUM(is_correct), 0)
            FROM (
                SELECT kind, position, is_correct
                FROM attempts
                ORDER BY id DESC
                LIMIT ?
            ) t
            GROUP BY kind
            HAVING COUNT(*) >= ?
            ORDER BY (COALESCE(SUM(is_correct),0) * 1.0 / COUNT(*)) ASC, COUNT(*) DESC
            LIMIT ?
        """
        position_sql = """
            SELECT position, COUNT(*), COALESCE(SUM(is_correct), 0)
            FROM (
                SELECT kind, position, is_correct
                FROM attempts
                ORDER BY id DESC
                LIMIT ?
            ) t
            GROUP BY position
            HAVING COUNT(*) >= ?
            ORDER BY (COALESCE(SUM(is_correct),0) * 1.0 / COUNT(*)) ASC, COUNT(*) DESC
            LIMIT ?
        """
        params = (recent_n, min_attempts, top_k)
        report_recent_n: int | None = recent_n
    else:
        kind_sql = """
            SELECT kind, COUNT(*), COALESCE(SUM(is_correct), 0)
            FROM attempts
            GROUP BY kind
            HAVING COUNT(*) >= ?
            ORDER BY (COALESCE(SUM(is_correct),0) * 1.0 / COUNT(*)) ASC, COUNT(*) DESC
            LIMIT ?
        """
        position_sql = """
            SELECT position, COUNT(*), COALESCE(SUM(is_correct), 0)
            FROM attempts
            GROUP BY position
            HAVING COUNT(*) >= ?
            ORDER BY (COALESCE(SUM(is_correct),0) * 1.0 / COUNT(*)) ASC, COUNT(*) DESC
            LIMIT ?
        """
        params = (min_attempts, top_k)
        report_recent_n = None

    with sqlite3.connect(db_path_str) as con:
        kind_rows = con.execute(kind_sql, params).fetchall()
        weak_kinds = [_row_to_rate(str(key), int(attempts), int(correct)) for key, attempts, correct in kind_rows]

        position_rows = con.execute(position_sql, params).fetchall()
        weak_positions = [
            _row_to_rate(str(key), int(attempts), int(correct))
            for key, attempts, correct in position_rows
        ]

    return WeaknessReport(
        scope=scope,
        recent_n=report_recent_n,
        min_attempts=min_attempts,
        top_k=top_k,
        weak_kinds=weak_kinds,
        weak_positions=weak_positions,
    )


def compute_weakness_bundle(
    db_path: Path,
    *,
    recent_n: int = 20,
    recent_min_attempts: int = 5,
    recent_top_k: int = 3,
    all_min_attempts: int = 10,
    all_top_k: int = 5,
) -> dict[str, WeaknessReport]:
    return {
        "recent": compute_weakness_report(
            db_path,
            scope="recent",
            recent_n=recent_n,
            min_attempts=recent_min_attempts,
            top_k=recent_top_k,
        ),
        "all": compute_weakness_report(
            db_path,
            scope="all",
            min_attempts=all_min_attempts,
            top_k=all_top_k,
        ),
    }
