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
        self.game_map = None  # The actual hidden map
        self.agent_pos = (0, 0)
        self.agent_dir_idx = (
            1  # Start facing East (index 1 in DIRECTIONS: NORTH, EAST, SOUTH, WEST) [1]
        )
        self.agent_has_gold = False
        self.agent_has_arrow = True  # Agent starts with one arrow [1]
        self.score = 0
        self.game_state = GAME_STATE_PLAYING
        self.last_percepts = []
        self.scream_heard = False  # To track if a scream was heard in the previous turn

        self._initialize_game()

    def _initialize_game(self):
        """Initializes or resets the game state."""
        self.game_map = self.map_generator.generate_map()
        self.agent_pos = (0, 0)
        self.agent_dir_idx = 1  # East
        self.agent_has_gold = False
        self.agent_has_arrow = True
        self.score = 0
        self.game_state = GAME_STATE_PLAYING
        self.last_percepts = []
        self.scream_heard = False

        # Ensure (0,0) is safe after map generation (map_generator already handles this)
        # For robustness, we can double check here:
        if WUMPUS_SYMBOL in self.game_map[0][0] or PIT_SYMBOL in self.game_map[0][0]:
            # This should not happen if map_generator is correct, but as a safeguard:
            self.game_map[0][0].discard(WUMPUS_SYMBOL)
            self.game_map[0][0].discard(PIT_SYMBOL)
            # If gold was placed here, it's fine.

    def get_percepts(self):
        """
        Determines and returns the percepts for the agent's current cell.
        Percepts: Stench, Breeze, Glitter, Bump, Scream.
        """
        percepts = []
        x, y = self.agent_pos

        # Glitter: if gold is in the current cell [1]
        if GOLD_SYMBOL in self.game_map[x][y]:
            percepts.append(PERCEPT_GLITTER)

        # Stench: if one or more wumpuses are in adjacent cells [1]
        # Breeze: if one or more pits are in adjacent cells [1]
        for dx, dy in DIRECTIONS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.N and 0 <= ny < self.N:
                if WUMPUS_SYMBOL in self.game_map[nx][ny]:
                    percepts.append(PERCEPT_STENCH)
                if PIT_SYMBOL in self.game_map[nx][ny]:
                    percepts.append(PERCEPT_BREEZE)

        # Remove duplicates (e.g., if multiple wumpuses cause stench)
        percepts = list(set(percepts))

        # Add Scream if heard in the previous turn (after a Wumpus was killed)
        if self.scream_heard:
            percepts.append(PERCEPT_SCREAM)
            self.scream_heard = False  # Reset for next turn

        # Bump is handled directly by apply_action if agent hits a wall
        # We'll add it to percepts list there if it occurs.

        self.last_percepts = percepts
        return percepts

    def _check_game_over(self):
        """Checks if the game has ended (won or lost)."""
        x, y = self.agent_pos
        if WUMPUS_SYMBOL in self.game_map[x][y] or PIT_SYMBOL in self.game_map[x][y]:
            self.game_state = GAME_STATE_LOST
            self.score += SCORE_DIE
            return True
        return False

    def apply_action(self, action):
        """
        Applies the agent's action to the environment and updates state and score.
        Returns a message about the outcome.
        """
        message = ""
        self.scream_heard = False  # Reset scream for this turn

        if self.game_state != GAME_STATE_PLAYING:
            return "Game is already over."

        if action == ACTION_MOVE_FORWARD:
            self.score += SCORE_MOVE_FORWARD
            dx, dy = DIRECTIONS[self.agent_dir_idx]
            new_x, new_y = self.agent_pos[0] + dx, self.agent_pos[1] + dy

            if 0 <= new_x < self.N and 0 <= new_y < self.N:
                self.agent_pos = (new_x, new_y)
                message = f"Moved to ({new_x}, {new_y})."
            else:
                # Hit a wall [1]
                self.last_percepts.append(PERCEPT_BUMP)  # Add bump to current percepts
                message = "Bump! Hit a wall."

        elif action == ACTION_TURN_LEFT:
            self.score += SCORE_TURN
            self.agent_dir_idx = (self.agent_dir_idx - 1) % len(DIRECTIONS)
            message = "Turned left."

        elif action == ACTION_TURN_RIGHT:
            self.score += SCORE_TURN
            self.agent_dir_idx = (self.agent_dir_idx + 1) % len(DIRECTIONS)
            message = "Turned right."

        elif action == ACTION_GRAB:
            x, y = self.agent_pos
            if GOLD_SYMBOL in self.game_map[x][y]:
                self.agent_has_gold = True
                self.game_map[x][y].remove(GOLD_SYMBOL)  # Gold is removed from map
                self.score += SCORE_GRAB_GOLD
                message = "Grabbed the gold!"
            else:
                message = "Nothing to grab here."

        elif action == ACTION_SHOOT:
            self.score += SCORE_SHOOT
            if not self.agent_has_arrow:
                message = "No arrow left to shoot."
            else:
                self.agent_has_arrow = False
                message = "Shot an arrow."

                # Check for Wumpus hit in a straight line [1]
                dx, dy = DIRECTIONS[self.agent_dir_idx]
                current_x, current_y = self.agent_pos
                wumpus_killed = False

                # Arrow travels until it hits a wall or kills a Wumpus [1]
                while 0 <= current_x < self.N and 0 <= current_y < self.N:
                    if WUMPUS_SYMBOL in self.game_map[current_x][current_y]:
                        self.game_map[current_x][current_y].remove(WUMPUS_SYMBOL)
                        self.scream_heard = (
                            True  # Scream will be perceived next turn [2]
                        )
                        wumpus_killed = True
                        message += (
                            f" A Wumpus was killed at ({current_x}, {current_y})!"
                        )
                        break  # Arrow stops after hitting first Wumpus [1]
                    current_x += dx
                    current_y += dy

                if not wumpus_killed:
                    message += " The arrow flew into the void."

        elif action == ACTION_CLIMB_OUT:
            if self.agent_pos == (0, 0):
                if self.agent_has_gold:
                    self.score += SCORE_CLIMB_OUT_WITH_GOLD
                    self.game_state = GAME_STATE_WON
                    message = "Climbed out with the gold! You won!"
                else:
                    self.score += SCORE_CLIMB_OUT_WITHOUT_GOLD
                    self.game_state = (
                        GAME_STATE_WON  # Still a win condition, but no score
                    )
                    message = "Climbed out without the gold. Game over."
            else:
                message = "Can only climb out from (0,0)."

        else:
            message = "Invalid action."

        # Check for immediate death after action (e.g., moving into a Wumpus/Pit)
        if self._check_game_over():
            message = "You died! Game Over."

        return message

    def get_current_state(self):
        """Returns the current state of the environment for display/agent."""
        return {
            "game_map": self.game_map,  # For display, agent will have its own known_map
            "agent_pos": self.agent_pos,
            "agent_dir": DIRECTIONS[self.agent_dir_idx],
            "agent_has_gold": self.agent_has_gold,
            "agent_has_arrow": self.agent_has_arrow,  # ADDED THIS LINE
            "score": self.score,
            "game_state": self.game_state,
            "percepts": self.last_percepts,  # Percepts from the *previous* turn's action
        }
