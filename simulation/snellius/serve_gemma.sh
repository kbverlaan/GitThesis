#!/bin/bash
#SBATCH --job-name=serve_gemma
#SBATCH --partition=gpu_h100
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --time=06:00:00
#SBATCH --cpus-per-task=4
#SBATCH --output=logs/serve_gemma_%j.out
#SBATCH --error=logs/serve_gemma_%j.err

# Long-lived vLLM server for Gemma 4 31B.
# Writes endpoint to ~/origins/simulation/.server_endpoint so clients can find it.
# Keeps GPU held until time limit or scancel.

MODEL_PATH=/scratch-shared/kverlaan/origins_models/Gemma4-31B
CONTAINER=/scratch-shared/kverlaan/containers/vllm-nightly.sif
ENDPOINT_FILE=~/origins/simulation/.server_endpoint

echo "=== SERVE Gemma 4 ==="
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "Start: $(date -Iseconds)"

cd ~/origins/simulation
mkdir -p logs

HOSTNAME_FQ=$(hostname)
PORT=8000

apptainer exec --nv \
  -B /scratch-shared/kverlaan:/scratch-shared/kverlaan \
  $CONTAINER \
  vllm serve $MODEL_PATH \
  --tensor-parallel-size 1 \
  --trust-remote-code \
  --host 0.0.0.0 \
  --port $PORT \
  --max-model-len 32768 \
  --max-num-seqs 32 \
  --gpu-memory-utilization 0.95 \
  --dtype bfloat16 \
  --reasoning-parser gemma4 &

VLLM_PID=$!

# Wait for readiness, then publish endpoint
echo "Waiting for vLLM..."
for i in $(seq 1 180); do
  if curl -s http://localhost:$PORT/v1/models > /dev/null 2>&1; then
    echo "vLLM ready after $((i*5))s on $HOSTNAME_FQ:$PORT"
    echo "http://$HOSTNAME_FQ:$PORT/v1" > $ENDPOINT_FILE
    break
  fi
  if ! kill -0 $VLLM_PID 2>/dev/null; then
    echo "ERROR: vLLM died during startup"
    rm -f $ENDPOINT_FILE
    exit 1
  fi
  sleep 5
done

if [ ! -f $ENDPOINT_FILE ]; then
  echo "ERROR: vLLM never became ready"
  kill $VLLM_PID 2>/dev/null
  exit 1
fi

echo "Endpoint published: $(cat $ENDPOINT_FILE)"

# Stay alive until vLLM dies or the job is cancelled
wait $VLLM_PID
echo "vLLM exited at $(date -Iseconds)"
rm -f $ENDPOINT_FILE
