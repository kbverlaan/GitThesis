#!/bin/bash
# Auto-submit remaining 8 QwQ tasks when current batch finishes
# Indices: 60,61,62,63,80,81,82,83

cd ~/origins/simulation
LOG=~/origins/simulation/logs/auto_submit_batch2.log

echo "$(date -Iseconds) BATCH2: Waiting for current QwQ jobs to finish before submitting indices 60-63,80-83" >> $LOG

while true; do
    running=$(squeue -u kverlaan --name=arch_qwq -h -t RUNNING 2>/dev/null | wc -l)
    echo "$(date -Iseconds) QwQ running: $running" >> $LOG

    if [ "$running" -le 2 ]; then
        echo "$(date -Iseconds) Slots available ($running running). Submitting batch 60-63..." >> $LOG

        job1=$(sbatch --parsable --array=60-63 --gpus-per-node=1 --time=12:00:00 --job-name=arch_qwq \
            snellius/snellius_run.sh /scratch-shared/kverlaan/origins_models/qwq-32b \
            experiments/arch_combined_qwq_32b.yaml 1 1 2>&1)
        echo "$(date -Iseconds) Submitted job: $job1" >> $LOG

        sleep 30

        # Check if they survived
        cancelled=$(sacct -j $job1 --format=State -n 2>/dev/null | grep -c "CANCELLED")
        if [ "$cancelled" -gt 0 ]; then
            echo "$(date -Iseconds) WARNING: $cancelled tasks cancelled. Will retry." >> $LOG
            sleep 600
            continue
        fi

        echo "$(date -Iseconds) Batch 60-63 survived. Submitting 80-83..." >> $LOG

        job2=$(sbatch --parsable --array=80-83 --gpus-per-node=1 --time=12:00:00 --job-name=arch_qwq \
            snellius/snellius_run.sh /scratch-shared/kverlaan/origins_models/qwq-32b \
            experiments/arch_combined_qwq_32b.yaml 1 1 2>&1)
        echo "$(date -Iseconds) Submitted job: $job2" >> $LOG

        sleep 30

        cancelled2=$(sacct -j $job2 --format=State -n 2>/dev/null | grep -c "CANCELLED")
        if [ "$cancelled2" -gt 0 ]; then
            echo "$(date -Iseconds) WARNING: 80-83 cancelled. Will wait and retry when 60-63 finish." >> $LOG
            # Wait for 60-63 to finish, then retry
            while true; do
                r=$(squeue -u kverlaan --name=arch_qwq -h -t RUNNING 2>/dev/null | wc -l)
                echo "$(date -Iseconds) Waiting for 60-63 to finish. Running: $r" >> $LOG
                if [ "$r" -le 2 ]; then
                    job3=$(sbatch --parsable --array=80-83 --gpus-per-node=1 --time=12:00:00 --job-name=arch_qwq \
                        snellius/snellius_run.sh /scratch-shared/kverlaan/origins_models/qwq-32b \
                        experiments/arch_combined_qwq_32b.yaml 1 1 2>&1)
                    echo "$(date -Iseconds) Retry submitted: $job3" >> $LOG
                    break
                fi
                sleep 600
            done
        fi

        echo "$(date -Iseconds) ALL TASKS SUBMITTED. Done." >> $LOG
        break
    fi

    sleep 600
done
