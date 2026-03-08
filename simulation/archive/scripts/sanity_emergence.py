"""
Maximum emergence run: L3, visible resources, neutral prompt, arm 10x/0.25 decay.
20 rounds, 5 agents, network rewiring.
Run with: python -u sanity_emergence.py
"""

import os
import sys
import json
import numpy as np
import random
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv
load_dotenv()

from game.engine import GameEngine, ActionType, Action
from game.spatial import NetworkTopology
from agents.llm_agent import LLMAgent
import display as d

# ---- Config: maximum emergence ----
NUM_AGENTS = 5
NUM_ROUNDS = 20
SEED = 42
MODEL = "qwen/qwen3.5-27b"

np.random.seed(SEED)
random.seed(SEED)

game_params = {
    'num_agents': NUM_AGENTS,
    'initial_resources': 25.0,
    'invest_self_pct': 2,
    'invest_other_cost_pct': 10,
    'invest_other_return_pct': 15,
    'arm_cost_pct': 10,
    'arm_multiplier': 10.0,       # strong arms — loading the gun
    'arm_other_cost_pct': 10,
    'arm_decay': 0.25,            # fast decay — use it or lose it
    'attack_take_pct': 40,
    'conflict_cost_pct': 5,
    'max_rounds': NUM_ROUNDS,
    'history_length': 10,
    'allow_invest_self': False,
    'action_order': 'simultaneous',
    'comm_scope': 'none',
    'network_enabled': True,
    'mean_degree': 3.0,
    'rewiring_prob': 0.3,
    'payoff_window': 3,
    'memory': {'enabled': True, 'window_size': 10},
}

# ---- Setup ----
agent_ids = [f"agent_{i+1}" for i in range(NUM_AGENTS)]

engine = GameEngine(
    agent_ids=agent_ids,
    initial_resources=game_params['initial_resources'],
    invest_self_pct=game_params['invest_self_pct'],
    invest_other_cost_pct=game_params['invest_other_cost_pct'],
    invest_other_return_pct=game_params['invest_other_return_pct'],
    arm_cost_pct=game_params['arm_cost_pct'],
    arm_multiplier=game_params['arm_multiplier'],
    arm_other_cost_pct=game_params['arm_other_cost_pct'],
    arm_decay=game_params['arm_decay'],
    attack_take_pct=game_params['attack_take_pct'],
    conflict_cost_pct=game_params['conflict_cost_pct'],
    max_rounds=game_params['max_rounds'],
)

network = NetworkTopology(agent_ids, mean_degree=3.0, rewiring_prob=0.3, payoff_window=3)

api_key = os.getenv("OPENROUTER_API_KEY")
agents = {}
for aid in agent_ids:
    agents[aid] = LLMAgent(
        agent_id=aid,
        api_key=api_key,
        model=MODEL,
        prompt_config={
            'objective_style': 'maximize_resources',
            'hide_resources': False,      # visible — enables strategic attacks
            'reasoning_level': 'level3',  # recursive opponent modeling
        },
        game_params=game_params,
        temperature=0.7,
        max_tokens=4096,
        timeout=120,
        retry_attempts=2,
        retry_delay=3,
        base_url="https://openrouter.ai/api/v1",
        memory_config=game_params['memory'],
    )

d.print_run_header(
    f"EMERGENCE RUN: {NUM_AGENTS} agents, {NUM_ROUNDS} rounds\n"
    f"Model: {MODEL} | L3 | visible resources | neutral prompt\n"
    f"Arms: {game_params['arm_multiplier']}x multiplier, {game_params['arm_decay']} decay | "
    f"Attack: {game_params['attack_take_pct']}% take, {game_params['conflict_cost_pct']}% cost\n"
    f"Network: ER <k>={game_params['mean_degree']}, rewire w={game_params['rewiring_prob']}"
)
d.print_network(agent_ids, network.get_neighbors)

# ---- Main loop ----
pending_messages = {aid: [] for aid in agent_ids}
resource_changes_history = []
round_summaries = []
resource_timeline = []

t0 = time.time()

for round_num in range(1, NUM_ROUNDS + 1):
    state = engine.get_state()
    rt = time.time()

    d.print_round_header(round_num, NUM_ROUNDS)
    d.print_resource_bars(state.resources, state.arm_bonuses, agent_ids)
    d.print_network(agent_ids, network.get_neighbors)

    # Get actions (parallel)
    actions = []
    action_map = {}

    def get_action(aid):
        obs = state.get_observation(aid, game_params['history_length'])
        obs['broke_agents'] = [a for a in agent_ids if state.resources[a] < 0.01]
        obs['visible_agents'] = network.get_neighbors(aid)
        if pending_messages.get(aid):
            obs['received_messages'] = pending_messages[aid]
        if agents[aid].memory is not None:
            obs['agent_memory'] = agents[aid].memory
        action = agents[aid].select_action(obs)
        return aid, action

    with ThreadPoolExecutor(max_workers=NUM_AGENTS) as executor:
        futures = {executor.submit(get_action, aid): aid for aid in agent_ids}
        for future in as_completed(futures):
            aid, action = future.result()
            actions.append(action)
            action_map[aid] = action

    # Build action summary for display + logging
    round_actions_summary = {}
    display_action_map = {}
    for aid in agent_ids:
        action = action_map[aid]
        round_actions_summary[aid] = {
            'action': action.action_type.value,
            'target': action.target_id,
        }
        display_action_map[aid] = round_actions_summary[aid]
    round_summaries.append(round_actions_summary)

    d.print_actions(display_action_map, agent_ids)

    # Resolve
    round_result = engine.resolve_round(actions)
    d.print_combat_results(round_result.get('combat_results', []))

    # Track resources
    updated_state = engine.get_state()
    resource_timeline.append({aid: updated_state.resources[aid] for aid in agent_ids})

    # Update memory
    post_resources = dict(updated_state.resources)
    round_actions = round_result.get('actions', [])
    resource_changes = round_result.get('resource_changes', {})
    combat_results = round_result.get('combat_results', [])

    agent_action_map = {}
    for a in round_actions:
        agent_action_map[a['agent']] = (a.get('action', 'no_action'), a.get('target'))
    agent_outcomes = {}
    for a in round_actions:
        aid = a['agent']
        outcome = {}
        rc = resource_changes.get(aid, 0.0)
        if abs(rc) > 0.001:
            outcome['resource_change'] = rc
        for combat in combat_results:
            if aid in combat.get('attackers', []):
                outcome['combat_won'] = (combat['winner'] == 'coalition')
                break
        agent_outcomes[aid] = outcome

    for aid in agent_ids:
        action_str, target = agent_action_map.get(aid, ('no_action', None))
        visible = network.get_neighbors(aid)
        agents[aid].update_memory(
            round_num=round_num, action_str=action_str, target=target,
            outcome=agent_outcomes.get(aid, {}), visible_agents=visible,
            round_actions=round_actions, resource_changes=resource_changes,
            combat_results=combat_results, all_resources=post_resources,
            received_messages=pending_messages.get(aid, []),
        )

    resource_changes_history.append(resource_changes)
    rewire_stats = network.rewire(resource_changes_history)
    d.print_network_rewire(rewire_stats)
    d.print_round_time(time.time() - rt)

# ---- Final summary ----
elapsed = time.time() - t0
final = engine.get_state()

d.print_final_summary(final.resources, final.arm_bonuses, agent_ids, elapsed)
d.print_action_distribution(round_summaries)
d.print_agent_profiles(round_summaries, agent_ids, final.resources)

# Gini
vals = sorted(final.resources.values())
n = len(vals)
gini = sum(abs(vals[i] - vals[j]) for i in range(n) for j in range(n)) / (2 * n * sum(vals))
d.print_gini(gini, final.resources)

# Final network
d.p(f"\n{d.C('Final network:', 'bold')}")
d.print_network(agent_ids, network.get_neighbors)

# ---- Save ----
log_dir = os.path.join(os.path.dirname(__file__), 'data', 'sanity_tests')
os.makedirs(log_dir, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_path = os.path.join(log_dir, f"emergence_20r_{timestamp}.json")

all_traces = {aid: agents[aid].get_reasoning_traces() for aid in agent_ids}

log_data = {
    "config": {
        "model": MODEL, "num_agents": NUM_AGENTS, "num_rounds": NUM_ROUNDS,
        "reasoning_level": "level3", "comm_scope": "none",
        "hide_resources": False, "seed": SEED, "prompt": "neutral_v2",
        "arm_multiplier": game_params['arm_multiplier'],
        "arm_decay": game_params['arm_decay'],
        "game_params": game_params,
    },
    "resource_timeline": resource_timeline,
    "final_resources": dict(final.resources),
    "action_distribution": {a: c for rs in round_summaries for a, c in
                            [(rs[aid]['action'], 1) for aid in rs]},
    "round_summaries": round_summaries,
    "gini": gini,
    "traces": all_traces,
    "memories": {aid: agents[aid].memory.to_dict() for aid in agent_ids if agents[aid].memory},
    "initial_network": {aid: network.get_neighbors(aid) for aid in agent_ids},
    "final_network": {aid: network.get_neighbors(aid) for aid in agent_ids},
    "history": final.history,
}

with open(log_path, 'w') as f:
    json.dump(log_data, f, indent=2, default=str)
d.p(f"\n📁 Logs: {log_path}")
