# wumpus_world/agent/inference_engine.py

from utils.constants import (
    N_DEFAULT,
    K_DEFAULT,
    PERCEPT_STENCH,
    PERCEPT_BREEZE,
    PERCEPT_GLITTER,
    PERCEPT_SCREAM,
    PERCEPT_BUMP,
    WUMPUS_SYMBOL,
    PIT_SYMBOL,
    GOLD_SYMBOL,
    ACTION_MOVE_FORWARD,
    DIRECTIONS,
)
from itertools import combinations


class InferenceEngine:
    def __init__(self, N=N_DEFAULT, K=1):
        self.N = N
        self.K = K
        self.known_wumpus_count = K # Agent knows how many Wumpuses are alive

        # The Knowledge Base (KB) stores facts about each cell.
        # This is a simplified version. A full implementation would use
        # propositional logic sentences (e.g., using a custom class for clauses).
        # Example facts: 'W' (is Wumpus), '-P' (is not Pit), 'S' (is Safe).
        self.kb = [[set() for _ in range(self.N)] for _ in range(self.N)]
        
        # This map stores the agent's inferred status for planning and display.
        self.kb_status = [["Unknown" for _ in range(self.N)] for _ in range(self.N)]
        self.visited = [[False for _ in range(self.N)] for _ in range(self.N)]

        # The starting cell (0,0) is always safe.
        self.kb_status[0][0] = "Safe"
        self.kb[0][0].add("S")

    def _is_valid_coord(self, x, y):
        """Checks if coordinates are within the map boundaries."""
        return 0 <= x < self.N and 0 <= y < self.N

    def _get_neighbors(self, x, y):
        """Gets all valid neighbor coordinates for a given cell."""
        neighbors = []
        for dx, dy in DIRECTIONS:
            nx, ny = x + dx, y + dy
            if self._is_valid_coord(nx, ny):
                neighbors.append((nx, ny))
        return neighbors

    def update_knowledge(self, current_pos, percepts, last_action=None, last_shoot_dir=None):
        """
        Updates the KB based on new percepts. This process is a form of inference,
        where new facts are derived from existing ones and new evidence.
        A full implementation would use a forward chaining or resolution algorithm.
        """
        x, y = current_pos

        # Mark the current cell as visited and definitely safe.
        if not self.visited[x][y]:
            self.visited[x][y] = True
            self.kb_status[x][y] = "Visited"
            self.kb[x][y].add("S") # Add "is Safe" to the KB

        # --- Inference from Percepts ---

        # If we hear a scream, a Wumpus is dead.
        if PERCEPT_SCREAM in percepts:
            self.known_wumpus_count -= 1
            # If we know which way we shot, we can deduce the Wumpus's location.
            if last_shoot_dir:
                shot_x, shot_y = x + last_shoot_dir[0], y + last_shoot_dir[1]
                while self._is_valid_coord(shot_x, shot_y):
                    # The first unvisited/unknown cell in the line of fire is the dead Wumpus.
                    if self.kb_status[shot_x][shot_y] != "Visited":
                        self.kb[shot_x][shot_y].add("-W") # No more Wumpus here
                        self.kb[shot_x][shot_y].add("S")  # It's now safe
                        self.kb_status[shot_x][shot_y] = "Safe"
                        break
                    shot_x, shot_y = shot_x + last_shoot_dir[0], shot_y + last_shoot_dir[1]

        # If we bump, we know the boundaries (though N is known).
        if PERCEPT_BUMP in percepts and last_action == ACTION_MOVE_FORWARD:
            # This could be used to infer walls if N were unknown.
            pass

        # --- Propositional Logic Rules ---
        # For each neighbor, update knowledge based on Stench and Breeze.
        neighbors = self._get_neighbors(x, y)

        # Rule: No Stench => All neighbors are not Wumpuses.
        if PERCEPT_STENCH not in percepts:
            for nx, ny in neighbors:
                self.kb[nx][ny].add("-W")
        # Rule: Stench => At least one neighbor is a Wumpus.
        # (W1 v W2 v ... v Wn). This requires more complex reasoning (e.g., model checking).
        else:
            # For now, we can mark unvisited neighbors with a potential Wumpus.
            for nx, ny in neighbors:
                if not self.visited[nx][ny]:
                    self.kb[nx][ny].add(WUMPUS_SYMBOL) # Tentative

        # Rule: No Breeze => All neighbors are not Pits.
        if PERCEPT_BREEZE not in percepts:
            for nx, ny in neighbors:
                self.kb[nx][ny].add("-P")
        # Rule: Breeze => At least one neighbor is a Pit.
        # (P1 v P2 v ... v Pn).
        else:
            # Mark unvisited neighbors with a potential Pit.
            for nx, ny in neighbors:
                if not self.visited[nx][ny]:
                    self.kb[nx][ny].add(PIT_SYMBOL) # Tentative

        # --- Re-evaluate all cells based on new KB facts ---
        self._update_all_cell_statuses()

    def _update_all_cell_statuses(self):
        """
        Iterates through the entire grid and updates the high-level status
        ('Safe', 'Dangerous', 'Unknown') based on the facts in the KB.
        """
        for x in range(self.N):
            for y in range(self.N):
                if self.visited[x][y]:
                    self.kb_status[x][y] = "Visited"
                    continue

                facts = self.kb[x][y]
                # A cell is confirmed safe if we know there's no Wumpus AND no Pit.
                if "-W" in facts and "-P" in facts:
                    self.kb_status[x][y] = "Safe"
                # A cell is confirmed dangerous if we know there's a Wumpus OR a Pit.
                elif "W" in facts or "P" in facts:
                     self.kb_status[x][y] = "Dangerous"
                # Otherwise, it remains unknown.

    def get_known_map(self):
        """Returns the map of things the agent knows for sure (W, P, G)."""
        known_map = [[set() for _ in range(self.N)] for _ in range(self.N)]
        for r in range(self.N):
            for c in range(self.N):
                # This part is for visualization, showing inferred elements.
                if WUMPUS_SYMBOL in self.kb[r][c]:
                    known_map[r][c].add(WUMPUS_SYMBOL)
                if PIT_SYMBOL in self.kb[r][c]:
                    known_map[r][c].add(PIT_SYMBOL)
                if GOLD_SYMBOL in self.kb[r][c]:
                    known_map[r][c].add(GOLD_SYMBOL)
        return known_map

    def get_kb_status(self):
        """Returns the high-level status map for the planner."""
        return self.kb_status

    def get_visited_cells(self):
        return self.visited

    def get_safe_unvisited_cells(self):
        """Returns a list of cells that are inferred to be safe but not yet visited."""
        safe_cells = []
        for x in range(self.N):
            for y in range(self.N):
                if self.kb_status[x][y] == "Safe" and not self.visited[x][y]:
                    safe_cells.append((x, y))
        return safe_cells
    
    def get_possible_wumpus_locations(self):
        """Returns cells that might contain a Wumpus."""
        possible_wumpus = []
        for x in range(self.N):
            for y in range(self.N):
                # A cell could have a wumpus if it's not confirmed safe and not confirmed no-wumpus
                if self.kb_status[x][y] == "Unknown" and "-W" not in self.kb[x][y]:
                    possible_wumpus.append((x,y))
        return possible_wumpus

    def _is_valid_coord(self, x, y):
        return 0 <= x < self.N and 0 <= y < self.N

    def _get_neighbors(self, x, y):
        neighbors = []
        for dx, dy in DIRECTIONS:
            nx, ny = x + dx, y + dy
            if self._is_valid_coord(nx, ny):
                neighbors.append((nx, ny))
        return neighbors

    def update_knowledge(self, current_pos, percepts, last_action=None, last_shoot_dir=None):
        x, y = current_pos

        # Mark current cell as visited and safe
        self.visited[x][y] = True
        self.kb[x][y].add("S")
        self.kb_status[x][y] = "Safe"

        # Add facts about current cell to KB
        if PERCEPT_GLITTER in percepts:
            self.kb[x][y].add(GOLD_SYMBOL)

        # Handle scream
        if PERCEPT_SCREAM in percepts and self.known_wumpus_count > 0:
            self.known_wumpus_count -= 1
            if last_shoot_dir:
                # Infer wumpus location
                wx, wy = x, y
                while self._is_valid_coord(wx, wy):
                    wx, wy = wx + last_shoot_dir[0], wy + last_shoot_dir[1]
                    if self._is_valid_coord(wx, wy):
                        self.kb[wx][wy].add("-W")  # Wumpus is not here
                        self.kb[wx][wy].add("S")  # Cell is safe from wumpus
                        self.kb_status[wx][wy] = "Safe"
                        break  # Only first wumpus is killed

        # Handle bump
        if PERCEPT_BUMP in percepts and last_action == ACTION_MOVE_FORWARD:
            # This confirms a wall, but agent already knows N.
            # Could be used for more complex maps.
            pass

        # Add percept rules to KB
        neighbors = self._get_neighbors(x, y)

        # Stench
        if PERCEPT_STENCH in percepts:
            # At least one neighbor has a wumpus
            # This is a clause: W(n1) v W(n2) v ...
            # For now, we'll use a simplified model
            pass  # More complex logic needed here
        else:
            # No wumpus in any neighbor
            for nx, ny in neighbors:
                self.kb[nx][ny].add("-W")

        # Breeze
        if PERCEPT_BREEZE in percepts:
            # At least one neighbor has a pit
            pass
        else:
            # No pit in any neighbor
            for nx, ny in neighbors:
                self.kb[nx][ny].add("-P")

        # Re-evaluate all cells based on new info
        self._infer_all_cells()

    def _infer_all_cells(self):
        for x in range(self.N):
            for y in range(self.N):
                if "S" in self.kb[x][y]:
                    self.kb_status[x][y] = "Safe"
                    continue

                # If we know it's not a wumpus and not a pit, it's safe
                if "-W" in self.kb[x][y] and "-P" in self.kb[x][y]:
                    self.kb[x][y].add("S")
                    self.kb_status[x][y] = "Safe"

                # Check for definite wumpus/pit
                # This is a simplification of resolution
                for vx, vy in self._get_neighbors(x, y):
                    if self.visited[vx][vy]:
                        # Check stench
                        # If stench at (vx,vy) and all other neighbors of (vx,vy) are not wumpuses
                        # then (x,y) must be a wumpus
                        v_neighbors = self._get_neighbors(vx, vy)
                        other_neighbors_safe_from_wumpus = True
                        unknown_neighbors = []
                        for vnx, vny in v_neighbors:
                            if (vnx, vny) != (x, y):
                                if "-W" not in self.kb[vnx][vny]:
                                    other_neighbors_safe_from_wumpus = False
                                    unknown_neighbors.append((vnx, vny))

                        # This logic is complex and needs to be more robust
                        # For now, we'll stick to simpler inferences

        # Update status for display
        for x in range(self.N):
            for y in range(self.N):
                if self.kb_status[x][y] != "Safe" and self.kb_status[x][y] != "Dangerous":
                    if ("W" in self.kb[x][y] or "P" in self.kb[x][y]):
                        self.kb_status[x][y] = "Dangerous"
                    elif ('-W' in self.kb[x][y] and '-P' in self.kb[x][y]):
                        self.kb_status[x][y] = "Safe"
                    else:
                        self.kb_status[x][y] = "Unknown"

    def get_known_map(self):
        # This needs to be adapted to the new KB
        known_map = [[set() for _ in range(self.N)] for _ in range(self.N)]
        for x in range(self.N):
            for y in range(self.N):
                if 'W' in self.kb[x][y]: known_map[x][y].add(WUMPUS_SYMBOL)
                if 'P' in self.kb[x][y]: known_map[x][y].add(PIT_SYMBOL)
                if GOLD_SYMBOL in self.kb[x][y]: known_map[x][y].add(GOLD_SYMBOL)
        return known_map

    def get_kb_status(self):
        return self.kb_status

    def get_visited_cells(self):
        return self.visited

    @property
    def possible_wumpus(self):
        # Derive from KB
        possible = set()
        for x in range(self.N):
            for y in range(self.N):
                if not self.visited[x][y] and '-W' not in self.kb[x][y]:
                    possible.add((x,y))
        return possible

    @property
    def possible_pits(self):
        # Derive from KB
        possible = set()
        for x in range(self.N):
            for y in range(self.N):
                if not self.visited[x][y] and '-P' not in self.kb[x][y]:
                    possible.add((x,y))
        return possible
