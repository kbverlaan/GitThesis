#!/bin/bash
#SBATCH --job-name=textgrad_opt
#SBATCH --partition=gpu_h100
#SBATCH --gpus-per-node=1
#SBATCH --nodes=1
#SBATCH --time=03:00:00
#SBATCH --output=logs/textgrad_opt_%j.out
#SBATCH --error=logs/textgrad_opt_%j.err

MODEL_PATH=/scratch-shared/kverlaan/origins_models/Qwen3.5-27B
CONTAINER=/scratch-shared/kverlaan/containers/vllm-nightly.sif

echo "=== TextGrad Prompt Optimization ==="
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "Start: $(date -Iseconds)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null

# Start vLLM WITHOUT --reasoning-parser so <think> tags stay in content.
# TextGrad evaluator checks INSTRUCTION CLARITY (not reasoning depth).
# Also use --language-model-only to skip vision encoder.
apptainer exec --nv \
  -B /scratch-shared/kverlaan:/scratch-shared/kverlaan \
  $CONTAINER \
  vllm serve $MODEL_PATH \
  --trust-remote-code \
  --port 8000 \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.9 \
  --dtype auto \
  --language-model-only &

VLLM_PID=$!

# Wait for vLLM
echo "Waiting for vLLM to start..."
for i in $(seq 1 120); do
  if curl -s http://localhost:8000/v1/models > /dev/null 2>&1; then
    echo "vLLM ready after $((i*5))s"
    break
  fi
  if ! kill -0 $VLLM_PID 2>/dev/null; then
    echo "ERROR: vLLM process died"
    exit 1
  fi
  sleep 5
done

if ! curl -s http://localhost:8000/v1/models > /dev/null 2>&1; then
  echo "ERROR: vLLM failed to start"
  kill $VLLM_PID 2>/dev/null
  exit 1
fi

curl -s http://localhost:8000/v1/models | python3 -m json.tool

# Activate venv and install textgrad if needed
source ~/origins/venv/bin/activate
pip install textgrad 2>/dev/null || echo "textgrad already installed"

cd ~/origins/simulation

export VLLM_BASE_URL=http://localhost:8000/v1
export VLLM_MODEL=$MODEL_PATH
# Load API key from .env if not already set
if [ -z "$OPENROUTER_API_KEY" ] && [ -f ~/origins/simulation/.env ]; then
  echo "Loading OPENROUTER_API_KEY from .env"
  source ~/origins/simulation/.env
fi

if [ -z "$OPENROUTER_API_KEY" ]; then
  echo "ERROR: OPENROUTER_API_KEY not set (set in env or ~/origins/simulation/.env)"
  kill $VLLM_PID 2>/dev/null
  exit 1
fi

echo "Starting TextGrad optimization (evaluator: Sonnet 4.6 via OpenRouter)..."
PYTHONUNBUFFERED=1 python scripts/textgrad_optimize.py

echo "=== DONE ==="
kill $VLLM_PID 2>/dev/null
