import heapq
import math
from collections import deque
from typing import List, Tuple, Optional

class SlidingPuzzleAStar:
    """
    A solver for an N x N sliding-tile puzzle using A* with:
      - Summed Manhattan distance as the baseline heuristic
      - Father’s rule to raise h(s) if neighbors are all bigger
      - Bubble-up mechanism to propagate changes
      - Partial progress measured by "lowest h so far"
    """
    def __init__(self, initial_state: List[int], size: int, max_expansions: int = 100000):
        """
        :param initial_state: Flattened puzzle as a list of length N*N, with 0 for the blank.
        :param size: N (e.g., 4 for a 4x4 puzzle).
        :param max_expansions: Maximum expansions before early stopping.
        """
        self.size = size
        self.initial_state = tuple(initial_state)
        self.goal_state = tuple(range(1, size * size)) + (0,)
        self.max_expansions = max_expansions

        # We'll store heuristics in a dictionary. Start with Manhattan distances.
        self.h_dict = {}  # state -> current heuristic value

    def solve(self) -> Tuple[List[Tuple[int]], bool]:
        """
        Attempt to solve the puzzle using A* with father's rule + bubble-up + partial progress by h.

        :return: (path, solved_flag)
          path is a list of states from initial to best-h (or goal).
          If `solved_flag` is True, found a complete solution.
          If `solved_flag` is False, partial path to lowest-h node.
        """
        print(f"Starting A* FathersRule for {self.size}x{self.size}")
        if self.initial_state == self.goal_state:
            return ([self.initial_state], True)

        open_list = []  # Each entry: (f, g, state, parent)
        heapq.heapify(open_list)

        came_from = {}  # For path reconstruction
        g_scores = {}   # State -> best g found so far

        # Initialize
        init_h = self.heuristic(self.initial_state)
        self.h_dict[self.initial_state] = init_h
        f_init = init_h  # g=0 + h=init_h
        g_scores[self.initial_state] = 0

        heapq.heappush(open_list, (f_init, 0, self.initial_state, None))

        expansions = 0

        # We'll track best-by-h node. Store as (h_value, g_value, state, parent).
        best_h_node_so_far = (init_h, 0, self.initial_state, None)

        while open_list:
            # Pop lowest f
            f_current, g_current, current_state, parent_state = heapq.heappop(open_list)

            # Possibly record parent
            if parent_state is not None and current_state not in came_from:
                came_from[current_state] = parent_state

            # Update best-by-h node
            cur_h = self.h_dict[current_state]
            if cur_h < best_h_node_so_far[0]:
                best_h_node_so_far = (cur_h, g_current, current_state, parent_state)

            if expansions % 1000 == 0:
                print(f"Expansions: {expansions}, f_current={f_current}, h_current={cur_h}")

            # Early stop?
            if expansions >= self.max_expansions:
                print(f"Reached max expansions = {self.max_expansions}, stopping early")
                partial_path = self._reconstruct_partial_path(best_h_node_so_far, came_from)
                return partial_path, False

            expansions += 1

            # Goal check
            if current_state == self.goal_state:
                print(f"Solved after {expansions} expansions!")
                full_path = self._reconstruct_path(current_state, came_from)
                return full_path, True

            # Expand neighbors
            for nbr in self.get_neighbors(current_state):
                if nbr not in self.h_dict:
                    self.h_dict[nbr] = self.baseline_manhattan(nbr)

                g_next = g_current + 1
                if (nbr not in g_scores) or (g_next < g_scores[nbr]):
                    g_scores[nbr] = g_next
                    f_next = g_next + self.h_dict[nbr]
                    heapq.heappush(open_list, (f_next, g_next, nbr, current_state))

            # Father’s rule + bubble-up for current_state
            self.apply_fathers_rule_bubble_up(current_state)

            # Because we might have changed h(current_state), reinsert it if needed
            new_h = self.h_dict[current_state]
            new_f = g_current + new_h
            if new_f > f_current:
                # That means we raised h(current_state). Re-queue with updated f.
                heapq.heappush(open_list, (new_f, g_current, current_state, parent_state))

        # If we empty open_list, no solution found (unlikely if puzzle is solvable).
        print("Search ended with an empty open_list. No solution found or partial only.")
        partial_path = self._reconstruct_partial_path(best_h_node_so_far, came_from)
        return partial_path, False

    def apply_fathers_rule_bubble_up(self, s: Tuple[int]):
        """
        Apply father's rule to s, then bubble up changes to neighbors if needed.
        We'll keep a queue of states that might need re-checking.
        """
        queue = deque([s])
        visited = set()

        while queue:
            state = queue.popleft()
            if state in visited:
                continue
            visited.add(state)

            # Possibly apply father’s rule to 'state'
            old_h = self.h_dict[state]
            changed = self.fathers_rule_once(state)
            new_h = self.h_dict[state]

            # If we raised h(state), neighbors may need to raise their h as well.
            if changed:
                # Add neighbors to queue for re-check
                for nbr in self.get_neighbors(state):
                    if nbr in self.h_dict:
                        queue.append(nbr)

    def fathers_rule_once(self, s: Tuple[int]) -> bool:
        """
        Apply father’s rule a single time to state s:
          If all neighbors have h >= h(s)+1, then raise h(s) to (min_h_nbr + 1).
        Return True if h(s) was changed, False otherwise.
        """
        h_s = self.h_dict[s]
        nbrs = self.get_neighbors(s)

        if not nbrs:
            return False  # no neighbors? shouldn't happen, but safe

        # Check if all neighbors have h(nbr) >= h_s + 1
        min_h_nbr = math.inf
        all_bigger = True
        for nbr in nbrs:
            h_n = self.h_dict.get(nbr, self.baseline_manhattan(nbr))
            if h_n < h_s + 1:
                all_bigger = False
            if h_n < min_h_nbr:
                min_h_nbr = h_n

        if all_bigger:
            # Raise h(s) to min_h_nbr + 1
            old_val = self.h_dict[s]
            new_val = min_h_nbr + 1
            if new_val > old_val:
                self.h_dict[s] = new_val
                # Debug print if you like
                # print(f"FATHER'S RULE bubble-up: raise h({s}) from {old_val} to {new_val}.")
                return True

        return False

    def get_neighbors(self, state: Tuple[int]) -> List[Tuple[int]]:
        """
        Return all valid neighbor states by sliding one tile adjacent to the blank.
        """
        neighbors = []
        size = self.size
        blank_index = state.index(0)
        r, c = divmod(blank_index, size)

        # Up, down, left, right
        if r > 0:
            neighbors.append(self.swap(state, blank_index, blank_index - size))
        if r < size - 1:
            neighbors.append(self.swap(state, blank_index, blank_index + size))
        if c > 0:
            neighbors.append(self.swap(state, blank_index, blank_index - 1))
        if c < size - 1:
            neighbors.append(self.swap(state, blank_index, blank_index + 1))

        return neighbors

    def swap(self, state: Tuple[int], i: int, j: int) -> Tuple[int]:
        """
        Return a new tuple with positions i and j swapped.
        """
        s_list = list(state)
        s_list[i], s_list[j] = s_list[j], s_list[i]
        return tuple(s_list)

    def heuristic(self, state: Tuple[int]) -> int:
        """
        Our main heuristic accessor. If we already have a stored h, return it.
        Otherwise, compute the baseline manhattan distance.
        """
        if state not in self.h_dict:
            self.h_dict[state] = self.baseline_manhattan(state)
        return self.h_dict[state]

    def baseline_manhattan(self, state: Tuple[int]) -> int:
        """
        Compute the standard summed Manhattan distance for a puzzle state.
        """
        size = self.size
        dist_sum = 0
        for idx, tile in enumerate(state):
            if tile != 0:
                row = idx // size
                col = idx % size
                goal_row = (tile - 1) // size
                goal_col = (tile - 1) % size
                dist_sum += abs(row - goal_row) + abs(col - goal_col)
        return dist_sum

    def _reconstruct_path(self, end_state: Tuple[int], came_from: dict) -> List[Tuple[int]]:
        """
        Reconstruct a full path from the final (goal) state to the initial.
        """
        path = [end_state]
        while end_state in came_from:
            end_state = came_from[end_state]
            path.append(end_state)
        path.reverse()
        return path

    def _reconstruct_partial_path(self, best_h_node: Tuple[int, int, Tuple[int], Optional[Tuple[int]]], came_from: dict) -> List[Tuple[int]]:
        """
        best_h_node is (h_value, g_value, state, parent).
        Return path from initial to that state.
        """
        _, _, state, _ = best_h_node
        return self._reconstruct_path(state, came_from)


# ------------------------------------------------------------------------------
# Example usage (if you want to run this script directly):
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    # Let's do a random 4x4 puzzle, or your puzzle of choice.
    initial_4x4 = [
        15, 10, 0, 11,
        9, 5, 2, 1,
        3, 6, 7, 14,
        4, 13, 8, 12
    ]
    size = 4

    solver = SlidingPuzzleAStarFathersRule(initial_4x4, size, max_expansions=50000)
    path, solved = solver.solve()
    print(f"Solved? {solved}, path length={len(path)}")
    print("Final partial/solution path states:")
    for i, st in enumerate(path):
        print(f"  step {i}: {st}")
