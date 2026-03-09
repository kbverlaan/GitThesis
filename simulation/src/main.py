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
from agents.memory import AgentMemory
from analysis.metrics import compute_round_metrics, check_early_stopping
from analysis.network import analyze_run_networks, detect_communities
import display as d


def save_checkpoint(path, engine, agents, network, pending_messages, bilateral_flows_history, all_round_metrics):
    """Save full simulation state for resume."""
    checkpoint = {
        'round_number': engine.state.round_number,
        'resources': dict(engine.state.resources),
        'arm_bonuses': dict(engine.state.arm_bonuses),
        'history': [],
        'agent_memories': {},
        'pending_messages': pending_messages,
        'bilateral_flows_history': [],
        'all_round_metrics': all_round_metrics,
    }
    # Serialize history (bilateral_flows has tuple keys)
    for rd in engine.state.history:
        rd_copy = dict(rd)
        if 'bilateral_flows' in rd_copy:
            rd_copy['bilateral_flows'] = {
                f"{k[0]}→{k[1]}" if isinstance(k, tuple) else k: v
                for k, v in rd_copy['bilateral_flows'].items()
            }
        checkpoint['history'].append(rd_copy)
    # Serialize agent memories
    for aid, agent in agents.items():
        if agent.memory is not None:
            checkpoint['agent_memories'][aid] = agent.memory.to_dict()
    # Serialize network
    if network:
        checkpoint['network_edges'] = network.get_edge_list()
    # Serialize bilateral_flows_history
    for bf in bilateral_flows_history:
        checkpoint['bilateral_flows_history'].append({
            f"{k[0]}→{k[1]}" if isinstance(k, tuple) else k: v
            for k, v in bf.items()
        })
    with open(path, 'w') as f:
        json.dump(checkpoint, f, default=str)


def load_checkpoint(path):
    """Load checkpoint for resume."""
    with open(path) as f:
        return json.load(f)


def reconstruct_from_jsonl(jsonl_path: str, game_params: dict) -> dict:
    """Reconstruct full simulation state from JSONL reasoning log.

    Replays all rounds to rebuild agent memories, resources, network, etc.
    Returns a checkpoint-compatible dict.
    """
    from agents.memory import AgentMemory

    rounds = []
    with open(jsonl_path) as f:
        for line in f:
            rounds.append(json.loads(line))

    if not rounds:
        raise ValueError(f"Empty JSONL: {jsonl_path}")

    # Skip crashed rounds (>80% do_nothing = likely API failure)
    while len(rounds) > 1:
        last = rounds[-1]
        agents_data = last['agents']
        do_nothing_count = sum(1 for a in agents_data.values() if a.get('action') in ('do_nothing', None, ''))
        if do_nothing_count / len(agents_data) > 0.8:
            print(f"  Skipping round {last['round']} (likely API failure: {do_nothing_count}/{len(agents_data)} do_nothing)")
            rounds.pop()
        else:
            break

    last_round = rounds[-1]
    agent_ids = list(last_round['agents'].keys())

    # Build memories by replaying rounds
    memories = {aid: AgentMemory(aid, game_params.get('memory', {}).get('window_size', 10))
                for aid in agent_ids}

    all_round_metrics = []
    pending_messages = {aid: [] for aid in agent_ids}
    engine_history = []  # Minimal round logs for engine saturation counting

    for rd in rounds:
        rnd = rd['round']
        agents_data = rd['agents']
        network_edges = rd.get('network', {}).get('edges', [])

        # Build visible_agents from network edges
        visible = {aid: set() for aid in agent_ids}
        for edge in network_edges:
            a, b = edge[0], edge[1]
            if a in visible and b in visible:
                visible[a].add(b)
                visible[b].add(a)

        # Build round_actions list
        round_actions = []
        for aid, adata in agents_data.items():
            act = adata.get('action', 'no_action')
            if act and act != 'no_action':
                round_actions.append({
                    'agent': aid,
                    'action': act,
                    'target': adata.get('target'),
                })
            else:
                round_actions.append({
                    'agent': aid,
                    'action': 'no_action',
                })

        # Build resources dict
        all_resources = {aid: adata.get('resources', 0) for aid, adata in agents_data.items()}

        # Compute resource changes (approximate — not critical for memory)
        resource_changes = {aid: 0.0 for aid in agent_ids}

        # Get combat results
        combat_results = rd.get('combat', [])

        # Update each agent's memory
        for aid in agent_ids:
            adata = agents_data.get(aid, {})
            act = adata.get('action', 'no_action')
            target = adata.get('target')

            # Record own action
            memories[aid].record_action(rnd, act, target, {})

            # Update observations
            vis_list = list(visible.get(aid, []))
            memories[aid].update_observations(
                rnd, vis_list, round_actions,
                resource_changes, combat_results, all_resources
            )

            # Record note
            note = adata.get('note_to_self')
            if note:
                memories[aid].record_note(note)

        # Process messages
        msgs = rd.get('messages', [])
        next_messages = {aid: [] for aid in agent_ids}
        for msg in msgs:
            sender = msg.get('from') or msg.get('agent_id')
            msg_to = msg.get('message_to')
            text = msg.get('message', '')
            if not text:
                continue

            # Record sent message
            if sender in memories:
                memories[sender].record_messages(
                    {'message': text, 'message_to': msg_to},
                    pending_messages.get(sender, []),
                    rnd
                )

            # Route for next round
            if msg_to and msg_to != 'all' and msg_to in agent_ids:
                next_messages[msg_to].append({'from': sender, 'message': text, 'channel': 'dm'})
            elif msg_to == 'all':
                for target in agent_ids:
                    if target != sender:
                        next_messages[target].append({'from': sender, 'message': text, 'channel': 'broadcast'})

        pending_messages = next_messages

        # Store minimal round log for engine history (needed for saturation counting)
        engine_history.append({'actions': round_actions, 'round': rnd})

        # Store metrics if available
        if 'primary' in rd:
            metrics = dict(rd['primary'])
            metrics['round'] = rnd
            if 'secondary' in rd:
                metrics.update(rd['secondary'])
            all_round_metrics.append(metrics)

    # Build checkpoint
    checkpoint = {
        'round_number': last_round['round'] + 1,  # Next round to play
        'resources': {aid: agents_data[aid].get('resources', 0) for aid, agents_data in [(a, last_round['agents']) for a in agent_ids]},
        'arm_bonuses': {aid: last_round['agents'][aid].get('arm_bonus', 0) for aid in agent_ids},
        'history': engine_history,  # Minimal history for engine (needed for saturation counting)
        'agent_memories': {aid: memories[aid].to_dict() for aid in agent_ids},
        'network_edges': last_round.get('network', {}).get('edges', []),
        'pending_messages': pending_messages,
        'bilateral_flows_history': [],
        'all_round_metrics': all_round_metrics,
    }

    # Fix resources dict (handle the list comp issue)
    checkpoint['resources'] = {aid: last_round['agents'][aid].get('resources', 0) for aid in agent_ids}

    print(f"Reconstructed state from {len(rounds)} rounds of {jsonl_path}")
    print(f"  Agents: {agent_ids}")
    print(f"  Resuming from round {checkpoint['round_number']}")

    return checkpoint

# Optional: per-round modularity via Leiden
try:
    import networkx as nx
    _HAS_NX = True
except ImportError:
    _HAS_NX = False


def _compute_round_modularity(history: list, window: int = 5) -> float:
    """Compute network modularity Q(t) on recent cooperation+conflict interactions.

    Uses a sliding window of the last `window` rounds. Uses networkx's built-in
    greedy modularity (no leidenalg/igraph dependency). Returns 0.0 if not enough
    history or no edges.
    """
    if not _HAS_NX or len(history) < 2:
        return 0.0

    recent = history[-window:]
    G = nx.Graph()  # Undirected for modularity computation

    for round_data in recent:
        for action in round_data.get('actions', []):
            agent = action.get('agent')
            target = action.get('target')
            action_type = action.get('action', '')
            if not target or action_type in ('no_action', 'do_nothing', 'invest_self', 'arm_self'):
                continue
            if G.has_edge(agent, target):
                G[agent][target]['weight'] += 1
            else:
                G.add_edge(agent, target, weight=1)

    if G.number_of_edges() < 2 or G.number_of_nodes() < 3:
        return 0.0

    try:
        communities = nx.community.greedy_modularity_communities(
            G, weight='weight', resolution=1.0
        )
        return nx.community.modularity(G, communities, weight='weight')
    except Exception:
        return 0.0


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

    # Save game history — convert tuple keys in bilateral_flows to strings
    serializable_history = []
    for rd in game_state.history:
        rd_copy = dict(rd)
        if 'bilateral_flows' in rd_copy:
            rd_copy['bilateral_flows'] = {
                f"{k[0]}→{k[1]}": v for k, v in rd_copy['bilateral_flows'].items()
            }
        serializable_history.append(rd_copy)
    history_file = output_dir / f"{run_id}_history.json"
    with open(history_file, 'w') as f:
        json.dump({
            "agents": game_state.agents,
            "final_resources": game_state.resources,
            "total_rounds": game_state.round_number,
            "history": serializable_history
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
                   run_id: Optional[str] = None,
                   resume_path: Optional[str] = None) -> tuple:
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
    
    # Create agent IDs — random color names to avoid positional/ordinal LLM bias
    AGENT_NAMES = [
        "Red", "Blue", "Green", "Gold", "Silver",
        "Coral", "Jade", "Amber", "Ivory", "Slate",
        "Crimson", "Teal", "Copper", "Violet", "Pearl",
        "Bronze", "Scarlet", "Indigo", "Onyx", "Cobalt",
        "Maroon", "Olive", "Cyan", "Rust", "Mauve",
        "Sage", "Plum", "Dusk", "Ash", "Storm",
    ]
    n_agents = game_params['num_agents']

    # If resuming, extract agent IDs from checkpoint before creating agents
    _resume_ckpt = None
    if resume_path:
        if resume_path.endswith('.jsonl'):
            _resume_ckpt = reconstruct_from_jsonl(resume_path, game_params)
        else:
            _resume_ckpt = load_checkpoint(resume_path)
        names = list(_resume_ckpt['resources'].keys())
        n_agents = len(names)
    elif n_agents <= len(AGENT_NAMES):
        names = random.sample(AGENT_NAMES, n_agents)
    else:
        names = [f"agent_{i+1}" for i in range(n_agents)]
    agent_ids = names

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
        resource_decay_pct=game_params.get('resource_decay_pct', 0),
        invest_saturation_decay=game_params.get('invest_saturation_decay', 1.0),
        invest_saturation_window=game_params.get('invest_saturation_window', 5),
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

    # Resume from checkpoint or JSONL
    resumed_metrics = []
    resumed_bilateral = []
    resumed_pending = {}
    if resume_path and _resume_ckpt:
        ckpt = _resume_ckpt
        print(f"Resuming from round {ckpt['round_number']} (source: {resume_path})")
        # Restore engine state
        engine.state.round_number = ckpt['round_number']
        engine.state.resources = {aid: float(v) for aid, v in ckpt['resources'].items()}
        engine.state.arm_bonuses = {aid: float(v) for aid, v in ckpt.get('arm_bonuses', {}).items()}
        # Restore history (bilateral_flows keys back to tuples)
        engine.state.history = []
        for rd in ckpt.get('history', []):
            if 'bilateral_flows' in rd:
                restored_bf = {}
                for k, v in rd['bilateral_flows'].items():
                    parts = k.split('→')
                    if len(parts) == 2:
                        restored_bf[(parts[0], parts[1])] = v
                    else:
                        restored_bf[k] = v
                rd['bilateral_flows'] = restored_bf
            engine.state.history.append(rd)
        # Restore agent memories
        for aid, mem_dict in ckpt.get('agent_memories', {}).items():
            if aid in agents:
                agents[aid].memory = AgentMemory.from_dict(mem_dict)
        # Restore network
        if network and 'network_edges' in ckpt:
            network.restore_edges(ckpt['network_edges'])
        # Restore run state
        resumed_pending = ckpt.get('pending_messages', {})
        resumed_metrics = ckpt.get('all_round_metrics', [])
        for bf_str in ckpt.get('bilateral_flows_history', []):
            restored = {}
            for k, v in bf_str.items():
                parts = k.split('→')
                if len(parts) == 2:
                    restored[(parts[0], parts[1])] = v
                else:
                    restored[k] = v
            resumed_bilateral.append(restored)
    
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
    all_round_metrics = resumed_metrics if resumed_metrics else []
    previous_actions_map = None
    bilateral_flows_history = resumed_bilateral if resumed_bilateral else []
    comm_scope = game_params.get('comm_scope', 'none')
    pending_messages = resumed_pending if resumed_pending else {aid: [] for aid in agent_ids}

    # Checkpoint + log directory
    log_dir = Path(__file__).parent.parent / "data" / "runs"
    log_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_dir = log_dir / "checkpoints"
    checkpoint_dir.mkdir(exist_ok=True)
    checkpoint_path = checkpoint_dir / f"{run_id}_checkpoint.json"

    # Live reasoning log — appended after each round so you can `tail -f`
    reasoning_log_path = None
    if run_id:
        reasoning_log_path = log_dir / f"{run_id}_reasoning_live.jsonl"
        d.p(f"{d.C('Live reasoning log:', 'dim')} {reasoning_log_path}")

    start_round = engine.get_state().round_number  # 1 for fresh, >1 for resumed
    while not engine.is_game_over(max_rounds):
        state = engine.get_state()
        round_num = state.round_number
        
        d.print_round_header(round_num, max_rounds)
        d.print_resource_bars(state.resources, state.arm_bonuses, agent_ids)
        if network:
            d.print_network(agent_ids, network.get_neighbors)
        
        # Set valid targets for network-restricted actions
        if network:
            valid_targets = {aid: network.get_neighbors(aid) for aid in agent_ids}
            engine.set_valid_targets(valid_targets)
        else:
            engine.set_valid_targets(None)

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
            # Inject received messages from previous round
            if pending_messages.get(agent_id):
                observation['received_messages'] = pending_messages[agent_id]
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
                    d.p(f"\n{d._ca(agent_id)}: {d.C('BROKE - NO ACTION', 'red')}")
                    round_log["actions"].append({"agent": agent_id, "action": "no_action", "reason": "insufficient_resources"})
                    continue

                agent_id, action, reasoning = get_agent_action(agent_id, current_state)
                action_desc = action.action_type.value + (f" → {action.target_id}" if action.target_id else "")
                d.p(f"\n{d._ca(agent_id)}: {action_desc}")

                result = engine.resolve_single_action(action)
                round_log["actions"].extend(result["actions"])
                round_log["combat_results"].extend(result.get("combat_results", []))
                all_actions_this_round.append(action)

                d.print_combat_results(result.get("combat_results", []))

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

            # Build display map and show reasoning
            display_action_map = {}
            for detail in action_details:
                aid = detail['agent']
                display_action_map[aid] = {
                    'action': detail['action'].action_type.value,
                    'target': detail['action'].target_id,
                }
            round_result = engine.resolve_round(actions)

            # Collect notes for smart display
            round_notes = {}
            for aid in agent_ids:
                agent = agents[aid]
                if hasattr(agent, '_last_note') and agent._last_note:
                    round_notes[aid] = agent._last_note
                elif agent.memory and agent.memory.note_to_self:
                    round_notes[aid] = agent.memory.note_to_self

            d.print_agent_round_summary(display_action_map, round_notes, agent_ids)
            d.print_combat_results(round_result.get('combat_results', []))

        # Collect and route messages for next round
        # Messages are global — any agent can message any other agent
        if comm_scope != 'none':
            next_messages = {aid: [] for aid in agent_ids}
            msg_count = 0
            other_agents = {aid: [x for x in agent_ids if x != aid] for aid in agent_ids}
            for aid in agent_ids:
                msg = agents[aid].get_last_message()
                if msg and msg.get('message'):
                    msg_to = msg.get('message_to')
                    if msg_to == 'all' or comm_scope == 'broadcast':
                        # Broadcast to all other agents
                        for target in other_agents[aid]:
                            next_messages[target].append({
                                'from': aid,
                                'message': msg['message'],
                                'channel': 'broadcast',
                            })
                        msg_count += 1
                    elif msg_to and msg_to in other_agents[aid]:
                        # DM to specific agent (any agent, not just neighbors)
                        next_messages[msg_to].append({
                            'from': aid,
                            'message': msg['message'],
                            'channel': 'dm',
                        })
                        msg_count += 1
            pending_messages = next_messages
            # Log messages in round result for post-hoc analysis
            round_messages = []
            for aid in agent_ids:
                msg = agents[aid].get_last_message()
                if msg and msg.get('message'):
                    round_messages.append(msg)
            if round_messages:
                round_result['messages'] = round_messages
            if round_messages:
                d.print_messages(round_messages)

        # Compute per-round metrics
        updated_state = engine.get_state()
        metrics, previous_actions_map = compute_round_metrics(
            updated_state.resources,
            round_result['actions'],
            previous_actions_map
        )
        metrics['round'] = round_num
        metrics['resources'] = dict(updated_state.resources)

        # Primary metric: network modularity Q(t)
        current_history = updated_state.history if updated_state.history else []
        metrics['modularity'] = _compute_round_modularity(current_history, window=5)

        all_round_metrics.append(metrics)

        # Display metrics dashboard with trends
        prev_metrics = all_round_metrics[-2] if len(all_round_metrics) >= 2 else None
        d.print_metrics_dashboard(metrics, prev_metrics)

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
                d.p(f"\n{d.C('=' * 70, 'bold')}")
                d.p(d.C(f"EARLY STOPPING at round {round_num}: {stop_reason}", 'yellow'))
                d.p(d.C('=' * 70, 'bold'))
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
                    all_resources=post_resources,
                    received_messages=pending_messages.get(aid, []),
                )

        # Append reasoning to live log (JSONL — one JSON object per round)
        if reasoning_log_path:
            # Build per-agent trace: extract reasoning from thinking or response
            agent_traces = {}
            for aid in agent_ids:
                traces = agents[aid].get_reasoning_traces()
                if not traces:
                    continue
                last = traces[-1]
                thinking = last.get('thinking', '') or ''
                response = last.get('response', '') or ''

                # Extract reasoning text: prefer <think> block, fall back to response
                if thinking:
                    reasoning_text = thinking
                elif response:
                    # Gemini-style: reasoning + JSON in response. Split at first {
                    brace = response.find('{')
                    reasoning_text = response[:brace].strip() if brace > 0 else ''
                else:
                    reasoning_text = ''

                # Extract the parsed action from round_result (authoritative)
                action_entry = next(
                    (a for a in round_result.get('actions', []) if a.get('agent') == aid),
                    {}
                )

                agent_traces[aid] = {
                    'action': action_entry.get('action', ''),
                    'target': action_entry.get('target'),
                    'reasoning': reasoning_text,
                    'thinking': thinking if thinking else None,
                    'note_to_self': agents[aid].memory.note_to_self,
                    'tokens': last.get('usage', {}).get('total_tokens', 0),
                    'latency_s': last.get('latency_s') or last.get('latency', 0),
                    'prompt': last.get('prompt', ''),
                    'response': response,
                }

            log_entry = {
                'round': round_num,
                # Embed config in first round for viewer
                **({'config': {
                    'reasoning_level': prompt_config.get('reasoning_level', 'unknown'),
                    'rewiring_prob': game_params.get('rewiring_prob', 0),
                    'comm_scope': game_params.get('comm_scope', 'none'),
                    'num_agents': len(agent_ids),
                    'max_rounds': game_params.get('max_rounds'),
                    'model': openrouter_config.get('model', 'unknown'),
                }} if round_num == 1 or round_num == start_round else {}),
                # §3.5.1 Primary metrics
                'primary': {
                    'cooperation_ratio': metrics['cooperation_ratio'],
                    'gini': metrics['gini'],
                    'modularity': metrics['modularity'],
                },
                # §3.5.2 Secondary metrics
                'secondary': {
                    'palma': metrics['palma'],
                    'action_stability': metrics['action_stability'],
                    'action_distribution': metrics.get('action_distribution', {}),
                },
                # Per-agent state
                'agents': {
                    aid: {
                        'resources': updated_state.resources[aid],
                        'arm_bonus': updated_state.arm_bonuses.get(aid, 0.0),
                        'breakdown': round_result.get('resource_breakdown', {}).get(aid, {}),
                        **agent_traces.get(aid, {}),
                    }
                    for aid in agent_ids
                },
                # Events
                'combat': round_result.get('combat_results', []),
                'messages': [
                    {'from': m.get('from'), 'to': m.get('message_to'), 'text': m.get('message', '')}
                    for m in round_result.get('messages', [])
                ],
                # Network topology for viewer
                'network': {
                    'edges': network.get_edge_list() if network else [],
                },
            }
            with open(reasoning_log_path, 'a') as f:
                f.write(json.dumps(log_entry, default=str) + '\n')

        # Network rewiring (end of round, after resource updates)
        if network:
            bf = dict(round_result.get('bilateral_flows', {}))
            bilateral_flows_history.append(bf)
            rewire_stats = network.rewire(bilateral_flows_history)
            d.print_network_rewire(rewire_stats)

        # Save checkpoint after each round (for resume)
        save_checkpoint(checkpoint_path, engine, agents, network,
                       pending_messages, bilateral_flows_history, all_round_metrics)

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

    d.print_final_summary(state.resources, state.arm_bonuses, agent_ids, elapsed,
                          all_round_metrics)
    d.p(f"  Rounds: {rounds_played}  ({elapsed/max(rounds_played,1):.1f}s/round)")

    # Build round_summaries from history for action distribution
    round_summaries = []
    for round_data in state.history:
        rs = {}
        for action in round_data['actions']:
            rs[action['agent']] = {
                'action': action.get('action', 'unknown'),
                'target': action.get('target'),
            }
        round_summaries.append(rs)

    d.print_action_distribution(round_summaries)
    d.print_agent_profiles(round_summaries, agent_ids, state.resources)
    
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
    """Unified entry point for single runs and parameter sweeps.

    Usage:
        # Single run with config YAMLs:
        python src/main.py --game config/sweetspot_game.yaml --api config/sweetspot_openrouter.yaml

        # Parameter sweep:
        python src/main.py --sweep experiments/reasoning_depth_pilot.yaml

        # Single run from sweep (for SLURM array jobs):
        python src/main.py --sweep experiments/reasoning_depth_pilot.yaml --run-index 0

        # Batch of runs from sweep:
        python src/main.py --sweep experiments/reasoning_depth_pilot.yaml --run-index 0 --batch-size 5
    """
    import argparse
    parser = argparse.ArgumentParser(description="Run simulation or parameter sweep")
    parser.add_argument('--game', type=str, default=None, help='Game params YAML (default: config/game_params.yaml)')
    parser.add_argument('--api', type=str, default=None, help='API config YAML (default: config/openrouter_config.yaml)')
    parser.add_argument('--output', type=str, default=None, help='Output directory (default: data/runs)')
    parser.add_argument('--sweep', type=str, default=None, help='Experiment YAML for parameter sweep')
    parser.add_argument('--run-index', type=int, default=None, help='Run single (condition, rep) by index (for SLURM array jobs)')
    parser.add_argument('--batch-size', type=int, default=1, help='Number of consecutive runs per job (default: 1)')
    parser.add_argument('--resume', type=str, default=None, help='Resume from checkpoint JSON (saves after each round)')
    args = parser.parse_args()

    if args.sweep:
        # Sweep mode — delegate to sweep module
        from sweep import run_sweep, run_single, run_batch
        if args.run_index is not None:
            if args.batch_size > 1:
                run_batch(args.sweep, args.run_index, args.batch_size)
            else:
                run_single(args.sweep, args.run_index)
        else:
            run_sweep(args.sweep)
    else:
        # Single run mode
        load_dotenv()
        project_root = Path(__file__).parent.parent

        game_path = Path(args.game) if args.game else project_root / "config" / "game_params.yaml"
        api_path = Path(args.api) if args.api else project_root / "config" / "openrouter_config.yaml"
        game_params = load_config(game_path)
        openrouter_config = load_config(api_path)

        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        state, traces, round_metrics, run_metadata = run_simulation(
            game_params, openrouter_config, run_id, resume_path=args.resume
        )

        output_dir = Path(args.output) if args.output else project_root / "data" / "runs"
        save_results(state, traces, round_metrics, output_dir, run_id, run_metadata)


if __name__ == "__main__":
    main()
