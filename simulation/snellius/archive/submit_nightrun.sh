#!/bin/bash
# Submit Arch 1+2 production runs — Qwen3-32B
# Gemma 2 already done (100/100). This submits Qwen3-32B.
#
# Budget: ~46,700 SBU remaining, 192 SBU/GPU-h
# Estimated: ~2.5h/run (max_tokens=2048) → 480 SBU/run
# 100 runs (20 reps × 5 framings) = ~48,000 SBU
#
# 10 array tasks × 10 runs each = 100 runs

set -e
cd ~/origins/simulation

echo "=== ARCH 1+2 SUBMISSION — QWEN3-32B ==="
echo "Date: $(date -Iseconds)"
echo ""

# Verify Qwen3-32B model exists
if [ ! -d "/scratch-shared/kverlaan/origins_models/Qwen3-32B" ]; then
  echo "ERROR: Qwen3-32B model not found. Download first."
  exit 1
fi

# Qwen3-32B — 1 GPU, thinking model (enable_thinking=True, max_tokens=2048, 240s timeout)
# Estimate: ~2.5h per run (30 agents, 50 rounds, thinking enabled)
# 10 array tasks × 10 runs each = 100 runs (20 reps per framing)
echo "Submitting Qwen3-32B (10 array tasks × 10 runs = 100 runs)..."
QWEN3_JOB=$(sbatch --parsable \
  --array=0-9 \
  --gpus-per-node=1 \
  --time=2-00:00:00 \
  --job-name=arch_qwen3 \
  snellius/snellius_run.sh \
  /scratch-shared/kverlaan/origins_models/Qwen3-32B \
  experiments/arch_combined_qwen3_32b.yaml 1 10)
echo "  Job ID: $QWEN3_JOB"

echo ""
echo "=== SUBMITTED ==="
echo "Qwen3-32B: $QWEN3_JOB (10 tasks × 10 runs, 1 GPU each, 48h)"
echo "Gemma 2:   ALREADY COMPLETE (100/100 runs)"
echo "Total: 200 runs across 2 models"
echo ""
echo "Monitor: squeue -u kverlaan --name=arch_qwen3 -l"
echo "Logs:    ls -lt logs/arch_qwen3_*.out | head -10"
