import subprocess
import time
import subprocess
import time
import urllib.request
import urllib.error
import sys
import os
import statistics
import random

# Fixed configuration
REPLICATES = 50
TIMEOUT_SEC = 5
RUNTIMES = {
    'node': ['node', 'benchmark_project/services/node/server.js'],
    'bun': ['bun', 'benchmark_project/services/bun/server.ts'],
    'deno': ['deno', 'run', '--allow-net', '--allow-env', 'benchmark_project/services/deno/server.ts']
}

PORTS = {
    'node': 4000,
    'bun': 4001,
    'deno': 4002
}

def bootstrap_ci(data, n_boot=1000, ci=0.95):
    """Calculates bootstrap confidence interval for the mean."""
    if not data:
        return (0, 0)
    means = []
    n = len(data)
    for _ in range(n_boot):
        sample = [random.choice(data) for _ in range(n)]
        means.append(statistics.mean(sample))
    means.sort()
    lower_idx = int(n_boot * (1 - ci) / 2)
    upper_idx = int(n_boot * (1 + ci) / 2)
    return (means[lower_idx], means[upper_idx])

def measure_one(runtime, replicate):
    cmd = RUNTIMES[runtime]
    port = PORTS[runtime]
    url = f"http://localhost:{port}/health"
    
    env = os.environ.copy()
    env['PORT'] = str(port)
    
    # Start process
    start_time = time.time()
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    except Exception as e:
        return None

    success = False
    first_byte_time = 0
    
    # Poll
    while time.time() - start_time < TIMEOUT_SEC:
        try:
            with urllib.request.urlopen(url, timeout=0.1) as response:
                if response.status == 200:
                    first_byte_time = time.time()
                    success = True
                    break
        except Exception:
            time.sleep(0.01) # 10ms poll

    # Cleanup
    proc.terminate()
    try:
        proc.wait(timeout=1)
    except:
        proc.kill()
        
    if success:
        return (first_byte_time - start_time) * 1000
    return None

def main():
    print("runtime,replicate,cold_start_ms", flush=True)
    all_results = {r: [] for r in RUNTIMES}
    
    # Measurement Loop
    for r in range(REPLICATES):
        for runtime in RUNTIMES.keys():
            val = measure_one(runtime, r)
            if val is not None:
                all_results[runtime].append(val)
                print(f"{runtime},{r},{val:.2f}", flush=True)
            else:
                print(f"{runtime},{r},FAIL", flush=True)
                
            # Random sleep between runs to prevent thermal synchronization
            time.sleep(random.uniform(0.5, 1.5))

    # Statistical Summary
    print("\n--- STATISTICAL SUMMARY ---")
    print(f"{'Runtime':<10} {'N':<5} {'Mean':<10} {'Median':<10} {'StdDev':<10} {'95% CI (Mean)':<20}")
    for runtime, values in all_results.items():
        if len(values) < 2:
            print(f"{runtime:<10} {len(values):<5} N/A")
            continue
            
        mean_val = statistics.mean(values)
        median_val = statistics.median(values)
        stdev_val = statistics.stdev(values)
        ci_lower, ci_upper = bootstrap_ci(values)
        
        print(f"{runtime:<10} {len(values):<5} {mean_val:.2f}      {median_val:.2f}      {stdev_val:.2f}      [{ci_lower:.2f}, {ci_upper:.2f}]")

if __name__ == "__main__":
    main()
