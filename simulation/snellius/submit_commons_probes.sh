#!/bin/bash
#SBATCH --job-name=commons_probes
#SBATCH --partition=gpu_h100
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --time=05:00:00
#SBATCH --cpus-per-task=16
#SBATCH --output=/home/kverlaan/origins/simulation/logs/iso_%x_%j.out
#SBATCH --error=/home/kverlaan/origins/simulation/logs/iso_%x_%j.err

# COMMONS DESIGN PROBES: 1 run each of 5 commons configs to PICK the fixed L4
# commons configuration (then the ladder OFAT sweeps g_inv only).
#   P1 commons_p1_action   harvest-as-ACTION, regen 2.0, start full   (isolate option i)
#   P2 commons_p2_fragile  parallel field,    regen 1.5, start MSY=60  (isolate ii+iii)
#   P3 commons_p3_full     harvest-as-ACTION, regen 1.5, start MSY=60  (full)
#   R1 commons_p4_regen10  harvest-as-ACTION, regen 1.0, start MSY=60  (no regrowth)
#   R2 commons_p5_regen075 harvest-as-ACTION, regen 0.75, start MSY=60 (sub-renewable)
set -u
CELLS=("commons_p1_action" "commons_p2_fragile" "commons_p3_full" "commons_p4_regen10" "commons_p5_regen075")
RUNS_PER="${1:-1}"
MAXC="${2:-2}"

MODEL_PATH=/scratch-shared/kverlaan/origins_models/Gemma4-31B
CONTAINER=/scratch-shared/kverlaan/containers/vllm-nightly.sif
API_CONFIG=config/vllm_gemma_config.yaml

echo "=== COMMONS-PROBES: ${#CELLS[@]} cells x ${RUNS_PER} run, max ${MAXC} concurrent ==="
echo "Job: $SLURM_JOB_ID / Node: $SLURM_NODELIST / Start: $(date -Iseconds)"
cd ~/origins/simulation
mkdir -p logs
for CELL in "${CELLS[@]}"; do
  [ -f "config/${CELL}.yaml" ] || { echo "ERROR: config/${CELL}.yaml not found"; exit 1; }
  mkdir -p "data/runs/${CELL}" "data/runs/${CELL}/checkpoints"
done

apptainer exec --nv -B /scratch-shared/kverlaan:/scratch-shared/kverlaan $CONTAINER \
  vllm serve $MODEL_PATH --tensor-parallel-size 1 --trust-remote-code --port 8000 \
  --max-model-len 65536 --max-num-seqs 48 --gpu-memory-utilization 0.95 \
  --dtype bfloat16 --quantization fp8 --reasoning-parser gemma4 &
VLLM_PID=$!

echo "Waiting for vLLM..."
for i in $(seq 1 240); do
  curl -s http://localhost:8000/v1/models >/dev/null 2>&1 && { echo "vLLM ready after $((i*5))s"; break; }
  kill -0 $VLLM_PID 2>/dev/null || { echo "ERROR: vLLM died"; exit 1; }
  sleep 5
done
curl -s http://localhost:8000/v1/models >/dev/null 2>&1 || { echo "ERROR: vLLM not up"; kill $VLLM_PID; exit 1; }

source ~/origins/venv/bin/activate

pids=()
reap() {
  [ "${#pids[@]}" -eq 0 ] && return 0
  local alive=() p
  for p in "${pids[@]}"; do kill -0 "$p" 2>/dev/null && alive+=("$p"); done
  pids=()
  [ "${#alive[@]}" -gt 0 ] && pids=("${alive[@]}")
}

for CELL in "${CELLS[@]}"; do
  for r in $(seq 1 ${RUNS_PER}); do
    while reap; [ "${#pids[@]}" -ge ${MAXC} ]; do sleep 10; done
    RID="${SLURM_JOB_ID}_${CELL}_r${r}"
    echo "[${CELL}] launch run ${r}/${RUNS_PER} run_id=${RID} $(date -Iseconds)"
    ( PYTHONUNBUFFERED=1 python src/main.py --game config/${CELL}.yaml --api ${API_CONFIG} \
        --label ${CELL} --run-id ${RID}
      echo "[${CELL}] run ${r} exit=$? $(date -Iseconds)" ) &
    pids+=("$!")
    sleep 3
  done
done

DEADLINE=$(( $(date +%s) + 16200 ))
if [ "${#pids[@]}" -gt 0 ]; then
  for p in "${pids[@]}"; do
    while kill -0 "$p" 2>/dev/null; do
      [ "$(date +%s)" -ge "$DEADLINE" ] && { echo "WARNING: deadline hit, killing clients $(date -Iseconds)"; kill "${pids[@]}" 2>/dev/null; break 2; }
      sleep 15
    done
  done
fi

kill $VLLM_PID 2>/dev/null
for CELL in "${CELLS[@]}"; do
  echo "=== ${CELL} DONE: $(ls data/runs/${CELL}/*_log.jsonl 2>/dev/null | wc -l) runs ==="
done
echo "=== ALL DONE $(date -Iseconds) ==="
