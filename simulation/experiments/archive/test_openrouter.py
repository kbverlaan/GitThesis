"""
Quick OpenRouter test: Qwen3.5-27B with updated prompts.
Tests 3 parameter sets × select scenarios to verify prompt quality.

Usage: source .env && python test_openrouter.py
"""

import json
import os
import time
import requests

BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "qwen/qwen3.5-27b"
API_KEY = os.environ["OPENROUTER_API_KEY"]

# Three parameter regimes
PARAM_SETS = {
    "free": {
        "label": "Free (current defaults)",
        "invest_self_cost": 0, "invest_self_return": 2,
        "invest_other_cost": 0, "invest_other_return": 5,
        "arm_cost": 2, "arm_multiplier": 2, "arm_duration": 3,
        "arm_other_contribution": 0.5, "arm_other_duration": 3,
        "attack_take_percent": 40, "conflict_cost": 0,
        "allow_invest_self": True,
    },
    "moderate": {
        "label": "Moderate costs",
        "invest_self_cost": 1, "invest_self_return": 3,
        "invest_other_cost": 2, "invest_other_return": 5,
        "arm_cost": 5, "arm_multiplier": 2, "arm_duration": 3,
        "arm_other_contribution": 0.5, "arm_other_duration": 3,
        "attack_take_percent": 40, "conflict_cost": 3,
        "allow_invest_self": True,
    },
    "expensive": {
        "label": "Expensive (high stakes)",
        "invest_self_cost": 2, "invest_self_return": 4,
        "invest_other_cost": 3, "invest_other_return": 6,
        "arm_cost": 8, "arm_multiplier": 3, "arm_duration": 3,
        "arm_other_contribution": 0.5, "arm_other_duration": 3,
        "attack_take_percent": 50, "conflict_cost": 5,
        "allow_invest_self": True,
    },
}

REASONING_BLOCKS = {
    "L0": None,
    "L1": (
        "THINK BEFORE CHOOSING:\n"
        "Other agents choose without strategic reasoning.\n"
        "Calculate the expected value of each available action given the current state, "
        "then choose the one that maximizes your resources."
    ),
    "L2": (
        "THINK BEFORE CHOOSING:\n"
        "Other agents calculate their best action based on the current state (Level-1 reasoning).\n"
        "1. For each neighbor, predict what action they will likely choose based on their recent behavior and resources.\n"
        "2. Given these predictions, choose your best response."
    ),
    "L3": (
        "THINK BEFORE CHOOSING:\n"
        "Other agents predict your behavior and respond to it (Level-2 reasoning).\n"
        "1. What do your neighbors expect YOU to do, based on your recent actions?\n"
        "2. Given that expectation, what will THEY choose?\n"
        "3. Knowing their anticipated responses, choose your best action."
    ),
}


def build_actions_block(params):
    """Build AVAILABLE ACTIONS section from game params."""
    actions = []
    if params.get("allow_invest_self", True):
        c, r = params["invest_self_cost"], params["invest_self_return"]
        actions.append(f"- invest_self: spend {c}, YOU gain {r} (net +{r-c} for you)")

    c_io, r_io = params["invest_other_cost"], params["invest_other_return"]
    actions.append(f"- invest_other: spend {c_io}, the TARGET gains {r_io} (you gain nothing; this is a gift to another agent)")

    ac = params["arm_cost"]
    am = params["arm_multiplier"]
    ad = params["arm_duration"]
    aoc = params["arm_other_contribution"]
    aod = params["arm_other_duration"]
    actions.append(f"- arm_self: spend {ac}, YOUR combat power x{am} for {ad} rounds")
    actions.append(f"- arm_other: spend {ac}, add {aoc*100:.0f}% of your resources to TARGET's combat power for {aod} rounds (this coalition bonus stacks with their own arming — a supported agent is stronger than one who arms alone)")

    cc = params["conflict_cost"]
    at = params["attack_take_percent"]
    actions.append(f"- attack: both pay {cc}, winner takes {at:.0f}% of loser's resources (loser LOSES those resources)")
    actions.append("- do_nothing: pass this round, no cost")

    return f"""AVAILABLE ACTIONS:
{chr(10).join(actions)}

Combat: win probability = your power / (your power + opponent power).
Power = resources x multiplier (if armed) + coalition support.
You can only perform actions you can afford."""


def build_prompt(scenario, params):
    """Build a full prompt from scenario + params."""
    parts = []
    parts.append(f"You are {scenario['agent_id']}.")
    parts.append("OBJECTIVE: Maximize your absolute resource count.")

    # State
    state_lines = [f"CURRENT STATE (Round {scenario['round']}/{scenario['max_rounds']}):"]
    state_lines.append(f"\nYou can only interact with nearby agents this round.")
    state_lines.append(f"Nearby agents: {', '.join(scenario['neighbors'])}")
    state_lines.append("\nRESOURCES:")
    for aid, res in scenario['resources'].items():
        marker = " (you)" if aid == scenario['agent_id'] else ""
        broke = " [BROKE]" if res <= 0 else ""
        state_lines.append(f"  {aid}: {res:.1f}{marker}{broke}")
    if scenario.get('armed'):
        state_lines.append("\nARMED:")
        for aid, rounds_left in scenario['armed'].items():
            state_lines.append(f"  {aid}: {rounds_left} rounds remaining")
    parts.append("\n".join(state_lines))

    # Neighbor profiles
    if scenario.get('profiles'):
        profile_lines = [f"NEIGHBOR PROFILES (last {scenario.get('history_rounds', 10)} rounds):"]
        for p in scenario['profiles']:
            profile_lines.append(f"  {p}")
        parts.append("\n".join(profile_lines))

    # Actions + reasoning block + JSON
    action_parts = [build_actions_block(params)]
    rb = REASONING_BLOCKS.get(scenario['level'])
    if rb:
        action_parts.append(rb)
    action_parts.append('Respond with valid JSON only:\n{\n  "action": "<action_type>",\n  "target": "<agent_id or null>"\n}')
    parts.append("\n\n".join(action_parts))

    return "\n\n".join(parts)


# Key test scenarios — one per level, diverse situations
TEST_SCENARIOS = [
    {
        "name": "L0 - Early game, equal start",
        "level": "L0",
        "agent_id": "agent_7",
        "round": 2, "max_rounds": 50,
        "neighbors": ["agent_3", "agent_12", "agent_15", "agent_22"],
        "resources": {"agent_7": 25.0, "agent_3": 25.0, "agent_12": 25.0, "agent_15": 25.0, "agent_22": 25.0},
        "armed": {},
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
        "round": 20, "max_rounds": 50,
        "neighbors": ["agent_2", "agent_8", "agent_19", "agent_25"],
        "resources": {"agent_14": 89.0, "agent_2": 31.0, "agent_8": 12.0, "agent_19": 45.0, "agent_25": 5.0},
        "armed": {"agent_14": 2},
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
        "round": 15, "max_rounds": 50,
        "neighbors": ["agent_1", "agent_5", "agent_11", "agent_28"],
        "resources": {"agent_21": 8.0, "agent_1": 120.0, "agent_5": 45.0, "agent_11": 32.0, "agent_28": 15.0},
        "armed": {"agent_1": 3, "agent_5": 1},
        "profiles": [
            "agent_1 [120]: attack | attacked you 2x | you invest other them 1x",
            "agent_5 [45]: arm self | no direct interaction",
            "agent_11 [32]: invest other | invest other you 2x",
            "agent_28 [15]: mixed | no direct interaction",
        ],
    },
    {
        "name": "L3 - Mid game, arms race",
        "level": "L3",
        "agent_id": "agent_15",
        "round": 18, "max_rounds": 50,
        "neighbors": ["agent_1", "agent_8", "agent_22", "agent_27"],
        "resources": {"agent_15": 40.0, "agent_1": 55.0, "agent_8": 42.0, "agent_22": 38.0, "agent_27": 30.0},
        "armed": {"agent_1": 2, "agent_8": 1, "agent_22": 3},
        "profiles": [
            "agent_1 [55]: arm self | arm self 4x | attack 1x",
            "agent_8 [42]: arm self | arm self 3x | no direct interaction",
            "agent_22 [38]: arm self | arm self 5x | attacked you 1x",
            "agent_27 [30]: invest other | invest other you 2x | you invest other them 1x",
        ],
    },
]


def query_openrouter(prompt):
    """Send prompt to OpenRouter and return response with thinking."""
    try:
        resp = requests.post(
            f"{BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 8000,
            },
            timeout=180,
        )
        resp.raise_for_status()
        data = resp.json()
        choice = data["choices"][0]
        message = choice.get("message", {})

        # OpenRouter returns reasoning in reasoning_content for thinking models
        thinking = message.get("reasoning_content", "") or message.get("reasoning", "") or ""
        content = message.get("content", "")
        usage = data.get("usage", {})

        return {
            "thinking": thinking,
            "content": content,
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
        }
    except Exception as e:
        return {"error": str(e), "thinking": "", "content": ""}


def parse_action(content):
    """Try to extract action from response content."""
    try:
        # Try direct JSON parse
        parsed = json.loads(content.strip())
        action = parsed.get("action", "???")
        target = parsed.get("target")
        if target and target != "null":
            return f"{action}->{target}"
        return action
    except:
        pass

    # Try to find JSON in content
    import re
    json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            action = parsed.get("action", "???")
            target = parsed.get("target")
            if target and target != "null":
                return f"{action}->{target}"
            return action
        except:
            pass

    # Last resort: find action name
    for a in ["invest_self", "invest_other", "arm_self", "arm_other", "attack", "do_nothing"]:
        if a in content:
            return a
    return "???"


def main():
    print(f"OpenRouter Test: Qwen3.5-27B")
    print(f"Model: {MODEL}")
    print(f"Scenarios: {len(TEST_SCENARIOS)} × {len(PARAM_SETS)} param sets = {len(TEST_SCENARIOS) * len(PARAM_SETS)} calls")
    print("=" * 100)

    results = []

    for param_name, params in PARAM_SETS.items():
        print(f"\n{'='*100}")
        print(f"PARAM SET: {params['label']}")
        print(f"  invest_self: cost={params['invest_self_cost']}, return={params['invest_self_return']}")
        print(f"  invest_other: cost={params['invest_other_cost']}, return={params['invest_other_return']}")
        print(f"  arm: cost={params['arm_cost']}, conflict_cost={params['conflict_cost']}")
        print(f"{'='*100}")

        for i, scenario in enumerate(TEST_SCENARIOS):
            prompt = build_prompt(scenario, params)
            print(f"\n  [{param_name}] [{i+1}/{len(TEST_SCENARIOS)}] {scenario['name']}")

            t0 = time.time()
            response = query_openrouter(prompt)
            elapsed = time.time() - t0

            action = parse_action(response.get("content", ""))
            think_len = len(response.get("thinking", ""))

            result = {
                "param_set": param_name,
                "scenario": scenario["name"],
                "level": scenario["level"],
                "agent_id": scenario["agent_id"],
                "round": scenario["round"],
                "prompt_length": len(prompt),
                "elapsed_seconds": round(elapsed, 1),
                "action": action,
                **response,
            }
            results.append(result)

            if response.get("error"):
                print(f"    ERROR: {response['error']}")
            else:
                print(f"    Action: {action}")
                print(f"    Think: {think_len} chars | Tokens: {response.get('prompt_tokens', '?')}p + {response.get('completion_tokens', '?')}c | {elapsed:.1f}s")
                # Show first 150 chars of thinking for quality check
                if think_len > 0:
                    think_preview = response["thinking"][:150].replace("\n", " ")
                    print(f"    Think preview: {think_preview}...")

            # Rate limit: be gentle with OpenRouter
            time.sleep(1)

    # Save results
    outfile = "test_openrouter_results.json"
    with open(outfile, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n{'=' * 100}")
    print(f"Results saved to {outfile}")

    # Summary table
    print(f"\n{'Param':<12} {'Scenario':<40} {'Lv':<4} {'Action':<25} {'Think':<8} {'Time':<6}")
    print("-" * 100)
    for r in results:
        if r.get("error"):
            print(f"{r['param_set']:<12} {r['scenario']:<40} {r['level']:<4} {'ERROR':<25}")
        else:
            print(f"{r['param_set']:<12} {r['scenario']:<40} {r['level']:<4} {r['action']:<25} {len(r.get('thinking','')):<8} {r['elapsed_seconds']:<6}")


if __name__ == "__main__":
    main()
