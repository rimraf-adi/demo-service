import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.load_trades import load_and_preprocess_data
from tabulate import tabulate

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--capital", type=float, default=10000)
    parser.add_argument("--limit", type=float, default=1000)
    parser.add_argument("--sims", type=int, default=1000)
    parser.add_argument("--trades", type=int, default=100)
    args = parser.parse_args()

    df = load_and_preprocess_data(args.input)
    if df.empty:
        return
        
    pnl_samples = df["pnl_usd"].values
    
    final_pnls = []
    max_drawdowns = []
    ruin_count = 0
    
    for _ in range(args.sims):
        sim_trades = np.random.choice(pnl_samples, size=args.trades, replace=True)
        cum_pnl = np.cumsum(sim_trades)
        equity = args.capital + cum_pnl
        
        peak_equity = np.maximum.accumulate(equity)
        drawdowns = peak_equity - equity
        max_dd = np.max(drawdowns)
        
        if np.any(equity <= (args.capital - args.limit)):
            ruin_count += 1
            
        final_pnls.append(cum_pnl[-1])
        max_drawdowns.append(max_dd)
        
    final_pnls = np.array(final_pnls)
    max_drawdowns = np.array(max_drawdowns)
    
    median_pnl = np.median(final_pnls)
    p5 = np.percentile(final_pnls, 5)
    p95 = np.percentile(final_pnls, 95)
    prob_ruin = (ruin_count / args.sims) * 100
    exp_max_dd = np.mean(max_drawdowns)
    
    print("\n--- TIER 3: MONTE CARLO RISK SIZING ---")
    results = [
        ["Median Final P&L", f"${median_pnl:.2f}"],
        ["5th Percentile (Worst Case)", f"${p5:.2f}"],
        ["95th Percentile (Best Case)", f"${p95:.2f}"],
        ["Expected Max Drawdown", f"${exp_max_dd:.2f}"],
        ["Probability of Ruin", f"{prob_ruin:.1f}%"]
    ]
    print(tabulate(results, headers=["Metric", "Value"], tablefmt="grid"))
    
    plt.figure(figsize=(8, 4))
    plt.hist(final_pnls, bins=50, color='blue', alpha=0.7)
    plt.axvline(median_pnl, color='r', linestyle='dashed', linewidth=1)
    plt.title(f"Monte Carlo Final P&L Distribution (N={args.sims})")
    plt.xlabel("Simulated P&L ($)")
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig("monte_carlo.png")
    print("\nSaved distribution chart to monte_carlo.png")

if __name__ == "__main__":
    main()
