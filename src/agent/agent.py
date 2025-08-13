# src/agent/agent.py

from .inference_module import InferenceModule 
from .pathfinding_module import PathfindingModule # Class name changed
from .planning_module import StrategicPlanner    # New strategic module
from .agent_goal import AgentGoal                # Enum in a separate file


from utils.constants import N_DEFAULT, K_DEFAULT, PERCEPT_GLITTER, ACTION_MOVE_FORWARD, ACTION_TURN_LEFT, ACTION_TURN_RIGHT, ACTION_SHOOT, ACTION_GRAB, ACTION_CLIMB_OUT, DIRECTIONS, EAST, WUMPUS_MOVE_INTERVAL


class WumpusWorldAgent:
    """
    A multi-strategy agent that acts as a high-level 'Director', making strategic decisions.
    Detailed action planning is delegated to the StrategicPlanner.
    """
    def __init__(self, N=N_DEFAULT, K=K_DEFAULT, is_moving_wumpus_mode=False):
        self.N = N
        self.K = K
        self.is_moving_wumpus_mode = is_moving_wumpus_mode
        self.actions_in_current_epoch = 0
        
        # Functional modules owned by the Agent
        self.inference_module = InferenceModule(N, K)
        self.pathfinding_module = PathfindingModule(N)
        self.strategic_planner = StrategicPlanner(self.pathfinding_module)

        # Physical state of the agent
        self.agent_pos, self.agent_dir = (0, 0), EAST
        self.agent_has_gold, self.agent_has_arrow = False, True
        self.score = 0
        self.actions_in_current_epoch = 0

        # Planning and goal state
        self.path_to_follow = []
        self.current_goal = AgentGoal.EXPLORE_SAFELY
        self.last_action, self.last_shoot_dir = None, None
    
    def increment_epoch_counter(self):
        """Increments the action counter for the current epoch."""
        self.actions_in_current_epoch += 1

    def update_state(self, env_state):
        """Synchronizes the agent's internal state with the environment's state."""
        self.agent_pos = env_state["agent_pos"]
        self.agent_dir = env_state["agent_dir"]
        self.agent_has_gold = env_state["agent_has_gold"]
        self.agent_has_arrow = env_state["agent_has_arrow"]
        self.score = env_state["score"]

    def _simulate_first_forward_dest(self):
        """
        Simulates the actions in self.path_to_follow (without executing them)
        starting from (self.agent_pos, self.agent_dir) and returns the destination
        coordinate of the first ACTION_MOVE_FORWARD encountered.

        Returns:
            - (x,y) tuple: The cell that would be stepped into by the first MOVE.
            - "INVALID_SHOOT": If the plan expects a SHOOT but the agent has no arrow.
            - "INVALID_CLIMB": If the plan expects to CLIMB from a cell other than (0,0).
            - None: If there is no MOVE in the remaining plan (e.g., only turns).
        This function does NOT mutate the agent's state.
        """
        if not self.path_to_follow:
            return None

        dir_idx = DIRECTIONS.index(self.agent_dir)
        pos_x, pos_y = self.agent_pos

        for action in self.path_to_follow:
            if action == ACTION_TURN_LEFT:
                dir_idx = (dir_idx - 1) % len(DIRECTIONS)
            elif action == ACTION_TURN_RIGHT:
                dir_idx = (dir_idx + 1) % len(DIRECTIONS)
            elif action == ACTION_MOVE_FORWARD:
                d = DIRECTIONS[dir_idx]
                return (pos_x + d[0], pos_y + d[1])
            elif action == ACTION_SHOOT:
                # If the plan requires a shot but we're out of arrows, it's invalid.
                if not getattr(self, "agent_has_arrow", False):
                    return "INVALID_SHOOT"
                # A shoot action doesn't change position, so continue simulation.
            elif action == ACTION_CLIMB_OUT:
                # A climb action is only valid at the start.
                if self.agent_pos != (0,0):
                    return "INVALID_CLIMB"
            # Other actions like GRAB don't affect position/direction for this check.

        return None  # No ACTION_MOVE_FORWARD was found in the plan.

    def decide_action(self, percepts):
        """The main decision-making loop of the agent."""
        # Handle epoch transitions at the beginning of a decision cycle.
        if self.is_moving_wumpus_mode and self.actions_in_current_epoch >= WUMPUS_MOVE_INTERVAL:
            # A wumpus movement phase has just occurred. Reset knowledge.
            self.actions_in_current_epoch = 0
            self.inference_module.on_new_epoch_starts(is_moving_wumpus_mode=True)
            # print("DEBUG: New epoch started. Knowledge reset.")

        # 1. THINK: Update the knowledge base with new information.
        self.inference_module.update_knowledge(
            self.agent_pos, 
            percepts, 
            self.last_action, 
            self.last_shoot_dir, 
            self.is_moving_wumpus_mode
        )

        # The shooting direction is a one-time piece of information for the inference engine. Clear it after use.
        self.last_shoot_dir = None

        # 1b. VALIDATE: Check if the current plan is still valid given new knowledge.
        if self.path_to_follow:
            # Quick pre-check: if the very first action is SHOOT but we have no arrow, invalidate.
            if self.path_to_follow[0] == ACTION_SHOOT and not self.agent_has_arrow:
                self.path_to_follow = []
            else:
                # Simulate to find the destination of the first forward move.
                dest = self._simulate_first_forward_dest()

                if dest in ["INVALID_SHOOT", "INVALID_CLIMB"]:
                    # Plan depends on a precondition that is no longer met.
                    self.path_to_follow = []
                elif isinstance(dest, tuple):
                    # Ensure the next move's destination is still considered safe.
                    kb_status = self.inference_module.get_kb_status()
                    if not self.pathfinding_module._is_valid_coord(*dest) or kb_status[dest[0]][dest[1]] == "Dangerous":
                        # The path leads into known danger. Invalidate and force replan.
                        self.path_to_follow = []

        # 2. REFLEX: Handle high-priority, immediate actions.
        # Grabbing glitter is a non-negotiable, immediate action that overrides any plan.
        if PERCEPT_GLITTER in percepts:
            self.path_to_follow = []  
            self.last_action = ACTION_GRAB
            return self.last_action

        if self.agent_has_gold and not self.path_to_follow:
            path_home = self.strategic_planner.create_plan(self, AgentGoal.RETURN_HOME)
            if path_home:
                self.path_to_follow = path_home
            else:
                self.last_action = ACTION_CLIMB_OUT if self.agent_pos == (0, 0) else ACTION_TURN_RIGHT
                return self.last_action
            
        # 3. EXECUTE PLAN: If a valid plan exists, follow it.
        if self.path_to_follow:
            self.last_action = self.path_to_follow.pop(0)
            return self.last_action

        # 4. DECIDE & RE-PLAN: If there's no active plan, determine a new goal base on curent knowledge and create a plan.
        self._determine_next_goal()
        new_path = self.strategic_planner.create_plan(
            self, 
            self.current_goal, 
            self.actions_in_current_epoch
        )

        if new_path:
            self.path_to_follow = new_path
            self.last_action = self.path_to_follow.pop(0)
            return self.last_action

        # 5. FALLBACK ACTION
        self.last_action = ACTION_CLIMB_OUT if self.agent_pos == (0, 0) else ACTION_TURN_RIGHT
        return self.last_action

    def _determine_next_goal(self):
        """Strategically determines the next high-level goal based on the agent's current state and knowledge."""
        plan_to_explore = self.strategic_planner.create_plan(
            self,
            AgentGoal.EXPLORE_SAFELY,
            self.actions_in_current_epoch
        )
        if plan_to_explore:
            self.current_goal = AgentGoal.EXPLORE_SAFELY
            return

        plan_to_get_unstuck = self.strategic_planner.create_plan(
            self,
            AgentGoal.GET_UNSTUCK,
            self.actions_in_current_epoch
        )
        if plan_to_get_unstuck:
            self.current_goal = AgentGoal.GET_UNSTUCK
            return

        self.current_goal = AgentGoal.ESCAPE

    def get_known_map(self):
        """Returns the map of definitively known items (Wumpus, Pit, Gold)."""
        return self.inference_module.get_known_map()

    def get_kb_status(self):
        """Returns the map of inferred cell statuses (Safe, Dangerous, etc.)."""
        return self.inference_module.get_kb_status()