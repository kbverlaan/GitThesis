"""
Quick test: Qwen3.5-35B-A3B on 10 realistic game prompts.
Covers L0-L3 reasoning levels, early/mid/late game, rich/poor agents, armed neighbors.

Usage on Snellius:
  1. Start vLLM: (see snellius_run.sh or run manually)
  2. python test_qwen35.py
  3. Results saved to test_qwen35_results.json

Locally against a running vLLM server:
  VLLM_BASE_URL=http://localhost:8000/v1 python test_qwen35.py
"""

import json
import os
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = os.environ.get("VLLM_BASE_URL", "http://localhost:8000/v1")
MODEL = os.environ.get("VLLM_MODEL", "/scratch-shared/kverlaan/origins_models/Qwen3.5-27B")

# Game params matching production config (%-based economy)
GAME_PARAMS = {
    "invest_self_cost_pct": 10, "invest_self_return_pct": 20,
    "invest_other_cost_pct": 10, "invest_other_return_mult": 1.5,
    "arm_cost_pct": 10, "arm_initial_multiplier": 2.0, "arm_decay": 0.5,
    "arm_other_cost_pct": 10,
    "attack_take_pct": 40, "conflict_cost_pct": 5,
}

_iot = GAME_PARAMS['invest_other_cost_pct'] * GAME_PARAMS['invest_other_return_mult']

ACTIONS_BLOCK = f"""Choose exactly ONE action this round.

AVAILABLE ACTIONS:
- invest_self: spend {GAME_PARAMS['invest_self_cost_pct']}% of your resources, gain {GAME_PARAMS['invest_self_return_pct']}% (net +{GAME_PARAMS['invest_self_return_pct'] - GAME_PARAMS['invest_self_cost_pct']}% for you)
- invest_other: spend {GAME_PARAMS['invest_other_cost_pct']}% of your resources, TARGET gains {_iot:.0f}% of your resources (grows the total economy)
- arm_self: spend {GAME_PARAMS['arm_cost_pct']}% of your resources (removed from economy), adds that amount to your combat strength. Your total combat strength = resources + arm bonus.
- arm_other: spend {GAME_PARAMS['arm_other_cost_pct']}% of your resources (removed from economy), adds that amount to TARGET's combat strength. TARGET's resource count does NOT increase — only their fighting power.
- attack: both pay {GAME_PARAMS['conflict_cost_pct']}% of own resources, winner takes {GAME_PARAMS['attack_take_pct']}% of loser's resources
- do_nothing: no cost, no effect

COMBAT RULES:
- Combat strength = your resources + your arm bonus
- arm_self adds {GAME_PARAMS['arm_cost_pct']}% of your resources to your arm bonus
- arm_other adds {GAME_PARAMS['arm_other_cost_pct']}% of your resources to TARGET's arm bonus
- All arm bonuses decay: they halve each round (x{GAME_PARAMS['arm_decay']} per round)
- Win probability = your_strength / (your_strength + opponent_strength)
- Costs are a % of your current resources, so always affordable unless you have 0."""

REASONING_BLOCKS = {
    "L0": None,
    "L1": (
        "THINK BEFORE CHOOSING:\n"
        "Assume other agents pick actions without strategic calculation.\n"
        "For each available action, compute its expected resource change:\n"
        "- invest_self/invest_other/do_nothing: use the costs and returns listed above.\n"
        "- arm_self: cost now vs combat advantage later (only useful if you expect to attack or be attacked).\n"
        "- attack: expected gain = win_probability x take% x opponent_resources, minus conflict_cost.\n"
        "Compare these values and choose the action with the highest expected payoff.\n"
        "Do NOT predict what specific neighbors will do — treat their actions as unknown."
    ),
    "L2": (
        "THINK BEFORE CHOOSING:\n"
        "Assume other agents pick their individually best action given the current state.\n"
        "1. For each neighbor, predict their most likely action based on:\n"
        "   - Their recent behavior pattern (shown in NEIGHBOR PROFILES)\n"
        "   - Their current resources and armed status\n"
        "   - What action would give THEM the best payoff right now\n"
        "2. Given these predictions, choose your best response.\n"
        "Do NOT reason about what neighbors think about YOU — only predict what they will do."
    ),
    "L3": (
        "THINK BEFORE CHOOSING:\n"
        "Assume other agents look at YOUR recent actions to predict what you will do, "
        "then pick their best response to that prediction.\n"
        "1. Look at your own recent actions in NEIGHBOR PROFILES (the 'you ... them' entries). "
        "What pattern do your neighbors see? What action would they predict you take this round?\n"
        "2. For each neighbor: given their prediction of YOUR action, what will THEY choose?\n"
        "3. Now choose YOUR best action given what each neighbor will do — "
        "which may differ from what they expect you to do."
    ),
}

JSON_TEMPLATE = """Your final output MUST be valid JSON with exactly these fields:
{
  "action": "<one of the action names above>",
  "target": "<agent_id or null>"
}
Do not include any text outside the JSON."""


def build_prompt(scenario):
    """Build a full prompt from a scenario dict."""
    parts = []
    parts.append(f"You are {scenario['agent_id']}.")
    parts.append(f"OBJECTIVE: Maximize your absolute resource count.")

    # State
    state_lines = [f"CURRENT STATE (Round {scenario['round']}):"]
    state_lines.append(f"\nYou can only interact with nearby agents this round.")
    state_lines.append(f"Nearby agents: {', '.join(scenario['neighbors'])}")
    state_lines.append("\nRESOURCES:")
    for aid, res in scenario['resources'].items():
        marker = " (you)" if aid == scenario['agent_id'] else ""
        broke = " [BROKE]" if res <= 0 else ""
        state_lines.append(f"  {aid}: {res:.1f}{marker}{broke}")
    if scenario.get('arm_bonuses'):
        state_lines.append("\nARM BONUSES (combat strength = resources + arm bonus):")
        for aid, bonus in sorted(scenario['arm_bonuses'].items()):
            state_lines.append(f"  {aid}: +{bonus:.1f}")
    parts.append("\n".join(state_lines))

    # Neighbor profiles
    if scenario.get('profiles'):
        profile_lines = [f"NEIGHBOR PROFILES (last {scenario.get('history_rounds', 10)} rounds):"]
        for p in scenario['profiles']:
            profile_lines.append(f"  {p}")
        parts.append("\n".join(profile_lines))

    # Actions + reasoning block
    action_parts = [ACTIONS_BLOCK]
    rb = REASONING_BLOCKS.get(scenario['level'])
    if rb:
        action_parts.append(rb)
    action_parts.append(JSON_TEMPLATE)
    parts.append("\n\n".join(action_parts))

    return "\n\n".join(parts)


# 10 diverse test scenarios
SCENARIOS = [
    {
        "name": "L0 - Early game, equal start",
        "level": "L0",
        "agent_id": "agent_7",
        "round": 2,
        "neighbors": ["agent_3", "agent_12", "agent_15", "agent_22"],
        "resources": {"agent_7": 25.0, "agent_3": 25.0, "agent_12": 25.0, "agent_15": 25.0, "agent_22": 25.0},
        "arm_bonuses": {},
        "profiles": [
            "agent_3 [25]: invest other | invest other you 1x",
            "agent_12 [25]: do nothing | no direct interaction",
            "agent_15 [25]: invest other | no direct interaction",
            "agent_22 [25]: arm self | no direct interaction",
        ],
    },
    {
        "name": "L1 - Mid game, you're rich",
        "level": "L1",
        "agent_id": "agent_14",
        "round": 20,
        "neighbors": ["agent_2", "agent_8", "agent_19", "agent_25"],
        "resources": {"agent_14": 89.0, "agent_2": 31.0, "agent_8": 12.0, "agent_19": 45.0, "agent_25": 5.0},
        "arm_bonuses": {"agent_14": 5.0},  # armed 1 round ago, decayed once
        "profiles": [
            "agent_2 [31]: invest other | invest other you 3x | you invest other them 2x",
            "agent_8 [12]: mixed | attacked you 1x",
            "agent_19 [45]: arm self | no direct interaction",
            "agent_25 [5 BROKE]: do nothing | you attack them 1x",
        ],
    },
    {
        "name": "L2 - Mid game, you're poor, neighbors armed",
        "level": "L2",
        "agent_id": "agent_21",
        "round": 15,
        "neighbors": ["agent_1", "agent_5", "agent_11", "agent_28"],
        "resources": {"agent_21": 8.0, "agent_1": 120.0, "agent_5": 45.0, "agent_11": 32.0, "agent_28": 15.0},
        "arm_bonuses": {"agent_1": 12.0, "agent_5": 2.3},  # agent_1 just armed, agent_5 decayed twice
        "profiles": [
            "agent_1 [120]: attack | attacked you 2x | you invest other them 1x",
            "agent_5 [45]: arm self | no direct interaction",
            "agent_11 [32]: invest other | invest other you 2x",
            "agent_28 [15]: mixed | no direct interaction",
        ],
    },
    {
        "name": "L3 - Late game, hegemon nearby",
        "level": "L3",
        "agent_id": "agent_9",
        "round": 42,
        "neighbors": ["agent_3", "agent_16", "agent_20"],
        "resources": {"agent_9": 35.0, "agent_3": 310.0, "agent_16": 18.0, "agent_20": 7.0},
        "arm_bonuses": {"agent_3": 47.0},  # hegemon armed + received arm_other, all on one pile
        "profiles": [
            "agent_3 [310]: attack | attacked you 1x | invest other you 3x",
            "agent_16 [18]: invest other | invest other you 4x | you invest other them 3x",
            "agent_20 [7 BROKE]: do nothing | no direct interaction",
        ],
        "history_rounds": 10,
    },
    {
        "name": "L0 - Mid game, all neighbors cooperative",
        "level": "L0",
        "agent_id": "agent_4",
        "round": 25,
        "neighbors": ["agent_6", "agent_10", "agent_17", "agent_23", "agent_29"],
        "resources": {"agent_4": 55.0, "agent_6": 60.0, "agent_10": 48.0, "agent_17": 52.0, "agent_23": 45.0, "agent_29": 40.0},
        "arm_bonuses": {},
        "profiles": [
            "agent_6 [60]: invest other | invest other you 5x | you invest other them 4x",
            "agent_10 [48]: invest other | invest other you 3x | you invest other them 3x",
            "agent_17 [52]: invest other | no direct interaction",
            "agent_23 [45]: invest other | invest other you 2x",
            "agent_29 [40]: invest other | you invest other them 1x",
        ],
    },
    {
        "name": "L2 - Early game, one aggressive neighbor",
        "level": "L2",
        "agent_id": "agent_18",
        "round": 5,
        "neighbors": ["agent_2", "agent_7", "agent_13"],
        "resources": {"agent_18": 22.0, "agent_2": 38.0, "agent_7": 20.0, "agent_13": 25.0},
        "arm_bonuses": {"agent_2": 3.8},  # agent_2 armed recently
        "profiles": [
            "agent_2 [38]: attack | attacked agent_7 2x | arm self 2x",
            "agent_7 [20]: invest other | invest other you 1x",
            "agent_13 [25]: invest other | no direct interaction",
        ],
    },
    {
        "name": "L1 - Late game, you're losing",
        "level": "L1",
        "agent_id": "agent_26",
        "round": 45,
        "neighbors": ["agent_4", "agent_11", "agent_30"],
        "resources": {"agent_26": 4.0, "agent_4": 95.0, "agent_11": 67.0, "agent_30": 12.0},
        "arm_bonuses": {},
        "profiles": [
            "agent_4 [95]: invest other | invest other you 1x | you invest other them 3x",
            "agent_11 [67]: arm self | no direct interaction",
            "agent_30 [12]: attack | attacked you 1x",
        ],
    },
    {
        "name": "L3 - Mid game, arms race happening",
        "level": "L3",
        "agent_id": "agent_15",
        "round": 18,
        "neighbors": ["agent_1", "agent_8", "agent_22", "agent_27"],
        "resources": {"agent_15": 40.0, "agent_1": 55.0, "agent_8": 42.0, "agent_22": 38.0, "agent_27": 30.0},
        "arm_bonuses": {"agent_1": 2.8, "agent_8": 2.1, "agent_22": 3.8},  # all armed at different times
        "profiles": [
            "agent_1 [55]: arm self | arm self 4x | attack 1x",
            "agent_8 [42]: arm self | arm self 3x | no direct interaction",
            "agent_22 [38]: arm self | arm self 5x | attacked you 1x",
            "agent_27 [30]: invest other | invest other you 2x | you invest other them 1x",
        ],
    },
    {
        "name": "L2 - Late game, wealth inequality",
        "level": "L2",
        "agent_id": "agent_12",
        "round": 48,
        "neighbors": ["agent_5", "agent_19", "agent_24"],
        "resources": {"agent_12": 72.0, "agent_5": 180.0, "agent_19": 30.0, "agent_24": 15.0},
        "arm_bonuses": {"agent_5": 9.0},  # armed recently
        "profiles": [
            "agent_5 [180]: attack | attacked agent_19 3x | invest other you 2x",
            "agent_19 [30]: invest other | invest other you 6x | you invest other them 5x",
            "agent_24 [15]: do nothing | no direct interaction",
        ],
    },
    {
        "name": "L3 - Early game, fresh start, predict others",
        "level": "L3",
        "agent_id": "agent_1",
        "round": 3,
        "neighbors": ["agent_6", "agent_10", "agent_14", "agent_20", "agent_25"],
        "resources": {"agent_1": 28.0, "agent_6": 30.0, "agent_10": 22.0, "agent_14": 35.0, "agent_20": 25.0, "agent_25": 25.0},
        "arm_bonuses": {},
        "profiles": [
            "agent_6 [30]: invest other | invest other you 1x",
            "agent_10 [22]: arm self | no direct interaction",
            "agent_14 [35]: invest other | no direct interaction",
            "agent_20 [25]: invest other | you invest other them 1x",
            "agent_25 [25]: do nothing | no direct interaction",
        ],
    },
]


def query_model(prompt, scenario_name, enable_thinking=True):
    """Send prompt to vLLM and return full response."""
    try:
        # Qwen3.5 recommended sampling: thinking mode uses T=1.0, non-thinking uses T=0.7
        # See: https://huggingface.co/Qwen/Qwen3.5-27B
        body = {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 1.0 if enable_thinking else 0.7,
            "top_p": 0.95 if enable_thinking else 0.8,
            "top_k": 20,
            "max_tokens": 16000,
        }
        # Disable thinking for L0 (reactive, no deliberation)
        if not enable_thinking:
            body["chat_template_kwargs"] = {"enable_thinking": False}

        resp = requests.post(
            f"{BASE_URL}/chat/completions",
            json=body,
            timeout=300,
        )
        resp.raise_for_status()
        data = resp.json()
        choice = data["choices"][0]

        # Extract thinking (reasoning model) and content separately
        # vLLM v0.16.x uses "reasoning", OpenRouter uses "reasoning_content"
        message = choice.get("message", {})
        thinking = message.get("reasoning", "") or message.get("reasoning_content", "") or ""
        content = message.get("content", "") or ""
        usage = data.get("usage", {})

        # Debug: log raw message keys for first call
        if not hasattr(query_model, '_logged'):
            import sys
            print(f"  [DEBUG] message keys: {list(message.keys())}", file=sys.stderr)
            print(f"  [DEBUG] message: {json.dumps({k: (v[:100] if isinstance(v, str) else v) for k, v in message.items()})}", file=sys.stderr)
            print(f"  [DEBUG] finish_reason: {choice.get('finish_reason')}", file=sys.stderr)
            print(f"  [DEBUG] usage: {usage}", file=sys.stderr)
            query_model._logged = True

        return {
            "thinking": thinking,
            "content": content,
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "thinking_tokens": usage.get("reasoning_tokens", usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0)),
        }
    except Exception as e:
        return {"error": str(e), "thinking": "", "content": ""}


def run_scenario(i, scenario):
    """Run a single scenario and return result dict."""
    prompt = build_prompt(scenario)
    enable_thinking = scenario["level"] != "L0"
    t0 = time.time()
    response = query_model(prompt, scenario["name"], enable_thinking=enable_thinking)
    elapsed = time.time() - t0
    return {
        "scenario": scenario["name"],
        "level": scenario["level"],
        "agent_id": scenario["agent_id"],
        "round": scenario["round"],
        "prompt_length": len(prompt),
        "elapsed_seconds": round(elapsed, 1),
        **response,
    }


def print_results(results, label):
    """Print summary table for a set of results."""
    print(f"\n{'Scenario':<45} {'Level':<5} {'Action':<15} {'Think':<8} {'Time':<6}")
    print("-" * 85)
    for r in results:
        if r.get("error"):
            print(f"{r['scenario']:<45} {r['level']:<5} {'ERROR':<15}")
            continue
        action = "???"
        try:
            parsed = json.loads(r["content"])
            action = parsed.get("action", "???")
            target = parsed.get("target")
            if target:
                action = f"{action}->{target}"
        except:
            for a in ["invest_other", "arm_self", "arm_other", "attack", "do_nothing"]:
                if a in r["content"]:
                    action = a
                    break
        think_len = len(r.get("thinking", ""))
        print(f"{r['scenario']:<45} {r['level']:<5} {action:<15} {think_len:<8} {r['elapsed_seconds']:<6}")


def main():
    print(f"Testing Qwen3.5-27B at {BASE_URL}")
    print(f"Model: {MODEL}")
    print(f"Scenarios: {len(SCENARIOS)}")

    # === Phase 1: Sequential (baseline) ===
    print("\n" + "=" * 80)
    print("PHASE 1: SEQUENTIAL (baseline)")
    print("=" * 80)

    seq_results = []
    t_seq_start = time.time()
    for i, scenario in enumerate(SCENARIOS):
        print(f"\n[{i+1}/{len(SCENARIOS)}] {scenario['name']}")
        result = run_scenario(i, scenario)
        seq_results.append(result)
        if result.get("error"):
            print(f"  ERROR: {result['error']}")
        else:
            print(f"  Thinking: {len(result['thinking'])} chars | Content: {result['content'][:100]}")
            print(f"  Tokens: {result.get('prompt_tokens', '?')}p + {result.get('completion_tokens', '?')}c ({result['elapsed_seconds']}s)")
    t_seq_total = time.time() - t_seq_start

    print_results(seq_results, "Sequential")
    print(f"\nSequential total wall time: {t_seq_total:.1f}s")

    # === Phase 2: Concurrent (throughput test) ===
    print("\n" + "=" * 80)
    print("PHASE 2: CONCURRENT (all 10 at once)")
    print("=" * 80)

    conc_results = [None] * len(SCENARIOS)
    t_conc_start = time.time()
    with ThreadPoolExecutor(max_workers=len(SCENARIOS)) as executor:
        futures = {executor.submit(run_scenario, i, s): i for i, s in enumerate(SCENARIOS)}
        for future in as_completed(futures):
            idx = futures[future]
            result = future.result()
            conc_results[idx] = result
            print(f"  [{idx+1}] {result['scenario']}: {result['elapsed_seconds']}s")
    t_conc_total = time.time() - t_conc_start

    print_results(conc_results, "Concurrent")
    print(f"\nConcurrent total wall time: {t_conc_total:.1f}s")

    # === Comparison ===
    print("\n" + "=" * 80)
    print("THROUGHPUT COMPARISON")
    print("=" * 80)
    print(f"Sequential:  {t_seq_total:.1f}s total")
    print(f"Concurrent:  {t_conc_total:.1f}s total")
    print(f"Speedup:     {t_seq_total / t_conc_total:.1f}x")

    # Save all results
    output = {
        "sequential": {"results": seq_results, "wall_time_s": round(t_seq_total, 1)},
        "concurrent": {"results": conc_results, "wall_time_s": round(t_conc_total, 1)},
        "speedup": round(t_seq_total / t_conc_total, 1),
    }
    outfile = "test_qwen35_results.json"
    with open(outfile, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {outfile}")


if __name__ == "__main__":
    main()
