"""Grid dimensions, cell states, and workflow stages for Smart Evac."""

GRID_ROWS = 20
GRID_COLS = 20

EMPTY = 0
WALL = 1
EXIT = 2
START = 3
VISITED = 4
PATH = 5

STAGE_WALLS = 1
STAGE_EXITS = 2
STAGE_START = 3
STAGE_RUNNING = 4
STAGE_DONE = 5
