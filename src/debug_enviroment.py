# src/debug_environment.py

from environment.environment import WumpusWorldEnvironment
from utils.constants import WUMPUS_SYMBOL, PIT_SYMBOL, GOLD_SYMBOL

class DebugWumpusWorldEnvironment(WumpusWorldEnvironment):
    """
    An environment class used for debugging specific map layouts.
    It overrides the map generation to always return a predefined map,
    ignoring the N, K, p parameters passed during initialization.
    
    This specific map is designed to replicate the scenario where the agent
    loses with a score of -1039.
    """
    def _initialize_game(self):
        """
        Overrides the game initialization to use a fixed, hard-coded map
        instead of a randomly generated one.
        """
        # Call the parent's initialization first to set up agent state, etc.
        super()._initialize_game()

        # Define the fixed map layout.
        # This map is an exact replica of the "True Map" from the screenshot.
        N = 6  # The size of this specific map is 6x6
        self.N = N
        
        # Create an empty map of the correct size
        self.game_map = [[set() for _ in range(N)] for _ in range(N)]

        # --- Place items according to the "True Map" from the screenshot ---

        # Pits (P)
        self.game_map[0][5].add(PIT_SYMBOL)
        self.game_map[4][1].add(PIT_SYMBOL)
        self.game_map[5][3].add(PIT_SYMBOL)

        # Wumpus (W)
        self.game_map[1][3].add(WUMPUS_SYMBOL)

        # Gold (G)
        self.game_map[1][4].add(GOLD_SYMBOL)

        # Reset agent to the starting position for this specific test case
        self.agent_pos = (0, 0) # Agent starts at (0,0) as usual
        self.agent_dir_idx = 1 # Facing East