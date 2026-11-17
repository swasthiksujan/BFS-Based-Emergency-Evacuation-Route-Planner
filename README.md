# Node Run

Node Run is a small browser maze game built around the project's breadth-first search implementation. Guide the player around randomized mazes and avoid three seekers that use BFS to find a shortest path toward the player. Each arrow or WASD press moves one tile, so you choose every move. Seekers recalculate after every step. Every walkable tile starts with a dot; clear the maze to generate a new random level. Purple pulse dots freeze the seekers for four moves.

## Run locally

```bash
python -m pip install -r requirements.txt
python main.py
```

Open <http://127.0.0.1:5000> in a browser. Steer with the arrow keys or WASD; the on-screen directional pad also works on touch devices. The game engine and pathfinding run in Python through Flask, while the browser handles the board display and input.
