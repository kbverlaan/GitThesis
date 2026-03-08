"""
Integration test: run a real 3-agent, 3-round simulation with memory enabled.

Uses OpenRouter (gemini-2.5-flash-lite) for actual LLM calls.
Prints the full prompt sent to each agent at each round so we can verify
memory accumulates correctly in the real pipeline.
"""

import os
import sys
import json
import yaml
import random
import numpy as np
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent / "src"))

from game.engine import GameEngine, GameState
from game.spatial import SpatialField
from agents.llm_agent import LLMAgent
from agents.prompts import get_prompt_style

load_dotenv()

# --- Minimal config ---
GAME_PARAMS = {
    "num_agents": 3,
    "initial_resources": 25.0,
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
    "max_rounds": 3,
    "history_length": 10,
    "allow_invest_self": True,
    "initial_distribution": "equal",
    "action_order": "simultaneous",
    "spatial_enabled": True,
    "interaction_radius": 2,
    # Game params used by prompt formatting
    "invest_self_cost_pct": 10,
    "invest_self_return_pct": 20,
    "invest_other_cost_pct": 10,
    "invest_other_return_pct": 15,
    "arm_cost_pct": 10,
    "arm_other_cost_pct": 10,
    "arm_decay": 0.5,
    "attack_take_pct": 40,
    "conflict_cost_pct": 5,
    # Memory
    "memory": {
        "enabled": True,
        "window_size": 10,
    },
}

OPENROUTER_CONFIG = {
    "api_key_env_var": "OPENROUTER_API_KEY",
    "base_url": "https://openrouter.ai/api/v1",
    "model": "google/gemini-2.5-flash-lite",
    "temperature": 0.7,
    "max_tokens": 500,
    "timeout": 30,
    "retry_attempts": 2,
    "retry_delay": 2,
    "prompt_config": {
        "objective_style": "maximize_resources",
    },
}


def main():
    seed = 42
    np.random.seed(seed)
    random.seed(seed)

    agent_ids = [f"agent_{i+1}" for i in range(GAME_PARAMS["num_agents"])]

    # Engine
    engine = GameEngine(
        agent_ids=agent_ids,
        initial_resources=GAME_PARAMS["initial_resources"],
        invest_self_cost=GAME_PARAMS["invest_self_cost"],
        invest_self_return=GAME_PARAMS["invest_self_return"],
        invest_other_cost=GAME_PARAMS["invest_other_cost"],
        invest_other_return=GAME_PARAMS["invest_other_return"],
        arm_cost=GAME_PARAMS["arm_cost"],
        arm_multiplier=GAME_PARAMS["arm_multiplier"],
        arm_duration=GAME_PARAMS["arm_duration"],
        arm_other_contribution=GAME_PARAMS["arm_other_contribution"],
        arm_other_duration=GAME_PARAMS["arm_other_duration"],
        attack_take_percent=GAME_PARAMS["attack_take_percent"],
        conflict_cost=GAME_PARAMS["conflict_cost"],
        max_rounds=GAME_PARAMS["max_rounds"],
    )

    # Spatial — small grid, all agents close (everyone sees everyone for simplicity)
    grid_size = 5
    spatial_field = SpatialField(grid_size, agent_ids, interaction_radius=GAME_PARAMS["interaction_radius"])

    # LLM Agents with memory
    api_key = os.getenv(OPENROUTER_CONFIG["api_key_env_var"])
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set")
        sys.exit(1)

    memory_config = GAME_PARAMS["memory"]
    prompt_config = OPENROUTER_CONFIG.get("prompt_config", {})

    agents = {}
    for agent_id in agent_ids:
        agents[agent_id] = LLMAgent(
            agent_id=agent_id,
            api_key=api_key,
            model=OPENROUTER_CONFIG["model"],
            prompt_config=prompt_config,
            game_params=GAME_PARAMS,
            temperature=OPENROUTER_CONFIG["temperature"],
            max_tokens=OPENROUTER_CONFIG["max_tokens"],
            timeout=OPENROUTER_CONFIG["timeout"],
            retry_attempts=OPENROUTER_CONFIG["retry_attempts"],
            retry_delay=OPENROUTER_CONFIG["retry_delay"],
            base_url=OPENROUTER_CONFIG["base_url"],
            memory_config=memory_config,
        )

    print(f"Model: {OPENROUTER_CONFIG['model']}")
    print(f"Agents: {agent_ids}")
    print(f"Memory enabled: {memory_config.get('enabled')}")
    print(f"Rounds: {GAME_PARAMS['max_rounds']}")
    print()

    # --- Run rounds ---
    max_rounds = GAME_PARAMS["max_rounds"]
    history_length = GAME_PARAMS["history_length"]

    for round_idx in range(max_rounds):
        state = engine.get_state()
        round_num = state.round_number

        print(f"\n{'='*70}")
        print(f"ROUND {round_num}")
        print(f"{'='*70}")
        print(f"Resources: {dict(state.resources)}")

        spatial_field.move_agents()

        # Collect actions
        actions = []
        prompts_sent = {}

        for agent_id in agent_ids:
            observation = state.get_observation(agent_id, history_length)
            observation["broke_agents"] = []
            neighbors = spatial_field.get_neighbors(agent_id)
            observation["visible_agents"] = neighbors

            # Inject memory
            if agents[agent_id].memory is not None:
                observation["agent_memory"] = agents[agent_id].memory

            # Capture the prompt that will be sent
            prompt_text = agents[agent_id].prompt.format_observation(observation, agent_id)
            prompts_sent[agent_id] = prompt_text

            action = agents[agent_id].select_action(observation)
            actions.append(action)

            action_desc = action.action_type.value
            if action.target_id:
                action_desc += f" -> {action.target_id}"
            print(f"\n  {agent_id}: {action_desc}")

        # Resolve
        round_result = engine.resolve_round(actions)
        updated_state = engine.get_state()

        print(f"\n  Resource changes: {round_result['resource_changes']}")
        for combat in round_result.get("combat_results", []):
            print(f"  Combat: {combat['attacker']} vs {combat['defender']} -> {combat['winner']} won")
        print(f"  Resources after: {dict(updated_state.resources)}")

        # Update memories
        post_resources = dict(updated_state.resources)
        round_actions = round_result["actions"]
        resource_changes = round_result["resource_changes"]
        combat_results = round_result.get("combat_results", [])

        agent_action_map = {}
        for a in round_actions:
            agent_action_map[a["agent"]] = (a.get("action", "no_action"), a.get("target"))

        agent_outcomes = {}
        for a in round_actions:
            aid = a["agent"]
            outcome = {}
            rc = resource_changes.get(aid, 0.0)
            if abs(rc) > 0.001:
                outcome["resource_change"] = rc
            for combat in combat_results:
                if combat["attacker"] == aid:
                    outcome["combat_won"] = combat["winner"] == aid
            agent_outcomes[aid] = outcome

        for aid in agent_ids:
            action_str, target = agent_action_map.get(aid, ("no_action", None))
            visible = spatial_field.get_neighbors(aid)
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
            )

    # --- Print final prompts and memory state ---
    print(f"\n\n{'='*70}")
    print("PROMPTS SENT IN LAST ROUND")
    print(f"{'='*70}")

    for agent_id in agent_ids:
        print(f"\n{'~'*70}")
        print(f"{agent_id}")
        print(f"{'~'*70}")
        # Show only memory sections from last round's prompt
        prompt = prompts_sent[agent_id]
        for section in prompt.split("\n\n"):
            if any(k in section for k in ["YOUR RECENT", "NEIGHBOR MEMORY"]):
                print(section)
                print()

    # --- Dump memory state ---
    print(f"\n{'='*70}")
    print("FINAL MEMORY STATE (serialized)")
    print(f"{'='*70}")
    for agent_id in agent_ids:
        mem = agents[agent_id].memory
        if mem:
            print(f"\n{agent_id}:")
            d = mem.to_dict()
            print(f"  action_log ({len(d['action_log'])} entries):")
            for entry in d["action_log"]:
                print(f"    R{entry['round']}: {entry['action']}" +
                      (f" -> {entry['target']}" if entry['target'] else "") +
                      (f" | {entry['outcome']}" if entry['outcome'] else ""))
            print(f"  neighbors ({len(d['neighbor_observations'])} tracked):")
            for nid, nrec in d["neighbor_observations"].items():
                print(f"    {nid}: seen={nrec['times_seen']} toward_me={nrec['their_actions_toward_me']} "
                      f"from_me={nrec['my_actions_toward_them']} general={nrec['their_actions_general']}")

    print("\nDone.")


if __name__ == "__main__":
    main()
