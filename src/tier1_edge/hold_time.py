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
    total_trades = len(df)
    
    if total_trades == 0:
        print("No data.")
        return
        
    buckets = ["Scalp", "Short", "Medium", "Long"]
    table_data = []
    
    for b in buckets:
        bdf = df[df["duration_bucket"] == b]
        count = len(bdf)
        if count == 0:
            continue
            
        wins = bdf[bdf["is_winner"]]
        losers = bdf[~bdf["is_winner"]]
        
        wr = len(wins) / count
        net = bdf["pnl_usd"].sum()
        avg = bdf["pnl_usd"].mean()
        aw = wins["pnl_usd"].mean() if len(wins) > 0 else 0
        al = losers["pnl_usd"].mean() if len(losers) > 0 else 0
        sw = wins["pnl_usd"].sum()
        sl = losers["pnl_usd"].sum()
        pf = abs(sw / sl) if sl != 0 else float('inf')
        pct = (count / total_trades) * 100
        
        table_data.append([
            b,
            count,
            f"{pct:.1f}%",
            f"{wr*100:.1f}%",
            f"${net:.2f}",
            f"${avg:.2f}",
            f"${aw:.2f}",
            f"${al:.2f}",
            f"{pf:.2f}"
        ])
        
    print("\n--- TIER 1: HOLD TIME ANALYSIS ---")
    print(tabulate(table_data, headers=["Bucket", "Trades", "% of All", "Win Rate", "Net P&L", "Avg P&L", "Avg Win", "Avg Loss", "PF"], tablefmt="grid"))
    
    if table_data:
        most_freq_bucket = max(table_data, key=lambda x: x[1])
        most_freq_avg_pnl = float(most_freq_bucket[5].replace('$', ''))
        if most_freq_avg_pnl < 0:
            print(f"\n[!] FLAG: Your most common hold time ({most_freq_bucket[0]}) is negative expectancy (${most_freq_avg_pnl:.2f} avg).")

if __name__ == "__main__":
    main()
