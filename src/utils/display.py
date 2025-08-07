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
        Displays the Wumpus World from the agent's perspective.
        - agent_known_map: What the agent knows for sure is in a cell (Wumpus, Pit, Gold).
        - agent_kb_status: What the agent has inferred about a cell (Safe, Dangerous, Unknown).
        """
        self.clear_screen()
        print("--- Wumpus World ---")
        print(f"Score: {score}")
        print(f"Percepts: {', '.join(percepts) if percepts else 'None'}")
        print(f"Agent has gold: {'Yes' if agent_has_gold else 'No'}")
        print(f"Message: {message}\n")

        # Print top border
        print("  " + WALL_SYMBOL * (self.N * 2 + 1))

        # Iterate from top-to-bottom, left-to-right to draw the map
        for y in range(self.N - 1, -1, -1):
            row_str = f"{y} " + WALL_SYMBOL
            for x in range(self.N):
                cell_content = EMPTY_CELL_SYMBOL

                if (x, y) == agent_pos:
                    # Display the agent with its direction
                    cell_content = DIRECTION_SYMBOLS.get(agent_dir, AGENT_SYMBOL)
                else:
                    known_elements = agent_known_map[x][y]
                    status = agent_kb_status[x][y]

                    # Display known facts first (Wumpus, Pit, Gold)
                    if GOLD_SYMBOL in known_elements:
                        cell_content = GOLD_SYMBOL
                    elif WUMPUS_SYMBOL in known_elements:
                        cell_content = WUMPUS_SYMBOL
                    elif PIT_SYMBOL in known_elements:
                        cell_content = PIT_SYMBOL
                    # If no definite objects, show inferred status or percepts
                    elif status == "Visited":
                        cell_content = "V"  # Mark visited and safe cells
                    elif status == "Safe":
                        cell_content = "S"
                    elif status == "Dangerous":
                        cell_content = "D"
                    elif BREEZE_SYMBOL in known_elements and STENCH_SYMBOL in known_elements:
                        cell_content = "S/B" # Both stench and breeze inferred
                    elif BREEZE_SYMBOL in known_elements:
                        cell_content = "b" # Inferred breeze
                    elif STENCH_SYMBOL in known_elements:
                        cell_content = "s" # Inferred stench
                    else:
                        cell_content = "?"  # Default to unknown

                row_str += f" {cell_content}"
            row_str += " " + WALL_SYMBOL
            print(row_str)

        # Print bottom border
        print("  " + WALL_SYMBOL * (self.N * 2 + 1))

        # Print X-axis labels
        x_labels = "   " + " ".join(map(str, range(self.N)))
        print(x_labels)
        print("\n")

    def pause(self, seconds=0.5):
        """Pauses the display for a given number of seconds."""
        time.sleep(seconds)
