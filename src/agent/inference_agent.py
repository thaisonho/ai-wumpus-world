# wumpus_world/agent/inference_engine.py

from utils.constants import (
    N_DEFAULT,
    PERCEPT_STENCH,
    PERCEPT_BREEZE,
    PERCEPT_GLITTER,
    PERCEPT_SCREAM,
    PERCEPT_BUMP,
    WUMPUS_SYMBOL,
    PIT_SYMBOL,
    GOLD_SYMBOL,
    NORTH,
    EAST,
    SOUTH,
    WEST,
    DIRECTIONS,
)


class InferenceEngine:
    def __init__(self, N=N_DEFAULT):
        self.N = N
        # Agent's internal knowledge base
        # known_map: What the agent knows about each cell's contents (e.g., {PIT_SYMBOL}, {STENCH_SYMBOL})
        # Each cell stores a set of symbols it *knows* are there or *knows* are not there.
        # For simplicity, we'll use positive assertions for now.
        self.known_map = [[set() for _ in range(self.N)] for _ in range(self.N)]

        # kb_status: Inferred safety status of each cell ('Safe', 'Dangerous', 'Unknown')
        self.kb_status = [["Unknown" for _ in range(self.N)] for _ in range(self.N)]

        # Visited cells
        self.visited = [[False for _ in range(self.N)] for _ in range(self.N)]

        # Possible locations for Wumpus and Pits (for advanced inference)
        self.possible_wumpus = set()  # Stores (x,y) tuples
        self.possible_pits = set()  # Stores (x,y) tuples

        # Initialize all cells as possible Wumpus/Pit locations, except (0,0)
        for x in range(self.N):
            for y in range(self.N):
                if (x, y) != (0, 0):
                    self.possible_wumpus.add((x, y))
                    self.possible_pits.add((x, y))

        # Mark starting cell (0,0) as safe and visited
        self.kb_status[0][0] = "Safe"
        self.visited[0][0] = True
        self.possible_wumpus.discard((0, 0))  # Wumpus cannot be at (0,0)
        self.possible_pits.discard((0, 0))  # Pit cannot be at (0,0)

    def _is_valid_coord(self, x, y):
        return 0 <= x < self.N and 0 <= y < self.N

    def _get_neighbors(self, x, y):
        neighbors = []
        for dx, dy in DIRECTIONS:
            nx, ny = x + dx, y + dy
            if self._is_valid_coord(nx, ny):
                neighbors.append((nx, ny))
        return neighbors

    def update_knowledge(
        self, current_pos, percepts, last_action=None, last_action_success=True
    ):
        """
        Updates the agent's knowledge base based on current percepts and actions.
        This is the core of the inference engine.
        """
        x, y = current_pos

        # 1. Mark current cell as visited and safe
        self.visited[x][y] = True
        self.kb_status[x][y] = "Safe"
        self.possible_wumpus.discard((x, y))  # Cannot be Wumpus if safe
        self.possible_pits.discard((x, y))  # Cannot be Pit if safe

        # 2. Process Percepts at current_pos
        has_stench = PERCEPT_STENCH in percepts
        has_breeze = PERCEPT_BREEZE in percepts
        has_glitter = PERCEPT_GLITTER in percepts
        has_scream = PERCEPT_SCREAM in percepts
        has_bump = (
            PERCEPT_BUMP in percepts
        )  # Bump is a percept, but also implies hitting a wall

        # If Glitter, Gold is here
        if has_glitter:
            self.known_map[x][y].add(GOLD_SYMBOL)

        # If Scream, a Wumpus was killed. This implies its location was along the last shot.
        # For now, we'll simplify: if scream, all known Wumpus locations are invalidated.
        # A more advanced agent would use the shooting direction to pinpoint.
        if has_scream:
            # Invalidate all current possible Wumpus locations
            # This is a simplification. A real agent would use the shooting direction.
            # For now, we just know one less Wumpus exists.
            # We don't clear possible_wumpus, but rather reduce the count if we track it.
            # For this project, we assume only one Wumpus is killed per scream.
            pass  # The agent's planning module will need to account for this.

        # Process Stench and Breeze
        neighbors = self._get_neighbors(x, y)

        if has_stench:
            # If stench, then at least one Wumpus is in an adjacent cell.
            # Mark all unvisited neighbors as potentially containing a Wumpus.
            for nx, ny in neighbors:
                if not self.visited[nx][ny]:
                    self.possible_wumpus.add((nx, ny))
                # If a neighbor is already known safe, it cannot have a Wumpus.
                if self.kb_status[nx][ny] == "Safe":
                    self.possible_wumpus.discard((nx, ny))
        else:  # No Stench
            # If no stench, then NO Wumpus in any adjacent cell.
            for nx, ny in neighbors:
                self.possible_wumpus.discard((nx, ny))
                # If a neighbor is not visited and not a possible Wumpus, it's safe.
                if not self.visited[nx][ny] and (nx, ny) not in self.possible_pits:
                    self.kb_status[nx][ny] = "Safe"

        if has_breeze:
            # If breeze, then at least one Pit is in an adjacent cell.
            # Mark all unvisited neighbors as potentially containing a Pit.
            for nx, ny in neighbors:
                if not self.visited[nx][ny]:
                    self.possible_pits.add((nx, ny))
                # If a neighbor is already known safe, it cannot have a Pit.
                if self.kb_status[nx][ny] == "Safe":
                    self.possible_pits.discard((nx, ny))
        else:  # No Breeze
            # If no breeze, then NO Pit in any adjacent cell.
            for nx, ny in neighbors:
                self.possible_pits.discard((nx, ny))
                # If a neighbor is not visited and not a possible Pit, it's safe.
                if not self.visited[nx][ny] and (nx, ny) not in self.possible_wumpus:
                    self.kb_status[nx][ny] = "Safe"

        # 3. Update KB status based on possible locations
        # A cell is dangerous if it's a possible Wumpus AND a possible Pit, or only one of them.
        # A cell is safe if it's not a possible Wumpus AND not a possible Pit.
        for x_cell in range(self.N):
            for y_cell in range(self.N):
                if self.visited[x_cell][y_cell]:
                    self.kb_status[x_cell][y_cell] = "Safe"
                elif (x_cell, y_cell) in self.possible_wumpus or (
                    x_cell,
                    y_cell,
                ) in self.possible_pits:
                    self.kb_status[x_cell][y_cell] = "Dangerous"
                else:
                    # If not visited, and not a possible Wumpus/Pit, then it's safe.
                    self.kb_status[x_cell][y_cell] = "Safe"

        # Refine dangerous cells: if a cell is marked dangerous, but we've ruled out both Wumpus and Pit, it's safe.
        for x_cell in range(self.N):
            for y_cell in range(self.N):
                if self.kb_status[x_cell][y_cell] == "Dangerous":
                    is_possible_wumpus = (x_cell, y_cell) in self.possible_wumpus
                    is_possible_pit = (x_cell, y_cell) in self.possible_pits
                    if not is_possible_wumpus and not is_possible_pit:
                        self.kb_status[x_cell][y_cell] = "Safe"
                    elif not is_possible_wumpus and is_possible_pit:
                        self.known_map[x_cell][y_cell].add(PIT_SYMBOL)  # Known pit
                    elif is_possible_wumpus and not is_possible_pit:
                        self.known_map[x_cell][y_cell].add(
                            WUMPUS_SYMBOL
                        )  # Known wumpus
                    # If both are possible, it remains dangerous.

        # Special handling for Bump percept:
        # If agent bumped, it means the attempted move was into a wall.
        # This implies the cell in the direction of the attempted move is a wall,
        # and thus not a valid Wumpus/Pit location.
        if (
            has_bump and last_action == PERCEPT_BUMP
        ):  # PERCEPT_BUMP is used as a pseudo-action for bump
            # The agent's position didn't change, but it tried to move.
            # The cell it tried to move into is outside the map.
            # This percept is more about boundary knowledge than cell content.
            pass  # The environment already handles the agent staying in place.

    def get_known_map(self):
        return self.known_map

    def get_kb_status(self):
        return self.kb_status

    def get_visited_cells(self):
        return self.visited

    def get_possible_wumpus_locations(self):
        return self.possible_wumpus

    def get_possible_pit_locations(self):
        return self.possible_pits
