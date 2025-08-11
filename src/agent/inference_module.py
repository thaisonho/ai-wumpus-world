# wumpus_world/agent/inference_module.py

from utils.constants import (
    N_DEFAULT,
    K_DEFAULT,
    PERCEPT_STENCH,
    PERCEPT_BREEZE,
    PERCEPT_GLITTER,
    PERCEPT_SCREAM,
    ACTION_MOVE_FORWARD,
    WUMPUS_SYMBOL,
    PIT_SYMBOL,
    GOLD_SYMBOL,
    DIRECTIONS,
)

# --- Atomic Sentences/Facts representation in the KB sets ---
# Using strings for clarity in the knowledge base sets
# Positive facts
F_WUMPUS = "W"
F_PIT = "P"
F_GOLD = "G"
F_SAFE = "S"
# Negative facts (negations)
F_NOT_WUMPUS = "-W"
F_NOT_PIT = "-P"
# Tentative facts (possibilities)
F_POSSIBLE_WUMPUS = "W?"
F_POSSIBLE_PIT = "P?"


class KnowledgeBase:
    """
    Là "bộ não" chứa kiến thức. Nó trả lời câu hỏi: "Agent biết những gì?"
    KB chứa các atomic sentences được thể hiện bằng ma trận các trạng thái của ô.
    """
    def __init__(self, N=N_DEFAULT, K=K_DEFAULT):
        self.N = N
        self.initial_wumpus_count = K
        self.known_wumpus_count = K  # Agent's belief about live Wumpuses
        self.gold_found_at = None

        # kb: Detailed knowledge, stores atomic sentences (facts) for each cell.
        # e.g., {'-W', '-P', 'S'} means the cell is known to be Not a Wumpus, Not a Pit, and is Safe.
        self.kb = [[set() for _ in range(self.N)] for _ in range(self.N)]
        
        # kb_status: High-level summary for the planning module and display.
        self.kb_status = [["Unknown" for _ in range(self.N)] for _ in range(self.N)]
        self.visited = [[False for _ in range(self.N)] for _ in range(self.N)]

        # Rule 5: Ràng buộc về ô xuất phát.
        # Ô (0,0) luôn an toàn, nghĩa là ~P(0,0) ^ ~W(0,0).
        self.add_fact((0, 0), F_NOT_PIT)
        self.add_fact((0, 0), F_NOT_WUMPUS)
        self.add_fact((0, 0), F_SAFE)
        self.kb_status[0][0] = "Safe"

    def add_fact(self, pos, fact):
        """Adds a single atomic sentence (fact) to the KB for a given position."""
        x, y = pos
        if self._is_valid_coord(x, y):
            self.kb[x][y].add(fact)

    def get_facts(self, pos):
        """Returns the set of facts for a given position."""
        x, y = pos
        return self.kb[x][y]

    def mark_visited(self, pos):
        x, y = pos
        self.visited[x][y] = True
        self.kb_status[x][y] = "Visited"
        self.add_fact(pos, F_SAFE) # A visited cell is definitionally safe.

    def _is_valid_coord(self, x, y):
        return 0 <= x < self.N and 0 <= y < self.N

    def _get_neighbors(self, x, y):
        neighbors = []
        for dx, dy in DIRECTIONS:
            nx, ny = x + dx, y + dy
            if self._is_valid_coord(nx, ny):
                neighbors.append((nx, ny))
        return neighbors

class InferenceEngine:
    """
    Là "cơ chế tư duy" để tạo ra kiến thức mới từ kiến thức đã có.
    Nó trả lời câu hỏi: "Agent suy luận như thế nào?".
    Sử dụng các quy tắc logic để suy luận mệnh đề mới và cập nhật lại KB.
    """
    def __init__(self, knowledge_base: KnowledgeBase):
        self.kb = knowledge_base

    def run_inference(self, current_pos, percepts, last_shoot_dir=None):
        """
        The main inference loop. It repeatedly applies logical rules to derive new knowledge
        until no more facts can be inferred. This simulates a forward chaining process.
        """
        x, y = current_pos
        
        # 1. Update direct knowledge from percepts at current_pos
        self._apply_percept_rules(current_pos, percepts)

        # 2. Handle special events (Scream)
        if PERCEPT_SCREAM in percepts:
            self._handle_scream(current_pos, last_shoot_dir)

        # 3. Iteratively apply deduction rules until knowledge base stabilizes
        while True:
            new_knowledge_derived = False
            for r in range(self.kb.N):
                for c in range(self.kb.N):
                    if self._apply_deduction_rules_for_cell((r, c)):
                        new_knowledge_derived = True
            
            if self._apply_global_constraint_rules():
                new_knowledge_derived = True

            if not new_knowledge_derived:
                break # KB is stable, no new inferences can be made in this cycle.
        
        # 4. Final update of high-level status map for the planner
        self._update_all_cell_statuses()

    def _apply_percept_rules(self, pos, percepts):
        """Applies rules based on the immediate percepts at the current location."""
        x, y = pos
        neighbors = self.kb._get_neighbors(x, y)

        # Rule 1 & 2 (Inverse): No Breeze/Stench implies safe neighbors
        # ~B(x,y) => ~P(neighbor) for all neighbors
        if PERCEPT_BREEZE not in percepts:
            for nx, ny in neighbors:
                self.kb.add_fact((nx, ny), F_NOT_PIT)
        # ~S(x,y) => ~W(neighbor) for all neighbors
        if PERCEPT_STENCH not in percepts:
            for nx, ny in neighbors:
                self.kb.add_fact((nx, ny), F_NOT_WUMPUS)
        
        # Rule 1 & 2 (Forward): Breeze/Stench implies possible danger
        # B(x,y) => P(n1) V P(n2) ...
        if PERCEPT_BREEZE in percepts:
            for nx, ny in neighbors:
                if not self.kb.visited[nx][ny]:
                    self.kb.add_fact((nx, ny), F_POSSIBLE_PIT)
        # S(x,y) => W(n1) V W(n2) ...
        if PERCEPT_STENCH in percepts:
             for nx, ny in neighbors:
                if not self.kb.visited[nx][ny]:
                    self.kb.add_fact((nx, ny), F_POSSIBLE_WUMPUS)

        # Rule 4: Glitter <=> Gold
        if PERCEPT_GLITTER in percepts:
            self.kb.add_fact(pos, F_GOLD)
            self.kb.gold_found_at = pos

    def _handle_scream(self, shooter_pos, shoot_dir):
        """Rule 9 & 10: Handles the 'Scream' percept and its consequences."""
        if self.kb.known_wumpus_count == 0:
            return # Should not happen if env is correct, but good practice

        self.kb.known_wumpus_count -= 1
        
        if shoot_dir:
            # Infer Wumpus location along the arrow's path
            wx, wy = shooter_pos
            while self.kb._is_valid_coord(wx, wy):
                wx += shoot_dir[0]
                wy += shoot_dir[1]
                if self.kb._is_valid_coord(wx, wy):
                     # The first non-visited or possibly dangerous cell is the most likely candidate
                    if not self.kb.visited[wx][wy] or F_WUMPUS in self.kb.get_facts((wx,wy)):
                        self.kb.add_fact((wx, wy), F_NOT_WUMPUS) # It's now dead
                        # Since Wumpus is dead, the cell is safe from Wumpus threat
                        self.kb.add_fact((wx, wy), F_SAFE) 
                        print(f"Inferred Wumpus at {(wx,wy)} is killed!")
                        break

    def _apply_deduction_rules_for_cell(self, pos):
        """
        Applies resolution-style logic for a single cell to determine if it's a definite Pit or Wumpus.
        This is the core of the reasoning process.
        """
        facts_added = False
        facts = self.kb.get_facts(pos)

        # Skip if already known
        if F_WUMPUS in facts or F_PIT in facts or F_SAFE in facts:
            return False

        # --- Try to prove Wumpus ---
        # If a cell (x,y) is a possible Wumpus, check all its visited neighbors.
        # If any neighbor (vx,vy) has a Stench, and ALL OTHER neighbors of (vx,vy) are known NOT to be Wumpus,
        # then (x,y) MUST be the Wumpus.
        if F_POSSIBLE_WUMPUS in facts:
            for nx, ny in self.kb._get_neighbors(pos[0], pos[1]):
                if self.kb.visited[nx][ny]: # Check from a visited (and thus known percept) cell
                    # Let's check if (nx,ny) had a stench percept implicitly
                    # This requires storing percepts, or more simply, using resolution
                    # Simple version: check neighbors of the neighbor
                    neighbors_of_neighbor = self.kb._get_neighbors(nx, ny)
                    unknown_neighbors = []
                    for non in neighbors_of_neighbor:
                        if F_NOT_WUMPUS not in self.kb.get_facts(non):
                            unknown_neighbors.append(non)
                    
                    # If this cell 'pos' is the ONLY possible source of the stench for neighbor (nx,ny)
                    if len(unknown_neighbors) == 1 and unknown_neighbors[0] == pos:
                        self.kb.add_fact(pos, F_WUMPUS)
                        facts_added = True
                        break # Found Wumpus, no need to check other neighbors

        # --- Try to prove Pit (same logic) ---
        if F_POSSIBLE_PIT in facts and not facts_added:
            for nx, ny in self.kb._get_neighbors(pos[0], pos[1]):
                if self.kb.visited[nx][ny]:
                    neighbors_of_neighbor = self.kb._get_neighbors(nx, ny)
                    unknown_neighbors = []
                    for non in neighbors_of_neighbor:
                        if F_NOT_PIT not in self.kb.get_facts(non):
                            unknown_neighbors.append(non)
                    
                    if len(unknown_neighbors) == 1 and unknown_neighbors[0] == pos:
                        self.kb.add_fact(pos, F_PIT)
                        facts_added = True
                        break
        
        # Rule 6: Ràng buộc về sự tồn tại duy nhất trong một ô
        if F_WUMPUS in self.kb.get_facts(pos):
             self.kb.add_fact(pos, F_NOT_PIT)
        if F_PIT in self.kb.get_facts(pos):
            self.kb.add_fact(pos, F_NOT_WUMPUS)

        # Rule 3: Quy tắc về sự an toàn
        if F_NOT_WUMPUS in self.kb.get_facts(pos) and F_NOT_PIT in self.kb.get_facts(pos):
            if F_SAFE not in self.kb.get_facts(pos):
                self.kb.add_fact(pos, F_SAFE)
                facts_added = True

        return facts_added

    def _apply_global_constraint_rules(self):
        """Applies world-wide constraints like the number of Wumpuses and Gold."""
        facts_added = False
        # Rule 7: Ràng buộc về số lượng Wumpus
        confirmed_wumpuses = []
        possible_wumpuses = []
        for r in range(self.kb.N):
            for c in range(self.kb.N):
                facts = self.kb.get_facts((r, c))
                if F_WUMPUS in facts:
                    confirmed_wumpuses.append((r,c))
                elif F_NOT_WUMPUS not in facts and not self.kb.visited[r][c]:
                    possible_wumpuses.append((r,c))

        # If we've found all the wumpuses, all other possible spots are safe from wumpuses.
        if len(confirmed_wumpuses) == self.kb.known_wumpus_count:
            for pos in possible_wumpuses:
                if F_NOT_WUMPUS not in self.kb.get_facts(pos):
                    self.kb.add_fact(pos, F_NOT_WUMPUS)
                    facts_added = True
        
        # Rule 8: Ràng buộc về số lượng Vàng
        if self.kb.gold_found_at:
            for r in range(self.kb.N):
                for c in range(self.kb.N):
                    if (r, c) != self.kb.gold_found_at:
                        if F_GOLD in self.kb.get_facts((r,c)): # Should not happen
                             self.kb.get_facts((r,c)).remove(F_GOLD)
        
        return facts_added

    def _update_all_cell_statuses(self):
        """Updates the high-level kb_status map based on the detailed facts in the KB."""
        for x in range(self.kb.N):
            for y in range(self.kb.N):
                if self.kb.visited[x][y]:
                    self.kb.kb_status[x][y] = "Visited"
                    continue

                facts = self.kb.get_facts((x, y))
                if F_SAFE in facts or (F_NOT_WUMPUS in facts and F_NOT_PIT in facts):
                    self.kb.kb_status[x][y] = "Safe"
                elif F_WUMPUS in facts or F_PIT in facts:
                    self.kb.kb_status[x][y] = "Dangerous"
                else:
                    self.kb.kb_status[x][y] = "Unknown"


class InferenceModule:
    """
    Module tích hợp chứa KnowledgeBase và InferenceEngine.
    Đây là giao diện chính mà Agent sẽ tương tác để cập nhật và truy vấn kiến thức.
    """
    def __init__(self, N=N_DEFAULT, K=K_DEFAULT):
        self.kb = KnowledgeBase(N, K)
        self.engine = InferenceEngine(self.kb)

    def update_knowledge(self, current_pos, percepts, last_action=None, last_shoot_dir=None):
        """
        Cập nhật toàn bộ kiến thức của agent dựa trên cảm nhận mới.
        """
        # 1. Mark current cell as visited and safe.
        self.kb.mark_visited(current_pos)
        self.kb.add_fact(current_pos, F_NOT_PIT)
        self.kb.add_fact(current_pos, F_NOT_WUMPUS)
        
        # 2. Run the inference engine to deduce new facts.
        self.engine.run_inference(current_pos, percepts, last_shoot_dir)

    # --- Methods for Agent/Planner to access knowledge ---
    
    def get_kb_status(self):
        """Returns the high-level status map for the planner."""
        return self.kb.kb_status

    def get_visited_cells(self):
        return self.kb.visited

    def get_known_map(self):
        """Returns a map for display purposes showing confirmed W, P, G."""
        known_map = [[set() for _ in range(self.kb.N)] for _ in range(self.kb.N)]
        for r in range(self.kb.N):
            for c in range(self.kb.N):
                facts = self.kb.get_facts((r, c))
                if F_WUMPUS in facts:
                    known_map[r][c].add(WUMPUS_SYMBOL)
                if F_PIT in facts:
                    known_map[r][c].add(PIT_SYMBOL)
                if F_GOLD in facts:
                    known_map[r][c].add(GOLD_SYMBOL)
        return known_map
    
    @property
    def possible_wumpus(self):
        """Derives possible wumpus locations from the KB."""
        possible = set()
        for x in range(self.kb.N):
            for y in range(self.kb.N):
                facts = self.kb.get_facts((x,y))
                if not self.kb.visited[x][y] and F_NOT_WUMPUS not in facts:
                    possible.add((x, y))
        return possible