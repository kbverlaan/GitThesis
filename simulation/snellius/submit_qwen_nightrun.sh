#!/bin/bash
# Nightrun Stage 1: Qwen 3.5-27B OAT screening sweeps
# Quick: 10 agents, 10 rounds | invest_self OFF (default)
# invest_self on/off tested as separate sweep
#
# Total: 116 runs, 15 array tasks
#
# Usage: ssh snellius 'bash ~/origins/simulation/snellius/submit_qwen_nightrun.sh'

cd ~/origins/simulation
MODEL=/scratch-shared/kverlaan/origins_models/Qwen3.5-27B
TIME="06:00:00"  # Reduced from 8h: MTP + higher timeout = fewer wasted retries

echo "=== Qwen 3.5-27B Stage 1: Screening Sweeps ==="
echo "Start: $(date)"
echo "Quick mode: 10 agents, 10 rounds, invest_self OFF"
echo "Levels: L1 + L3 | Reps: 2"
echo ""

mkdir -p logs

# --- Conflict theta ---

# 1. conflict_cost_pct: [2,5,10,20] × L1+L3 × 2 reps = 16 runs
JOB1=$(sbatch --parsable --array=0-1 --gpus-per-node=1 --time=$TIME \
  --job-name=qw_conflict snellius/snellius_run.sh \
  $MODEL experiments/qwen_sweep_conflict_cost.yaml 1 8)
echo "conflict_cost_pct [2,5,10,20%]: job $JOB1 (16 runs, 2 tasks)"

# 2. attack_take_pct: [20,40,60,80] × L1+L3 × 2 reps = 16 runs
JOB2=$(sbatch --parsable --array=0-1 --gpus-per-node=1 --time=$TIME \
  --job-name=qw_take snellius/snellius_run.sh \
  $MODEL experiments/qwen_sweep_attack_take.yaml 1 8)
echo "attack_take_pct [20,40,60,80%]: job $JOB2 (16 runs, 2 tasks)"

# --- Arming theta ---

# 3. arm_cost_pct (self): [5,10,20] × L1+L3 × 2 reps = 12 runs
JOB3=$(sbatch --parsable --array=0-1 --gpus-per-node=1 --time=$TIME \
  --job-name=qw_arm_self snellius/snellius_run.sh \
  $MODEL experiments/qwen_sweep_arm_self.yaml 1 6)
echo "arm_cost_pct (self) [5,10,20%]: job $JOB3 (12 runs, 2 tasks)"

# 4. arm_other_cost_pct: [5,10,20] × L1+L3 × 2 reps = 12 runs
JOB4=$(sbatch --parsable --array=0-1 --gpus-per-node=1 --time=$TIME \
  --job-name=qw_arm_other snellius/snellius_run.sh \
  $MODEL experiments/qwen_sweep_arm_other.yaml 1 6)
echo "arm_other_cost_pct [5,10,20%]: job $JOB4 (12 runs, 2 tasks)"

# --- Cooperation theta ---

# 5. invest_other_return_pct: [10,15,25] × L1+L3 × 2 reps = 12 runs
JOB5=$(sbatch --parsable --array=0-1 --gpus-per-node=1 --time=$TIME \
  --job-name=qw_return snellius/snellius_run.sh \
  $MODEL experiments/qwen_sweep_invest_return.yaml 1 6)
echo "invest_other_return_pct [10,15,25%]: job $JOB5 (12 runs, 2 tasks)"

# 6. invest_other_cost_pct: [5,10,20] × L1+L3 × 2 reps = 12 runs
JOB6=$(sbatch --parsable --array=0-1 --gpus-per-node=1 --time=$TIME \
  --job-name=qw_invest_cost snellius/snellius_run.sh \
  $MODEL experiments/qwen_sweep_invest_cost.yaml 1 6)
echo "invest_other_cost_pct [5,10,20%]: job $JOB6 (12 runs, 2 tasks)"

# --- Spatial ---

# 7. interaction_radius: [1,2,3] × L1+L3 × 2 reps = 12 runs
JOB7=$(sbatch --parsable --array=0-1 --gpus-per-node=1 --time=$TIME \
  --job-name=qw_radius snellius/snellius_run.sh \
  $MODEL experiments/qwen_sweep_radius.yaml 1 6)
echo "radius [1,2,3]: job $JOB7 (12 runs, 2 tasks)"

# --- Toggles ---

# 8. invest_self on/off: 2 × L1+L3 × 2 reps = 8 runs
JOB8=$(sbatch --parsable --array=0-0 --gpus-per-node=1 --time=$TIME \
  --job-name=qw_inv_self snellius/snellius_run.sh \
  $MODEL experiments/qwen_sweep_invest_self.yaml 1 8)
echo "invest_self [on,off]: job $JOB8 (8 runs, 1 task)"

# 9. memory on/off: 2 × L1+L3 × 2 reps = 8 runs
JOB9=$(sbatch --parsable --array=0-0 --gpus-per-node=1 --time=$TIME \
  --job-name=qw_memory snellius/snellius_run.sh \
  $MODEL experiments/qwen_sweep_memory.yaml 1 8)
echo "memory [on,off]: job $JOB9 (8 runs, 1 task)"

echo ""
echo "=== Submitted 9 experiments, 15 array tasks, 116 runs total ==="
echo "SBU estimate: ~12K (15 tasks × 4h × 192 SBU/GPU-h)"
echo "Monitor: squeue -u kverlaan"
echo "Logs: tail -f ~/origins/simulation/logs/qw_*"
