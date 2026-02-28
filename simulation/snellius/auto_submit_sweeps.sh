#!/bin/bash
# Auto-submit sweep jobs, keeping max 3 sweep GPUs running
# Reserves 2 GPU slots for training jobs
cd ~/origins/simulation
MODEL=/scratch-shared/kverlaan/origins_models/gemma-2-27b-it
LOG=~/origins/simulation/logs/auto_submit_sweeps.log
MAX_SWEEP_GPUS=3

echo "$(date): Auto-submit started. Max $MAX_SWEEP_GPUS sweep GPUs." >> $LOG

# Phase 1: wait for current sweeps (arm_cost + conflict_cost) to drop below limit
# Phase 2: submit invest_self (2 tasks)
# Phase 3: submit invest_return (3 tasks)

PHASE=1

while true; do
  SWEEP_RUNNING=$(squeue -u kverlaan --partition=gpu_h100 -h 2>/dev/null | grep -cE "sweep_|reasoning_pilot")

  echo "$(date): Phase=$PHASE, sweep_gpus=$SWEEP_RUNNING" >> $LOG

  if [ "$PHASE" -eq 1 ]; then
    # Wait until we have room for invest_self (2 tasks)
    SLOTS=$((MAX_SWEEP_GPUS - SWEEP_RUNNING))
    if [ "$SLOTS" -ge 2 ]; then
      JOB=$(sbatch --parsable --array=0-1 --gpus-per-node=1 --time=12:00:00 \
        --job-name=sweep_self snellius/snellius_run.sh \
        $MODEL experiments/sweep_invest_self_reasoning.yaml 1 12 2>&1)
      echo "$(date): Submitted invest_self: $JOB" >> $LOG
      PHASE=2
    fi

  elif [ "$PHASE" -eq 2 ]; then
    # Wait until we have room for invest_return (3 tasks)
    SLOTS=$((MAX_SWEEP_GPUS - SWEEP_RUNNING))
    if [ "$SLOTS" -ge 3 ]; then
      JOB=$(sbatch --parsable --array=0-2 --gpus-per-node=1 --time=12:00:00 \
        --job-name=sweep_return snellius/snellius_run.sh \
        $MODEL experiments/sweep_invest_return_reasoning.yaml 1 12 2>&1)
      echo "$(date): Submitted invest_return: $JOB" >> $LOG
      echo "$(date): All experiments submitted!" >> $LOG
      exit 0
    fi
  fi

  sleep 120
done
