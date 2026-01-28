import os
import json
import pandas as pd
import numpy as np
import glob
from scipy.stats import mannwhitneyu

RAW_DIR = "benchmark_project/results/raw"
PROCESSED_DIR = "benchmark_project/results/processed"
SLO_THRESHOLD_MS = 200
BASE_RUNTIME = "node"

def load_data():
    records = []
    # Pattern: runtime_workload_replicate_otel[true/false]
    dirs = glob.glob(os.path.join(RAW_DIR, "*"))
    for d in dirs:
        if not os.path.isdir(d): continue
        dirname = os.path.basename(d)
        parts = dirname.split('_')
        # Expect: runtime_workload_replicate_otelMode
        # handle variable length?
        # node_w1_rest_1_otelfalse -> 5 parts
        # node_w3_ws_1_otelfalse -> 5 parts
        
        # Robust parsing?
        # runtime is first
        # otel is last part "oteltrue" or "otelfalse"
        # replicate is second to last
        # middle is workload
        
        if len(parts) < 4: continue
        
        runtime = parts[0]
        otel_part = parts[-1]
        replicate = parts[-2]
        workload = "_".join(parts[1:-2])
        
        otel_enabled = "true" in otel_part
        
        # Load k6 JSON
        # Load k6 Summary JSON
        json_path = os.path.join(d, "k6_summary.json")
        
        if not os.path.exists(json_path): continue
        
        try:
            with open(json_path) as f:
                data = json.load(f)
                
            metrics = data.get('metrics', {})
            
            throughput = 0
            p95 = 0
            p99 = 0
            error_rate = 0
            
            # Throughput
            if 'http_reqs' in metrics:
                # k6 summary usually has 'rate' inside the metric object
                throughput = metrics['http_reqs'].get('rate', 0)
                if 'http_req_failed' in metrics:
                    error_rate = metrics['http_req_failed'].get('rate', 0)
            elif 'ws_msgs_sent' in metrics:
                throughput = metrics['ws_msgs_sent'].get('rate', 0)
                
            # Latency
            if 'http_req_duration' in metrics:
                # Summary format: "p(95)", "p(99)"
                # Sometimes it's "values" -> "p(95)" depending on k6 version/config
                # Standard summary export is direct keys.
                vals = metrics['http_req_duration']
                if 'values' in vals: vals = vals['values'] # Handle potential nesting
                
                p95 = vals.get('p(95)', 0)
                p99 = vals.get('p(99)', 0)
            
            records.append({
                'runtime': runtime,
                'workload': workload,
                'replicate': int(replicate),
                'otel': otel_enabled,
                'throughput': throughput,
                'p95': p95,
                'p99': p99,
                'error_rate': error_rate
            })
            
        except Exception as e:
            print(f"Error processing {d}: {e}")
            
    return pd.DataFrame(records)

def compute_stats(df):
    # Group by (runtime, workload, otel)
    summary = []
    
    grouped = df.groupby(['runtime', 'workload', 'otel'])
    
    for name, group in grouped:
        runtime, workload, otel = name
        
        # Bootstrap CI for Mean (Throughput)
        throughput_vals = group['throughput'].values
        if len(throughput_vals) > 0:
            res_th = np.mean(throughput_vals) # Simple mean for now, bootstrap if time
            th_std = np.std(throughput_vals)
        else:
            res_th, th_std = 0, 0
            
        # Bootstrap CI for Median/Mean (p99)
        p99_vals = group['p99'].values
        if len(p99_vals) > 0:
            res_p99 = np.mean(p99_vals) 
            p99_std = np.std(p99_vals)
        else:
            res_p99, p99_std = 0, 0
            
        # Cost / SLO
        # SLO met?
        slo_met_count = np.sum(p99_vals <= SLO_THRESHOLD_MS)
        slo_rate = slo_met_count / len(p99_vals) if len(p99_vals) > 0 else 0
        
        # Valid throughput (throughput * slo_met?) - No, T_SLO = T * 1(p99 < tau)
        # Here we average over replicates.
        t_slo_vals = throughput_vals * (p99_vals <= SLO_THRESHOLD_MS).astype(int)
        avg_t_slo = np.mean(t_slo_vals) if len(t_slo_vals) > 0 else 0
        
        # Cost placeholder (normalized)
        # Assume Cost is constant 1.0 per unit time per runtime for fair comparison
        cost_per_success = 1.0 / avg_t_slo if avg_t_slo > 0 else float('inf')
        
        summary.append({
            'runtime': runtime,
            'workload': workload,
            'otel': otel,
            'N': len(group),
            'throughput_mean': res_th,
            'throughput_std': th_std,
            'p99_mean': res_p99,
            'p99_std': p99_std,
            'cost_per_success': cost_per_success
        })
        
    return pd.DataFrame(summary)

def generate_latex(df):
    # Filter for Table 1: W1 REST (No OTel)
    w1 = df[(df['workload'] == 'w1_rest') & (df['otel'] == False)]
    
    print("\\begin{table}[htbp]")
    print("\\caption{W1 REST Performance (K=10)}")
    print("\\begin{center}")
    print("\\begin{tabular}{lcccc}")
    print("\\toprule")
    print("Runtime & Throughput (req/s) & p99 (ms) & Cost/Success \\\\")
    print("\\midrule")
    
    for _, row in w1.iterrows():
        print(f"{row['runtime']} & {row['throughput_mean']:.2f} $\\pm$ {row['throughput_std']:.2f} & {row['p99_mean']:.2f} $\\pm$ {row['p99_std']:.2f} & {row['cost_per_success']:.4f} \\\\")
        
    print("\\bottomrule")
    print("\\end{tabular}")
    print("\\end{center}")
    print("\\end{table}")

if __name__ == "__main__":
    df = load_data()
    if not df.empty:
        stats = compute_stats(df)
        print("=== SUMMARY STATS ===")
        print(stats)
        print("\n=== LATEX TABLES ===")
        generate_latex(stats)
        
        # Save to processed
        if not os.path.exists(PROCESSED_DIR): os.makedirs(PROCESSED_DIR)
        stats.to_csv(os.path.join(PROCESSED_DIR, "summary_stats.csv"))
    else:
        print("No metrics found.")
