import argparse
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from load_trades import load_and_preprocess_data
from tabulate import tabulate

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to trade export CSV/TXT")
    args = parser.parse_args()

    df = load_and_preprocess_data(args.input)
    
    print("\n--- FREE TIER: HOURLY STATS ---")
    if not df.empty:
        hourly_stats = df.groupby("entry_hour").agg(
            trade_count=("trade_id", "count"),
            net_pnl=("pnl_usd", "sum"),
            win_rate=("is_winner", "mean"),
            avg_pnl=("pnl_usd", "mean")
        ).reset_index()
        
        hourly_stats["win_rate"] = hourly_stats["win_rate"] * 100
        hourly_stats["flag"] = hourly_stats["trade_count"].apply(lambda x: "Low Sample" if x < 3 else "")
        
        fmt_hourly = hourly_stats.copy()
        fmt_hourly["net_pnl"] = fmt_hourly["net_pnl"].apply(lambda x: f"${x:.2f}")
        fmt_hourly["avg_pnl"] = fmt_hourly["avg_pnl"].apply(lambda x: f"${x:.2f}")
        fmt_hourly["win_rate"] = fmt_hourly["win_rate"].apply(lambda x: f"{x:.1f}%")
        print(tabulate(fmt_hourly, headers=["Hour", "Trades", "Net P&L", "Win Rate", "Avg P&L", "Note"], tablefmt="grid"))
        
        print("\n--- FREE TIER: SESSION ROLLUP ---")
        session_stats = df.groupby("session").agg(
            trade_count=("trade_id", "count"),
            net_pnl=("pnl_usd", "sum"),
            win_rate=("is_winner", "mean"),
            avg_pnl=("pnl_usd", "mean")
        ).reset_index()
        session_stats["win_rate"] = session_stats["win_rate"] * 100
        
        fmt_session = session_stats.copy()
        fmt_session["net_pnl"] = fmt_session["net_pnl"].apply(lambda x: f"${x:.2f}")
        fmt_session["avg_pnl"] = fmt_session["avg_pnl"].apply(lambda x: f"${x:.2f}")
        fmt_session["win_rate"] = fmt_session["win_rate"].apply(lambda x: f"{x:.1f}%")
        print(tabulate(fmt_session, headers=["Session", "Trades", "Net P&L", "Win Rate", "Avg P&L"], tablefmt="grid"))
        
        # Heatmap generation
        heatmap_data = hourly_stats.set_index("entry_hour")[["net_pnl"]].T
        plt.figure(figsize=(10, 2))
        sns.heatmap(heatmap_data, annot=True, cmap="RdYlGn", center=0, cbar=False, fmt=".0f")
        plt.title("Net P&L by Entry Hour")
        plt.xlabel("Hour of Day (Local)")
        plt.yticks([])
        plt.tight_layout()
        plt.savefig("session_heatmap.png", bbox_inches='tight')
        print("\nHeatmap saved to session_heatmap.png")
    else:
        print("No data available.")

if __name__ == "__main__":
    main()
