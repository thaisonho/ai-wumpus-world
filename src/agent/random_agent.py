# wumpus_world/agent/random_agent.py

from utils.constants import (
    ACTION_MOVE_FORWARD,
    ACTION_TURN_LEFT,
    ACTION_TURN_RIGHT,
    ACTION_GRAB,
    ACTION_SHOOT,
    ACTION_CLIMB_OUT,
)
import random

class RandomAgent:
    def __init__(self, N):
        self.N = N
        self.agent_has_arrow = True

    def decide_action(self, percepts):
        """
        Decides an action randomly from the set of possible actions.
        """
        possible_actions = [
            ACTION_MOVE_FORWARD,
            ACTION_TURN_LEFT,
            ACTION_TURN_RIGHT,
            ACTION_GRAB,
            ACTION_CLIMB_OUT,
        ]
        if self.agent_has_arrow:
            possible_actions.append(ACTION_SHOOT)
        
        return random.choice(possible_actions)

    def update_state(self, env_state):
        """
        Updates the agent's state. For the random agent, we only need to know
        if it has an arrow.
        """
        self.agent_has_arrow = env_state["agent_has_arrow"]
