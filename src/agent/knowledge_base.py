# src/agent/knowledge_base.py

from utils.constants import N_DEFAULT, K_DEFAULT, DIRECTIONS

# --- Fact Constants ---
F_WUMPUS, F_PIT, F_GOLD, F_SAFE = "W", "P", "G", "S"
F_NOT_WUMPUS, F_NOT_PIT = "-W", "-P"
F_POSSIBLE_WUMPUS, F_POSSIBLE_PIT = "W?", "P?"
F_HAS_STENCH, F_HAS_BREEZE = "HasStench", "HasBreeze"
F_DEAD_WUMPUS = "DeadW"

class KnowledgeBase:
    """
    Represents the agent's memory. It now distinguishes between permanent and
    volatile (temporary) facts, which is crucial for dynamic environments.
    """
    def __init__(self, N=N_DEFAULT, K=K_DEFAULT):
        self.N = N
        self.initial_wumpus_count = K
        self.known_wumpus_count = K
        self.gold_found_at = None

        # Each cell now has two sets: one for permanent facts and one for volatile facts.
        self.kb: list[list[dict[str, set]]] = [
            {'permanent': set(), 'volatile': set()} for _ in range(self.N * self.N)
        ]
        self.kb_status: list[list[str]] = [["Unknown" for _ in range(self.N)] for _ in range(self.N)]
        self.visited: list[list[bool]] = [[False for _ in range(self.N)] for _ in range(self.N)]

        # --- Initial Knowledge ---
        # Start cell is safe. These are permanent facts.
        self.add_fact((0, 0), F_NOT_PIT, volatile=False)
        self.add_fact((0, 0), F_NOT_WUMPUS, volatile=False)
        self.add_fact((0, 0), F_SAFE, volatile=False)
        self.kb_status[0][0] = "Safe"

    def _pos_to_idx(self, pos: tuple[int, int]) -> int:
        return pos[0] * self.N + pos[1]

    def add_fact(self, pos: tuple[int, int], fact: str, volatile: bool = False):
        """Adds a fact to the KB for a specific cell, marking it as volatile if necessary."""
        key = 'volatile' if volatile else 'permanent'
        self.kb[self._pos_to_idx(pos)][key].add(fact)

    def get_facts(self, pos: tuple[int, int]) -> set[str]:
        """Retrieves a combined set of all known facts (permanent and volatile) for a cell."""
        idx = self._pos_to_idx(pos)
        return self.kb[idx]['permanent'].union(self.kb[idx]['volatile'])

    def remove_fact(self, pos: tuple[int, int], fact: str):
        """Removes a fact from both permanent and volatile storage to ensure cleanliness."""
        idx = self._pos_to_idx(pos)
        self.kb[idx]['permanent'].discard(fact)
        self.kb[idx]['volatile'].discard(fact)

    def drop_volatile_facts(self, pos: tuple[int, int]):
        """Clears all volatile facts for a cell. This is called at the end of an epoch."""
        self.kb[self._pos_to_idx(pos)]['volatile'].clear()

    def mark_visited(self, pos: tuple[int, int]):
        """Marks a cell as visited. A visited cell is permanently safe."""
        x, y = pos
        if not self.visited[x][y]:
            self.visited[x][y] = True
            self.kb_status[x][y] = "Visited"
            # Facts derived from visiting are permanent.
            self.add_fact(pos, F_SAFE, volatile=False)
            self.add_fact(pos, F_NOT_WUMPUS, volatile=False)
            self.add_fact(pos, F_NOT_PIT, volatile=False)

    def _is_valid_coord(self, x: int, y: int) -> bool:
        return 0 <= x < self.N and 0 <= y < self.N

    def get_neighbors(self, pos: tuple[int, int]) -> list[tuple[int, int]]:
        x, y = pos
        neighbors = []
        for dx, dy in DIRECTIONS:
            nx, ny = x + dx, y + dy
            if self._is_valid_coord(nx, ny):
                neighbors.append((nx, ny))
        return neighbors