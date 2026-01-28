import csv
import sys
import math
import statistics
import os
import random

# Configuration
FRONTIER_FILE = 'benchmark_project/results/frontier/frontier_summary.csv'
COLDSTART_FILE = 'benchmark_project/results/raw/coldstart_results.csv'
SLO_THRESHOLD_MS = 200

def load_frontier_data():
    data = []
    if not os.path.exists(FRONTIER_FILE):
        print(f"Warning: {FRONTIER_FILE} not found.")
        return data
        
    with open(FRONTIER_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # columns: timestamp,runtime,vus,otel,throughput_rps,p99_ms,failures
            row['vus'] = int(row['vus'])
            row['throughput_rps'] = float(row['throughput_rps'])
            row['p99_ms'] = float(row['p99_ms'])
            row['failures'] = float(row['failures'])
            data.append(row)
    return data

def calculate_cpss(data):
    # Cost Per Success = 1 / (Throughput * Indicator(p99 <= SLO))
    # We aggregate by runtime and OTel mode, finding the max stable throughput
    
    summary = {} # key: (runtime, otel) -> max_stable_rps
    
    for row in data:
        key = (row['runtime'], row['otel'])
        if row['p99_ms'] <= SLO_THRESHOLD_MS:
            current_max = summary.get(key, 0)
            if row['throughput_rps'] > current_max:
                summary[key] = row['throughput_rps']
        else:
            if key not in summary:
                summary[key] = 0 # Failed SLO at all measured points so far
                
    print("\n--- ECONOMIC ANALYSIS (SLO < 200ms) ---")
    print(f"{'Runtime':<10} {'OTel':<8} {'Max Stable RPS':<15} {'Cost Per Success (1/T)':<25}")
    
    for (runtime, o), rps in summary.items():
        cpss = 1.0 / rps if rps > 0 else float('inf')
        cpss_str = f"{cpss:.6f}" if rps > 0 else "SLO VIOLATION"
        print(f"{runtime:<10} {o:<8} {rps:<15.2f} {cpss_str:<25}")
        
    return summary

def analyze_otel_impact(data):
    # Comparse max RPS at measured VUs between OTel=false and true
    # This is tricky because VUs are discrete. We can compare at same VUs.
    
    print("\n--- OTEL OVERHEAD ANALYSIS ---")
    
    # Organize by runtime -> vus -> {false: p99, true: p99}
    comparison = {}
    
    for row in data:
        r = row['runtime']
        v = row['vus']
        o = row['otel']
        
        if r not in comparison: comparison[r] = {}
        if v not in comparison[r]: comparison[r][v] = {}
        
        comparison[r][v][o] = row['p99_ms']
        
    print(f"{'Runtime':<10} {'VUs':<5} {'No-OTel (ms)':<15} {'OTel (ms)':<15} {'Delta (%)':<10}")
    
    for r, vus_map in comparison.items():
        for vus, modes in vus_map.items():
            if 'false' in modes and 'true' in modes:
                base = modes['false']
                otel = modes['true']
                if base > 0:
                    delta = ((otel - base) / base) * 100
                    print(f"{r:<10} {vus:<5} {base:<15.2f} {otel:<15.2f} +{delta:.1f}%")

def generate_latex_cpss(summary):
    print("\n% --- LaTeX Table: Frontier CPSS ---")
    print(r"\begin{table}[htbp]")
    print(r"\caption{Economic Efficiency: Cost Per Success ($SLO \le 200ms$)}")
    print(r"\begin{center}")
    print(r"\begin{tabular}{llcc}")
    print(r"\toprule")
    print(r"Runtime & Mode & Max Stable RPS & Cost Per Success ($10^{-3}$) \\")
    print(r"\midrule")
    
    # Sort for consistent output
    sorted_items = sorted(summary.items())
    
    for (runtime, otel), rps in sorted_items:
        otel_str = "OTel" if otel == 'true' else "Base"
        runtime_str = runtime.capitalize()
        if rps > 0:
            cpss = (1.0 / rps) * 1000 # Scaling for readability
            print(f"{runtime_str} & {otel_str} & {rps:.0f} & {cpss:.3f} \\\\")
        else:
            print(f"{runtime_str} & {otel_str} & Failed & $> \infty$ \\\\")
            
    print(r"\bottomrule")
    print(r"\end{tabular}")
    print(r"\end{center}")
    print(r"\label{tab:cpss}")
    print(r"\end{table}")

def generate_latex_coldstart(file_path):
    if not os.path.exists(file_path):
        return

    data = {} # runtime -> list of ms
    with open(file_path, 'r') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if not row or len(row) < 3: continue
            r, rep, val = row
            if val != 'FAIL':
                if r not in data: data[r] = []
                data[r].append(float(val))

    print("\n% --- LaTeX Table: Cold Start ---")
    print(r"\begin{table}[htbp]")
    print(r"\caption{Cold Start Latency (N=50)}")
    print(r"\begin{center}")
    print(r"\begin{tabular}{lccccc}")
    print(r"\toprule")
    print(r"Runtime & Mean (ms) & Median (ms) & P95 (ms) & Best (ms) & CI (95\%) \\")
    print(r"\midrule")

    for runtime in sorted(data.keys()):
        values = data[runtime]
        if not values:
            print(f"{runtime} & N/A & N/A & N/A & N/A & N/A \\\\")
            continue
            
        mean_val = statistics.mean(values)
        median_val = statistics.median(values)
        p95_val = sorted(values)[int(len(values)*0.95)] if len(values) >= 20 else max(values)
        min_val = min(values)
        
        # Simple bootstrap CI for mean
        means = []
        for _ in range(1000):
            sample = [random.choice(values) for _ in range(len(values))]
            means.append(statistics.mean(sample))
        means.sort()
        ci_low = means[int(1000*0.025)]
        ci_high = means[int(1000*0.975)]
        
        print(f"{runtime.capitalize()} & {mean_val:.2f} & {median_val:.2f} & {p95_val:.2f} & {min_val:.2f} & [{ci_low:.1f}, {ci_high:.1f}] \\\\")

    print(r"\bottomrule")
    print(r"\end{tabular}")
    print(r"\end{center}")
    print(r"\label{tab:coldstart}")
    print(r"\end{table}")

def main():
    print("Loading data...")
    frontier_data = load_frontier_data()
    
    if frontier_data:
        summary = calculate_cpss(frontier_data)
        generate_latex_cpss(summary)
        analyze_otel_impact(frontier_data)
    else:
        print("No frontier data available.")

    # Cold start checks
    if os.path.exists(COLDSTART_FILE):
        print(f"\nCold start data found at {COLDSTART_FILE}.")
        generate_latex_coldstart(COLDSTART_FILE)
    else:
        print("\nCold start data missing.")

if __name__ == "__main__":
    main()
