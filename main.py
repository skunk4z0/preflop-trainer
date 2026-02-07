import logging
import random
import sys
import tkinter as tk
from pathlib import Path

from config import FINAL_TAGS_JSON_PATH
from controller import GameController
from core.engine import PokerEngine
from core.generator import JuegoProblemGenerator
from juego_judge import JUEGOJudge
from json_range_repository import JsonRangeRepository
from ui import PokerTrainerUI


def _ensure_final_tags_exists() -> None:
    p = Path(FINAL_TAGS_JSON_PATH)
    if not p.exists():
        msg = (
            "[FATAL] final_tags.json not found.\n"
            f"Expected: {p}\n"
            "Run build first:\n"
            "  .\\.venv-build\\Scripts\\python -m tools.build_final_tags_json\n"
        )
        print(msg, file=sys.stderr)
        raise SystemExit(1)


def main() -> None:
    _ensure_final_tags_exists()
    logging.basicConfig(level=logging.INFO)

    # ---- Repo (JSON only) ----
    repo = JsonRangeRepository(FINAL_TAGS_JSON_PATH)

    # ---- Judge ----
    judge = JUEGOJudge(repo)

    # ---- Generator ----
    # NOTE: list_positions の kind 名はあなたのJSON設計に依存
    positions_3bet = repo.list_positions("CC_3BET")
    gen = JuegoProblemGenerator(
        rng=random.Random(),
        positions_3bet=positions_3bet,
    )

    # ---- Core Engine ----
    engine = PokerEngine(generator=gen, juego_judge=judge, enable_debug=False)

    # ---- UI / Controller ----
    root = tk.Tk()
    ui = PokerTrainerUI(root)
    controller = GameController(ui=ui, engine=engine, enable_debug=False)
    ui.controller = controller

    root.mainloop()


if __name__ == "__main__":
    main()
