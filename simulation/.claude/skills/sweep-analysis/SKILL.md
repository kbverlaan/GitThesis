---
name: sweep-analysis
description: Analyze simulation sweep results. Use when the user asks to check results, analyze a sweep, show metrics, or generate plots for completed simulation runs.
allowed-tools: Bash, Read, Glob, Grep
argument-hint: "[sweep-dir-name or 'all']"
---

# Sweep Analysis

Analyze simulation sweep results from Snellius HPC or local data.

## What to do

1. **Find the sweep data.** If `$ARGUMENTS` is provided, use it as the sweep directory name under `data/runs/`. If "all", analyze all `qwen_sweep_*` directories. If empty, list available sweep directories.

2. **Run the analysis script** on Snellius (data lives there):
```bash
ssh snellius "cd ~/origins/simulation && python3 scripts/analyze_sweep.py data/runs/<sweep_dir> --traces"
```

3. **Generate plots** if the user asks or if this is a first look:
```bash
ssh snellius "cd ~/origins/simulation && python3 scripts/analyze_sweep.py data/runs/<sweep_dir> --plot"
```
Then download and show:
```bash
scp "snellius:origins/simulation/data/runs/<sweep_dir>/plots/*" /tmp/
```
Use the Read tool to display the PNG files.

4. **Present findings.** Always include:
   - Summary table: conditions × action distributions × gini
   - Key pattern: what's the L1 vs L3 difference?
   - Thinking trace status: are traces being saved? Average length?
   - Any anomalies: parse errors, missing conditions, unexpected behavior?

5. **Interpret results** in context of the thesis:
   - do_nothing dominance at L1 = rational equilibrium (EV calculation)
   - invest_other at L3 = emergent cooperation via strategic reasoning
   - Higher gini = more inequality = more dynamic system
   - Compare to Gemma baselines if relevant (Gemma had 70%+ invest at L0 due to RLHF bias)

## Key metrics to report

| Metric | What it means |
|--------|--------------|
| Action distribution (%) | What agents are doing — do_nothing, invest_other, attack, arm_self |
| Final Gini | Inequality at end of simulation. 0 = flat, >0.5 = high inequality |
| Res±σ | Mean resources ± std dev. Growing mean = economy expanding |
| Thinking chars | Average thinking trace length. >10K = model reasoning deeply |

## Available sweep directories (typical)

- `qwen_sweep_conflict_cost` — conflict_cost_pct [2,5,10,20] × L1+L3
- `qwen_sweep_attack_take` — attack_take_pct [20,40,60,80] × L1+L3
- `qwen_sweep_arm_self` — arm_cost_pct [5,10,20] × L1+L3
- `qwen_sweep_arm_other` — arm_other_cost_pct [5,10,20] × L1+L3
- `qwen_sweep_invest_return` — invest_other_return_pct [10,15,25] × L1+L3
- `qwen_sweep_invest_cost` — invest_other_cost_pct [5,10,20] × L1+L3
- `qwen_sweep_radius` — interaction_radius [1,2,3] × L1+L3
- `qwen_sweep_invest_self` — invest_self on/off × L1+L3
- `qwen_sweep_memory` — memory on/off × L1+L3
- Old Gemma sweeps: `sweep_conflict_cost_reasoning`, `sweep_invest_return_reasoning`, etc.
