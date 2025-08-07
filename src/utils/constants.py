# wumpus_world/utils/constants.py

# --- Game Defaults ---
N_DEFAULT = 8  # Default grid size (N x N) [1]
K_DEFAULT = 2  # Default number of Wumpuses [1]
P_DEFAULT = 0.2  # Default probability of a pit in a cell [1]

# --- Game Elements Symbols ---
AGENT_SYMBOL = "A"
WUMPUS_SYMBOL = "W"
PIT_SYMBOL = "P"
GOLD_SYMBOL = "G"
BREEZE_SYMBOL = "B"
STENCH_SYMBOL = "S"
GLITTER_SYMBOL = "*"  # Using * for glitter as G is for Gold
EMPTY_CELL_SYMBOL = "_"
WALL_SYMBOL = "#"  # For visualization if needed, though environment handles bumps [1]

# --- Percepts ---
PERCEPT_STENCH = "Stench"
PERCEPT_BREEZE = "Breeze"
PERCEPT_GLITTER = "Glitter"
PERCEPT_BUMP = "Bump"
PERCEPT_SCREAM = "Scream"

# --- Actions ---
ACTION_MOVE_FORWARD = "MoveForward"
ACTION_TURN_LEFT = "TurnLeft"
ACTION_TURN_RIGHT = "TurnRight"
ACTION_GRAB = "Grab"
ACTION_SHOOT = "Shoot"
ACTION_CLIMB_OUT = "ClimbOut"

# --- Directions ---
# Represented as (dx, dy) for coordinate changes
NORTH = (0, 1)
EAST = (1, 0)
SOUTH = (0, -1)
WEST = (-1, 0)

DIRECTIONS = [NORTH, EAST, SOUTH, WEST]  # Order matters for turning

# Mapping directions to symbols for display
DIRECTION_SYMBOLS = {NORTH: "^", EAST: ">", SOUTH: "v", WEST: "<"}

# --- Scores ---
SCORE_GRAB_GOLD = 10
SCORE_MOVE_FORWARD = -1
SCORE_TURN = -1  # Applies to both TurnLeft and TurnRight
SCORE_SHOOT = -10
SCORE_DIE = -1000  # Fall in pit or eaten by wumpus
SCORE_CLIMB_OUT_WITH_GOLD = 1000
SCORE_CLIMB_OUT_WITHOUT_GOLD = 0

# --- Game State ---
GAME_STATE_PLAYING = "Playing"
GAME_STATE_WON = "Won"
GAME_STATE_LOST = "Lost"
