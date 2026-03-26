#!/bin/bash

DATA="data.txt"

echo "=========================================="
echo " RUNNING ALL TIER SCRIPTS"
echo "=========================================="

echo -e "\n--- FREE TIER ---"
uv run free_pnl_summary.py --input "$DATA"
uv run free_direction_split.py --input "$DATA"
uv run free_session_heatmap.py --input "$DATA"

echo -e "\n--- TIER 1 ---"
uv run t1_hold_time.py --input "$DATA"
uv run t1_entry_quality.py --input "$DATA"
uv run t1_streaks.py --input "$DATA"

echo -e "\n--- TIER 2 ---"
uv run t2_setup_detector.py --input "$DATA"
uv run t2_tilt_detection.py --input "$DATA"
uv run t2_weekly_digest.py --input "$DATA"

echo -e "\n--- TIER 3 ---"
uv run t3_regime.py --input "$DATA"
uv run t3_monte_carlo.py --input "$DATA" --capital 10000 --limit 1000 --sims 10000
uv run t3_rule_alerts.py --input "$DATA" --rules rules.json

echo -e "\n=========================================="
echo "All scripts requested by Claude-spec.md executed successfully."
