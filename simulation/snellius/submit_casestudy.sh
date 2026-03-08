#!/bin/bash
#SBATCH --job-name=casestudy30
#SBATCH --partition=gpu_h100
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=4
#SBATCH --output=logs/casestudy_%j.out
#SBATCH --error=logs/casestudy_%j.err

# Case study: 30 agents, 60 rounds, Qwen 3.5-27B
# Budget: ~676 SBU remaining, H100 = ~128 SBU/h → ~5h max
# Expected: ~3-3.5h for 30 agents × 60 rounds

MODEL_PATH=/scratch-shared/kverlaan/origins_models/Qwen3.5-27B
CONTAINER=/scratch-shared/kverlaan/containers/vllm-nightly.sif

echo "=== CASE STUDY: 30 agents × 60 rounds ==="
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "Start: $(date -Iseconds)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null

cd ~/origins/simulation
mkdir -p logs data/runs data/runs/checkpoints

# Start vLLM with Qwen3.5 optimizations
apptainer exec --nv \
  -B /scratch-shared/kverlaan:/scratch-shared/kverlaan \
  $CONTAINER \
  vllm serve $MODEL_PATH \
  --tensor-parallel-size 1 \
  --trust-remote-code \
  --port 8000 \
  --max-model-len 16384 \
  --max-num-seqs 32 \
  --gpu-memory-utilization 0.95 \
  --dtype auto \
  --reasoning-parser qwen3 \
  --language-model-only \
  --speculative-config '{"method":"mtp","num_speculative_tokens":1}' &

VLLM_PID=$!

# Wait for vLLM (up to 10 min)
echo "Waiting for vLLM..."
for i in $(seq 1 120); do
  if curl -s http://localhost:8000/v1/models > /dev/null 2>&1; then
    echo "vLLM ready after $((i*5))s"
    break
  fi
  if ! kill -0 $VLLM_PID 2>/dev/null; then
    echo "ERROR: vLLM died"
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

# Run simulation
source ~/origins/venv/bin/activate

# Resume from R2 checkpoint (previous run hung at R3)
PYTHONUNBUFFERED=1 python src/main.py \
  --game config/casestudy_30agent.yaml \
  --api config/vllm_config.yaml \
  --output data/runs \
  --resume data/runs/checkpoints/20260305_155319_checkpoint.json

EXIT_CODE=$?
echo "=== CASE STUDY COMPLETE (exit: $EXIT_CODE) at $(date -Iseconds) ==="

kill $VLLM_PID 2>/dev/null
