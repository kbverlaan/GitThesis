"""
Sanity comparison: no-comm vs choice, same seed, Qwen 3.5-27B.
Runs both conditions and saves logs side by side.
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


def run_condition(comm_scope: str, seed: int = 42):
    """Run one condition and return structured results."""
    NUM_AGENTS = 5
    NUM_ROUNDS = 3
    REASONING_LEVEL = "level2"
    MODEL = "qwen/qwen3.5-27b"

    np.random.seed(seed)
    random.seed(seed)

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
        'comm_scope': comm_scope,
        'network_enabled': True,
        'mean_degree': 3.0,
        'rewiring_prob': 0.3,
        'payoff_window': 3,
        'memory': {'enabled': True, 'window_size': 10},
    }

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
            max_tokens=4096,
            timeout=120,
            retry_attempts=2,
            retry_delay=3,
            base_url="https://openrouter.ai/api/v1",
            memory_config=game_params['memory'],
        )

    print(f"\n{'='*80}")
    print(f"CONDITION: comm_scope={comm_scope}")
    print(f"{'='*80}")
    print(f"Initial network:")
    for aid in agent_ids:
        print(f"  {aid}: {network.get_neighbors(aid)}")

    pending_messages = {aid: [] for aid in agent_ids}
    resource_changes_history = []
    round_summaries = []

    for round_num in range(1, NUM_ROUNDS + 1):
        state = engine.get_state()
        print(f"\n--- Round {round_num}/{NUM_ROUNDS} ---")
        print(f"Resources: " + ", ".join(f"{aid}={state.resources[aid]:.1f}" for aid in agent_ids))

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

        # Print actions
        round_actions_summary = {}
        for aid in agent_ids:
            action = action_map[aid]
            desc = action.action_type.value
            if action.target_id:
                desc += f" → {action.target_id}"
            msg = agents[aid].get_last_message()
            msg_desc = ""
            if msg and msg.get('message'):
                to = msg.get('message_to', '?')
                msg_desc = f"  📨→{to}: \"{msg['message'][:60]}{'...' if len(msg.get('message','')) > 60 else ''}\""
            print(f"  {aid}: {desc}{msg_desc}")

            # Get thinking snippet
            traces = agents[aid].get_reasoning_traces()
            thinking = traces[-1].get('thinking', '') if traces else ''
            round_actions_summary[aid] = {
                'action': action.action_type.value,
                'target': action.target_id,
                'message': msg.get('message', '') if msg else '',
                'thinking_snippet': thinking[:300] if thinking else '',
            }

        round_summaries.append(round_actions_summary)

        # Resolve
        round_result = engine.resolve_round(actions)

        for combat in round_result.get('combat_results', []):
            attackers_str = ",".join(combat.get('attackers', []))
            print(f"  ⚔️ {attackers_str} vs {combat['defender']}: {combat['winner']} ({combat['attacker_win_prob']:.0%})")

        # Route messages
        if comm_scope != 'none':
            next_messages = {aid: [] for aid in agent_ids}
            for aid in agent_ids:
                msg = agents[aid].get_last_message()
                if msg and msg.get('message'):
                    msg_to = msg.get('message_to')
                    neighbors = network.get_neighbors(aid)
                    if msg_to == 'all' or comm_scope == 'broadcast':
                        for nbr in neighbors:
                            next_messages[nbr].append({'from': aid, 'message': msg['message'], 'channel': 'broadcast'})
                    elif msg_to and msg_to in neighbors:
                        next_messages[msg_to].append({'from': aid, 'message': msg['message'], 'channel': 'dm'})
            pending_messages = next_messages

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
                round_num=round_num, action_str=action_str, target=target,
                outcome=agent_outcomes.get(aid, {}), visible_agents=visible,
                round_actions=round_actions, resource_changes=resource_changes,
                combat_results=combat_results, all_resources=post_resources,
                received_messages=pending_messages.get(aid, []),
            )

        resource_changes_history.append(resource_changes)
        network.rewire(resource_changes_history)

    # Final state
    final = engine.get_state()
    print(f"\nFinal resources:")
    for aid in sorted(agent_ids, key=lambda a: final.resources[a], reverse=True):
        print(f"  {aid}: {final.resources[aid]:.1f}")

    # Action distribution
    action_counts = {}
    for rs in round_summaries:
        for aid, info in rs.items():
            a = info['action']
            action_counts[a] = action_counts.get(a, 0) + 1
    total_actions = sum(action_counts.values())
    print(f"Action distribution:")
    for a, c in sorted(action_counts.items(), key=lambda x: -x[1]):
        print(f"  {a}: {c}/{total_actions} ({c/total_actions:.0%})")

    # Build log
    all_traces = {}
    for aid in agent_ids:
        all_traces[aid] = agents[aid].get_reasoning_traces()

    return {
        "comm_scope": comm_scope,
        "seed": seed,
        "model": "qwen/qwen3.5-27b",
        "reasoning_level": "level2",
        "game_params": game_params,
        "initial_network": {aid: network.get_neighbors(aid) for aid in agent_ids},
        "final_resources": dict(final.resources),
        "action_distribution": action_counts,
        "round_summaries": round_summaries,
        "traces": all_traces,
        "memories": {aid: agents[aid].memory.to_dict() for aid in agent_ids if agents[aid].memory},
        "history": final.history,
    }


# ----- Run both conditions -----
if __name__ == "__main__":
    t0 = time.time()

    results = {}
    for scope in ["none", "choice"]:
        results[scope] = run_condition(scope, seed=42)

    elapsed = time.time() - t0

    # ----- Comparison summary -----
    print(f"\n{'='*80}")
    print(f"COMPARISON SUMMARY (seed=42, L2, Qwen 3.5-27B)")
    print(f"{'='*80}")
    print(f"Time: {elapsed:.0f}s")

    for scope in ["none", "choice"]:
        r = results[scope]
        res = r['final_resources']
        gini_vals = list(res.values())
        mean_r = np.mean(gini_vals)
        sorted_r = sorted(gini_vals)
        n = len(sorted_r)
        gini = sum(abs(sorted_r[i] - sorted_r[j]) for i in range(n) for j in range(n)) / (2 * n * sum(sorted_r))

        print(f"\n  comm_scope={scope}:")
        print(f"    Resources: {', '.join(f'{v:.1f}' for v in sorted(res.values(), reverse=True))}")
        print(f"    Mean: {mean_r:.1f}, Gini: {gini:.3f}")
        print(f"    Actions: {r['action_distribution']}")

    # Save
    log_dir = os.path.join(os.path.dirname(__file__), 'data', 'sanity_tests')
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(log_dir, f"sanity_compare_{timestamp}.json")
    with open(log_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n📁 Logs: {log_path}")
