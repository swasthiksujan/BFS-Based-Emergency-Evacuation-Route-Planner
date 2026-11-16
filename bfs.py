"""
Breadth-First Search (BFS) pathfinding algorithm and path reconstruction
for 2D grid evacuation planning.
"""

from collections import deque
from constants import WALL


def bfs(start, exits, grid):
    rows = len(grid)
    cols = len(grid[0])

    # Four directions: up, down, left, right
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    # BFS data structures
    queue   = deque()
    visited = set()
    parent  = {}            # parent[cell] = cell that first reached it

    # Seed the BFS from the starting position
    queue.append(start)
    visited.add(start)
    parent[start] = None

    explored   = []         # list used by the animation
    found_exit = None

    # Main BFS loop
    while queue:
        current = queue.popleft()

        if current in exits:
            found_exit = current
            break

        # Inspect the four neighbours
        for dr, dc in directions:
            nr = current[0] + dr
            nc = current[1] + dc
            neighbour = (nr, nc)

            if nr < 0 or nr >= rows or nc < 0 or nc >= cols:
                continue
            if grid[nr][nc] == WALL:
                continue
            if neighbour in visited:
                continue

            visited.add(neighbour)
            parent[neighbour] = current
            queue.append(neighbour)

            if neighbour != start:
                explored.append(neighbour)

    # Reconstruct the shortest path
    path = reconstruct_path(parent, found_exit)
    return explored, path


def reconstruct_path(parent, exit_cell):
    if exit_cell is None:
        return []

    path    = []
    current = exit_cell
    while current is not None:
        path.append(current)
        current = parent[current]

    path.reverse()
    return path
