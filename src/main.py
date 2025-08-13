from environment.environment import WumpusWorldEnvironment
from environment.advanced_environment import AdvancedWumpusWorldEnvironment
from agent.agent import WumpusWorldAgent  # Import the intelligent agent with inference capability
from utils.display import WumpusWorldDisplay  # Text-based display fallback
from utils.gui import WumpusWorldGUI  # Graphical user interface
from utils.constants import (
    N_DEFAULT,
    K_DEFAULT,
    P_DEFAULT,
    GAME_STATE_PLAYING,
    GAME_STATE_WON,
    GAME_STATE_LOST,
    PERCEPT_SCREAM,
    WUMPUS_SYMBOL,
    PIT_SYMBOL,
    GOLD_SYMBOL,
)


def get_user_config():
    """Prompts the user for simulation settings."""
    try:
        print("\n===== Wumpus World Simulation Configuration =====\n")
        
        print("Grid size determines the NxN dimensions of the world.")
        N = int(input(f"Enter grid size N (4-15, default: {N_DEFAULT}): ") or N_DEFAULT)
        N = max(4, min(15, N))  # Clamp between 4 and 15 for reasonable display
        
        print("\nNumber of Wumpuses affects difficulty (more wumpuses = harder).")
        K = int(input(f"Enter number of Wumpuses K (1-{N//2}, default: {K_DEFAULT}): ") or K_DEFAULT)
        K = max(1, min(N//2, K))  # Clamp to reasonable values
        
        print("\nPit probability affects how many pits appear in the world.")
        p = float(input(f"Enter pit probability p (0.0-0.3, default: {P_DEFAULT}): ") or P_DEFAULT)
        p = max(0.0, min(0.3, p))  # Clamp to reasonable values
        
        print("\nDelay controls how fast the simulation runs (smaller = faster).")
        delay = float(input("Enter delay between steps (0.0-1.0, default: 0.3): ") or 0.3)
        delay = max(0.0, min(1.0, delay))  # Clamp to reasonable values
        
        print("\nMoving wumpuses can change positions during the game (harder).")
        moving = input("Enable moving Wumpus? (y/N): ").strip().lower() in {"y", "yes"}
        
        print("\nChoose between graphical interface (GUI) or text display.")
        use_gui = input("Use GUI? (Y/n): ").strip().lower() not in {"n", "no"}
        
        print("\nConfiguration complete! Starting simulation...\n")
        
        return N, K, p, delay, moving, use_gui
    except ValueError:
        print("Invalid input. Falling back to default values.")
        return N_DEFAULT, K_DEFAULT, P_DEFAULT, 0.3, False, True


def run_simulation(N=N_DEFAULT, K=K_DEFAULT, p=P_DEFAULT, delay=0.3, moving_wumpus=False, use_gui=True):
    """
    Initializes and runs a Wumpus World simulation.

    Args:
        N (int): The size of the grid (N x N).
        K (int): The number of Wumpuses.
        p (float): The probability of a pit in any given cell.
        delay (float): The delay in seconds between simulation steps for visualization.
        moving_wumpus (bool): Whether wumpuses should move around.
        use_gui (bool): Whether to use the GUI (True) or text display (False).
    """
    EnvClass = AdvancedWumpusWorldEnvironment if moving_wumpus else WumpusWorldEnvironment
    env = EnvClass(N, K, p)
    agent = WumpusWorldAgent(N)
    
    # Choose between GUI and text display
    if use_gui:
        display = WumpusWorldGUI(N)
        print("Using graphical display (pygame)")
    else:
        display = WumpusWorldDisplay(N)

    # For GUI: Initialize with the true environment state for visualization
    if hasattr(env, 'game_map') and hasattr(display, 'update_environment_state'):
        # Create a complete map of the environment for GUI rendering
        env_map = [[''] * N for _ in range(N)]
        for y in range(N):
            for x in range(N):
                if 'W' in env.game_map[x][y]:
                    env_map[x][y] += WUMPUS_SYMBOL
                    # Debug print to verify wumpus positions
                    print(f"Initial Wumpus at ({x}, {y})")
                if 'P' in env.game_map[x][y]:
                    env_map[x][y] += PIT_SYMBOL
                if 'G' in env.game_map[x][y]:
                    env_map[x][y] += GOLD_SYMBOL
        
        # Call a special initialization method for the first update
        if hasattr(display, 'initialize_environment'):
            display.initialize_environment(env_map)
        else:
            display.update_environment_state(env_map)

    step_count = 0
    max_steps = 500  # A safeguard against infinite loops.

    # Main game loop
    while env.game_state == GAME_STATE_PLAYING and step_count < max_steps:
        step_count += 1

        # 1. Agent perceives the environment
        current_percepts = env.get_percepts()
        env_state = env.get_current_state()
        agent.update_state(env_state)

        # 2. Display the world from the agent's perspective before acting
        display.display_map(
            agent_known_map=agent.get_known_map(),
            agent_kb_status=agent.get_kb_status(),
            agent_pos=agent.agent_pos,
            agent_dir=agent.agent_dir,
            agent_has_gold=agent.agent_has_gold,
            score=agent.score,
            percepts=current_percepts,
            message=f"Step {step_count}: Agent is thinking...",
        )
        display.pause(delay)

        # 3. Agent makes a decision
        chosen_action = agent.decide_action(current_percepts)

        # 4. The environment processes the action
        action_message = env.apply_action(chosen_action)
        
        # Check for wumpus scream to mark killed wumpuses
        if hasattr(display, 'mark_wumpus_killed') and PERCEPT_SCREAM in env.last_percepts:
            # When a scream is heard, it means a wumpus was killed
            # We need to determine which wumpus was killed
            
            if hasattr(agent, 'last_shoot_dir') and agent.last_shoot_dir:
                # If the agent has a record of the last shoot direction, use it
                shoot_dir = agent.last_shoot_dir
            else:
                # Default to the agent's current direction
                shoot_dir = agent.agent_dir
            
            # Get the map knowledge to find wumpuses
            agent_known_map = agent.get_known_map()
            
            # Find wumpuses in the path of the arrow
            shot_x, shot_y = agent.agent_pos
            
            # Look for wumpuses in the direction of the shot
            killed_wumpus = False
            for i in range(N):  # Maximum arrow distance is N cells
                shot_x += shoot_dir[0]
                shot_y += shoot_dir[1]
                
                # Check if we're still in bounds
                if 0 <= shot_x < N and 0 <= shot_y < N:
                    if WUMPUS_SYMBOL in agent_known_map[shot_x][shot_y]:
                        # Mark this wumpus as killed
                        display.mark_wumpus_killed((shot_x, shot_y))
                        killed_wumpus = True
                        break
                else:
                    # Arrow went out of bounds
                    break
            
            # If no specific wumpus was found in the path, mark all known wumpuses
            # This is a fallback in case the arrow path determination isn't accurate
            if not killed_wumpus:
                for x in range(N):
                    for y in range(N):
                        if WUMPUS_SYMBOL in agent_known_map[x][y]:
                            # Mark this wumpus as killed
                            display.mark_wumpus_killed((x, y))
                            break  # Just mark one wumpus

        # 5. Sync the agent's state and display the result of the action
        env_state = env.get_current_state()
        agent.update_state(env_state)
        
        # For GUI: Update with the latest environment state, especially important for moving wumpuses
        if hasattr(env, 'game_map') and hasattr(display, 'update_environment_state'):
            # Update the environment map for GUI rendering
            env_map = [[''] * N for _ in range(N)]
            
            # Ensure we catch all elements in the game map
            for y in range(N):
                for x in range(N):
                    # Clear any previous content at this position to ensure clean updates
                    env_map[x][y] = ''
                    
                    # Add current elements from the game map
                    if 'W' in env.game_map[x][y]:
                        env_map[x][y] += WUMPUS_SYMBOL
                    if 'P' in env.game_map[x][y]:
                        env_map[x][y] += PIT_SYMBOL
                    if 'G' in env.game_map[x][y]:
                        env_map[x][y] += GOLD_SYMBOL
            
            # Update the GUI with the complete current state
            display.update_environment_state(env_map)

        display.display_map(
            agent_known_map=agent.get_known_map(),
            agent_kb_status=agent.get_kb_status(),
            agent_pos=agent.agent_pos,
            agent_dir=agent.agent_dir,
            agent_has_gold=agent.agent_has_gold,
            score=agent.score,
            percepts=env.last_percepts,  # Use last_percepts to include bumps
            message=f"Step {step_count}: Action: {chosen_action}. Result: {action_message}",
        )
        display.pause(delay)

    # --- Game Over ---
    # Final sync and display
    env_state = env.get_current_state()
    agent.update_state(env_state)

    if env_state["game_state"] == GAME_STATE_WON:
        final_message = "Simulation Ended: The agent won!"
    elif env_state["game_state"] == GAME_STATE_LOST:
        final_message = "Simulation Ended: The agent lost."
    else:
        final_message = "Simulation Ended: Maximum steps reached."

    display.display_map(
        agent_known_map=agent.get_known_map(),
        agent_kb_status=agent.get_kb_status(),
        agent_pos=agent.agent_pos,
        agent_dir=agent.agent_dir,
        agent_has_gold=agent.agent_has_gold,
        score=agent.score,
        percepts=env.last_percepts,
        message=final_message,
    )
    
    # Show final results
    print(f"\nFinal Score: {env_state['score']}")
    print(f"Game State: {env_state['game_state']}")
    
    if hasattr(display, 'wait_for_key'):
        # For GUI, wait for a key press
        print("Press any key to exit.")
        display.wait_for_key()
    else:
        # For text display, wait for Enter
        print("Press Enter to exit.")
        input()
    
    # Clean up resources if using GUI
    if hasattr(display, 'cleanup'):
        display.cleanup()


if __name__ == "__main__":
    N, K, p, delay, moving, use_gui = get_user_config()
    run_simulation(N=N, K=K, p=p, delay=delay, moving_wumpus=moving, use_gui=use_gui)
