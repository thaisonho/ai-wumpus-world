# src/agent/pathfinding_module.py
import heapq
from utils.constants import (
    DIRECTIONS,
    ACTION_MOVE_FORWARD,
    ACTION_TURN_LEFT,
    ACTION_TURN_RIGHT,
    SCORE_MOVE_FORWARD,
    SCORE_TURN,
)

class PathfindingModule:
    """
    Handles pathfinding for the agent using a risk-aware A* search algorithm.
    It can find paths that avoid danger or paths that take calculated risks
    to reach a destination.
    """
    def __init__(self, N):
        """
        Initializes the PathfindingModule.
        Args:
            N (int): The size of the N x N grid.
        """
        self.N = N

    def _is_valid_coord(self, x, y):
        """
        Checks if a given coordinate (x, y) is within the grid boundaries.
        Returns:
            bool: True if the coordinate is valid, False otherwise.
        """
        return 0 <= x < self.N and 0 <= y < self.N

    def _get_heuristic_cost(self, pos, goal_pos):
        """
        Calculates the heuristic cost (h_cost) using the Manhattan distance.
        This is an admissible heuristic for a grid where movement is restricted
        to cardinal directions.
        Args:
            pos (tuple): The current position (x, y).
            goal_pos (tuple): The target position (x, y).
        Returns:
            int: The Manhattan distance between the two positions.
        """
        return abs(pos[0] - goal_pos[0]) + abs(pos[1] - goal_pos[1])

    def find_path(
        self,
        start_pos,
        start_dir,
        goal_pos,
        kb_status,
        avoid_dangerous=True,
    ):
        """
        Implements the A* search algorithm to find an optimal path from a start
        to a goal position.

        The state in the search space is defined by (position, direction).
        The cost function incorporates movement cost, turning cost, and a risk
        penalty for entering unknown or dangerous cells.

        Args:
            start_pos (tuple): The starting (x, y) coordinate.
            start_dir (tuple): The starting direction vector (dx, dy).
            goal_pos (tuple): The target (x, y) coordinate.
            kb_status (list[list[str]]): The agent's knowledge of cell statuses
                                         ('Safe', 'Dangerous', 'Unknown', 'Visited').
            avoid_dangerous (bool): If True, the path will not enter cells marked
                                    as 'Dangerous'. If False, it may enter them,
                                    but at a high cost penalty.

        Returns:
            list[str] or None: A list of actions (e.g., ['MoveForward', 'TurnRight'])
                               representing the path, or None if no path is found.
        """
        # The priority queue (min-heap) stores tuples of:
        # (f_cost, g_cost, position, direction, action_path)
        # f_cost = g_cost + h_cost
        open_set = []
        h_cost = self._get_heuristic_cost(start_pos, goal_pos)
        heapq.heappush(open_set, (h_cost, 0, start_pos, start_dir, []))

        # A dictionary to store the lowest g_cost found so far for each state (pos, dir).
        g_costs = {(start_pos, start_dir): 0}
        # A helper dictionary to quickly get the index of a direction tuple.
        dir_to_idx = {dir_tuple: i for i, dir_tuple in enumerate(DIRECTIONS)}

        while open_set:
            # Pop the node with the lowest f_cost from the priority queue.
            _, g_cost, current_pos, current_dir, path = heapq.heappop(open_set)

            # If we've found a better path to this state already, skip.
            if g_cost > g_costs.get((current_pos, current_dir), float("inf")):
                continue

            # If the current position is the goal, we have found the path.
            if current_pos == goal_pos:
                return path

            current_dir_idx = dir_to_idx[current_dir]

            # --- Explore possible actions from the current state ---

            # 1. Try moving forward
            next_pos = (current_pos[0] + current_dir[0], current_pos[1] + current_dir[1])
            if self._is_valid_coord(next_pos[0], next_pos[1]):
                cell_status = kb_status[next_pos[0]][next_pos[1]]

                # Check if moving to the next cell is allowed based on risk preference.
                if not (avoid_dangerous and cell_status == "Dangerous"):
                    # Add a risk penalty to the cost for entering non-safe cells.
                    risk_cost = 0
                    if cell_status == "Dangerous": risk_cost = 100 # High penalty for known danger
                    elif cell_status == "Unknown": risk_cost = 10  # Moderate penalty for uncertainty

                    new_g_cost = g_cost + abs(SCORE_MOVE_FORWARD) + risk_cost
                    next_state = (next_pos, current_dir)

                    # If this is a better path to the next state, update it.
                    if new_g_cost < g_costs.get(next_state, float("inf")):
                        g_costs[next_state] = new_g_cost
                        h_cost = self._get_heuristic_cost(next_pos, goal_pos)
                        f_cost = new_g_cost + h_cost
                        heapq.heappush(open_set, (f_cost, new_g_cost, next_pos, current_dir, path + [ACTION_MOVE_FORWARD]))

            # 2. & 3. Try turning left and right
            # Turning happens in place, so the position doesn't change, only the direction.
            for turn_action, turn_change in [(ACTION_TURN_LEFT, -1), (ACTION_TURN_RIGHT, 1)]:
                new_dir_idx = (current_dir_idx + turn_change + len(DIRECTIONS)) % len(DIRECTIONS)
                new_dir = DIRECTIONS[new_dir_idx]

                new_g_cost = g_cost + abs(SCORE_TURN)
                next_state = (current_pos, new_dir)

                # If this is a better path to the next state (same position, new direction), update it.
                if new_g_cost < g_costs.get(next_state, float("inf")):
                    g_costs[next_state] = new_g_cost
                    h_cost = self._get_heuristic_cost(current_pos, goal_pos) # Heuristic is the same
                    f_cost = new_g_cost + h_cost
                    heapq.heappush(open_set, (f_cost, new_g_cost, current_pos, new_dir, path + [turn_action]))

        # If the open_set becomes empty and the goal was not reached, no path exists.
        return None