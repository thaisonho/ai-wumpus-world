# wumpus_world/agent/agent.py

from .inference_module import InferenceModule 
from .pathfinding_module import PathfindingModule # Class name changed
from .planning_module import StrategicPlanner    # New strategic module
from .agent_goal import AgentGoal                # Enum in a separate file


from utils.constants import N_DEFAULT, K_DEFAULT, PERCEPT_GLITTER, ACTION_MOVE_FORWARD, ACTION_TURN_LEFT, ACTION_TURN_RIGHT, ACTION_SHOOT, ACTION_GRAB, ACTION_CLIMB_OUT
from utils.constants import DIRECTIONS, EAST


class WumpusWorldAgent:
    """
    A multi-strategy agent that acts as a high-level 'Director', making strategic decisions.
    Detailed action planning is delegated to the StrategicPlanner.
    """
    def __init__(self, N=N_DEFAULT, K=K_DEFAULT):
        self.N = N
        self.K = K
        # Functional modules owned by the Agent
        self.inference_module = InferenceModule(N, K)
        self.pathfinding_module = PathfindingModule(N)
        self.strategic_planner = StrategicPlanner(self.pathfinding_module)

        # Physical state of the agent
        self.agent_pos, self.agent_dir = (0, 0), EAST
        self.agent_has_gold, self.agent_has_arrow = False, True
        self.score = 0

        # Planning and goal state
        self.path_to_follow = []
        self.current_goal = AgentGoal.EXPLORE_SAFELY
        self.last_action, self.last_shoot_dir = None, None

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
        # 1. THINK: Update the knowledge base with new information.
        self.inference_module.update_knowledge(self.agent_pos, percepts, self.last_action, self.last_shoot_dir)

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
            return ACTION_GRAB

        # 3. EXECUTE PLAN: If a valid plan exists, follow it.
        if self.path_to_follow:
            self.last_action = self.path_to_follow.pop(0)
            return self.last_action

        # 4. DECIDE & RE-PLAN: If there's no active plan, determine a new goal and create a plan.
        self._determine_next_goal()
        new_path = self.strategic_planner.create_plan(self, self.current_goal)

        if new_path:
            self.path_to_follow = new_path
            self.last_action = self.path_to_follow.pop(0)
            return self.last_action

        # 5. FALLBACK ACTION: If all else fails, perform a default action.
        # This prevents the agent from getting stuck. Climb if at the start, otherwise turn.
        self.last_action = ACTION_CLIMB_OUT if self.agent_pos == (0, 0) else ACTION_TURN_RIGHT
        return self.last_action

    def _determine_next_goal(self):
        """Strategically determines the next high-level goal based on the agent's current state and knowledge."""
        if self.agent_has_gold:
            self.current_goal = AgentGoal.RETURN_HOME
            return

        kb_status = self.inference_module.get_kb_status()
        visited_cells = self.inference_module.get_visited_cells()
        safe_unvisited_cells = [(x, y) for x in range(self.N) for y in range(self.N) if kb_status[x][y] == "Safe" and not visited_cells[x][y]]

        # Priority 1: If there are guaranteed safe cells to explore, do that.
        if safe_unvisited_cells:
            self.current_goal = AgentGoal.EXPLORE_SAFELY
        else:
            # Priority 2: If there are no safe options, the agent is "stuck".
            # Delegate the hard choice (shoot vs. risky move) to the planner.
            self.current_goal = AgentGoal.GET_UNSTUCK
            
        # Safeguard: If the planner can't find a way to get unstuck, the final goal is to escape.
        # This check is done to ensure we always have a goal if GET_UNSTUCK returns no plan.
        plan = self.strategic_planner.create_plan(self, self.current_goal)
        if not plan:
            self.current_goal = AgentGoal.ESCAPE

    def get_known_map(self):
        """Returns the map of definitively known items (Wumpus, Pit, Gold)."""
        return self.inference_module.get_known_map()

    def get_kb_status(self):
        """Returns the map of inferred cell statuses (Safe, Dangerous, etc.)."""
        return self.inference_module.get_kb_status()