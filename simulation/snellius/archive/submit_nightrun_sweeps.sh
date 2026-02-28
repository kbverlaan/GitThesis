#!/bin/bash
# Nightrun: parameter sweeps × reasoning depth on Gemma 2 27B
# Total: 132 runs across 4 experiments
# Strategy: batch_size=12, max 5 GPUs concurrent via Slurm account limit
#
# Usage: ssh snellius 'bash ~/origins/simulation/snellius/submit_nightrun_sweeps.sh'

cd ~/origins/simulation
MODEL=/scratch-shared/kverlaan/origins_models/gemma-2-27b-it
TIME="12:00:00"

echo "=== Nightrun Parameter Sweeps ==="
echo "Start: $(date)"

# Ensure output dirs and log dir exist
mkdir -p logs

# 1. arm_cost sweep: 3 values × 4 levels × 3 reps = 36 runs
#    array=0-2, batch=12 → 3 tasks, 12 runs each (~7h)
JOB1=$(sbatch --parsable --array=0-2 --gpus-per-node=1 --time=$TIME \
  --job-name=sweep_arm snellius/snellius_run.sh \
  $MODEL experiments/sweep_arm_cost_reasoning.yaml 1 12)
echo "arm_cost sweep: job $JOB1 (36 runs, 3 tasks)"

# 2. conflict_cost sweep: 3 values × 4 levels × 3 reps = 36 runs
JOB2=$(sbatch --parsable --array=0-2 --gpus-per-node=1 --time=$TIME \
  --job-name=sweep_conflict snellius/snellius_run.sh \
  $MODEL experiments/sweep_conflict_cost_reasoning.yaml 1 12)
echo "conflict_cost sweep: job $JOB2 (36 runs, 3 tasks)"

# 3. invest_self sweep: 2 values × 4 levels × 3 reps = 24 runs
JOB3=$(sbatch --parsable --array=0-1 --gpus-per-node=1 --time=$TIME \
  --job-name=sweep_self snellius/snellius_run.sh \
  $MODEL experiments/sweep_invest_self_reasoning.yaml 1 12)
echo "invest_self sweep: job $JOB3 (24 runs, 2 tasks)"

# 4. invest_other_return sweep: 3 values × 4 levels × 3 reps = 36 runs
JOB4=$(sbatch --parsable --array=0-2 --gpus-per-node=1 --time=$TIME \
  --job-name=sweep_return snellius/snellius_run.sh \
  $MODEL experiments/sweep_invest_return_reasoning.yaml 1 12)
echo "invest_return sweep: job $JOB4 (36 runs, 3 tasks)"

echo ""
echo "=== Submitted 4 experiments, 11 array tasks, 132 runs total ==="
echo "Monitor: squeue -u kverlaan"
echo "Logs: tail -f ~/origins/simulation/logs/sweep_*"
