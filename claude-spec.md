
**Document version:** 1.0  
**Last updated:** March 26, 2026  
**Instrument scope:** MNQ futures (Micro E-mini Nasdaq-100)  
**Data source:** Trade export log (entry price, exit price, direction, size, timestamps, P&L)

---

## 1. Overview

This document defines the feature set, data requirements, and analysis logic for a tiered trading analytics service built on MNQ futures trade data. The service surfaces meaningful behavioural and statistical patterns from a trader's own history, structured into progressively deeper tiers based on subscription level.

**Data Sufficiency Note:** The standard trade export log (as provided in the sample data) is sufficient for all features described in this specification, utilizing behavioral and proxy metrics where high-resolution tick data is unavailable.

---

## 2. Data Schema

Each trade record contains the following fields. All downstream analysis depends on this schema being clean and consistently typed. The schema is designed to be compatible with standard Ninjatracker/Tradovate/Quantower CSV exports.

|Field|Type|Description|Example|
|---|---|---|---|
|`trade_id`|int|Sequential trade number|`1`|
|`instrument`|str|e.g. `MNQM6`, `MNQH6`|`MNQM6`|
|`direction`|str|`Buy` or `Sell`|`Sell`|
|`contracts`|int|Number of contracts traded|`1`|
|`entry_price`|float|Fill price at entry|`24357.00`|
|`entry_time`|datetime|Timestamp of entry (local)|`March 24, 2026 at 6:49:09 PM`|
|`exit_price`|float|Fill price at exit|`24367.75`|
|`exit_time`|datetime|Timestamp of exit (local)|`March 24, 2026 at 6:51:14 PM`|
|`duration`|str|Text duration string|`2m 5s`|
|`pnl_usd`|float|Net P&L in USD|`$-22.62`|

**MNQ tick value:** $0.50 per tick, $2.00 per point per contract.

---

## 2.1 Data Sufficiency Analysis

Based on the provided demo data, the following analysis confirms sufficiency for the service tiers:

### Is the data sufficient?
**Yes.** The standard trade log contains the "DNA" of the trader's behavior. While it lacks tick-by-tick precision (see below), it is 100% sufficient for extracting the patterns required for Fibonacci-level analytics (Tiers 1–3).

### What is covered by this data?
- **All Core P&L Metrics:** Accuracy is 100% as long as commissions are reflected in `pnl_usd`.
- **Hold-time & Edge Analysis:** Sufficient. Duration and timestamps allow for precise bucket classification.
- **Behavioral Patterns (Tilt/Streaks):** Sufficient. Chronological sequence and P&L magnitude reveal psychological pressure points.
- **Expectancy & Setup Detection:** Sufficient. Cross-referencing session, duration, and direction provides high-confidence edge tracking.

### What would "Level 2" data add?
If the user provided intra-trade OHLC or Tick Data, the service could add:
1. **True MFE/MAE:** Knowing exactly how deep the trade went into drawdown before hitting the target.
2. **Slippage Analysis:** Comparing fill price to the exact tape price at the millisecond of entry.
3. **Execution Quality:** Measuring "heat" (how long the trade spent in the red).

*Note: For the current "features only" manual script phase, the provided demo data is the optimal balance of availability and insight.*

**Derived fields** (computed at load time, not stored):

- `pnl_points` = `pnl_usd / (2.0 * contracts)`
- `is_winner` = `pnl_usd > 0`
- `entry_hour` = hour extracted from `entry_time` (0–23)
- `duration_bucket` = categorised duration (see §5.1)
- `session` = derived trading session label (see §4.3)

---

## 3. Tier Structure

### 3.1 Summary

| Tier   | Name                   | Target user          | Key value proposition                                 |
| ------ | ---------------------- | -------------------- | ----------------------------------------------------- |
| Free   | Trade log transparency | Curious / evaluating | See your overall shape at a glance                    |
| Tier 1 | Edge tracker           | Active trader        | Understand when and how long your edge works          |
| Tier 2 | Pattern intelligence   | Serious trader       | Find the specific setups that make or lose money      |
| Tier 3 | Coaching layer         | Performance-focused  | Behavioural risk detection and forward-looking sizing |

Each tier is a strict superset of the tier below it.

---

## 4. Free Tier — Trade Log Transparency

### 4.1 P&L Summary

**Purpose:** Give the trader an honest, clean picture of their overall performance.

**Inputs:** Full trade log.

**Outputs:**

|Metric|Formula|
|---|---|
|Total net P&L|`sum(pnl_usd)`|
|Total trades|`count(trades)`|
|Win count|`count(trades where pnl_usd > 0)`|
|Loss count|`count(trades where pnl_usd <= 0)`|
|Win rate|`win_count / total_trades`|
|Average winner (USD)|`mean(pnl_usd where pnl_usd > 0)`|
|Average loser (USD)|`mean(pnl_usd where pnl_usd <= 0)`|
|Profit factor|`abs(sum of winners) / abs(sum of losers)`|
|Expectancy per trade|`(win_rate × avg_winner) + ((1 − win_rate) × avg_loser)`|
|Largest single winner|`max(pnl_usd)`|
|Largest single loser|`min(pnl_usd)`|

**Display format:** Single summary table, sorted by metric name. USD values to 2 decimal places. Ratios to 2 decimal places.

**Notes:** Profit factor > 1.0 indicates a net-positive system. Expectancy is the most important single number — surface it prominently.

---

### 4.2 Trade Direction Split

**Purpose:** Separate long (Buy) and short (Sell) performance to identify directional bias or blind spots.

**Inputs:** Full trade log, split by `direction`.

**Outputs per direction (Buy / Sell):**

|Metric|Formula|
|---|---|
|Trade count|`count`|
|Win rate|`winners / count`|
|Net P&L|`sum(pnl_usd)`|
|Average P&L per trade|`mean(pnl_usd)`|
|Average winner|`mean(winners)`|
|Average loser|`mean(losers)`|
|Profit factor|as above|

**Display format:** Two-column comparison table (Buy vs Sell). Highlight the direction with higher win rate and higher net P&L using a simple indicator (e.g. `*`).

**Pattern to watch:** A direction with high win rate but negative net P&L signals winners are too small relative to losers (size asymmetry problem).

---

### 4.3 Session Heatmap

**Purpose:** Show which hours of day are profitable vs losing, averaged across all trades.

**Inputs:** `entry_hour` (0–23) and `pnl_usd` per trade.

**Session labels** (apply to `entry_hour`):

|Label|Hours (local)|Notes|
|---|---|---|
|Asian|18:00–01:00|Prior evening + overnight|
|London|02:00–08:00|Pre-US open|
|NY morning|09:00–12:00|Primary US session|
|NY afternoon|13:00–16:00|Post-lunch US|
|Extended|17:00–17:59|CME globex transition|

**Outputs:**

- Count of trades per hour
- Net P&L per hour
- Win rate per hour
- Average P&L per trade per hour

**Display format:** Tabular heatmap — rows = hours, columns = metrics. Shade cells by net P&L (green positive, red negative, neutral at zero). Also produce a session-level rollup (aggregate the hourly rows into the 5 session buckets above).

**Notes:** Hours with fewer than 3 trades should be flagged as low-sample. Do not draw conclusions from single-trade hours.

---

## 5. Tier 1 — Edge Tracker

_Includes all Free tier outputs, plus the following._

### 5.1 Hold Time Analysis

**Purpose:** Determine whether the trader's edge is in quick scalps, medium holds, or longer swings — or whether certain durations are systematically losing.

**Inputs:** `duration_seconds` and `pnl_usd` per trade.

**Duration buckets:**

|Bucket label|Range|
|---|---|
|Scalp|< 5 minutes (< 300s)|
|Short|5–30 minutes (300–1800s)|
|Medium|30 minutes – 2 hours (1800–7200s)|
|Long|> 2 hours (> 7200s)|

**Outputs per bucket:**

|Metric|Formula|
|---|---|
|Trade count|`count`|
|Win rate|`winners / count`|
|Net P&L|`sum(pnl_usd)`|
|Avg P&L per trade|`mean(pnl_usd)`|
|Avg winner|`mean(winners pnl)`|
|Avg loser|`mean(losers pnl)`|
|Profit factor|as standard|

**Display format:** Table sorted by bucket duration ascending. Include a column for `% of all trades` to show where the trader spends most of their time.

**Interpretation flags (auto-generated text):**

- If the trader's most frequent bucket has a negative avg P&L → "Your most common hold time is your worst-performing bucket."
- If profit factor > 1.5 in one bucket and < 1.0 in another → "Strong edge in [bucket], consider avoiding [bucket]."

---

### 5.2 Entry Quality Score

**Purpose:** Separate losses caused by bad entries (price moved against immediately) from losses caused by bad exits (trade was right but held too long or cut too early).

**Concept:** For each trade, the entry quality score is the ratio of the maximum favourable excursion (MFE) to the maximum adverse excursion (MAE). Because raw MFE/MAE are not stored in the current log, this module uses a proxy derived from the relationship between entry price, exit price, and duration.

**Proxy approach** (when tick-by-tick data is unavailable):

Define:

- `raw_move` = `exit_price − entry_price` (for Buy) or `entry_price − exit_price` (for Sell)
- `raw_move_usd` = `raw_move × 2 × contracts`
- Compare `raw_move_usd` to `pnl_usd` to infer slippage and friction
- `friction` = `raw_move_usd − pnl_usd` (the cost of commissions + slippage, always ≥ 0 for a well-formed record)

**Note:** Full MFE/MAE scoring requires intra-trade OHLC data. Flag this module as "enhanced accuracy available with tick data export."

**Outputs per trade:**

|Field|Value|
|---|---|
|`raw_move_points`|Points captured from entry to exit|
|`raw_move_usd`|Dollar value of the move|
|`friction_usd`|Difference from actual P&L (commissions + slippage)|
|`friction_pct`|`friction / abs(raw_move_usd)`|

**Aggregate outputs:**

- Average friction per trade (USD and %)
- Distribution of `friction_pct` (histogram: < 5%, 5–15%, 15–30%, > 30%)
- Trades where friction exceeded 30% of the gross move (flag as "high-cost trades")

---

### 5.3 Streak Tracker

**Purpose:** Identify patterns in winning and losing streaks — both within a session and across sessions — to detect momentum bias and psychological pressure points.

**Inputs:** Trades sorted chronologically by `entry_time`.

**Outputs:**

**Streak statistics:**

|Metric|Formula|
|---|---|
|Longest winning streak|Max consecutive `is_winner = True`|
|Longest losing streak|Max consecutive `is_winner = False`|
|Average winning streak length|Mean of all win streaks|
|Average losing streak length|Mean of all loss streaks|

**Session-level drawdown:**

For each calendar day (or trading session), compute:

- Running cumulative P&L through the session (trade by trade)
- Peak intra-session P&L
- Max intra-session drawdown from peak = `peak − trough`
- End-of-session P&L

**Outputs:** Table of sessions with columns: date, trade count, session P&L, peak P&L, max drawdown from peak, final result.

**Pattern flag:** If a session ends negative after being positive at some point → "Gave back a winner in [N] of [M] sessions."

---

## 6. Tier 2 — Pattern Intelligence

_Includes all Free and Tier 1 outputs, plus the following._

### 6.1 Best Setup Detector

**Purpose:** Find the specific combination of variables (direction + session + hold duration + contract size) that has the highest expectancy, and surface it as the trader's "core setup."

**Method:** Cross-tabulation across all combinations of:

- `direction` (Buy / Sell)
- `session` (5 labels from §4.3)
- `duration_bucket` (4 buckets from §5.1)
- `contracts` (1 / 2 / other)

For each combination with ≥ 3 trades, compute:

- Trade count
- Win rate
- Net P&L
- Avg P&L per trade
- Expectancy

**Outputs:**

Ranked table of all combinations with ≥ 3 trades, sorted by expectancy descending. Include a `confidence` label:

|Sample size|Confidence|
|---|---|
|≥ 10 trades|High|
|5–9 trades|Medium|
|3–4 trades|Low|
|< 3 trades|Not shown|

**Top-3 setups:** Extract the top 3 combinations by expectancy and display as a highlight card with all metrics.

**Bottom-3 setups:** Same for lowest (most negative) expectancy — these are the combinations to avoid.

---

### 6.2 Tilt Detection

**Purpose:** Detect behavioural signatures of emotional or reactive trading following losses — specifically overtrading, position-size escalation, and rapid revenge entries.

**Inputs:** Trades sorted chronologically. Sessions identified by date + session label.

**Signal 1 — Loss clustering:**  
After any losing trade, count how many trades were taken within the next 30 minutes. If ≥ 2 follow-on trades occur within 30 minutes of a loss, flag as a "rapid re-entry cluster."

**Signal 2 — Size escalation after loss:**  
Detect sequences where `contracts` increases on the trade immediately following a losing trade. Count occurrences. A trader who consistently increases size after a loss is likely averaging down or revenge trading.

**Signal 3 — Session tilt:**  
For each session, compute cumulative P&L at each trade. If a session goes net negative and the trader continues trading after the first loss that pushed them negative, flag as "continued after session went negative."

**Outputs:**

|Metric|Value|
|---|---|
|Rapid re-entry clusters|Count and list of trade pairs|
|Size escalations after loss|Count and % of all losses|
|Sessions continued after going negative|Count|
|Estimated P&L impact of tilt trades|Sum of P&L from flagged trades|

**Interpretation output:** Short plain-English paragraph summarising the tilt signature (e.g. "You escalated size after a loss in 4 of 12 instances. Those follow-on trades lost an average of $87 each, vs $−23 for your typical loss.").

---

### 6.3 Weekly Digest

**Purpose:** Auto-generate a structured weekly insight summary that a trader can read in under 2 minutes.

**Inputs:** All trades in the past 7 calendar days.

**Sections:**

**1. This week at a glance**

- Trade count, net P&L, win rate, profit factor for the week
- Comparison to all-time averages (delta: better / worse / flat)

**2. Best trade of the week**

- Highest P&L trade: instrument, direction, entry time, duration, P&L
- Annotate what session and duration bucket it fell into

**3. Worst trade of the week**

- Lowest P&L trade: same fields
- Flag if this was a tilt trade (per §6.2 signals)

**4. Pattern consistency check**

- Compare this week's top setup (by expectancy) to the all-time top setup
- Flag if they match ("Trading your edge this week") or diverge ("You deviated from your best setup this week")

**5. One actionable observation**

- Rule-based single sentence based on whichever signal is strongest:
    - If win rate this week < 40% → "Win rate was low this week — check if session timing shifted."
    - If tilt signals fired > 2 times → "Multiple rapid re-entry clusters detected. Consider a rule: max 1 re-entry per session after a loss."
    - If best session this week ≠ all-time best session → "You traded [session] most heavily this week, but your long-run edge is in [all-time best session]."

**Output format:** Plain text or markdown file, named `digest_YYYY-MM-DD.md`. One file per week.

---

## 7. Tier 3 — Coaching Layer

_Includes all Free, Tier 1, and Tier 2 outputs, plus the following._

### 7.1 Personalised Regime Detection

**Purpose:** Classify each trading session into a market regime (trending vs. choppy vs. volatile) based on the trader's own results, without requiring external market data.

**Proxy regime classification** (from trade log only):

- **Trending regime:** Multiple trades in the same direction, each profitable. Session P&L strongly positive or strongly negative.
- **Choppy regime:** Alternating win/loss pattern. Short durations. Small absolute P&L per trade.
- **Volatile regime:** Large average absolute P&L (both wins and losses large). Few trades.

**Method:** For each session, compute:

- `direction_consistency` = proportion of trades in the majority direction
- `pnl_variance` = standard deviation of per-trade P&L within session
- `avg_duration` = mean hold time in the session

Assign regime using a rule-based classifier:

|Condition|Regime|
|---|---|
|`direction_consistency ≥ 0.75` and `pnl_variance < threshold`|Trending|
|`direction_consistency < 0.6` and `avg_duration < 600s`|Choppy|
|`pnl_variance > 2 × all-time mean pnl_variance`|Volatile|
|Otherwise|Mixed|

**Output:** Regime label per session. Aggregate statistics by regime (trade count, avg P&L, win rate). Flag the trader's best and worst regime.

---

### 7.2 Monte Carlo Risk Sizing

**Purpose:** Simulate forward-looking drawdown risk at different position sizes and win rates, using the trader's actual P&L distribution as the simulation input.

**Method:**

1. Bootstrap the trader's historical P&L distribution (sample with replacement from `pnl_usd` records).
2. For a given `n_trades` (e.g. 50, 100, 200) and `n_simulations` (default: 10,000), simulate the cumulative equity curve.
3. At each simulation, record: max drawdown, final P&L, whether the account hit a defined drawdown limit.

**Inputs (configurable):**

|Parameter|Default|Description|
|---|---|---|
|`starting_capital`|$10,000|Account size|
|`max_drawdown_limit`|10%|Stop-trading threshold|
|`contract_multiplier`|1×|Scale all P&Ls by this factor to model different sizing|
|`n_trades`|100|Trades to simulate per path|
|`n_simulations`|10,000|Number of paths|

**Outputs:**

|Metric|Value|
|---|---|
|Median final P&L|50th percentile of simulated outcomes|
|5th percentile outcome|Worst-case band|
|95th percentile outcome|Best-case band|
|Ruin probability|% of paths that hit `max_drawdown_limit`|
|Expected max drawdown|Mean of per-path max drawdowns|
|Recommended max contracts|Largest size where ruin probability < 5%|

**Display format:** Summary table + optional equity curve chart (matplotlib, saved as PNG).

---

### 7.3 Custom Rule Alerts

**Purpose:** Allow the trader to define their own circuit-breaker rules, which the analysis script evaluates against each session's data and flags violations.

**Rule types supported:**

|Rule ID|Rule|Trigger condition|
|---|---|---|
|`MAX_LOSSES_PER_SESSION`|Stop after N consecutive losses|Streak of losses ≥ N in one session|
|`DAILY_LOSS_LIMIT`|Stop after losing $X in one session|Session P&L ≤ −$X|
|`MAX_TRADES_PER_SESSION`|No more than N trades per session|Trade count > N in one session|
|`NO_TRADE_AFTER_LOSS`|Minimum gap after a loss|Next trade within M minutes of a loss|
|`SIZE_LIMIT`|No more than N contracts|Any trade with `contracts > N`|

**Configuration:** Rules defined in a `rules.json` file:

```json
{
  "rules": [
    { "id": "MAX_LOSSES_PER_SESSION", "value": 3 },
    { "id": "DAILY_LOSS_LIMIT", "value": 200 },
    { "id": "MAX_TRADES_PER_SESSION", "value": 6 },
    { "id": "NO_TRADE_AFTER_LOSS", "minutes": 15 }
  ]
}
```

**Outputs:**

For each session, a list of rules that would have been triggered, the trade that triggered them, and the P&L impact of all trades taken after the rule should have fired (i.e. what was lost by not stopping).

**Aggregate output:** Rule violation summary table — how many times each rule was violated, and total P&L of post-violation trades.

---

## 8. Script Architecture

All scripts are standalone Python files. They share a common data loading module.

### 8.1 Shared loader — `load_trades.py`

Accepts a CSV export matching the schema in §2. Returns a cleaned `pandas.DataFrame` with all raw and derived fields.

**Required CSV columns:** `instrument`, `direction`, `contracts`, `entry_price`, `entry_time`, `exit_price`, `exit_time`, `pnl_usd` (`trade_id` and `duration` are optional/fallback).

**Data Cleaning Requirements:**
- **Datetime parsing:** `entry_time` and `exit_time` follow the format `%B %d, %Y at %I:%M:%S %p`.
- **Currency symbols:** `pnl_usd` must have `$` and `,` stripped before conversion to float.
- **Timezone:** Assumed local unless a `tz` parameter is passed.

**Derived field computation:** All derived fields (§2) computed at load time and appended to the DataFrame.

---

### 8.2 Script inventory

|Script|Tier|Output|
|---|---|---|
|`free_pnl_summary.py`|Free|Console table + CSV|
|`free_direction_split.py`|Free|Console table + CSV|
|`free_session_heatmap.py`|Free|Console table + PNG heatmap|
|`t1_hold_time.py`|Tier 1|Console table + CSV|
|`t1_entry_quality.py`|Tier 1|Console table + CSV|
|`t1_streaks.py`|Tier 1|Console table + CSV|
|`t2_setup_detector.py`|Tier 2|Console table + CSV|
|`t2_tilt_detection.py`|Tier 2|Console report (text)|
|`t2_weekly_digest.py`|Tier 2|Markdown file|
|`t3_regime.py`|Tier 3|Console table + CSV|
|`t3_monte_carlo.py`|Tier 3|Console table + PNG|
|`t3_rule_alerts.py`|Tier 3|Console report + CSV|

---

### 8.3 Invocation pattern

All scripts follow the same CLI interface:

```bash
python free_pnl_summary.py --input trades.csv
python t1_hold_time.py --input trades.csv --output results/
python t3_monte_carlo.py --input trades.csv --capital 10000 --limit 0.10 --sims 10000
```

---

## 9. Known Limitations

|Limitation|Impact|Mitigation|
|---|---|---|
|No intra-trade OHLC data|MFE/MAE in §5.2 is a proxy only|Note this clearly in output; label as "estimated"|
|Demo Data Format|Specific date/currency formats in sample|Loader (§8.1) explicitly handles the "At" timestamp format|
|Small sample size|Statistical confidence is low across all outputs|Flag any metric based on < 10 trades|
|Local timestamps|Session labels may be off by ±1 hour in DST transitions|Document assumed timezone; add `--tz` flag|
|Single instrument (MNQ)|No cross-instrument comparison possible yet|Schema supports multi-instrument; extend loader later|
|No account balance data|Ruin probability in §7.2 requires user-supplied capital figure|Prompt for it via CLI arg|

---

## 10. Glossary

|Term|Definition|
|---|---|
|Expectancy|Expected P&L per trade = (win rate × avg winner) + ((1 − win rate) × avg loser)|
|Profit factor|Gross profit divided by gross loss (absolute values). > 1.0 = net positive system|
|MFE|Maximum favourable excursion — how far a trade moved in your favour before exit|
|MAE|Maximum adverse excursion — how far a trade moved against you before exit|
|Tilt|Emotionally-driven trading behaviour, typically after a loss, characterised by increased frequency, size, or deviation from planned setups|
|Regime|A classification of current market conditions (trending, choppy, volatile)|
|Session|A named time window within the 24-hour trading day (Asian, London, NY morning, NY afternoon, Extended)|
|Ruin probability|In Monte Carlo context: the probability that a sequence of trades hits the defined drawdown limit|

---

_End of specification._