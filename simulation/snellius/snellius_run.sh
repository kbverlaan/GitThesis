#!/bin/bash
#SBATCH --job-name=origins
#SBATCH --partition=gpu_h100
#SBATCH --nodes=1
#SBATCH --time=12:00:00
#SBATCH --output=logs/%x_%A_%a.out
#SBATCH --error=logs/%x_%A_%a.err

# Usage: sbatch --gpus-per-node=N [--array=0-99] snellius/snellius_run.sh <MODEL_PATH> <EXPERIMENT_YAML> <NUM_GPUS> [BATCH_SIZE]
# Single run:   sbatch --gpus-per-node=1 --array=0-99 snellius/snellius_run.sh <model> <yaml> 1
# Batched runs: sbatch --gpus-per-node=4 --array=0-9  snellius/snellius_run.sh <model> <yaml> 4 10
#
# Throughput: game engine sends 30 concurrent requests per round (ThreadPoolExecutor).
# vLLM handles concurrency server-side via continuous batching + prefix caching.
# For models that fit on 1 GPU (e.g. Qwen3.5-27B), use NUM_GPUS=1 — the throughput
# comes from concurrent sequences, not tensor parallelism.

MODEL_PATH=$1
EXPERIMENT=$2
NUM_GPUS=${3:-1}
BATCH_SIZE=${4:-1}
# Use nightly for Qwen3.5 support, fall back to managed for older models
if [[ "$MODEL_PATH" == *"Qwen3.5"* ]] && [ -f /scratch-shared/kverlaan/containers/vllm-nightly.sif ]; then
  CONTAINER=/scratch-shared/kverlaan/containers/vllm-nightly.sif
else
  CONTAINER=/projects/2/managed_datasets/containers/vllm/vllm_25.09.sif
fi

echo "=== INFRA METADATA ==="
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "GPUs: $NUM_GPUS"
echo "Model: $MODEL_PATH"
echo "Experiment: $EXPERIMENT"
echo "Start: $(date -Iseconds)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null

# Save infra metadata to JSON
cat > ~/origins/simulation/data/runs/infra_${SLURM_JOB_ID}.json << INFRA_EOF
{
  "slurm_job_id": "$SLURM_JOB_ID",
  "node": "$SLURM_NODELIST",
  "partition": "$SLURM_JOB_PARTITION",
  "num_gpus": $NUM_GPUS,
  "model_path": "$MODEL_PATH",
  "experiment": "$EXPERIMENT",
  "start_time": "$(date -Iseconds)",
  "gpu_info": "$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | tr '\n' '; ')"
}
INFRA_EOF

# Build model-specific vLLM flags
EXTRA_FLAGS=""
if [[ "$MODEL_PATH" == *"mimo"* ]]; then
  EXTRA_FLAGS="--generation-config vllm"
fi
if [[ "$MODEL_PATH" == *"gemma-3"* ]]; then
  EXTRA_FLAGS="--enforce-eager --dtype float16"
fi
if [[ "$MODEL_PATH" == *"gemma-2"* ]]; then
  # Gemma 2 uses logit softcapping unsupported by default Flash Attention
  # FlashInfer backend supports softcapping (vLLM docs + issue #7419)
  export VLLM_ATTENTION_BACKEND=FLASHINFER
fi
# Thinking models: use reasoning parser to separate thinking from content
if [[ "$MODEL_PATH" == *"qwq"* ]]; then
  EXTRA_FLAGS="$EXTRA_FLAGS --reasoning-parser deepseek_r1"
fi
if [[ "$MODEL_PATH" == *"Qwen3"* ]]; then
  # Qwen3/3.5: use qwen3 parser + text-only mode (skip vision encoder)
  # See: https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3.5.html
  EXTRA_FLAGS="$EXTRA_FLAGS --reasoning-parser qwen3 --language-model-only"
fi
if [[ "$MODEL_PATH" == *"Qwen3.5"* ]]; then
  # MTP speculative decoding: Qwen3.5 has native multi-token prediction heads
  # ~1.5-2.75x latency reduction per request (fewer decode steps)
  EXTRA_FLAGS="$EXTRA_FLAGS --speculative-config {\"method\":\"mtp\",\"num_speculative_tokens\":1}"
  # Disable async scheduling to fix prefix caching for DeltaNet/Mamba hybrid
  # See: github.com/vllm-project/vllm/pull/33352
  EXTRA_FLAGS="$EXTRA_FLAGS --no-async-scheduling"
fi

# Throughput settings: game engine sends 30 concurrent requests per round
# --enable-prefix-caching: all agents share game rules prefix (~300 tokens), computed once
# --max-num-seqs: allow all 30 agents to be processed concurrently
# --max-model-len: reasoning models need headroom (thinking + JSON response)
MAX_MODEL_LEN=16384
MAX_NUM_SEQS=32
if [[ "$MODEL_PATH" == *"Qwen3"* ]]; then
  # Reasoning models: ~2K prompt + ~8K thinking + ~200 response = ~10K
  # 16K gives headroom without wasting KV cache on unused context
  MAX_MODEL_LEN=16384
fi

# Start vLLM in background with bind-mount for model access
apptainer exec --nv \
  -B /scratch-shared/kverlaan:/scratch-shared/kverlaan \
  $CONTAINER \
  vllm serve $MODEL_PATH \
  --tensor-parallel-size $NUM_GPUS \
  --trust-remote-code \
  --port 8000 \
  --max-model-len $MAX_MODEL_LEN \
  --max-num-seqs $MAX_NUM_SEQS \
  --enable-prefix-caching \
  --gpu-memory-utilization 0.95 \
  --dtype auto \
  $EXTRA_FLAGS &

VLLM_PID=$!

# Wait for vLLM to be ready (up to 75 min for large models — Qwen3-235B FP8 needs ~60 min for 48 shards)
WAIT_ITERATIONS=900
echo "Waiting for vLLM to start (max $((WAIT_ITERATIONS*5/60)) min)..."
for i in $(seq 1 $WAIT_ITERATIONS); do
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

# Check if vLLM actually started
if ! curl -s http://localhost:8000/v1/models > /dev/null 2>&1; then
  echo "ERROR: vLLM failed to start within $((WAIT_ITERATIONS*5/60)) minutes"
  kill $VLLM_PID 2>/dev/null
  exit 1
fi

# Verify model loaded
curl -s http://localhost:8000/v1/models | python3 -m json.tool

# Run sweep (single run if array job, full sweep otherwise)
source ~/origins/venv/bin/activate
cd ~/origins/simulation

if [ -n "$SLURM_ARRAY_TASK_ID" ]; then
  RUN_INDEX=$(( SLURM_ARRAY_TASK_ID * BATCH_SIZE ))
  echo "Array task $SLURM_ARRAY_TASK_ID, run_index=$RUN_INDEX, batch_size=$BATCH_SIZE"
  PYTHONUNBUFFERED=1 python src/sweep.py $EXPERIMENT --run-index $RUN_INDEX --batch-size $BATCH_SIZE
else
  PYTHONUNBUFFERED=1 python src/sweep.py $EXPERIMENT
fi

EXIT_CODE=$?

# Update infra metadata with end time
python3 -c "
import json
f = 'data/runs/infra_${SLURM_JOB_ID}.json'
d = json.load(open(f))
d['end_time'] = '$(date -Iseconds)'
d['exit_code'] = $EXIT_CODE
json.dump(d, open(f, 'w'), indent=2)
"

echo "=== JOB COMPLETE (exit: $EXIT_CODE) ==="

# Cleanup
kill $VLLM_PID 2>/dev/null
