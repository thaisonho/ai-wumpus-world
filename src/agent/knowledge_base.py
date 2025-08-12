# src/agent/knowledge_base.py

from utils.constants import N_DEFAULT, K_DEFAULT, DIRECTIONS

# --- Fact Constants ---
# Using constants for atomic sentences (facts) ensures consistency and readability across the system.
# Positive facts: Something is present or true.
F_WUMPUS, F_PIT, F_GOLD, F_SAFE = "W", "P", "G", "S"
# Negative facts: Something is proven to be absent or false.
F_NOT_WUMPUS, F_NOT_PIT = "-W", "-P"
# Tentative facts: A possibility that has not been confirmed or denied.
F_POSSIBLE_WUMPUS, F_POSSIBLE_PIT = "W?", "P?"

# --- ADDED: New constants for percepts and Wumpus state ---
F_HAS_STENCH = "HasStench"  # Fact that a cell has a stench percept
F_HAS_BREEZE = "HasBreeze"  # Fact that a cell has a breeze percept
F_DEAD_WUMPUS = "DeadW"     # Fact that a Wumpus in this cell is confirmed dead

class KnowledgeBase:
    """
    Represents the "Memory" or "Database" of the Agent.
    
    Role: Its sole responsibility is to store, manage, and provide access to facts
    (the agent's beliefs about the world). It performs no reasoning itself; it is
    a passive data repository that is acted upon by the InferenceEngine.
    """
    def __init__(self, N=N_DEFAULT, K=K_DEFAULT):
        """
        Initializes the knowledge base for a new game.

        Args:
            N (int): The size of the N x N grid.
            K (int): The initial number of Wumpuses in the world.
        """
        self.N = N
        self.initial_wumpus_count = K
        # MODIFIED: This now explicitly means the number of *living* Wumpuses believed to exist.
        self.known_wumpus_count = K
        self.gold_found_at = None

        # The core of the KB: A 2D grid where each cell holds a set of string-based facts.
        self.kb: list[list[set[str]]] = [[set() for _ in range(self.N)] for _ in range(self.N)]
        
        # A high-level summary map for the PlanningModule. Statuses: 'Unknown', 'Safe', 'Dangerous', 'Visited'.
        self.kb_status: list[list[str]] = [["Unknown" for _ in range(self.N)] for _ in range(self.N)]
        
        # A boolean grid to track which cells the agent has physically entered.
        self.visited: list[list[bool]] = [[False for _ in range(self.N)] for _ in range(self.N)]

        # --- Initial Knowledge Axiom ---
        # World Rule #5: The starting cell (0,0) is always safe.
        # This translates to: Not a Pit AND Not a Wumpus.
        self.add_fact((0, 0), F_NOT_PIT)
        self.add_fact((0, 0), F_NOT_WUMPUS)
        self.add_fact((0, 0), F_SAFE)
        self.kb_status[0][0] = "Safe"

    def add_fact(self, pos: tuple[int, int], fact: str):
        """
        Adds a single atomic sentence (a fact) to the KB for a specific cell.

        Args:
            pos: The (x, y) coordinates of the cell.
            fact: The string representation of the fact to be added (e.g., F_NOT_WUMPUS).
        """
        x, y = pos
        if self._is_valid_coord(x, y):
            self.kb[x][y].add(fact)

    def get_facts(self, pos: tuple[int, int]) -> set[str]:
        """
        Retrieves the set of all known facts for a specific cell.

        Args:
            pos: The (x, y) coordinates of the cell.

        Returns:
            A set of strings, where each string is a fact about the cell.
        """
        return self.kb[pos[0]][pos[1]]

    def mark_visited(self, pos: tuple[int, int]):
        """
        Marks a cell as having been visited by the agent.
        A visited cell is, by definition, safe.

        Args:
            pos: The (x, y) coordinates of the cell.
        """
        x, y = pos
        self.visited[x][y] = True
        self.kb_status[x][y] = "Visited"
        self.add_fact(pos, F_SAFE)
        self.add_fact(pos, F_NOT_WUMPUS)
        self.add_fact(pos, F_NOT_PIT)

    def _is_valid_coord(self, x: int, y: int) -> bool:
        """A private helper to check if coordinates are within the grid boundaries."""
        return 0 <= x < self.N and 0 <= y < self.N

    def get_neighbors(self, pos: tuple[int, int]) -> list[tuple[int, int]]:
        """
        A utility method to get all valid neighbor coordinates for a given cell.
        This represents knowledge about the grid structure, not logical inference.

        Args:
            pos: The (x, y) coordinates of the cell.

        Returns:
            A list of valid (x, y) neighbor coordinates.
        """
        x, y = pos
        neighbors = []
        for dx, dy in DIRECTIONS:
            nx, ny = x + dx, y + dy
            if self._is_valid_coord(nx, ny):
                neighbors.append((nx, ny))
        return neighbors