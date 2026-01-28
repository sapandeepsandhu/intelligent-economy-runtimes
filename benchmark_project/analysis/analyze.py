import json
import pandas as pd
import glob
import os
import sys

def parse_k6_json(filepath):
    """Parses k6 JSON output (one JSON object per line)"""
    data = []
    with open(filepath, 'r') as f:
        for line in f:
            try:
                entry = json.loads(line)
                if entry['type'] == 'Point' and entry['metric'] == 'http_req_duration':
                     # entry['data']['value'] is the duration in ms
                     # entry['data']['tags'] contains status, url, etc.
                     data.append({
                         'timestamp': entry['data']['time'],
                         'duration': entry['data']['value'],
                         'status': entry['data']['tags'].get('status'),
                         'name': entry['data']['tags'].get('name')
                     })
            except:
                pass
    return pd.DataFrame(data)

def analyze_replicate(runtime, workload, replicate):
    path = f"benchmark_project/results/raw/{runtime}_{workload}_{replicate}/k6_metrics.json"
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return None

    df = parse_k6_json(path)
    if df.empty:
        print(f"No data for {runtime} {workload} {replicate}")
        return None

    # Filter warmup/cooldown if needed (k6 script has stages, we can use timestamp)
    # For now, just analyze all
    
    stats = {
        'runtime': runtime,
        'workload': workload,
        'replicate': replicate,
        'count': len(df),
        'mean': df['duration'].mean(),
        'p50': df['duration'].quantile(0.50),
        'p95': df['duration'].quantile(0.95),
        'p99': df['duration'].quantile(0.99),
        'max': df['duration'].max(),
        'error_rate': (df['status'] != '200').mean()
    }
    return stats

if __name__ == "__main__":
    results = []
    # Find all result dirs
    dirs = glob.glob("benchmark_project/results/raw/*")
    for d in dirs:
        if not os.path.isdir(d):
            continue
        parts = os.path.basename(d).split('_')
        # runtime_workload_replicate, but workload might have underscores
        # assumption: runtime is first, replicate is last
        runtime = parts[0]
        replicate = parts[-1]
        workload = "_".join(parts[1:-1])
        
        stats = analyze_replicate(runtime, workload, replicate)
        if stats:
            results.append(stats)
            
    df_res = pd.DataFrame(results)
    print(df_res.to_string())
    df_res.to_csv("benchmark_project/results/processed/summary.csv", index=False)
