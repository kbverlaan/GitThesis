#!/bin/bash
#SBATCH --job-name=origins-parallel
#SBATCH --partition=gpu_h100
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --time=12:00:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

# Parallel runner: launches N simulation runs staggered against a single vLLM instance.
# Each run is an independent sweep.py process. Staggered starts ensure GPU stays busy
# even when individual runs have retries or slow agents.
#
# Usage:
#   sbatch snellius/parallel_runs.sh <MODEL_PATH> <EXPERIMENT_YAML> [PARALLEL=2] [STAGGER_SEC=30]
#
# Example:
#   sbatch snellius/parallel_runs.sh /scratch-shared/kverlaan/origins_models/Qwen3.5-27B experiments/timing_benchmark.yaml 3 30
#
# How it works:
#   1. Starts vLLM with higher MAX_NUM_SEQS to handle concurrent runs
#   2. Launches PARALLEL sweep.py processes with staggered starts
#   3. Each process gets a different --run-index range (non-overlapping)
#   4. Waits for all to complete, reports exit codes
#
# Tuning PARALLEL:
#   - 30 agents/run → ~30 concurrent seqs per run
#   - PARALLEL=2 → ~60 seqs (safe, good GPU utilization)
#   - PARALLEL=3 → ~90 seqs (aggressive, may queue at vLLM level)
#   - For 10-agent runs: PARALLEL=4-5 is fine

MODEL_PATH=$1
EXPERIMENT=$2
PARALLEL=${3:-2}
STAGGER_SEC=${4:-0}

echo "=== PARALLEL RUNNER ==="
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "Model: $MODEL_PATH"
echo "Experiment: $EXPERIMENT"
echo "Parallel runs: $PARALLEL"
echo "Stagger: ${STAGGER_SEC}s between launches"
echo "Start: $(date -Iseconds)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null

# Save infra metadata
cat > ~/origins/simulation/data/runs/infra_${SLURM_JOB_ID}.json << INFRA_EOF
{
  "slurm_job_id": "$SLURM_JOB_ID",
  "node": "$SLURM_NODELIST",
  "partition": "$SLURM_JOB_PARTITION",
  "model_path": "$MODEL_PATH",
  "experiment": "$EXPERIMENT",
  "parallel_runs": $PARALLEL,
  "stagger_sec": $STAGGER_SEC,
  "start_time": "$(date -Iseconds)",
  "gpu_info": "$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | tr '\n' '; ')"
}
INFRA_EOF

# --- vLLM setup (same as snellius_run.sh) ---

if [[ "$MODEL_PATH" == *"Qwen3.5"* ]] && [ -f /scratch-shared/kverlaan/containers/vllm-nightly.sif ]; then
  CONTAINER=/scratch-shared/kverlaan/containers/vllm-nightly.sif
else
  CONTAINER=/projects/2/managed_datasets/containers/vllm/vllm_25.09.sif
fi

EXTRA_FLAGS=""
if [[ "$MODEL_PATH" == *"Qwen3"* ]]; then
  EXTRA_FLAGS="$EXTRA_FLAGS --reasoning-parser qwen3 --language-model-only"
fi
if [[ "$MODEL_PATH" == *"Qwen3.5"* ]]; then
  EXTRA_FLAGS="$EXTRA_FLAGS --speculative-config {\"method\":\"mtp\",\"num_speculative_tokens\":1}"
  EXTRA_FLAGS="$EXTRA_FLAGS --no-async-scheduling"
fi
if [[ "$MODEL_PATH" == *"qwq"* ]]; then
  EXTRA_FLAGS="$EXTRA_FLAGS --reasoning-parser deepseek_r1"
fi
if [[ "$MODEL_PATH" == *"gemma-3"* ]]; then
  EXTRA_FLAGS="$EXTRA_FLAGS --enforce-eager --dtype float16"
fi
if [[ "$MODEL_PATH" == *"gemma-2"* ]]; then
  export VLLM_ATTENTION_BACKEND=FLASHINFER
fi

# vLLM default=256, queues excess requests automatically via KV cache pressure.
# No need to scale with PARALLEL — vLLM scheduler handles backpressure.
MAX_NUM_SEQS=256
MAX_MODEL_LEN=16384

echo "vLLM config: MAX_NUM_SEQS=$MAX_NUM_SEQS, MAX_MODEL_LEN=$MAX_MODEL_LEN"

apptainer exec --nv \
  -B /scratch-shared/kverlaan:/scratch-shared/kverlaan \
  $CONTAINER \
  vllm serve $MODEL_PATH \
  --tensor-parallel-size 1 \
  --trust-remote-code \
  --port 8000 \
  --max-model-len $MAX_MODEL_LEN \
  --max-num-seqs $MAX_NUM_SEQS \
  --enable-prefix-caching \
  --gpu-memory-utilization 0.95 \
  --dtype auto \
  $EXTRA_FLAGS &

VLLM_PID=$!

# Wait for vLLM
WAIT_ITERATIONS=900
echo "Waiting for vLLM to start..."
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

if ! curl -s http://localhost:8000/v1/models > /dev/null 2>&1; then
  echo "ERROR: vLLM failed to start"
  kill $VLLM_PID 2>/dev/null
  exit 1
fi

curl -s http://localhost:8000/v1/models | python3 -m json.tool

# --- Launch parallel runs ---

source ~/origins/venv/bin/activate
cd ~/origins/simulation

PIDS=()
for i in $(seq 0 $(( PARALLEL - 1 ))); do
  RUN_INDEX=$i
  BATCH_SIZE=1

  if [ $i -gt 0 ]; then
    echo "Staggering: sleeping ${STAGGER_SEC}s before run $i..."
    sleep $STAGGER_SEC
  fi

  echo "=== Launching run $i (run_index=$RUN_INDEX) at $(date -Iseconds) ==="
  PYTHONUNBUFFERED=1 python src/sweep.py $EXPERIMENT \
    --run-index $RUN_INDEX \
    --batch-size $BATCH_SIZE \
    > logs/parallel_run_${SLURM_JOB_ID}_${i}.log 2>&1 &

  PIDS+=($!)
  echo "  PID: ${PIDS[-1]}"
done

echo ""
echo "=== All $PARALLEL runs launched. PIDs: ${PIDS[*]} ==="
echo "Waiting for completion..."

# Wait for all runs and collect exit codes
EXIT_CODES=()
for i in $(seq 0 $(( PARALLEL - 1 ))); do
  wait ${PIDS[$i]}
  EXIT_CODES+=($?)
  echo "Run $i (PID ${PIDS[$i]}) finished with exit code ${EXIT_CODES[-1]} at $(date -Iseconds)"
done

# Report
echo ""
echo "=== ALL RUNS COMPLETE ==="
FAILURES=0
for i in $(seq 0 $(( PARALLEL - 1 ))); do
  STATUS="OK"
  if [ ${EXIT_CODES[$i]} -ne 0 ]; then
    STATUS="FAILED (exit ${EXIT_CODES[$i]})"
    FAILURES=$(( FAILURES + 1 ))
  fi
  echo "  Run $i: $STATUS"
done

# Update infra metadata
python3 -c "
import json
f = 'data/runs/infra_${SLURM_JOB_ID}.json'
d = json.load(open(f))
d['end_time'] = '$(date -Iseconds)'
d['exit_codes'] = [${EXIT_CODES[*]}]
d['failures'] = $FAILURES
json.dump(d, open(f, 'w'), indent=2)
"

echo "=== JOB COMPLETE ($FAILURES failures) ==="

kill $VLLM_PID 2>/dev/null

exit $FAILURES
