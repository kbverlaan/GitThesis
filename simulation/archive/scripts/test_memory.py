"""
Test script for persistent agent memory.

Simulates 5 rounds with scripted actions (no LLM calls) and prints
the full prompt that each agent would see at each round. This lets us
verify that memory accumulates correctly and the prompt output is
complete and accurate.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from agents.memory import AgentMemory
from agents.prompts import BaselinePrompt
from game.engine import GameEngine, ActionType, Action
from game.spatial import SpatialField

# --- Config ---
AGENT_IDS = ["agent_1", "agent_2", "agent_3", "agent_4", "agent_5"]
INITIAL_RESOURCES = 25.0
GAME_PARAMS = {
    "invest_self_cost_pct": 10,
    "invest_self_return_pct": 20,
    "invest_other_cost_pct": 10,
    "invest_other_return_pct": 15,
    "arm_cost_pct": 10,
    "arm_other_cost_pct": 10,
    "arm_decay": 0.5,
    "attack_take_pct": 40,
    "conflict_cost_pct": 5,
    "allow_invest_self": True,
}
ENGINE_PARAMS = {
    "invest_self_cost": 0,
    "invest_self_return": 2,
    "invest_other_cost": 0,
    "invest_other_return": 5,
    "arm_cost": 0,
    "arm_multiplier": 2.0,
    "arm_duration": 3,
    "arm_other_contribution": 0.5,
    "arm_other_duration": 3,
    "attack_take_percent": 40.0,
    "conflict_cost": 0,
    "max_rounds": 10,
}
WINDOW_SIZE = 10

# --- Scripted actions per round ---
# Each round: list of (agent_id, action_type, target_or_none)
SCRIPTED_ROUNDS = [
    # Round 1: agent_1 invests in agent_2, agent_2 invests self, agent_3 arms, agent_4 invests in agent_5, agent_5 does nothing
    [
        ("agent_1", ActionType.INVEST_OTHER, "agent_2"),
        ("agent_2", ActionType.INVEST_SELF, None),
        ("agent_3", ActionType.ARM_SELF, None),
        ("agent_4", ActionType.INVEST_OTHER, "agent_5"),
        ("agent_5", ActionType.DO_NOTHING, None),
    ],
    # Round 2: agent_3 attacks agent_1, agent_2 invests in agent_1, agent_4 invests self, agent_5 invests in agent_4
    [
        ("agent_1", ActionType.INVEST_SELF, None),
        ("agent_2", ActionType.INVEST_OTHER, "agent_1"),
        ("agent_3", ActionType.ATTACK, "agent_1"),
        ("agent_4", ActionType.INVEST_SELF, None),
        ("agent_5", ActionType.INVEST_OTHER, "agent_4"),
    ],
    # Round 3: agent_1 attacks agent_3 (revenge), agent_2 invests self, agent_4 arms, agent_5 invests in agent_2
    [
        ("agent_1", ActionType.ATTACK, "agent_3"),
        ("agent_2", ActionType.INVEST_SELF, None),
        ("agent_4", ActionType.ARM_SELF, None),
        ("agent_5", ActionType.INVEST_OTHER, "agent_2"),
        ("agent_3", ActionType.ARM_SELF, None),
    ],
    # Round 4: agent_1 invests in agent_2 (cooperate), agent_3 attacks agent_2, agent_4 attacks agent_5, agent_5 do nothing
    [
        ("agent_1", ActionType.INVEST_OTHER, "agent_2"),
        ("agent_2", ActionType.INVEST_OTHER, "agent_1"),
        ("agent_3", ActionType.ATTACK, "agent_2"),
        ("agent_4", ActionType.ATTACK, "agent_5"),
        ("agent_5", ActionType.DO_NOTHING, None),
    ],
    # Round 5: mixed
    [
        ("agent_1", ActionType.INVEST_SELF, None),
        ("agent_2", ActionType.INVEST_OTHER, "agent_1"),
        ("agent_3", ActionType.INVEST_SELF, None),
        ("agent_4", ActionType.INVEST_OTHER, "agent_3"),
        ("agent_5", ActionType.ARM_SELF, None),
    ],
]

# --- Spatial setup: small grid so some agents can't see each other ---
# Use a 5x5 grid with radius 2. Place agents manually for controlled visibility.
import numpy as np
np.random.seed(42)

spatial = SpatialField(grid_size=20, agent_ids=AGENT_IDS, interaction_radius=2)
# Override positions for predictable visibility
# Cluster A: agents 1-3 close together at (1,1) area
# Cluster B: agents 4-5 far away at (15,15) area
# With radius=2 on a 20x20 grid, clusters can't see each other
spatial.positions = {
    "agent_1": (1, 1),
    "agent_2": (2, 1),
    "agent_3": (1, 2),
    "agent_4": (15, 15),
    "agent_5": (15, 14),
}


def main():
    # Init engine
    engine = GameEngine(agent_ids=AGENT_IDS, initial_resources=INITIAL_RESOURCES, **ENGINE_PARAMS)

    # Init memories
    memories = {aid: AgentMemory(aid, window_size=WINDOW_SIZE) for aid in AGENT_IDS}

    # Init prompt
    prompt = BaselinePrompt(game_params=GAME_PARAMS)

    for round_idx, scripted_actions in enumerate(SCRIPTED_ROUNDS):
        round_num = round_idx + 1
        state = engine.get_state()

        print(f"\n{'='*80}")
        print(f"ROUND {round_num}")
        print(f"{'='*80}")
        print(f"\nResources before: {dict(state.resources)}")

        # Build actions
        actions = [
            Action(agent_id=aid, action_type=atype, target_id=target)
            for aid, atype, target in scripted_actions
        ]

        # Resolve
        round_result = engine.resolve_round(actions)
        updated_state = engine.get_state()

        print(f"Actions: {[(a['agent'], a['action'], a.get('target')) for a in round_result['actions']]}")
        print(f"Resource changes: {round_result['resource_changes']}")
        if round_result['combat_results']:
            for c in round_result['combat_results']:
                print(f"  Combat: {c['attacker']} vs {c['defender']} -> winner: {c['winner']} (p={c['attacker_win_prob']:.2f})")
        print(f"Resources after: {dict(updated_state.resources)}")

        # Update memories
        post_resources = dict(updated_state.resources)
        round_actions = round_result['actions']
        resource_changes = round_result['resource_changes']
        combat_results = round_result['combat_results']

        for aid in AGENT_IDS:
            # Find this agent's action
            agent_action = next((a for a in round_actions if a['agent'] == aid), None)
            action_str = agent_action['action'] if agent_action else 'no_action'
            target = agent_action.get('target') if agent_action else None

            # Build outcome
            outcome = {}
            rc = resource_changes.get(aid, 0.0)
            if abs(rc) > 0.001:
                outcome['resource_change'] = rc
            # Only attach combat_won to attackers (defenders had a different action)
            for combat in combat_results:
                if combat['attacker'] == aid:
                    outcome['combat_won'] = (combat['winner'] == aid)

            # Get visible agents from spatial
            visible = spatial.get_neighbors(aid)

            memories[aid].record_action(round_num, action_str, target, outcome)
            memories[aid].update_observations(
                round_num, visible, round_actions,
                resource_changes, combat_results, post_resources
            )

    # --- Print full prompts for selected agents after round 5 ---
    print("\n" + "="*80)
    print("FULL PROMPTS AFTER 5 ROUNDS")
    print("="*80)

    final_state = engine.get_state()

    # Show visibility
    print("\nSpatial positions:")
    for aid in AGENT_IDS:
        pos = spatial.positions[aid]
        neighbors = spatial.get_neighbors(aid)
        print(f"  {aid} at {pos}: sees {neighbors}")

    for focus_agent in ["agent_1", "agent_3", "agent_4"]:
        print(f"\n{'~'*80}")
        print(f"PROMPT FOR {focus_agent}")
        print(f"{'~'*80}")

        observation = final_state.get_observation(focus_agent, WINDOW_SIZE)
        observation['broke_agents'] = []
        neighbors = spatial.get_neighbors(focus_agent)
        observation['visible_agents'] = neighbors
        observation['agent_memory'] = memories[focus_agent]

        full_prompt = prompt.format_observation(observation, focus_agent)
        print(full_prompt)

    # --- Also show what the OLD prompt would look like for comparison ---
    print(f"\n{'~'*80}")
    print(f"LEGACY PROMPT FOR agent_1 (no memory, god-view profiles)")
    print(f"{'~'*80}")

    observation_legacy = final_state.get_observation("agent_1", WINDOW_SIZE)
    observation_legacy['broke_agents'] = []
    observation_legacy['visible_agents'] = spatial.get_neighbors("agent_1")
    # No agent_memory -> falls back to neighbor profiles

    legacy_prompt = prompt.format_observation(observation_legacy, "agent_1")
    print(legacy_prompt)


if __name__ == "__main__":
    main()
