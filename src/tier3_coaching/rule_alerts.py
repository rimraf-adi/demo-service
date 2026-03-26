import argparse
import json
import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.load_trades import load_and_preprocess_data
from tabulate import tabulate

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--rules", default="rules.json")
    args = parser.parse_args()

    df = load_and_preprocess_data(args.input)
    if df.empty:
        return
        
    try:
        with open(args.rules, "r") as f:
            config = json.load(f)
            rules = config.get("rules", [])
    except Exception as e:
        print(f"Error loading rules.json: {e}")
        return

    rule_dict = {}
    for r in rules:
        rule_dict[r["id"]] = r

    df = df.sort_values("entry_time").reset_index(drop=True)
    df["date"] = df["entry_time"].dt.date
    
    violations = []
    
    for date, sdf in df.groupby("date"):
        sdf = sdf.sort_values("entry_time")
        
        loss_streak = 0
        trade_count = 0
        cum_pnl = 0
        last_loss_time = None
        
        for idx in sdf.index:
            trade = sdf.loc[idx]
            trade_count += 1
            cum_pnl += trade["pnl_usd"]
            
            # Check limits prior to the trade impact logic if needed, but doing it post-trade here for simplicity
            if "MAX_TRADES_PER_SESSION" in rule_dict and trade_count > rule_dict["MAX_TRADES_PER_SESSION"]["value"]:
                violations.append({"rule": "MAX_TRADES_PER_SESSION", "trade_id": trade["trade_id"], "date": date, "pnl_impact": trade["pnl_usd"]})
                
            if "DAILY_LOSS_LIMIT" in rule_dict and (cum_pnl - trade["pnl_usd"]) <= -rule_dict["DAILY_LOSS_LIMIT"]["value"]:
                violations.append({"rule": "DAILY_LOSS_LIMIT", "trade_id": trade["trade_id"], "date": date, "pnl_impact": trade["pnl_usd"]})
                
            if "MAX_LOSSES_PER_SESSION" in rule_dict and loss_streak >= rule_dict["MAX_LOSSES_PER_SESSION"]["value"]:
                violations.append({"rule": "MAX_LOSSES_PER_SESSION", "trade_id": trade["trade_id"], "date": date, "pnl_impact": trade["pnl_usd"]})
                
            if "NO_TRADE_AFTER_LOSS" in rule_dict and last_loss_time is not None:
                mins_since_loss = (trade["entry_time"] - last_loss_time).total_seconds() / 60.0
                if mins_since_loss < rule_dict["NO_TRADE_AFTER_LOSS"]["minutes"]:
                    violations.append({"rule": "NO_TRADE_AFTER_LOSS", "trade_id": trade["trade_id"], "date": date, "pnl_impact": trade["pnl_usd"]})
                    
            if "SIZE_LIMIT" in rule_dict and trade["contracts"] > rule_dict["SIZE_LIMIT"]["value"]:
                violations.append({"rule": "SIZE_LIMIT", "trade_id": trade["trade_id"], "date": date, "pnl_impact": trade["pnl_usd"]})

            # Update state
            if not trade["is_winner"]:
                loss_streak += 1
                last_loss_time = trade["exit_time"]
            else:
                loss_streak = 0
                
    print("\n--- TIER 3: CUSTOM RULE ALERTS ---")
    if not violations:
        print("Excellent discipline! Zero rule violations found.")
        return
        
    v_df = pd.DataFrame(violations)
    
    print("\nRule Violation Details:")
    fmt_v = v_df.copy()
    fmt_v["pnl_impact"] = fmt_v["pnl_impact"].apply(lambda x: f"${x:.2f}")
    print(tabulate(fmt_v, headers="keys", tablefmt="grid", showindex=False))
    
    print("\nAggregate Violation Summary:")
    agg = v_df.groupby("rule").agg(
        violations=("trade_id", "count"),
        total_pnl_impact=("pnl_impact", "sum")
    ).reset_index()
    fmt_agg = agg.copy()
    fmt_agg["total_pnl_impact"] = fmt_agg["total_pnl_impact"].apply(lambda x: f"${x:.2f}")
    print(tabulate(fmt_agg, headers="keys", tablefmt="grid", showindex=False))

if __name__ == "__main__":
    main()
