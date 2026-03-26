import argparse
import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.load_trades import load_and_preprocess_data
from tabulate import tabulate

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    df = load_and_preprocess_data(args.input)
    if df.empty:
        return
        
    print("\n--- TIER 1: ENTRY QUALITY SCORE (PROXY MFE/MAE) ---")
    avg_friction = df["friction_usd"].mean()
    avg_friction_pct = df["friction_pct"].mean() * 100
    
    print(f"Average friction per trade: ${avg_friction:.2f} ({avg_friction_pct:.1f}% of gross move)")
    
    # Distribution of friction_pct
    friction_pct_100 = df["friction_pct"] * 100
    bins = [-float('inf'), 5, 15, 30, float('inf')]
    labels = ["< 5%", "5-15%", "15-30%", "> 30%"]
    df["friction_bucket"] = pd.cut(friction_pct_100, bins=bins, labels=labels)
    dist = df["friction_bucket"].value_counts().sort_index()
    
    print("\nFriction Distribution (Spread + Commissions impact on gross move):")
    for k, v in dist.items():
        print(f"  {k}: {v} trades")
        
    high_cost = df[df["friction_pct"] > 0.30]
    if len(high_cost) > 0:
        print(f"\n[!] FLAG: {len(high_cost)} trades had friction > 30% of the gross move.")
        fmt_hc = high_cost[["trade_id", "direction", "duration_str", "raw_move_usd", "pnl_usd", "friction_usd"]].copy()
        fmt_hc["friction_usd"] = fmt_hc["friction_usd"].apply(lambda x: f"${x:.2f}")
        fmt_hc["raw_move_usd"] = fmt_hc["raw_move_usd"].apply(lambda x: f"${x:.2f}")
        fmt_hc["pnl_usd"] = fmt_hc["pnl_usd"].apply(lambda x: f"${x:.2f}")
        print(tabulate(fmt_hc, headers="keys", tablefmt="simple", showindex=False))

    print("\n*Note: Full MFE/MAE scoring requires intra-trade OHLC tick data. This module uses an estimated proxy derivation.")

if __name__ == "__main__":
    main()
