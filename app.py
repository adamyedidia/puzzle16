from flask import Flask, jsonify, request
from flask_cors import CORS
import random

app = Flask(__name__)
CORS(app)

# We'll use 0 to represent the empty "hole".
# Our global puzzle_state can be refreshed with a call to /api/new

puzzle_state = list(range(1, 16)) + [0]  # Start with a solved puzzle.

def get_puzzle_as_grid():
    """Return puzzle_state as a 2D list (4x4)."""
    return [puzzle_state[i*4:(i+1)*4] for i in range(4)]

def find_position(tile):
    """Find row, col of the given tile in puzzle_state."""
    idx = puzzle_state.index(tile)
    return divmod(idx, 4)  # (row, col)

def count_inversions(puzzle):
    """
    Count inversions in a 1D list (excluding the 0/hole).
    An inversion is any pair of tiles (a, b) such that a > b but a appears before b.
    """
    arr = [x for x in puzzle if x != 0]
    inversions = 0
    for i in range(len(arr)):
        for j in range(i + 1, len(arr)):
            if arr[i] > arr[j]:
                inversions += 1
    return inversions

def is_solvable(puzzle):
    """
    Check if a 4x4 puzzle is solvable.
    For 4x4:
      - If the grid width is even, puzzle is solvable if:
        (number of inversions + row_of_blank) is odd
      - row_of_blank is counted from the bottom (1-based)
    """
    # Find row of the hole from the *top* (0-based)
    hole_index = puzzle.index(0)
    # Convert to row in 0-based from the top:
    hole_row_from_top = hole_index // 4
    # Convert to row in 1-based from the bottom:
    row_of_blank_from_bottom = 4 - hole_row_from_top

    inv_count = count_inversions(puzzle)
    return (inv_count + row_of_blank_from_bottom) % 2 == 0

def generate_solvable_puzzle():
    """
    Generate a random solvable 4x4 puzzle.
    """
    puzzle = list(range(1, 16)) + [0]
    while True:
        random.shuffle(puzzle)
        if is_solvable(puzzle):
            return puzzle

@app.route("/api/puzzle", methods=["GET"])
def get_puzzle():
    """Return the current puzzle state as JSON."""
    return jsonify({"puzzle": puzzle_state})

@app.route("/api/move", methods=["POST"])
def move_tile():
    """
    Attempt to move a tile (specified in JSON body as {"tile": x}).
    Valid if the tile is adjacent (up, down, left, right) to the hole.
    """
    data = request.get_json()
    tile_to_move = data.get("tile")

    if tile_to_move not in puzzle_state or tile_to_move == 0:
        return jsonify({"error": "Invalid tile"}), 400

    # Find the positions of the tile and the hole
    tile_row, tile_col = find_position(tile_to_move)
    hole_row, hole_col = find_position(0)

    # Check adjacency (Manhattan distance == 1)
    if abs(tile_row - hole_row) + abs(tile_col - hole_col) == 1:
        # Swap the tile with the hole
        tile_idx = puzzle_state.index(tile_to_move)
        hole_idx = puzzle_state.index(0)
        puzzle_state[tile_idx], puzzle_state[hole_idx] = puzzle_state[hole_idx], puzzle_state[tile_idx]

    # Return updated puzzle
    return jsonify({"puzzle": puzzle_state})

@app.route("/api/new", methods=["POST"])
def new_puzzle():
    """
    Generate a new random, solvable puzzle and set puzzle_state accordingly.
    """
    global puzzle_state
    puzzle_state = generate_solvable_puzzle()
    return jsonify({"puzzle": puzzle_state})

if __name__ == "__main__":
    app.run(debug=True)
