import argparse
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.load_trades import load_and_preprocess_data
from tabulate import tabulate

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to trade export CSV/TXT")
    args = parser.parse_args()

    df = load_and_preprocess_data(args.input)
    table_data = []
    
    better_direction = None
    best_pnl = float('-inf')
    
    for direction in ["Buy", "Sell"]:
        ddf = df[df["direction"] == direction]
        count = len(ddf)
        if count == 0:
            continue
        
        wins = ddf[ddf["is_winner"]]
        losers = ddf[~ddf["is_winner"]]
        
        win_rate = len(wins) / count
        net_pnl = ddf["pnl_usd"].sum()
        avg_pnl = ddf["pnl_usd"].mean()
        avg_winner = wins["pnl_usd"].mean() if len(wins) > 0 else 0
        avg_loser = losers["pnl_usd"].mean() if len(losers) > 0 else 0
        
        sum_winners = wins["pnl_usd"].sum()
        sum_losers = losers["pnl_usd"].sum()
        pf = abs(sum_winners / sum_losers) if sum_losers != 0 else float('inf')
        
        # Determine best direction (highest P&L heuristic)
        if net_pnl > best_pnl:
            best_pnl = net_pnl
            better_direction = direction
        
        table_data.append({
            "dir": direction,
            "count": count,
            "wr": win_rate,
            "pnl": net_pnl,
            "avg": avg_pnl,
            "aw": avg_winner,
            "al": avg_loser,
            "pf": pf
        })
        
    formatted_data = []
    for d in table_data:
        star = " *" if d["dir"] == better_direction else ""
        formatted_data.append([
            f"{d['dir']}{star}",
            d['count'],
            f"{d['wr']*100:.2f}%",
            f"${d['pnl']:.2f}",
            f"${d['avg']:.2f}",
            f"${d['aw']:.2f}",
            f"${d['al']:.2f}",
            f"{d['pf']:.2f}"
        ])
        
    print("\n--- FREE TIER: DIRECTION SPLIT ---")
    print(tabulate(formatted_data, headers=["Direction (*)", "Trade Count", "Win Rate", "Net P&L", "Avg P&L", "Avg Winner", "Avg Loser", "Profit Factor"], tablefmt="grid"))
    print("\n(*) Indicates the more profitable direction based on Net P&L.")

if __name__ == "__main__":
    main()
