#!/bin/bash
set -e

REPLICATES=10
RUNTIMES=("node" "bun" "deno")
WORKLOADS=("w1_rest" "w3_ws")
MODES=("false" "true") # OTEL_ENABLED

mkdir -p benchmark_project/results/raw
mkdir -p benchmark_project/results/processed

echo "Starting Rigorous SCI-Level Evaluation (K=$REPLICATES)"

# 1. Cold Start Benchmark (W4)
echo "Running Cold Start Measurement..."
# We run 10 replicates in python script itself, good enough for cold start
python3 benchmark_project/experiments/measure_coldstart.py > "benchmark_project/results/raw/coldstart_results.csv"

# 2. Main Experiment Loop
for r in $(seq 1 $REPLICATES); do
    echo "=================================================="
    echo " GLOBAL REPLICATE BATCH: $r / $REPLICATES"
    echo "=================================================="

    # Construct a list of jobs to randomize
    # Format: "runtime workload mode"
    JOBS=()
    for workload in "${WORKLOADS[@]}"; do
        for runtime in "${RUNTIMES[@]}"; do
            for mode in "${MODES[@]}"; do
                JOBS+=("$runtime $workload $mode")
            done
        done
    done

    # Shuffle and Execute
    printf "%s\n" "${JOBS[@]}" | sort -R | while read -r RUNTIME WORKLOAD OTEL; do
        echo "--------------------------------------------------"
        echo "Executing: Runtime=$RUNTIME | Workload=$WORKLOAD | OTel=$OTEL | Rep=$r"
        ./benchmark_project/experiments/run_one.sh "$RUNTIME" "$r" "$WORKLOAD" "$OTEL"
        
        # Cool down/Cleanup to ensure stability
        sleep 5
    done
done
