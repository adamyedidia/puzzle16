import heapq
import math
from collections import deque
from typing import List, Tuple, Dict, Optional

class SlidingPuzzleAStar:
    """
    A solver for an N x N sliding-tile puzzle using:
      - Father’s rule with multi-pass updates (batched),
      - A "closed" or "expanded" set to avoid re-expanding the same cost,
      - If father's rule raises h(s), we remove s from expanded so we can re-expand it later.
    """

    def __init__(self,
                 initial_state: List[int],
                 size: int,
                 max_expansions: int = 100000,
                 batch_size: int = 50):
        """
        :param initial_state: Flattened puzzle (list of length N*N, with 0 for blank).
        :param size: N (e.g., 4 for a 4x4 puzzle).
        :param max_expansions: Maximum expansions before early stopping.
        :param batch_size: We run father’s rule after every 'batch_size' expansions.
        """
        self.size = size
        self.initial_state = tuple(initial_state)
        self.goal_state = tuple(range(1, size * size)) + (0,)
        self.max_expansions = max_expansions
        self.batch_size = batch_size

        # Heuristic dictionary (h-values)
        self.h_dict: Dict[Tuple[int], int] = {}
        # g-scores
        self.g_scores: Dict[Tuple[int], int] = {}
        # Parent for path reconstruction
        self.came_from: Dict[Tuple[int], Tuple[int]] = {}
        # last_f for "smart re-queue"
        self.last_f: Dict[Tuple[int], int] = {}
        # expanded set (closed set)
        self.expanded = set()

    def solve(self) -> Tuple[List[Tuple[int]], bool]:
        """
        Attempt to solve using a batched father’s rule approach with an expanded set.
        We'll measure partial progress by lowest h so far.
        """
        print(f"[A* FathersRule - BATCHED + CLOSED] size={self.size}, batch_size={self.batch_size}")
        if self.initial_state == self.goal_state:
            return ([self.initial_state], True)

        open_list = []
        heapq.heapify(open_list)

        # Initialize the initial state
        init_h = self.baseline_manhattan(self.initial_state)
        self.h_dict[self.initial_state] = init_h
        self.g_scores[self.initial_state] = 0
        f_init = init_h
        self.last_f[self.initial_state] = f_init

        # Push initial
        heapq.heappush(open_list, (f_init, self.initial_state))

        expansions = 0
        # Track best-by-h node: (h_value, state)
        best_h_node_so_far = (init_h, self.initial_state)
        discovered_states = {self.initial_state}

        while open_list:
            # Pop from the heap
            f_current, current_state = heapq.heappop(open_list)

            # Skip if outdated
            if (current_state not in self.last_f) or (f_current != self.last_f[current_state]):
                continue

            # Skip if already expanded at this cost
            if current_state in self.expanded:
                continue

            g_current = self.g_scores[current_state]
            h_current = self.h_dict[current_state]

            # Mark current as expanded now that we are about to handle it
            self.expanded.add(current_state)

            # Possibly update best-by-h
            if h_current < best_h_node_so_far[0]:
                best_h_node_so_far = (h_current, current_state)

            if expansions % 1000 == 0:
                print(f"Expansions={expansions}, current f={f_current}, h={h_current}")

            # Early stop?
            if expansions >= self.max_expansions:
                print(f"Reached max expansions={self.max_expansions}, stopping early.")
                partial_path = self._reconstruct_path_by_h(best_h_node_so_far[1])
                return partial_path, False

            expansions += 1

            # Goal check
            if current_state == self.goal_state:
                print(f"Solved after {expansions} expansions!")
                final_path = self._reconstruct_path_by_h(current_state)
                return final_path, True

            # Expand neighbors
            for nbr in self.get_neighbors(current_state):
                if nbr not in self.h_dict:
                    self.h_dict[nbr] = self.baseline_manhattan(nbr)
                g_next = g_current + 1
                old_g = self.g_scores.get(nbr, math.inf)
                if g_next < old_g:
                    # We found a cheaper path to neighbor
                    self.g_scores[nbr] = g_next
                    self.came_from[nbr] = current_state
                    f_next = g_next + self.h_dict[nbr]
                    self.update_f(nbr, f_next)
                    heapq.heappush(open_list, (f_next, nbr))
                    discovered_states.add(nbr)

            # Batched father’s rule
            if expansions % self.batch_size == 0:
                self.multi_pass_fathers_rule(discovered_states)
                self.requeue_updated_states(open_list)

        print("[A* FathersRule - BATCHED + CLOSED] open_list empty, partial or no solution.")
        partial_path = self._reconstruct_path_by_h(best_h_node_so_far[1])
        return partial_path, False

    def multi_pass_fathers_rule(self, discovered_states: set):
        """
        Repeatedly apply father’s rule to all discovered states until no more changes.
        If we raise h(s) for any s that was in expanded, we remove it from expanded
        so that it can be re-expanded.
        """
        queue = deque(discovered_states)
        visited = set()

        while queue:
            s = queue.popleft()
            if s in visited:
                continue
            visited.add(s)

            changed = self.fathers_rule_once(s)
            if changed:
                # If s was expanded, remove it so we can re-expand at new cost
                if s in self.expanded:
                    self.expanded.remove(s)
                # Re-check neighbors
                for nbr in self.get_neighbors(s):
                    if nbr in self.h_dict:
                        queue.append(nbr)

    def fathers_rule_once(self, s: Tuple[int]) -> bool:
        """
        Apply father’s rule a single time to s:
          If all neighbors have h(nbr) >= h(s)+1, raise h(s) to (min_h_nbr+1).
        Return True if we actually raised h(s).
        """
        old_h = self.h_dict[s]
        nbrs = self.get_neighbors(s)
        if not nbrs:
            return False

        min_h_nbr = math.inf
        all_bigger = True
        for n in nbrs:
            h_n = self.h_dict.get(n, self.baseline_manhattan(n))
            if h_n < old_h + 1:
                all_bigger = False
            if h_n < min_h_nbr:
                min_h_nbr = h_n

        if all_bigger:
            new_h = min_h_nbr + 1
            if new_h > old_h:
                self.h_dict[s] = new_h
                g_val = self.g_scores[s]
                new_f = g_val + new_h
                self.update_f(s, new_f)
                # Debug example:
                # print(f"Father's rule: Raising h({s}) from {old_h} to {new_h}")
                return True
        return False

    def requeue_updated_states(self, open_list):
        """
        Re-queue any state whose f-value changed. This ensures the open_list sees new priorities.
        """
        for s, g_val in self.g_scores.items():
            new_h = self.h_dict[s]
            new_f = g_val + new_h
            if s not in self.last_f or self.last_f[s] != new_f:
                self.update_f(s, new_f)
                heapq.heappush(open_list, (new_f, s))

    def update_f(self, s: Tuple[int], new_f: int):
        """
        Update self.last_f[s] to new_f.
        """
        self.last_f[s] = new_f

    def get_neighbors(self, state: Tuple[int]) -> List[Tuple[int]]:
        neighbors = []
        size = self.size
        blank_index = state.index(0)
        r, c = divmod(blank_index, size)

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
        arr = list(state)
        arr[i], arr[j] = arr[j], arr[i]
        return tuple(arr)

    def baseline_manhattan(self, state: Tuple[int]) -> int:
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

    def _reconstruct_path_by_h(self, end_state: Tuple[int]) -> List[Tuple[int]]:
        """
        Reconstruct path from initial to end_state via self.came_from.
        """
        path = [end_state]
        while end_state in self.came_from:
            end_state = self.came_from[end_state]
            path.append(end_state)
        path.reverse()
        return path

# ---------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------
if __name__ == "__main__":
    puzzle_4x4 = [
        15, 10, 0, 11,
        9,  5,  2,  1,
        3,  6,  7, 14,
        4, 13, 8, 12
    ]
    solver = SlidingPuzzleAStarFathersRuleGlobalSmartBatchedWithClosedSet(
        initial_state=puzzle_4x4,
        size=4,
        max_expansions=20000,
        batch_size=50
    )
    path, solved = solver.solve()
    print(f"Solved? {solved}")
    print(f"Path length: {len(path)}")
    for i, st in enumerate(path):
        print(f"{i}: {st}")
