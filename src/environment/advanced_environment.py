# wumpus_world/environment/advanced_environment.py

from .environment import WumpusWorldEnvironment
from utils.constants import DIRECTIONS, SCORE_DIE
import random

class AdvancedWumpusWorldEnvironment(WumpusWorldEnvironment):
    def __init__(self, N, K, p):
        super().__init__(N, K, p)
        self.wumpus_move_counter = 0

    def apply_action(self, action):
        """
        Applies the agent's action and then moves the Wumpuses if it's time.
        """
        action_message = super().apply_action(action)
        
        self.wumpus_move_counter += 1
        if self.wumpus_move_counter >= 5:
            self.wumpus_move_counter = 0
            self._move_wumpuses()

        return action_message

    def _move_wumpuses(self):
        """
        Moves each Wumpus to a random adjacent cell that is not a pit,
        not occupied by another Wumpus, and not a wall.
        """
        new_wumpus_positions = set()
        
        for wx, wy in list(self.wumpus_pos): # Iterate over a copy
            possible_moves = []
            for dx, dy in DIRECTIONS:
                nx, ny = wx + dx, wy + dy
                if self._is_valid_coord(nx, ny) and \
                   (nx, ny) not in self.pit_pos and \
                   (nx, ny) not in self.wumpus_pos and \
                   (nx, ny) not in new_wumpus_positions:
                    possible_moves.append((nx, ny))
            
            if possible_moves:
                new_pos = random.choice(possible_moves)
                self.wumpus_pos.remove((wx, wy))
                self.wumpus_pos.add(new_pos)
                new_wumpus_positions.add(new_pos)

                # Check if Wumpus moved to agent's cell
                if new_pos == self.agent_pos:
                    self.game_state = "Lost"
                    self.score += SCORE_DIE
