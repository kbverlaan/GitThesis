"""
Main simulation runner.
Orchestrates multi-agent games and saves results.
"""

import os
import sys
import yaml
import json
import time
from typing import Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from game.engine import GameEngine, GameState
from agents.llm_agent import LLMAgent


def load_config(config_path: str) -> dict:
    """Load YAML configuration file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def save_results(game_state: GameState, 
                 reasoning_traces: list,
                 output_dir: Path,
                 run_id: str):
    """Save simulation results to files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save game history
    history_file = output_dir / f"{run_id}_history.json"
    with open(history_file, 'w') as f:
        json.dump({
            "agents": game_state.agents,
            "final_resources": game_state.resources,
            "total_rounds": game_state.round_number,
            "history": game_state.history
        }, f, indent=2)
    
    # Save reasoning traces
    traces_file = output_dir / f"{run_id}_traces.json"
    with open(traces_file, 'w') as f:
        json.dump(reasoning_traces, f, indent=2)
    
    print(f"Results saved to {output_dir}")
    print(f"  - History: {history_file.name}")
    print(f"  - Traces: {traces_file.name}")


def run_simulation(game_params: dict, 
                   openrouter_config: dict,
                   run_id: Optional[str] = None) -> tuple:
    """
    Run a complete simulation.
    
    Args:
        game_params: Game parameters from config
        openrouter_config: OpenRouter API configuration
        run_id: Optional run identifier
        
    Returns:
        Tuple of (game_state, reasoning_traces)
    """
    if run_id is None:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print(f"\n{'='*60}")
    print(f"Starting simulation: {run_id}")
    print(f"{'='*60}\n")
    
    # Load API key
    api_key_env = openrouter_config['api_key_env_var']
    api_key = os.getenv(api_key_env)
    if not api_key:
        raise ValueError(f"API key not found in environment variable: {api_key_env}")
    
    # Create agent IDs
    agent_ids = [f"agent_{i+1}" for i in range(game_params['num_agents'])]
    
    # Initialize game engine
    engine = GameEngine(
        agent_ids=agent_ids,
        initial_resources=game_params['initial_resources'],
        invest_self_cost=game_params['invest_self_cost'],
        invest_self_return=game_params['invest_self_return'],
        invest_other_cost=game_params['invest_other_cost'],
        invest_other_return=game_params['invest_other_return'],
        arm_cost=game_params['arm_cost'],
        arm_multiplier=game_params['arm_multiplier'],
        arm_duration=game_params['arm_duration'],
        arm_other_contribution=game_params['arm_other_contribution'],
        arm_other_duration=game_params['arm_other_duration'],
        attack_take_percent=game_params['attack_take_percent'],
        conflict_cost=game_params['conflict_cost'],
        max_rounds=game_params['max_rounds']
    )
    
    # Initialize LLM agents
    agents = {}
    prompt_config = openrouter_config.get('prompt_config', {})
    
    for agent_id in agent_ids:
        agents[agent_id] = LLMAgent(
            agent_id=agent_id,
            api_key=api_key,
            model=openrouter_config['model'],
            prompt_config=prompt_config,
            game_params=game_params,
            temperature=openrouter_config['temperature'],
            max_tokens=openrouter_config['max_tokens'],
            timeout=openrouter_config['timeout'],
            retry_attempts=openrouter_config['retry_attempts'],
            retry_delay=openrouter_config['retry_delay']
        )
    
    print(f"Initialized {len(agents)} LLM agents")
    print(f"Model: {openrouter_config['model']}")
    print(f"Prompt config: {prompt_config}")
    print(f"Max rounds: {game_params['max_rounds']}\n")
    
    def can_afford_any_action(resources: float, game_params: Dict) -> bool:
        """Check if agent can afford any action."""
        min_cost = min(
            game_params['invest_self_cost'],
            game_params['invest_other_cost'],
            game_params['arm_cost'],
            game_params['conflict_cost']
        )
        return resources >= min_cost
    
    # Run simulation
    max_rounds = game_params['max_rounds']
    start_time = time.time()
    
    while not engine.is_game_over(max_rounds):
        state = engine.get_state()
        round_num = state.round_number
        
        print(f"\n{'='*70}")
        print(f"ROUND {round_num}/{max_rounds}")
        print(f"{'='*70}")
        
        # Show current resources at start of round
        print("\n📊 Current Resources:")
        for agent_id in agent_ids:
            armed_marker = " [ARMED]" if agent_id in state.active_arms else ""
            print(f"  {agent_id}: {state.resources[agent_id]:.1f}{armed_marker}")
        
        # Show coalitions
        if state.arm_coalitions:
            print("\n🤝 Active Coalitions:")
            for target_id, supporters in state.arm_coalitions.items():
                supporter_list = ", ".join([f"{s} (+{state.resources[s]*game_params['arm_other_contribution']:.1f})" 
                                           for s in supporters.keys()])
                print(f"  {target_id} supported by: {supporter_list}")
        
        print(f"\n🤔 Agent Decisions:")
        print("-" * 70)
        
        # Get actions from all agents (in parallel for speed)
        actions = []
        action_details = []  # Store for better display
        broke_agents = []  # Track agents who can't afford any action
        
        # Get history length from config
        history_length = game_params.get('history_length', 10)
        
        # First pass: identify broke agents
        active_agents = []
        for agent_id in agent_ids:
            agent_resources = state.resources[agent_id]
            if not can_afford_any_action(agent_resources, game_params):
                broke_agents.append(agent_id)
                action_details.append({
                    'agent': agent_id,
                    'action': None,
                    'reasoning': f"Cannot afford any action (has {agent_resources:.1f} resources, needs at least {min(game_params['invest_cost'], game_params['arm_cost'], game_params['conflict_cost']):.1f})"
                })
            else:
                active_agents.append(agent_id)
        
        # Second pass: call LLMs in parallel for active agents
        def get_agent_action(agent_id):
            observation = state.get_observation(agent_id, history_length)
            observation['broke_agents'] = broke_agents.copy()
            action = agents[agent_id].select_action(observation)
            
            # Get reasoning from the last trace
            agent_traces = agents[agent_id].get_reasoning_traces()
            reasoning = ""
            if agent_traces:
                last_trace = agent_traces[-1]
                response_text = last_trace.get('response', '')
                try:
                    start_idx = response_text.find('{')
                    end_idx = response_text.rfind('}') + 1
                    if start_idx >= 0 and end_idx > start_idx:
                        parsed = json.loads(response_text[start_idx:end_idx])
                        reasoning = parsed.get('reasoning', 'No reasoning provided')
                except:
                    reasoning = "Could not parse reasoning"
            
            return agent_id, action, reasoning
        
        # Execute LLM calls in parallel
        if active_agents:
            with ThreadPoolExecutor(max_workers=len(active_agents)) as executor:
                futures = {executor.submit(get_agent_action, agent_id): agent_id for agent_id in active_agents}
                
                for future in as_completed(futures):
                    agent_id, action, reasoning = future.result()
                    actions.append(action)
                    action_details.append({
                        'agent': agent_id,
                        'action': action,
                        'reasoning': reasoning
                    })
        
        # Sort action_details to maintain consistent agent order in display
        action_details.sort(key=lambda x: agent_ids.index(x['agent']))
        
        # Display all actions with reasoning
        for detail in action_details:
            agent_id = detail['agent']
            action = detail['action']
            reasoning = detail['reasoning']
            
            if action is None:
                # Broke agent
                print(f"\n{agent_id}:")
                print(f"  Action: [BROKE - NO ACTION]")
                print(f"  Status: {reasoning}")
            else:
                # Format action description
                action_desc = action.action_type.value
                if action.target_id:
                    action_desc += f" → {action.target_id}"
                
                print(f"\n{agent_id}:")
                print(f"  Action: {action_desc}")
                print(f"  Reasoning: {reasoning}")
        
        print(f"\n" + "-" * 70)
        
        # Resolve round
        round_result = engine.resolve_round(actions)
        
        # Show round results
        print(f"\n⚡ Round Results:")
        
        # Show rejected actions
        rejected = [a for a in round_result['actions'] if a.get('action') == 'no_action']
        if rejected:
            print("  ❌ Rejected actions (insufficient resources):")
            for action in rejected:
                print(f"    {action['agent']}: cannot afford their chosen action")
        
        # Show resource changes
        if round_result['resource_changes']:
            print("  Resource changes:")
            for agent_id, change in round_result['resource_changes'].items():
                if abs(change) > 0.01:  # Only show if meaningful change
                    sign = "+" if change > 0 else ""
                    new_total = state.resources[agent_id]
                    print(f"    {agent_id}: {sign}{change:.1f} (now: {new_total:.1f})")
        
        # Show combat results
        if round_result.get('combat_results'):
            print("\n  ⚔️  Combat outcomes:")
            for combat in round_result['combat_results']:
                winner_mark = "✓" if combat['winner'] == combat['attacker'] else "✗"
                print(f"    {combat['attacker']} vs {combat['defender']}: {combat['winner']} won {winner_mark}")
                print(f"      (Win probability: {combat['attacker_win_prob']:.1%})")
        
        print()
    
    elapsed = time.time() - start_time
    
    # Collect all reasoning traces
    all_traces = []
    for agent in agents.values():
        all_traces.extend(agent.get_reasoning_traces())
    
    # Final summary
    state = engine.get_state()
    rounds_played = state.round_number - 1  # Round number is incremented after last round
    print(f"\n{'='*70}")
    print("🏁 SIMULATION COMPLETE")
    print(f"{'='*70}")
    print(f"Total rounds: {rounds_played}")
    print(f"Time elapsed: {elapsed:.1f}s ({elapsed/rounds_played:.1f}s per round)")
    print(f"\n📈 Final Resources (sorted):")
    sorted_resources = sorted(state.resources.items(), key=lambda x: x[1], reverse=True)
    for rank, (agent_id, resources) in enumerate(sorted_resources, 1):
        print(f"  {rank}. {agent_id}: {resources:.1f}")
    
    # Calculate statistics
    total_resources = sum(state.resources.values())
    avg_resources = total_resources / len(state.resources)
    print(f"\n📊 Statistics:")
    print(f"  Total resources in system: {total_resources:.1f}")
    print(f"  Average per agent: {avg_resources:.1f}")
    
    # Count action types
    action_counts = {}
    for round_data in state.history:
        for action in round_data['actions']:
            action_type = action.get('action', 'unknown')
            action_counts[action_type] = action_counts.get(action_type, 0) + 1
    
    print(f"\n🎯 Action Distribution:")
    for action_type, count in sorted(action_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / sum(action_counts.values())) * 100
        print(f"  {action_type}: {count} ({pct:.1f}%)")
    
    print()
    
    return state, all_traces


def main():
    """Main entry point."""
    # Load environment variables
    load_dotenv()
    
    # Get project root
    project_root = Path(__file__).parent.parent
    
    # Load configurations
    game_params = load_config(project_root / "config" / "game_params.yaml")
    openrouter_config = load_config(project_root / "config" / "openrouter_config.yaml")
    
    # Run simulation
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    state, traces = run_simulation(game_params, openrouter_config, run_id)
    
    # Save results
    output_dir = project_root / "data" / "runs"
    save_results(state, traces, output_dir, run_id)


if __name__ == "__main__":
    main()
