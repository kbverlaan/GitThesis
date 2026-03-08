"""
Sanity test: 5 agents, 3 rounds, communication=choice, network topology.
Saves full logs (prompts, thinking traces, actions, messages) to JSON.
"""

import os
import sys
import json
import numpy as np
import random
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv
load_dotenv()

from game.engine import GameEngine, ActionType, Action
from game.spatial import NetworkTopology
from agents.llm_agent import LLMAgent
from agents.prompts import BaselinePrompt

# ----- Config -----
NUM_AGENTS = 5
NUM_ROUNDS = 3
COMM_SCOPE = "choice"  # Test the most complex scope
REASONING_LEVEL = "level2"  # L2: opponent modeling
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
    'arm_multiplier': 2.0,
    'arm_other_cost_pct': 10,
    'arm_decay': 0.5,
    'attack_take_pct': 40,
    'conflict_cost_pct': 5,
    'max_rounds': NUM_ROUNDS,
    'history_length': 10,
    'allow_invest_self': False,
    'action_order': 'simultaneous',
    'comm_scope': COMM_SCOPE,
    'network_enabled': True,
    'mean_degree': 3.0,
    'rewiring_prob': 0.3,
    'payoff_window': 3,
    'memory': {'enabled': True, 'window_size': 10},
}

# ----- Setup -----
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
            'hide_resources': True,
            'reasoning_level': REASONING_LEVEL,
        },
        game_params=game_params,
        temperature=0.7,
        max_tokens=4096,   # Qwen 3.5 needs room for <think> + JSON
        timeout=120,       # Reasoning model needs more time
        retry_attempts=2,
        retry_delay=3,
        base_url="https://openrouter.ai/api/v1",
        memory_config=game_params['memory'],
    )

# ----- Print initial state -----
print("=" * 80)
print(f"SANITY TEST: {NUM_AGENTS} agents, {NUM_ROUNDS} rounds")
print(f"Model: {MODEL}")
print(f"Comm scope: {COMM_SCOPE}, Reasoning: {REASONING_LEVEL}")
print(f"Network: ER ⟨k⟩=3.0, w=0.3")
print("=" * 80)

print("\nInitial network:")
for aid in agent_ids:
    print(f"  {aid}: {network.get_neighbors(aid)}")

# ----- Print the FULL prompt for agent_1 round 1 -----
state = engine.get_state()
obs = state.get_observation('agent_1', game_params['history_length'])
obs['broke_agents'] = []
obs['visible_agents'] = network.get_neighbors('agent_1')
# No messages yet (round 1)
obs['agent_memory'] = agents['agent_1'].memory

prompt_text = agents['agent_1'].prompt.format_observation(obs, 'agent_1')
print("\n" + "=" * 80)
print("FULL PROMPT FOR agent_1 (Round 1, before any messages):")
print("=" * 80)
print(prompt_text)
print("=" * 80)

# ----- Run the actual simulation -----
pending_messages = {aid: [] for aid in agent_ids}
resource_changes_history = []

for round_num in range(1, NUM_ROUNDS + 1):
    state = engine.get_state()
    print(f"\n{'='*80}")
    print(f"ROUND {round_num}/{NUM_ROUNDS}")
    print(f"{'='*80}")

    # Show resources
    print("\nResources:")
    for aid in agent_ids:
        bonus = state.arm_bonuses.get(aid, 0)
        armed = f" [ARM +{bonus:.1f}]" if bonus > 0 else ""
        print(f"  {aid}: {state.resources[aid]:.1f}{armed}")

    # Show pending messages
    for aid in agent_ids:
        if pending_messages[aid]:
            print(f"\n  Messages for {aid}:")
            for m in pending_messages[aid]:
                ch = "broadcast" if m['channel'] == 'broadcast' else "private"
                print(f"    from {m['from']} ({ch}): {m['message']}")

    # Get actions
    actions = []
    for aid in agent_ids:
        obs = state.get_observation(aid, game_params['history_length'])
        obs['broke_agents'] = [a for a in agent_ids if state.resources[a] < 0.01]
        obs['visible_agents'] = network.get_neighbors(aid)
        if pending_messages.get(aid):
            obs['received_messages'] = pending_messages[aid]
        if agents[aid].memory is not None:
            obs['agent_memory'] = agents[aid].memory

        # Print prompt for agent_1 in rounds 2+ (when there are messages)
        if aid == 'agent_1' and round_num == 2:
            prompt_text = agents[aid].prompt.format_observation(obs, aid)
            print(f"\n{'~'*60}")
            print(f"PROMPT for {aid} Round {round_num} (with messages/memory):")
            print(f"{'~'*60}")
            print(prompt_text)
            print(f"{'~'*60}")

        action = agents[aid].select_action(obs)
        actions.append(action)

        # Get last trace for this agent
        traces = agents[aid].get_reasoning_traces()
        last_trace = traces[-1] if traces else {}
        thinking = last_trace.get('thinking', '')
        response = last_trace.get('response', '')

        # Show action + message + thinking
        action_desc = action.action_type.value
        if action.target_id:
            action_desc += f" → {action.target_id}"

        msg = agents[aid].get_last_message()
        msg_desc = ""
        if msg and msg.get('message'):
            to = msg.get('message_to', '?')
            msg_desc = f"  📨 → {to}: \"{msg['message']}\""

        print(f"\n{aid}: {action_desc}{msg_desc}")
        if thinking:
            # Show first 500 chars of thinking
            snippet = thinking[:500] + ("..." if len(thinking) > 500 else "")
            print(f"  💭 Thinking: {snippet}")
        elif response:
            snippet = response[:300] + ("..." if len(response) > 300 else "")
            print(f"  📝 Response: {snippet}")

    # Resolve round
    round_result = engine.resolve_round(actions)

    # Show combat results
    for combat in round_result.get('combat_results', []):
        attackers_str = ",".join(combat.get('attackers', []))
        winner_mark = "✓" if combat['winner'] == 'coalition' else "✗"
        print(f"\n  ⚔️ {attackers_str} vs {combat['defender']}: {combat['winner']} won {winner_mark} ({combat['attacker_win_prob']:.1%})")

    # Route messages for next round
    next_messages = {aid: [] for aid in agent_ids}
    msg_count = 0
    for aid in agent_ids:
        msg = agents[aid].get_last_message()
        if msg and msg.get('message'):
            msg_to = msg.get('message_to')
            neighbors = network.get_neighbors(aid)
            if msg_to == 'all' or COMM_SCOPE == 'broadcast':
                for nbr in neighbors:
                    next_messages[nbr].append({
                        'from': aid,
                        'message': msg['message'],
                        'channel': 'broadcast',
                    })
                msg_count += 1
            elif msg_to and msg_to in neighbors:
                next_messages[msg_to].append({
                    'from': aid,
                    'message': msg['message'],
                    'channel': 'dm',
                })
                msg_count += 1
    pending_messages = next_messages
    if msg_count > 0:
        print(f"\n  💬 {msg_count} messages sent")

    # Update memory
    updated_state = engine.get_state()
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

    # Network rewiring
    resource_changes_history.append(resource_changes)
    rewire_stats = network.rewire(resource_changes_history)
    if rewire_stats['agents_rewired'] > 0:
        print(f"  🔗 Network rewired: {rewire_stats['agents_rewired']} agents")

print(f"\n{'='*80}")
print("FINAL STATE")
print(f"{'='*80}")
final = engine.get_state()
for aid in sorted(agent_ids, key=lambda a: final.resources[a], reverse=True):
    print(f"  {aid}: {final.resources[aid]:.1f}")
print(f"\nFinal network:")
for aid in agent_ids:
    print(f"  {aid}: {network.get_neighbors(aid)}")

# ----- Save full logs -----
log_dir = os.path.join(os.path.dirname(__file__), 'data', 'sanity_tests')
os.makedirs(log_dir, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_path = os.path.join(log_dir, f"sanity_{timestamp}.json")

# Collect all traces per agent
all_traces = {}
for aid in agent_ids:
    all_traces[aid] = agents[aid].get_reasoning_traces()

# Build structured log
log_data = {
    "config": {
        "model": MODEL,
        "num_agents": NUM_AGENTS,
        "num_rounds": NUM_ROUNDS,
        "comm_scope": COMM_SCOPE,
        "reasoning_level": REASONING_LEVEL,
        "seed": SEED,
        "game_params": game_params,
    },
    "initial_network": {aid: network.get_neighbors(aid) for aid in agent_ids},
    "final_network": {aid: network.get_neighbors(aid) for aid in agent_ids},
    "final_resources": dict(final.resources),
    "history": final.history,
    "traces": all_traces,
    "memories": {aid: agents[aid].memory.to_dict() for aid in agent_ids if agents[aid].memory},
}

with open(log_path, 'w') as f:
    json.dump(log_data, f, indent=2, default=str)

print(f"\n📁 Full logs saved to: {log_path}")
print(f"   Inspect with: python -m json.tool {log_path} | less")
