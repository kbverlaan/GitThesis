#!/bin/bash
#SBATCH --job-name=night30x30_gemma
#SBATCH --partition=gpu_h100
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --time=02:30:00
#SBATCH --cpus-per-task=4
#SBATCH --output=logs/night30x30_gemma_%j.out
#SBATCH --error=logs/night30x30_gemma_%j.err

# 30 agents × 30 rounds, L2 ToM + DM + rewiring w=0.3
# Gemma 4 31B Dense via vLLM nightly (no reasoning parser — Gemma is not a <think>-tag model).

MODEL_PATH=/scratch-shared/kverlaan/origins_models/Gemma4-31B
CONTAINER=/scratch-shared/kverlaan/containers/vllm-nightly.sif
API_CONFIG=config/vllm_gemma_config.yaml

echo "=== NIGHT RUN (Gemma 4): 30 agents × 30 rounds ==="
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "Model: $MODEL_PATH"
echo "Start: $(date -Iseconds)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null

cd ~/origins/simulation
mkdir -p logs data/runs data/runs/checkpoints

apptainer exec --nv \
  -B /scratch-shared/kverlaan:/scratch-shared/kverlaan \
  $CONTAINER \
  vllm serve $MODEL_PATH \
  --tensor-parallel-size 1 \
  --trust-remote-code \
  --port 8000 \
  --max-model-len 32768 \
  --max-num-seqs 32 \
  --gpu-memory-utilization 0.95 \
  --dtype bfloat16 \
  --reasoning-parser gemma4 &

VLLM_PID=$!

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

source ~/origins/venv/bin/activate

PYTHONUNBUFFERED=1 python src/main.py \
  --game config/night_params.yaml \
  --api $API_CONFIG \
  --output data/runs

EXIT_CODE=$?
echo "=== NIGHT RUN COMPLETE (exit: $EXIT_CODE) at $(date -Iseconds) ==="

kill $VLLM_PID 2>/dev/null
