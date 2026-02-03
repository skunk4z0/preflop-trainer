# main.py
from __future__ import annotations

import logging
import tkinter as tk

import openpyxl

from controller import GameController
from core.engine import PokerEngine
from core.generator import JuegoProblemGenerator
from juego_judge import JUEGOJudge
from excel_range_repository import ExcelRangeRepository
from ui import PokerTrainerUI

from config import (
    EXCEL_PATH,
    SHEET_NAME,
    AA_SEARCH_RANGES,
    GRID_TOPLEFT_OFFSET,
    REF_COLOR_CELLS,
)


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    # ---- Data access (Workbook -> Repo) ----
    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    repo = ExcelRangeRepository(
        wb=wb,
        sheet_name=SHEET_NAME,
        aa_search_ranges=AA_SEARCH_RANGES,
        grid_topleft_offset=GRID_TOPLEFT_OFFSET,
        ref_color_cells=REF_COLOR_CELLS,
        enable_debug=False,
    )

    # ---- Judge ----
    judge = JUEGOJudge(repo)

    # ---- Generator ----
    positions_3bet = repo.list_positions("3BET")
    generator = JuegoProblemGenerator(positions_3bet=positions_3bet)


    # ---- Core Engine ----
    engine = PokerEngine(generator=generator, juego_judge=judge, enable_debug=False)

    # ---- UI ----
    root = tk.Tk()
    ui = PokerTrainerUI(root)
    controller = GameController(ui=ui, engine=engine, enable_debug=False)

    # UIが controller を呼ぶ設計なら attach
    ui.controller = controller

    root.mainloop()


if __name__ == "__main__":
    main()
