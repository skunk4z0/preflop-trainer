from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow direct execution: `python tools/print_stats.py`
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.stats import RateByKey, compute_summary, compute_weakness_bundle


def _fmt_rate(value: float) -> str:
    return f"{value * 100:.1f}%"


def _print_rates(title: str, rows: list[RateByKey]) -> None:
    print(title)
    if rows:
        for item in rows:
            print(
                f"- {item.key}: attempts={item.attempts}, correct={item.correct}, "
                f"accuracy={_fmt_rate(item.accuracy)}"
            )
    else:
        print("- (not enough data)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Print learning stats summary from SQLite.")
    parser.add_argument("--db", type=Path, default=Path("data/learning.db"), help="Path to learning.db")
    parser.add_argument("--summary-recent-n", type=int, default=50, help="Recent N attempts for summary section")
    parser.add_argument("--recent-n", type=int, default=20, help="Recent N attempts for weakness ranking")
    parser.add_argument("--recent-min-attempts", type=int, default=5, help="Min attempts for recent weakness ranking")
    parser.add_argument("--recent-top-k", type=int, default=3, help="Top K recent weakness entries")
    parser.add_argument("--all-min-attempts", type=int, default=10, help="Min attempts for all-time weakness ranking")
    parser.add_argument("--all-top-k", type=int, default=5, help="Top K all-time weakness entries")
    args = parser.parse_args()

    summary = compute_summary(db_path=args.db, recent_n=args.summary_recent_n)
    weakness = compute_weakness_bundle(
        db_path=args.db,
        recent_n=args.recent_n,
        recent_min_attempts=args.recent_min_attempts,
        recent_top_k=args.recent_top_k,
        all_min_attempts=args.all_min_attempts,
        all_top_k=args.all_top_k,
    )
    recent_report = weakness["recent"]
    all_report = weakness["all"]

    print(f"DB: {args.db}")
    print(f"Total attempts: {summary.total_attempts}")
    print(f"Total correct: {summary.total_correct}")
    print(f"Total accuracy: {_fmt_rate(summary.total_accuracy)}")

    print("\nBy kind:")
    if summary.by_kind:
        for item in summary.by_kind:
            print(
                f"- {item.key}: attempts={item.attempts}, correct={item.correct}, "
                f"accuracy={_fmt_rate(item.accuracy)}"
            )
    else:
        print("- (no data)")

    print("\nBy position:")
    if summary.by_position:
        for item in summary.by_position:
            print(
                f"- {item.key}: attempts={item.attempts}, correct={item.correct}, "
                f"accuracy={_fmt_rate(item.accuracy)}"
            )
    else:
        print("- (no data)")

    print("\nRecent:")
    print(
        f"- last {summary.recent.recent_n} attempts: "
        f"count={summary.recent.attempts}, "
        f"correct={summary.recent.correct}, "
        f"accuracy={_fmt_rate(summary.recent.accuracy)}"
    )

    print()
    _print_rates(f"Weak kinds (recent {recent_report.recent_n}):", recent_report.weak_kinds)
    print()
    _print_rates(f"Weak positions (recent {recent_report.recent_n}):", recent_report.weak_positions)
    print()
    _print_rates("Weak kinds (all-time):", all_report.weak_kinds)
    print()
    _print_rates("Weak positions (all-time):", all_report.weak_positions)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
