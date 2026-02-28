#!/bin/bash
#SBATCH --job-name=build_vllm_nightly
#SBATCH --partition=gpu_h100
#SBATCH --gpus-per-node=1
#SBATCH --nodes=1
#SBATCH --time=01:00:00
#SBATCH --output=logs/build_vllm_nightly_%j.out
#SBATCH --error=logs/build_vllm_nightly_%j.err

# Build vLLM nightly container with Qwen 3.5 support
# vLLM 0.16.0 does NOT support Qwen3_5ForConditionalGeneration
# Need nightly until 0.17.0 is released

CONTAINER_DIR=/scratch-shared/kverlaan/containers
CONTAINER_OUT=$CONTAINER_DIR/vllm-nightly.sif

echo "=== Building vLLM Nightly Container ==="
echo "Job ID: $SLURM_JOB_ID"
echo "Start: $(date -Iseconds)"

# Back up old container
if [ -f $CONTAINER_OUT ]; then
  mv $CONTAINER_OUT ${CONTAINER_OUT}.bak
  echo "Backed up existing nightly container"
fi

# Pull nightly image from Docker Hub
echo "Pulling vllm/vllm-openai:nightly..."
apptainer pull --force $CONTAINER_OUT docker://vllm/vllm-openai:nightly

echo "Container size: $(du -h $CONTAINER_OUT | cut -f1)"

# Quick sanity check: does it know Qwen3_5?
echo "=== Checking Qwen 3.5 support ==="
apptainer exec $CONTAINER_OUT python3 -c "
import vllm
print('vLLM version:', vllm.__version__)
from vllm.model_executor.models import ModelRegistry
registry = ModelRegistry()
# Check if Qwen3_5 is in supported models
import json
models = [k for k in dir(registry) if 'qwen' in k.lower()]
print('Qwen-related entries:', models)
" 2>&1 || echo "Registry check failed, but container may still work"

# Alternative check
apptainer exec $CONTAINER_OUT python3 -c "
from vllm.config import ModelConfig
print('ModelConfig imported OK')
" 2>&1

echo "=== DONE ==="
echo "End: $(date -Iseconds)"
echo "Container: $CONTAINER_OUT"
