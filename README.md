# AI Wumpus World

This project implements an AI agent that navigates through the Wumpus World environment using logical inference and strategic planning.

## Features

- Intelligent agent using logical inference and knowledge representation
- Multiple environment options (static or moving wumpuses)
- Choice between text-based display or graphical user interface (GUI)

## GUI Features

The GUI visualizes the Wumpus World environment with the following elements:

- **Map Display**: Shows the current state of the world
  - Discovered squares use `floor.png`
  - Undiscovered squares use `wall_3.png`
  - Gold is represented by `gold-icon.png` 
  - Pits are represented by `hole.png`
  - Wumpuses are represented by `wumpus.png`
  - The agent is represented by `player_facing_to_down.png` (rotated based on direction)
  - Killed wumpuses are marked with a red X

- **Status Panel**: Shows current game information
  - Current score
  - Current percepts (Stench, Breeze, Glitter, etc.)
  - Gold collection status
  - Agent position and direction
  - Current action/status message

- **Agent Log**: Shows a history of agent actions and events

## How to Run

1. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the main script:
   ```
   python src/main.py
   ```

3. Follow the on-screen prompts to configure the simulation parameters.

## Requirements

- Python 3.8 or higher
- Pygame 2.5.2 (for GUI display)