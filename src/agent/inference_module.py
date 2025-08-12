# src/agent/inference_module.py
from collections import deque

from utils.constants import (
    N_DEFAULT, 
    K_DEFAULT, 
    PERCEPT_BREEZE, 
    PERCEPT_GLITTER, 
    PERCEPT_SCREAM, 
    PERCEPT_STENCH, 
    WUMPUS_SYMBOL, 
    PIT_SYMBOL, 
    GOLD_SYMBOL
)
from .knowledge_base import (
    KnowledgeBase, 
    F_WUMPUS, 
    F_PIT, 
    F_GOLD, 
    F_SAFE, 
    F_NOT_WUMPUS, 
    F_NOT_PIT, 
    F_POSSIBLE_WUMPUS, 
    F_POSSIBLE_PIT, 
    F_HAS_BREEZE, 
    F_HAS_STENCH, 
    F_DEAD_WUMPUS
)
from .rules import (
    Rule, 
    SafetyFromNoThreatsRule, 
    ContradictionRule, 
    WumpusResolutionRule, 
    PitResolutionRule, 
    GlobalWumpusCountRule
)

class InferenceEngine:
    """
    Represents the "Logic Processor" or the "Execution Engine".
    """
    def __init__(self, knowledge_base: KnowledgeBase):
        self.kb = knowledge_base
        
        # AGENDA-BASED REFACTOR: Rules are now categorized.
        self.local_rules: list[Rule] = [
            SafetyFromNoThreatsRule(),
            ContradictionRule(),
        ]
        self.relational_rules: list[Rule] = [
            WumpusResolutionRule(),
            PitResolutionRule(),
        ]
        self.global_rule = GlobalWumpusCountRule()

    def _add_fact_to_kb(self, pos, fact, agenda):
        """A helper to add a fact and update the agenda if the fact is new."""
        if fact not in self.kb.get_facts(pos):
            self.kb.add_fact(pos, fact)
            # Any change at 'pos' means we should re-evaluate 'pos' and its neighbors.
            agenda.append(pos)
            for neighbor in self.kb.get_neighbors(pos):
                agenda.append(neighbor)

    def run_inference_cycle(self, current_pos, percepts, last_shoot_dir=None):
        """
        # AGENDA-BASED FORWARD-CHAINNING.
        1. Seeds the agenda with initial facts from percepts.
        2. Processes the agenda until it's empty, applying local and relational rules.
        3. Applies global rules once at the end.
        """
        agenda = deque()

        # Step 1: Seed the agenda with the current location.
        agenda.append(current_pos)

        # Handle special events first, they might add facts and update the agenda.
        if PERCEPT_SCREAM in percepts:
            self._handle_scream_event(current_pos, last_shoot_dir, agenda)

        self._apply_percept_rules(current_pos, percepts, agenda)
        
        # Step 2: Process the agenda.
        while True:
            # Process local and relational rules until the agenda is locally stable.
            processed_this_loop = set()
            while agenda:
                pos_to_process = agenda.popleft()
                if pos_to_process in processed_this_loop:
                    continue
                processed_this_loop.add(pos_to_process)

                for rule in self.local_rules:
                    new_facts = rule.apply(self.kb, pos_to_process)
                    for pos, fact in new_facts:
                        self._add_fact_to_kb(pos, fact, agenda)
                
                for rule in self.relational_rules:
                    new_facts = rule.apply(self.kb, pos_to_process)
                    for pos, fact in new_facts:
                        self._add_fact_to_kb(pos, fact, agenda)

            # Now that local inference has stabilized, apply the global rule.
            new_global_facts = self.global_rule.apply(self.kb)
            for pos, fact in new_global_facts:
                self._add_fact_to_kb(pos, fact, agenda)

            # If the global rule produced new facts, the agenda is no longer empty,
            # and the outer loop will continue to process their consequences.
            # If the agenda is still empty, it means the KB is fully stable, so we break.
            if not agenda:
                break

    def _apply_percept_rules(self, current_pos, percepts, agenda):
        """Applies direct percept rules and seeds the agenda."""
        neighbors = self.kb.get_neighbors(current_pos)
        
        if PERCEPT_STENCH not in percepts:
            for n_pos in neighbors: self._add_fact_to_kb(n_pos, F_NOT_WUMPUS, agenda)
        else:
            self._add_fact_to_kb(current_pos, F_HAS_STENCH, agenda)
            for n_pos in neighbors:
                 if F_NOT_WUMPUS not in self.kb.get_facts(n_pos):
                    self._add_fact_to_kb(n_pos, F_POSSIBLE_WUMPUS, agenda)

        if PERCEPT_BREEZE not in percepts:
            for n_pos in neighbors: self._add_fact_to_kb(n_pos, F_NOT_PIT, agenda)
        else:
            self._add_fact_to_kb(current_pos, F_HAS_BREEZE, agenda)
            for n_pos in neighbors:
                if F_NOT_PIT not in self.kb.get_facts(n_pos):
                    self._add_fact_to_kb(n_pos, F_POSSIBLE_PIT, agenda)
            
        if PERCEPT_GLITTER in percepts:
            self._add_fact_to_kb(current_pos, F_GOLD, agenda)
            self.kb.gold_found_at = current_pos

    def _handle_scream_event(self, shooter_pos, shoot_dir, agenda):
        # If no living Wumpus left, nothing to do.
        if self.kb.known_wumpus_count == 0:
            return

        # We heard a scream: one living Wumpus has died. Decrement immediately.
        # (This ensures we account for the death even if we cannot localize.)
        self.kb.known_wumpus_count = max(0, self.kb.known_wumpus_count - 1)

        # If shooting direction unknown, we cannot localize — just return.
        if not shoot_dir:
            return

        # Start from the cell next to shooter.
        wx, wy = shooter_pos
        wx += shoot_dir[0]; wy += shoot_dir[1]

        localized = False
        while self.kb._is_valid_coord(wx, wy):
            pos = (wx, wy)
            facts = self.kb.get_facts(pos)

            # Candidate if this cell is NOT proven to be Wumpus-free and not already dead.
            # This treats unknown cells as potential real targets (correct for arrow semantics).
            if F_NOT_WUMPUS not in facts and F_DEAD_WUMPUS not in facts:
                # Localize the killed Wumpus here.
                self._add_fact_to_kb(pos, F_WUMPUS, agenda)
                self._add_fact_to_kb(pos, F_DEAD_WUMPUS, agenda)

                # Explain/remove stench where appropriate.
                self._explain_stenches_by_dead(pos, agenda)

                localized = True
                break

            wx += shoot_dir[0]
            wy += shoot_dir[1]

        if not localized:
            pass


    def _explain_stenches_by_dead(self, dead_pos, agenda):
        """
        When a Wumpus is confirmed dead, any stench percept in its neighboring
        visited cells that *cannot* be explained by any other still-possible source
        should be removed. We consider a grand-neighbor (neighbor of the visited)
        a potential source unless it is proven F_NOT_WUMPUS or proven dead.
        """
        for neighbor in self.kb.get_neighbors(dead_pos):
            facts = self.kb.get_facts(neighbor)
            if F_HAS_STENCH not in facts:
                continue

            # Determine if any other adjacent cell (excluding the dead_pos) could still explain the stench.
            other_potential_source_exists = False
            for grand_neighbor in self.kb.get_neighbors(neighbor):
                if grand_neighbor == dead_pos:
                    continue
                gn_facts = self.kb.get_facts(grand_neighbor)

                # If grand_neighbor is not proven Wumpus-free and not proven dead, it is still a possible source.
                if F_NOT_WUMPUS not in gn_facts and F_DEAD_WUMPUS not in gn_facts:
                    other_potential_source_exists = True
                    break

            # If no other potential sources remain, it is safe to remove F_HAS_STENCH.
            if not other_potential_source_exists:
                # safer to record an "explained" tag rather than permanently deleting,
                # but following your original design we remove and re-enqueue for re-eval.
                facts.remove(F_HAS_STENCH)
                agenda.append(neighbor)


# It acts as a facade, so the agent doesn't need to know about the internal changes.
class InferenceModule:
    """
    Acts as the "Manager" and a "Facade" for the entire reasoning system.
    """
    def __init__(self, N=N_DEFAULT, K=K_DEFAULT):
        self.kb = KnowledgeBase(N, K)
        self.engine = InferenceEngine(self.kb)

    def update_knowledge(self, current_pos, percepts, last_action=None, last_shoot_dir=None):
        self.kb.mark_visited(current_pos)
        self.engine.run_inference_cycle(current_pos, percepts, last_shoot_dir)
        self._update_kb_status_map()

    def _update_kb_status_map(self):
        for x in range(self.kb.N):
            for y in range(self.kb.N):
                pos = (x, y)
                if self.kb.visited[x][y]:
                    self.kb.kb_status[x][y] = "Visited"
                    continue
                facts = self.kb.get_facts(pos)
                if F_SAFE in facts:
                    self.kb.kb_status[x][y] = "Safe"
                elif (F_WUMPUS in facts and F_DEAD_WUMPUS not in facts) or F_PIT in facts:
                    self.kb.kb_status[x][y] = "Dangerous"
                else:
                    self.kb.kb_status[x][y] = "Unknown"

    def get_kb_status(self):
        return self.kb.kb_status

    def get_visited_cells(self):
        return self.kb.visited
    
    def get_known_map(self):
        known_map = [[set() for _ in range(self.kb.N)] for _ in range(self.kb.N)]
        for r in range(self.kb.N):
            for c in range(self.kb.N):
                facts = self.kb.get_facts((r, c))
                if F_WUMPUS in facts and F_DEAD_WUMPUS not in facts: 
                    known_map[r][c].add(WUMPUS_SYMBOL)
                if F_PIT in facts: 
                    known_map[r][c].add(PIT_SYMBOL)
                if F_GOLD in facts: 
                    known_map[r][c].add(GOLD_SYMBOL)
        return known_map
    
    @property
    def possible_wumpus(self):
        possible = set()
        for x in range(self.kb.N):
            for y in range(self.kb.N):
                facts = self.kb.get_facts((x,y))
                if not self.kb.visited[x][y] and F_NOT_WUMPUS not in facts and F_WUMPUS not in facts:
                    possible.add((x, y))
        return possible