"""
Evaluate whether the NEIGHBOR MEMORY prompt format is clear to Qwen 3.5-27B.

Lightweight diagnostic: sends scenarios with memory-format prompts to Qwen,
captures <think> traces, then has Claude evaluate whether the model correctly
parsed and used the memory information.

NOT optimization — just a clarity audit. Reuses TextGrad infra (vLLM + OpenRouter).

Usage on Snellius:
  1. Start vLLM serving Qwen 3.5-27B
  2. OPENROUTER_API_KEY=sk-or-... python scripts/eval_memory_clarity.py

Locally (if vLLM running):
  VLLM_BASE_URL=http://localhost:8000/v1 \
  OPENROUTER_API_KEY=sk-or-... \
  python scripts/eval_memory_clarity.py
"""

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

from openai import OpenAI

# ── Configuration ──────────────────────────────────────────────────────────

VLLM_BASE_URL = os.environ.get("VLLM_BASE_URL", "http://localhost:8000/v1")
VLLM_MODEL = os.environ.get("VLLM_MODEL", "/scratch-shared/kverlaan/origins_models/Qwen3.5-27B")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
EVAL_MODEL = os.environ.get("EVAL_MODEL", "anthropic/claude-sonnet-4-6")

OUTPUT_DIR = Path(__file__).parent.parent / "data"

# ── Game parameters (match production config) ─────────────────────────────

GAME_PARAMS = {
    "invest_self_cost_pct": 10, "invest_self_return_pct": 20,
    "invest_other_cost_pct": 10, "invest_other_return_pct": 15,
    "arm_cost_pct": 10, "arm_other_cost_pct": 10, "arm_decay": 0.5,
    "attack_take_pct": 40, "conflict_cost_pct": 5,
}

# ── Prompt components (from prompts.py) ───────────────────────────────────

OBJECTIVE = "OBJECTIVE: Maximize your absolute resource count."

_iot = GAME_PARAMS["invest_other_return_pct"]

ACTIONS_AND_COMBAT = f"""Choose exactly ONE action this round.

AVAILABLE ACTIONS:
- invest_other: spend {GAME_PARAMS['invest_other_cost_pct']}% of your resources, TARGET gains {_iot:.0f}% of your resources (grows the total economy)
- arm_self: spend {GAME_PARAMS['arm_cost_pct']}% of your resources (removed from economy), adds that amount to your combat strength. Your total combat strength = resources + arm bonus.
- arm_other: spend {GAME_PARAMS['arm_other_cost_pct']}% of your resources (removed from economy), adds that amount to TARGET's combat strength. TARGET's resource count does NOT increase — only their fighting power.
- attack: you pay {GAME_PARAMS['conflict_cost_pct']}% of your resources, opponent pays {GAME_PARAMS['conflict_cost_pct']}% of theirs. Winner takes {GAME_PARAMS['attack_take_pct']}% of loser's remaining resources. Loser keeps the rest.
- do_nothing: no cost, no effect

COMBAT RULES:
- Combat strength = your resources + your arm bonus (agents not listed under ARM BONUSES have arm bonus = 0)
- arm_self adds {GAME_PARAMS['arm_cost_pct']}% of your resources to your arm bonus
- arm_other adds {GAME_PARAMS['arm_other_cost_pct']}% of your resources to TARGET's arm bonus
- All arm bonuses decay at the END of each round: they halve (x{GAME_PARAMS['arm_decay']})
- Win probability = your_strength / (your_strength + opponent_strength)
- Attack expected value = win_prob x {GAME_PARAMS['attack_take_pct']}% x opponent_resources - lose_prob x {GAME_PARAMS['attack_take_pct']}% x your_resources - {GAME_PARAMS['conflict_cost_pct']}% x your_resources"""

REASONING_BLOCKS = {
    "L1": (
        "THINK BEFORE CHOOSING:\n"
        "Assume other agents pick actions without strategic calculation.\n"
        "For each available action, compute its expected resource change:\n"
        "- invest_other/do_nothing: use the costs and returns listed above.\n"
        "- arm_self: cost now vs combat advantage later (only useful if you expect to attack or be attacked).\n"
        "- attack: expected gain = win_probability x take% x opponent_resources, minus conflict_cost.\n"
        "  Include your arm bonus when computing win probability (combat strength = resources + arm bonus).\n"
        "Compare these values and choose the action with the highest expected payoff.\n"
        "Do NOT predict what specific neighbors will do — treat their actions as unknown."
    ),
    "L2": (
        "THINK BEFORE CHOOSING:\n"
        "Assume other agents pick their individually best action given the current state.\n"
        "1. For each neighbor, predict their most likely action based on:\n"
        "   - Their history (shown in NEIGHBOR MEMORY)\n"
        "   - Their current resources and armed status\n"
        "   - What action would give THEM the best payoff right now\n"
        "2. Given these predictions, choose your best response.\n"
        "Do NOT reason about what neighbors think about YOU — only predict what they will do."
    ),
    "L3": (
        "THINK BEFORE CHOOSING:\n"
        "Assume other agents look at YOUR recent actions to predict what you will do, "
        "then pick their best response to that prediction.\n"
        "1. Look at your own recent actions in YOUR RECENT ACTIONS. "
        "List your recent actions — what pattern do your neighbors see? What action would they predict you take this round?\n"
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
target must be null (not the string "null") when no target is needed.
Do not include any text outside the JSON."""

# ── Memory-format scenarios ───────────────────────────────────────────────
# Each scenario tests a different memory pattern the model needs to parse.

SCENARIOS = [
    {
        "name": "Cooperative history — does model use reciprocity info?",
        "level": "L1",
        "agent_id": "agent_7",
        "round": 15,
        "neighbors": ["agent_3", "agent_12", "agent_15"],
        "resources": {"agent_7": 45.0, "agent_3": 52.0, "agent_12": 38.0, "agent_15": 41.0},
        "arm_bonuses": {},
        "own_history": (
            "YOUR RECENT ACTIONS:\n"
            "  Round 10: invest_other -> agent_3 (+3.8)\n"
            "  Round 11: invest_other -> agent_12 (+2.1)\n"
            "  Round 12: invest_other -> agent_3 (+4.2)\n"
            "  Round 13: do_nothing\n"
            "  Round 14: invest_other -> agent_15 (+3.5)"
        ),
        "neighbor_memory": (
            "NEIGHBOR MEMORY:\n"
            "  agent_3 [52, seen 12/14 rounds]: invest other you 5x | you invest other them 3x | observed: invest other 8x\n"
            "  agent_12 [38, seen 10/14 rounds]: invest other you 2x | you invest other them 1x | observed: invest other 4x, arm self 2x\n"
            "  agent_15 [41, seen 8/14 rounds]: no interaction with you | observed: invest other 5x, do nothing 3x"
        ),
        "test_focus": "Does model reference reciprocal investment history with agent_3?",
    },
    {
        "name": "Stale neighbor — does model handle 'last seen' correctly?",
        "level": "L2",
        "agent_id": "agent_14",
        "round": 25,
        "neighbors": ["agent_2", "agent_19"],
        "resources": {"agent_14": 60.0, "agent_2": 35.0, "agent_19": 48.0},
        "arm_bonuses": {"agent_19": 4.8},
        "own_history": (
            "YOUR RECENT ACTIONS:\n"
            "  Round 20: invest_other -> agent_8 (+5.2)\n"
            "  Round 21: arm_self (-6.0)\n"
            "  Round 22: attack -> agent_8 (won, +12.4)\n"
            "  Round 23: invest_other -> agent_2 (+3.1)\n"
            "  Round 24: do_nothing"
        ),
        "neighbor_memory": (
            "NEIGHBOR MEMORY:\n"
            "  agent_2 [35, seen 8/24 rounds]: invest other you 1x | you invest other them 1x | observed: invest other 3x\n"
            "  agent_19 [48, seen 15/24 rounds]: no interaction with you | observed: arm self 6x, attack 3x\n"
            "  agent_8 [?, seen 0/24 rounds, last seen round 22]: you attack them 1x | you invest other them 1x"
        ),
        "test_focus": "Does model treat agent_8 (stale, '?') differently from current neighbors? Does it not try to interact with agent_8?",
    },
    {
        "name": "Threat detection — incoming attacks in memory",
        "level": "L2",
        "agent_id": "agent_21",
        "round": 18,
        "neighbors": ["agent_1", "agent_5", "agent_11"],
        "resources": {"agent_21": 22.0, "agent_1": 95.0, "agent_5": 40.0, "agent_11": 30.0},
        "arm_bonuses": {"agent_1": 9.5},
        "own_history": (
            "YOUR RECENT ACTIONS:\n"
            "  Round 13: invest_other -> agent_11 (+2.0)\n"
            "  Round 14: invest_other -> agent_5 (+2.5)\n"
            "  Round 15: arm_self (-2.2)\n"
            "  Round 16: arm_self (-2.0)\n"
            "  Round 17: do_nothing"
        ),
        "neighbor_memory": (
            "NEIGHBOR MEMORY:\n"
            "  agent_1 [95, seen 14/17 rounds]: attack you 3x | observed: attack 5x, arm self 4x\n"
            "  agent_5 [40, seen 10/17 rounds]: invest other you 2x | you invest other them 1x | observed: invest other 3x\n"
            "  agent_11 [30, seen 12/17 rounds]: invest other you 4x | you invest other them 1x | observed: invest other 7x"
        ),
        "test_focus": "Does model identify agent_1 as threat based on 'attack you 3x' + high resources + arm bonus?",
    },
    {
        "name": "L3 recursive — does model use OWN history for prediction?",
        "level": "L3",
        "agent_id": "agent_9",
        "round": 30,
        "neighbors": ["agent_3", "agent_16"],
        "resources": {"agent_9": 55.0, "agent_3": 120.0, "agent_16": 28.0},
        "arm_bonuses": {"agent_3": 12.0},
        "own_history": (
            "YOUR RECENT ACTIONS:\n"
            "  Round 25: invest_other -> agent_16 (+2.8)\n"
            "  Round 26: invest_other -> agent_16 (+3.0)\n"
            "  Round 27: invest_other -> agent_3 (+5.5)\n"
            "  Round 28: invest_other -> agent_16 (+2.6)\n"
            "  Round 29: invest_other -> agent_3 (+5.8)"
        ),
        "neighbor_memory": (
            "NEIGHBOR MEMORY:\n"
            "  agent_3 [120, seen 20/29 rounds]: invest other you 8x | you invest other them 4x | observed: attack 3x, invest other 5x, arm self 4x\n"
            "  agent_16 [28, seen 18/29 rounds]: invest other you 6x | you invest other them 5x | observed: invest other 10x"
        ),
        "test_focus": "Does L3 model reference its own cooperative history and predict neighbors will expect cooperation?",
    },
    {
        "name": "Unknown neighbor — '?' resources, never seen",
        "level": "L1",
        "agent_id": "agent_18",
        "round": 12,
        "neighbors": ["agent_6", "agent_10", "agent_25"],
        "resources": {"agent_18": 30.0, "agent_6": 42.0, "agent_10": 28.0, "agent_25": 35.0},
        "arm_bonuses": {},
        "own_history": (
            "YOUR RECENT ACTIONS:\n"
            "  Round 8: invest_other -> agent_6 (+3.0)\n"
            "  Round 9: do_nothing\n"
            "  Round 10: invest_other -> agent_10 (+2.5)\n"
            "  Round 11: do_nothing"
        ),
        "neighbor_memory": (
            "NEIGHBOR MEMORY:\n"
            "  agent_6 [42, seen 8/11 rounds]: invest other you 3x | you invest other them 1x | observed: invest other 5x\n"
            "  agent_10 [28, seen 6/11 rounds]: no interaction with you | observed: arm self 2x, do nothing 3x\n"
            "  agent_25 [?, seen 0/11 rounds]: attack you 1x"
        ),
        "test_focus": "Does model handle agent_25 with '?' resources correctly? Notes that attack came from outside radius?",
    },
    {
        "name": "Mixed signals — cooperative AND aggressive neighbor",
        "level": "L2",
        "agent_id": "agent_12",
        "round": 35,
        "neighbors": ["agent_5", "agent_19", "agent_24"],
        "resources": {"agent_12": 72.0, "agent_5": 88.0, "agent_19": 30.0, "agent_24": 15.0},
        "arm_bonuses": {"agent_5": 4.4},
        "own_history": (
            "YOUR RECENT ACTIONS:\n"
            "  Round 30: invest_other -> agent_19 (+3.5)\n"
            "  Round 31: invest_other -> agent_5 (+7.0)\n"
            "  Round 32: arm_self (-7.2)\n"
            "  Round 33: invest_other -> agent_19 (+3.2)\n"
            "  Round 34: do_nothing"
        ),
        "neighbor_memory": (
            "NEIGHBOR MEMORY:\n"
            "  agent_5 [88, seen 25/34 rounds]: invest other you 6x | attack you 2x | you invest other them 3x | observed: attack 4x, invest other 5x, arm self 6x\n"
            "  agent_19 [30, seen 20/34 rounds]: invest other you 8x | you invest other them 4x | observed: invest other 12x\n"
            "  agent_24 [15, seen 5/34 rounds, last seen round 30]: no interaction with you | observed: do nothing 4x"
        ),
        "test_focus": "Does model note agent_5's mixed behavior (invested 6x BUT attacked 2x)? Does it factor in both?",
    },
]

# ── Memory clarity evaluation rubric ──────────────────────────────────────

MEMORY_EVAL_RUBRIC = """You are evaluating whether a game-playing AI correctly PARSED AND USED memory information from its prompt.

The agent received a prompt containing two memory sections:
1. YOUR RECENT ACTIONS — the agent's own action history (last N rounds)
2. NEIGHBOR MEMORY — accumulated observations about each neighbor, formatted as:
   agent_id [resources, seen X/Y rounds]: interaction summary | observed actions

The agent then produced <think> reasoning followed by a JSON action choice.

Evaluate the following aspects by examining the <think> trace:

## A. OWN HISTORY COMPREHENSION (0-10)
- Did the model reference or acknowledge its own recent actions?
- Did it correctly interpret action outcomes (won/lost, resource changes)?
- Did it use its own history to inform its choice (e.g., continuing a pattern, or deliberately changing)?

## B. NEIGHBOR MEMORY PARSING (0-10)
- Did the model correctly distinguish:
  - Actions BY neighbors TOWARD the agent ("invest other you 3x", "attack you 2x")
  - Actions BY the agent TOWARD neighbors ("you invest other them 2x")
  - Third-party observed actions ("observed: arm self 4x, attack 2x")
- Did it use the "seen X/Y rounds" information appropriately?
- For stale entries (with "last seen round X"): did it note the information is outdated?
- For "?" resources: did it acknowledge uncertainty rather than assuming a value?

## C. STRATEGIC USE OF MEMORY (0-10)
- Did the model use memory to inform its strategy (not just acknowledge it)?
- Examples of good use: identifying threats from attack history, reciprocating cooperative neighbors, being cautious about armed/aggressive agents
- Did the model confuse or conflate different neighbors' histories?

## D. VALID OUTPUT (0-10)
- Is the JSON output valid with "action" and "target" fields?
- Does the chosen target make sense given the available neighbors?
- Did the model NOT try to target agents outside its current neighbor list?

Provide:
1. Scores for A, B, C, D (each 0-10)
2. Overall score (average of A-D)
3. SPECIFIC QUOTES from the <think> trace showing correct or incorrect memory use
4. List any CONFUSION POINTS where the memory format caused misunderstanding
5. Actionable suggestions for improving the memory format if needed

IMPORTANT: Focus on whether the MEMORY FORMAT is clear and parseable, not whether the strategic choice is optimal."""

# ── Helper functions ──────────────────────────────────────────────────────


def extract_thinking(response_text: str) -> str:
    """Extract content between <think> tags (fallback for non-parser mode)."""
    matches = re.findall(r'<think>(.*?)</think>', response_text, re.DOTALL)
    return "\n".join(matches).strip() if matches else ""


def get_thinking_from_response(response) -> str:
    """Get thinking content from vLLM response.

    With --reasoning-parser qwen3, vLLM puts thinking in a 'reasoning' field
    on the message dict. The OpenAI Python client doesn't expose this as a
    typed attribute, so we access it via model_extra or the raw dict.
    """
    choice = response.choices[0]
    msg = choice.message

    # vLLM uses "reasoning" field (accessible via model_extra on pydantic model)
    if hasattr(msg, 'model_extra') and msg.model_extra:
        reasoning = msg.model_extra.get('reasoning', None)
        if reasoning:
            return reasoning.strip()

    # Also try as direct attribute (some client versions)
    for field in ('reasoning', 'reasoning_content'):
        val = getattr(msg, field, None)
        if val:
            return val.strip()

    # Fallback: extract <think> tags from content
    content = msg.content or ""
    return extract_thinking(content)


def extract_json(response_text: str):
    """Extract JSON from response (after </think> tag)."""
    # Try after </think>
    after_think = re.split(r'</think>', response_text, maxsplit=1)
    text = after_think[-1].strip() if len(after_think) > 1 else response_text
    # Find JSON
    match = re.search(r'\{[^{}]*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return None
    return None


def build_memory_prompt(scenario: dict) -> str:
    """Build a full game prompt with memory sections."""
    parts = []

    # Identity
    parts.append(f"You are {scenario['agent_id']}.")

    # Objective
    parts.append(OBJECTIVE)

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

    # Memory sections (the key difference from TextGrad scenarios)
    parts.append(scenario["own_history"])
    parts.append(scenario["neighbor_memory"])

    # Actions + reasoning + JSON
    level = scenario["level"]
    action_parts = [ACTIONS_AND_COMBAT]
    if level in REASONING_BLOCKS:
        action_parts.append(REASONING_BLOCKS[level])
    action_parts.append(JSON_TEMPLATE)
    parts.append("\n\n".join(action_parts))

    return "\n\n".join(parts)


# ── Main evaluation ──────────────────────────────────────────────────────


def run_eval():
    """Run all scenarios through Qwen, then evaluate with Claude."""
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY environment variable required")

    # Qwen on vLLM
    vllm_client = OpenAI(base_url=VLLM_BASE_URL, api_key="none")

    # Claude on OpenRouter
    eval_client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

    print("=" * 70)
    print("Memory Clarity Evaluation")
    print(f"Forward model: {VLLM_MODEL} at {VLLM_BASE_URL}")
    print(f"Evaluator: {EVAL_MODEL} via OpenRouter")
    print(f"Scenarios: {len(SCENARIOS)}")
    print("=" * 70)

    results = []

    for i, scenario in enumerate(SCENARIOS):
        print(f"\n{'─' * 60}")
        print(f"[{i+1}/{len(SCENARIOS)}] {scenario['name']}")
        print(f"  Level: {scenario['level']} | Agent: {scenario['agent_id']} | Round: {scenario['round']}")
        print(f"  Test focus: {scenario['test_focus']}")
        print(f"{'─' * 60}")

        # Build prompt
        prompt = build_memory_prompt(scenario)

        # Forward pass: Qwen
        t0 = time.time()
        try:
            response = vllm_client.chat.completions.create(
                model=VLLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=8000,
                temperature=0.7,
            )
            msg = response.choices[0].message
            response_text = msg.content or ""
            thinking = get_thinking_from_response(response)
            # Debug: print all message fields to find where thinking goes
            if i == 0:
                print(f"  DEBUG message fields: {[k for k in dir(msg) if not k.startswith('_')]}")
                print(f"  DEBUG content length: {len(response_text)}")
                print(f"  DEBUG content[:200]: {response_text[:200]}")
                # Check for extra fields via model_extra or raw dict
                if hasattr(msg, 'model_extra') and msg.model_extra:
                    print(f"  DEBUG model_extra keys: {list(msg.model_extra.keys())}")
                    for k, v in msg.model_extra.items():
                        vstr = str(v)[:200] if v else "None"
                        print(f"  DEBUG   {k}: {vstr}")
        except Exception as e:
            print(f"  ERROR (vLLM): {e}")
            results.append({"scenario": scenario["name"], "error": str(e)})
            continue
        forward_time = time.time() - t0

        action_json = extract_json(response_text)

        print(f"  Forward pass: {forward_time:.1f}s")
        print(f"  Thinking: {len(thinking)} chars")
        print(f"  Action: {json.dumps(action_json) if action_json else 'PARSE FAILED'}")

        # Print first 500 chars of thinking for quick review
        if thinking:
            preview = thinking[:500].replace('\n', '\n    ')
            print(f"  Think preview:\n    {preview}...")

        # Eval pass: Claude
        # Combine thinking + content for eval (thinking is in separate field)
        full_response = ""
        if thinking:
            full_response = f"<think>\n{thinking}\n</think>\n\n{response_text}"
        else:
            full_response = response_text

        eval_prompt = (
            f"## Scenario: {scenario['name']}\n"
            f"## Test focus: {scenario['test_focus']}\n\n"
            f"## PROMPT SENT TO MODEL:\n```\n{prompt}\n```\n\n"
            f"## MODEL RESPONSE:\n```\n{full_response}\n```\n\n"
            f"Please evaluate according to the rubric."
        )

        t0 = time.time()
        try:
            eval_response = eval_client.chat.completions.create(
                model=EVAL_MODEL,
                messages=[
                    {"role": "system", "content": MEMORY_EVAL_RUBRIC},
                    {"role": "user", "content": eval_prompt},
                ],
                max_tokens=2000,
                temperature=0.0,
            )
            eval_text = eval_response.choices[0].message.content
        except Exception as e:
            print(f"  ERROR (eval): {e}")
            eval_text = f"EVAL ERROR: {e}"
        eval_time = time.time() - t0

        print(f"  Eval pass: {eval_time:.1f}s")

        # Extract scores from eval (look for X/10 patterns)
        scores = {}
        for label in ["A", "B", "C", "D"]:
            match = re.search(rf'{label}[^:]*:\s*(\d+)/10', eval_text)
            if match:
                scores[label] = int(match.group(1))
        overall_match = re.search(r'[Oo]verall[^:]*:\s*(\d+(?:\.\d+)?)/10', eval_text)
        if overall_match:
            scores["overall"] = float(overall_match.group(1))
        elif scores:
            scores["overall"] = sum(scores.values()) / len(scores)

        if scores:
            print(f"  Scores: {scores}")

        results.append({
            "scenario": scenario["name"],
            "level": scenario["level"],
            "test_focus": scenario["test_focus"],
            "prompt": prompt,
            "response": response_text,
            "thinking": thinking,
            "thinking_chars": len(thinking),
            "action": action_json,
            "eval_text": eval_text,
            "scores": scores,
            "forward_time_s": round(forward_time, 1),
            "eval_time_s": round(eval_time, 1),
        })

    # Summary
    print(f"\n\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")

    all_scores = {"A": [], "B": [], "C": [], "D": [], "overall": []}
    for r in results:
        if "error" in r:
            continue
        for k, v in r.get("scores", {}).items():
            if k in all_scores:
                all_scores[k].append(v)

    for k in ["A", "B", "C", "D", "overall"]:
        vals = all_scores[k]
        if vals:
            avg = sum(vals) / len(vals)
            label = {
                "A": "Own History Comprehension",
                "B": "Neighbor Memory Parsing",
                "C": "Strategic Use of Memory",
                "D": "Valid Output",
                "overall": "OVERALL",
            }[k]
            print(f"  {k}. {label}: {avg:.1f}/10 (n={len(vals)}, range={min(vals)}-{max(vals)})")

    # Identify worst-performing scenarios
    scored = [(r["scenario"], r["scores"].get("overall", 0)) for r in results if r.get("scores")]
    scored.sort(key=lambda x: x[1])
    if scored:
        print(f"\n  Lowest scoring: {scored[0][0]} ({scored[0][1]}/10)")
        print(f"  Highest scoring: {scored[-1][0]} ({scored[-1][1]}/10)")

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outfile = OUTPUT_DIR / "memory_clarity_eval.json"
    output = {
        "results": results,
        "summary": {k: {"mean": sum(v)/len(v) if v else 0, "values": v} for k, v in all_scores.items()},
        "config": {
            "forward_model": VLLM_MODEL,
            "eval_model": EVAL_MODEL,
            "vllm_url": VLLM_BASE_URL,
            "n_scenarios": len(SCENARIOS),
            "timestamp": datetime.now().isoformat(),
        },
    }
    with open(outfile, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to {outfile}")

    # Print full eval texts for manual review
    print(f"\n\n{'=' * 70}")
    print("DETAILED EVALUATIONS")
    print(f"{'=' * 70}")
    for r in results:
        if "error" in r:
            continue
        print(f"\n{'─' * 60}")
        print(f"{r['scenario']} [{r['level']}] — Scores: {r.get('scores', {})}")
        print(f"{'─' * 60}")
        print(r.get("eval_text", "No evaluation"))


if __name__ == "__main__":
    run_eval()
