import argparse
import pandas as pd
from load_trades import load_and_preprocess_data
from tabulate import tabulate

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    df = load_and_preprocess_data(args.input)
    if df.empty:
        return
        
    df["contracts_cat"] = df["contracts"].apply(lambda x: str(x) if x in [1, 2] else "other")
    
    grouped = df.groupby(["direction", "session", "duration_bucket", "contracts_cat"]).agg(
        trade_count=("trade_id", "count"),
        net_pnl=("pnl_usd", "sum"),
        win_rate=("is_winner", "mean"),
        avg_pnl=("pnl_usd", "mean")
    ).reset_index()
    
    # Filter for >= 3 trades
    valid_setups = grouped[grouped["trade_count"] >= 3].copy()
    
    if valid_setups.empty:
        print("\n--- TIER 2: BEST SETUP DETECTOR ---")
        print("No specific setups with >= 3 trades found in the sample.")
        return
        
    valid_setups["expectancy"] = valid_setups["avg_pnl"]
    valid_setups = valid_setups.sort_values("expectancy", ascending=False)
    
    def get_confidence(n):
        if n >= 10: return "High"
        if n >= 5: return "Medium"
        return "Low"
        
    valid_setups["confidence"] = valid_setups["trade_count"].apply(get_confidence)
    
    fmt_setups = valid_setups.copy()
    fmt_setups["net_pnl"] = fmt_setups["net_pnl"].apply(lambda x: f"${x:.2f}")
    fmt_setups["avg_pnl"] = fmt_setups["avg_pnl"].apply(lambda x: f"${x:.2f}")
    fmt_setups["expectancy"] = fmt_setups["expectancy"].apply(lambda x: f"${x:.2f}")
    fmt_setups["win_rate"] = (fmt_setups["win_rate"] * 100).apply(lambda x: f"{x:.1f}%")
    
    print("\n--- TIER 2: BEST SETUP DETECTOR ---")
    print(tabulate(fmt_setups, headers="keys", tablefmt="grid", showindex=False))

    top = valid_setups.iloc[0]
    print(f"\n[+] TOP SETUP: {top['direction']} | {top['session']} | {top['duration_bucket']} | {top['contracts_cat']} contracts")
    print(f"    Expectancy: ${float(str(top['expectancy']).replace('$','')):.2f} per trade (Confidence: {top['confidence']})")
    
    bottom = valid_setups.iloc[-1]
    bottom_expectancy = float(str(bottom['expectancy']).replace('$',''))
    if bottom_expectancy < 0:
        print(f"\n[-] WORST SETUP: {bottom['direction']} | {bottom['session']} | {bottom['duration_bucket']} | {bottom['contracts_cat']} contracts")
        print(f"    Expectancy: ${bottom_expectancy:.2f} per trade (Confidence: {bottom['confidence']})")

if __name__ == "__main__":
    main()
