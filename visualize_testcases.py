#!/usr/bin/env python3
# Visualize testcases and their results

import os
import sys
import json
import argparse
from pathlib import Path

# Add the src directory to the path so we can import the modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from utils.constants import (
    WUMPUS_SYMBOL,
    PIT_SYMBOL,
    GOLD_SYMBOL,
    AGENT_SYMBOL,
    DIRECTION_SYMBOLS,
    NORTH, EAST, SOUTH, WEST
)

def load_json_file(file_path):
    """Load a JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)

def print_map(game_map, agent_pos=None, agent_dir=None):
    """Print a visual representation of the map."""
    N = len(game_map)
    
    # Print the top border
    print("+" + "-" * (2 * N + 1) + "+")
    
    # Print the map rows in reverse order (y=N-1 at the top)
    for y in range(N-1, -1, -1):
        print("|", end=" ")
        for x in range(N):
            cell_content = ""
            
            # Add the agent if it's at this position
            if agent_pos and (x, y) == tuple(agent_pos):
                # Get direction symbol
                if agent_dir:
                    dir_symbol = ""
                    if tuple(agent_dir) == NORTH:
                        dir_symbol = "^"
                    elif tuple(agent_dir) == EAST:
                        dir_symbol = ">"
                    elif tuple(agent_dir) == SOUTH:
                        dir_symbol = "v"
                    elif tuple(agent_dir) == WEST:
                        dir_symbol = "<"
                    cell_content += dir_symbol
                else:
                    cell_content += "A"
            
            # Add wumpus, pit, and gold symbols
            cell = game_map[x][y]
            if isinstance(cell, str):
                if 'W' in cell:
                    cell_content += "W"
                if 'P' in cell:
                    cell_content += "P"
                if 'G' in cell:
                    cell_content += "G"
            else:  # Assuming it's a set
                if 'W' in cell or WUMPUS_SYMBOL in cell:
                    cell_content += "W"
                if 'P' in cell or PIT_SYMBOL in cell:
                    cell_content += "P"
                if 'G' in cell or GOLD_SYMBOL in cell:
                    cell_content += "G"
            
            # Print cell content or empty space
            if cell_content:
                print(cell_content, end=" ")
            else:
                print(".", end=" ")
        
        print("|")
    
    # Print the bottom border
    print("+" + "-" * (2 * N + 1) + "+")

def visualize_testcase(testcase_path):
    """Visualize a testcase."""
    testcase = load_json_file(testcase_path)
    
    N = testcase['N']
    
    # Create an empty map
    game_map = [[set() for _ in range(N)] for _ in range(N)]
    
    # Place wumpuses, pits, and gold
    for wx, wy in testcase.get('wumpus_positions', []):
        game_map[wx][wy].add('W')
    
    for px, py in testcase.get('pit_positions', []):
        game_map[px][py].add('P')
    
    gx, gy = testcase.get('gold_position')
    game_map[gx][gy].add('G')
    
    print(f"\n=== Testcase: {testcase.get('name', os.path.basename(testcase_path))} ===")
    print(f"Description: {testcase.get('description', 'No description')}")
    print(f"Map Size: {N}x{N}")
    print(f"Wumpuses: {len(testcase.get('wumpus_positions', []))}")
    print(f"Pits: {len(testcase.get('pit_positions', []))}")
    print(f"Gold Position: ({gx}, {gy})")
    print("\nMap:")
    print_map(game_map)

def visualize_result(result_path):
    """Visualize a testcase result."""
    result = load_json_file(result_path)
    
    testcase_config = result.get('config', {})
    steps = result.get('steps', [])
    final_state = result.get('final_state', {})
    
    print(f"\n=== Result: {os.path.basename(result_path)} ===")
    print(f"Testcase: {testcase_config.get('name', 'Unknown')}")
    print(f"Map Size: {testcase_config.get('N')}x{testcase_config.get('N')}")
    
    # Print final state information
    print("\n--- Final State ---")
    print(f"Game State: {final_state.get('game_state')}")
    print(f"Score: {final_state.get('score')}")
    print(f"Steps Used: {final_state.get('steps_used')}")
    print(f"Agent Position: {tuple(final_state.get('agent_pos', [0, 0]))}")
    print(f"Agent Has Gold: {final_state.get('agent_has_gold', False)}")
    
    # Print true map and agent's known map side by side
    print("\n--- Maps ---")
    print("True Map:")
    print_map(final_state.get('true_map', [[]]))
    print("\nAgent's Known Map:")
    print_map(final_state.get('agent_known_map', [[]]), 
              agent_pos=final_state.get('agent_pos'), 
              agent_dir=final_state.get('agent_dir', [1, 0]))
    
    # Ask if user wants to see step-by-step replay
    show_replay = input("\nShow step-by-step replay? (y/n): ").lower() == 'y'
    if show_replay:
        print("\n--- Step by Step Replay ---")
        for step in steps:
            print(f"\nStep {step.get('step')}:")
            print(f"Agent Position: {tuple(step.get('agent_pos', [0, 0]))}")
            print(f"Agent Direction: {step.get('agent_dir', [1, 0])}")
            print(f"Percepts: {', '.join(step.get('percepts', []))}")
            print(f"Action: {step.get('action')}")
            print(f"Result: {step.get('action_result', '')}")
            print(f"Score: {step.get('score', 0)}")
            
            input("Press Enter to continue...")

def list_available_files(directory, extension='.json'):
    """List all files with the given extension in the directory."""
    files = []
    for file in os.listdir(directory):
        if file.endswith(extension):
            files.append(os.path.join(directory, file))
    return files

def main():
    parser = argparse.ArgumentParser(description='Visualize Wumpus World testcases and results')
    parser.add_argument('--testcase', type=str, help='Path to a testcase file')
    parser.add_argument('--result', type=str, help='Path to a result file')
    parser.add_argument('--list', action='store_true', help='List available testcases and results')
    
    args = parser.parse_args()
    
    # Set up Python virtual environment if it exists
    venv_path = os.path.join(os.path.dirname(__file__), '.venv')
    if os.path.exists(venv_path):
        print(f"Using Python virtual environment at {venv_path}")
        # Add the virtual environment's site-packages to sys.path
        venv_site_packages = os.path.join(venv_path, 'lib', f'python{sys.version_info.major}.{sys.version_info.minor}', 'site-packages')
        sys.path.insert(0, venv_site_packages)
    
    testcases_dir = os.path.join(os.path.dirname(__file__), 'testcases')
    
    if args.list:
        # List available testcases and results
        print("=== Available Testcases ===")
        for category in ['small_map', 'medium_map', 'large_map']:
            category_dir = os.path.join(testcases_dir, category)
            if os.path.exists(category_dir):
                print(f"\n{category.replace('_', ' ').title()}:")
                for file in os.listdir(category_dir):
                    if file.endswith('.json') and not os.path.isdir(os.path.join(category_dir, file)):
                        print(f"  {file}")
                
                results_dir = os.path.join(category_dir, 'results')
                if os.path.exists(results_dir) and os.listdir(results_dir):
                    print(f"\n{category.replace('_', ' ').title()} Results:")
                    for file in os.listdir(results_dir):
                        if file.endswith('.json'):
                            print(f"  {file}")
    
    elif args.testcase:
        # Visualize a specific testcase
        if not os.path.exists(args.testcase):
            print(f"Error: Testcase file '{args.testcase}' does not exist.")
            return
        visualize_testcase(args.testcase)
    
    elif args.result:
        # Visualize a specific result
        if not os.path.exists(args.result):
            print(f"Error: Result file '{args.result}' does not exist.")
            return
        visualize_result(args.result)
    
    else:
        # Interactive mode
        print("\nWumpus World Testcase Visualizer")
        print("===============================")
        
        while True:
            print("\nOptions:")
            print("1. List available testcases")
            print("2. Visualize a testcase")
            print("3. Visualize a result")
            print("4. Exit")
            
            choice = input("\nEnter your choice (1-4): ")
            
            if choice == '1':
                # List available testcases and results
                print("\n=== Available Testcases ===")
                for category in ['small_map', 'medium_map', 'large_map']:
                    category_dir = os.path.join(testcases_dir, category)
                    if os.path.exists(category_dir):
                        print(f"\n{category.replace('_', ' ').title()}:")
                        for file in os.listdir(category_dir):
                            if file.endswith('.json') and not os.path.isdir(os.path.join(category_dir, file)):
                                print(f"  {file}")
                        
                        results_dir = os.path.join(category_dir, 'results')
                        if os.path.exists(results_dir) and os.listdir(results_dir):
                            print(f"\n{category.replace('_', ' ').title()} Results:")
                            for file in os.listdir(results_dir):
                                if file.endswith('.json'):
                                    print(f"  {file}")
            
            elif choice == '2':
                # Visualize a testcase
                category = input("\nEnter map category (small_map, medium_map, large_map): ")
                if category not in ['small_map', 'medium_map', 'large_map']:
                    print("Invalid category.")
                    continue
                
                category_dir = os.path.join(testcases_dir, category)
                if not os.path.exists(category_dir):
                    print(f"Category directory '{category_dir}' does not exist.")
                    continue
                
                testcase_files = [file for file in os.listdir(category_dir) 
                                 if file.endswith('.json') and not os.path.isdir(os.path.join(category_dir, file))]
                
                print("\nAvailable testcases:")
                for i, file in enumerate(testcase_files, 1):
                    print(f"{i}. {file}")
                
                try:
                    index = int(input("\nEnter the number of the testcase to visualize: ")) - 1
                    if 0 <= index < len(testcase_files):
                        visualize_testcase(os.path.join(category_dir, testcase_files[index]))
                    else:
                        print("Invalid index.")
                except ValueError:
                    print("Invalid input.")
            
            elif choice == '3':
                # Visualize a result
                category = input("\nEnter map category (small_map, medium_map, large_map): ")
                if category not in ['small_map', 'medium_map', 'large_map']:
                    print("Invalid category.")
                    continue
                
                results_dir = os.path.join(testcases_dir, category, 'results')
                if not os.path.exists(results_dir):
                    print(f"Results directory '{results_dir}' does not exist.")
                    continue
                
                result_files = [file for file in os.listdir(results_dir) if file.endswith('.json')]
                
                if not result_files:
                    print("No result files found. Run some testcases first.")
                    continue
                
                print("\nAvailable results:")
                for i, file in enumerate(result_files, 1):
                    print(f"{i}. {file}")
                
                try:
                    index = int(input("\nEnter the number of the result to visualize: ")) - 1
                    if 0 <= index < len(result_files):
                        visualize_result(os.path.join(results_dir, result_files[index]))
                    else:
                        print("Invalid index.")
                except ValueError:
                    print("Invalid input.")
            
            elif choice == '4':
                break
            
            else:
                print("Invalid choice.")

if __name__ == "__main__":
    main()
