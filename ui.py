"""Flask web interface and application state for Smart Evac."""

from copy import deepcopy

from flask import Flask, jsonify, render_template, request

from bfs import bfs
from constants import (
    EMPTY, EXIT, GRID_COLS, GRID_ROWS, PATH, STAGE_DONE, STAGE_EXITS,
    STAGE_RUNNING, STAGE_START, STAGE_WALLS, START, VISITED, WALL,
)

app = Flask(__name__)


def fresh_state():
    return {
        "grid": [[EMPTY] * GRID_COLS for _ in range(GRID_ROWS)],
        "stage": STAGE_WALLS,
        "exits": [],
        "start": None,
        "result": "Awaiting simulation…",
        "resultType": "muted",
        "speed": "Normal",
        "explored": [],
        "path": [],
    }


state = fresh_state()


def snapshot():
    return deepcopy(state)


def cell_from(data):
    try:
        row, col = int(data["row"]), int(data["col"])
    except (KeyError, TypeError, ValueError):
        return None
    if 0 <= row < GRID_ROWS and 0 <= col < GRID_COLS:
        return row, col
    return None


@app.get("/")
def index():
    return render_template("index.html", rows=GRID_ROWS, cols=GRID_COLS)


@app.get("/api/state")
def get_state():
    return jsonify(snapshot())


@app.post("/api/cell")
def edit_cell():
    cell = cell_from(request.json or {})
    if cell is None:
        return jsonify(error="Invalid grid cell."), 400
    if state["stage"] in (STAGE_RUNNING, STAGE_DONE):
        return jsonify(snapshot())
    row, col = cell
    value = state["grid"][row][col]
    stage = state["stage"]
    if stage == STAGE_WALLS:
        action = (request.json or {}).get("action")
        if action == "place" and value == EMPTY:
            state["grid"][row][col] = WALL
        elif action == "erase" and value == WALL:
            state["grid"][row][col] = EMPTY
        elif action not in ("place", "erase"):
            state["grid"][row][col] = EMPTY if value == WALL else WALL if value == EMPTY else value
    elif stage == STAGE_EXITS:
        if value == WALL:
            state["result"], state["resultType"] = "Cannot place an exit on a wall.", "warning"
        elif value == EXIT:
            state["exits"].remove([row, col])
            state["grid"][row][col] = EMPTY
        else:
            state["exits"].append([row, col])
            state["grid"][row][col] = EXIT
    elif stage == STAGE_START:
        if value == WALL:
            state["result"], state["resultType"] = "Cannot start on a wall.", "warning"
        elif value == EXIT:
            state["result"], state["resultType"] = "Cannot start on an exit.", "warning"
        else:
            if state["start"]:
                sr, sc = state["start"]
                state["grid"][sr][sc] = EMPTY
            state["start"] = [row, col]
            state["grid"][row][col] = START
    return jsonify(snapshot())


@app.post("/api/navigate")
def navigate():
    action = (request.json or {}).get("action")
    if action == "next":
        if state["stage"] == STAGE_WALLS:
            state["stage"] = STAGE_EXITS
        elif state["stage"] == STAGE_EXITS:
            if not state["exits"]:
                state["result"], state["resultType"] = "Place at least one emergency exit first.", "warning"
            else:
                state["stage"] = STAGE_START
    elif action == "back":
        if state["stage"] == STAGE_EXITS:
            state["stage"] = STAGE_WALLS
        elif state["stage"] == STAGE_START:
            state["stage"] = STAGE_EXITS
    return jsonify(snapshot())


@app.post("/api/speed")
def set_speed():
    speed = (request.json or {}).get("speed")
    if speed in ("Slow", "Normal", "Fast"):
        state["speed"] = speed
    return jsonify(snapshot())


@app.post("/api/start")
def start_simulation():
    if not state["exits"]:
        state["result"], state["resultType"] = "No emergency exits placed.", "warning"
    elif state["start"] is None:
        state["result"], state["resultType"] = "No starting position set.", "warning"
    else:
        state["stage"] = STAGE_RUNNING
        state["result"], state["resultType"] = "BFS in progress…", "active"
        state["explored"], state["path"] = bfs(tuple(state["start"]), {tuple(cell) for cell in state["exits"]}, state["grid"])
        state["explored"] = [list(cell) for cell in state["explored"]]
        state["path"] = [list(cell) for cell in state["path"]]
    return jsonify(snapshot())


@app.post("/api/finish")
def finish_simulation():
    if state["stage"] != STAGE_RUNNING:
        return jsonify(snapshot())
    grid, path, explored = state["grid"], state["path"], state["explored"]
    for row, col in explored:
        if grid[row][col] not in (START, EXIT):
            grid[row][col] = VISITED
    if path:
        for row, col in path:
            if grid[row][col] not in (START, EXIT):
                grid[row][col] = PATH
        count = sum(cell in (VISITED, PATH, EXIT) for line in grid for cell in line)
        state["result"] = (f"EVACUATION ROUTE FOUND!\nNearest exit: {tuple(path[-1])}\n"
                           f"Path length: {len(path) - 1} step(s)\nCells explored: {count}")
        state["resultType"] = "success"
    else:
        state["result"] = f"NO ACCESSIBLE EXIT FOUND\n\nCells explored: {len(explored)}"
        state["resultType"] = "error"
    state["stage"] = STAGE_DONE
    return jsonify(snapshot())


@app.post("/api/reset")
def reset_simulation():
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            if state["grid"][row][col] in (VISITED, PATH):
                state["grid"][row][col] = EMPTY
    for row, col in state["exits"]:
        state["grid"][row][col] = EXIT
    if state["start"]:
        row, col = state["start"]
        state["grid"][row][col] = START
    state.update(stage=STAGE_START, result="Reset done — ready to simulate again.",
                 resultType="muted", explored=[], path=[])
    return jsonify(snapshot())


@app.post("/api/clear")
def clear_all():
    state.clear()
    state.update(fresh_state())
    return jsonify(snapshot())
