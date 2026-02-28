#!/bin/bash
#SBATCH --job-name=test_qwen35
#SBATCH --partition=gpu_h100
#SBATCH --gpus-per-node=1
#SBATCH --nodes=1
#SBATCH --time=02:00:00
#SBATCH --output=logs/test_qwen35_%j.out
#SBATCH --error=logs/test_qwen35_%j.err

MODEL_PATH=/scratch-shared/kverlaan/origins_models/Qwen3.5-27B
# Qwen3.5-27B needs vLLM nightly (qwen3_5 arch not in managed vllm_25.09.sif v0.10.1)
CONTAINER=/scratch-shared/kverlaan/containers/vllm-nightly.sif

echo "=== Qwen3.5-27B (dense) Test ==="
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "Start: $(date -Iseconds)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null

# Start vLLM with recommended Qwen3.5 settings
# See: https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3.5.html
apptainer exec --nv \
  -B /scratch-shared/kverlaan:/scratch-shared/kverlaan \
  $CONTAINER \
  vllm serve $MODEL_PATH \
  --trust-remote-code \
  --port 8000 \
  --max-model-len 32768 \
  --max-num-seqs 32 \
  --enable-prefix-caching \
  --gpu-memory-utilization 0.9 \
  --dtype auto \
  --reasoning-parser qwen3 \
  --language-model-only &

VLLM_PID=$!

# Wait for vLLM (up to 10 min for model loading + CUDA graph capture)
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

# Run test
source ~/origins/venv/bin/activate
cd ~/origins/simulation

export VLLM_BASE_URL=http://localhost:8000/v1
export VLLM_MODEL=$MODEL_PATH
python test_qwen35.py

echo "=== DONE ==="
kill $VLLM_PID 2>/dev/null
