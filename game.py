"""Random-level maze game where BFS-controlled seekers pursue the player."""

from copy import deepcopy
import random

from bfs import bfs
from constants import FLOOR, WALL

ROWS = 17
COLS = 21
PLAYER_START = (1, 1)
SEEKER_STARTS = ((1, 19), (15, 1), (15, 19))
DIRECTIONS = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}


def build_maze():
    """Generate a connected, randomized maze with a few extra loops."""
    grid = [[WALL for _ in range(COLS)] for _ in range(ROWS)]
    start = PLAYER_START
    grid[start[0]][start[1]] = FLOOR
    stack = [start]

    while stack:
        row, col = stack[-1]
        neighbors = [(row + dr, col + dc, dr, dc) for dr, dc in ((-2, 0), (2, 0), (0, -2), (0, 2))
                     if 1 <= row + dr < ROWS - 1 and 1 <= col + dc < COLS - 1
                     and grid[row + dr][col + dc] == WALL]
        if not neighbors:
            stack.pop()
            continue
        nr, nc, dr, dc = random.choice(neighbors)
        grid[row + dr // 2][col + dc // 2] = FLOOR
        grid[nr][nc] = FLOOR
        stack.append((nr, nc))

    # Open a few walls between adjacent corridors so the maze has alternate routes.
    for row in range(1, ROWS - 1):
        for col in range(1, COLS - 1):
            if grid[row][col] != WALL:
                continue
            vertical = grid[row - 1][col] == FLOOR and grid[row + 1][col] == FLOOR
            horizontal = grid[row][col - 1] == FLOOR and grid[row][col + 1] == FLOOR
            if (vertical or horizontal) and random.random() < 0.52:
                grid[row][col] = FLOOR

    # Give the player and seekers a small open area at each spawn point.
    for center_row, center_col in (PLAYER_START, *SEEKER_STARTS):
        for row in range(max(1, center_row - 1), min(ROWS - 1, center_row + 2)):
            for col in range(max(1, center_col - 1), min(COLS - 1, center_col + 2)):
                grid[row][col] = FLOOR
    return grid


class NodeRun:
    """Game state, randomized levels, collectibles, and BFS pursuit."""

    def __init__(self):
        self.score = 0
        self.collected = 0
        self.tick = 0
        self.level = 1
        self.status = "playing"
        self.reset()

    def reset(self):
        self.score = 0
        self.collected = 0
        self.tick = 0
        self.level = 1
        self.status = "playing"
        self.start_level("New maze generated. Every corridor has a dot. Avoid the BFS seekers.")
        return self.snapshot()

    def start_level(self, message):
        self.grid = build_maze()
        self.open_cells = [(row, col) for row in range(1, ROWS - 1)
                           for col in range(1, COLS - 1) if self.grid[row][col] == FLOOR]
        self.player = PLAYER_START
        self.direction = None
        self.seekers = list(SEEKER_STARTS)
        available = set(self.open_cells) - {self.player, *self.seekers}
        self.pulses = set(random.sample(sorted(available), min(4, len(available))))
        self.pellets = available - self.pulses
        self.power_turns = 0
        self.last_paths = [[] for _ in self.seekers]
        self.last_explored = [0 for _ in self.seekers]
        self.last_discovered = [[] for _ in self.seekers]
        self.last_traces = [[] for _ in self.seekers]
        self.message = message

    def snapshot(self):
        return {
            "grid": deepcopy(self.grid),
            "rows": ROWS,
            "cols": COLS,
            "player": list(self.player),
            "direction": self.direction,
            "seekers": [list(cell) for cell in self.seekers],
            "pellets": [list(cell) for cell in sorted(self.pellets)],
            "pulses": [list(cell) for cell in sorted(self.pulses)],
            "score": self.score,
            "collected": self.collected,
            "tick": self.tick,
            "level": self.level,
            "remaining": len(self.pellets) + len(self.pulses),
            "status": self.status,
            "message": self.message,
            "paths": deepcopy(self.last_paths),
            "explored": list(self.last_explored),
            "discovered": deepcopy(self.last_discovered),
            "traces": deepcopy(self.last_traces),
            "powerTurns": self.power_turns,
            "algorithm": "Breadth-First Search",
        }

    def move(self, requested_direction=None):
        if self.status != "playing" or requested_direction not in DIRECTIONS:
            return self.snapshot()
        self.direction = requested_direction
        dr, dc = DIRECTIONS[requested_direction]
        next_player = (self.player[0] + dr, self.player[1] + dc)
        if self.grid[next_player[0]][next_player[1]] == WALL:
            self.message = "Wall ahead. Choose another direction."
            return self.snapshot()

        self.player = next_player
        self.tick += 1
        if self.player in self.seekers:
            self.status = "caught"
            self.message = "A seeker caught you. Restart and try another route."
            return self.snapshot()

        collected_pellet = self.player in self.pellets
        collected_pulse = self.player in self.pulses
        if collected_pellet:
            self.pellets.remove(self.player)
            self.score += 10
            self.collected += 1
            self.message = "Dot collected! Clear the maze to reveal the next random level."
        if collected_pulse:
            self.pulses.remove(self.player)
            self.score += 50
            self.collected += 1
            self.power_turns = 5
            self.message = "Pulse collected! Seekers frozen for 4 moves."

        self.last_paths = []
        self.last_explored = []
        self.last_discovered = []
        self.last_traces = []
        next_seekers = []
        for seeker in self.seekers:
            explored, path, trace = bfs(seeker, {self.player}, self.grid, include_trace=True)
            self.last_explored.append(len(explored))
            self.last_discovered.append([list(cell) for cell in explored])
            self.last_traces.append(trace)
            self.last_paths.append([list(cell) for cell in path])
            next_seekers.append(path[1] if len(path) > 1 else seeker)

        seekers_reset = False
        if self.power_turns:
            self.power_turns -= 1
        else:
            previous_seekers = self.seekers
            self.seekers = next_seekers
            for _ in range(len(self.seekers)):
                groups = {}
                for index, position in enumerate(self.seekers):
                    groups.setdefault(position, []).append(index)
                overlaps = [group for group in groups.values() if len(group) > 1]
                if not overlaps:
                    break
                for group in overlaps:
                    # Keep a seeker already at its own spawn, otherwise keep
                    # one that held its position. Only the merged seekers reset.
                    home = [i for i in group if self.seekers[i] == SEEKER_STARTS[i]]
                    stationary = [i for i in group if next_seekers[i] == previous_seekers[i]]
                    keeper = (home or stationary or group)[0]
                    for index in group:
                        if index == keeper:
                            continue
                        self.seekers[index] = SEEKER_STARTS[index]
                        self.last_paths[index] = []
                        self.last_explored[index] = 0
                        seekers_reset = True
            if seekers_reset:
                self.message = "A merged seeker reset to its spawn point."
            if self.player in self.seekers:
                self.status = "caught"
                self.message = "A seeker found your position using BFS. Restart and try another route."

        if self.status == "playing" and not self.pellets and not self.pulses:
            self.level += 1
            self.start_level(f"Level {self.level}: new random maze. Keep moving!")
        elif self.status == "playing" and not collected_pellet and not collected_pulse and not seekers_reset:
            self.message = "Seekers recalculate shortest paths after every move."
        return self.snapshot()


game = NodeRun()
