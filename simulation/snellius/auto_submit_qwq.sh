#!/bin/bash
# Auto-submit remaining QwQ tasks as GPU slots free up
# Runs in background on Snellius, checks every 10 minutes
#
# Remaining tasks needed (4 reps per framing):
#   Cooperative (cond 1): indices 20,21,22,23
#   Competitive (cond 2): indices 41,43
#   Strategic (cond 3): indices 60,61,62,63
#   Cautious (cond 4): indices 80,81,82,83

cd ~/origins/simulation

REMAINING_INDICES=(20 21 22 23 41 43 60 61 62 63 80 81 82 83)
MAX_CONCURRENT=15  # Max total arch_* jobs running at once
BATCH_SIZE=5       # Submit this many at a time
LOG=~/origins/simulation/logs/auto_submit.log

echo "$(date -Iseconds) AUTO-SUBMIT started. ${#REMAINING_INDICES[@]} tasks to submit." >> $LOG

submitted=()

while true; do
    # Count currently running arch_* jobs
    running=$(squeue -u kverlaan --name=arch_gemma2,arch_qwq -h -t RUNNING 2>/dev/null | wc -l)
    pending=$(squeue -u kverlaan --name=arch_gemma2,arch_qwq -h -t PENDING 2>/dev/null | wc -l)

    echo "$(date -Iseconds) Running: $running, Pending: $pending, Submitted so far: ${#submitted[@]}/${#REMAINING_INDICES[@]}" >> $LOG

    # Find indices not yet submitted
    to_submit=()
    for idx in "${REMAINING_INDICES[@]}"; do
        already=false
        for s in "${submitted[@]}"; do
            if [ "$s" = "$idx" ]; then
                already=true
                break
            fi
        done
        if [ "$already" = false ]; then
            to_submit+=($idx)
        fi
    done

    # All done?
    if [ ${#to_submit[@]} -eq 0 ]; then
        echo "$(date -Iseconds) All tasks submitted! Exiting." >> $LOG
        break
    fi

    # Calculate available slots
    total_jobs=$((running + pending))
    available=$((MAX_CONCURRENT - total_jobs))

    if [ $available -gt 0 ]; then
        # Submit up to BATCH_SIZE or available slots
        count=$BATCH_SIZE
        if [ $available -lt $count ]; then
            count=$available
        fi
        if [ ${#to_submit[@]} -lt $count ]; then
            count=${#to_submit[@]}
        fi

        # Build array string for sbatch
        array_str=""
        for ((i=0; i<count; i++)); do
            if [ -n "$array_str" ]; then
                array_str="${array_str},${to_submit[$i]}"
            else
                array_str="${to_submit[$i]}"
            fi
            submitted+=(${to_submit[$i]})
        done

        echo "$(date -Iseconds) Submitting array=$array_str ($count tasks, $available slots available)" >> $LOG

        job_id=$(sbatch --parsable \
            --array=$array_str \
            --gpus-per-node=1 \
            --time=12:00:00 \
            --job-name=arch_qwq \
            snellius/snellius_run.sh \
            /scratch-shared/kverlaan/origins_models/qwq-32b \
            experiments/arch_combined_qwq_32b.yaml 1 1 2>&1)

        echo "$(date -Iseconds) Submitted job: $job_id" >> $LOG

        # Wait 60s and check if they survived
        sleep 60

        # Check if any were cancelled
        cancelled=$(sacct -j $job_id --format=State -n 2>/dev/null | grep -c "CANCELLED")
        if [ "$cancelled" -gt 0 ]; then
            echo "$(date -Iseconds) WARNING: $cancelled tasks cancelled! Reducing MAX_CONCURRENT." >> $LOG
            MAX_CONCURRENT=$((running - 1))
            if [ $MAX_CONCURRENT -lt 1 ]; then
                MAX_CONCURRENT=1
            fi
            echo "$(date -Iseconds) New MAX_CONCURRENT: $MAX_CONCURRENT. Will retry when slots free up." >> $LOG
            # Remove cancelled indices from submitted so they get retried
            for ((i=count-1; i>=0; i--)); do
                task_state=$(sacct -j ${job_id}_${to_submit[$i]} --format=State -n 2>/dev/null | head -1 | tr -d ' ')
                if [ "$task_state" = "CANCELLED+" ] || [ "$task_state" = "CANCELLED" ]; then
                    # Remove from submitted array
                    new_submitted=()
                    for s in "${submitted[@]}"; do
                        if [ "$s" != "${to_submit[$i]}" ]; then
                            new_submitted+=($s)
                        fi
                    done
                    submitted=("${new_submitted[@]}")
                fi
            done
        else
            echo "$(date -Iseconds) All $count tasks survived fairshare check." >> $LOG
        fi
    else
        echo "$(date -Iseconds) No slots available (total_jobs=$total_jobs >= MAX_CONCURRENT=$MAX_CONCURRENT). Waiting..." >> $LOG
    fi

    # Wait 10 minutes before next check
    sleep 600
done

echo "$(date -Iseconds) AUTO-SUBMIT complete. Total submitted: ${#submitted[@]}" >> $LOG
