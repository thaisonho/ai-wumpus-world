import pygame
import os
import time
from utils.constants import (
    AGENT_SYMBOL,
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
    DIRECTIONS,
    NORTH,
    EAST,
    SOUTH,
    WEST,
    GAME_STATE_PLAYING,
    GAME_STATE_WON,
    GAME_STATE_LOST,
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
        self.grid_offset_x = 50
        self.grid_offset_y = 50
        
        # Font configuration
        self.font_small = pygame.font.SysFont('Arial', 16)
        self.font_medium = pygame.font.SysFont('Arial', 20)
        self.font_large = pygame.font.SysFont('Arial', 24, True)
        
        # Initialize assets dictionary
        self.assets = {}
        self._load_assets()
        
        # Initialize log area
        self.log_messages = []
        self.max_log_messages = 10
        
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
            'player': 'player_facing_to_down.png'
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
        
        # Add message to log if it's different from last message
        if message and (not self.log_messages or message != self.log_messages[-1]):
            self.log_messages.append(message)
            if len(self.log_messages) > self.max_log_messages:
                self.log_messages.pop(0)
        
        # Handle agent_dir rotation
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
                    # Get the player image and rotate according to direction
                    player_img = self.assets['player'].copy()
                    rotation = player_rotations.get(agent_dir, 0)
                    if rotation != 0:
                        player_img = pygame.transform.rotate(player_img, rotation)
                    
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
        
        dir_symbols = {NORTH: "↑", EAST: "→", SOUTH: "↓", WEST: "←"}
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
        
        # Draw log area with header and border
        log_header = self.font_medium.render("Agent Log:", True, (255, 255, 255))
        self.screen.blit(log_header, (info_panel_x, info_panel_y))
        info_panel_y += 30
        
        # Create a background for the log area
        log_height = self.window_height - info_panel_y - 30
        log_bg = pygame.Rect(info_panel_x, info_panel_y, info_panel_width, log_height)
        pygame.draw.rect(self.screen, (30, 30, 40), log_bg, border_radius=5)
        
        # Draw log messages with timestamps
        log_y = info_panel_y + 10
        for i, log_msg in enumerate(self.log_messages):
            # Wrap long log messages
            words = log_msg.split()
            log_lines = []
            current_line = ""
            for word in words:
                test_line = current_line + " " + word if current_line else word
                if self.font_small.size(test_line)[0] < info_panel_width - 20:
                    current_line = test_line
                else:
                    log_lines.append(current_line)
                    current_line = word
            if current_line:
                log_lines.append(current_line)
            
            # Draw each line of the log message
            for j, line in enumerate(log_lines):
                # Use different colors for alternating log entries
                text_color = (180, 180, 200) if i % 2 == 0 else (200, 200, 180)
                log_line_text = self.font_small.render(line, True, text_color)
                
                # Check if we're still within the log area
                if log_y + j * 20 < info_panel_y + log_height - 10:
                    self.screen.blit(log_line_text, (info_panel_x + 10, log_y + j * 20))
            
            log_y += len(log_lines) * 20 + 5  # Add spacing between log entries
            
            # Stop if we run out of space
            if log_y >= info_panel_y + log_height - 20:
                break
        
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
                    
                    # Add elements from the environment
                    for element in cell_elements:
                        if element in [PIT_SYMBOL, GOLD_SYMBOL]:
                            self.env_map[pos].add(element)
                        elif element == WUMPUS_SYMBOL:
                            self.env_map[pos].add(WUMPUS_SYMBOL)
                            if pos not in self.wumpus_positions:
                                self.wumpus_positions.append(pos)
            
            # Re-apply killed wumpuses to ensure they don't disappear
            self.killed_wumpuses = killed_wumpuses
            
        else:  # This is the agent's knowledge map
            # Process the agent's map to update our environment record
            # We'll only add elements that the agent discovers, not remove them
            for x in range(self.N):
                for y in range(self.N):
                    pos = (x, y)
                    cell_elements = agent_known_map[x][y]
                    
                    # Initialize the position in our environment map if needed
                    if pos not in self.env_map:
                        self.env_map[pos] = set()
                    
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
                
        # Debug print
        if self.wumpus_positions:
            print(f"Current wumpus positions: {self.wumpus_positions}")
        
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
        """Pause the display for a given number of seconds"""
        start_time = time.time()
        while time.time() - start_time < seconds:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()
            time.sleep(0.01)  # Small sleep to prevent high CPU usage
    
    def wait_for_key(self):
        """Wait for a key press to continue"""
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()
                elif event.type == pygame.KEYDOWN:
                    waiting = False
    
    def cleanup(self):
        """Clean up Pygame resources"""
        pygame.quit()
