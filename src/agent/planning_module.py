# src/agent/planning_module.py
from .agent_goal import AgentGoal
from utils.constants import (
    ACTION_GRAB, ACTION_SHOOT, ACTION_CLIMB_OUT,
    ACTION_TURN_LEFT, ACTION_TURN_RIGHT, DIRECTIONS,
    WUMPUS_MOVE_INTERVAL,
)
from .knowledge_base import (
    F_WUMPUS, F_DEAD_WUMPUS, F_POSSIBLE_WUMPUS, 
    F_HAS_STENCH, F_HAS_BREEZE
)
import random

class StrategicPlanner:
    """
    Responsible for converting a high-level strategic goal (AgentGoal) 
    into a low-level action plan (a list of actions).
    It uses a central decision-making function (_plan_to_get_unstuck) 
    when the agent is trapped to choose the least-worst option.
    """
    def __init__(self, pathfinding_module):
        self.pathfinder = pathfinding_module

    # Accept epoch info for time-aware planning.
    def create_plan(self, agent, goal, actions_in_current_epoch=0):
        """
        The main method that generates a plan based on the agent's current goal.
        """
        if goal == AgentGoal.RETURN_HOME:
            return self._plan_return_home(agent)
        elif goal == AgentGoal.EXPLORE_SAFELY:
            return self._plan_explore_safely(agent)
        elif goal == AgentGoal.GET_UNSTUCK:
            return self._plan_to_get_unstuck(agent, actions_in_current_epoch)
        elif goal == AgentGoal.ESCAPE:
            return self._plan_escape(agent)
        return None
    
    def _plan_return_home(self, agent):
        """Plans a path back to (0,0) to climb out."""
        if agent.agent_pos == (0, 0):
            return [ACTION_CLIMB_OUT]
        kb_status = agent.inference_module.get_kb_status()
        # When returning home, the agent can traverse known dangerous cells (e.g., a dead wumpus location).
        return self.pathfinder.find_path(agent.agent_pos, agent.agent_dir, (0, 0), kb_status, avoid_dangerous=False)

    def _plan_explore_safely(self, agent):
        """Plans a path to explore the nearest unvisited safe cells."""
        kb_status = agent.inference_module.get_kb_status()
        visited_cells = agent.inference_module.get_visited_cells()
        safe_unvisited_cells = [(x, y) for x in range(agent.N) for y in range(agent.N) if kb_status[x][y] == "Safe" and not visited_cells[x][y]]
        
        if not safe_unvisited_cells:
            return None
            
        # Sort safe cells by Manhattan distance to prioritize the closest ones.
        safe_unvisited_cells.sort(key=lambda p: abs(p[0] - agent.agent_pos[0]) + abs(p[1] - agent.agent_pos[1]))
        
        for target in safe_unvisited_cells:
            # Find a path that avoids all known and suspected dangers.
            path = self.pathfinder.find_path(agent.agent_pos, agent.agent_dir, target, kb_status, avoid_dangerous=True)
            if path:
                return path
        return None

    def _plan_escape(self, agent):
        """The last resort plan: try to get back to (0,0) at all costs."""
        if agent.agent_pos == (0, 0):
            return [ACTION_CLIMB_OUT]
        kb_status = agent.inference_module.get_kb_status()
        # Accept risks to escape.
        return self.pathfinder.find_path(agent.agent_pos, agent.agent_dir, (0, 0), kb_status, avoid_dangerous=False)

    # Accept epoch info to make time-aware decisions.
    def _plan_to_get_unstuck(self, agent, actions_in_current_epoch=0):
        """
        The supreme decision-making function for when the agent is trapped.
        It evaluates options (shooting vs. risky move) and selects the one with the highest "utility score".
        In moving wumpus mode, it penalizes long plans that might be interrupted.
        """
        options = []
        kb = agent.inference_module.kb
        kb_status = agent.inference_module.get_kb_status()
        actions_left_in_epoch = WUMPUS_MOVE_INTERVAL - actions_in_current_epoch

        # --- 1. GATHER ALL POSSIBLE SHOOTING OPTIONS ---
        if agent.agent_has_arrow:
            potential_targets = []
            for x in range(agent.N):
                for y in range(agent.N):
                    pos = (x, y)
                    facts = kb.get_facts(pos)
                    # A target is a cell that is confirmed or possibly a Wumpus, and not yet dead.
                    if (F_WUMPUS in facts or F_POSSIBLE_WUMPUS in facts) and F_DEAD_WUMPUS not in facts:
                        potential_targets.append(pos)
            
            for target in potential_targets:
                # Find safe shooting spots adjacent to the target.
                neighbors = kb.get_neighbors(target)
                safe_spots = [n for n in neighbors if kb_status[n[0]][n[1]] in ["Safe", "Visited"]]
                for spot in safe_spots:
                    path = self.pathfinder.find_path(agent.agent_pos, agent.agent_dir, spot, kb_status, avoid_dangerous=True)
                    if path is not None:
                        # Calculate a utility score for this shooting action.
                        utility = 0
                        if F_WUMPUS in kb.get_facts(target):
                            utility += 100  # High reward for a confirmed target.
                        else:  # F_POSSIBLE_WUMPUS
                            # Reward based on the number of Stench clues pointing to it.
                            utility += 10 * self._calculate_wumpus_likelihood_score(agent, target)
                        
                        utility -= len(path)  # Subtract the cost of travel.
                        
                        # Penalize plans that are likely to be interrupted.
                        if agent.is_moving_wumpus_mode and len(path) > actions_left_in_epoch:
                            utility -= 50 # Heavy penalty for interruption risk.
                        
                        options.append((utility, "shoot", (target, spot)))

        # --- 2. GATHER ALL RISKY MOVE OPTIONS ---
        unknown_cells = [(x, y) for x in range(agent.N) for y in range(agent.N) if kb_status[x][y] == "Unknown"]
        for target in unknown_cells:
            # Find a path that accepts risk.
            path = self.pathfinder.find_path(agent.agent_pos, agent.agent_dir, target, kb_status, avoid_dangerous=False)
            if path:
                # Calculate the utility (always negative) for this risky move.
                threat_score = self._calculate_threat_score(agent, target)
                utility = -50  # A large default penalty for taking a risk.
                utility -= 20 * threat_score  # Add penalties based on surrounding threats (Breeze, Stench).
                utility -= len(path)  # Subtract the cost of travel.
                
                # Penalize plans that are likely to be interrupted.
                if agent.is_moving_wumpus_mode and len(path) > actions_left_in_epoch:
                    utility -= 50 # Heavy penalty for interruption risk.
                
                options.append((utility, "move", path))

        # --- 3. COMPARE OPTIONS AND MAKE A DECISION ---
        if not options:
            return None  # Truly no options left.

        # Sort options by utility score in descending order.
        options.sort(key=lambda x: x[0], reverse=True)

        best_option = options[0]
        _, action_type, details = best_option

        if action_type == "shoot":
            # Construct the full shooting plan from the saved details.
            wumpus_pos, shooting_spot = details
            path_to_spot = self.pathfinder.find_path(agent.agent_pos, agent.agent_dir, shooting_spot, kb_status, avoid_dangerous=True)
            
            if path_to_spot is None: return None # Safety check.

            # Logic to turn and face the target.
            final_agent_dir = agent.agent_dir
            dir_idx = DIRECTIONS.index(agent.agent_dir)
            for action in path_to_spot:
                if action == ACTION_TURN_LEFT: dir_idx = (dir_idx - 1 + 4) % 4
                if action == ACTION_TURN_RIGHT: dir_idx = (dir_idx + 1) % 4
            final_agent_dir = DIRECTIONS[dir_idx]
            
            turns = []
            target_dir_vec = (wumpus_pos[0] - shooting_spot[0], wumpus_pos[1] - shooting_spot[1])
            if target_dir_vec not in DIRECTIONS: return None # Invalid shooting vector.

            while final_agent_dir != target_dir_vec:
                current_idx, target_idx = DIRECTIONS.index(final_agent_dir), DIRECTIONS.index(target_dir_vec)
                # Compare to find the shortest turn direction.
                if (target_idx - current_idx + 4) % 4 < (current_idx - target_idx + 4) % 4:
                    turns.append(ACTION_TURN_RIGHT)
                    final_agent_dir = DIRECTIONS[(current_idx + 1) % 4]
                else:
                    turns.append(ACTION_TURN_LEFT)
                    final_agent_dir = DIRECTIONS[(current_idx - 1 + 4) % 4]
            
            agent.last_shoot_dir = target_dir_vec # Crucial for processing the Scream percept.
            return path_to_spot + turns + [ACTION_SHOOT]

        elif action_type == "move":
            # The movement plan is already contained in 'details'.
            return details
            
        return None

    def _calculate_threat_score(self, agent, pos):
        """Calculates a threat score for an unknown cell based on percepts in neighboring cells."""
        score = 0
        kb = agent.inference_module.kb
        for neighbor in kb.get_neighbors(pos):
            # Check adjacent cells that have been visited.
            if kb.visited[neighbor[0]][neighbor[1]]:
                facts = kb.get_facts(neighbor)
                if F_HAS_STENCH in facts: score += 1
                if F_HAS_BREEZE in facts: score += 1
        return score

    def _calculate_wumpus_likelihood_score(self, agent, pos):
        """
        Calculates a simple heuristic score for the likelihood of a Wumpus at 'pos'.
        The score is based on the number of adjacent, visited cells that have a stench.
        """
        score = 0
        kb = agent.inference_module.kb
        # Look at the neighbors of the suspected cell 'pos'.
        for neighbor_of_pos in kb.get_neighbors(pos):
            # If we have visited that neighbor...
            if kb.visited[neighbor_of_pos[0]][neighbor_of_pos[1]]:
                # ...and that neighbor has the 'HasStench' fact...
                if F_HAS_STENCH in kb.get_facts(neighbor_of_pos):
                    score += 1  # ...increase the confidence score.
        return score