# wumpus_world/environment/environment.py

import random
from environment.map_generator import MapGenerator
from utils.constants import (
    WUMPUS_SYMBOL,
    PIT_SYMBOL,
    GOLD_SYMBOL,
    PERCEPT_STENCH,
    PERCEPT_BREEZE,
    PERCEPT_GLITTER,
    PERCEPT_BUMP,
    PERCEPT_SCREAM,
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
    SCORE_GRAB_GOLD,
    SCORE_MOVE_FORWARD,
    SCORE_TURN,
    SCORE_SHOOT,
    SCORE_DIE,
    SCORE_CLIMB_OUT_WITH_GOLD,
    SCORE_CLIMB_OUT_WITHOUT_GOLD,
    GAME_STATE_PLAYING,
    GAME_STATE_WON,
    GAME_STATE_LOST,
)


class WumpusWorldEnvironment:
    def __init__(self, N, K, p):
        self.N = N
        self.K = K
        self.p = p
        self.map_generator = MapGenerator(N, K, p)
        self.game_map = None  # The true, hidden map of the world
        self.agent_pos = (0, 0)
        self.agent_dir_idx = 1  # Start facing East (index 1 in DIRECTIONS)
        self.agent_has_gold = False
        self.agent_has_arrow = True
        self.score = 0
        self.game_state = GAME_STATE_PLAYING
        self.last_percepts = []
        self.scream_heard_this_turn = False  # Tracks if a scream should be perceived

        self._initialize_game()

    def _initialize_game(self):
        """Sets up a new game board and resets all state variables."""
        self.game_map = self.map_generator.generate_map()
        self.agent_pos = (0, 0)
        self.agent_dir_idx = 1  # East
        self.agent_has_gold = False
        self.agent_has_arrow = True
        self.score = 0
        self.game_state = GAME_STATE_PLAYING
        self.last_percepts = []
        self.scream_heard_this_turn = False

    def get_percepts(self):
        """
        Gathers all percepts for the agent's current location.
        Percepts include Stench, Breeze, Glitter, Bump, and Scream.
        """
        percepts = set()
        x, y = self.agent_pos

        # Check for Glitter if gold is present.
        if GOLD_SYMBOL in self.game_map[x][y]:
            percepts.add(PERCEPT_GLITTER)

        # Check for Stench (near Wumpus) and Breeze (near Pit).
        for dx, dy in DIRECTIONS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.N and 0 <= ny < self.N:
                if WUMPUS_SYMBOL in self.game_map[nx][ny]:
                    percepts.add(PERCEPT_STENCH)
                if PIT_SYMBOL in self.game_map[nx][ny]:
                    percepts.add(PERCEPT_BREEZE)

        # A scream is perceived in the turn *after* a Wumpus is shot.
        if self.scream_heard_this_turn:
            percepts.add(PERCEPT_SCREAM)
            self.scream_heard_this_turn = False  # Reset after perception

        # Bump is added directly by apply_action when a wall is hit.
        # We convert the set to a list for consistent output.
        self.last_percepts = list(percepts)
        return self.last_percepts

    def _check_game_over(self):
        """Checks for game-ending conditions (falling in a pit or meeting a Wumpus)."""
        x, y = self.agent_pos
        if WUMPUS_SYMBOL in self.game_map[x][y] or PIT_SYMBOL in self.game_map[x][y]:
            self.score += SCORE_DIE
            self.game_state = GAME_STATE_LOST
            return True
        return False

    def apply_action(self, action):
        """
        Processes the agent's chosen action, updates the environment state,
        and returns a message describing the outcome.
        """
        if self.game_state != GAME_STATE_PLAYING:
            return "The game is over."

        message = ""
        # Reset bump percept for this action
        if PERCEPT_BUMP in self.last_percepts:
            self.last_percepts.remove(PERCEPT_BUMP)

        if action == ACTION_MOVE_FORWARD:
            self.score += SCORE_MOVE_FORWARD
            dx, dy = DIRECTIONS[self.agent_dir_idx]
            new_x, new_y = self.agent_pos[0] + dx, self.agent_pos[1] + dy

            if 0 <= new_x < self.N and 0 <= new_y < self.N:
                self.agent_pos = (new_x, new_y)
                message = f"Moved to {self.agent_pos}."
            else:
                self.last_percepts.append(PERCEPT_BUMP)
                message = "Bump! You hit a wall."

        elif action == ACTION_TURN_LEFT:
            self.score += SCORE_TURN
            self.agent_dir_idx = (self.agent_dir_idx - 1 + len(DIRECTIONS)) % len(DIRECTIONS)
            message = "Turned left."

        elif action == ACTION_TURN_RIGHT:
            self.score += SCORE_TURN
            self.agent_dir_idx = (self.agent_dir_idx + 1) % len(DIRECTIONS)
            message = "Turned right."

        elif action == ACTION_GRAB:
            if GOLD_SYMBOL in self.game_map[self.agent_pos[0]][self.agent_pos[1]]:
                self.agent_has_gold = True
                self.game_map[self.agent_pos[0]][self.agent_pos[1]].remove(GOLD_SYMBOL)
                print(f"Gold removed from environment at position {self.agent_pos}")
                self.score += SCORE_GRAB_GOLD
                message = "Success! You grabbed the gold."
            else:
                message = "There is nothing here to grab."

        elif action == ACTION_SHOOT:
            self.score += SCORE_SHOOT
            if not self.agent_has_arrow:
                message = "You have no arrow left."
            else:
                self.agent_has_arrow = False
                message = "You shot your arrow."
                
                # Check if the arrow hits a Wumpus.
                dx, dy = DIRECTIONS[self.agent_dir_idx]
                curr_x, curr_y = self.agent_pos
                
                while 0 <= curr_x < self.N and 0 <= curr_y < self.N:
                    if WUMPUS_SYMBOL in self.game_map[curr_x][curr_y]:
                        self.game_map[curr_x][curr_y].remove(WUMPUS_SYMBOL)
                        self.scream_heard_this_turn = True
                        message += " You hear a terrible scream!"
                        break  # Arrow hits the first Wumpus in its path.
                    curr_x += dx
                    curr_y += dy

        elif action == ACTION_CLIMB_OUT:
            if self.agent_pos == (0, 0):
                if self.agent_has_gold:
                    self.score += SCORE_CLIMB_OUT_WITH_GOLD
                    self.game_state = GAME_STATE_WON
                    message = "You climbed out with the gold. You win!"
                else:
                    self.score += SCORE_CLIMB_OUT_WITHOUT_GOLD
                    self.game_state = GAME_STATE_LOST # Climbing out without gold is a loss
                    message = "You climbed out without the gold. You lose."
            else:
                message = "You can only climb out from the starting cell (0,0)."

        # Check for death after the action is performed.
        self._check_game_over()
        
        return message

    def get_current_state(self):
        """Returns a dictionary of the current environment state for the agent."""
        return {
            "agent_pos": self.agent_pos,
            "agent_dir": DIRECTIONS[self.agent_dir_idx],
            "agent_has_gold": self.agent_has_gold,
            "agent_has_arrow": self.agent_has_arrow,
            "score": self.score,
            "game_state": self.game_state,
        }
    
    def get_true_map(self):
        """
        # Trả về bản đồ thực của môi trường để gỡ lỗi.
        """
        return self.game_map
