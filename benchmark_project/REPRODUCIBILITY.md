# Reproducibility Guide

This repository contains all the necessary artifacts to reproduce the results presented in the paper **"Architectural Substrates for the Intelligent Economy"**.

## Prerequisites
- **Runtimes**:
  - Node.js v25+
  - Bun v1.3+
  - Deno v2.6+
- **Tools**:
  - `k6` (Load Generator)
  - `python3` (Analysis & Cold Start)
  - `pdflatex` (Manuscript Compilation)
  - `bc` (Basic Calculator for scripts)

## 1. Experimental Execution

### W1: Runtime Frontier (Throughput vs Latency)
This script sweeps concurrency (10, 100, 500, 1000 VUs) for all runtimes in both Base and OTel modes.
```bash
# Estimated Runtime: ~30 minutes
./benchmark_project/experiments/run_frontier.sh
```
*Output*: `benchmark_project/results/frontier/frontier_summary.csv`

### W4: Cold Start Latency
This script measures the time-to-first-byte (TTFB) for 50 independent process spawns.
```bash
# Estimated Runtime: ~5 minutes
python3 benchmark_project/experiments/measure_coldstart.py
```
*Output*: `benchmark_project/results/raw/coldstart_results.csv`

## 2. Analysis & Data Verification
Run the analysis script to process raw CSVs and generate the exact values used in the paper's tables.
```bash
python3 benchmark_project/analysis/analyze_results.py
```
*Output*: Console output containing LaTeX tables for "Economic Efficiency" and "Cold Start".

**Verification Check**:
Compare the console output with `benchmark_project/paper/main.tex`:
- Table I: Cost Per Success
- Table II: Cold Start Latency
- Figures 4, 5, 6: Derived directly from these datasets.

## 3. Manuscript Compilation
Compile the LaTeX source (including TikZ figures) into the final PDF.
```bash
pdflatex -interaction=nonstopmode -output-directory=benchmark_project/paper benchmark_project/paper/main.tex
```
*Output*: `benchmark_project/paper/main.pdf`

## Data Provenance
- **Figure 4 (CPSS)**: Derived from `frontier_summary.csv` via the formula $1 / (RPS * I(p99 < 200ms))$.
- **Figure 5 (Cold Start)**: Mean and 95% CI calculated from `coldstart_results.csv` using 1000-sample bootstrap.
- **Figure 6 (Frontier)**: Plotted directly from `frontier_summary.csv` datapoints.
