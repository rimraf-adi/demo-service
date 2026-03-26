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
    
    total_pnl = df["pnl_usd"].sum()
    total_trades = len(df)
    wins = df[df["is_winner"]]
    losers = df[~df["is_winner"]]
    
    win_count = len(wins)
    loss_count = len(losers)
    win_rate = win_count / total_trades if total_trades > 0 else 0
    
    avg_winner = wins["pnl_usd"].mean() if win_count > 0 else 0
    avg_loser = losers["pnl_usd"].mean() if loss_count > 0 else 0
    
    sum_winners = wins["pnl_usd"].sum()
    sum_losers = losers["pnl_usd"].sum()
    profit_factor = abs(sum_winners / sum_losers) if sum_losers != 0 else float('inf')
    
    expectancy = (win_rate * avg_winner) + ((1 - win_rate) * avg_loser)
    
    largest_winner = df["pnl_usd"].max() if total_trades > 0 else 0
    largest_loser = df["pnl_usd"].min() if total_trades > 0 else 0
    
    metrics = [
        ["Total net P&L", f"${total_pnl:.2f}"],
        ["Total trades", total_trades],
        ["Win count", win_count],
        ["Loss count", loss_count],
        ["Win rate", f"{win_rate*100:.2f}%"],
        ["Average winner", f"${avg_winner:.2f}"],
        ["Average loser", f"${avg_loser:.2f}"],
        ["Profit factor", f"{profit_factor:.2f}"],
        ["Expectancy per trade", f"${expectancy:.2f}"],
        ["Largest single winner", f"${largest_winner:.2f}"],
        ["Largest single loser", f"${largest_loser:.2f}"]
    ]
    
    print("\n--- FREE TIER: P&L SUMMARY ---")
    print(tabulate(metrics, headers=["Metric", "Value"], tablefmt="grid"))
    print(f"\n=> EXPECTANCY: ${expectancy:.2f} per trade")

if __name__ == "__main__":
    main()
