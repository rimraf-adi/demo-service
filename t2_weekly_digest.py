import argparse
import pandas as pd
from load_trades import load_and_preprocess_data

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    df = load_and_preprocess_data(args.input)
    if df.empty:
        return
        
    latest_date = df["entry_time"].max()
    week_ago = latest_date - pd.Timedelta(days=7)
    
    week_df = df[df["entry_time"] >= week_ago]
    
    w_trades = len(week_df)
    w_pnl = week_df["pnl_usd"].sum()
    w_win_rate = week_df["is_winner"].mean() * 100 if w_trades > 0 else 0
    w_wins = week_df[week_df["is_winner"]]["pnl_usd"].sum()
    w_loss = week_df[~week_df["is_winner"]]["pnl_usd"].sum()
    w_pf = abs(w_wins/w_loss) if w_loss != 0 else float('inf')
    
    lines = [
        f"# Weekly Digest (Week ending {latest_date.strftime('%Y-%m-%d')})",
        "",
        "## 1. This week at a glance",
        f"- Trades: {w_trades}",
        f"- Net P&L: ${w_pnl:.2f}",
        f"- Win Rate: {w_win_rate:.1f}%",
        f"- Profit Factor: {w_pf:.2f}",
        ""
    ]
    
    if w_trades > 0:
        best_trade = week_df.loc[week_df["pnl_usd"].idxmax()]
        worst_trade = week_df.loc[week_df["pnl_usd"].idxmin()]
        
        lines.extend([
            "## 2. Best trade of the week",
            f"- Instrument: {best_trade['instrument']} ({best_trade['direction']})",
            f"- Date: {best_trade['entry_time'].strftime('%Y-%m-%d %H:%M')}",
            f"- Duration: {best_trade['duration_str']} ({best_trade['duration_bucket']})",
            f"- P&L: ${best_trade['pnl_usd']:.2f}",
            "",
            "## 3. Worst trade of the week",
            f"- Instrument: {worst_trade['instrument']} ({worst_trade['direction']})",
            f"- Date: {worst_trade['entry_time'].strftime('%Y-%m-%d %H:%M')}",
            f"- Duration: {worst_trade['duration_str']} ({worst_trade['duration_bucket']})",
            f"- P&L: ${worst_trade['pnl_usd']:.2f}",
            ""
        ])    
    
    filename = f"digest_{latest_date.strftime('%Y-%m-%d')}.md"
    with open(filename, "w") as f:
        f.write("\n".join(lines))
        
    print(f"\n--- TIER 2: WEEKLY DIGEST ---")
    print(f"Generated digest: {filename}")

if __name__ == "__main__":
    main()
