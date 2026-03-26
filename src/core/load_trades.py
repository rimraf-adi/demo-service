import pandas as pd
import numpy as np

def categorize_session(hour):
    if 18 <= hour <= 23 or 0 <= hour <= 1:
        return "Asian"
    elif 2 <= hour <= 8:
        return "London"
    elif 9 <= hour <= 12:
        return "NY morning"
    elif 13 <= hour <= 16:
        return "NY afternoon"
    elif hour == 17:
        return "Extended"
    else:
        return "Unknown"

def categorize_duration(seconds):
    if seconds < 300:
        return "Scalp"
    elif 300 <= seconds <= 1800:
        return "Short"
    elif 1800 < seconds <= 7200:
        return "Medium"
    else:
        return "Long"

def load_and_preprocess_data(filepath, tz=None):
    """
    Loads trade export data from a file, generating all derived fields specified in the claude-spec.md.
    Supports NinjaTrader/Tradovate/Quantower TXT/CSV format.
    """
    data_lines = []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("Serial") or line.startswith("trade_id"):
                continue
            parts = line.split('\t')
            if len(parts) >= 10:
                data_lines.append(parts[:10])

    df = pd.DataFrame(data_lines, columns=[
        "Serial", "Symbol", "Direction", "Contracts", "Open_Price", 
        "Open_Time", "Close_Price", "Close_Time", "Duration", "Net_PNL"
    ])
    
    # Clean and rename
    df = df.rename(columns={
        "Serial": "trade_id",
        "Symbol": "instrument",
        "Direction": "direction",
        "Contracts": "contracts",
        "Open_Price": "entry_price",
        "Open_Time": "entry_time",
        "Close_Price": "exit_price",
        "Close_Time": "exit_time",
        "Net_PNL": "pnl_usd",
        "Duration": "duration_str"
    })
    
    # Deduplicate by trade_id
    df['trade_id'] = df['trade_id'].astype(int)
    df = df.drop_duplicates(subset=["trade_id"]).sort_values("trade_id")
    
    # Types
    df["contracts"] = df["contracts"].astype(int)
    df["entry_price"] = df["entry_price"].astype(float)
    df["exit_price"] = df["exit_price"].astype(float)
    df["pnl_usd"] = df["pnl_usd"].astype(str).str.replace(r"[$,]", "", regex=True).astype(float)
    
    # Datetimes
    df["entry_time"] = pd.to_datetime(df["entry_time"], format="%B %d, %Y at %I:%M:%S %p")
    df["exit_time"] = pd.to_datetime(df["exit_time"], format="%B %d, %Y at %I:%M:%S %p")
    if tz:
        df["entry_time"] = df["entry_time"].dt.tz_localize('UTC').dt.tz_convert(tz)
        df["exit_time"] = df["exit_time"].dt.tz_localize('UTC').dt.tz_convert(tz)
        
    df["duration_seconds"] = (df["exit_time"] - df["entry_time"]).dt.total_seconds().astype(int)
    
    # Derived fields
    df["pnl_points"] = df["pnl_usd"] / (2.0 * df["contracts"])
    df["is_winner"] = df["pnl_usd"] > 0
    df["entry_hour"] = df["entry_time"].dt.hour
    df["duration_bucket"] = df["duration_seconds"].apply(categorize_duration)
    df["session"] = df["entry_hour"].apply(categorize_session)
    
    # Proxy MFE/MAE (friction)
    df["raw_move"] = np.where(df["direction"] == "Buy", df["exit_price"] - df["entry_price"], df["entry_price"] - df["exit_price"])
    df["raw_move_usd"] = df["raw_move"] * 2.0 * df["contracts"]
    df["friction_usd"] = df["raw_move_usd"] - df["pnl_usd"]
    # Handle division by zero
    df["friction_pct"] = np.where(df["raw_move_usd"] != 0, df["friction_usd"] / df["raw_move_usd"].abs(), 0.0)

    return df
