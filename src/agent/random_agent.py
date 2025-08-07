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
        A simple agent that chooses an action randomly.
        It doesn't use percepts to make intelligent decisions.
        """
        possible_actions = [
            ACTION_MOVE_FORWARD,
            ACTION_TURN_LEFT,
            ACTION_TURN_RIGHT,
            ACTION_GRAB,
            ACTION_CLIMB_OUT,
        ]
        # The agent can only shoot if it has an arrow.
        if self.agent_has_arrow:
            possible_actions.append(ACTION_SHOOT)
        
        return random.choice(possible_actions)

    def update_state(self, env_state):
        """
        Syncs the agent's state with the environment.
        For this simple agent, we only care about whether it has an arrow.
        """
        self.agent_has_arrow = env_state["agent_has_arrow"]
        
    def get_known_map(self):
        """The random agent doesn't build a map."""
        return [[set() for _ in range(self.N)] for _ in range(self.N)]

    def get_kb_status(self):
        """The random agent doesn't have a knowledge base."""
        return [["Unknown" for _ in range(self.N)] for _ in range(self.N)]
