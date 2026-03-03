"""
Main simulation runner.
Orchestrates multi-agent games and saves results.
"""

import os
import sys
import yaml
import json
import time
import platform
import random
import numpy as np
from typing import Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from game.engine import GameEngine, GameState
from game.spatial import NetworkTopology
from agents.llm_agent import LLMAgent
from analysis.metrics import compute_round_metrics, check_early_stopping
from analysis.network import analyze_run_networks


def load_config(config_path: str) -> dict:
    """Load YAML configuration file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def save_results(game_state: GameState,
                 reasoning_traces: list,
                 round_metrics: list,
                 output_dir: Path,
                 run_id: str,
                 run_metadata: Optional[dict] = None):
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

    # Save reasoning traces (with token usage, latency, errors)
    traces_file = output_dir / f"{run_id}_traces.json"
    with open(traces_file, 'w') as f:
        json.dump(reasoning_traces, f, indent=2)

    # Save per-round metrics
    metrics_file = output_dir / f"{run_id}_metrics.json"
    with open(metrics_file, 'w') as f:
        json.dump(round_metrics, f, indent=2)

    # Run network analysis (Leiden communities, ingroup/outgroup, hierarchy)
    if game_state.history:
        try:
            network_results = analyze_run_networks(
                game_state.history, window_size=5, resolution=1.0
            )
            # Serialize: strip networkx objects, keep only JSON-safe data
            network_output = {
                'metrics_per_window': network_results['metrics_per_window'],
                'communities_per_window': [
                    {
                        'window': cw['window'],
                        'partition': [sorted(list(s)) for s in cw['partition']],
                        'modularity': cw.get('modularity', 0.0),
                        'n_communities': cw.get('n_communities', 0),
                    }
                    for cw in network_results['communities_per_window']
                ],
                'community_stability': network_results['community_stability'],
                'hierarchy_metrics': {
                    k: v for k, v in network_results['hierarchy_metrics'].items()
                    if k != 'david_scores'  # david_scores saved separately (large)
                },
                'david_scores': network_results['hierarchy_metrics'].get('david_scores', {}),
                'elo_ratings': {
                    'final_ratings': network_results['elo_ratings'].get('final_ratings', {}),
                    'steepness': network_results['elo_ratings'].get('steepness', 0.0),
                    'landau_h': network_results['elo_ratings'].get('landau_h', 0.0),
                },
                'ingroup_outgroup_per_window': network_results['ingroup_outgroup_per_window'],
                'ingroup_outgroup_overall': network_results['ingroup_outgroup_overall'],
            }
            # Strip non-serializable centrality dicts from metrics_per_window
            for mw in network_output['metrics_per_window']:
                mw.pop('betweenness_centrality', None)
                mw.pop('eigenvector_centrality', None)

            network_file = output_dir / f"{run_id}_network.json"
            with open(network_file, 'w') as f:
                json.dump(network_output, f, indent=2)
            print(f"  - Network: {network_file.name}")
        except Exception as e:
            print(f"  - Network analysis failed: {e}")

    # Save run metadata (seed, tokens, system info)
    if run_metadata:
        meta_file = output_dir / f"{run_id}_meta.json"
        with open(meta_file, 'w') as f:
            json.dump(run_metadata, f, indent=2)

    print(f"Results saved to {output_dir}")
    print(f"  - History: {history_file.name}")
    print(f"  - Traces: {traces_file.name}")
    print(f"  - Metrics: {metrics_file.name}")
    if run_metadata:
        print(f"  - Metadata: {run_id}_meta.json")


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

    # Set and log random seed for reproducibility
    seed = game_params.get('random_seed', None)
    if seed is None:
        seed = int.from_bytes(os.urandom(4), 'big')
    np.random.seed(seed)
    random.seed(seed)

    print(f"\n{'='*60}")
    print(f"Starting simulation: {run_id}")
    print(f"{'='*60}\n")
    print(f"Random seed: {seed}")
    
    # Load API key (optional for local vLLM endpoints)
    api_key_env = openrouter_config.get('api_key_env_var', '')
    api_key = os.getenv(api_key_env) if api_key_env else None
    base_url = openrouter_config.get('base_url', 'https://openrouter.ai/api/v1')

    if not api_key and 'openrouter.ai' in base_url:
        raise ValueError(f"API key not found in environment variable: {api_key_env}")
    if not api_key:
        api_key = "none"  # vLLM doesn't require an API key
    
    # Create agent IDs
    agent_ids = [f"agent_{i+1}" for i in range(game_params['num_agents'])]

    # Build initial resource distribution
    dist_type = game_params.get('initial_distribution', 'equal')
    base_resources = game_params['initial_resources']
    n = len(agent_ids)
    total = base_resources * n

    if dist_type == 'unequal':
        # 1 rich agent, rest share remainder equally
        rich_share = total * 0.4
        poor_share = (total - rich_share) / (n - 1)
        initial_resources = {agent_ids[0]: rich_share}
        for aid in agent_ids[1:]:
            initial_resources[aid] = poor_share
    elif dist_type == 'random':
        raw = np.random.uniform(5, 45, size=n)
        scaled = raw / raw.sum() * total
        initial_resources = {aid: float(s) for aid, s in zip(agent_ids, scaled)}
    else:  # 'equal'
        initial_resources = base_resources

    # Initialize game engine (param names match prompt — see prompts.py _format_actions)
    engine = GameEngine(
        agent_ids=agent_ids,
        initial_resources=initial_resources,
        invest_self_pct=game_params.get('invest_self_pct', 2),
        invest_other_cost_pct=game_params.get('invest_other_cost_pct', 10),
        invest_other_return_pct=game_params.get('invest_other_return_pct', 15),
        arm_cost_pct=game_params.get('arm_cost_pct', 10),
        arm_multiplier=game_params.get('arm_multiplier', 2.0),
        arm_other_cost_pct=game_params.get('arm_other_cost_pct', None),
        arm_decay=game_params.get('arm_decay', 0.5),
        attack_take_pct=game_params.get('attack_take_pct', 40),
        conflict_cost_pct=game_params.get('conflict_cost_pct', 5),
        max_rounds=game_params['max_rounds'],
    )

    # Initialize network topology if enabled
    network_enabled = game_params.get('network_enabled', game_params.get('spatial_enabled', False))
    network = None
    if network_enabled:
        mean_degree = game_params.get('mean_degree', 5.0)
        rewiring_prob = game_params.get('rewiring_prob', 0.0)
        payoff_window = game_params.get('payoff_window', 5)
        network = NetworkTopology(agent_ids, mean_degree, rewiring_prob, payoff_window)
        degree_stats = network.get_degree_stats()
        print(f"Network topology: ER graph, ⟨k⟩={degree_stats['mean']:.1f} "
              f"(target {mean_degree}), w={rewiring_prob}, "
              f"degree range [{degree_stats['min']}, {degree_stats['max']}]")

    # Initialize LLM agents
    agents = {}
    prompt_config = openrouter_config.get('prompt_config', {})
    memory_config = game_params.get('memory', {})

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
            retry_delay=openrouter_config['retry_delay'],
            base_url=base_url,
            memory_config=memory_config
        )
    
    print(f"Initialized {len(agents)} LLM agents")
    print(f"Model: {openrouter_config['model']}")
    print(f"Prompt config: {prompt_config}")
    print(f"Max rounds: {game_params['max_rounds']}\n")
    
    def can_afford_any_action(resources: float, game_params: Dict) -> bool:
        """Check if agent can afford any action (all costs are %-based)."""
        return resources > 0.01
    
    # Run simulation
    max_rounds = game_params['max_rounds']
    action_order = game_params.get('action_order', 'simultaneous')

    # Early stopping config (Two-Phase Adaptive; Lee et al. 2015, JASSS 18(4))
    early_stop_cfg = game_params.get('early_stopping', {})
    early_stop_enabled = early_stop_cfg.get('enabled', False)
    early_stopped = False
    early_stop_reason = None
    if early_stop_enabled:
        max_rounds = early_stop_cfg.get('max_rounds', max_rounds)
        es_min_rounds = early_stop_cfg.get('min_rounds', 15)
        es_patience = early_stop_cfg.get('patience', 5)
        es_gini_threshold = early_stop_cfg.get('gini_threshold', 0.01)
        es_entropy_threshold = early_stop_cfg.get('entropy_threshold', 0.05)
        print(f"Early stopping: enabled (min={es_min_rounds}, max={max_rounds}, "
              f"patience={es_patience}, gini_thr={es_gini_threshold}, "
              f"entropy_thr={es_entropy_threshold})")

    start_time = time.time()
    all_round_metrics = []
    previous_actions_map = None
    resource_changes_history = []  # For network rewiring payoff window

    while not engine.is_game_over(max_rounds):
        state = engine.get_state()
        round_num = state.round_number
        
        print(f"\n{'='*70}")
        print(f"ROUND {round_num}/{max_rounds}")
        print(f"{'='*70}")

        # Network rewiring happens at END of round (after resource updates)
        # No movement step needed — network is static within a round

        # Show current resources at start of round
        print("\n📊 Current Resources:")
        for agent_id in agent_ids:
            bonus = state.arm_bonuses.get(agent_id, 0)
            armed_marker = f" [ARM +{bonus:.1f}]" if bonus > 0 else ""
            print(f"  {agent_id}: {state.resources[agent_id]:.1f}{armed_marker}")
        
        print(f"\n🤔 Agent Decisions:")
        print("-" * 70)
        
        # Get history length from config
        history_length = game_params.get('history_length', 10)

        def get_agent_action(agent_id, current_state):
            observation = current_state.get_observation(agent_id, history_length)
            observation['broke_agents'] = [
                aid for aid in agent_ids
                if not can_afford_any_action(current_state.resources[aid], game_params)
            ]
            # Add network topology info if enabled
            if network:
                neighbors = network.get_neighbors(agent_id)
                observation['visible_agents'] = neighbors
            # Inject memory into observation for prompt formatting
            if agents[agent_id].memory is not None:
                observation['agent_memory'] = agents[agent_id].memory

            action = agents[agent_id].select_action(observation)

            agent_traces = agents[agent_id].get_reasoning_traces()
            reasoning = ""
            if agent_traces:
                last_trace = agent_traces[-1]
                # Prefer the 'thinking' field (populated by vLLM reasoning parser
                # for models like Qwen3.5 that use <think> tokens)
                thinking = last_trace.get('thinking', '') or ''
                if thinking:
                    # Truncate for log display (full trace saved in traces JSON)
                    reasoning = thinking[:2000] + ('...' if len(thinking) > 2000 else '')
                else:
                    # Fallback: try to extract reasoning from JSON response body
                    response_text = last_trace.get('response', '') or ''
                    try:
                        import re
                        clean_text = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL)
                        start_idx = clean_text.find('{')
                        end_idx = clean_text.rfind('}') + 1
                        if start_idx >= 0 and end_idx > start_idx:
                            parsed = json.loads(clean_text[start_idx:end_idx])
                            reasoning = parsed.get('reasoning', 'No reasoning provided')
                    except:
                        reasoning = "Could not parse reasoning"

            return agent_id, action, reasoning

        if action_order == 'sequential':
            # Sequential: random order, resolve each action immediately
            order = list(agent_ids)
            np.random.shuffle(order)
            round_log = {"round": state.round_number, "actions": [], "resource_changes": {}, "combat_results": []}
            all_actions_this_round = []

            for agent_id in order:
                current_state = engine.get_state()
                if not can_afford_any_action(current_state.resources[agent_id], game_params):
                    print(f"\n{agent_id}: [BROKE - NO ACTION]")
                    round_log["actions"].append({"agent": agent_id, "action": "no_action", "reason": "insufficient_resources"})
                    continue

                agent_id, action, reasoning = get_agent_action(agent_id, current_state)
                action_desc = action.action_type.value + (f" → {action.target_id}" if action.target_id else "")
                print(f"\n{agent_id}: {action_desc}")
                print(f"  Reasoning: {reasoning}")

                result = engine.resolve_single_action(action)
                round_log["actions"].extend(result["actions"])
                round_log["combat_results"].extend(result.get("combat_results", []))
                all_actions_this_round.append(action)

                # Show immediate result for attacks
                for combat in result.get("combat_results", []):
                    attackers_str = ",".join(combat.get('attackers', []))
                    winner_mark = "✓" if combat['winner'] == 'coalition' else "✗"
                    print(f"    ⚔️ {attackers_str} vs {combat['defender']}: {combat['winner']} won {winner_mark} ({combat['attacker_win_prob']:.1%})")

            # Tick arms and advance round
            engine.tick_arms()
            engine.advance_round(round_log)
            round_result = round_log

        else:
            # Simultaneous: parallel decisions, batch resolution
            actions = []
            action_details = []
            broke_agents = [
                aid for aid in agent_ids
                if not can_afford_any_action(state.resources[aid], game_params)
            ]
            active_agents = [aid for aid in agent_ids if aid not in broke_agents]

            if active_agents:
                with ThreadPoolExecutor(max_workers=len(active_agents)) as executor:
                    futures = {executor.submit(get_agent_action, aid, state): aid for aid in active_agents}
                    for future in as_completed(futures):
                        agent_id, action, reasoning = future.result()
                        actions.append(action)
                        action_details.append({'agent': agent_id, 'action': action, 'reasoning': reasoning})

            action_details.sort(key=lambda x: agent_ids.index(x['agent']))

            for detail in action_details:
                action_desc = detail['action'].action_type.value
                if detail['action'].target_id:
                    action_desc += f" → {detail['action'].target_id}"
                print(f"\n{detail['agent']}:")
                print(f"  Action: {action_desc}")
                print(f"  Reasoning: {detail['reasoning']}")

            for aid in broke_agents:
                print(f"\n{aid}: [BROKE - NO ACTION]")

            print(f"\n" + "-" * 70)

            round_result = engine.resolve_round(actions)

            # Show round results
            print(f"\n⚡ Round Results:")
            if round_result['resource_changes']:
                print("  Resource changes:")
                for agent_id, change in round_result['resource_changes'].items():
                    if abs(change) > 0.01:
                        sign = "+" if change > 0 else ""
                        new_total = state.resources[agent_id]
                        print(f"    {agent_id}: {sign}{change:.1f} (now: {new_total:.1f})")

            if round_result.get('combat_results'):
                print("\n  ⚔️  Combat outcomes:")
                for combat in round_result['combat_results']:
                    attackers_str = ",".join(combat.get('attackers', []))
                    winner_mark = "✓" if combat['winner'] == 'coalition' else "✗"
                    print(f"    {attackers_str} vs {combat['defender']}: {combat['winner']} won {winner_mark}")
                    print(f"      (Win probability: {combat['attacker_win_prob']:.1%})")

        # Compute per-round metrics
        updated_state = engine.get_state()
        metrics, previous_actions_map = compute_round_metrics(
            updated_state.resources,
            round_result['actions'],
            previous_actions_map
        )
        metrics['round'] = round_num
        metrics['resources'] = dict(updated_state.resources)
        all_round_metrics.append(metrics)

        stability_str = f"{metrics['action_stability']:.0%}" if metrics['action_stability'] is not None else "n/a"
        print(f"\n  Metrics: Gini={metrics['gini']:.3f}  Palma={metrics['palma']:.2f}  Stability={stability_str}")

        # Early stopping check (Phase 2: after min_rounds, check convergence)
        if early_stop_enabled:
            should_stop, stop_reason = check_early_stopping(
                all_round_metrics,
                min_rounds=es_min_rounds,
                patience=es_patience,
                gini_threshold=es_gini_threshold,
                entropy_threshold=es_entropy_threshold,
            )
            if should_stop:
                print(f"\n{'='*70}")
                print(f"EARLY STOPPING at round {round_num}: {stop_reason}")
                print(f"{'='*70}")
                early_stopped = True
                early_stop_reason = stop_reason
                break

        # Update agent memories
        if memory_config.get('enabled', False):
            post_resources = dict(updated_state.resources)
            round_actions = round_result.get('actions', [])
            resource_changes = round_result.get('resource_changes', {})
            combat_results = round_result.get('combat_results', [])

            # Build per-agent action/outcome map from round_result
            agent_action_map = {}  # agent_id -> (action_str, target)
            for a in round_actions:
                agent_action_map[a['agent']] = (a.get('action', 'no_action'), a.get('target'))

            # Build per-agent outcome from resource changes and combat results
            agent_outcomes = {}  # agent_id -> outcome dict
            for a in round_actions:
                aid = a['agent']
                outcome = {}
                rc = resource_changes.get(aid, 0.0)
                if abs(rc) > 0.001:
                    outcome['resource_change'] = rc
                # Only attach combat_won to the attacker's action outcome
                # (defenders had a different action; their defense is passive)
                for combat in combat_results:
                    if aid in combat.get('attackers', []):
                        outcome['combat_won'] = (combat['winner'] == 'coalition')
                        break
                agent_outcomes[aid] = outcome

            for aid in agent_ids:
                action_str, target = agent_action_map.get(aid, ('no_action', None))
                visible = network.get_neighbors(aid) if network else None
                agents[aid].update_memory(
                    round_num=round_num,
                    action_str=action_str,
                    target=target,
                    outcome=agent_outcomes.get(aid, {}),
                    visible_agents=visible,
                    round_actions=round_actions,
                    resource_changes=resource_changes,
                    combat_results=combat_results,
                    all_resources=post_resources
                )

        # Network rewiring (end of round, after resource updates)
        if network:
            rc = round_result.get('resource_changes', {})
            resource_changes_history.append(rc)
            rewire_stats = network.rewire(resource_changes_history)
            if rewire_stats['agents_rewired'] > 0:
                print(f"  🔗 Network rewired: {rewire_stats['agents_rewired']} agents, "
                      f"{rewire_stats['edges_dropped']} edges swapped")

        print()

    elapsed = time.time() - start_time
    
    # Collect all reasoning traces
    all_traces = []
    for agent in agents.values():
        all_traces.extend(agent.get_reasoning_traces())

    # Compute token totals from traces
    total_prompt_tokens = sum(t.get('usage', {}).get('prompt_tokens', 0) for t in all_traces)
    total_completion_tokens = sum(t.get('usage', {}).get('completion_tokens', 0) for t in all_traces)

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
    
    # Run metadata
    run_metadata = {
        "run_id": run_id,
        "random_seed": seed,
        "model": openrouter_config.get('model', 'unknown'),
        "temperature": openrouter_config.get('temperature'),
        "max_tokens": openrouter_config.get('max_tokens'),
        "base_url": openrouter_config.get('base_url', ''),
        "elapsed_seconds": round(elapsed, 1),
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "total_tokens": total_prompt_tokens + total_completion_tokens,
        "early_stopped": early_stopped,
        "early_stop_reason": early_stop_reason,
        "early_stop_round": len(all_round_metrics) if early_stopped else None,
        "system": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "node": platform.node(),
            "slurm_job_id": os.getenv("SLURM_JOB_ID"),
            "slurm_nodelist": os.getenv("SLURM_NODELIST"),
            "cuda_visible": os.getenv("CUDA_VISIBLE_DEVICES"),
        },
    }

    print()

    return state, all_traces, all_round_metrics, run_metadata


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
    state, traces, round_metrics, run_metadata = run_simulation(game_params, openrouter_config, run_id)

    # Save results
    output_dir = project_root / "data" / "runs"
    save_results(state, traces, round_metrics, output_dir, run_id, run_metadata)


if __name__ == "__main__":
    main()
