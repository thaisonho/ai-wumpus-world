# src/agent/rules.py

from abc import ABC, abstractmethod
# MODIFIED: Imported new fact constants
from .knowledge_base import KnowledgeBase, F_WUMPUS, F_PIT, F_SAFE, F_NOT_WUMPUS, F_NOT_PIT, F_HAS_STENCH, F_HAS_BREEZE, F_DEAD_WUMPUS

class Rule(ABC):
    @abstractmethod
    def apply(self, kb: KnowledgeBase, pos: tuple[int, int]) -> list[tuple[tuple[int, int], str]]:
        pass
class SafetyFromNoThreatsRule(Rule):
    """A cell is definitively safe if it's known to contain neither a Wumpus NOR a Pit."""
    def apply(self, kb: KnowledgeBase, pos: tuple[int, int]) -> list[tuple[tuple[int, int], str]]:
        facts = kb.get_facts(pos)
        if F_NOT_WUMPUS in facts and F_NOT_PIT in facts:
            if F_SAFE not in facts:
                return [(pos, F_SAFE)]
        return []

class ContradictionRule(Rule):
    """A cell cannot contain both a Wumpus and a Pit."""
    def apply(self, kb: KnowledgeBase, pos: tuple[int, int]) -> list[tuple[tuple[int, int], str]]:
        new_facts = []
        facts = kb.get_facts(pos)
        if F_WUMPUS in facts and F_NOT_PIT not in facts:
            new_facts.append((pos, F_NOT_PIT))
        if F_PIT in facts and F_NOT_WUMPUS not in facts:
            new_facts.append((pos, F_NOT_WUMPUS))
        return new_facts

class WumpusResolutionRule(Rule):
    """
    Applies resolution logic for Wumpuses.
    A stench at a visited cell `pos` is caused by Wumpuses in adjacent cells.
    If we can account for all but one of the neighbors, we can make a new deduction.
    """
    def apply(self, kb: KnowledgeBase, pos: tuple[int, int]) -> list[tuple[tuple[int, int], str]]:
        new_facts = []
        pos_facts = kb.get_facts(pos)

        # CHECK 1: A stench at 'pos' might resolve an unknown neighbor.
        if kb.visited[pos[0]][pos[1]] and F_HAS_STENCH in pos_facts:
            neighbors = kb.get_neighbors(pos)
            
            # Find all neighbors that could POSSIBLY be the source of the stench.
            # A neighbor is a possible source if we haven't proven it's Wumpus-free.
            potential_sources = [
                n for n in neighbors
                if F_NOT_WUMPUS not in kb.get_facts(n)
            ]

            # If, after eliminating safe neighbors, there is only ONE possible source left,
            # then that source MUST be the Wumpus.
            if len(potential_sources) == 1:
                the_one = potential_sources[0]
                # Only add the fact if it's new information.
                if F_WUMPUS not in kb.get_facts(the_one):
                    new_facts.append((the_one, F_WUMPUS))

        # CHECK 2: 'pos' being safe (-W) might help resolve a stench in a neighbor.
        # This logic is for when new information about 'pos' (e.g., it's safe) is learned.
        if kb.visited[pos[0]][pos[1]] and F_NOT_WUMPUS in pos_facts:
            for neighbor in kb.get_neighbors(pos):
                # We only care about neighbors that we've visited and perceived a stench in.
                if kb.visited[neighbor[0]][neighbor[1]] and F_HAS_STENCH in kb.get_facts(neighbor):
                    # Now, re-evaluate from the neighbor's perspective.
                    other_neighbors = kb.get_neighbors(neighbor)
                    
                    potential_sources_for_neighbor = [
                        n for n in other_neighbors
                        if F_NOT_WUMPUS not in kb.get_facts(n)
                    ]
                    
                    if len(potential_sources_for_neighbor) == 1:
                        the_one = potential_sources_for_neighbor[0]
                        if F_WUMPUS not in kb.get_facts(the_one):
                            new_facts.append((the_one, F_WUMPUS))
                            
        return new_facts
        
class PitResolutionRule(Rule):
    """
    Applies resolution logic for pits.
    This is perfectly analogous to the WumpusResolutionRule.
    """
    def apply(self, kb: KnowledgeBase, pos: tuple[int, int]) -> list[tuple[tuple[int, int], str]]:
        new_facts = []
        pos_facts = kb.get_facts(pos)

        # CHECK 1: A breeze at 'pos' might resolve an unknown neighbor.
        if kb.visited[pos[0]][pos[1]] and F_HAS_BREEZE in pos_facts:
            neighbors = kb.get_neighbors(pos)
            
            potential_sources = [
                n for n in neighbors
                if F_NOT_PIT not in kb.get_facts(n)
            ]
            
            if len(potential_sources) == 1:
                the_one = potential_sources[0]
                if F_PIT not in kb.get_facts(the_one):
                    new_facts.append((the_one, F_PIT))

        # CHECK 2: 'pos' being pit-free (-P) might help resolve a breeze in a neighbor.
        if F_NOT_PIT in pos_facts:
            for neighbor in kb.get_neighbors(pos):
                if kb.visited[neighbor[0]][neighbor[1]] and F_HAS_BREEZE in kb.get_facts(neighbor):
                    other_neighbors = kb.get_neighbors(neighbor)
                    
                    potential_sources_for_neighbor = [
                        n for n in other_neighbors
                        if F_NOT_PIT not in kb.get_facts(n)
                    ]
                    
                    if len(potential_sources_for_neighbor) == 1:
                        the_one = potential_sources_for_neighbor[0]
                        if F_PIT not in kb.get_facts(the_one):
                            new_facts.append((the_one, F_PIT))

        return new_facts

class GlobalWumpusCountRule:
    """ This rule is inherently global and cannot be localized. """
    def apply(self, kb: KnowledgeBase) -> list[tuple[tuple[int, int], str]]:
        new_facts = []
        confirmed_living_wumpuses = []
        
        for x in range(kb.N):
            for y in range(kb.N):
                pos = (x, y)
                facts = kb.get_facts(pos)
                if F_WUMPUS in facts and F_DEAD_WUMPUS not in facts:
                    confirmed_living_wumpuses.append(pos)
        
        if len(confirmed_living_wumpuses) == kb.known_wumpus_count:
            for x in range(kb.N):
                for y in range(kb.N):
                    pos = (x, y)
                    facts = kb.get_facts(pos)
                    if pos not in confirmed_living_wumpuses and F_NOT_WUMPUS not in facts:
                        # Instead of kb.add_fact, append to the list to be returned.
                        new_facts.append((pos, F_NOT_WUMPUS))
        return new_facts