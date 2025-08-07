import heapq  # For A* priority queue
from utils.constants import (
    NORTH,
    EAST,
    SOUTH,
    WEST,
    DIRECTIONS,
    ACTION_MOVE_FORWARD,
    ACTION_TURN_LEFT,
    ACTION_TURN_RIGHT,
    SCORE_MOVE_FORWARD,
    SCORE_TURN,
)


class PlanningModule:
    def __init__(self, N):
        self.N = N

    def _is_valid_coord(self, x, y):
        return 0 <= x < self.N and 0 <= y < self.N

    def _get_cost(self, action):
        """Returns the cost of an action."""
        if action == ACTION_MOVE_FORWARD:
            return abs(SCORE_MOVE_FORWARD)
        elif action in [ACTION_TURN_LEFT, ACTION_TURN_RIGHT]:
            return abs(SCORE_TURN)
        return 0  # Other actions like Grab, Shoot, ClimbOut don't have movement cost

    def find_path(
        self,
        start_pos,
        start_dir,
        goal_pos,
        kb_status,
        visited_cells,
        avoid_dangerous=True,
    ):
        """
        Finds a path from start_pos to goal_pos using A* search.
        Considers agent's current direction and costs of turning/moving.

        :param start_pos: (x, y) tuple of the agent's starting position.
        :param start_dir: (dx, dy) tuple of the agent's starting direction.
        :param goal_pos: (x, y) tuple of the target position.
        :param kb_status: 2D list of agent's inferred cell statuses ('Safe', 'Dangerous', 'Unknown').
        :param visited_cells: 2D boolean list of visited cells.
        :param avoid_dangerous: If True, avoids 'Dangerous' cells. If False, allows them (e.g., for shooting).
        :return: A list of actions to reach the goal, or None if no path found.
        """
        # Priority queue: (f_cost, g_cost, (x,y), (dx,dy), path_actions)
        # f_cost = g_cost + h_cost
        # g_cost = cost from start to current node
        # h_cost = heuristic (Manhattan distance to goal)
        # (x,y) = current position
        # (dx,dy) = current direction
        # path_actions = list of actions taken to reach this state

        # State in closed_set: ((x,y), (dx,dy))
        # This prevents cycles and re-exploring states with higher cost
        open_set = []
        heapq.heappush(open_set, (0, 0, start_pos, start_dir, []))

        # g_costs: stores the lowest g_cost to reach a state ((x,y), (dx,dy))
        g_costs = {(start_pos, start_dir): 0}

        # Convert direction tuple to index for easier turning logic
        dir_to_idx = {dir_tuple: i for i, dir_tuple in enumerate(DIRECTIONS)}
        start_dir_idx = dir_to_idx[start_dir]

        while open_set:
            f_cost, g_cost, current_pos, current_dir, path_actions = heapq.heappop(
                open_set
            )
            current_dir_idx = dir_to_idx[current_dir]

            # If we reached the goal
            if current_pos == goal_pos:
                return path_actions

            # Check if we've found a better path to this state already
            if g_cost > g_costs.get((current_pos, current_dir), float("inf")):
                continue

            # Explore neighbors
            # 1. Try moving forward
            move_dx, move_dy = current_dir
            next_x, next_y = current_pos[0] + move_dx, current_pos[1] + move_dy

            if self._is_valid_coord(next_x, next_y):
                # Check if the next cell is safe or allowed
                is_safe = kb_status[next_x][next_y] == "Safe"
                is_visited = visited_cells[next_x][next_y]
                is_dangerous = kb_status[next_x][next_y] == "Dangerous"
                is_unknown = kb_status[next_x][next_y] == "Unknown"

                # Allow moving into dangerous cells if avoid_dangerous is False
                # Always allow moving into visited cells (they are safe)
                if is_safe or is_visited or not avoid_dangerous:
                    risk_cost = 0
                    if not avoid_dangerous:
                        if is_dangerous:
                            risk_cost = 100  # High cost for dangerous cells
                        elif is_unknown:
                            risk_cost = 10 # Moderate cost for unknown cells
                    
                    new_g_cost = g_cost + self._get_cost(ACTION_MOVE_FORWARD) + risk_cost
                    if new_g_cost < g_costs.get(
                        ((next_x, next_y), current_dir), float("inf")
                    ):
                        g_costs[((next_x, next_y), current_dir)] = new_g_cost
                        h_cost = abs(next_x - goal_pos[0]) + abs(
                            next_y - goal_pos[1]
                        )  # Manhattan distance
                        heapq.heappush(
                            open_set,
                            (
                                new_g_cost + h_cost,
                                new_g_cost,
                                (next_x, next_y),
                                current_dir,
                                path_actions + [ACTION_MOVE_FORWARD],
                            ),
                        )
            
            # 2. Try turning left
            next_dir_idx_left = (current_dir_idx - 1 + len(DIRECTIONS)) % len(DIRECTIONS)
            next_dir_left = DIRECTIONS[next_dir_idx_left]
            new_g_cost_left = g_cost + self._get_cost(ACTION_TURN_LEFT)
            if new_g_cost_left < g_costs.get(
                (current_pos, next_dir_left), float("inf")
            ):
                g_costs[(current_pos, next_dir_left)] = new_g_cost_left
                h_cost = abs(current_pos[0] - goal_pos[0]) + abs(
                    current_pos[1] - goal_pos[1]
                )  # Manhattan distance
                heapq.heappush(
                    open_set,
                    (
                        new_g_cost_left + h_cost,
                        new_g_cost_left,
                        current_pos,
                        next_dir_left,
                        path_actions + [ACTION_TURN_LEFT],
                    ),
                )

            # 3. Try turning right
            next_dir_idx_right = (current_dir_idx + 1) % len(DIRECTIONS)
            next_dir_right = DIRECTIONS[next_dir_idx_right]
            new_g_cost_right = g_cost + self._get_cost(ACTION_TURN_RIGHT)
            if new_g_cost_right < g_costs.get(
                (current_pos, next_dir_right), float("inf")
            ):
                g_costs[(current_pos, next_dir_right)] = new_g_cost_right
                h_cost = abs(current_pos[0] - goal_pos[0]) + abs(
                    current_pos[1] - goal_pos[1]
                )  # Manhattan distance
                heapq.heappush(
                    open_set,
                    (
                        new_g_cost_right + h_cost,
                        new_g_cost_right,
                        current_pos,
                        next_dir_right,
                        path_actions + [ACTION_TURN_RIGHT],
                    ),
                )

        return None  # No path found
