# wumpus_world/environment/map_generator.py

import random
from utils.constants import (
    WUMPUS_SYMBOL,
    PIT_SYMBOL,
    GOLD_SYMBOL,
    EMPTY_CELL_SYMBOL,
    N_DEFAULT,
    K_DEFAULT,
    P_DEFAULT,
)


class MapGenerator:
    def __init__(self, N=N_DEFAULT, K=K_DEFAULT, p=P_DEFAULT):
        self.N = N
        self.K = K
        self.p = p

    def generate_map(self):
        """
        Generates a random N x N Wumpus World map.
        The map is represented as a 2D list (grid[x][y]) where each cell
        contains a set of symbols representing its contents.
        """
        # Initialize an empty N x N grid
        # Each cell will store a set of elements (e.g., {WUMPUS_SYMBOL, PIT_SYMBOL})
        game_map = [[set() for _ in range(self.N)] for _ in range(self.N)]

        # List of all possible cell coordinates (excluding (0,0) for Wumpus/Pit placement)
        possible_coords = [(x, y) for x in range(self.N) for y in range(self.N)]

        # (0,0) is always safe [1]
        safe_start_cell = (0, 0)
        if safe_start_cell in possible_coords:
            possible_coords.remove(safe_start_cell)

        # 1. Place Wumpuses [1]
        wumpus_coords = random.sample(possible_coords, self.K)
        for wx, wy in wumpus_coords:
            game_map[wx][wy].add(WUMPUS_SYMBOL)
            # Remove wumpus_coords from possible_coords for pit/gold placement
            # to ensure no overlap with pits/gold in the same cell [1]
            if (
                wx,
                wy,
            ) in possible_coords:  # Check needed as it might have been removed if it was (0,0)
                possible_coords.remove((wx, wy))

        # 2. Place Pits [1]
        # Pits appear with probability p in cells (excluding (0,0) and wumpus cells)
        pit_coords = []
        for px, py in possible_coords:  # Iterate over remaining possible_coords
            if random.random() < self.p:
                game_map[px][py].add(PIT_SYMBOL)
                pit_coords.append((px, py))

        # Remove pit_coords from possible_coords for gold placement
        for pc in pit_coords:
            if pc in possible_coords:
                possible_coords.remove(pc)

        # 3. Place Gold [1]
        # Exactly one gold, placed randomly in a cell without pit or wumpus.
        # Gold can appear at any cell, including (0,0) [1].
        # If (0,0) was removed from possible_coords, add it back for gold consideration
        if safe_start_cell not in possible_coords:
            possible_coords.append(safe_start_cell)

        # Ensure there's at least one valid spot for gold
        if not possible_coords:
            # This case should ideally not happen with default N=8, K=2, p=0.2
            # but as a fallback, place gold in (0,0) if no other safe spot
            gold_x, gold_y = safe_start_cell
        else:
            gold_x, gold_y = random.choice(possible_coords)

        game_map[gold_x][gold_y].add(GOLD_SYMBOL)

        return game_map
