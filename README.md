# Kagal Capital: MNQ Trading Analytics Service

A fully automated, multi-tiered algorithmic analytics and coaching engine built specifically for Micro E-mini Nasdaq (MNQ) future trades.

## Repository Structure
```text
analytics_demo/
├── README.md
├── claude-spec.md
├── requirements.md
├── run_all.sh
├── data/
│   ├── data.txt
│   └── rules.json
└── src/
    ├── core/
    │   └── load_trades.py
    ├── free_tier/
    │   ├── pnl_summary.py
    │   ├── direction_split.py
    │   └── session_heatmap.py
    ├── tier1_edge/
    │   ├── hold_time.py
    │   ├── entry_quality.py
    │   └── streaks.py
    ├── tier2_pattern/
    │   ├── setup_detector.py
    │   ├── tilt_detection.py
    │   └── weekly_digest.py
    ├── tier3_coaching/
    │   ├── regime.py
    │   ├── monte_carlo.py
    │   └── rule_alerts.py
    └── reports/
        └── generate_full_report.py
```

## Overview
This service parses raw trading broker exports (NinjaTrader, Tradovate, Quantower) and systematically processes the data through 4 tiers of advanced analytics. The engine detects statistical edges, flags psychological "tilt" patterns (like revenge trading), defines the market regime via variance tracking, and computes risk of ruin via a 10,000-path Monte Carlo simulation. 

Finally, a unified master process generates a sophisticated, LaTeX-rendered PDF report that provides both the calculated data and personalized, conversational **Actionable Coaching Directives**.

## Architecture & Layers

1. **Phase 1: Shared Infrastructure & Free Tier**
   - `src/core/load_trades.py`: The core ingestion module. Scrubs dirty data, assigns `duration_buckets`, categorises specific trading `sessions` (Asian, London, NY), and extracts Proxy MFE/MAE estimates based on gross move friction.
   - `src/free_tier/pnl_summary.py`: High-level metrics (Expectancy, Profit Factor).
   - `src/free_tier/direction_split.py`: Performance breakdown by Buy vs. Sell.
   - `src/free_tier/session_heatmap.py`: Uses `seaborn` to output a PNG heatmap of hourly execution quality.

2. **Phase 2: Tier 1 Edge Tracker**
   - `src/tier1_edge/hold_time.py`: Buckets duration metrics to determine if the edge is in scalping vs swing holding.
   - `src/tier1_edge/entry_quality.py`: Evaluates what percentage of the absolute gross move is consumed by friction (spread + fees).
   - `src/tier1_edge/streaks.py`: Identifies winning/losing session momentums and peak-to-trough max drawdowns per session.

3. **Phase 3: Tier 2 Pattern Intelligence**
   - `src/tier2_pattern/setup_detector.py`: Cross-tabulates constraints (Size + Duration + Direction + Session) to filter historical trades and identify the single highest-expectancy setup cluster.
   - `src/tier2_pattern/tilt_detection.py`: Behavioral analysis searching strictly for negative psychological markers including rapid re-entry (revenge trading under 30m) and size escalation after losses (averaging down).
   - `src/tier2_pattern/weekly_digest.py`: Auto-generates a Markdown summary of the last 7 calendar days.

4. **Phase 4: Tier 3 Coaching Layer**
   - `src/tier3_coaching/regime.py`: Purely variance-based mathematical identification of the market regime (Trending, Volatile, Choppy).
   - `src/tier3_coaching/monte_carlo.py`: Bootstraps historical P&L for 10,000 drawdown risk simulations to find the quantitative Probability of Ruin.
   - `src/tier3_coaching/rule_alerts.py`: Connects with the configurable `data/rules.json` to hard-scan the trade log for discipline breaches.

## Setup & Execution

### Prerequisites
- Python 3.10+
- `uv` (Fast Python Package Manager)
- `pdflatex` (Required to compile the master PDF report)

### Quick Start
To immediately execute every script in sequence against the sample `data.txt`:

```bash
bash run_all.sh
```

### Generating the Master PDF Report
To run the holistic evaluator that reads the dataset, calculates all 4 tiers, injects AI-derived coaching directives, and formats it into a gorgeous multi-page PDF:

```bash
uv run src/reports/generate_full_report.py --input data/data.txt --rules data/rules.json
```
*Output will be generated as `master_report.pdf`.*

## Source Documentation
The original project requirements and Claude-aligned technical specification files are included for structural reference:
- `requirements.md`
- `claude-spec.md`
