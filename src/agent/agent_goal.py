# src/agent/agent_goal.py
from enum import Enum, auto

class AgentGoal(Enum):
    EXPLORE_SAFELY = auto()
    RETURN_HOME = auto()
    SHOOT_WUMPUS = auto() 
    GET_UNSTUCK = auto()  
    RISKY_EXPLORATION = auto() 
    ESCAPE = auto()
    DO_NOTHING = auto()