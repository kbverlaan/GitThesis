#!/bin/bash
# Auto-submit Qwen3-32B runs in batches of 2
# Monitors queue and submits next batch when slots free up
# Total: array tasks 0-9, 10 runs each = 100 runs

cd ~/origins/simulation
LOG=~/origins/simulation/logs/auto_submit.log

NEXT_BATCH=4  # Start at 4 (0-1 already submitted as 19626732, 2-3 next)

# First submit batch 2-3
echo "$(date): Submitting array 2-3" >> $LOG
JOB=$(sbatch --parsable --array=2-3 --gpus-per-node=1 --time=2-00:00:00 \
  --job-name=arch_qwen3 snellius/snellius_run.sh \
  /scratch-shared/kverlaan/origins_models/Qwen3-32B \
  experiments/arch_combined_qwen3_32b.yaml 1 10 2>&1)
echo "$(date): Submitted $JOB" >> $LOG

while [ $NEXT_BATCH -le 9 ]; do
  # Count running GPU jobs
  RUNNING=$(squeue -u kverlaan --partition=gpu_h100 -h 2>/dev/null | wc -l)

  if [ "$RUNNING" -lt 2 ]; then
    END=$((NEXT_BATCH + 1))
    if [ $END -gt 9 ]; then END=9; fi

    echo "$(date): Submitting array ${NEXT_BATCH}-${END} (running=$RUNNING)" >> $LOG
    JOB=$(sbatch --parsable --array=${NEXT_BATCH}-${END} --gpus-per-node=1 \
      --time=2-00:00:00 --job-name=arch_qwen3 snellius/snellius_run.sh \
      /scratch-shared/kverlaan/origins_models/Qwen3-32B \
      experiments/arch_combined_qwen3_32b.yaml 1 10 2>&1)
    echo "$(date): Submitted $JOB" >> $LOG
    NEXT_BATCH=$((END + 1))
  fi

  sleep 300  # Check every 5 min
done

echo "$(date): All batches submitted!" >> $LOG
