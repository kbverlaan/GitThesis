#!/bin/bash
#SBATCH --job-name=build_vllm
#SBATCH --partition=genoa
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=48
#SBATCH --time=01:00:00
#SBATCH --output=logs/build_vllm_%j.out
#SBATCH --error=logs/build_vllm_%j.err

# Build latest vLLM container with Qwen3.5 support
VLLM_IMAGE="vllm/vllm-openai:latest"
OUTPUT_PATH=/scratch-shared/$USER/containers/
VLLM_IMAGE_NAME="vllm-latest.sif"

mkdir -p $OUTPUT_PATH

APPTAINER_CACHEDIR=/dev/shm/$USER/
APPTAINER_TMPDIR=/dev/shm/$USER/
mkdir -p $APPTAINER_CACHEDIR $APPTAINER_TMPDIR

cat > /tmp/vllm_latest.def <<EOF
Bootstrap: docker
From: $VLLM_IMAGE

%environment
    export CUDA_HOME=/usr/local/cuda
    export LD_LIBRARY_PATH=/usr/local/cuda/lib64
    export PYTHONNOUSERSITE=1
    export LD_PRELOAD=

%post
    # Ensure latest transformers for Qwen3.5 support
    pip install --upgrade transformers
EOF

echo "Building container from $VLLM_IMAGE..."
echo "Output: $OUTPUT_PATH/$VLLM_IMAGE_NAME"
echo "Start: $(date -Iseconds)"

APPTAINER_CACHEDIR=$APPTAINER_CACHEDIR APPTAINER_TMPDIR=$APPTAINER_TMPDIR \
  apptainer build $OUTPUT_PATH/$VLLM_IMAGE_NAME /tmp/vllm_latest.def

echo "Done: $(date -Iseconds)"
echo "Container size: $(du -sh $OUTPUT_PATH/$VLLM_IMAGE_NAME)"
