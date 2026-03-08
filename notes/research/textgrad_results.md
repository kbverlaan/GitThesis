# TextGrad Prompt Optimization Results

## Setup

| Parameter | Value |
|-----------|-------|
| Forward model | Qwen 3.5-27B (vLLM on Snellius H100) |
| Evaluator | Claude Opus 4.6 (OpenRouter) |
| Framework | TextGrad (TGD optimizer) |
| Epochs | 3 |
| Test scenarios | 10 (from test_qwen35.py) |
| vLLM config | NO reasoning parser (so `<think>` tags stay in content for evaluation) |

## Architecture

```
reasoning_var (system prompt, requires_grad=True)
        |
    BlackboxLLM (Qwen 3.5, vLLM, no reasoning parser)
        |
    response (<think>...</think> + JSON action)
        |
    TextLoss (Opus 4.6, level-specific rubric)
        |
    loss.backward() → textual gradient → TGD updates reasoning_var
```

Gradient flow: loss → response → system_prompt (reasoning_var). This is the standard TextGrad pattern where the system prompt is the optimized variable.

## K-Level Mapping (Zhang et al., 2024)

| Zhang K | Our Level | Prompt instruction | Intended reasoning |
|---------|-----------|-------------------|-------------------|
| — | L0 | (none) | Reactive, no deliberation |
| K=1 | L1 | "Other agents choose without strategic reasoning" | Expected value calculation |
| K=2 | L2 | "Other agents calculate their best action (L1)" | Opponent modeling |
| K=3 | L3 | "Other agents analyze your recent actions to predict you (L2)" | Recursive reasoning |

## Optimization Goal: INSTRUCTION CLARITY (not reasoning depth)

**Key methodological choice**: The evaluator judges whether the prompt instructions are **clear and unambiguous**, NOT whether the model's reasoning output matches the intended depth. Optimizing for "correct" reasoning output would create a confound — we'd be training the prompts to produce specific outputs rather than ensuring the model understands what's being asked.

### Stage 1: Base Prompt — Game Mechanics Clarity
Optimizes the shared instructional text (objective + action descriptions + constraints). Evaluated on all 10 scenarios. Rubric: did the model misunderstand any action mechanic, cost, or game rule? Were the instructions parseable?

### Stage 2: Per-Level Reasoning Blocks — Instruction Clarity
Optimizes each level's reasoning instruction separately. Rubric: is the reasoning instruction unambiguous? Does the model show confusion about what kind of thinking is expected? (NOT: did the model actually reason at the "correct" depth.)

---

## Run 1: 2026-02-28 (Job 20151816)

**Status**: Stage 1 ✅ complete (3 epochs), Stage 2 ~95% complete (TIMEOUT at 2h).
**No results file saved** (script killed before writing). All data in SLURM log.
**Known issue**: TextGrad sends `temperature=0` → Qwen thinking mode disabled → `think: 0 chars` in Stage 2. Evaluator still worked (evaluated inline reasoning). Fix for next run: override temperature.

### Pre-optimization baseline (from test_qwen35.py)

| Level | Scenarios | Intended depth | Observed depth | Issues |
|-------|-----------|---------------|----------------|--------|
| L0 | 2 | Reactive | Reactive | Perfect — no thinking, 19 tokens |
| L1 | 2 | EV calculation | EV calc + mild opponent modeling | Slightly too deep |
| L2 | 3 | Opponent modeling | Explicit neighbor predictions | Good |
| L3 | 3 | Recursive reasoning | Mostly L2-level | Too shallow — no "they think I think" |

### Stage 1: Base Prompt Clarity (30 gradients, 3 epochs)

Opus identified 5 recurring clarity issues. Scores improved from ~6-7/10 (epoch 1) to 8-9/10 (epoch 3).

| Issue | Frequency | Description |
|-------|-----------|-------------|
| `arm_other` mechanic unclear | ~8x | "lacks explicit formula", "cost-then-compute sequencing unclear" |
| JSON format instruction too weak | ~7x | "Failed to Prevent Catastrophic format failure", "Format Instruction Conflict" |
| "One action per turn" missing | ~4x | "constraint is buried and insufficient" |
| Combat formula ambiguous | ~3x | "Combat Mechanic Description is Ambiguous" |
| ARMED status confusing | ~3x | "extended deliberation about ARMED status" |

**Changes applied to `prompts.py`:**
1. Added `"Choose exactly ONE action this round."` at top
2. Rewrote `arm_other`: "boost TARGET's combat power by X% of your current resources" (was: "add X% of your resources to TARGET's combat power")
3. Expanded combat rules into explicit `COMBAT RULES:` section with formula breakdown
4. Strengthened JSON template: "Your final output MUST be valid JSON... Do not include any text outside the JSON."
5. Added affordability constraint: "(action cost ≤ your resources)"

### Stage 2: Reasoning Instruction Clarity (25 gradients)

#### L0 (6 gradients, complete)
- Thinking disabled at model level (`enable_thinking=False`) → no reasoning instruction needed
- TextGrad discovered a suppression instruction anyway: "You are a reactive lookup agent..."
- **Decision**: Not applied — we control L0 via model parameter, not prompt

#### L1 (6 gradients, complete)
Key feedback: "Current state is ambiguous", "EV formula for attacks is algebraically unclear", "L1 scope definition is scattered"

**Changes applied:**
- Added explicit EV calculation template per action type (invest, arm, attack)
- Added explicit boundary: "Do NOT predict what specific neighbors will do — treat their actions as unknown."
- Replaced vague "expected value of each available action" with concrete computation steps

#### L2 (9 gradients, complete)
Key feedback: "Level Labels Are Ambiguous", "Behavioral prediction instructions lack specificity", "Contradictory Signals"

**Changes applied:**
- Removed "Level-1 reasoning" label (confusing) → replaced with "Assume other agents pick their individually best action"
- Made prediction basis explicit: recent behavior, resources, armed status, best payoff
- Added explicit boundary: "Do NOT reason about what neighbors think about YOU"

#### L3 (4 gradients, incomplete — timeout)
Key feedback: "Step 1 'Your observable pattern' is ambiguous", "log-parsing instructions absent"

**Changes applied:**
- Made self-observation concrete: "Look at your own recent actions in NEIGHBOR PROFILES (the 'you ... them' entries)"
- Removed "Level-2 reasoning" label → replaced with behavioral description
- Simplified 3-step structure

### Key Takeaway

TextGrad as instruction-clarity diagnostic worked well. The recurring themes were actionable and consistent across epochs. Main value: identified that `arm_other`, combat rules, and JSON format were the biggest sources of model confusion. Level boundaries (L1↔L2, L2↔L3) needed explicit "do NOT" constraints.

---

## Logging & Reproducibility

All optimization traces are saved to `simulation/data/textgrad_results.json` with:
- Per-step prompt snapshots (before/after)
- Qwen's full response (thinking + action)
- Opus evaluator scores
- Textual gradients (critiques)
- Timing data
- Full config (model paths, epochs, scenarios)

SLURM job logs at `simulation/logs/textgrad_opt_<jobid>.out`.

## Cost Tracking

| Run | Opus calls | Input tokens | Output tokens | Cost |
|-----|-----------|-------------|---------------|------|
| Run 1 | ~120 | ~240K | ~60K | ~$2.70 |

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-28 | Use Opus 4.6 as evaluator (not Sonnet) | Better at judging subtle reasoning depth differences. Cost difference ~$1. |
| 2026-02-28 | Run vLLM WITHOUT reasoning parser for TextGrad | TextGrad's BlackboxLLM only captures `content` field. Without parser, `<think>` tags stay in content so evaluator can see them. |
| 2026-02-28 | Use reasoning_var as system prompt | Only way to get TextGrad gradient flow back to the optimized variable. |
| 2026-02-28 | Defer Option B (original vs optimized) | Robustness check for later sprint. |
