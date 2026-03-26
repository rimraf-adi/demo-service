import argparse
import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.load_trades import load_and_preprocess_data

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    df = load_and_preprocess_data(args.input)
    if df.empty:
        return
        
    df = df.sort_values("entry_time").reset_index(drop=True)
    
    rapid_reentry_clusters = 0
    size_escalations = 0
    sessions_continued_negative = 0
    tilt_trades_idx = set()
    
    session_dates = df["entry_time"].dt.date
    
    for i in range(len(df)):
        if i == 0: continue
        prev = df.loc[i-1]
        curr = df.loc[i]
        
        # Must be in the same session/day roughly
        if session_dates[i] != session_dates[i-1]:
            continue
            
        if not prev["is_winner"]:
            # Rapid re-entry
            minutes_diff = (curr["entry_time"] - prev["exit_time"]).total_seconds() / 60
            if minutes_diff < 30:
                rapid_reentry_clusters += 1
                tilt_trades_idx.add(i)
                
            # Size escalation
            if curr["contracts"] > prev["contracts"]:
                size_escalations += 1
                tilt_trades_idx.add(i)
                
    # Session tilt: goes negative, but keeps trading
    df["date"] = df["entry_time"].dt.date
    for date, sdf in df.groupby("date"):
        sdf = sdf.sort_values("entry_time")
        cum_pnl = sdf["pnl_usd"].cumsum()
        went_negative = cum_pnl < 0
        if went_negative.any():
            first_negative_idx = went_negative.idxmax()
            # If there are trades after going negative
            if first_negative_idx < sdf.index[-1]:
                sessions_continued_negative += 1
                post_negative_trades = sdf.loc[first_negative_idx+1:]
                for idx in post_negative_trades.index:
                    tilt_trades_idx.add(idx)
                    
    tilt_pnl = df.loc[list(tilt_trades_idx)]["pnl_usd"].sum() if tilt_trades_idx else 0
    all_losses = df[~df["is_winner"]]
    typical_loss = all_losses["pnl_usd"].mean() if len(all_losses) > 0 else 0
    tilt_losses = df.loc[list(tilt_trades_idx)]
    avg_tilt_pnl = tilt_losses["pnl_usd"].mean() if len(tilt_losses) > 0 else 0
    
    print("\n--- TIER 2: TILT DETECTION ---")
    print(f"Rapid re-entry clusters (< 30m after loss): {rapid_reentry_clusters}")
    print(f"Size escalations immediately after loss: {size_escalations}")
    print(f"Sessions continued after going net negative: {sessions_continued_negative}")
    print(f"Estimated P&L impact of tilt trades: ${tilt_pnl:.2f}")
    
    if size_escalations > 0:
        print(f"\nInterpretation: You escalated size after a loss in {size_escalations} instances. Those follow-on trades averaged ${avg_tilt_pnl:.2f}, vs ${typical_loss:.2f} for your typical loss.")

if __name__ == "__main__":
    main()
