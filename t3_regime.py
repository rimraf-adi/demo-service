import argparse
import pandas as pd
from load_trades import load_and_preprocess_data
from tabulate import tabulate

def classify_regime(sdf, all_time_variance):
    if len(sdf) < 2:
        return "Unknown (Low Sample)"
        
    counts = sdf["direction"].value_counts(normalize=True)
    majority_direction_ratio = counts.iloc[0] if not counts.empty else 0
    pnl_variance = sdf["pnl_usd"].var()
    avg_duration = sdf["duration_seconds"].mean()
    
    if majority_direction_ratio >= 0.75 and pnl_variance < all_time_variance:
        return "Trending"
    elif majority_direction_ratio < 0.6 and avg_duration < 600:
        return "Choppy"
    elif pnl_variance > 2 * all_time_variance:
        return "Volatile"
    else:
        return "Mixed"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    df = load_and_preprocess_data(args.input)
    if df.empty:
        return
        
    all_time_variance = df["pnl_usd"].var()
    df["date"] = df["entry_time"].dt.date
    
    session_regimes = []
    for date, sdf in df.groupby("date"):
        regime = classify_regime(sdf, all_time_variance)
        session_regimes.append({
            "date": date,
            "regime": regime,
            "trades": len(sdf),
            "pnl": sdf["pnl_usd"].sum(),
            "win_rate": sdf["is_winner"].mean() * 100
        })
        
    regime_df = pd.DataFrame(session_regimes)
    
    print("\n--- TIER 3: REGIME DETECTION ---")
    fmt_regimes = regime_df.copy()
    fmt_regimes["pnl"] = fmt_regimes["pnl"].apply(lambda x: f"${x:.2f}")
    fmt_regimes["win_rate"] = fmt_regimes["win_rate"].apply(lambda x: f"{x:.1f}%")
    print(tabulate(fmt_regimes, headers="keys", tablefmt="grid", showindex=False))
    
    print("\nAggregate Statistics by Regime:")
    agg = regime_df.groupby("regime").agg(
        sessions=("date", "count"),
        total_trades=("trades", "sum"),
        avg_pnl=("pnl", "mean"),
        avg_win_rate=("win_rate", "mean")
    ).reset_index()
    
    fmt_agg = agg.copy()
    fmt_agg["avg_pnl"] = fmt_agg["avg_pnl"].apply(lambda x: f"${x:.2f}")
    fmt_agg["avg_win_rate"] = fmt_agg["avg_win_rate"].apply(lambda x: f"{x:.1f}%")
    print(tabulate(fmt_agg, headers="keys", tablefmt="grid", showindex=False))

if __name__ == "__main__":
    main()
