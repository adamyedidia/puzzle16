import heapq
import math
from typing import List, Tuple, Optional

class SlidingPuzzleAStar:
    """
    A solver for an N x N sliding-tile puzzle using A* with summed Manhattan distance.
    """
    def __init__(self, initial_state: List[int], size: int, max_expansions: int = 100000):
        """
        :param initial_state: Flattened puzzle as a list of length N*N, with `0` for the blank.
        :param size: N (e.g., 4 for a 4x4 puzzle).
        :param max_expansions: Maximum expansions before early stopping.
        """
        self.size = size
        self.initial_state = tuple(initial_state)
        self.goal_state = tuple(range(1, size * size)) + (0,)
        self.max_expansions = max_expansions

    def solve(self) -> Tuple[List[Tuple[int]], bool]:
        print(f"Starting A* for {self.size}x{self.size}, initial f = {self.heuristic(self.initial_state)}")

        if self.initial_state == self.goal_state:
            return ([self.initial_state], True)

        open_list = []
        heapq.heapify(open_list)

        # g-scores and came_from logic as before
        g_scores = {self.initial_state: 0}
        came_from = {}
        f_initial = self.heuristic(self.initial_state)

        # (f, g, state, parent_state)
        heapq.heappush(open_list, (f_initial, 0, self.initial_state, None))

        expansions = 0

        # Two "best" trackers:
        best_f_node_so_far = (f_initial, 0, self.initial_state, None)
        # For best_h_node_so_far, store a tuple: (h_value, g, state, parent_state)
        h_initial = self.heuristic(self.initial_state)
        best_h_node_so_far = (h_initial, 0, self.initial_state, None)

        while open_list:
            f_current, g_current, current_state, parent_state = heapq.heappop(open_list)

            if expansions % 1000 == 0:
                print(f"Expansions: {expansions}, f_current={f_current}, h_current={self.heuristic(current_state)}")

            # Update best f
            if f_current < best_f_node_so_far[0]:
                best_f_node_so_far = (f_current, g_current, current_state, parent_state)

            # Update best h
            h_current = self.heuristic(current_state)
            if h_current < best_h_node_so_far[0]:
                best_h_node_so_far = (h_current, g_current, current_state, parent_state)

            # Early stop?
            if expansions >= self.max_expansions:
                print(f"Reached max expansions = {self.max_expansions}, stopping early")

                # Option A: Return partial path that is best by f
                # partial_path = self._reconstruct_partial_path(best_f_node_so_far, came_from)
                
                # Option B: Return partial path that is best by h
                partial_path = self._reconstruct_partial_path(best_h_node_so_far, came_from)

                return partial_path, False

            expansions += 1

            # Record parent if needed
            if parent_state is not None and current_state not in came_from:
                came_from[current_state] = parent_state

            # Goal check
            if current_state == self.goal_state:
                print(f"Solution found after {expansions} expansions")
                return (self._reconstruct_path(current_state, came_from), True)

            # Expand neighbors
            for next_state in self.get_neighbors(current_state):
                g_next = g_current + 1
                if next_state not in g_scores or g_next < g_scores[next_state]:
                    g_scores[next_state] = g_next
                    f_next = g_next + self.heuristic(next_state)
                    heapq.heappush(open_list, (f_next, g_next, next_state, current_state))

        # If we exhaust open_list with no solution:
        print("Search exhausted, no solution found (shouldn't happen if solvable).")
        partial_path = self._reconstruct_partial_path(best_h_node_so_far, came_from)
        return partial_path, False


    def get_neighbors(self, state: Tuple[int]) -> List[Tuple[int]]:
        """
        Return all valid neighbor states by sliding one tile adjacent to the blank.
        """
        neighbors = []
        size = self.size

        # print("State: ", state)
        blank_index = state.index(0)
        blank_row = blank_index // size
        blank_col = blank_index % size

        # Potential moves: up, down, left, right (if in-bounds)
        moves = []
        if blank_row > 0:
            moves.append((-1, 0))  # up
        if blank_row < size - 1:
            moves.append((1, 0))   # down
        if blank_col > 0:
            moves.append((0, -1))  # left
        if blank_col < size - 1:
            moves.append((0, 1))   # right

        for dr, dc in moves:
            new_row = blank_row + dr
            new_col = blank_col + dc
            new_index = new_row * size + new_col
            # Swap blank and the tile in new_index
            neighbor_list = list(state)
            neighbor_list[blank_index], neighbor_list[new_index] = \
                neighbor_list[new_index], neighbor_list[blank_index]
            neighbors.append(tuple(neighbor_list))

        return neighbors

    def heuristic(self, state: Tuple[int]) -> int:
        """
        Summed Manhattan distance of each tile from its goal position.
        
        For tile x (1..N*N-1), its solved location is (row, col) = divmod(x-1, size).
        The blank (0) is not counted.
        """
        size = self.size
        distance_sum = 0
        for index, tile in enumerate(state):
            if tile != 0:
                # Current position
                row = index // size
                col = index % size
                # Goal position
                goal_row = (tile - 1) // size
                goal_col = (tile - 1) % size
                distance_sum += abs(row - goal_row) + abs(col - goal_col)
        return distance_sum

    def _reconstruct_path(self, end_state: Tuple[int], came_from: dict) -> List[Tuple[int]]:
        """
        Reconstruct a full path from the final (goal) state back to the initial state.
        """
        path = [end_state]
        while end_state in came_from:
            end_state = came_from[end_state]
            path.append(end_state)
        path.reverse()
        return path

    def _reconstruct_partial_path(self, node: Tuple[int, int, Tuple[int], Optional[Tuple[int]]], came_from: dict) -> List[Tuple[int]]:
        """
        Reconstruct from the best node so far (which might not be the goal).
        Node is (f_val, g_val, state, parent_state).
        """
        _, _, state, _ = node
        return self._reconstruct_path(state, came_from)


# ------------------------------------------------------------------------------
# Example usage (if you want to run this script directly):
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    # Example: A 3x3 puzzle scrambled
    # We represent the puzzle in row-major order:
    # [1, 2, 3,
    #  4, 6, 0,
    #  7, 5, 8]
    # 0 is the blank/hole.
    # The solved configuration for 3x3 is: [1,2,3,4,5,6,7,8,0].
    
    initial = [
        1, 2, 3,
        4, 6, 0,
        7, 5, 8
    ]
    size = 3
    
    # Create solver with a modest expansion limit for demonstration
    solver = SlidingPuzzleAStar(initial_state=initial, size=size, max_expansions=1000)
    path, solved = solver.solve()
    
    print(f"Solved? {solved}")
    print(f"Number of states in path: {len(path)}")
    print("Solution/Partial path states:")
    for idx, st in enumerate(path):
        print(f"Step {idx}: {st}")
        
    # If solved == False, then we didn't get to the actual goal within max_expansions;
    # the final path step is just the best (lowest f) node we saw so far.