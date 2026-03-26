import argparse
import pandas as pd
from load_trades import load_and_preprocess_data
from tabulate import tabulate

def get_streaks(is_winner_series):
    streaks = []
    current_val = None
    current_length = 0
    for val in is_winner_series:
        if val == current_val:
            current_length += 1
        else:
            if current_val is not None:
                streaks.append((current_val, current_length))
            current_val = val
            current_length = 1
    if current_val is not None:
        streaks.append((current_val, current_length))
    return streaks

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    df = load_and_preprocess_data(args.input)
    if df.empty:
        return
        
    df = df.sort_values("entry_time")
    streaks = get_streaks(df["is_winner"])
    
    win_streaks = [s[1] for s in streaks if s[0] == True]
    loss_streaks = [s[1] for s in streaks if s[0] == False]
    
    max_win_streak = max(win_streaks) if win_streaks else 0
    max_loss_streak = max(loss_streaks) if loss_streaks else 0
    avg_win_streak = sum(win_streaks)/len(win_streaks) if win_streaks else 0
    avg_loss_streak = sum(loss_streaks)/len(loss_streaks) if loss_streaks else 0
    
    print("\n--- TIER 1: STREAK TRACKER ---")
    streak_data = [
        ["Longest winning streak", max_win_streak],
        ["Longest losing streak", max_loss_streak],
        ["Average winning streak length", f"{avg_win_streak:.1f}"],
        ["Average losing streak length", f"{avg_loss_streak:.1f}"]
    ]
    print(tabulate(streak_data, tablefmt="grid"))
    
    df["date"] = df["entry_time"].dt.date
    session_data = []
    for date, sdf in df.groupby("date"):
        sdf = sdf.sort_values("entry_time")
        cum_pnl = sdf["pnl_usd"].cumsum()
        peak_pnl = cum_pnl.cummax()
        drawdown = peak_pnl - cum_pnl
        max_dd = drawdown.max()
        final_pnl = cum_pnl.iloc[-1]
        session_data.append([
            date, len(sdf), final_pnl, peak_pnl.max(), max_dd
        ])
    
    print("\n--- Intra-Session Drawdown ---")
    fmt_sd = []
    gave_back_count = 0
    for s in session_data:
        if s[3] > 0 and s[2] < 0:
            gave_back_count += 1
        fmt_sd.append([
            s[0], s[1], f"${s[2]:.2f}", f"${s[3]:.2f}", f"${s[4]:.2f}"
        ])
        
    print(tabulate(fmt_sd, headers=["Date", "Trades", "Final P&L", "Peak P&L", "Max DD from Peak"], tablefmt="grid"))
    if gave_back_count > 0:
        print(f"\n[!] FLAG: Gave back a winner in {gave_back_count} of {len(session_data)} sessions.")

if __name__ == "__main__":
    main()
