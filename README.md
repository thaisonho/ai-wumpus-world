# AI Wumpus World

This project implements an AI agent that navigates through the Wumpus World environment using logical inference and strategic planning.

## Requirements

- Python 3.8 or higher
- Pygame 2.5.2 (for GUI display)

## Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/thaisonho/ai-wumpus-world.git
   cd ai-wumpus-world
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # On Linux/Mac
   # OR
   .venv\Scripts\activate      # On Windows
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Main Simulation

To run the main Wumpus World simulation:

```bash
python src/main.py
```

You will be prompted to configure the simulation parameters:
- Grid size (NxN)
- Number of wumpuses
- Pit probability
- Delay between steps
- Whether wumpuses can move
- Whether to use GUI or text-based display
- Simulation mode (single agent, comparison, or multi-trial)

## Running Testcases

The project includes predefined testcases with maps of different sizes.

### Running a Specific Testcase

To run a specific testcase:

```bash
python run_testcases.py --testcase testcases/small_map/map_01.json
```

This will execute the agent on the specified map and save the results to a JSON file in the corresponding results directory.

### Running All Testcases

To run all available testcases:

```bash
python run_testcases.py --all
```

### Visualizing Testcases and Results

You can visualize testcase maps and results using ASCII characters:

```bash
# Visualize a testcase map
python visualize_testcase.py --testcase testcases/small_map/map_01.json

# Visualize a test result
python visualize_testcase.py --result testcases/small_map/results/map_01_20250813_223457.json
```

## Testcase Directory Structure

```
testcases/
├── small_map/       # 4x4 maps
├── medium_map/      # 8x8 maps
└── large_map/       # 12x12 and 15x15 maps
```

For more details on the testcases, see [testcases/README.md](testcases/README.md).