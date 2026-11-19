# Node Run

Node Run is a browser maze game built around the project's breadth-first search implementation. Guide the player around randomized mazes and avoid three seekers that use BFS to find a shortest path toward the player. Each arrow or WASD press moves one tile, so you choose every move. Seekers recalculate after every step. Every walkable tile starts with a dot; clear the maze to generate a new random level. Purple pulse dots freeze the seekers for four moves.

The run screen includes an optional BFS trace. After a move, open **Inside the search** to inspect one seeker's actual expanded-cell order, queue frontier, shortest path, and route distance. The **Search step** control moves through the backend-recorded expansion sequence. Sound is off until enabled and uses simple synthesized tones, with no external audio assets.

## Run locally

```bash
python -m pip install -r requirements.txt
python main.py
```

Open <http://127.0.0.1:5000> in a browser. Steer with the arrow keys or WASD; the on-screen directional pad also works on touch devices. The game engine and pathfinding run in Python through Flask, while the browser handles the board display and input.
