# wumpus_world/agent/agent.py

from .inference_agent import InferenceEngine
from .planning_module import PlanningModule
from utils.constants import (
    N_DEFAULT,
    K_DEFAULT,
    PERCEPT_STENCH,
    PERCEPT_BREEZE,
    PERCEPT_GLITTER,
    PERCEPT_SCREAM,
    PERCEPT_BUMP,
    ACTION_MOVE_FORWARD,
    ACTION_TURN_LEFT,
    ACTION_TURN_RIGHT,
    ACTION_GRAB,
    ACTION_SHOOT,
    ACTION_CLIMB_OUT,
    NORTH,
    EAST,
    SOUTH,
    WEST,
    DIRECTIONS,
    WUMPUS_SYMBOL,
    PIT_SYMBOL,
    GOLD_SYMBOL,
)
import random


class WumpusWorldAgent:
    def __init__(self, N=N_DEFAULT, K=K_DEFAULT):
        self.N = N
        self.K = K
        self.inference_engine = InferenceEngine(N, K)
        self.planning_module = PlanningModule(N)

        self.agent_pos = (0, 0)
        self.agent_dir = EAST  # Start facing East
        self.agent_has_gold = False
        self.agent_has_arrow = True
        self.score = 0  # Agent's internal score tracking (should match env)

        self.path_to_follow = []  # List of actions from planning module
        self.last_action = None  # To help inference with Bump percept
        self.last_shoot_dir = None # To help with scream inference

    def update_state(self, env_state):
        """
        Updates the agent's internal state from the environment's state.
        This is for syncing agent's basic properties, not its KB.
        """
        self.agent_pos = env_state["agent_pos"]
        self.agent_dir = env_state["agent_dir"]
        self.agent_has_gold = env_state["agent_has_gold"]
        self.agent_has_arrow = env_state["agent_has_arrow"]
        self.score = env_state["score"]

    def update_knowledge(self, percepts):
        """
        Updates the agent's knowledge base using the inference engine.
        """
        # Pass last_action and whether it was successful (implied by no bump)
        # For bump, the environment adds PERCEPT_BUMP to percepts.
        self.inference_engine.update_knowledge(
            self.agent_pos,
            percepts,
            last_action=self.last_action,
            last_shoot_dir=self.last_shoot_dir,
        )

        # If scream, update internal Wumpus count/knowledge
        if PERCEPT_SCREAM in percepts:
            # A Wumpus was killed. If we track K, we'd decrement it.
            # For now, we just know one less Wumpus exists.
            # The planning module should avoid the square where the Wumpus was killed.
            # This is a simplification. A more advanced agent would use the shooting direction.
            pass

    def decide_action(self, percepts):
        """
        The agent's main decision-making logic.
        """
        # 1. Process percepts and update knowledge
        self.update_knowledge(percepts)

        # 2. Check for immediate actions
        if PERCEPT_GLITTER in percepts:
            self.last_action = ACTION_GRAB
            return ACTION_GRAB

        if self.agent_has_gold:
            if self.agent_pos == (0,0):
                self.last_action = ACTION_CLIMB_OUT
                return ACTION_CLIMB_OUT
            else:
                # Plan path back to (0,0)
                path_to_origin = self.planning_module.find_path(
                    self.agent_pos,
                    self.agent_dir,
                    (0, 0),
                    self.inference_engine.get_kb_status(),
                    self.inference_engine.get_visited_cells(),
                    avoid_dangerous=False, # May need to take risks to get home
                )
                if path_to_origin:
                    self.path_to_follow = path_to_origin
                    next_action = self.path_to_follow.pop(0)
                    self.last_action = next_action
                    return next_action

        if self.agent_pos == (0, 0) and self.agent_has_gold:
            self.last_action = ACTION_CLIMB_OUT
            return ACTION_CLIMB_OUT

        # 3. If a path is being followed, continue
        if self.path_to_follow:
            next_action = self.path_to_follow.pop(0)
            self.last_action = next_action
            return next_action

        # 4. Plan new actions
        # Prioritize exploring safe, unvisited cells
        safe_unvisited_cells = []
        for x in range(self.N):
            for y in range(self.N):
                if (
                    self.inference_engine.kb_status[x][y] == "Safe"
                    and not self.inference_engine.visited[x][y]
                ):
                    safe_unvisited_cells.append((x, y))

        # Try to find a path to the nearest safe, unvisited cell
        if safe_unvisited_cells:
            # Sort by Manhattan distance to current position
            safe_unvisited_cells.sort(
                key=lambda p: abs(p[0] - self.agent_pos[0])
                + abs(p[1] - self.agent_pos[1])
            )

            for target_cell in safe_unvisited_cells:
                path = self.planning_module.find_path(
                    self.agent_pos,
                    self.agent_dir,
                    target_cell,
                    self.inference_engine.get_kb_status(),
                    self.inference_engine.get_visited_cells(),
                    avoid_dangerous=True,  # Always avoid dangerous cells for exploration
                )
                if path:
                    self.path_to_follow = path
                    next_action = self.path_to_follow.pop(0)
                    self.last_action = next_action
                    return next_action

        # 5. If no safe unvisited cells, consider shooting or taking risks (advanced)
        # This is where the agent would decide to shoot a Wumpus or explore a dangerous path.
        if self.agent_has_arrow and self.inference_engine.possible_wumpus:
            # Find the most likely wumpus location
            # For now, just pick one from the possible locations
            target_wumpus = list(self.inference_engine.possible_wumpus)[0]
            
            # Plan path to a safe cell adjacent to the target wumpus to shoot from
            safe_shooting_spots = []
            for neighbor in self.inference_engine._get_neighbors(target_wumpus[0], target_wumpus[1]):
                if self.inference_engine.kb_status[neighbor[0]][neighbor[1]] == "Safe":
                    safe_shooting_spots.append(neighbor)
            
            if safe_shooting_spots:
                # Find the closest safe shooting spot
                safe_shooting_spots.sort(
                    key=lambda p: abs(p[0] - self.agent_pos[0])
                    + abs(p[1] - self.agent_pos[1])
                )
                shooting_spot = safe_shooting_spots[0]

                path_to_shoot = self.planning_module.find_path(
                    self.agent_pos,
                    self.agent_dir,
                    shooting_spot,
                    self.inference_engine.get_kb_status(),
                    self.inference_engine.get_visited_cells(),
                    avoid_dangerous=True,
                )

                if path_to_shoot:
                    # Now, plan the turn to face the wumpus and shoot
                    target_dir_x = target_wumpus[0] - shooting_spot[0]
                    target_dir_y = target_wumpus[1] - shooting_spot[1]
                    target_dir = (target_dir_x, target_dir_y)
                    
                    current_dir_at_shoot_spot = self.agent_dir
                    if path_to_shoot:
                        # This is a simplification, we need to know the direction at the end of the path
                        # For now, let's assume we can figure it out.
                        # A better way is to have find_path return the final direction.
                        pass

                    actions_to_turn = []
                    # This logic needs to be improved based on final direction after path
                    # For now, we'll just add the shoot action
                    
                    self.path_to_follow = path_to_shoot + [ACTION_SHOOT] # This needs more logic for turning
                    self.last_shoot_dir = target_dir
                    next_action = self.path_to_follow.pop(0)
                    self.last_action = next_action
                    return next_action

        # For now, a simple rule: if stench and has arrow, shoot in a random direction.
        if PERCEPT_STENCH in percepts and self.agent_has_arrow:
            # A more intelligent agent would infer Wumpus location and shoot precisely.
            # For now, just turn towards a random unvisited neighbor and shoot.
            neighbors = self.inference_engine._get_neighbors(
                self.agent_pos[0], self.agent_pos[1]
            )
            unvisited_neighbors = [
                n for n in neighbors if not self.inference_engine.visited[n[0]][n[1]]
            ]

            if unvisited_neighbors:
                target_neighbor = random.choice(unvisited_neighbors)
                # Calculate direction to target_neighbor
                target_dir_x = target_neighbor[0] - self.agent_pos[0]
                target_dir_y = target_neighbor[1] - self.agent_pos[1]
                target_dir = (target_dir_x, target_dir_y)

                # Plan turns to face target_dir
                current_dir_idx = DIRECTIONS.index(self.agent_dir)
                target_dir_idx = DIRECTIONS.index(target_dir)

                actions_to_turn = []
                if current_dir_idx != target_dir_idx:
                    diff = (target_dir_idx - current_dir_idx + 4) % 4
                    if diff == 1:  # Turn right
                        actions_to_turn.append(ACTION_TURN_RIGHT)
                    elif diff == 3:  # Turn left
                        actions_to_turn.append(ACTION_TURN_LEFT)
                    else:  # 2 turns (180 degrees), choose one
                        actions_to_turn.append(ACTION_TURN_RIGHT)
                        actions_to_turn.append(ACTION_TURN_RIGHT)

                if actions_to_turn:
                    self.path_to_follow = actions_to_turn + [ACTION_SHOOT]
                    self.last_shoot_dir = target_dir
                    next_action = self.path_to_follow.pop(0)
                    self.last_action = next_action
                    return next_action
            else:  # No unvisited neighbors, just shoot in current direction
                self.last_action = ACTION_SHOOT
                self.last_shoot_dir = self.agent_dir
                return ACTION_SHOOT

        # 6. If all else fails, return to (0,0) or take a random safe action
        # This is a fallback. A real agent would have more sophisticated risk assessment.
        if self.agent_pos != (0, 0):
            path_to_origin = self.planning_module.find_path(
                self.agent_pos,
                self.agent_dir,
                (0, 0),
                self.inference_engine.get_kb_status(),
                self.inference_engine.get_visited_cells(),
                avoid_dangerous=True,
            )
            if path_to_origin:
                self.path_to_follow = path_to_origin
                next_action = self.path_to_follow.pop(0)
                self.last_action = next_action
                return next_action

        # If no safe path, consider a risky one
        unvisited_cells = []
        for x in range(self.N):
            for y in range(self.N):
                if not self.inference_engine.visited[x][y]:
                    unvisited_cells.append((x,y))
        
        if unvisited_cells:
            unvisited_cells.sort(
                key=lambda p: abs(p[0] - self.agent_pos[0])
                + abs(p[1] - self.agent_pos[1])
            )
            target_cell = unvisited_cells[0]
            path = self.planning_module.find_path(
                self.agent_pos,
                self.agent_dir,
                target_cell,
                self.inference_engine.get_kb_status(),
                self.inference_engine.get_visited_cells(),
                avoid_dangerous=False,
            )
            if path:
                self.path_to_follow = path
                next_action = self.path_to_follow.pop(0)
                self.last_action = next_action
                return next_action

        # If absolutely no safe path or action, take a random safe move if possible
        # Or just stay put (no-op)
        safe_moves = []
        for action in [ACTION_MOVE_FORWARD, ACTION_TURN_LEFT, ACTION_TURN_RIGHT]:
            # Simulate action to check safety
            temp_x, temp_y = self.agent_pos
            temp_dir = self.agent_dir

            if action == ACTION_MOVE_FORWARD:
                move_dx, move_dy = temp_dir
                temp_x, temp_y = temp_x + move_dx, temp_y + move_dy
                if (
                    self.inference_engine._is_valid_coord(temp_x, temp_y)
                    and self.inference_engine.kb_status[temp_x][temp_y] == "Safe"
                ):
                    safe_moves.append(action)
            elif action == ACTION_TURN_LEFT:
                safe_moves.append(action)  # Turning is always safe
            elif action == ACTION_TURN_RIGHT:
                safe_moves.append(action)  # Turning is always safe

        if safe_moves:
            self.last_action = random.choice(safe_moves)
            return self.last_action

        # Last resort: if stuck, just turn to try to find new paths
        self.last_action = ACTION_TURN_RIGHT
        return ACTION_TURN_RIGHT

    def get_known_map(self):
        return self.inference_engine.get_known_map()

    def get_kb_status(self):
        return self.inference_engine.get_kb_status()
