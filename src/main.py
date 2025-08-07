from environment.environment import WumpusWorldEnvironment
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
    """Gets simulation configuration from the user."""
    try:
        N = int(input(f"Enter grid size N (default: {N_DEFAULT}): ") or N_DEFAULT)
        K = int(input(f"Enter number of Wumpuses K (default: {K_DEFAULT}): ") or K_DEFAULT)
        p = float(input(f"Enter pit probability p (default: {P_DEFAULT}): ") or P_DEFAULT)
        delay = float(input("Enter delay between steps (e.g., 0.2, default: 0.3): ") or 0.3)
        return N, K, p, delay
    except ValueError:
        print("Invalid input. Using default values.")
        return N_DEFAULT, K_DEFAULT, P_DEFAULT, 0.3


def run_simulation(N=N_DEFAULT, K=K_DEFAULT, p=P_DEFAULT, delay=0.3):
    """
    Runs a Wumpus World simulation with the intelligent agent.
    @param N: Grid size.
    :param K: Number of Wumpuses.
    :param p: Pit probability.
    :param delay: Delay between steps for visualization.
    """
    env = WumpusWorldEnvironment(N, K, p)
    agent = WumpusWorldAgent(N)  # Instantiate the intelligent agent
    display = WumpusWorldDisplay(N)

    step_count = 0
    max_steps = 500  # Increased max steps for intelligent agent

    while env.game_state == GAME_STATE_PLAYING and step_count < max_steps:
        step_count += 1

        # Get current percepts from the environment
        current_percepts = env.get_percepts()

        # Sync agent's basic state with environment
        env_state = env.get_current_state()
        agent.update_state(env_state)

        # Display the current state, including agent's KB
        display.display_map(
            agent_known_map=agent.get_known_map(),  # Pass agent's known map
            agent_kb_status=agent.get_kb_status(),  # Pass agent's KB status
            agent_pos=agent.agent_pos,
            agent_dir=agent.agent_dir,
            agent_has_gold=agent.agent_has_gold,
            score=agent.score,
            percepts=current_percepts,
            message=f"Step {step_count}: Agent is deciding...",
        )
        display.pause(delay)

        # Agent decides action based on percepts and its internal KB
        chosen_action = agent.decide_action(current_percepts)

        # Apply the chosen action to the environment
        action_message = env.apply_action(chosen_action)

        # Display the state after action
        env_state = (
            env.get_current_state()
        )  # Get updated env state for final display of this turn
        agent.update_state(
            env_state
        )  # Sync agent's state one last time for display consistency

        display.display_map(
            agent_known_map=agent.get_known_map(),
            agent_kb_status=agent.get_kb_status(),
            agent_pos=agent.agent_pos,
            agent_dir=agent.agent_dir,
            agent_has_gold=agent.agent_has_gold,
            score=agent.score,
            percepts=env.last_percepts,  # Use env's last_percepts which includes Bump if it happened
            message=f"Step {step_count}: Action: {chosen_action}. Outcome: {action_message}",
        )
        display.pause(delay)

    # Final display after game ends
    env_state = env.get_current_state()
    agent.update_state(env_state)  # Final sync
    final_message = ""
    if env_state["game_state"] == GAME_STATE_WON:
        final_message = "Simulation Ended: Agent WON!"
    elif env_state["game_state"] == GAME_STATE_LOST:
        final_message = "Simulation Ended: Agent LOST!"
    else:
        final_message = "Simulation Ended: Max steps reached."

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
    input()  # Keep the final display on screen until user presses Enter


if __name__ == "__main__":
    N, K, p, delay = get_user_config()
    run_simulation(N=N, K=K, p=p, delay=delay)
