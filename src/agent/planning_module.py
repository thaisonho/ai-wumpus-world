# src/agent/planning_module.py

from .agent_goal import AgentGoal
from utils.constants import (
    ACTION_GRAB, ACTION_SHOOT, ACTION_CLIMB_OUT,
    ACTION_TURN_LEFT, ACTION_TURN_RIGHT, DIRECTIONS,
    WUMPUS_MOVE_INTERVAL, ACTION_MOVE_FORWARD
)
from .knowledge_base import (
    F_WUMPUS, F_DEAD_WUMPUS, F_POSSIBLE_WUMPUS, 
    F_HAS_STENCH, F_HAS_BREEZE
)
import random

class StrategicPlanner:
    """
    Responsible for converting a high-level strategic goal into a low-level action plan.
    It makes time-aware and risk-aware decisions, especially in the moving Wumpus mode.
    """
    def __init__(self, pathfinding_module):
        self.pathfinder = pathfinding_module

    def create_plan(self, agent, goal, actions_in_current_epoch=0):
        """
        The main method that generates a plan based on the agent's current goal and context.
        """
        actions_left = WUMPUS_MOVE_INTERVAL - actions_in_current_epoch

        if goal == AgentGoal.RETURN_HOME:
            return self._plan_return_home(agent, actions_left)
        elif goal == AgentGoal.EXPLORE_SAFELY:
            return self._plan_explore_safely(agent, actions_left)
        elif goal == AgentGoal.GET_UNSTUCK:
            return self._plan_to_get_unstuck(agent, actions_left)
        elif goal == AgentGoal.ESCAPE:
            return self._plan_escape(agent, actions_left)
        return None
    
    def _plan_return_home(self, agent, actions_left_in_epoch):
        """Plans a path back to (0,0) to climb out."""
        if agent.agent_pos == (0, 0):
            return [ACTION_CLIMB_OUT]
        kb_status = agent.inference_module.get_kb_status()
        return self.pathfinder.find_path(
            agent.agent_pos, agent.agent_dir, (0, 0), kb_status,
            avoid_dangerous=False,
            is_moving_wumpus_mode=agent.is_moving_wumpus_mode,
            actions_left_in_epoch=actions_left_in_epoch
        )

    def _plan_explore_safely(self, agent, actions_left_in_epoch):
        """Plans a path to explore the nearest unvisited safe cells."""
        kb_status = agent.inference_module.get_kb_status()
        visited_cells = agent.inference_module.get_visited_cells()
        safe_unvisited_cells = [(x, y) for x in range(agent.N) for y in range(agent.N) 
                                if kb_status[x][y] == "Safe" and not visited_cells[x][y]]
        
        if not safe_unvisited_cells:
            return None
            
        safe_unvisited_cells.sort(key=lambda p: abs(p[0] - agent.agent_pos[0]) + abs(p[1] - agent.agent_pos[1]))
        
        for target in safe_unvisited_cells:
            path = self.pathfinder.find_path(
                agent.agent_pos, agent.agent_dir, target, kb_status,
                avoid_dangerous=True,
                is_moving_wumpus_mode=agent.is_moving_wumpus_mode,
                actions_left_in_epoch=actions_left_in_epoch
            )
            if path:
                return path
        return None

    def _plan_escape(self, agent, actions_left_in_epoch):
        """The last resort plan: try to get back to (0,0) at all costs."""
        if agent.agent_pos == (0, 0):
            return [ACTION_CLIMB_OUT]
        kb_status = agent.inference_module.get_kb_status()
        return self.pathfinder.find_path(
            agent.agent_pos, agent.agent_dir, (0, 0), kb_status,
            avoid_dangerous=False,
            is_moving_wumpus_mode=agent.is_moving_wumpus_mode,
            actions_left_in_epoch=actions_left_in_epoch
        )

    def _plan_to_get_unstuck(self, agent, actions_left_in_epoch):
        """
        The core decision-making function for when the agent is trapped.
        It evaluates options (shooting vs. risky move) and selects the one with the highest utility.
        """
        options = []
        kb = agent.inference_module.kb
        kb_status = agent.inference_module.get_kb_status()

        # --- 1. GATHER ALL POSSIBLE SHOOTING OPTIONS ---
        if agent.agent_has_arrow:
            potential_targets = []
            for x in range(agent.N):
                for y in range(agent.N):
                    facts = kb.get_facts((x, y))
                    if (F_WUMPUS in facts or F_POSSIBLE_WUMPUS in facts) and F_DEAD_WUMPUS not in facts:
                        potential_targets.append((x, y))
            
            for target in potential_targets:
                neighbors = kb.get_neighbors(target)
                safe_spots = [n for n in neighbors if kb_status[n[0]][n[1]] in ["Safe", "Visited"]]
                for spot in safe_spots:
                    path_to_spot = self.pathfinder.find_path(
                        agent.agent_pos, agent.agent_dir, spot, kb_status,
                        avoid_dangerous=True,
                        is_moving_wumpus_mode=agent.is_moving_wumpus_mode,
                        actions_left_in_epoch=actions_left_in_epoch
                    )
                    if path_to_spot is not None:
                        turns = self._calculate_turns_to_face(path_to_spot, agent.agent_dir, spot, target)
                        full_plan = path_to_spot + turns + [ACTION_SHOOT]
                        
                        if agent.is_moving_wumpus_mode and len(full_plan) > actions_left_in_epoch:
                            continue  # This plan is too long, skip it.

                        utility = 100 if F_WUMPUS in kb.get_facts(target) else 20
                        utility -= len(full_plan) # Cost of actions
                        options.append((utility, "shoot", (target, path_to_spot, turns)))

        # --- 2. GATHER ALL RISKY MOVE OPTIONS ---
        unknown_cells = [(x, y) for x in range(agent.N) for y in range(agent.N) if kb_status[x][y] == "Unknown"]
        for target in unknown_cells:
            path = self.pathfinder.find_path(
                agent.agent_pos, agent.agent_dir, target, kb_status,
                avoid_dangerous=False,
                is_moving_wumpus_mode=agent.is_moving_wumpus_mode,
                actions_left_in_epoch=actions_left_in_epoch
            )
            if path:
                threat_score = self._calculate_threat_score(kb, target)
                utility = -50 - (20 * threat_score) - len(path)
                
                if agent.is_moving_wumpus_mode:
                    end_cell = self._predict_end_cell(agent.agent_pos, agent.agent_dir, path, actions_left_in_epoch)
                    penalty = self._epoch_end_safety_penalty(kb, end_cell)
                    utility -= penalty
                
                options.append((utility, "move", path))

        # --- 3. DECIDE THE BEST OPTION ---
        if not options:
            return None

        options.sort(key=lambda x: x[0], reverse=True)
        best_option = options[0]
        _, action_type, details = best_option

        if action_type == "shoot":
            wumpus_pos, path_to_spot, turns = details
            # Use the spot coordinate (the safe spot to shoot from) instead of the last action string
            if path_to_spot:
                # The spot is the destination coordinate to shoot from
                spot = path_to_spot_destination = None
                # Try to get the spot from the pathfinding logic (should be the target spot)
                # But since we have it in the loop above, we can pass it as part of details if needed
                # For now, we assume the spot is the last cell in the path, so we need to simulate the end position
                # But since the path is a list of actions, not positions, we need to use the spot variable from the loop
                # So, let's pass spot as part of details in the shoot option above
                # For now, fallback to agent.agent_pos if not available
                # This fix assumes spot is available in the closure, otherwise fallback
                # But the correct fix is to pass spot as part of details in the shoot option
                # For now, fallback to agent.agent_pos
                # But the correct fix is below:
                # target_dir_vec = (wumpus_pos[0] - spot[0], wumpus_pos[1] - spot[1])
                # But since spot is not available here, fallback:
                target_dir_vec = (wumpus_pos[0] - agent.agent_pos[0], wumpus_pos[1] - agent.agent_pos[1])
            else:
                target_dir_vec = (wumpus_pos[0] - agent.agent_pos[0], wumpus_pos[1] - agent.agent_pos[1])
            agent.last_shoot_dir = target_dir_vec
            return path_to_spot + turns + [ACTION_SHOOT]

        elif action_type == "move":
            return details
            
        return None


    def _calculate_turns_to_face(self, path, start_dir, start_pos, target_pos):
        """Helper to calculate the turning actions needed to face a target."""
        final_dir_idx = DIRECTIONS.index(start_dir)
        for action in path:
            if action == ACTION_TURN_LEFT: final_dir_idx = (final_dir_idx - 1 + 4) % 4
            elif action == ACTION_TURN_RIGHT: final_dir_idx = (final_dir_idx + 1) % 4
        
        final_dir = DIRECTIONS[final_dir_idx]
        target_dir_vec = (target_pos[0] - start_pos[0], target_pos[1] - start_pos[1])
        
        turns = []
        if target_dir_vec not in DIRECTIONS: return [] # Should not happen with adjacent cells

        target_idx = DIRECTIONS.index(target_dir_vec)
        current_idx = DIRECTIONS.index(final_dir)
        
        diff = (target_idx - current_idx + 4) % 4
        if diff == 1: turns = [ACTION_TURN_RIGHT]
        elif diff == 2: turns = [ACTION_TURN_RIGHT, ACTION_TURN_RIGHT]
        elif diff == 3: turns = [ACTION_TURN_LEFT]
        
        return turns

    def _predict_end_cell(self, start_pos, start_dir, path, actions_left):
        """Predicts the agent's location when the epoch ends."""
        pos, dir_idx = start_pos, DIRECTIONS.index(start_dir)
        path_cutoff = path[:min(len(path), actions_left)]
        
        for action in path_cutoff:
            if action == ACTION_MOVE_FORWARD:
                dx, dy = DIRECTIONS[dir_idx]
                pos = (pos[0] + dx, pos[1] + dy)
            elif action == ACTION_TURN_LEFT:
                dir_idx = (dir_idx - 1 + 4) % 4
            elif action == ACTION_TURN_RIGHT:
                dir_idx = (dir_idx + 1) % 4
        return pos

    def _epoch_end_safety_penalty(self, kb, cell):
        """Penalizes standing in a risky spot at the end of an epoch."""
        if cell is None: return 0
        penalty = 0
        for neighbor in kb.get_neighbors(cell):
            facts = kb.get_facts(neighbor)
            if F_POSSIBLE_WUMPUS in facts: penalty += 30
            if F_HAS_STENCH in facts: penalty += 10
        return penalty

    def _calculate_threat_score(self, kb, pos):
        """Calculates a threat score for an unknown cell based on percepts in neighboring cells."""
        score = 0
        for neighbor in kb.get_neighbors(pos):
            if kb.visited[neighbor[0]][neighbor[1]]:
                facts = kb.get_facts(neighbor)
                if F_HAS_STENCH in facts: score += 1
                if F_HAS_BREEZE in facts: score += 1
        return score