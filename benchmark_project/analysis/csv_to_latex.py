import pandas as pd
import sys

def generate_latex_table(csv_path):
    try:
        df = pd.read_csv(csv_path)
    except:
        return ""
        
    # Group by runtime and workload
    # We want Mean +- CI
    # For now just Mean (p95)
    
    # Check columns
    if 'mean' not in df.columns:
        return ""
        
    summary = df.groupby(['runtime', 'workload']).agg({
        'mean': ['mean', 'std'],
        'p99': ['mean', 'std'],
        'count': 'sum' # Total requests
    })
    
    # Flatten
    summary.columns = ['_'.join(col) for col in summary.columns]
    summary = summary.reset_index()
    
    # Format
    latex = "\\begin{table}[htbp]\n\\caption{Performance Metrics}\n\\begin{center}\n\\begin{tabular}{lccccc}\n\\toprule\n"
    latex += "Runtime & Workload & Mean Latency (ms) & p99 Latency (ms) \\\\\n\\midrule\n"
    
    for _, row in summary.iterrows():
        rt = row['runtime']
        wl = row['workload']
        mean = f"{row['mean_mean']:.2f} $\\pm$ {row['mean_std']:.2f}"
        p99 = f"{row['p99_mean']:.2f} $\\pm$ {row['p99_std']:.2f}"
        latex += f"{rt} & {wl} & {mean} & {p99} \\\\\n"
        
    latex += "\\bottomrule\n\\end{tabular}\n\\end{center}\n\\end{table}"
    
    return latex

if __name__ == "__main__":
    print(generate_latex_table("benchmark_project/results/processed/summary.csv"))
