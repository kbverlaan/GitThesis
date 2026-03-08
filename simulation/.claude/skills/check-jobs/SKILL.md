---
name: check-jobs
description: Check Snellius HPC job status, progress, and budget. Use when the user asks if runs are done, how jobs are going, or wants a status update.
allowed-tools: Bash, Read
---

# Check Snellius Jobs

Monitor running simulation jobs on Snellius HPC.

## What to do

1. **Check job queue:**
```bash
ssh snellius 'squeue -u kverlaan --format="%.10i %.15j %.8T %.10M %.6D %R" 2>/dev/null'
```

2. **Check progress** of running jobs (count completed rounds):
```bash
ssh snellius 'for log in ~/origins/simulation/logs/qw_*.out; do name=$(basename $log .out); rounds=$(grep -c "Round Results" $log 2>/dev/null); echo "$name: $rounds rounds"; done'
```

3. **Check for errors:**
```bash
ssh snellius 'grep -l "Error\|Traceback\|FAILED" ~/origins/simulation/logs/qw_*.out 2>/dev/null'
```

4. **Check landed results:**
```bash
ssh snellius 'for dir in ~/origins/simulation/data/runs/qwen_sweep_*; do count=$(ls $dir/*_metrics.json 2>/dev/null | wc -l); echo "$(basename $dir): $count runs complete"; done'
```

5. **Check SBU budget:**
```bash
ssh snellius 'scontrol show assoc user=kverlaan 2>/dev/null | head -5'
```

6. **Report status** including:
   - How many jobs running / pending / completed
   - How many of 116 total runs are done
   - Estimated time to completion
   - Any budget concerns (14,474 SBU remaining as of Mar 1)
   - Any errors or issues

## Job structure (v3 nightrun)

Three dependency-chained batches:
- **Batch 1**: conflict (2 tasks) + take (2 tasks) = 32 runs
- **Batch 2** (after batch 1): arm_self (2) + arm_other (2) + return (2) + invest_cost (2) = 48 runs
- **Batch 3** (after batch 2): radius (2) + invest_self (1) + memory (1) = 36 runs

Each task runs 6-8 sequential simulation runs (mix of L1 and L3).
Wall time: 8h per task. Expected actual: ~6-7h per task.

## Timing estimates

- L1 run (10 agents, 10 rounds): ~35-40 min
- L3 run (10 agents, 10 rounds): ~60-70 min
- Per task (8 runs: 4×L1 + 4×L3): ~6-7 hours
- Total across 3 batches: ~20h wall time (sequential dependency chain)

## SSH details
- Host: `snellius` (alias for kverlaan@snellius.surf.nl)
- Working dir: `~/origins/simulation`
- Log dir: `~/origins/simulation/logs/`
- Data dir: `~/origins/simulation/data/runs/`
