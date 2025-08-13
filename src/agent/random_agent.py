# src/agent/random_agent.py
import random
from utils.constants import (
    ACTION_MOVE_FORWARD, ACTION_TURN_LEFT, ACTION_TURN_RIGHT,
    ACTION_SHOOT, ACTION_GRAB, ACTION_CLIMB_OUT,
    PERCEPT_GLITTER, EAST
)

class RandomAgent:
    """
    A simple agent that makes random decisions.
    This agent serves as a baseline for performance comparison.
    """
    def __init__(self, N):
        self.N = N
        # Physical state of the agent
        self.agent_pos = (0, 0)
        self.agent_dir = EAST
        self.agent_has_gold = False
        self.agent_has_arrow = True
        self.score = 0
        
        # Keep track of visited cells to improve random exploration
        self.visited = [[False for _ in range(N)] for _ in range(N)]
        self.visited[0][0] = True  # Start position is visited

    def update_state(self, env_state):
        """Synchronizes the agent's internal state with the environment's state."""
        self.agent_pos = env_state["agent_pos"]
        self.agent_dir = env_state["agent_dir"]
        self.agent_has_gold = env_state["agent_has_gold"]
        self.agent_has_arrow = env_state["agent_has_arrow"]
        self.score = env_state["score"]
        
        # Update visited cells
        self.visited[self.agent_pos[0]][self.agent_pos[1]] = True

    def decide_action(self, percepts):
        """
        Decides the next action randomly but with some basic rules:
        1. Always grab gold when sensing glitter
        2. Return home when having gold
        3. Shoot when having arrow (with small probability)
        4. Otherwise move randomly
        """
        # Grabbing glitter is a reflex action
        if PERCEPT_GLITTER in percepts:
            return ACTION_GRAB
            
        # If agent has gold, try to get back to (0,0) to climb out
        if self.agent_has_gold and self.agent_pos == (0, 0):
            return ACTION_CLIMB_OUT
            
        # Generate a list of possible actions with weights
        actions = []
        weights = []
        
        # Always consider turning
        actions.extend([ACTION_TURN_LEFT, ACTION_TURN_RIGHT])
        weights.extend([1, 1])
        
        # Consider shooting with a small probability if arrow is available
        if self.agent_has_arrow:
            actions.append(ACTION_SHOOT)
            weights.append(0.1)  # Lower weight means less likely to shoot
            
        # Consider moving forward unless at edge
        next_x, next_y = self._get_forward_position()
        if self._is_valid_position(next_x, next_y):
            actions.append(ACTION_MOVE_FORWARD)
            
            # Give higher weight to unvisited cells to encourage exploration
            if not self.visited[next_x][next_y]:
                weights.append(5)  # Higher weight for unvisited cells
            else:
                weights.append(1)
        
        # If the agent has gold, try to return to (0,0)
        if self.agent_has_gold:
            # Determine if turning helps get closer to (0,0)
            x, y = self.agent_pos
            if x > 0 and self.agent_dir != (-1, 0):  # Need to go west
                if self.agent_dir == (0, 1):  # Facing north, turn left
                    weights[actions.index(ACTION_TURN_LEFT)] = 10
                elif self.agent_dir == (0, -1):  # Facing south, turn right
                    weights[actions.index(ACTION_TURN_RIGHT)] = 10
                elif self.agent_dir == (1, 0):  # Facing east, turn left or right
                    weights[actions.index(ACTION_TURN_LEFT)] = 5
                    weights[actions.index(ACTION_TURN_RIGHT)] = 5
            elif x < 0 and self.agent_dir != (1, 0):  # Need to go east
                if self.agent_dir == (0, 1):  # Facing north, turn right
                    weights[actions.index(ACTION_TURN_RIGHT)] = 10
                elif self.agent_dir == (0, -1):  # Facing south, turn left
                    weights[actions.index(ACTION_TURN_LEFT)] = 10
                elif self.agent_dir == (-1, 0):  # Facing west, turn left or right
                    weights[actions.index(ACTION_TURN_LEFT)] = 5
                    weights[actions.index(ACTION_TURN_RIGHT)] = 5
            elif y > 0 and self.agent_dir != (0, -1):  # Need to go south
                if self.agent_dir == (1, 0):  # Facing east, turn right
                    weights[actions.index(ACTION_TURN_RIGHT)] = 10
                elif self.agent_dir == (-1, 0):  # Facing west, turn left
                    weights[actions.index(ACTION_TURN_LEFT)] = 10
                elif self.agent_dir == (0, 1):  # Facing north, turn left or right
                    weights[actions.index(ACTION_TURN_LEFT)] = 5
                    weights[actions.index(ACTION_TURN_RIGHT)] = 5
            elif y < 0 and self.agent_dir != (0, 1):  # Need to go north
                if self.agent_dir == (1, 0):  # Facing east, turn left
                    weights[actions.index(ACTION_TURN_LEFT)] = 10
                elif self.agent_dir == (-1, 0):  # Facing west, turn right
                    weights[actions.index(ACTION_TURN_RIGHT)] = 10
                elif self.agent_dir == (0, -1):  # Facing south, turn left or right
                    weights[actions.index(ACTION_TURN_LEFT)] = 5
                    weights[actions.index(ACTION_TURN_RIGHT)] = 5
                    
        # Choose action based on weights
        if not actions:  # If no actions are available, turn right
            return ACTION_TURN_RIGHT
            
        chosen_action = random.choices(actions, weights=weights, k=1)[0]
        return chosen_action

    def _get_forward_position(self):
        """Calculate the position if the agent moves forward."""
        x, y = self.agent_pos
        dx, dy = self.agent_dir
        return x + dx, y + dy

    def _is_valid_position(self, x, y):
        """Check if a position is valid (within the grid)."""
        return 0 <= x < self.N and 0 <= y < self.N

    def get_known_map(self):
        """Returns an empty map since the random agent doesn't maintain a knowledge base."""
        return [[[] for _ in range(self.N)] for _ in range(self.N)]
        
    def get_kb_status(self):
        """Returns a map with only visited cells marked."""
        kb_status = [["Unknown" for _ in range(self.N)] for _ in range(self.N)]
        for x in range(self.N):
            for y in range(self.N):
                if self.visited[x][y]:
                    kb_status[x][y] = "Visited"
        return kb_status
