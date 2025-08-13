"""Moving-Wumpus advanced environment.

This module extends the base environment so that after each fixed number of
agent actions, every Wumpus moves randomly to one adjacent valid cell.
"""

from .environment import WumpusWorldEnvironment
from utils.constants import (
    DIRECTIONS,
    WUMPUS_SYMBOL,
    PIT_SYMBOL,
    SCORE_DIE,
    GAME_STATE_PLAYING,
    GAME_STATE_LOST,
    WUMPUS_MOVE_INTERVAL,
)
import random


class AdvancedWumpusWorldEnvironment(WumpusWorldEnvironment):
    """Environment where Wumpuses move every fixed number of agent actions.

    Rules:
    - Count all agent actions (move/turn/grab/shoot/climb).
    - After each WUMPUS_MOVE_INTERVAL actions, move all Wumpuses:
        * Each Wumpus selects uniformly at random one valid adjacent cell
          among the 4 cardinal directions (N/E/S/W).
        * A valid cell is inside the grid, not a pit, and not occupied by
          another Wumpus (including those that already moved in this phase).
        * If a Wumpus moves onto the agent, the agent immediately loses.
    """

    def __init__(self, N, K, p, move_interval=WUMPUS_MOVE_INTERVAL, rng=None):
        super().__init__(N, K, p)
        self._move_interval = int(move_interval)
        self._actions_since_move = 0
        self._rng = rng if rng is not None else random.Random()

    def apply_action(self, action):
        """Run base logic, then possibly trigger the Wumpus movement phase."""
        action_message = super().apply_action(action)

        # If the game ended because of the agent's action, do not move Wumpuses
        if self.game_state != GAME_STATE_PLAYING:
            return action_message

        self._actions_since_move += 1
        if self._actions_since_move >= self._move_interval:
            self._actions_since_move = 0
            self._move_wumpuses()

        return action_message

    # -------------------- internal helpers --------------------

    def _current_wumpus_positions(self):
        """Collect all current Wumpus coordinates from the game map."""
        positions = []
        for x in range(self.N):
            for y in range(self.N):
                if WUMPUS_SYMBOL in self.game_map[x][y]:
                    positions.append((x, y))
        return positions

    def _is_inside(self, x, y):
        return 0 <= x < self.N and 0 <= y < self.N

    def _move_wumpuses(self):
        """Move all Wumpuses according to the movement rules described above."""
        current_positions = self._current_wumpus_positions()
        if not current_positions:
            return

        reserved_targets = set()

        for wx, wy in current_positions:
            # Skip if this Wumpus was already moved (cell no longer has a Wumpus)
            if WUMPUS_SYMBOL not in self.game_map[wx][wy]:
                continue

            candidate_moves = []
            for dx, dy in DIRECTIONS:  # DIRECTIONS is a list in [N, E, S, W] order
                nx, ny = wx + dx, wy + dy
                if not self._is_inside(nx, ny):
                    continue
                if PIT_SYMBOL in self.game_map[nx][ny]:
                    continue
                if WUMPUS_SYMBOL in self.game_map[nx][ny]:
                    continue
                if (nx, ny) in reserved_targets:
                    continue
                candidate_moves.append((nx, ny))

            if candidate_moves:
                new_x, new_y = self._rng.choice(candidate_moves)

                # Update map: move the Wumpus symbol
                self.game_map[wx][wy].discard(WUMPUS_SYMBOL)
                self.game_map[new_x][new_y].add(WUMPUS_SYMBOL)
                reserved_targets.add((new_x, new_y))

                # If a Wumpus steps onto the agent, it's game over immediately
                if (new_x, new_y) == self.agent_pos:
                    self.game_state = GAME_STATE_LOST
                    self.score += SCORE_DIE
                    break
