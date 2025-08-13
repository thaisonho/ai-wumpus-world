#!/usr/bin/env python3
# visualize_testcase.py - Script to visualize testcase maps and results using ASCII characters

import os
import sys
import json
import argparse
from pathlib import Path

# Add the src directory to the path for importing constants
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from utils.constants import (
    WUMPUS_SYMBOL,
    PIT_SYMBOL,
    GOLD_SYMBOL,
    AGENT_SYMBOL,
    DIRECTION_SYMBOLS,
    EMPTY_CELL_SYMBOL,
)

def load_json_file(file_path):
    """Load a JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)

def visualize_testcase_map(testcase_path):
    """Visualize a testcase map using ASCII characters."""
    testcase = load_json_file(testcase_path)
    
    N = testcase.get('N')
    wumpus_positions = testcase.get('wumpus_positions', [])
    pit_positions = testcase.get('pit_positions', [])
    gold_position = testcase.get('gold_position')
    
    # Create an empty map
    ascii_map = [[EMPTY_CELL_SYMBOL for _ in range(N)] for _ in range(N)]
    
    # Fill in the elements
    for wx, wy in wumpus_positions:
        ascii_map[wy][wx] = WUMPUS_SYMBOL
    
    for px, py in pit_positions:
        ascii_map[py][px] = PIT_SYMBOL
    
    if gold_position:
        gx, gy = gold_position
        ascii_map[gy][gx] = GOLD_SYMBOL
    
    # Mark the starting position
    ascii_map[0][0] = AGENT_SYMBOL
    
    # Print map information
    print(f"\n===== TESTCASE MAP: {testcase.get('name')} =====")
    print(f"Size: {N}x{N}")
    print(f"Description: {testcase.get('description')}")
    print(f"Wumpuses: {len(wumpus_positions)}")
    print(f"Pits: {len(pit_positions)}")
    print(f"Gold at: {gold_position}")
    print("\nMAP VISUALIZATION:")
    
    # Print column numbers
    print("   ", end="")
    for x in range(N):
        print(f" {x:2}", end="")
    print("\n   +" + "---" * N + "+")
    
    # Print rows
    for y in range(N-1, -1, -1):  # Print top-to-bottom for correct orientation
        print(f"{y:2} |", end="")
        for x in range(N):
            print(f" {ascii_map[y][x]} ", end="")
        print("|")
    
    # Print bottom border
    print("   +" + "---" * N + "+")
    print("\nLegend:")
    print(f"  {AGENT_SYMBOL}: Agent starting position")
    print(f"  {WUMPUS_SYMBOL}: Wumpus")
    print(f"  {PIT_SYMBOL}: Pit")
    print(f"  {GOLD_SYMBOL}: Gold")
    print(f"  {EMPTY_CELL_SYMBOL}: Empty cell")

def visualize_result(result_path):
    """Visualize a testcase result using ASCII characters."""
    result = load_json_file(result_path)
    
    # Extract data
    testcase_name = result.get('testcase_name')
    config = result.get('config', {})
    steps = result.get('steps', [])
    final_state = result.get('final_state', {})
    
    N = config.get('N')
    true_map = final_state.get('true_map')
    
    # Create a map for the agent's path
    path_map = [[' ' for _ in range(N)] for _ in range(N)]
    
    # Plot the path with step numbers
    agent_positions = []
    for i, step in enumerate(steps):
        pos = step.get('agent_pos', [0, 0])
        agent_positions.append(pos)
        x, y = pos
        # We'll display the last digit of step numbers to avoid clutter
        path_map[y][x] = str((i+1) % 10)
    
    # Print result information
    print(f"\n===== TESTCASE RESULT: {testcase_name} =====")
    print(f"Map Size: {N}x{N}")
    print(f"Description: {config.get('description')}")
    print(f"\nOutcome: {final_state.get('game_state')}")
    print(f"Final Score: {final_state.get('score')}")
    print(f"Steps Used: {final_state.get('steps_used')}")
    print(f"Agent Has Gold: {final_state.get('agent_has_gold')}")
    print(f"Final Position: {final_state.get('agent_pos')}")
    
    # Print the true map with agent's path
    print("\nTRUE MAP WITH AGENT'S PATH:")
    
    # Print column numbers
    print("   ", end="")
    for x in range(N):
        print(f" {x:2}", end="")
    print("\n   +" + "---" * N + "+")
    
    # Print rows
    for y in range(N-1, -1, -1):  # Print top-to-bottom for correct orientation
        print(f"{y:2} |", end="")
        for x in range(N):
            cell_content = ""
            # Add true map elements
            if true_map and x < len(true_map) and y < len(true_map[x]):
                cell_contents = true_map[x][y]
                if WUMPUS_SYMBOL in cell_contents:
                    cell_content += WUMPUS_SYMBOL
                if PIT_SYMBOL in cell_contents:
                    cell_content += PIT_SYMBOL
                if GOLD_SYMBOL in cell_contents:
                    cell_content += GOLD_SYMBOL
            
            # Add path information
            if path_map[y][x] != ' ':
                cell_content += path_map[y][x]
            
            # If cell is empty, print empty cell symbol
            if not cell_content:
                cell_content = EMPTY_CELL_SYMBOL
                
            # Truncate to avoid overlapping in display
            if len(cell_content) > 3:
                cell_content = cell_content[:3]
            
            print(f" {cell_content:3}", end="")
        print("|")
    
    # Print bottom border
    print("   +" + "---" * N + "+")
    
    # Print legend
    print("\nLegend:")
    print("  0-9: Agent's path (last digit of step number)")
    print(f"  {WUMPUS_SYMBOL}: Wumpus")
    print(f"  {PIT_SYMBOL}: Pit")
    print(f"  {GOLD_SYMBOL}: Gold")
    print(f"  {EMPTY_CELL_SYMBOL}: Empty cell")
    
    # Print action summary
    print("\nACTION SUMMARY:")
    print("-" * 80)
    print(f"{'Step':>5} {'Position':>10} {'Direction':>10} {'Action':>15} {'Result':>30}")
    print("-" * 80)
    
    # Print the first 10 steps and last 5 steps if there are more than 15 steps
    if len(steps) > 15:
        steps_to_show = steps[:10] + [{"step": "..."}, {"step": "..."}, {"step": "..."}] + steps[-5:]
    else:
        steps_to_show = steps
    
    for step in steps_to_show:
        if isinstance(step["step"], str):
            print(f"{'...':>5} {'...':>10} {'...':>10} {'...':>15} {'...':>30}")
            continue
        
        step_num = step.get('step')
        pos = step.get('agent_pos', [0, 0])
        pos_str = f"({pos[0]},{pos[1]})"
        
        dir = step.get('agent_dir', [1, 0])
        dir_symbol = DIRECTION_SYMBOLS.get(tuple(dir), '?')
        
        action = step.get('action', '')
        result = step.get('action_result', '')
        if len(result) > 30:
            result = result[:27] + "..."
        
        print(f"{step_num:5d} {pos_str:>10} {dir_symbol:>10} {action:>15} {result:>30}")

def main():
    parser = argparse.ArgumentParser(description='Visualize Wumpus World testcases and results')
    parser.add_argument('--testcase', type=str, help='Path to a testcase file for visualization')
    parser.add_argument('--result', type=str, help='Path to a result file for visualization')
    
    args = parser.parse_args()
    
    # Set up Python virtual environment if it exists
    venv_path = os.path.join(os.path.dirname(__file__), '.venv')
    if os.path.exists(venv_path):
        print(f"Using Python virtual environment at {venv_path}")
        # Add the virtual environment's site-packages to sys.path
        venv_site_packages = os.path.join(venv_path, 'lib', f'python{sys.version_info.major}.{sys.version_info.minor}', 'site-packages')
        sys.path.insert(0, venv_site_packages)
    
    if args.testcase:
        if not os.path.exists(args.testcase):
            print(f"Testcase file {args.testcase} does not exist")
            sys.exit(1)
        visualize_testcase_map(args.testcase)
    elif args.result:
        if not os.path.exists(args.result):
            print(f"Result file {args.result} does not exist")
            sys.exit(1)
        visualize_result(args.result)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
