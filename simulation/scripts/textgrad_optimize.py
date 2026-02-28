"""
TextGrad prompt optimization for K-level reasoning prompts.

FOCUS: Instruction clarity — NOT reasoning depth.
The evaluator judges whether the prompt instructions are clear and unambiguous,
so the model knows exactly what is being asked. This removes noise from prompts
without creating a confound (we do NOT optimize for "correct" reasoning output).

Two-stage optimization:
  Stage 1: Optimize shared base prompt (objective, action descriptions, constraints)
           → Are game mechanics clear? Can the model parse actions/costs correctly?
  Stage 2: Optimize per-level reasoning blocks (L0-L3)
           → Is the reasoning instruction unambiguous? Does the model understand
             what kind of thinking is expected (not whether it does it "correctly")?

Uses Qwen 3.5-27B (vLLM) as forward model, Claude (OpenRouter) as evaluator.

Usage on Snellius:
  1. Start vLLM serving Qwen 3.5-27B
  2. OPENROUTER_API_KEY=sk-or-... python scripts/textgrad_optimize.py

Locally (if vLLM running):
  VLLM_BASE_URL=http://localhost:8000/v1 \
  OPENROUTER_API_KEY=sk-or-... \
  python scripts/textgrad_optimize.py
"""

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

import textgrad as tg
from openai import OpenAI
from textgrad.engine.local_model_openai_api import ChatExternalClient

# ── Configuration ──────────────────────────────────────────────────────────

VLLM_BASE_URL = os.environ.get("VLLM_BASE_URL", "http://localhost:8000/v1")
VLLM_MODEL = os.environ.get("VLLM_MODEL", "/scratch-shared/kverlaan/origins_models/Qwen3.5-27B")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
EVAL_MODEL = os.environ.get("EVAL_MODEL", "anthropic/claude-sonnet-4-6")

EPOCHS = 3  # TextGrad tutorial default
OUTPUT_DIR = Path(__file__).parent.parent / "data"

# ── Game parameters (%-based economy, match production config) ────────────

GAME_PARAMS = {
    "invest_self_cost_pct": 10, "invest_self_return_pct": 20,
    "invest_other_cost_pct": 10, "invest_other_return_mult": 1.5,
    "arm_cost_pct": 10, "arm_other_cost_pct": 10, "arm_decay": 0.5,
    "attack_take_pct": 40, "conflict_cost_pct": 5,
}

# ── Current prompt components ─────────────────────────────────────────────

_iot = GAME_PARAMS["invest_other_cost_pct"] * GAME_PARAMS["invest_other_return_mult"]

CURRENT_BASE_PROMPT = f"""Choose exactly ONE action this round.

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

CURRENT_OBJECTIVE = "OBJECTIVE: Maximize your absolute resource count."

# Current reasoning blocks (from prompts.py)
REASONING_BLOCKS = {
    "L0": "",  # No reasoning instruction — thinking disabled at model level
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

# ── Test scenarios (same as test_qwen35.py) ───────────────────────────────

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
        "arm_bonuses": {"agent_14": 5.0},
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
        "arm_bonuses": {"agent_1": 12.0, "agent_5": 2.3},
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
        "arm_bonuses": {"agent_3": 47.0},
        "profiles": [
            "agent_3 [310]: attack | attacked you 1x | invest other you 3x",
            "agent_16 [18]: invest other | invest other you 4x | you invest other them 3x",
            "agent_20 [7 BROKE]: do nothing | no direct interaction",
        ],
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
        "arm_bonuses": {"agent_2": 3.8},
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
        "arm_bonuses": {"agent_1": 2.8, "agent_8": 2.1, "agent_22": 3.8},
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
        "arm_bonuses": {"agent_5": 9.0},
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

# ── Evaluation rubrics ────────────────────────────────────────────────────

# ── Evaluation rubrics: INSTRUCTION CLARITY (not reasoning depth) ─────
# The evaluator diagnoses whether the PROMPT is clear, not whether the
# model's reasoning is at the "right" depth. This avoids the confound
# of optimizing for specific reasoning output.

BASE_EVAL_RUBRIC = """You are evaluating the CLARITY of a game prompt's instructions.
The model received a prompt with game mechanics (actions, costs, combat) and produced
a response containing internal reasoning in <think> blocks followed by a JSON action.

Judge the PROMPT's clarity by looking at the model's response for confusion signals:
1. Did the model misunderstand any action mechanic (e.g., wrong cost, wrong target type)?
2. Did the model seem confused about what actions are available or how they work?
3. Did the model correctly parse numeric parameters (costs, percentages, durations)?
4. Is the JSON output valid with "action" and "target" fields?
5. Did the model reference game state that was actually provided (not hallucinated)?

Score 1-10 for how CLEAR the instructions were (10 = model showed no confusion about mechanics).
Provide specific feedback: which parts of the prompt caused confusion or could be clearer?
Do NOT judge whether the chosen action is strategically optimal — only whether the model
understood the rules and options correctly."""

LEVEL_EVAL_RUBRICS = {
    "L0": """You are evaluating the CLARITY of a reasoning instruction given to a game agent.
The instruction told this agent to be REACTIVE (Level-0 — no deliberation).

Judge whether the INSTRUCTION was clear and unambiguous by examining the response:
1. Did the model understand what "reactive" / "no deliberation" means in this context?
2. Are there signs the model was confused about what was expected of it?
3. Did the instruction clearly communicate the desired behavior, or was it vague?
4. If the model deliberated anyway, is that because the instruction was unclear (prompt issue)
   or because the model chose to ignore a clear instruction (model issue)?

Score 1-10 for INSTRUCTION CLARITY (10 = perfectly clear what behavior is expected).
Suggest specific wording improvements to make the instruction less ambiguous.
Do NOT score based on whether the model actually behaved reactively — only whether
the instruction clearly communicated what was expected.""",

    "L1": """You are evaluating the CLARITY of a reasoning instruction given to a game agent.
The instruction told this agent to CALCULATE EXPECTED VALUES (Level-1 — strategic calculation).

Judge whether the INSTRUCTION was clear and unambiguous by examining the response:
1. Did the model understand what "expected value calculation" means in this game context?
2. Was it clear which calculations the model should perform (and which it should NOT)?
3. Did the instruction clearly distinguish L1 (calculate your own best action) from
   L2 (also predict what neighbors will do)? Or was this boundary ambiguous?
4. Are there signs the model was confused about the scope of analysis expected?

Score 1-10 for INSTRUCTION CLARITY (10 = perfectly clear what reasoning scope is expected).
Suggest specific wording improvements to make the instruction less ambiguous.
Do NOT score based on whether the model's calculations were correct or optimal.""",

    "L2": """You are evaluating the CLARITY of a reasoning instruction given to a game agent.
The instruction told this agent to do OPPONENT MODELING (Level-2 — predict neighbor actions).

Judge whether the INSTRUCTION was clear and unambiguous by examining the response:
1. Did the model understand what "opponent modeling" means in this context?
2. Was it clear the model should predict specific neighbors' actions (not abstract others)?
3. Did the instruction clearly distinguish L2 (predict what neighbors do) from
   L3 (predict what neighbors think YOU will do)? Or was this boundary ambiguous?
4. Were the step-by-step instructions (predict → best response) clear?

Score 1-10 for INSTRUCTION CLARITY (10 = perfectly clear what reasoning process is expected).
Suggest specific wording improvements to make the instruction less ambiguous.
Do NOT score based on whether the model's predictions were accurate.""",

    "L3": """You are evaluating the CLARITY of a reasoning instruction given to a game agent.
The instruction told this agent to do RECURSIVE REASONING (Level-3 — they predict you, you respond).

Judge whether the INSTRUCTION was clear and unambiguous by examining the response:
1. Did the model understand the recursive structure (your history → their prediction of you
   → their action → your best response)?
2. Was the 3-step process (examine own history → predict their prediction → choose best action)
   clearly communicated?
3. Did the instruction clearly explain what "Level-2 reasoning by neighbors" means?
4. Are there signs the model was confused about the recursive logic, or did it simply
   not go deep enough despite understanding the instruction?

Score 1-10 for INSTRUCTION CLARITY (10 = perfectly clear what recursive process is expected).
Suggest specific wording improvements to make the instruction less ambiguous.
Do NOT score based on whether the model achieved true recursive depth.""",
}

# ── Helper functions ──────────────────────────────────────────────────────


def extract_thinking(response_text: str) -> str:
    """Extract content between <think> tags from reasoning model output."""
    matches = re.findall(r'<think>(.*?)</think>', response_text, re.DOTALL)
    return "\n".join(matches).strip() if matches else ""


def build_game_prompt(scenario: dict, objective: str = None,
                      base_actions: str = None, reasoning_block: str = None) -> str:
    """Build a full game prompt from scenario + optimizable components."""
    parts = []

    # Identity
    parts.append(f"You are {scenario['agent_id']}.")

    # Objective (optimizable in stage 1)
    parts.append(objective or CURRENT_OBJECTIVE)

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

    # Actions (optimizable in stage 1)
    action_parts = [base_actions or CURRENT_BASE_PROMPT]

    # Reasoning block (optimizable in stage 2)
    if reasoning_block:
        action_parts.append(reasoning_block)

    action_parts.append(JSON_TEMPLATE)
    parts.append("\n\n".join(action_parts))

    return "\n\n".join(parts)


# ── Main optimization ─────────────────────────────────────────────────────


def setup_engines():
    """Create vLLM (forward) and OpenRouter (evaluator) engines."""
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY environment variable required")

    # Qwen on vLLM
    vllm_client = OpenAI(base_url=VLLM_BASE_URL, api_key="none")
    vllm_engine = ChatExternalClient(
        client=vllm_client, model_string=VLLM_MODEL
    )

    # Claude on OpenRouter
    or_client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY
    )
    eval_engine = ChatExternalClient(
        client=or_client, model_string=EVAL_MODEL
    )

    return vllm_engine, eval_engine


def run_stage1(vllm_engine, eval_engine):
    """Stage 1: Optimize shared base prompt for CLARITY of game mechanics.

    Focus: Are action descriptions, costs, and combat mechanics clear enough
    that the model doesn't misinterpret any game rule?

    Uses base_var as system prompt in BlackboxLLM so TextGrad gradients flow:
    loss → response → base_var (system prompt).
    """
    print("\n" + "=" * 70)
    print("STAGE 1: Base Prompt Optimization")
    print("=" * 70)

    tg.set_backward_engine(eval_engine, override=True)

    # Combine objective + actions as one optimizable block
    current_text = f"{CURRENT_OBJECTIVE}\n\n{CURRENT_BASE_PROMPT}"

    base_var = tg.Variable(
        current_text,
        requires_grad=True,
        role_description=(
            "Shared instructional text for a game-playing agent. "
            "Contains the objective and available action descriptions with costs/mechanics. "
            "Must preserve all action names (invest_other, arm_self, arm_other, attack, do_nothing) "
            "and their numeric parameters exactly."
        )
    )

    # base_var as system prompt → gradient flows back through it
    model = tg.BlackboxLLM(vllm_engine, base_var)
    loss_fn = tg.TextLoss(eval_system_prompt=BASE_EVAL_RUBRIC, engine=eval_engine)
    optimizer = tg.TGD(parameters=[base_var])

    trace_log = []  # Full trace for thesis reproducibility

    for epoch in range(EPOCHS):
        print(f"\n--- Epoch {epoch + 1}/{EPOCHS} ---")

        for i, scenario in enumerate(SCENARIOS):
            optimizer.zero_grad()

            prompt_before = base_var.value  # Snapshot before step

            # Game state + reasoning block as the user message (not optimized)
            prompt = build_game_prompt(
                scenario,
                objective="",  # objective is in base_var (system prompt)
                base_actions="",  # actions are in base_var (system prompt)
                reasoning_block=REASONING_BLOCKS.get(scenario["level"], "")
            )
            question = tg.Variable(prompt, requires_grad=False, role_description="game state and context")

            t0 = time.time()
            response = model(question)
            elapsed = time.time() - t0

            loss = loss_fn(response)
            loss.backward()

            # Capture gradient (textual critique) before optimizer clears it
            gradient_text = ""
            if hasattr(base_var, 'gradients') and base_var.gradients:
                grad = next(iter(base_var.gradients))  # gradients is a set
                gradient_text = str(grad.value) if hasattr(grad, 'value') else str(grad)
            elif hasattr(base_var, 'get_gradient_text'):
                gradient_text = base_var.get_gradient_text()

            optimizer.step()

            trace_log.append({
                "stage": "base_prompt",
                "epoch": epoch + 1,
                "scenario": scenario["name"],
                "level": scenario["level"],
                "prompt_before": prompt_before,
                "prompt_after": base_var.value,
                "response": response.value[:2000] if hasattr(response, 'value') else "",
                "eval_score": loss.value[:500] if hasattr(loss, 'value') else str(loss)[:500],
                "gradient": gradient_text[:1000],
                "elapsed_s": round(elapsed, 1),
            })

            print(f"  [{i+1}/{len(SCENARIOS)}] {scenario['name']} ({elapsed:.1f}s)")
            if gradient_text:
                print(f"    Gradient: {gradient_text[:120]}...")

    print("\nFinal base prompt:")
    print(base_var.value[:500])

    return {
        "original": current_text,
        "optimized": base_var.value,
        "trace": trace_log,
    }


def run_stage2(vllm_engine, eval_engine):
    """Stage 2: Optimize per-level reasoning blocks for INSTRUCTION CLARITY.

    Focus: Is each level's reasoning instruction clear and unambiguous?
    Can the model understand what kind of thinking is expected?
    We do NOT optimize for "correct" reasoning output (that would be a confound).

    Key design: reasoning_var is the system prompt → gradient flows:
    loss → response → reasoning_var.

    vLLM runs WITHOUT --reasoning-parser, so <think> tags stay in the
    content field. The eval rubric examines whether the model showed
    confusion about what was asked, NOT whether it reasoned at the right depth.
    """
    print("\n" + "=" * 70)
    print("STAGE 2: Per-Level Reasoning Block Optimization")
    print("=" * 70)

    tg.set_backward_engine(eval_engine, override=True)

    results = {}

    for level in ["L0", "L1", "L2", "L3"]:
        level_scenarios = [s for s in SCENARIOS if s["level"] == level]
        if not level_scenarios:
            print(f"\n  No scenarios for {level}, skipping")
            continue

        print(f"\n{'─' * 50}")
        print(f"Optimizing {level} ({len(level_scenarios)} scenarios)")
        print(f"{'─' * 50}")

        current_block = REASONING_BLOCKS[level]

        reasoning_var = tg.Variable(
            current_block,
            requires_grad=True,
            role_description=(
                f"Reasoning instruction for a Level-{level[-1]} game agent. "
                f"This text tells the agent HOW to reason before choosing an action. "
                f"Optimize for CLARITY: the instruction should be unambiguous about what "
                f"kind of thinking is expected. Remove vague or confusing language. "
                f"Do NOT change the intended reasoning depth — only make the instruction clearer."
            )
        )

        # reasoning_var as system prompt → gradient flows back through it
        model = tg.BlackboxLLM(vllm_engine, reasoning_var)

        loss_fn = tg.TextLoss(
            eval_system_prompt=LEVEL_EVAL_RUBRICS[level],
            engine=eval_engine
        )
        optimizer = tg.TGD(parameters=[reasoning_var])
        trace_log = []

        for epoch in range(EPOCHS):
            print(f"\n  Epoch {epoch + 1}/{EPOCHS}")

            for i, scenario in enumerate(level_scenarios):
                optimizer.zero_grad()

                prompt_before = reasoning_var.value  # Snapshot

                # Game state as user message (not optimized)
                prompt = build_game_prompt(scenario, reasoning_block="")
                question = tg.Variable(
                    prompt, requires_grad=False,
                    role_description="game state and action descriptions"
                )

                t0 = time.time()
                response = model(question)
                elapsed = time.time() - t0

                # Response includes <think>...</think> + JSON (no reasoning parser)
                thinking = extract_thinking(response.value)
                loss = loss_fn(response)
                loss.backward()

                # Capture gradient before optimizer clears it
                gradient_text = ""
                if hasattr(reasoning_var, 'gradients') and reasoning_var.gradients:
                    grad = next(iter(reasoning_var.gradients))  # gradients is a set
                    gradient_text = str(grad.value) if hasattr(grad, 'value') else str(grad)
                elif hasattr(reasoning_var, 'get_gradient_text'):
                    gradient_text = reasoning_var.get_gradient_text()

                optimizer.step()

                trace_log.append({
                    "stage": f"level_{level}",
                    "epoch": epoch + 1,
                    "scenario": scenario["name"],
                    "prompt_before": prompt_before,
                    "prompt_after": reasoning_var.value,
                    "thinking_chars": len(thinking),
                    "thinking_excerpt": thinking[:1000] if thinking else "",
                    "response_excerpt": response.value[:500] if hasattr(response, 'value') else "",
                    "eval_score": loss.value[:500] if hasattr(loss, 'value') else str(loss)[:500],
                    "gradient": gradient_text[:1000],
                    "elapsed_s": round(elapsed, 1),
                })

                print(f"    [{i+1}/{len(level_scenarios)}] {scenario['name']} "
                      f"(think: {len(thinking)} chars, {elapsed:.1f}s)")
                if gradient_text:
                    print(f"      Gradient: {gradient_text[:120]}...")

        print(f"\n  {level} Original: {repr(current_block[:100])}")
        print(f"  {level} Optimized: {repr(reasoning_var.value[:100])}")

        results[level] = {
            "original": current_block,
            "optimized": reasoning_var.value,
            "trace": trace_log,
        }

    return results


def main():
    print("=" * 70)
    print("TextGrad Prompt Optimization")
    print(f"Forward model: {VLLM_MODEL} at {VLLM_BASE_URL}")
    print(f"Evaluator: {EVAL_MODEL} via OpenRouter")
    print(f"Scenarios: {len(SCENARIOS)}")
    print(f"Epochs: {EPOCHS}")
    print("=" * 70)

    vllm_engine, eval_engine = setup_engines()

    # Stage 1: Base prompt
    base_results = run_stage1(vllm_engine, eval_engine)

    # Stage 2: Per-level reasoning blocks
    level_results = run_stage2(vllm_engine, eval_engine)

    # Save all results
    output = {
        "base_prompt": base_results,
        **level_results,
        "config": {
            "evaluator_model": EVAL_MODEL,
            "test_model": VLLM_MODEL,
            "vllm_url": VLLM_BASE_URL,
            "epochs": EPOCHS,
            "n_scenarios": len(SCENARIOS),
            "timestamp": datetime.now().isoformat(),
        }
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outfile = OUTPUT_DIR / "textgrad_results.json"
    with open(outfile, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n{'=' * 70}")
    print(f"Results saved to {outfile}")
    print(f"{'=' * 70}")

    # Summary
    print("\n=== SUMMARY ===\n")
    print("Base prompt changed:", base_results["original"][:80] != base_results["optimized"][:80])
    for level in ["L0", "L1", "L2", "L3"]:
        if level in level_results:
            orig = level_results[level]["original"]
            opt = level_results[level]["optimized"]
            changed = orig != opt
            print(f"{level}: changed={changed}")
            if changed:
                print(f"  Original: {repr(orig[:80])}...")
                print(f"  Optimized: {repr(opt[:80])}...")


if __name__ == "__main__":
    main()
