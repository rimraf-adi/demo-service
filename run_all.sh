#!/bin/bash

DATA="data/data.txt"
RULES="data/rules.json"

echo "=========================================="
echo " RUNNING ALL TIER SCRIPTS"
echo "=========================================="

echo -e "\n--- FREE TIER ---"
uv run src/free_tier/pnl_summary.py --input "$DATA"
uv run src/free_tier/direction_split.py --input "$DATA"
uv run src/free_tier/session_heatmap.py --input "$DATA"

echo -e "\n--- TIER 1 ---"
uv run src/tier1_edge/hold_time.py --input "$DATA"
uv run src/tier1_edge/entry_quality.py --input "$DATA"
uv run src/tier1_edge/streaks.py --input "$DATA"

echo -e "\n--- TIER 2 ---"
uv run src/tier2_pattern/setup_detector.py --input "$DATA"
uv run src/tier2_pattern/tilt_detection.py --input "$DATA"
uv run src/tier2_pattern/weekly_digest.py --input "$DATA"

echo -e "\n--- TIER 3 ---"
uv run src/tier3_coaching/regime.py --input "$DATA"
uv run src/tier3_coaching/monte_carlo.py --input "$DATA" --capital 10000 --limit 1000 --sims 10000
uv run src/tier3_coaching/rule_alerts.py --input "$DATA" --rules "$RULES"

echo -e "\n=========================================="
echo "All scripts executing within the new modular architecture."
