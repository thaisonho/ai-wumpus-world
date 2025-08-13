# Wumpus World Testcases

This directory contains testcases for the Wumpus World simulation. Each testcase is a JSON file with a predefined map configuration.

## Directory Structure

```
testcases/
├── small_map/      # Maps of size 4x4
│   ├── map_01.json
│   ├── map_02.json
│   ├── map_03.json
│   └── results/    # Results of running the testcases
├── medium_map/     # Maps of size 8x8
│   ├── map_01.json
│   ├── map_02.json
│   ├── map_03.json
│   └── results/    # Results of running the testcases
└── large_map/      # Maps of size 12x12 and 15x15
    ├── map_01.json
    ├── map_02.json
    ├── map_03.json
    └── results/    # Results of running the testcases
```

## Testcase Format

Each testcase is a JSON file with the following format:

```json
{
  "name": "Map Name",
  "description": "Description of the map",
  "N": 4,  // Size of the map (NxN)
  "wumpus_positions": [[x1, y1], [x2, y2], ...],  // Positions of wumpuses
  "pit_positions": [[x1, y1], [x2, y2], ...],     // Positions of pits
  "gold_position": [x, y]                          // Position of the gold
}
```

## Running Testcases

To run a specific testcase:

```bash
# Make sure you're in the project root directory and using the virtual environment
source .venv/bin/activate  # Activate the virtual environment
python run_testcases.py --testcase testcases/small_map/map_01.json
```

To run all testcases:

```bash
# Make sure you're in the project root directory and using the virtual environment
source .venv/bin/activate  # Activate the virtual environment
python run_testcases.py --all
```

## Results

Each test run creates a JSON file in the corresponding `results/` directory with:

1. The testcase configuration
2. A step-by-step log of the agent's actions, percepts, and score
3. The final state of the game

The result files are named with the format: `{testcase_name}_{timestamp}.json`

## Visualizing Results

The results can be analyzed by reviewing the JSON files directly or by using the visualization script. 

To visualize a testcase map or result:

```bash
# Visualize a testcase map
python visualize_testcase.py --testcase testcases/small_map/map_01.json

# Visualize a testcase result
python visualize_testcase.py --result testcases/small_map/results/map_01_20250813_223457.json
```

The visualization uses ASCII characters to display:
- The map layout with wumpuses, pits, and gold
- The agent's path through the map 
- A summary of agent actions and their results

The JSON result files contain detailed information about:
- The agent's path through the map
- Percepts received at each step
- Actions taken by the agent
- Final score and game state (won/lost)
- Agent's final knowledge of the map
- The true map for comparison
