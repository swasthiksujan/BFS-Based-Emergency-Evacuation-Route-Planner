"""
Configuration settings, grid dimensions, cell states, colors, and static labels
for the Smart Evac emergency route planner application.
"""

# Grid Configuration
GRID_ROWS    = 20
GRID_COLS    = 20
CELL_SIZE    = 34        # pixels per grid cell
GRID_PADDING = 10        # canvas padding around the grid

# Cell State Constants
EMPTY   = 0
WALL    = 1
EXIT    = 2
START   = 3
VISITED = 4
PATH    = 5

# Color Palette
COLOUR = {
    EMPTY:   "#303030",
    WALL:    "#555555",
    EXIT:    "#00C853",
    START:   "#2979FF",
    VISITED: "#F9A825",
    PATH:    "#00BCD4",
}
GRID_LINE_COLOUR = "#444444"
CANVAS_BG        = "#1a1a1a"
PANEL_BG         = "#1e1e1e"

# BFS animation speeds (milliseconds between each step)
SPEED_OPTIONS = {"Slow": 150, "Normal": 60, "Fast": 15}

# Workflow Stages
STAGE_WALLS   = 1   # user is drawing walls
STAGE_EXITS   = 2   # user is placing exits
STAGE_START   = 3   # user is placing start position
STAGE_RUNNING = 4   # BFS animation is active
STAGE_DONE    = 5   # simulation finished

# Step Information & Guidance
STEP_INFO = {
    STAGE_WALLS: (
        "STEP 1 of 3 — Draw Walls",
        "Click to place/remove walls.\n"
        "Click-and-drag to draw quickly.",
    ),
    STAGE_EXITS: (
        "STEP 2 of 3 — Place Exits",
        "Click empty cells to add exits (green).\n"
        "Click an exit again to remove it.",
    ),
    STAGE_START: (
        "STEP 3 of 3 — Set Start Position",
        "Click an empty cell to place\n"
        "the person's starting point (blue).",
    ),
    STAGE_RUNNING: (
        "Simulation Running…",
        "BFS is exploring the building.\nPlease wait.",
    ),
    STAGE_DONE: (
        "Simulation Complete",
        "Reset to run again or\nClear All to start over.",
    ),
}
