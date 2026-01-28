#!/bin/bash
set -e

RUNTIME=$1
REPLICATE=$2
WORKLOAD=${3:-"w1_rest"}
OTEL_ENABLED=${4:-"false"}
DURATION="1m"

DATA_DIR="benchmark_project/results/raw/${RUNTIME}_${WORKLOAD}_${REPLICATE}_otel${OTEL_ENABLED}"
mkdir -p "$DATA_DIR"

echo "=== Starting Experiment: Runtime=$RUNTIME, Workload=$WORKLOAD, Replicate=$REPLICATE, OTel=$OTEL_ENABLED ==="

# 1. Start Server
echo "Starting $RUNTIME server..."
# Export env for children
export OTEL_ENABLED="$OTEL_ENABLED"

PID=""
if [ "$RUNTIME" == "node" ]; then
  node benchmark_project/services/node/server.js > "$DATA_DIR/server.log" 2>&1 &
  PID=$!
  PORT=3000
elif [ "$RUNTIME" == "bun" ]; then
  # Ensure bun is in path
  export PATH=$HOME/.bun/bin:$PATH
  bun benchmark_project/services/bun/server.ts > "$DATA_DIR/server.log" 2>&1 &
  PID=$!
  PORT=3001
elif [ "$RUNTIME" == "deno" ]; then
  # Ensure deno is in path
  export PATH=$HOME/.deno/bin:$PATH
  deno run --allow-net --allow-env benchmark_project/services/deno/server.ts > "$DATA_DIR/server.log" 2>&1 &
  PID=$!
  PORT=3002
else
  echo "Unknown runtime: $RUNTIME"
  exit 1
fi

echo "Server PID: $PID"

# 2. Wait for Health
echo "Waiting for health check on port $PORT..."
RETRIES=0
while ! curl -s "http://localhost:$PORT/health" > /dev/null; do
  sleep 1
  RETRIES=$((RETRIES+1))
  if [ "$RETRIES" -gt 15 ]; then
    echo "Server failed to start."
    cat "$DATA_DIR/server.log"
    kill $PID || true
    exit 1
  fi
done
echo "Server is up."

# 3. Run Load Test
echo "Running k6 for $WORKLOAD..."
# Pass target via env var
export TARGET="$RUNTIME"

SCRIPT="benchmark_project/loadgen/script.js"
if [ "$WORKLOAD" == "w3_ws" ]; then
  SCRIPT="benchmark_project/loadgen/w3_ws.js"
fi

k6 run --out json="$DATA_DIR/k6_metrics.json" --out csv="$DATA_DIR/k6_metrics.csv" --summary-export "$DATA_DIR/k6_summary.json" "$SCRIPT" > "$DATA_DIR/k6.log" 2>&1

# 4. Cleanup
echo "Stopping server $PID..."
kill $PID || true
wait $PID 2>/dev/null || true

echo "Experiment finished."
