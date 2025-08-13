# src/utils/constants.py

# --- Game Configuration Defaults ---
N_DEFAULT = 8  # Default grid size (e.g., 8x8)
K_DEFAULT = 2  # Default number of Wumpuses
P_DEFAULT = 0.2  # Default probability of a pit in any given cell

# --- Map Symbols ---
AGENT_SYMBOL = "A"
WUMPUS_SYMBOL = "W"
PIT_SYMBOL = "P"
GOLD_SYMBOL = "G"
BREEZE_SYMBOL = "B"  # Note: Not directly displayed, but used in logic
STENCH_SYMBOL = "S"  # Note: Not directly displayed, but used in logic
EMPTY_CELL_SYMBOL = "_"
WALL_SYMBOL = "#"  # Used for displaying the map border

# --- Percepts ---
PERCEPT_STENCH = "Stench"
PERCEPT_BREEZE = "Breeze"
PERCEPT_GLITTER = "Glitter"
PERCEPT_BUMP = "Bump"
PERCEPT_SCREAM = "Scream"

# --- Agent Actions ---
ACTION_MOVE_FORWARD = "MoveForward"
ACTION_TURN_LEFT = "TurnLeft"
ACTION_TURN_RIGHT = "TurnRight"
ACTION_GRAB = "Grab"
ACTION_SHOOT = "Shoot"
ACTION_CLIMB_OUT = "ClimbOut"

# --- Directions ---
# Directions are represented as (dx, dy) tuples for coordinate changes.
# The order is important for turning logic (e.g., TurnLeft from North -> West).
NORTH = (0, 1)
EAST = (1, 0)
SOUTH = (0, -1)
WEST = (-1, 0)
DIRECTIONS = [NORTH, EAST, SOUTH, WEST]  # Order matters for turning

# Symbols for displaying the agent's direction
DIRECTION_SYMBOLS = {NORTH: "^", EAST: ">", SOUTH: "v", WEST: "<"}


# --- Scoring ---
SCORE_GRAB_GOLD = +10  # Score for successfully grabbing the gold
SCORE_MOVE_FORWARD = -1      # Cost for moving one step
SCORE_TURN = -1          # Cost for turning left or right
SCORE_SHOOT = -10        # Cost for using the arrow
SCORE_DIE = -1000      # Penalty for being eaten by a Wumpus or falling into a pit
SCORE_CLIMB_OUT_WITH_GOLD = 1000 # Winning score
SCORE_CLIMB_OUT_WITHOUT_GOLD = 0 # No points for giving up

# --- Game States ---
GAME_STATE_PLAYING = "Playing"
GAME_STATE_WON = "Won"
GAME_STATE_LOST = "Lost"

# --- Advanced / Moving Wumpus ---
# After every WUMPUS_MOVE_INTERVAL agent actions, each Wumpus moves 1 step.
WUMPUS_MOVE_INTERVAL = 5
RISK_UNKNOWN = 6
RISK_DANGEROUS = 60
RISK_VISITED_SOFT = 2 