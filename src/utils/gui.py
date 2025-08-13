import pygame
import os
import time
import copy
from utils.constants import (
    WUMPUS_SYMBOL,
    PIT_SYMBOL,
    GOLD_SYMBOL,
    BREEZE_SYMBOL,
    STENCH_SYMBOL,
    PERCEPT_STENCH,
    PERCEPT_BREEZE,
    PERCEPT_GLITTER,
    PERCEPT_BUMP,
    PERCEPT_SCREAM,
    NORTH,
    EAST,
    SOUTH,
    WEST,
)

class WumpusWorldGUI:
    def __init__(self, N, window_width=1200, window_height=800):
        """
        Initialize the Pygame GUI for Wumpus World.
        
        Args:
            N (int): Size of the grid (N x N)
            window_width (int): Width of the Pygame window
            window_height (int): Height of the Pygame window
        """
        # Initialize Pygame
        pygame.init()
        pygame.display.set_caption("Wumpus World")
        
        # Set up the window
        self.window_width = window_width
        self.window_height = window_height
        self.screen = pygame.display.set_mode((window_width, window_height))
        
        # Grid configuration - calculate optimal grid size based on window
        self.N = N
        max_grid_height = window_height - 100  # Leave room for other UI elements
        max_grid_width = window_width - 400    # Leave room for info panel
        self.grid_size = min(max_grid_width // N, max_grid_height // N)
        self.grid_margin = 50
        
        # Initialize player direction images dictionary (will be set in display_map)
        self.player_direction_images = {}
        
        # Simulation control
        self.paused = False
        self.step_mode = False  # Add missing step_mode attribute
        self.grid_offset_x = 50
        self.grid_offset_y = 50
        
        # History tracking for step navigation
        self.history = []  # List of game state snapshots
        self.current_history_index = -1  # Current position in history (-1 means live/current state)
        self.max_history = 100  # Maximum number of history states to keep
        
        # Font configuration
        self.font_small = pygame.font.SysFont('Arial', 16)
        self.font_medium = pygame.font.SysFont('Arial', 20)
        self.font_large = pygame.font.SysFont('Arial', 24, True)
        
        # Initialize assets dictionary
        self.assets = {}
        self._load_assets()
        
        # Initialize log area
        self.log_messages = []
        self.max_log_messages = 100  # Maximum number of messages to store
        
        # Game state
        self.current_message = ""
        self.killed_wumpuses = set()  # Track killed wumpuses by coordinates
        
        # Track the true environment state
        self.env_map = {}  # Will store elements at each (x,y) position
        self.wumpus_positions = []   # List of wumpus positions for tracking movement
        
    def _load_assets(self):
        """Load all image assets with proper scaling"""
        asset_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'assets', 'img')
        
        # Load and scale all images
        asset_files = {
            'floor': 'floor.png',
            'wall': 'wall_3.png',
            'wumpus': 'wumpus.png',
            'gold': 'gold-icon.png',
            'pit': 'hole.png',
            # Player images for each direction
            'player_down': 'player_facing_to_down.png',
            'player_up': 'player_facing_to_up.png',
            'player_left': 'player_facing_to_left.png',
            'player_right': 'player_facing_to_right.png'
        }
        
        for key, filename in asset_files.items():
            path = os.path.join(asset_dir, filename)
            try:
                original_img = pygame.image.load(path)
                self.assets[key] = pygame.transform.scale(original_img, (self.grid_size, self.grid_size))
            except pygame.error as e:
                print(f"Error loading asset {filename}: {e}")
                # Create a placeholder colored square if image can't be loaded
                placeholder = pygame.Surface((self.grid_size, self.grid_size))
                placeholder.fill((200, 50, 50))
                self.assets[key] = placeholder
                
        # For backward compatibility
        self.assets['player'] = self.assets['player_down']
        
        # Create a red cross for marking killed wumpuses
        cross = pygame.Surface((self.grid_size, self.grid_size), pygame.SRCALPHA)
        pygame.draw.line(cross, (255, 0, 0), (5, 5), (self.grid_size - 5, self.grid_size - 5), 5)
        pygame.draw.line(cross, (255, 0, 0), (self.grid_size - 5, 5), (5, self.grid_size - 5), 5)
        self.assets['cross'] = cross
    
    def display_map(self, agent_known_map, agent_kb_status, agent_pos, agent_dir,
                   agent_has_gold, score, percepts, message=""):
        """
        Display the Wumpus World map using Pygame.
        
        Args:
            agent_known_map: What the agent knows for sure in a cell
            agent_kb_status: What the agent has inferred about a cell
            agent_pos: Current agent position
            agent_dir: Current agent direction
            agent_has_gold: Whether the agent has the gold
            score: Current score
            percepts: Current percepts
            message: Message to display
        """
        # Update current message
        self.current_message = message
        
        # Add message to log if it's not empty
        if message:
            # Always add step messages to the log
            self.log_messages.append(message)
                
            # Limit the number of messages we keep
            if len(self.log_messages) > self.max_log_messages:
                self.log_messages.pop(0)
                
        # Save the state to history if we're not in history viewing mode or special mode
        # Always save state to ensure logs are captured properly
        if self.current_history_index == -1:  # Only save if we're in live mode (not viewing history)
            self.save_state_snapshot(agent_known_map, agent_kb_status, agent_pos, agent_dir,
                                    agent_has_gold, score, percepts)
        # Special value -2 means we're redrawing from history, don't save
        
        # Map directions to player images
        self.player_direction_images = {
            NORTH: 'player_up',    # Facing up
            EAST: 'player_right',  # Facing right
            SOUTH: 'player_down',  # Facing down
            WEST: 'player_left'    # Facing left
        }
        
        # For backwards compatibility
        player_rotations = {
            NORTH: 0,    # Facing up - no rotation needed
            EAST: 270,   # Facing right - rotate 270 degrees counterclockwise
            SOUTH: 180,  # Facing down - rotate 180 degrees
            WEST: 90     # Facing left - rotate 90 degrees counterclockwise
        }
        
        # Clear the screen with a dark background
        self.screen.fill((20, 20, 20))
        
        # Draw a background for the grid area
        grid_total_width = self.N * self.grid_size
        grid_total_height = self.N * self.grid_size
        pygame.draw.rect(self.screen, (40, 40, 40), 
                        (self.grid_offset_x - 5, self.grid_offset_y - 5, 
                        grid_total_width + 10, grid_total_height + 10))
        
        # Draw grid
        for y in range(self.N):
            for x in range(self.N):
                # Convert to screen coordinates
                screen_x = self.grid_offset_x + x * self.grid_size
                # Invert y-axis since pygame's (0,0) is top-left, but our map has (0,0) at bottom-left
                screen_y = self.grid_offset_y + (self.N - 1 - y) * self.grid_size
                
                cell_pos = (x, y)
                is_visited = agent_kb_status[x][y] == "Visited"
                status = agent_kb_status[x][y]
                known_elements = agent_known_map[x][y]
                
                # First, determine if the cell is visited
                is_visited = agent_kb_status[x][y] == "Visited"
                
                # Draw the appropriate background
                if is_visited:
                    # Discovered cell - draw floor
                    self.screen.blit(self.assets['floor'], (screen_x, screen_y))
                else:
                    # Undiscovered cell - draw wall
                    self.screen.blit(self.assets['wall'], (screen_x, screen_y))
                
                # Check the environment elements in the cell
                # Get the full environment state (this also updates our tracking)
                env = self._get_environment_from_map(agent_known_map)
                cell_pos = (x, y)
                
                # Show inferred knowledge with status indicators
                if status == "Safe" and not is_visited:
                    # Add a subtle green overlay to indicate safe
                    safe_overlay = pygame.Surface((self.grid_size, self.grid_size), pygame.SRCALPHA)
                    safe_overlay.fill((0, 255, 0, 40))  # Very transparent green
                    self.screen.blit(safe_overlay, (screen_x, screen_y))
                elif status == "Dangerous" and not is_visited:
                    # Add a subtle red overlay to indicate danger
                    danger_overlay = pygame.Surface((self.grid_size, self.grid_size), pygame.SRCALPHA)
                    danger_overlay.fill((255, 0, 0, 40))  # Very transparent red
                    self.screen.blit(danger_overlay, (screen_x, screen_y))
                
                # Draw percept indicators for visited cells
                if is_visited:
                    if BREEZE_SYMBOL in known_elements:
                        # Draw breeze indicator (light blue circle)
                        pygame.draw.circle(self.screen, (100, 200, 255, 180), 
                                        (screen_x + self.grid_size//4, screen_y + self.grid_size//4), 
                                        self.grid_size//8)
                    
                    if STENCH_SYMBOL in known_elements:
                        # Draw stench indicator (green square)
                        pygame.draw.rect(self.screen, (100, 255, 100, 180),
                                        (screen_x + self.grid_size//4, screen_y + 3*self.grid_size//4, 
                                        self.grid_size//4, self.grid_size//4))
                
                # Draw all elements from our environment tracking
                # This ensures we show elements even if the agent doesn't know them yet
                
                # Draw pits - show on every cell where a pit exists in our tracking
                if cell_pos in env['pits']:
                    pit_img = self.assets['pit'].copy()
                    if not is_visited:
                        pit_img.set_alpha(128)  # 50% transparency for undiscovered
                    self.screen.blit(pit_img, (screen_x, screen_y))
                
                # Draw wumpuses - show on every cell where a wumpus exists in our tracking
                if cell_pos in env['wumpuses'] or cell_pos in self.wumpus_positions:
                    # Double check to make sure we catch all wumpuses
                    wumpus_img = self.assets['wumpus'].copy()
                    if not is_visited:
                        wumpus_img.set_alpha(128)  # 50% transparency for undiscovered
                    self.screen.blit(wumpus_img, (screen_x, screen_y))
                    
                    # If this wumpus is killed, draw the red cross
                    if cell_pos in self.killed_wumpuses:
                        self.screen.blit(self.assets['cross'], (screen_x, screen_y))
                
                # Draw gold - show on every cell where gold exists in our tracking
                if cell_pos in env['gold']:
                    gold_img = self.assets['gold'].copy()
                    if not is_visited:
                        gold_img.set_alpha(128)  # 50% transparency for undiscovered
                    self.screen.blit(gold_img, (screen_x, screen_y))
                
                # Draw agent if this is agent's position
                # Draw the agent AFTER all other elements so it's always visible on top
                # This ensures it doesn't appear to move through pits or wumpuses
                if cell_pos == agent_pos:
                    # Get the appropriate player image based on direction
                    player_image_key = self.player_direction_images.get(agent_dir, 'player_down')
                    player_img = self.assets[player_image_key].copy()
                    
                    self.screen.blit(player_img, (screen_x, screen_y))
                    
                # Draw grid cell borders
                pygame.draw.rect(self.screen, (100, 100, 100), 
                                (screen_x, screen_y, self.grid_size, self.grid_size), 1)
                
                # Special highlight for the exit/entry point (0,0)
                if (x, y) == (0, 0):
                    entry_overlay = pygame.Surface((self.grid_size, self.grid_size), pygame.SRCALPHA)
                    entry_overlay.fill((255, 255, 0, 40))  # Transparent yellow
                    self.screen.blit(entry_overlay, (screen_x, screen_y))
                    pygame.draw.rect(self.screen, (255, 255, 0), 
                                    (screen_x, screen_y, self.grid_size, self.grid_size), 3)
        
        # Draw coordinates
        for i in range(self.N):
            # Draw row numbers (y-axis)
            text = self.font_small.render(str(i), True, (255, 255, 255))
            self.screen.blit(text, (
                self.grid_offset_x - 20, 
                self.grid_offset_y + (self.N - 1 - i) * self.grid_size + self.grid_size//2 - text.get_height()//2
            ))
            
            # Draw column numbers (x-axis)
            text = self.font_small.render(str(i), True, (255, 255, 255))
            self.screen.blit(text, (
                self.grid_offset_x + i * self.grid_size + self.grid_size//2 - text.get_width()//2,
                self.grid_offset_y + self.N * self.grid_size + 10
            ))
        
        # Draw game info panel with a background
        info_panel_x = self.grid_offset_x + self.N * self.grid_size + 20
        info_panel_y = self.grid_offset_y
        info_panel_width = self.window_width - info_panel_x - 20
        info_panel_height = self.window_height - self.grid_offset_y * 2
        
        # Draw panel background
        pygame.draw.rect(self.screen, (40, 40, 40), 
                         (info_panel_x - 10, info_panel_y - 10, 
                          info_panel_width + 20, info_panel_height + 20))
        
        # Draw header with game title
        pygame.draw.rect(self.screen, (60, 60, 60), 
                         (info_panel_x - 10, info_panel_y - 10, 
                          info_panel_width + 20, 40))
        title_text = self.font_large.render("Wumpus World", True, (255, 255, 255))
        self.screen.blit(title_text, (
            info_panel_x + info_panel_width//2 - title_text.get_width()//2,
            info_panel_y - 5
        ))
        info_panel_y += 50
        
        # Draw score with a highlighted background
        score_bg = pygame.Rect(info_panel_x - 5, info_panel_y - 5, info_panel_width + 10, 40)
        pygame.draw.rect(self.screen, (50, 50, 80), score_bg, border_radius=5)
        score_text = self.font_large.render(f"Score: {score}", True, (255, 255, 255))
        self.screen.blit(score_text, (info_panel_x + 10, info_panel_y + 5))
        info_panel_y += 50
        
        # Draw current percepts with icons
        percept_header = self.font_medium.render("Current Percepts:", True, (255, 255, 255))
        self.screen.blit(percept_header, (info_panel_x, info_panel_y))
        info_panel_y += 30
        
        # Create a background for percepts
        percept_bg = pygame.Rect(info_panel_x, info_panel_y, info_panel_width, 60)
        pygame.draw.rect(self.screen, (50, 60, 50), percept_bg, border_radius=5)
        
        # Draw percept indicators with colors
        percept_colors = {
            PERCEPT_STENCH: (100, 255, 100),    # Green for stench
            PERCEPT_BREEZE: (100, 200, 255),    # Light blue for breeze
            PERCEPT_GLITTER: (255, 215, 0),     # Gold for glitter
            PERCEPT_BUMP: (255, 100, 100),      # Red for bump
            PERCEPT_SCREAM: (255, 255, 100)     # Yellow for scream
        }
        
        if percepts:
            percept_spacing = min(info_panel_width // len(percepts), 100)
            for i, percept in enumerate(percepts):
                percept_x = info_panel_x + 10 + i * percept_spacing
                percept_y = info_panel_y + 10
                
                # Draw colored circle for percept
                color = percept_colors.get(percept, (200, 200, 200))
                pygame.draw.circle(self.screen, color, (percept_x + 10, percept_y + 10), 10)
                
                # Draw percept text
                percept_text = self.font_small.render(percept, True, (255, 255, 255))
                self.screen.blit(percept_text, (percept_x - percept_text.get_width()//2 + 10, percept_y + 25))
        else:
            no_percept_text = self.font_small.render("None", True, (200, 200, 200))
            self.screen.blit(no_percept_text, (info_panel_x + 10, info_panel_y + 20))
        
        info_panel_y += 70
        
        # Draw gold status with appropriate color
        gold_color = (255, 215, 0) if agent_has_gold else (150, 150, 150)
        gold_bg = pygame.Rect(info_panel_x, info_panel_y, info_panel_width, 30)
        pygame.draw.rect(self.screen, (60, 60, 40) if agent_has_gold else (50, 50, 50), 
                         gold_bg, border_radius=5)
        
        gold_text = self.font_medium.render(f"Has Gold: {'Yes' if agent_has_gold else 'No'}", 
                                           True, gold_color)
        self.screen.blit(gold_text, (info_panel_x + 10, info_panel_y + 5))
        info_panel_y += 40
        
        # Draw current position and direction
        pos_text = self.font_medium.render(f"Position: {agent_pos}", True, (255, 255, 255))
        self.screen.blit(pos_text, (info_panel_x, info_panel_y))
        info_panel_y += 25
        
        dir_symbols = {NORTH: "^", EAST: ">", SOUTH: "v", WEST: "<"}
        dir_text = self.font_medium.render(
            f"Direction: {dir_symbols.get(agent_dir, '?')}", 
            True, (255, 255, 255))
        self.screen.blit(dir_text, (info_panel_x, info_panel_y))
        info_panel_y += 40
        
        # Draw current message with header
        message_header = self.font_medium.render("Status:", True, (255, 255, 255))
        self.screen.blit(message_header, (info_panel_x, info_panel_y))
        info_panel_y += 30
        
        # Create a background for the status message
        status_bg = pygame.Rect(info_panel_x, info_panel_y, info_panel_width, 60)
        pygame.draw.rect(self.screen, (60, 50, 60), status_bg, border_radius=5)
        
        # Handle long messages by wrapping text
        words = message.split()
        lines = []
        current_line = ""
        for word in words:
            test_line = current_line + " " + word if current_line else word
            if self.font_small.size(test_line)[0] < info_panel_width - 20:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        
        # Display status message
        for i, line in enumerate(lines[:3]):  # Limit to 3 lines in status area
            line_text = self.font_small.render(line, True, (200, 200, 200))
            self.screen.blit(line_text, (info_panel_x + 10, info_panel_y + 10 + i * 20))
        
        info_panel_y += 70
        
        # Draw log area with header, border, and controls
        log_header_rect = pygame.Rect(info_panel_x, info_panel_y, info_panel_width, 30)
        pygame.draw.rect(self.screen, (50, 50, 60), log_header_rect, border_radius=5)
        
        # Draw log header text
        log_header = self.font_medium.render("Agent Log:", True, (255, 255, 255))
        self.screen.blit(log_header, (info_panel_x + 10, info_panel_y + 5))
        
        info_panel_y += 35
        
        # Create a background for the log area
        log_height = self.window_height - info_panel_y - 30
        log_bg = pygame.Rect(info_panel_x, info_panel_y, info_panel_width, log_height)
        pygame.draw.rect(self.screen, (30, 30, 40), log_bg, border_radius=5)
        
        # Process log messages - show most recent messages first
        # Determine how many lines we can fit
        line_height = 20
        max_displayable_lines = (log_height - 20) // line_height
        
        # Always show the most recent messages (last N messages)
        # Get last N messages in reverse order (newest first)
        display_messages = list(reversed(self.log_messages[-max_displayable_lines:]))
        
        # Draw the messages starting from the newest at the top
        y_offset = 10
        for i, log_msg in enumerate(display_messages):
            # Alternate colors for readability
            text_color = (180, 180, 200) if i % 2 == 0 else (200, 200, 180)
            
            # Render the message
            log_text = self.font_small.render(log_msg, True, text_color)
            
            # Draw the message if it fits in the log area
            if y_offset + line_height <= log_height:
                self.screen.blit(log_text, (info_panel_x + 10, info_panel_y + y_offset))
                y_offset += line_height
        
        # Draw legend at the bottom
        legend_y = self.window_height - 30
        legend_text = self.font_small.render("Press any key to exit when game ends", True, (200, 200, 200))
        self.screen.blit(legend_text, (
            self.window_width//2 - legend_text.get_width()//2, 
            legend_y
        ))
        
        # Update display
        pygame.display.flip()
    
    def handle_percept_scream(self):
        """
        Mark a wumpus as killed when a scream is heard.
        This should be called when PERCEPT_SCREAM is detected.
        """
        # Needs to be implemented with access to wumpus location
        pass
    
    def initialize_environment(self, env_map):
        """
        Special initialization method for the first environment state update.
        This method ensures that all wumpuses, pits, and gold are properly registered
        at the beginning of the game.
        
        Args:
            env_map: The complete environment map from main.py
        """
        # Clear any existing state
        self.env_map = {}
        self.wumpus_positions = []
        
        # Process the environment map
        for x in range(self.N):
            for y in range(self.N):
                pos = (x, y)
                cell_elements = env_map[x][y]
                
                # Initialize position
                self.env_map[pos] = set()
                
                # Record all elements in this cell
                for element in cell_elements:
                    if element == WUMPUS_SYMBOL:
                        self.env_map[pos].add(WUMPUS_SYMBOL)
                        print(f"Registering wumpus at {pos}")
                        self.wumpus_positions.append(pos)
                    elif element in [PIT_SYMBOL, GOLD_SYMBOL]:
                        self.env_map[pos].add(element)
    
    def update_environment_state(self, agent_known_map):
        """
        Update the internal record of what's in the environment based on agent's knowledge.
        This ensures we maintain a record of all discovered elements, even as they move.
        
        Args:
            agent_known_map: The agent's knowledge about the world
        """
        # For moving wumpuses, we need to completely refresh our tracking
        # to avoid leaving "ghost" wumpuses behind
        if isinstance(agent_known_map, list):  # This is a complete environment map from main.py
            # Clear all wumpus positions first (but keep track of killed ones)
            killed_wumpuses = self.killed_wumpuses.copy()
            self.wumpus_positions = []
            
            # For each position in the environment
            for x in range(self.N):
                for y in range(self.N):
                    pos = (x, y)
                    cell_elements = agent_known_map[x][y]
                    
                    # Initialize position if needed
                    if pos not in self.env_map:
                        self.env_map[pos] = set()
                    
                    # Remove any wumpuses from this position (we'll add them back if still present)
                    if WUMPUS_SYMBOL in self.env_map[pos] and pos not in killed_wumpuses:
                        self.env_map[pos].remove(WUMPUS_SYMBOL)
                    
                    # First remove gold (if it was previously here) because it can be collected
                    if GOLD_SYMBOL in self.env_map[pos] and GOLD_SYMBOL not in cell_elements:
                        self.env_map[pos].remove(GOLD_SYMBOL)
                        print(f"Gold removed from position {pos} because it's no longer in the environment")
                        
                    # Add elements from the environment
                    for element in cell_elements:
                        if element == PIT_SYMBOL:
                            self.env_map[pos].add(element)
                        elif element == GOLD_SYMBOL:
                            self.env_map[pos].add(element)
                        elif element == WUMPUS_SYMBOL:
                            self.env_map[pos].add(WUMPUS_SYMBOL)
                            if pos not in self.wumpus_positions:
                                self.wumpus_positions.append(pos)
            
            # Re-apply killed wumpuses to ensure they don't disappear
            self.killed_wumpuses = killed_wumpuses
            
        else:  # This is the agent's knowledge map
            # Process the agent's map to update our environment record
            for x in range(self.N):
                for y in range(self.N):
                    pos = (x, y)
                    cell_elements = agent_known_map[x][y]
                    
                    # Initialize the position in our environment map if needed
                    if pos not in self.env_map:
                        self.env_map[pos] = set()
                    
                    # Check if gold is in this cell from agent's knowledge
                    has_gold_in_cell = GOLD_SYMBOL in cell_elements
                    
                    # Remove gold if it's not in the cell anymore (was collected)
                    if GOLD_SYMBOL in self.env_map[pos] and not has_gold_in_cell:
                        self.env_map[pos].remove(GOLD_SYMBOL)
                        print(f"Gold removed from GUI at position {pos} based on agent's knowledge")
                    
                    # Add any elements found in this cell
                    for element in cell_elements:
                        if element in [PIT_SYMBOL, GOLD_SYMBOL]:
                            self.env_map[pos].add(element)
    
    def _get_environment_from_map(self, agent_known_map):
        """
        Extract environment elements from the agent's known map.
        This is a helper function to identify what's in each cell.
        
        Args:
            agent_known_map: The agent's knowledge about the world
            
        Returns:
            Dictionary with environment elements
        """
        # First, update our environment state tracking
        if not isinstance(agent_known_map, list):  # Don't update for agent's knowledge
            self.update_environment_state(agent_known_map)
        
        # Extract the current environment state
        environment = {
            'pits': [],
            'wumpuses': [],
            'gold': []
        }
        
        # Check our env_map for all elements
        for pos, elements in self.env_map.items():
            if PIT_SYMBOL in elements:
                environment['pits'].append(pos)
            if GOLD_SYMBOL in elements:
                environment['gold'].append(pos)
            if WUMPUS_SYMBOL in elements:
                # For wumpuses, check if they're still in our current positions list
                # (to avoid showing "ghost" wumpuses that have moved)
                if pos in self.wumpus_positions or pos in self.killed_wumpuses:
                    environment['wumpuses'].append(pos)
        
        # Also ensure all tracked wumpus positions are included
        for wumpus_pos in self.wumpus_positions:
            if wumpus_pos not in environment['wumpuses']:
                environment['wumpuses'].append(wumpus_pos)
        
        # And ensure all killed wumpuses are included
        for killed_pos in self.killed_wumpuses:
            if killed_pos not in environment['wumpuses']:
                environment['wumpuses'].append(killed_pos)
        
        return environment
    
    def mark_wumpus_killed(self, wumpus_pos):
        """
        Mark a wumpus at the given position as killed.
        
        Args:
            wumpus_pos: (x, y) tuple of the wumpus position
        """
        self.killed_wumpuses.add(wumpus_pos)
        
        # Ensure the killed wumpus is recorded in our environment map
        if wumpus_pos not in self.env_map:
            self.env_map[wumpus_pos] = set()
            
        self.env_map[wumpus_pos].add(WUMPUS_SYMBOL)
        
        # Make sure the killed wumpus is in our wumpus positions list
        if wumpus_pos not in self.wumpus_positions:
            self.wumpus_positions.append(wumpus_pos)
    
    def pause(self, seconds=0.5):
        """
        Pause the display for a given number of seconds or handle key press during pause
        Also handles pause/unpause and step-by-step navigation via keyboard
        Returns True if the pause should be skipped (for next step)
        """
        start_time = time.time()
        waiting_for_step = False  # No longer using step mode
        should_skip_pause = False  # To return to main loop for immediate step
        
        # Create text overlay if paused or in history mode
        if self.paused or self.current_history_index != -1:
            overlay_surface = pygame.Surface((400, 120), pygame.SRCALPHA)
            overlay_surface.fill((0, 0, 0, 180))  # Semi-transparent black
            
            if self.current_history_index != -1:
                status_text = f"HISTORY ({self.current_history_index + 1}/{len(self.history)})"
                help_text1 = "LEFT/RIGHT arrows to navigate history"
                help_text2 = "HOME: return to live state"
            elif self.paused:
                status_text = "PAUSED"
                help_text1 = "P to play/unpause"
                help_text2 = "RIGHT/SPACE to execute next step"
            else:
                status_text = "PLAYING"
                help_text1 = "P to pause"
                help_text2 = "LEFT arrow to view history"
                
            # Add history indicator bar if we have history
            if self.history and (self.paused or self.current_history_index != -1):
                indicator_width = 300
                indicator_height = 10
                pygame.draw.rect(overlay_surface, (50, 50, 50), 
                                (50, 105, indicator_width, indicator_height))
                
                if self.current_history_index == -1:
                    # We're at live state, show at far right
                    pos = indicator_width
                else:
                    # Calculate position based on index
                    pos = int((self.current_history_index + 1) / len(self.history) * indicator_width)
                
                # Draw position indicator
                pygame.draw.rect(overlay_surface, (100, 255, 100), 
                                (50 + pos - 5, 105 - 2, 10, indicator_height + 4))
                
            text_render = self.font_large.render(status_text, True, (255, 255, 255))
            help_render1 = self.font_small.render(help_text1, True, (200, 200, 200))
            help_render2 = self.font_small.render(help_text2, True, (200, 200, 200))
            
            overlay_surface.blit(text_render, (200 - text_render.get_width() // 2, 20))
            overlay_surface.blit(help_render1, (200 - help_render1.get_width() // 2, 50))
            overlay_surface.blit(help_render2, (200 - help_render2.get_width() // 2, 80))
            
            # Position overlay in the center of the grid
            overlay_x = self.grid_offset_x + (self.grid_size * self.N) // 2 - 200
            overlay_y = self.grid_offset_y + (self.grid_size * self.N) // 2 - 60
            
            self.screen.blit(overlay_surface, (overlay_x, overlay_y))
            pygame.display.flip()
        
        while (self.paused or waiting_for_step or time.time() - start_time < seconds):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()
                    
                elif event.type == pygame.KEYDOWN:
                    # 'P' key toggles pause
                    if event.key == pygame.K_p:
                        self.paused = not self.paused
                        waiting_for_step = False
                        # Return to live state if unpausing from history view
                        if self.current_history_index != -1 and not self.paused:
                            self.current_history_index = -1
                        # Redraw the screen to update the overlay
                        pygame.display.flip()
                        
                    # Space bar advances one step when paused (same as RIGHT arrow)
                    elif event.key == pygame.K_SPACE and self.paused:
                        # Temporarily unpause to allow one step to execute
                        self.paused = False
                        should_skip_pause = True  # Signal to main loop we want one step
                        waiting_for_step = False  # Exit the pause loop
                        print("Next step requested - executing one step")
                    
                    # LEFT arrow to go to previous step
                    elif event.key == pygame.K_LEFT:
                        if not self.paused and not self.step_mode:
                            self.paused = True  # Pause when starting to navigate history
                        if self.go_to_previous_step():
                            # Redraw the overlay
                            pygame.display.flip()
                    
                    # RIGHT arrow to go to next step in history or advance step when paused
                    elif event.key == pygame.K_RIGHT:
                        if self.current_history_index != -1:
                            # In history mode - navigate forward in history
                            if self.go_to_next_step():
                                # Redraw the overlay
                                pygame.display.flip()
                        elif self.paused:
                            # When paused and at current state, advance one step
                            # Temporarily unpause to allow one step to execute
                            self.paused = False
                            should_skip_pause = True  # Signal to main loop we want one step
                            waiting_for_step = False  # Exit the pause loop
                            print("Next step requested - executing one step")
                    
                    # HOME key to return to current state
                    elif event.key == pygame.K_HOME:
                        original_index = self.current_history_index
                        self.current_history_index = -1
                        if original_index != -1:
                            # Force a redraw of the current state
                            pygame.display.flip()
                        
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    # Mouse clicks/scrolling - no scrolling needed for logs
                    pass
                        
            if not (self.paused or time.time() - start_time < seconds):
                break
                
            time.sleep(0.01)  # Small sleep to prevent high CPU usage
                
        # Return True if we should skip the pause for the next step
        return should_skip_pause
                
    def save_state_snapshot(self, agent_known_map=None, agent_kb_status=None, agent_pos=None, agent_dir=None,
                         agent_has_gold=None, score=None, percepts=None):
        """Save current game state to history"""
        # Create a deep copy of the current state
        snapshot = {
            'env_map': copy.deepcopy(self.env_map),
            'wumpus_positions': copy.deepcopy(self.wumpus_positions),
            'killed_wumpuses': copy.deepcopy(self.killed_wumpuses),
            'log_messages': copy.deepcopy(self.log_messages),
            'current_message': self.current_message
        }
        
        # Store agent state if provided
        if agent_known_map and agent_kb_status and agent_pos is not None and agent_dir is not None and agent_has_gold is not None and score is not None:
            snapshot['agent_state'] = {
                'agent_known_map': copy.deepcopy(agent_known_map),
                'agent_kb_status': copy.deepcopy(agent_kb_status),
                'agent_pos': agent_pos,
                'agent_dir': agent_dir,
                'agent_has_gold': agent_has_gold,
                'score': score,
                'percepts': copy.deepcopy(percepts) if percepts else []
            }
        
        # If we're viewing history and make a change, truncate forward history
        if self.current_history_index != -1:
            self.history = self.history[:self.current_history_index + 1]
            self.current_history_index = -1
            
        # Add the snapshot to history, maintaining maximum size
        self.history.append(snapshot)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
            
    def restore_state_snapshot(self, index):
        """Restore game state from history at given index"""
        if not self.history or index < 0 or index >= len(self.history):
            return False
            
        # Load the snapshot
        snapshot = self.history[index]
        self.env_map = copy.deepcopy(snapshot['env_map'])
        self.wumpus_positions = copy.deepcopy(snapshot['wumpus_positions'])
        self.killed_wumpuses = copy.deepcopy(snapshot['killed_wumpuses'])
        self.log_messages = copy.deepcopy(snapshot['log_messages'])
        self.current_message = snapshot['current_message']
        
        # If we have agent state in the snapshot, redraw the screen
        if 'agent_state' in snapshot:
            agent_state = snapshot['agent_state']
            self.redraw_from_snapshot(
                agent_state['agent_known_map'],
                agent_state['agent_kb_status'],
                agent_state['agent_pos'],
                agent_state['agent_dir'],
                agent_state['agent_has_gold'],
                agent_state['score'],
                agent_state['percepts'],
                self.current_message
            )
        else:
            # Just update the display
            pygame.display.flip()
            
        return True
        
    def redraw_from_snapshot(self, agent_known_map, agent_kb_status, agent_pos, agent_dir,
                             agent_has_gold, score, percepts, message):
        """Redraw the screen from a snapshot without saving a new history entry"""
        # Temporarily disable history saving
        original_index = self.current_history_index
        self.current_history_index = -2  # Special value to prevent history saving
        
        # Redraw the screen
        self.display_map(
            agent_known_map,
            agent_kb_status,
            agent_pos,
            agent_dir,
            agent_has_gold,
            score,
            percepts,
            message
        )
        
        # Restore original history index
        self.current_history_index = original_index
        

        
    def go_to_previous_step(self):
        """Navigate to the previous step in history"""
        if not self.history:
            print("No history available")
            return False
            
        target_index = self.current_history_index - 1
        if self.current_history_index == -1:  # We're at current/live state
            target_index = len(self.history) - 1
            print(f"Going to history step {target_index + 1}/{len(self.history)}")
            
        if target_index >= 0:
            self.current_history_index = target_index
            print(f"Going to history step {target_index + 1}/{len(self.history)}")
            return self.restore_state_snapshot(target_index)
        print("Already at earliest history step")
        return False
        
    def go_to_next_step(self):
        """Navigate to the next step in history"""
        if not self.history:
            print("No history available")
            return False
            
        if self.current_history_index == -1:
            print("Already at current state")
            return False
            
        target_index = self.current_history_index + 1
        if target_index < len(self.history):
            self.current_history_index = target_index
            print(f"Going to history step {target_index + 1}/{len(self.history)}")
            return self.restore_state_snapshot(target_index)
        else:
            # Return to live state
            self.current_history_index = -1
            print("Returning to current state")
            return True
    
    def wait_for_key(self, score=None, game_state=None):
        """
        Wait for a key press to continue and display final score and game state
        if provided
        """
        waiting = True
        
        # Create a "GAME OVER" text overlay with score and game state
        if score is not None and game_state is not None:
            overlay_surface = pygame.Surface((450, 210), pygame.SRCALPHA)
            overlay_surface.fill((0, 0, 0, 200))  # Semi-transparent black background
            
            # Prepare text renders
            game_over_text = self.font_large.render("GAME OVER", True, (255, 255, 255))
            score_text = self.font_medium.render(f"Final Score: {score}", True, (255, 255, 255))
            state_text = self.font_medium.render(f"Game State: {game_state}", True, (255, 255, 255))
            
            # Navigation help
            help_text1 = self.font_small.render("LEFT/RIGHT arrows: Navigate history/steps", True, (200, 200, 200))
            help_text2 = self.font_small.render("P: Play/Pause, SPACE/RIGHT: Next step when paused", True, (200, 200, 200))
            help_text3 = self.font_small.render("HOME: Return to live state when viewing history", True, (200, 200, 200))
            exit_text = self.font_small.render("Press any key to exit", True, (255, 200, 200))
            
            # Position text on overlay
            overlay_surface.blit(game_over_text, (225 - game_over_text.get_width() // 2, 20))
            overlay_surface.blit(score_text, (225 - score_text.get_width() // 2, 60))
            overlay_surface.blit(state_text, (225 - state_text.get_width() // 2, 90))
            
            # Position help text
            overlay_surface.blit(help_text1, (225 - help_text1.get_width() // 2, 120))
            overlay_surface.blit(help_text2, (225 - help_text2.get_width() // 2, 145))
            overlay_surface.blit(help_text3, (225 - help_text3.get_width() // 2, 170))
            overlay_surface.blit(exit_text, (225 - exit_text.get_width() // 2, 195))
            
            # Position overlay in the center of the grid
            overlay_x = self.grid_offset_x + (self.grid_size * self.N) // 2 - 225
            overlay_y = self.grid_offset_y + (self.grid_size * self.N) // 2 - 105
            
            self.screen.blit(overlay_surface, (overlay_x, overlay_y))
            pygame.display.flip()
        
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()
                elif event.type == pygame.KEYDOWN:
                    waiting = False
            time.sleep(0.01)  # Small sleep to prevent high CPU usage
    
    def cleanup(self):
        """Clean up Pygame resources"""
        pygame.quit()
