#!/bin/bash
#SBATCH --job-name=mem_clarity
#SBATCH --partition=gpu_h100
#SBATCH --gpus-per-node=1
#SBATCH --nodes=1
#SBATCH --time=01:00:00
#SBATCH --output=logs/mem_clarity_%j.out
#SBATCH --error=logs/mem_clarity_%j.err

MODEL_PATH=/scratch-shared/kverlaan/origins_models/Qwen3.5-27B
CONTAINER=/scratch-shared/kverlaan/containers/vllm-nightly.sif

echo "=== Memory Clarity Evaluation ==="
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "Start: $(date -Iseconds)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null

# Start vLLM WITH --reasoning-parser qwen3 (matches snellius_run.sh)
# Thinking goes to reasoning_content field in API response
apptainer exec --nv \
  -B /scratch-shared/kverlaan:/scratch-shared/kverlaan \
  $CONTAINER \
  vllm serve $MODEL_PATH \
  --trust-remote-code \
  --port 8000 \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.9 \
  --dtype auto \
  --reasoning-parser qwen3 \
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

# Activate venv
source ~/origins/venv/bin/activate
cd ~/origins/simulation

export VLLM_BASE_URL=http://localhost:8000/v1
export VLLM_MODEL=$MODEL_PATH

# Load API key from .env if not already set
if [ -z "$OPENROUTER_API_KEY" ] && [ -f ~/origins/simulation/.env ]; then
  echo "Loading OPENROUTER_API_KEY from .env"
  source ~/origins/simulation/.env
  export OPENROUTER_API_KEY
fi

if [ -z "$OPENROUTER_API_KEY" ]; then
  echo "ERROR: OPENROUTER_API_KEY not set (set in env or ~/origins/simulation/.env)"
  kill $VLLM_PID 2>/dev/null
  exit 1
fi

echo "Starting memory clarity evaluation..."
PYTHONUNBUFFERED=1 python scripts/eval_memory_clarity.py

echo "=== DONE ==="
kill $VLLM_PID 2>/dev/null
