#!/bin/bash
#SBATCH --job-name=sim_client
#SBATCH --partition=staging
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --time=04:00:00
#SBATCH --output=logs/sim_client_%j.out
#SBATCH --error=logs/sim_client_%j.err

# CPU-only client. Reads endpoint from ~/origins/simulation/.server_endpoint
# and runs a simulation against that vLLM server.
#
# Usage (pass via --export):
#   sbatch --export=ALL,GAME_CONFIG=config/pilot_params.yaml,API_CONFIG=config/vllm_gemma_config.yaml \
#          snellius/run_sim_client.sh

set -euo pipefail

GAME_CONFIG=${GAME_CONFIG:-config/pilot_params.yaml}
API_CONFIG=${API_CONFIG:-config/vllm_gemma_config.yaml}
ENDPOINT_FILE=~/origins/simulation/.server_endpoint

echo "=== SIM CLIENT ==="
echo "Job ID: $SLURM_JOB_ID"
echo "Game: $GAME_CONFIG"
echo "API:  $API_CONFIG"
echo "Start: $(date -Iseconds)"

cd ~/origins/simulation

echo "Waiting for server endpoint (up to 20 min)..."
for i in $(seq 1 240); do
  if [ -f "$ENDPOINT_FILE" ] && curl -s --max-time 5 "$(cat $ENDPOINT_FILE)/models" > /dev/null 2>&1; then
    break
  fi
  sleep 5
done

if [ ! -f $ENDPOINT_FILE ]; then
  echo "ERROR: server endpoint never materialised"
  exit 1
fi

export VLLM_BASE_URL=$(cat $ENDPOINT_FILE)
echo "Using vLLM endpoint: $VLLM_BASE_URL"

if ! curl -s --max-time 5 "$VLLM_BASE_URL/models" > /dev/null; then
  echo "ERROR: endpoint $VLLM_BASE_URL not reachable"
  exit 1
fi

source ~/origins/venv/bin/activate
RESUME_ARG=""
if [ -n "${RESUME:-}" ]; then
  RESUME_ARG="--resume $RESUME"
  echo "Resuming from: $RESUME"
fi

PYTHONUNBUFFERED=1 python src/main.py \
  --game $GAME_CONFIG \
  --api $API_CONFIG \
  --output data/runs \
  $RESUME_ARG

echo "=== CLIENT DONE at $(date -Iseconds) ==="
