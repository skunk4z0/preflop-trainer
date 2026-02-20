import logging
import os
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


def _init_debug_logging_from_env() -> None:
    level_name = os.getenv("POKER_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    kwargs = {
        "level": level,
        "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
    }
    try:
        logging.basicConfig(force=True, **kwargs)
    except TypeError:
        # Python 3.7 互換: force 非対応でも落とさない
        logging.basicConfig(**kwargs)
    except Exception:
        # ログ初期化失敗で通常起動を妨げない
        pass
    

    logging.getLogger("PIL").setLevel(logging.INFO)
    logging.getLogger("PIL.PngImagePlugin").setLevel(logging.INFO)



def main() -> None:
    _ensure_final_tags_exists()
    _init_debug_logging_from_env()

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
