#!/bin/bash
# Submit memory comparison: with vs without persistent agent memory
# Qwen 3.5-27B (dense), 10 agents, 20 rounds, L1 reasoning
# 2 conditions × 3 reps = 6 runs
#
# Budget: ~6 runs × 0.5h × 192 SBU/GPU-h ≈ 576 SBU

set -e
cd ~/origins/simulation

echo "=== MEMORY COMPARISON — Qwen 3.5-27B ==="
echo "Date: $(date -Iseconds)"
echo "Conditions: memory off vs memory on"
echo "Reps: 3"
echo "Total runs: 6"
echo ""

# Verify model exists
MODEL="/scratch-shared/kverlaan/origins_models/Qwen3.5-27B"
if [ ! -d "$MODEL" ]; then
  echo "ERROR: Qwen 3.5-27B not found at $MODEL"
  echo "Check: ls /scratch-shared/kverlaan/origins_models/"
  exit 1
fi

# Submit — 6 runs total, 1 per array task
JOB=$(sbatch --parsable \
  --array=0-5 \
  --gpus-per-node=1 \
  --time=02:00:00 \
  --job-name=memory_cmp \
  snellius/snellius_run.sh \
  $MODEL \
  experiments/memory_comparison.yaml 1 1)

echo "Job ID: $JOB"
echo ""
echo "Monitor: squeue -u kverlaan --name=memory_cmp -l"
echo "Logs:    ls -lt logs/memory_cmp_*.out | head -10"
echo "Results: ls data/runs/memory_comparison/"
