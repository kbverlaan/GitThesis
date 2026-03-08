---
name: compare-sweeps
description: Compare results between two sweep directories, e.g. Gemma vs Qwen, or old vs new runs. Use when the user asks to compare models, conditions, or run versions.
allowed-tools: Bash, Read, Glob, Grep
argument-hint: "[sweep1] [sweep2]"
---

# Compare Sweeps

Side-by-side comparison of two sweep directories.

## What to do

1. **Parse arguments.** `$ARGUMENTS` should contain two sweep directory names (or shortcuts).
   Common comparisons:
   - Gemma vs Qwen conflict: `sweep_conflict_cost_reasoning` vs `qwen_sweep_conflict_cost`
   - Gemma vs Qwen invest return: `sweep_invest_return_reasoning` vs `qwen_sweep_invest_return`
   - Old vs new (v2 vs v3): check `archive_v2_nomemory/` vs current

2. **Run the comparison:**
```bash
ssh snellius "cd ~/origins/simulation && python3 scripts/analyze_sweep.py data/runs/<sweep1> --compare data/runs/<sweep2>"
```

3. **Interpret key differences.** Always discuss:

   **Model differences (Gemma vs Qwen):**
   - Gemma-2-27B has strong RLHF alignment → invest_other bias even at L0 (70%+)
   - Qwen 3.5-27B is more "rational" → do_nothing when EV is negative
   - Gemma conflict_cost was 0 (no attack cost). Qwen uses realistic costs (2-20%)
   - Gemma had no memory. Qwen v3 has persistent per-agent memory
   - Gemma had god-view neighbor profiles. Qwen v3 has local-only observation

   **Design differences (v2 vs v3):**
   - v2: memory OFF by default, god-view neighbor profiles leaked info
   - v3: memory ON by default, no god-view fallback, thinking traces saved

   **What to highlight:**
   - L0/L1 invest_other in Gemma = RLHF bias, not emergent cooperation
   - L3 invest_other in Qwen = genuine strategic reasoning (verifiable from traces)
   - Higher Gini in Gemma = more dynamic but less valid
   - Cleaner L1→L3 effect in Qwen = stronger causal claim

4. **Present as a table** comparing the same reasoning levels across models:

```
| Model | Level | do_nothing | invest_other | attack | arm_self | Gini |
|-------|-------|-----------|-------------|--------|----------|------|
| Gemma | L0    | 22%       | 74%         | 3%     | 0%       | 0.59 |
| Gemma | L1    | 28%       | 63%         | 6%     | 3%       | 0.68 |
| Qwen  | L1    | 100%      | 0%          | 0%     | 0%       | 0.00 |
| Gemma | L3    | 23%       | 49%         | 8%     | 20%      | 0.69 |
| Qwen  | L3    | 88%       | 11%         | 0%     | 2%       | 0.11 |
```

## Available old sweeps (Gemma-2-27B)

All in `data/runs/` on Snellius:
- `sweep_conflict_cost_reasoning` — conflict_cost [0,3,5] × L0-L3 × 3 reps
- `sweep_invest_return_reasoning` — invest_return [2,5,20] × L0-L3 × 3 reps
- `sweep_arm_cost_reasoning` — arm_cost [0,2,5] × L0-L3 × 3 reps
- `sweep_invest_self_reasoning` — invest_self on/off × L0-L3 × 3 reps
- `arch_combined_gemma2_27b` — architecture framing comparison

Key difference: Gemma sweeps used conflict_cost=0 (free attacks), no memory, god-view profiles.
