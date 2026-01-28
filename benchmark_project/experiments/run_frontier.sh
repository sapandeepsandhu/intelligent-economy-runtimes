#!/bin/bash
set -e

# Configuration
RUNTIMES=("node" "bun" "deno")
VUS_LIST=(10 100 500 1000)
DURATION="20s"
RESULTS_DIR="benchmark_project/results/frontier"

mkdir -p "$RESULTS_DIR"

echo "timestamp,runtime,vus,otel,throughput_rps,p99_ms,failures" > "$RESULTS_DIR/frontier_summary.csv"

echo "=== Starting Frontier Landscape Sweep ==="

for OTEL in "false" "true"; do
    for RUNTIME in "${RUNTIMES[@]}"; do
        
        # 1. Start Server
        echo "Starting $RUNTIME server (OTel=$OTEL)..."
        export OTEL_ENABLED="$OTEL"
        
        LOG_FILE="$RESULTS_DIR/server_${RUNTIME}_otel${OTEL}.log"
        PID=""
        PORT=""
        
        if [ "$RUNTIME" == "node" ]; then
            node benchmark_project/services/node/server.js > "$LOG_FILE" 2>&1 &
            PID=$!
            PORT=3000
        elif [ "$RUNTIME" == "bun" ]; then
            export PATH=$HOME/.bun/bin:$PATH
            bun benchmark_project/services/bun/server.ts > "$LOG_FILE" 2>&1 &
            PID=$!
            PORT=3001
        elif [ "$RUNTIME" == "deno" ]; then
            export PATH=$HOME/.deno/bin:$PATH
            deno run --allow-net --allow-env benchmark_project/services/deno/server.ts > "$LOG_FILE" 2>&1 &
            PID=$!
            PORT=3002
        fi
        
        # Wait for Health
        RETRIES=0
        while ! curl -s "http://localhost:$PORT/health" > /dev/null; do
            sleep 1
            RETRIES=$((RETRIES+1))
            if [ "$RETRIES" -gt 15 ]; then
                echo "Server failed to start."
                kill $PID || true
                exit 1
            fi
        done
        
        # 2. Iterate VUs
        for VUS in "${VUS_LIST[@]}"; do
            echo "--> Benchmarking: $RUNTIME | OTel=$OTEL | VUs=$VUS"
            
            # Run k6
            export TARGET="$RUNTIME"
            export VUS="$VUS"
            export DURATION="$DURATION"
            
            SUMMARY_FILE="$RESULTS_DIR/k6_${RUNTIME}_otel${OTEL}_vus${VUS}.json"
            
            k6 run --out json="$RESULTS_DIR/raw_${RUNTIME}_otel${OTEL}_vus${VUS}.json" \
                   --summary-export "$SUMMARY_FILE" \
                   benchmark_project/loadgen/frontier_rest.js > /dev/null
                   
            # Extract Metrics using jq (if available) or python one-liner
            # We assume python3 is available since user has python scripts
            
            # Extract Metrics using helper script
            METRICS=$(python3 benchmark_project/experiments/parse_k6.py "$SUMMARY_FILE")
            
            TIMESTAMP=$(date +%s)
            echo "$TIMESTAMP,$RUNTIME,$VUS,$OTEL,$METRICS" >> "$RESULTS_DIR/frontier_summary.csv"
            
            # Short cooldown between VU steps
            sleep 2
        done
        
        # 3. Stop Server
        kill $PID || true
        wait $PID 2>/dev/null || true
        echo "Stopped $RUNTIME server."
        sleep 5
        
    done
done

echo "Frontier Sweep Complete. Data saved to $RESULTS_DIR/frontier_summary.csv"
