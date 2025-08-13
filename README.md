# AI Wumpus World

This project implements an AI agent that navigates through the Wumpus World environment using logical inference and strategic planning.

## Features

- Intelligent agent using logical inference and knowledge representation
- Knowledge base and inference engine for logical reasoning
- Multiple environment options (static or moving wumpuses)
- Choice between text-based display or graphical user interface (GUI)
- History tracking and playback of agent's actions
- Interactive pause/step functionality

## GUI Features

The GUI visualizes the Wumpus World environment with the following elements:

- **Map Display**: Shows the current state of the world
  - Discovered squares use floor textures
  - Undiscovered squares use wall textures
  - Visual indicators for gold, pits, and wumpuses
  - Agent with directional representation
  - Killed wumpuses are marked with a red X

- **Status Panel**: Shows current game information
  - Current score
  - Current percepts (Stench, Breeze, Glitter, etc.)
  - Gold collection status
  - Agent position and direction
  - Current action/status message

- **Agent Log**: Shows a history of agent actions and events

- **Interactive Controls**:
  - Pause/Resume simulation with 'P' key
  - Step-by-step execution with Space or Right arrow
  - Navigate history with Left/Right arrows
  - Return to live state with Home key

## How to Run

1. Create and activate a virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate   # On Linux/Mac
   # OR
   .venv\Scripts\activate      # On Windows
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the main script:
   ```
   python src/main.py
   ```

4. Follow the on-screen prompts to configure the simulation parameters.

## Code Structure

- **src/agent/**: Contains the intelligent agent implementation
  - `agent.py`: Main agent class
  - `knowledge_base.py`: Knowledge representation
  - `inference_module.py`: Logical reasoning engine
  - `pathfinding_module.py`: Path planning
  - `planning_module.py`: Action planning
  - `rules.py`: Logical rules

- **src/environment/**: Contains the world environment
  - `environment.py`: Base environment
  - `advanced_environment.py`: Environment with moving wumpuses
  - `map_generator.py`: World generation

- **src/utils/**: Contains utilities
  - `constants.py`: Game constants
  - `display.py`: Text-based display
  - `gui_optimized.py`: Optimized graphical interface

## Recent Improvements

- Optimized GUI code with better organization and reduced redundancy
- Modularized functions for better maintainability
- Improved method naming for clarity
- Reduced code duplication through helper methods
- Enhanced readability through consistent structure

## Requirements

- Python 3.8 or higher
- Pygame 2.5.2 (for GUI display)