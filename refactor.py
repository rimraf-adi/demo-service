import os
import shutil
from pathlib import Path

dirs = ["src/core", "src/free_tier", "src/tier1_edge", "src/tier2_pattern", "src/tier3_coaching", "src/reports", "data"]
for d in dirs:
    os.makedirs(d, exist_ok=True)
    Path(f"{d}/__init__.py").touch()
Path("src/__init__.py").touch()

try: shutil.move("data.txt", "data/data.txt")
except: pass
try: shutil.move("rules.json", "data/rules.json")
except: pass

mapping = {
    "load_trades.py": "src/core/load_trades.py",
    "free_pnl_summary.py": "src/free_tier/pnl_summary.py",
    "free_direction_split.py": "src/free_tier/direction_split.py",
    "free_session_heatmap.py": "src/free_tier/session_heatmap.py",
    "t1_hold_time.py": "src/tier1_edge/hold_time.py",
    "t1_entry_quality.py": "src/tier1_edge/entry_quality.py",
    "t1_streaks.py": "src/tier1_edge/streaks.py",
    "t2_setup_detector.py": "src/tier2_pattern/setup_detector.py",
    "t2_tilt_detection.py": "src/tier2_pattern/tilt_detection.py",
    "t2_weekly_digest.py": "src/tier2_pattern/weekly_digest.py",
    "t3_regime.py": "src/tier3_coaching/regime.py",
    "t3_monte_carlo.py": "src/tier3_coaching/monte_carlo.py",
    "t3_rule_alerts.py": "src/tier3_coaching/rule_alerts.py",
    "generate_report.py": "src/reports/generate_report.py",
    "generate_full_report.py": "src/reports/generate_full_report.py"
}

import_block = """import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.load_trades import load_and_preprocess_data"""

for src_file, dest_file in mapping.items():
    if not os.path.exists(src_file): continue
    
    with open(src_file, "r") as f:
        content = f.read()
        
    if "load_trades" in content and src_file != "load_trades.py":
        content = content.replace("from load_trades import load_and_preprocess_data", import_block)
        
    with open(dest_file, "w") as f:
        f.write(content)
        
    os.remove(src_file)
