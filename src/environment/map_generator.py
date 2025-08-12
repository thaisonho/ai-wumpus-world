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
        The map is a grid where each cell contains a set of items (Wumpus, Pit, Gold).
        It ensures the starting cell (0,0) is safe and places other items randomly.
        """
        # Initialize an empty N x N grid. Each cell holds a set of symbols.
        game_map = [[set() for _ in range(self.N)] for _ in range(self.N)]

        # Create a list of all possible coordinates for placing items, excluding the safe start.
        possible_coords = [(x, y) for x in range(self.N) for y in range(self.N)]
        possible_coords.remove((0, 0))
        
        # 1. Place K Wumpuses randomly.
        # A cell with a Wumpus cannot also contain a Pit.
        wumpus_coords = random.sample(possible_coords, self.K)
        for wx, wy in wumpus_coords:
            game_map[wx][wy].add(WUMPUS_SYMBOL)
            possible_coords.remove((wx, wy))

        # 2. Place Pits with probability p.
        # Pits cannot be in the same cell as a Wumpus.
        pit_coords = []
        for px, py in list(possible_coords): # Iterate over a copy
            if random.random() < self.p:
                game_map[px][py].add(PIT_SYMBOL)
                possible_coords.remove((px, py))
                pit_coords.append((px,py))

        # 3. Place one Gold in a random cell without a Pit or Wumpus.
        # The gold can be in the starting cell.
        gold_possible_coords = [(x, y) for x in range(self.N) for y in range(self.N) 
                                if not game_map[x][y]] # Check for empty set
        
        if gold_possible_coords:
            gold_x, gold_y = random.choice(gold_possible_coords)
            game_map[gold_x][gold_y].add(GOLD_SYMBOL)
        else:
            # Fallback: if the map is full (very unlikely), place gold at (0,0).
            game_map[0][0].add(GOLD_SYMBOL)

        return game_map
