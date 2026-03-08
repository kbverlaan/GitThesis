---
name: inspect-run
description: Deep-dive into a single simulation run. Use when the user wants to see per-round dynamics, agent timelines, thinking traces, or resource evolution for a specific run.
allowed-tools: Bash, Read, Glob, Grep
argument-hint: "[run-name or sweep/condition] [--thinking] [--agent agent_N]"
---

# Inspect Run

Deep-dive into a single simulation run to understand agent behavior.

## What to do

1. **Find the run.** `$ARGUMENTS` can be:
   - Full run name: `conflict_cost_pct_2_reasoning_level_level3_rep1`
   - Partial match: `conflict_2_L3` — find the closest match
   - Just a sweep + condition hint — list available runs and pick

2. **Run the inspect script** on Snellius:
```bash
ssh snellius "cd ~/origins/simulation && python3 scripts/inspect_run.py data/runs/<sweep_dir>/<run_prefix>"
```

3. **Show the per-round table.** This is the default output — action distributions per round, gini trajectory.

4. **If the user wants agent behavior**, show a timeline:
```bash
ssh snellius "cd ~/origins/simulation && python3 scripts/inspect_run.py data/runs/<sweep>/<run> --agent agent_7"
```

5. **If the user wants thinking traces**, show samples:
```bash
ssh snellius "cd ~/origins/simulation && python3 scripts/inspect_run.py data/runs/<sweep>/<run> --thinking"
```
   Filter by action: `--action invest_other` to find traces where agents chose to cooperate.
   Filter by agent: `--agent agent_1 --thinking` for one agent's reasoning over time.

6. **If the user wants resources**, show per-agent resource table:
```bash
ssh snellius "cd ~/origins/simulation && python3 scripts/inspect_run.py data/runs/<sweep>/<run> --resources"
```

## What to look for

- **Round 1-2 behavior**: What do agents do without history? (L1 should do_nothing, L3 may invest)
- **Parse errors/retries**: `(retry 2)` or `(retry 3)` = model struggled with JSON format
- **Thinking = 0 chars**: These are retry attempts where thinking wasn't captured
- **Action switches**: Agent went from do_nothing → invest → do_nothing = interesting adaptation
- **Target selection**: Who do agents invest in / attack? Weakest? Strongest? Previous partners?
- **Memory references**: In thinking traces, does the agent reference past interactions?

## Run naming convention

```
<param>_<value>_reasoning_level_<level>_rep<N>
```

Example: `conflict_cost_pct_2_reasoning_level_level3_rep1`
- Parameter: conflict_cost_pct = 2%
- Reasoning: level3 (recursive strategic reasoning)
- Repetition: 1 of 2

## Key directories

- Qwen v3 sweeps: `data/runs/qwen_sweep_*`
- Old Gemma sweeps: `data/runs/sweep_*_reasoning`
- Memory comparison: `data/runs/memory_comparison`
- Reasoning depth pilot: `data/runs/reasoning_depth_pilot`
