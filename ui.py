"""Flask routes for the Node Run BFS maze game."""

from flask import Flask, jsonify, render_template, request

from game import game

app = Flask(__name__)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/state")
def get_state():
    return jsonify(game.snapshot())


@app.post("/api/move")
def move():
    direction = (request.json or {}).get("direction")
    return jsonify(game.move(direction))


@app.post("/api/reset")
def reset():
    return jsonify(game.reset())
