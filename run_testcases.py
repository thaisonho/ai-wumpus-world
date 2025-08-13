#!/usr/bin/env python3
# Run testcases with specific map configurations

import os
import sys
import json
import argparse
import datetime
from pathlib import Path
from typing import Set, Dict, List, Any

# Add the src directory to the path so we can import the modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from environment.environment import WumpusWorldEnvironment
from agent.agent import WumpusWorldAgent
from utils.display import WumpusWorldDisplay
from utils.constants import (
    GAME_STATE_PLAYING,
    GAME_STATE_WON,
    GAME_STATE_LOST,
    PERCEPT_SCREAM,
    WUMPUS_SYMBOL,
    PIT_SYMBOL,
    GOLD_SYMBOL,
)

def load_testcase(testcase_file):
    """Load testcase configuration from a JSON file."""
    with open(testcase_file, 'r') as f:
        testcase = json.load(f)
    return testcase

def create_custom_environment(config):
    """Create a custom environment with a predefined map."""
    N = config.get('N')
    env = WumpusWorldEnvironment(N, 0, 0)  # K and p don't matter as we'll manually set the map
    
    # Initialize empty map
    env.game_map = [[set() for _ in range(N)] for _ in range(N)]
    
    # Place wumpuses
    for wx, wy in config.get('wumpus_positions', []):
        env.game_map[wx][wy].add(WUMPUS_SYMBOL)
    
    # Place pits
    for px, py in config.get('pit_positions', []):
        env.game_map[px][py].add(PIT_SYMBOL)
    
    # Place gold
    gx, gy = config.get('gold_position')
    env.game_map[gx][gy].add(GOLD_SYMBOL)
    
    return env

def run_testcase(testcase_path, use_gui=False):
    """Run a specific testcase and return the results."""
    testcase = load_testcase(testcase_path)
    
    # Create environment from testcase config
    env = create_custom_environment(testcase)
    N = testcase.get('N')
    
    # Create agent
    agent = WumpusWorldAgent(N)
    
    # Use text display for logging
    display = WumpusWorldDisplay(N)
    
    # Initialize log
    log = {
        "testcase_name": os.path.basename(testcase_path),
        "config": testcase,
        "steps": [],
        "final_state": None,
    }
    
    # Main simulation loop
    step_count = 0
    max_steps = 500
    
    while env.game_state == GAME_STATE_PLAYING and step_count < max_steps:
        step_count += 1
        
        # Get percepts and current state
        current_percepts = env.get_percepts()
        env_state = env.get_current_state()
        agent.update_state(env_state)
        
        # Log agent knowledge and percepts before action
        step_log = {
            "step": step_count,
            "agent_pos": agent.agent_pos,
            "agent_dir": agent.agent_dir,
            "agent_has_gold": agent.agent_has_gold,
            "percepts": current_percepts,
            "score": agent.score,
        }
        
        # Agent makes a decision
        chosen_action = agent.decide_action(current_percepts)
        step_log["action"] = chosen_action
        
        # Environment processes the action
        action_result = env.apply_action(chosen_action)
        step_log["action_result"] = action_result
        
        # Update agent state after action
        env_state = env.get_current_state()
        agent.update_state(env_state)
        
        # Add step to log
        log["steps"].append(step_log)
    
    # Final state
    log["final_state"] = {
        "game_state": env.game_state,
        "score": agent.score,
        "steps_used": step_count,
        "agent_pos": agent.agent_pos,
        "agent_has_gold": agent.agent_has_gold,
        "agent_known_map": agent.get_known_map(),
        "true_map": env.get_true_map()
    }
    
    return log

class SetEncoder(json.JSONEncoder):
    """Custom JSON encoder that can handle sets by converting them to lists."""
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)

def save_log(log, output_dir):
    """Save the log to a file."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    testcase_name = log["testcase_name"].replace('.json', '')
    log_filename = f"{testcase_name}_{timestamp}.json"
    log_path = os.path.join(output_dir, log_filename)
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Convert sets to lists for JSON serialization
    def convert_sets_to_lists(obj):
        if isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, list):
            return [convert_sets_to_lists(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: convert_sets_to_lists(value) for key, value in obj.items()}
        else:
            return obj
    
    # Convert all sets in the log to lists for JSON serialization
    serializable_log = convert_sets_to_lists(log)
    
    # Save log with custom encoder for any remaining sets
    with open(log_path, 'w') as f:
        json.dump(serializable_log, f, indent=2, cls=SetEncoder)
    
    print(f"Log saved to {log_path}")
    return log_path

def run_all_testcases():
    """Run all testcases in the testcases directory."""
    testcases_dir = os.path.join(os.path.dirname(__file__), 'testcases')
    categories = ['small_map', 'medium_map', 'large_map']
    
    for category in categories:
        category_dir = os.path.join(testcases_dir, category)
        output_dir = os.path.join(testcases_dir, category, 'results')
        
        if not os.path.exists(category_dir):
            print(f"Directory {category_dir} does not exist, skipping...")
            continue
        
        # Get all JSON files in the category directory
        testcases = [f for f in os.listdir(category_dir) if f.endswith('.json')]
        
        for testcase in testcases:
            testcase_path = os.path.join(category_dir, testcase)
            print(f"Running testcase: {testcase}")
            
            try:
                log = run_testcase(testcase_path)
                save_log(log, output_dir)
            except Exception as e:
                print(f"Error running testcase {testcase}: {e}")

def main():
    parser = argparse.ArgumentParser(description='Run Wumpus World testcases')
    parser.add_argument('--all', action='store_true', help='Run all testcases')
    parser.add_argument('--testcase', type=str, help='Path to a specific testcase file')
    
    args = parser.parse_args()
    
    # Set up Python virtual environment if it exists
    venv_path = os.path.join(os.path.dirname(__file__), '.venv')
    if os.path.exists(venv_path):
        print(f"Using Python virtual environment at {venv_path}")
        # Add the virtual environment's site-packages to sys.path
        venv_site_packages = os.path.join(venv_path, 'lib', f'python{sys.version_info.major}.{sys.version_info.minor}', 'site-packages')
        sys.path.insert(0, venv_site_packages)
    
    if args.all:
        run_all_testcases()
    elif args.testcase:
        if not os.path.exists(args.testcase):
            print(f"Testcase file {args.testcase} does not exist")
            sys.exit(1)
            
        testcase_dir = os.path.dirname(args.testcase)
        output_dir = os.path.join(testcase_dir, 'results')
        log = run_testcase(args.testcase)
        save_log(log, output_dir)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
