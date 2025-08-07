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
        self.known_wumpus_count = K

        # KB stores facts about cells: 'W', 'P', '-W', '-P', 'S' (Safe)
        self.kb = [[set() for _ in range(self.N)] for _ in range(self.N)]

        # Inferred status for display and planning
        self.kb_status = [["Unknown" for _ in range(self.N)] for _ in range(self.N)]
        self.visited = [[False for _ in range(self.N)] for _ in range(self.N)]

        # Initialize KB for starting cell
        self.kb[0][0].add("S")  # Safe
        self.kb_status[0][0] = "Safe"

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
