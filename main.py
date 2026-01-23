# main.py
from __future__ import annotations

import os
import logging
import tkinter as tk

from ui import PokerTrainerUI


if __name__ == "__main__":
    debug = os.environ.get("POKER_DEBUG", "0") not in ("0", "false", "False", "")
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    root = tk.Tk()
    PokerTrainerUI(root)
    root.mainloop()
