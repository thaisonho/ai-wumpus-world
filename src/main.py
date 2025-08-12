from environment.environment import WumpusWorldEnvironment
from environment.advanced_environment import AdvancedWumpusWorldEnvironment
from agent.agent import WumpusWorldAgent  # Import the intelligent agent
from utils.display import WumpusWorldDisplay
from utils.constants import (
    N_DEFAULT,
    K_DEFAULT,
    P_DEFAULT,
    GAME_STATE_PLAYING,
    GAME_STATE_WON,
    GAME_STATE_LOST,
)


def get_user_config():
    """Prompts the user for simulation settings."""
    try:
        N = int(input(f"Enter grid size N (default: {N_DEFAULT}): ") or N_DEFAULT)
        K = int(input(f"Enter number of Wumpuses K (default: {K_DEFAULT}): ") or K_DEFAULT)
        p = float(input(f"Enter pit probability p (default: {P_DEFAULT}): ") or P_DEFAULT)
        delay = float(input("Enter delay between steps (e.g., 0.2, default: 0.3): ") or 0.3)
        moving = input("Enable moving Wumpus? (y/N): ").strip().lower() in {"y", "yes"}
        return N, K, p, delay, moving
    except ValueError:
        print("Invalid input. Falling back to default values.")
        return N_DEFAULT, K_DEFAULT, P_DEFAULT, 0.3


def run_simulation(N=N_DEFAULT, K=K_DEFAULT, p=P_DEFAULT, delay=0.3, moving_wumpus=False):
    """
    Initializes and runs a Wumpus World simulation.

    Args:
        N (int): The size of the grid (N x N).
        K (int): The number of Wumpuses.
        p (float): The probability of a pit in any given cell.
        delay (float): The delay in seconds between simulation steps for visualization.
    """
    EnvClass = AdvancedWumpusWorldEnvironment if moving_wumpus else WumpusWorldEnvironment
    env = EnvClass(N, K, p)
    agent = WumpusWorldAgent(N)
    display = WumpusWorldDisplay(N)

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

        # 5. Sync the agent's state and display the result of the action
        env_state = env.get_current_state()
        agent.update_state(env_state)

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
    print(f"\nFinal Score: {env_state['score']}")
    print(f"Game State: {env_state['game_state']}")
    print("Press Enter to exit.")
    input()  # Wait for user confirmation to close


if __name__ == "__main__":
    N, K, p, delay, moving = get_user_config()
    run_simulation(N=N, K=K, p=p, delay=delay, moving_wumpus=moving)
