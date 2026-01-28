import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import sys

def plot_latency_bar(csv_path):
    try:
        df = pd.read_csv(csv_path)
    except:
        return

    # Group by runtime
    plt.figure(figsize=(10, 6))
    sns.barplot(data=df, x='runtime', y='p99', hue='workload')
    plt.title('p99 Latency by Runtime')
    plt.ylabel('Latency (ms)')
    plt.savefig('benchmark_project/paper/latency_p99.png')
    
    plt.figure(figsize=(10, 6))
    sns.barplot(data=df, x='runtime', y='mean', hue='workload')
    plt.title('Mean Latency by Runtime')
    plt.ylabel('Latency (ms)')
    plt.savefig('benchmark_project/paper/latency_mean.png')

if __name__ == "__main__":
    plot_latency_bar("benchmark_project/results/processed/summary.csv")
