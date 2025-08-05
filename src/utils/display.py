# wumpus_world/utils/display.py

import os
import time
from utils.constants import *


class WumpusWorldDisplay:
    def __init__(self, N):
        self.N = N

    def clear_screen(self):
        """Clears the terminal screen."""
        os.system("cls" if os.name == "nt" else "clear")

    def display_map(
        self,
        agent_known_map,
        agent_kb_status,
        agent_pos,
        agent_dir,
        agent_has_gold,
        score,
        percepts,
        message="",
    ):
        """
        Displays the current state of the Wumpus World map based on agent's knowledge.
        :param agent_known_map: A 2D list representing the agent's internal known map.
                                Each cell contains a set of known elements/percepts.
        :param agent_kb_status: A 2D list representing the agent's inferred status for each cell
                                (e.g., 'Safe', 'Dangerous', 'Unknown').
        :param agent_pos: Tuple (x, y) of agent's current position.
        :param agent_dir: Tuple (dx, dy) of agent's current direction.
        :param agent_has_gold: Boolean, true if agent has gold.
        :param score: Current score of the agent.
        :param percepts: List of current percepts.
        :param message: An optional message to display.
        """
        self.clear_screen()
        print("--- Wumpus World ---")
        print(f"Score: {score}")
        print(f"Percepts: {', '.join(percepts) if percepts else 'None'}")
        print(f"Agent has gold: {'Yes' if agent_has_gold else 'No'}")
        print(f"Message: {message}\n")

        # Print top border
        print("  " + WALL_SYMBOL * (self.N * 2 + 1))

        # Iterate from top (N-1) to bottom (0) for Y-axis
        for y in range(self.N - 1, -1, -1):
            row_str = f"{y} " + WALL_SYMBOL  # Y-axis label and left wall
            for x in range(self.N):
                cell_content = EMPTY_CELL_SYMBOL

                # Prioritize agent display
                if (x, y) == agent_pos:
                    cell_content = DIRECTION_SYMBOLS.get(agent_dir, AGENT_SYMBOL)
                else:
                    # Display agent's known map content
                    known_elements = agent_known_map[x][y]

                    # Prioritize known elements
                    if GOLD_SYMBOL in known_elements:
                        cell_content = GOLD_SYMBOL
                    elif WUMPUS_SYMBOL in known_elements:
                        cell_content = WUMPUS_SYMBOL
                    elif PIT_SYMBOL in known_elements:
                        cell_content = PIT_SYMBOL
                    elif STENCH_SYMBOL in known_elements:
                        cell_content = STENCH_SYMBOL
                    elif BREEZE_SYMBOL in known_elements:
                        cell_content = BREEZE_SYMBOL
                    else:
                        # If nothing specific known, display KB status
                        status = agent_kb_status[x][y]
                        if status == "Safe":
                            cell_content = "S"  # Safe
                        elif status == "Dangerous":
                            cell_content = "D"  # Dangerous
                        elif status == "Unknown":
                            cell_content = "?"  # Unknown
                        else:
                            cell_content = EMPTY_CELL_SYMBOL  # Default empty

                row_str += cell_content + " "
            row_str += WALL_SYMBOL  # Right wall
            print(row_str)

        # Print bottom border
        print("  " + WALL_SYMBOL * (self.N * 2 + 1))

        # Print X-axis labels
        x_labels = "  "
        for i in range(self.N):
            x_labels += str(i) + " "
        print(x_labels)
        print("\n")

    def pause(self, seconds=0.5):
        """Pauses the display for a given number of seconds."""
        time.sleep(seconds)
