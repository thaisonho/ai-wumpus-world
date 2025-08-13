# src/environment/map_generator.py

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
        It ensures the starting cell (0,0) and its adjacent cells (1,0), (0,1) are safe.
        """
        # Initialize an empty N x N grid. Each cell holds a set of symbols.
        game_map = [[set() for _ in range(self.N)] for _ in range(self.N)]

        # Create a list of all possible coordinates for placing items.
        possible_coords = [(x, y) for x in range(self.N) for y in range(self.N)]
        
        safe_starting_area = [(0, 0)]
        if self.N > 1:
            safe_starting_area.extend([(1, 0), (0, 1)])
        
        for coord in safe_starting_area:
            if coord in possible_coords:
                possible_coords.remove(coord)
        
        # 1. Place K Wumpuses randomly.
        # A cell with a Wumpus cannot also contain a Pit.
        
        num_wumpus_to_place = min(self.K, len(possible_coords))
        wumpus_coords = random.sample(possible_coords, num_wumpus_to_place)
        
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
        # The gold CAN be in the starting cell (0,0) as it's not a hazard.
        gold_possible_coords = [(x, y) for x in range(self.N) for y in range(self.N) 
                                if not game_map[x][y]] # Check for empty set
        
        if gold_possible_coords:
            gold_x, gold_y = random.choice(gold_possible_coords)
            game_map[gold_x][gold_y].add(GOLD_SYMBOL)
        else:
            # Fallback: if the map is full (very unlikely), place gold at (0,0).
            # This can happen if pits fill up every available cell.
            game_map[0][0].add(GOLD_SYMBOL)

        return game_map