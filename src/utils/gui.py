import pygame
import os
import time
import copy
from utils.constants import (
    WUMPUS_SYMBOL, PIT_SYMBOL, GOLD_SYMBOL, BREEZE_SYMBOL, STENCH_SYMBOL,
    PERCEPT_STENCH, PERCEPT_BREEZE, PERCEPT_GLITTER, PERCEPT_BUMP, PERCEPT_SCREAM,
    NORTH, EAST, SOUTH, WEST
)

class WumpusWorldGUI:
    """Pygame-based GUI for the Wumpus World simulation."""
    
    def __init__(self, N, window_width=1200, window_height=800):
        """Initialize the Pygame GUI for Wumpus World."""
        # Initialize Pygame
        pygame.init()
        pygame.display.set_caption("Wumpus World")
        
        # Window setup
        self.window_width = window_width
        self.window_height = window_height
        self.screen = pygame.display.set_mode((window_width, window_height))
        
        # Grid configuration
        self.N = N
        self.grid_size = min((window_width - 400) // N, (window_height - 100) // N)
        self.grid_offset_x = 50
        self.grid_offset_y = 50
        
        # Player direction images mapping
        self.player_direction_images = {
            NORTH: 'player_up',
            EAST: 'player_right',
            SOUTH: 'player_down',
            WEST: 'player_left'
        }
        
        # Simulation control
        self.paused = False
        self.step_mode = False
        
        # History tracking
        self.history = []
        self.current_history_index = -1  # -1 means live/current state
        self.max_history = 100
        
        # UI elements
        self.font_small = pygame.font.SysFont('Arial', 16)
        self.font_medium = pygame.font.SysFont('Arial', 20)
        self.font_large = pygame.font.SysFont('Arial', 24, True)
        
        # Game state tracking
        self.assets = {}
        self._load_assets()
        self.log_messages = []
        self.max_log_messages = 100
        self.current_message = ""
        self.killed_wumpuses = set()
        self.env_map = {}
        self.wumpus_positions = []
    
    def _load_assets(self):
        """Load and scale all game image assets."""
        asset_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'assets', 'img')
        
        asset_files = {
            'floor': 'floor.png',
            'wall': 'wall_3.png',
            'wumpus': 'wumpus.png',
            'gold': 'gold-icon.png',
            'pit': 'hole.png',
            'player_down': 'player_facing_to_down.png',
            'player_up': 'player_facing_to_up.png',
            'player_left': 'player_facing_to_left.png',
            'player_right': 'player_facing_to_right.png'
        }
        
        for key, filename in asset_files.items():
            try:
                path = os.path.join(asset_dir, filename)
                original_img = pygame.image.load(path)
                self.assets[key] = pygame.transform.scale(original_img, (self.grid_size, self.grid_size))
            except pygame.error as e:
                print(f"Error loading asset {filename}: {e}")
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
        """Display the Wumpus World map using Pygame."""
        # Update message and log
        self._update_message_and_log(message)
        
        # Save state to history if in live mode
        if self.current_history_index == -1:
            self.save_state_snapshot(agent_known_map, agent_kb_status, agent_pos, agent_dir,
                                    agent_has_gold, score, percepts)
        
        # Draw the basic screen elements
        self._draw_screen_background()
        
        # Get environment state (updates tracking)
        env = self._get_environment_from_map(agent_known_map)
        
        # Draw the grid cells
        self._draw_grid(agent_known_map, agent_kb_status, agent_pos, agent_dir, env)
        
        # Draw grid coordinates
        self._draw_grid_coordinates()
        
        # Draw the info panel
        self._draw_info_panel(agent_pos, agent_dir, agent_has_gold, score, percepts, message)
        
        # Update display
        pygame.display.flip()
    
    def _update_message_and_log(self, message):
        """Update current message and add to log if not empty."""
        self.current_message = message
        
        if message:
            self.log_messages.append(message)
            
            # Limit the number of messages we keep
            if len(self.log_messages) > self.max_log_messages:
                self.log_messages.pop(0)
    
    def _draw_screen_background(self):
        """Draw the base background for the screen."""
        # Clear the screen with a dark background
        self.screen.fill((20, 20, 20))
        
        # Draw a background for the grid area
        grid_total_width = self.N * self.grid_size
        grid_total_height = self.N * self.grid_size
        pygame.draw.rect(self.screen, (40, 40, 40), 
                        (self.grid_offset_x - 5, self.grid_offset_y - 5, 
                        grid_total_width + 10, grid_total_height + 10))
    
    def _draw_grid(self, agent_known_map, agent_kb_status, agent_pos, agent_dir, env):
        """Draw the grid with all elements."""
        for y in range(self.N):
            for x in range(self.N):
                # Convert to screen coordinates
                screen_x = self.grid_offset_x + x * self.grid_size
                # Invert y-axis since pygame's (0,0) is top-left, but our map has (0,0) at bottom-left
                screen_y = self.grid_offset_y + (self.N - 1 - y) * self.grid_size
                
                cell_pos = (x, y)
                is_visited = agent_kb_status[x][y] == "Visited"
                status = agent_kb_status[x][y]
                
                # Draw the appropriate background
                self.screen.blit(self.assets['floor' if is_visited else 'wall'], (screen_x, screen_y))
                
                # Draw status overlays
                self._draw_cell_status_overlay(screen_x, screen_y, status, is_visited)
                
                # Draw percept indicators
                self._draw_cell_percepts(screen_x, screen_y, is_visited, agent_known_map[x][y])
                
                # Draw environment elements
                self._draw_cell_environment_elements(screen_x, screen_y, cell_pos, is_visited, env)
                
                # Draw agent if this is agent's position
                if cell_pos == agent_pos:
                    player_image_key = self.player_direction_images.get(agent_dir, 'player_down')
                    player_img = self.assets[player_image_key].copy()
                    self.screen.blit(player_img, (screen_x, screen_y))
                
                # Draw grid cell borders
                pygame.draw.rect(self.screen, (100, 100, 100), 
                                (screen_x, screen_y, self.grid_size, self.grid_size), 1)
                
                # Special highlight for the exit/entry point (0,0)
                if cell_pos == (0, 0):
                    entry_overlay = pygame.Surface((self.grid_size, self.grid_size), pygame.SRCALPHA)
                    entry_overlay.fill((255, 255, 0, 40))  # Transparent yellow
                    self.screen.blit(entry_overlay, (screen_x, screen_y))
                    pygame.draw.rect(self.screen, (255, 255, 0), 
                                    (screen_x, screen_y, self.grid_size, self.grid_size), 3)
    
    def _draw_cell_status_overlay(self, screen_x, screen_y, status, is_visited):
        """Draw the cell status overlay (safe, dangerous, etc.)."""
        if status == "Safe" and not is_visited:
            overlay = pygame.Surface((self.grid_size, self.grid_size), pygame.SRCALPHA)
            overlay.fill((0, 255, 0, 40))  # Very transparent green
            self.screen.blit(overlay, (screen_x, screen_y))
        elif status == "Dangerous" and not is_visited:
            overlay = pygame.Surface((self.grid_size, self.grid_size), pygame.SRCALPHA)
            overlay.fill((255, 0, 0, 40))  # Very transparent red
            self.screen.blit(overlay, (screen_x, screen_y))
    
    def _draw_cell_percepts(self, screen_x, screen_y, is_visited, known_elements):
        """Draw percept indicators for a cell."""
        if is_visited:
            if BREEZE_SYMBOL in known_elements:
                pygame.draw.circle(self.screen, (100, 200, 255, 180), 
                                (screen_x + self.grid_size//4, screen_y + self.grid_size//4), 
                                self.grid_size//8)
            
            if STENCH_SYMBOL in known_elements:
                pygame.draw.rect(self.screen, (100, 255, 100, 180),
                                (screen_x + self.grid_size//4, screen_y + 3*self.grid_size//4, 
                                self.grid_size//4, self.grid_size//4))
    
    def _draw_cell_environment_elements(self, screen_x, screen_y, cell_pos, is_visited, env):
        """Draw environment elements (pits, wumpuses, gold) in a cell."""
        # Draw pits
        if cell_pos in env['pits']:
            pit_img = self.assets['pit'].copy()
            if not is_visited:
                pit_img.set_alpha(128)  # 50% transparency for undiscovered
            self.screen.blit(pit_img, (screen_x, screen_y))
        
        # Draw wumpuses
        if cell_pos in env['wumpuses'] or cell_pos in self.wumpus_positions:
            wumpus_img = self.assets['wumpus'].copy()
            if not is_visited:
                wumpus_img.set_alpha(128)  # 50% transparency for undiscovered
            self.screen.blit(wumpus_img, (screen_x, screen_y))
            
            # If this wumpus is killed, draw the red cross
            if cell_pos in self.killed_wumpuses:
                self.screen.blit(self.assets['cross'], (screen_x, screen_y))
        
        # Draw gold
        if cell_pos in env['gold']:
            gold_img = self.assets['gold'].copy()
            if not is_visited:
                gold_img.set_alpha(128)  # 50% transparency for undiscovered
            self.screen.blit(gold_img, (screen_x, screen_y))
    
    def _draw_grid_coordinates(self):
        """Draw the coordinate numbers around the grid."""
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
    
    def _draw_info_panel(self, agent_pos, agent_dir, agent_has_gold, score, percepts, message):
        """Draw the information panel on the right side of the screen."""
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
        
        # Draw score
        info_panel_y = self._draw_score_panel(info_panel_x, info_panel_y, info_panel_width, score)
        
        # Draw percepts
        info_panel_y = self._draw_percepts_panel(info_panel_x, info_panel_y, info_panel_width, percepts)
        
        # Draw gold status
        info_panel_y = self._draw_gold_status(info_panel_x, info_panel_y, info_panel_width, agent_has_gold)
        
        # Draw position and direction
        info_panel_y = self._draw_position_direction(info_panel_x, info_panel_y, agent_pos, agent_dir)
        
        # Draw current message
        info_panel_y = self._draw_status_message(info_panel_x, info_panel_y, info_panel_width, message)
        
        # Draw log area
        self._draw_log_area(info_panel_x, info_panel_y, info_panel_width, info_panel_height)
    
    def _draw_score_panel(self, x, y, width, score):
        """Draw the score panel and return the next y position."""
        score_bg = pygame.Rect(x - 5, y - 5, width + 10, 40)
        pygame.draw.rect(self.screen, (50, 50, 80), score_bg, border_radius=5)
        score_text = self.font_large.render(f"Score: {score}", True, (255, 255, 255))
        self.screen.blit(score_text, (x + 10, y + 5))
        return y + 50
    
    def _draw_percepts_panel(self, x, y, width, percepts):
        """Draw the percepts panel and return the next y position."""
        percept_header = self.font_medium.render("Current Percepts:", True, (255, 255, 255))
        self.screen.blit(percept_header, (x, y))
        y += 30
        
        # Create a background for percepts
        percept_bg = pygame.Rect(x, y, width, 60)
        pygame.draw.rect(self.screen, (50, 60, 50), percept_bg, border_radius=5)
        
        # Define percept colors
        percept_colors = {
            PERCEPT_STENCH: (100, 255, 100),    # Green for stench
            PERCEPT_BREEZE: (100, 200, 255),    # Light blue for breeze
            PERCEPT_GLITTER: (255, 215, 0),     # Gold for glitter
            PERCEPT_BUMP: (255, 100, 100),      # Red for bump
            PERCEPT_SCREAM: (255, 255, 100)     # Yellow for scream
        }
        
        if percepts:
            percept_spacing = min(width // len(percepts), 100)
            for i, percept in enumerate(percepts):
                percept_x = x + 10 + i * percept_spacing
                percept_y = y + 10
                
                # Draw colored circle for percept
                color = percept_colors.get(percept, (200, 200, 200))
                pygame.draw.circle(self.screen, color, (percept_x + 10, percept_y + 10), 10)
                
                # Draw percept text
                percept_text = self.font_small.render(percept, True, (255, 255, 255))
                self.screen.blit(percept_text, (percept_x - percept_text.get_width()//2 + 10, percept_y + 25))
        else:
            no_percept_text = self.font_small.render("None", True, (200, 200, 200))
            self.screen.blit(no_percept_text, (x + 10, y + 20))
        
        return y + 70
    
    def _draw_gold_status(self, x, y, width, has_gold):
        """Draw the gold status and return the next y position."""
        gold_color = (255, 215, 0) if has_gold else (150, 150, 150)
        gold_bg = pygame.Rect(x, y, width, 30)
        pygame.draw.rect(self.screen, (60, 60, 40) if has_gold else (50, 50, 50), 
                         gold_bg, border_radius=5)
        
        gold_text = self.font_medium.render(f"Has Gold: {'Yes' if has_gold else 'No'}", 
                                           True, gold_color)
        self.screen.blit(gold_text, (x + 10, y + 5))
        return y + 40
    
    def _draw_position_direction(self, x, y, pos, dir):
        """Draw the position and direction information and return the next y position."""
        pos_text = self.font_medium.render(f"Position: {pos}", True, (255, 255, 255))
        self.screen.blit(pos_text, (x, y))
        y += 25
        
        dir_symbols = {NORTH: "^", EAST: ">", SOUTH: "v", WEST: "<"}
        dir_text = self.font_medium.render(
            f"Direction: {dir_symbols.get(dir, '?')}", 
            True, (255, 255, 255))
        self.screen.blit(dir_text, (x, y))
        return y + 40
    
    def _draw_status_message(self, x, y, width, message):
        """Draw the status message area and return the next y position."""
        message_header = self.font_medium.render("Status:", True, (255, 255, 255))
        self.screen.blit(message_header, (x, y))
        y += 30
        
        # Create a background for the status message
        status_bg = pygame.Rect(x, y, width, 60)
        pygame.draw.rect(self.screen, (60, 50, 60), status_bg, border_radius=5)
        
        # Handle long messages by wrapping text
        words = message.split()
        lines = []
        current_line = ""
        for word in words:
            test_line = current_line + " " + word if current_line else word
            if self.font_small.size(test_line)[0] < width - 20:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        
        # Display status message
        for i, line in enumerate(lines[:3]):  # Limit to 3 lines in status area
            line_text = self.font_small.render(line, True, (200, 200, 200))
            self.screen.blit(line_text, (x + 10, y + 10 + i * 20))
        
        return y + 70
    
    def _draw_log_area(self, x, y, width, panel_height):
        """Draw the log area with agent messages."""
        # Draw log header
        log_header_rect = pygame.Rect(x, y, width, 30)
        pygame.draw.rect(self.screen, (50, 50, 60), log_header_rect, border_radius=5)
        log_header = self.font_medium.render("Agent Log:", True, (255, 255, 255))
        self.screen.blit(log_header, (x + 10, y + 5))
        y += 35
        
        # Create background for log area
        log_height = panel_height - (y - self.grid_offset_y) - 30
        log_bg = pygame.Rect(x, y, width, log_height)
        pygame.draw.rect(self.screen, (30, 30, 40), log_bg, border_radius=5)
        
        # Determine how many lines we can fit and display the most recent messages
        line_height = 20
        max_displayable_lines = (log_height - 20) // line_height
        display_messages = list(reversed(self.log_messages[-max_displayable_lines:]))
        
        # Draw the messages
        y_offset = 10
        for i, log_msg in enumerate(display_messages):
            text_color = (180, 180, 200) if i % 2 == 0 else (200, 200, 180)
            log_text = self.font_small.render(log_msg, True, text_color)
            
            if y_offset + line_height <= log_height:
                self.screen.blit(log_text, (x + 10, y + y_offset))
                y_offset += line_height
    
    def initialize_environment(self, env_map):
        """Initialize the environment state at the beginning of the game."""
        # Clear any existing state
        self.env_map = {}
        self.wumpus_positions = []
        
        # Process the environment map
        for x in range(self.N):
            for y in range(self.N):
                pos = (x, y)
                cell_elements = env_map[x][y]
                
                self.env_map[pos] = set()
                
                for element in cell_elements:
                    if element == WUMPUS_SYMBOL:
                        self.env_map[pos].add(WUMPUS_SYMBOL)
                        self.wumpus_positions.append(pos)
                    elif element in [PIT_SYMBOL, GOLD_SYMBOL]:
                        self.env_map[pos].add(element)
    
    def update_environment_state(self, agent_known_map):
        """Update the internal environment state tracking based on agent's knowledge."""
        if isinstance(agent_known_map, list):  # This is a complete environment map from main.py
            # Keep track of killed wumpuses
            killed_wumpuses = self.killed_wumpuses.copy()
            self.wumpus_positions = []
            
            # Process each position
            for x in range(self.N):
                for y in range(self.N):
                    pos = (x, y)
                    cell_elements = agent_known_map[x][y]
                    
                    # Initialize position if needed
                    if pos not in self.env_map:
                        self.env_map[pos] = set()
                    
                    # Remove any wumpuses from this position if not killed
                    if WUMPUS_SYMBOL in self.env_map[pos] and pos not in killed_wumpuses:
                        self.env_map[pos].remove(WUMPUS_SYMBOL)
                    
                    # Update gold status
                    if GOLD_SYMBOL in self.env_map[pos] and GOLD_SYMBOL not in cell_elements:
                        self.env_map[pos].remove(GOLD_SYMBOL)
                        
                    # Add elements from the environment
                    for element in cell_elements:
                        if element in [PIT_SYMBOL, GOLD_SYMBOL]:
                            self.env_map[pos].add(element)
                        elif element == WUMPUS_SYMBOL:
                            self.env_map[pos].add(WUMPUS_SYMBOL)
                            if pos not in self.wumpus_positions:
                                self.wumpus_positions.append(pos)
            
            # Restore killed wumpuses
            self.killed_wumpuses = killed_wumpuses
        else:  # This is the agent's knowledge map
            for x in range(self.N):
                for y in range(self.N):
                    pos = (x, y)
                    cell_elements = agent_known_map[x][y]
                    
                    # Initialize position if needed
                    if pos not in self.env_map:
                        self.env_map[pos] = set()
                    
                    # Update gold status
                    has_gold_in_cell = GOLD_SYMBOL in cell_elements
                    if GOLD_SYMBOL in self.env_map[pos] and not has_gold_in_cell:
                        self.env_map[pos].remove(GOLD_SYMBOL)
                    
                    # Add any elements found in this cell
                    for element in cell_elements:
                        if element in [PIT_SYMBOL, GOLD_SYMBOL]:
                            self.env_map[pos].add(element)
    
    def _get_environment_from_map(self, agent_known_map):
        """Extract environment elements from the agent's known map."""
        # First, update our environment state tracking
        if not isinstance(agent_known_map, list):  # Don't update for agent's knowledge
            self.update_environment_state(agent_known_map)
        
        # Extract the current environment state
        environment = {
            'pits': [],
            'wumpuses': [],
            'gold': []
        }
        
        # Collect elements from environment map
        for pos, elements in self.env_map.items():
            if PIT_SYMBOL in elements:
                environment['pits'].append(pos)
            if GOLD_SYMBOL in elements:
                environment['gold'].append(pos)
            if WUMPUS_SYMBOL in elements and (pos in self.wumpus_positions or pos in self.killed_wumpuses):
                environment['wumpuses'].append(pos)
        
        # Ensure all tracked wumpuses are included
        for wumpus_pos in self.wumpus_positions:
            if wumpus_pos not in environment['wumpuses']:
                environment['wumpuses'].append(wumpus_pos)
        
        # Ensure all killed wumpuses are included
        for killed_pos in self.killed_wumpuses:
            if killed_pos not in environment['wumpuses']:
                environment['wumpuses'].append(killed_pos)
        
        return environment
    
    def mark_wumpus_killed(self, wumpus_pos):
        """Mark a wumpus at the given position as killed."""
        self.killed_wumpuses.add(wumpus_pos)
        
        # Ensure the killed wumpus is recorded in our environment map
        if wumpus_pos not in self.env_map:
            self.env_map[wumpus_pos] = set()
            
        self.env_map[wumpus_pos].add(WUMPUS_SYMBOL)
        
        # Make sure the killed wumpus is in our wumpus positions list
        if wumpus_pos not in self.wumpus_positions:
            self.wumpus_positions.append(wumpus_pos)
    
    def pause(self, seconds=0.5):
        """Pause the display for a given number of seconds or handle key press during pause."""
        start_time = time.time()
        should_skip_pause = False
        
        # Draw pause/history overlay if needed
        if self.paused or self.current_history_index != -1:
            overlay_surface = self._create_pause_overlay()
            
            # Position overlay in the center of the grid
            overlay_x = self.grid_offset_x + (self.grid_size * self.N) // 2 - 200
            overlay_y = self.grid_offset_y + (self.grid_size * self.N) // 2 - 60
            
            self.screen.blit(overlay_surface, (overlay_x, overlay_y))
            pygame.display.flip()
        
        # Main pause loop
        while (self.paused or time.time() - start_time < seconds):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()
                    
                elif event.type == pygame.KEYDOWN:
                    should_skip_pause = self._handle_pause_key_press(event)
                    if should_skip_pause:
                        break
                        
            if should_skip_pause:
                break
                
            time.sleep(0.01)  # Small sleep to prevent high CPU usage
                
        return should_skip_pause
    
    def _create_pause_overlay(self):
        """Create the pause/history overlay surface."""
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
        
        return overlay_surface
    
    def _handle_pause_key_press(self, event):
        """Handle key presses during pause. Returns True if pause should be skipped."""
        # 'P' key toggles pause
        if event.key == pygame.K_p:
            self.paused = not self.paused
            # Return to live state if unpausing from history view
            if self.current_history_index != -1 and not self.paused:
                self.current_history_index = -1
            # Redraw the screen
            pygame.display.flip()
            return False
            
        # Space bar or RIGHT arrow advances one step when paused
        elif (event.key in [pygame.K_SPACE, pygame.K_RIGHT]) and self.paused and self.current_history_index == -1:
            self.paused = False
            return True  # Signal to main loop we want one step
        
        # LEFT arrow to go to previous step
        elif event.key == pygame.K_LEFT:
            if not self.paused and not self.step_mode:
                self.paused = True  # Pause when starting to navigate history
            if self.go_to_previous_step():
                pygame.display.flip()
            return False
        
        # RIGHT arrow for history navigation
        elif event.key == pygame.K_RIGHT and self.current_history_index != -1:
            if self.go_to_next_step():
                pygame.display.flip()
            return False
        
        # HOME key to return to current state
        elif event.key == pygame.K_HOME:
            original_index = self.current_history_index
            self.current_history_index = -1
            if original_index != -1:
                pygame.display.flip()
            return False
            
        return False
    
    def save_state_snapshot(self, agent_known_map=None, agent_kb_status=None, agent_pos=None, agent_dir=None,
                         agent_has_gold=None, score=None, percepts=None):
        """Save current game state to history."""
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
        """Restore game state from history at given index."""
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
        """Redraw the screen from a snapshot without saving a new history entry."""
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
        """Navigate to the previous step in history."""
        if not self.history:
            return False
            
        target_index = self.current_history_index - 1
        if self.current_history_index == -1:  # We're at current/live state
            target_index = len(self.history) - 1
            
        if target_index >= 0:
            self.current_history_index = target_index
            return self.restore_state_snapshot(target_index)
        return False
        
    def go_to_next_step(self):
        """Navigate to the next step in history."""
        if not self.history or self.current_history_index == -1:
            return False
            
        target_index = self.current_history_index + 1
        if target_index < len(self.history):
            self.current_history_index = target_index
            return self.restore_state_snapshot(target_index)
        else:
            # Return to live state
            self.current_history_index = -1
            return True
    
    def wait_for_key(self, score=None, game_state=None):
        """Wait for a key press to continue and display final score and game state."""
        if score is not None and game_state is not None:
            # Create a game over overlay
            overlay = self._create_game_over_overlay(score, game_state)
            
            # Position overlay in the center of the grid
            overlay_x = self.grid_offset_x + (self.grid_size * self.N) // 2 - 225
            overlay_y = self.grid_offset_y + (self.grid_size * self.N) // 2 - 105
            
            self.screen.blit(overlay, (overlay_x, overlay_y))
            pygame.display.flip()
        
        # Wait for any key press
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()
                elif event.type == pygame.KEYDOWN:
                    waiting = False
            time.sleep(0.01)  # Small sleep to prevent high CPU usage
    
    def _create_game_over_overlay(self, score, game_state):
        """Create the game over overlay with score and state information."""
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
        overlay_surface.blit(help_text1, (225 - help_text1.get_width() // 2, 120))
        overlay_surface.blit(help_text2, (225 - help_text2.get_width() // 2, 145))
        overlay_surface.blit(help_text3, (225 - help_text3.get_width() // 2, 170))
        overlay_surface.blit(exit_text, (225 - exit_text.get_width() // 2, 195))
        
        return overlay_surface
    
    def cleanup(self):
        """Clean up Pygame resources."""
        pygame.quit()
