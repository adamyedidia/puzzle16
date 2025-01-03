import time
import threading
import random
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit

from solver import SlidingPuzzleAStar  # Your A* solver from earlier

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
CORS(app)

# Initialize SocketIO (using eventlet or gevent as async_mode)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global puzzle data
puzzle_state = []  # e.g., a list of length N*N
puzzle_size = 4
is_solving = False
solver_thread = None

num_moves = 0
thinking_time = 0.0

def find_position(tile):
    """Return (row, col) of the given tile in puzzle_state, for the current puzzle_size."""
    idx = puzzle_state.index(tile)
    return divmod(idx, puzzle_size)

def count_inversions(puzzle):
    """
    Count inversions in a 1D puzzle list (excluding 0).
    An inversion is any pair (a, b) such that a appears before b, a > b, and both != 0.
    """
    arr = [x for x in puzzle if x != 0]
    inversions = 0
    for i in range(len(arr)):
        for j in range(i + 1, len(arr)):
            if arr[i] > arr[j]:
                inversions += 1
    return inversions

def is_solvable(puzzle, n):
    """
    Check if an N x N puzzle is solvable.

    Rules for NxN:
      1) If N is odd:
         - The puzzle is solvable if the number of inversions is even.
      2) If N is even:
         - Let 'row_of_blank_from_bottom' = row of the blank, counted from the bottom (1-based).
         - The puzzle is solvable if:
               (row_of_blank_from_bottom is even and number_of_inversions is odd) OR
               (row_of_blank_from_bottom is odd  and number_of_inversions is even)
    """
    inv = count_inversions(puzzle)
    hole_index = puzzle.index(0)
    hole_row_from_top = hole_index // n
    # Convert to 1-based row counting from bottom:
    row_of_blank_from_bottom = n - hole_row_from_top

    if n % 2 == 1:
        # If grid width is odd, then puzzle is solvable if number of inversions is even
        return (inv % 2 == 0)
    else:
        # If grid width is even, puzzle is solvable if:
        # (blank is on even row counting from bottom and inversions is odd) OR
        # (blank is on odd row counting from bottom and inversions is even)
        return (
            (row_of_blank_from_bottom % 2 == 0 and inv % 2 == 1) or
            (row_of_blank_from_bottom % 2 == 1 and inv % 2 == 0)
        )

def generate_solvable_puzzle(n):
    """
    Generate a random, solvable puzzle for an NxN board.
    Puzzle is represented by a list of length n*n with values [1..n*n-1] and 0 for the hole.
    """
    puzzle = list(range(1, n*n)) + [0]
    # Shuffle until solvable
    while True:
        random.shuffle(puzzle)
        if is_solvable(puzzle, n):
            return puzzle

@app.route("/api/puzzle", methods=["GET"])
def get_puzzle():
    """
    Returns JSON:
      {
        "size": <puzzle_size>,
        "puzzle": <list of length size*size>
      }
    """
    return jsonify({
        "size": puzzle_size,
        "puzzle": puzzle_state
    })

@app.route("/api/move", methods=["POST"])
def move_tile():
    """
    Attempt to move a tile given in JSON {"tile": x}.
    Valid if the tile is adjacent to the hole (manhattan distance == 1).
    """
    global puzzle_state
    data = request.get_json()
    tile_to_move = data.get("tile")

    # Basic validation
    if tile_to_move not in puzzle_state or tile_to_move == 0:
        return jsonify({"error": "Invalid tile"}), 400

    # Current positions
    tile_row, tile_col = find_position(tile_to_move)
    hole_row, hole_col = find_position(0)

    global num_moves
    num_moves += 1

    # Check adjacency (Manhattan distance == 1)
    if abs(tile_row - hole_row) + abs(tile_col - hole_col) == 1:
        # Swap the tile with the hole
        tile_idx = puzzle_state.index(tile_to_move)
        hole_idx = puzzle_state.index(0)
        puzzle_state[tile_idx], puzzle_state[hole_idx] = \
            puzzle_state[hole_idx], puzzle_state[tile_idx]

    return jsonify({"size": puzzle_size, "puzzle": puzzle_state, "num_moves": num_moves})

@app.route("/api/new", methods=["POST"])
def new_puzzle():
    """
    Generate a new random solvable puzzle.  
    Expects JSON: {"size": <integer>}  
    Returns puzzle state: {"size": ..., "puzzle": ...}
    """
    global puzzle_state, puzzle_size
    data = request.get_json()
    new_size = data.get("size", 4)

    global num_moves, thinking_time
    num_moves = 0
    thinking_time = 0.0

    # Validate puzzle size
    try:
        new_size = int(new_size)
        if new_size < 2 or new_size > 50:
            # Example constraint: limit max to 50 for performance
            return jsonify({"error": "Size must be between 2 and 50"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid size"}), 400

    # Generate puzzle
    puzzle_size = new_size
    puzzle_state = generate_solvable_puzzle(puzzle_size)

    return jsonify({"size": puzzle_size, "puzzle": puzzle_state})

# ----------------------------------------------------------------------
# AUTO-SOLVE logic
# ----------------------------------------------------------------------

@app.route("/api/auto_solve", methods=["POST"])
def auto_solve():
    global is_solving, solver_thread
    max_expansions = request.get_json().get('max_expansions', 50000)
    use_heuristic_adjustment = request.get_json().get('use_heuristic_adjustment', False)
    if not is_solving:
        is_solving = True
        solver_thread = threading.Thread(target=run_solver, args=(max_expansions, use_heuristic_adjustment))
        solver_thread.start()
    return jsonify({"status": "solver_started"})

@app.route("/api/stop_auto_solve", methods=["POST"])
def stop_auto_solve():
    global is_solving
    is_solving = False
    return jsonify({"status": "solver_stopped"})

@app.route("/api/set_state", methods=["POST"])
def set_state():
    """
    Set puzzle to a specific state.
    Expects JSON: {"puzzle": [list of integers]}
    Returns: {"size": <size>, "puzzle": <new_state>}
    """
    global puzzle_state, puzzle_size
    data = request.get_json()
    new_state = data.get("puzzle")

    global num_moves, thinking_time
    num_moves = 0
    thinking_time = 0.0

    # Validate input
    try:
        # Check that we got a list of integers
        if not isinstance(new_state, list) or not all(isinstance(x, int) for x in new_state):
            return jsonify({"error": "Invalid puzzle format - must be list of integers"}), 400

        # Check length matches current size
        if len(new_state) != puzzle_size * puzzle_size:
            return jsonify({"error": f"Puzzle must be of length {puzzle_size * puzzle_size}"}), 400

        # Check numbers are valid (0 to N²-1)
        valid_numbers = set(range(puzzle_size * puzzle_size))
        if set(new_state) != valid_numbers:
            return jsonify({"error": f"Puzzle must contain exactly numbers 0 to {puzzle_size * puzzle_size - 1}"}), 400

        # Update puzzle state
        puzzle_state = new_state
        return jsonify({"size": puzzle_size, "puzzle": puzzle_state})

    except Exception as e:
        return jsonify({"error": str(e)}), 400    

def run_solver(max_expansions, use_heuristic_adjustment):
    """
    Runs the solver in repeated 'chunks' until puzzle is solved or user stops.
    Each iteration:
      - Build A* from current puzzle_state
      - Solve (partial or full)
      - Step through the returned path, updating puzzle + sending events
      - If partial, loop again from new state
    """
    global is_solving, puzzle_state

    # print("Puzzle state: ", puzzle_state)

    global num_moves, thinking_time

    while is_solving:
        # Snapshot the puzzle state at this moment
        current_state = puzzle_state[:]
        # Create A* solver (set expansions limit as desired)
        
        solver = SlidingPuzzleAStar(
            initial_state=current_state,
            size=puzzle_size,
            max_expansions=max_expansions,
            use_heuristic_adjustment=use_heuristic_adjustment
        )
        # Solve returns (path, solved)
        start_time = time.time()
        path, solved = solver.solve()
        end_time = time.time()
        thinking_time += end_time - start_time

        print("Path: ", path)
        print("Solved: ", solved)

        # 'path' is a list of states from current_state -> best_node (partial or goal)
        if len(path) <= 1 and not use_heuristic_adjustment:
            # No progress possible? We'll break to avoid spinning endlessly
            is_solving = False
            socketio.emit("solver_complete", {"message": "No progress possible (partial or unsolvable)."})
            break

        print("Path: ", path)

        # Step through the path, updating puzzle at each step
        for idx, state in enumerate(path):
            if not is_solving:
                # user or other event asked us to stop
                break

            puzzle_state = list(state)  # update global puzzle

            print("emitting solver update")

            num_moves += 1

            # Emit to client
            socketio.emit("solver_update", {
                "puzzle": puzzle_state,
                "size": puzzle_size,
                "step": idx,
                "total_steps": len(path),
                "num_moves": num_moves,
                "thinking_time": thinking_time,
                "solved": (idx == len(path) - 1 and solved),
            })

            # If this is the final step AND we found an actual solution
            if idx == len(path) - 1 and solved:
                is_solving = False
                socketio.emit("solver_complete", {"message": "Puzzle solved!"})
                break

            # Sleep to visually show the move (0.25s)
            time.sleep(0.25)

        if not is_solving:
            break

        # If we finished stepping through path but didn't solve, that means
        # 'path' was partial. Now puzzle_state = best node so far.
        # We'll loop again, building a new solver from this partial state.

        if solved:
            # If we solved it, exit the outer while
            break

    # Make sure we mark solver as no longer running
    is_solving = False

if __name__ == "__main__":
    app.run(debug=True)
