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
    GOLD_SYMBOL,
    ACTION_SHOOT
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
        
        self.local_rules: list[Rule] = [
            SafetyFromNoThreatsRule(),
            ContradictionRule(),
        ]
        self.relational_rules: list[Rule] = [
            WumpusResolutionRule(),
            PitResolutionRule(),
        ]
        self.global_rule = GlobalWumpusCountRule()

    def _add_fact_to_kb(self, pos, fact, agenda, volatile=False):
        """Helper to add a fact and update the agenda if it's new."""
        # Check against all facts, but add with the correct volatility.
        if fact not in self.kb.get_facts(pos):
            self.kb.add_fact(pos, fact, volatile=volatile)
            agenda.append(pos)
            for neighbor in self.kb.get_neighbors(pos):
                agenda.append(neighbor)

    # Implement the knowledge reset logic.
    def clear_volatile_knowledge(self, is_moving_wumpus_mode=False):
        """Resets knowledge at the start of a new epoch."""
        for x in range(self.kb.N):
            for y in range(self.kb.N):
                pos = (x, y)
                # 1. Clear all temporary facts (from no-stench, shot misses, etc.)
                self.kb.drop_volatile_facts(pos)

                if not is_moving_wumpus_mode:
                    continue

                # 2. In moving mode, re-evaluate permanent facts
                permanent_facts = self.kb.kb[self.kb._pos_to_idx(pos)]['permanent']

                # 2a. Demote confirmed Wumpus to possible Wumpus
                if F_WUMPUS in permanent_facts and F_DEAD_WUMPUS not in permanent_facts:
                    self.kb.remove_fact(pos, F_WUMPUS)
                    self.kb.add_fact(pos, F_POSSIBLE_WUMPUS, volatile=True)

                # 2b. A cell's Wumpus-safety is no longer guaranteed, unless a Wumpus there is dead.
                # This correctly handles (0,0) as well.
                is_safe_from_wumpus = F_DEAD_WUMPUS in permanent_facts
                if not is_safe_from_wumpus:
                    if F_NOT_WUMPUS in permanent_facts:
                        self.kb.remove_fact(pos, F_NOT_WUMPUS)
                    if F_SAFE in permanent_facts:
                        self.kb.remove_fact(pos, F_SAFE)

    def run_inference_cycle(self, current_pos, percepts, last_action=None, last_shoot_dir=None, is_moving_wumpus_mode=True):
        """
        # AGENDA-BASED FORWARD-CHAINNING.
        1. Seeds the agenda with initial facts from percepts.
        2. Processes the agenda until it's empty, applying local and relational rules.
        3. Applies global rules once at the end.
        """

        agenda = deque([current_pos])

        # Handle Scream (permanent change)
        if PERCEPT_SCREAM in percepts:
            self._handle_scream_event(current_pos, last_shoot_dir, agenda)

        # Handle a missed shot. This provides VOLATILE information.
        elif last_action == ACTION_SHOOT:
            if last_shoot_dir:
                sx, sy = current_pos
                dx, dy = last_shoot_dir
                cx, cy = sx + dx, sy + dy
                while self.kb._is_valid_coord(cx, cy):
                    cell_to_clear = (cx, cy)
                    self._add_fact_to_kb(cell_to_clear, F_NOT_WUMPUS, agenda, volatile=True)
                    cx += dx
                    cy += dy

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

            # Conditionally apply the global rule.
            # This rule is unsound in a dynamic environment.
            if not is_moving_wumpus_mode:
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
            for n_pos in neighbors: 
                self._add_fact_to_kb(n_pos, F_NOT_WUMPUS, agenda, volatile=True)
        else:
            self._add_fact_to_kb(current_pos, F_HAS_STENCH, agenda, volatile=True)
            for n_pos in neighbors:
                 if F_NOT_WUMPUS not in self.kb.get_facts(n_pos):
                    self._add_fact_to_kb(n_pos, F_POSSIBLE_WUMPUS, agenda, volatile=True)

        if PERCEPT_BREEZE not in percepts:
            for n_pos in neighbors: self._add_fact_to_kb(n_pos, F_NOT_PIT, agenda, volatile=True)
        else:
            self._add_fact_to_kb(current_pos, F_HAS_BREEZE, agenda, volatile=True)
            for n_pos in neighbors:
                if F_NOT_PIT not in self.kb.get_facts(n_pos):
                    self._add_fact_to_kb(n_pos, F_POSSIBLE_PIT, agenda, volatile=True)

        if PERCEPT_GLITTER in percepts:
            self._add_fact_to_kb(current_pos, F_GOLD, agenda, volatile=True)
            self.kb.gold_found_at = current_pos

    def _handle_scream_event(self, shooter_pos, shoot_dir, agenda):
        if self.kb.known_wumpus_count == 0:
            return

        self.kb.known_wumpus_count = max(0, self.kb.known_wumpus_count - 1)

        if not shoot_dir:
            return

        candidates = []
        unknowns = []
        
        cx, cy = shooter_pos
        cx += shoot_dir[0]; cy += shoot_dir[1]

        while self.kb._is_valid_coord(cx, cy):
            pos = (cx, cy)
            facts = self.kb.get_facts(pos)
            
            if F_DEAD_WUMPUS not in facts:
                if F_WUMPUS in facts or F_POSSIBLE_WUMPUS in facts and F_SAFE not in facts:
                    candidates.append(pos)
                elif F_NOT_WUMPUS not in facts:
                    unknowns.append(pos)
            
            cx += shoot_dir[0]
            cy += shoot_dir[1]

        dead_wumpus_pos = None
        if candidates:
            dead_wumpus_pos = candidates[0]
        elif unknowns:
            dead_wumpus_pos = unknowns[0]
        
        if dead_wumpus_pos:
            facts = self.kb.get_facts(dead_wumpus_pos)
            
            facts.discard(F_WUMPUS)
            facts.discard(F_POSSIBLE_WUMPUS)

            self._add_fact_to_kb(dead_wumpus_pos, F_DEAD_WUMPUS, agenda)
            self._add_fact_to_kb(dead_wumpus_pos, F_SAFE, agenda)
            self._add_fact_to_kb(dead_wumpus_pos, F_NOT_WUMPUS, agenda)
            self._add_fact_to_kb(dead_wumpus_pos, F_NOT_PIT, agenda)

            self.kb.kb_status[dead_wumpus_pos[0]][dead_wumpus_pos[1]] = "Safe"
            
            self._explain_stenches_by_dead(dead_wumpus_pos, agenda)

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


# This class acts as a facade, so the agent doesn't need to know about the internal changes.
class InferenceModule:
    """
    Acts as the "Manager" and a "Facade" for the entire reasoning system.
    """
    def __init__(self, N=N_DEFAULT, K=K_DEFAULT):
        self.kb = KnowledgeBase(N, K)
        self.engine = InferenceEngine(self.kb)

    # Add the entry point for epoch transition logic.
    def on_new_epoch_starts(self, is_moving_wumpus_mode=False):
        """Called by the agent when a wumpus movement phase has passed."""
        self.engine.clear_volatile_knowledge(is_moving_wumpus_mode)
        self._update_kb_status_map() # Refresh the high-level map after clearing knowledge.

    # Accept the mode flag.
    def update_knowledge(self, current_pos, percepts, last_action=None, last_shoot_dir=None, is_moving_wumpus_mode=False):
        self.kb.mark_visited(current_pos)
        self.engine.run_inference_cycle(current_pos, percepts, last_action, last_shoot_dir, is_moving_wumpus_mode)
        self._update_kb_status_map()
    
    def _update_kb_status_map(self):
        for x in range(self.kb.N):
            for y in range(self.kb.N):
                pos = (x, y)
                if self.kb.visited[x][y]:
                    self.kb.kb_status[x][y] = "Visited"
                    continue
                facts = self.kb.get_facts(pos)
                if F_SAFE in facts or F_DEAD_WUMPUS in facts:
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