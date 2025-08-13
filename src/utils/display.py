# src/utils/display.py

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
        agent_has_arrow,
        score,
        percepts,
        message="",
        true_map=None,  
    ):
        """
        Displays the Wumpus World.
        """
        self.clear_screen()
        print("--- Wumpus World ---")
        print(f"Score: {score}")
        print(f"Percepts: {', '.join(percepts) if percepts else 'None'}")
        print(f"Agent has gold: {'Yes' if agent_has_gold else 'No'}")
        print(f"Number of remaining arrows: {agent_has_arrow}")
        print(f"Message: {message}\n")

        print("--- Agent's Knowledge ---")
        self._render_map(agent_pos, agent_dir, agent_known_map, agent_kb_status)

        if true_map:
            print("\n--- True Map ---")
            self._render_map(agent_pos, agent_dir, true_map=true_map, agent_has_arrow=agent_has_arrow)

    # Extract map rendering logic into a separate function for reuse
    def _render_map(self, agent_pos, agent_dir, agent_known_map=None, agent_kb_status=None, true_map=None, agent_has_arrow=None):
        """Hàm helper để vẽ một lưới bản đồ."""
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
                    if true_map:
                        items = true_map[x][y]
                        content = []
                        if WUMPUS_SYMBOL in items: content.append(WUMPUS_SYMBOL)
                        if PIT_SYMBOL in items: content.append(PIT_SYMBOL)
                        if GOLD_SYMBOL in items: content.append(GOLD_SYMBOL)
                        cell_content = "/".join(content) if content else EMPTY_CELL_SYMBOL
                    
                    elif agent_known_map and agent_kb_status:
                        known_elements = agent_known_map[x][y]
                        status = agent_kb_status[x][y]

                        if GOLD_SYMBOL in known_elements: cell_content = GOLD_SYMBOL
                        elif status == "Safe": cell_content = "S"
                        elif WUMPUS_SYMBOL in known_elements: cell_content = WUMPUS_SYMBOL
                        elif PIT_SYMBOL in known_elements: cell_content = PIT_SYMBOL
                        elif status == "Visited": cell_content = "V"
                        elif status == "Dangerous": cell_content = "D"
                        else: cell_content = "?"

                row_str += f" {cell_content:<3}"[:4]

            row_str += WALL_SYMBOL
            print(row_str)

        # Print bottom border
        print("  " + WALL_SYMBOL * (self.N * 2 + 1))
        # Print X-axis labels
        x_labels = "   "
        for i in range(self.N):
            x_labels += f"{i:<2} "
        print(x_labels)
        
        print(f"Number of remaining arrows: {agent_has_arrow}")


    def pause(self, seconds=0.5):
        """Pauses the display for a given number of seconds."""
        time.sleep(seconds)