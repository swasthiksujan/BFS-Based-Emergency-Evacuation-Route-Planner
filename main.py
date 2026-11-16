"""
SMART EVAC | Emergency Route Planner
Main application entry point.
"""

import customtkinter as ctk

from constants import (
    GRID_ROWS,
    GRID_COLS,
    CELL_SIZE,
    GRID_PADDING,
)
from ui import SmartEvac


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("green")

    root = ctk.CTk()

    # Calculate window size from grid dimensions
    canvas_w = GRID_COLS * CELL_SIZE + 2 * GRID_PADDING
    canvas_h = GRID_ROWS * CELL_SIZE + 2 * GRID_PADDING
    win_w    = canvas_w + 272 + 8 * 3 + 16 + 20   # canvas + panel + margins
    win_h    = canvas_h + 8 * 2 + 16 + 20          # canvas + margins

    # Centre on screen
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f"{win_w}x{win_h}+{(sw - win_w) // 2}+{(sh - win_h) // 2}")

    SmartEvac(root)
    root.mainloop()


if __name__ == "__main__":
    main()
