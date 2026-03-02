#!/bin/bash
#SBATCH --job-name=test_fp8
#SBATCH --partition=gpu_h100
#SBATCH --gpus-per-node=1
#SBATCH --nodes=1
#SBATCH --time=01:00:00
#SBATCH --output=logs/test_fp8_%j.out
#SBATCH --error=logs/test_fp8_%j.err

# FP8 throughput benchmark: uses sweep.py with fp8_benchmark.yaml (same pipeline as production)
MODEL_PATH=/scratch-shared/kverlaan/origins_models/Qwen3.5-27B-FP8
CONTAINER=/scratch-shared/kverlaan/containers/vllm-nightly.sif

echo "=== FP8 Throughput Test ==="
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "Model: $MODEL_PATH"
echo "Start: $(date -Iseconds)"
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader 2>/dev/null

# Start vLLM with FP8 model — same flags as production (snellius_run.sh)
# Port 8199 to avoid collision with other vLLM instances on shared nodes
apptainer exec --nv \
  -B /scratch-shared/kverlaan:/scratch-shared/kverlaan \
  $CONTAINER \
  vllm serve $MODEL_PATH \
  --trust-remote-code \
  --port 8199 \
  --max-model-len 16384 \
  --max-num-seqs 32 \
  --enable-prefix-caching \
  --gpu-memory-utilization 0.95 \
  --dtype auto \
  --reasoning-parser qwen3 \
  --language-model-only \
  --speculative-config '{"method":"mtp","num_speculative_tokens":1}' \
  --no-async-scheduling &

VLLM_PID=$!

echo "Waiting for vLLM to start..."
for i in $(seq 1 120); do
  if curl -s http://localhost:8199/v1/models > /dev/null 2>&1; then
    echo "vLLM ready after $((i*5))s"
    break
  fi
  if ! kill -0 $VLLM_PID 2>/dev/null; then
    echo "ERROR: vLLM process died"
    cat logs/test_fp8_${SLURM_JOB_ID}.err | tail -30
    exit 1
  fi
  sleep 5
done

if ! curl -s http://localhost:8199/v1/models > /dev/null 2>&1; then
  echo "ERROR: vLLM failed to start"
  kill $VLLM_PID 2>/dev/null
  exit 1
fi

curl -s http://localhost:8199/v1/models | python3 -m json.tool

# Check GPU memory after loading
echo ""
echo "=== GPU Memory After Loading ==="
nvidia-smi --query-gpu=memory.used,memory.free,memory.total --format=csv,noheader 2>/dev/null

# Run via sweep.py — same pipeline as production runs
# Override base_url and model to point to our FP8 server on port 8199
source ~/origins/venv/bin/activate
cd ~/origins/simulation

echo ""
echo "=== Running FP8 benchmark (3 rounds, L3, 10 agents) ==="
PYTHONUNBUFFERED=1 python src/sweep.py experiments/fp8_benchmark.yaml

echo ""
echo "=== DONE ==="
echo "End: $(date -Iseconds)"
kill $VLLM_PID 2>/dev/null
