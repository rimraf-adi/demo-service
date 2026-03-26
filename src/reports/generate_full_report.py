import argparse
import json
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.load_trades import load_and_preprocess_data
import jinja2
import subprocess
import os

def render_full_report(df, rules_file="rules.json", output_tex="full_report.tex"):
    # ===== FREE TIER =====
    total_pnl = df["pnl_usd"].sum()
    total_trades = len(df)
    wins = df[df["is_winner"]]
    losers = df[~df["is_winner"]]
    win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0
    avg_win = wins["pnl_usd"].mean() if len(wins) > 0 else 0
    avg_loss = losers["pnl_usd"].mean() if len(losers) > 0 else 0
    sum_winners = wins["pnl_usd"].sum()
    sum_losers = losers["pnl_usd"].sum()
    profit_factor = abs(sum_winners / sum_losers) if sum_losers != 0 else float('inf')
    expectancy = (len(wins)/total_trades * avg_win) + ((1 - len(wins)/total_trades) * avg_loss) if total_trades > 0 else 0
    
    direction_stats = []
    better_direction = None
    best_pnl = float('-inf')
    for d in ["Buy", "Sell"]:
        ddf = df[df["direction"] == d]
        count = len(ddf)
        if count == 0: continue
        dwins = ddf[ddf["is_winner"]]
        dlosers = ddf[~ddf["is_winner"]]
        d_pnl = ddf["pnl_usd"].sum()
        d_wr = len(dwins)/count * 100
        d_pf = abs(dwins["pnl_usd"].sum() / dlosers["pnl_usd"].sum()) if dlosers["pnl_usd"].sum() != 0 else float('inf')
        if d_pnl > best_pnl:
            best_pnl = d_pnl
            better_direction = d
        direction_stats.append({
            "dir": d, "trades": count, "win_rate": f"{d_wr:.1f}\\%", 
            "pnl": f"{d_pnl:.2f}", "color": "goodgreen" if d_pnl >= 0 else "badred", "pf": f"{d_pf:.2f}"
        })
    for d in direction_stats:
        if d["dir"] == better_direction: d["dir"] += " (*)"

    hourly_stats = df.groupby("entry_hour")["pnl_usd"].sum().reset_index()
    heatmap_data = hourly_stats.set_index("entry_hour").T
    plt.figure(figsize=(10, 2))
    sns.heatmap(heatmap_data, annot=True, cmap="RdYlGn", center=0, cbar=False, fmt=".0f")
    plt.title("Net P&L by Entry Hour")
    plt.xlabel("Hour of Day (Local)")
    plt.yticks([])
    plt.tight_layout()
    plt.savefig("session_heatmap.png", bbox_inches='tight')
    plt.close()
    
    # ===== TIER 1 =====
    buckets = ["Scalp", "Short", "Medium", "Long"]
    hold_stats = []
    for b in buckets:
        bdf = df[df["duration_bucket"] == b]
        count = len(bdf)
        if count == 0: continue
        bwins = bdf[bdf["is_winner"]]
        bnet = bdf["pnl_usd"].sum()
        bwr = len(bwins)/count * 100
        bpct = count/total_trades * 100
        bls = bdf[~bdf["is_winner"]]["pnl_usd"].sum()
        bpf = abs(bwins["pnl_usd"].sum() / bls) if bls != 0 else float('inf')
        hold_stats.append({
            "bucket": b, "trades": count, "pct": f"{bpct:.1f}\\%", "wr": f"{bwr:.1f}\\%",
            "pnl": f"{bnet:.2f}", "color": "goodgreen" if bnet >= 0 else "badred", "pf": f"{bpf:.2f}"
        })
        
    avg_friction = df["friction_usd"].mean()
    avg_friction_pct = df["friction_pct"].mean() * 100
    
    streaks = []
    current_val, current_length = None, 0
    for val in df.sort_values("entry_time")["is_winner"]:
        if val == current_val: current_length += 1
        else:
            if current_val is not None: streaks.append((current_val, current_length))
            current_val = val
            current_length = 1
    if current_val is not None: streaks.append((current_val, current_length))
    win_streaks = [s[1] for s in streaks if s[0]]
    loss_streaks = [s[1] for s in streaks if not s[0]]
    streak_metrics = {
        "max_win": max(win_streaks) if win_streaks else 0,
        "max_loss": max(loss_streaks) if loss_streaks else 0,
        "avg_win": sum(win_streaks)/len(win_streaks) if win_streaks else 0,
        "avg_loss": sum(loss_streaks)/len(loss_streaks) if loss_streaks else 0
    }
    
    # ===== TIER 2 =====
    df["contracts_cat"] = df["contracts"].apply(lambda x: str(x) if x in [1, 2] else "other")
    grouped = df.groupby(["direction", "session", "duration_bucket", "contracts_cat"]).agg(
        trade_count=("trade_id", "count"), net_pnl=("pnl_usd", "sum"),
        win_rate=("is_winner", "mean"), avg_pnl=("pnl_usd", "mean")
    ).reset_index()
    valid_setups = grouped[grouped["trade_count"] >= 3].copy().sort_values("avg_pnl", ascending=False)
    setup_stats = []
    for _, row in valid_setups.iterrows():
        setup_stats.append({
            "dir": row["direction"], "session": row["session"], "dur": row["duration_bucket"],
            "size": row["contracts_cat"], "trades": row["trade_count"],
            "wr": f"{(row['win_rate']*100):.1f}\\%", "exp": f"{row['avg_pnl']:.2f}",
            "color": "goodgreen" if row['avg_pnl'] >= 0 else "badred"
        })
        
    df_sort = df.sort_values("entry_time").reset_index(drop=True)
    rapid_reentry, size_escalations, tilt_pnl = 0, 0, 0
    tilt_idx = set()
    for i in range(1, len(df_sort)):
        if df_sort["entry_time"].dt.date[i] != df_sort["entry_time"].dt.date[i-1]: continue
        if not df_sort.loc[i-1, "is_winner"]:
            diff = (df_sort.loc[i, "entry_time"] - df_sort.loc[i-1, "exit_time"]).total_seconds()/60
            if diff < 30: 
                rapid_reentry += 1
                tilt_idx.add(i)
            if df_sort.loc[i, "contracts"] > df_sort.loc[i-1, "contracts"]:
                size_escalations += 1
                tilt_idx.add(i)
    tilt_pnl = df_sort.loc[list(tilt_idx), "pnl_usd"].sum() if tilt_idx else 0
    
    tilt_metrics = {
        "rapid": rapid_reentry,
        "size": size_escalations,
        "impact": f"{tilt_pnl:.2f}",
        "color": "goodgreen" if tilt_pnl >= 0 else "badred"
    }

    # ===== TIER 3 =====
    all_var = df["pnl_usd"].var()
    regimes = []
    for date, sdf in df.groupby(df["entry_time"].dt.date):
        if len(sdf) < 2: reg = "Low Sample"
        else:
            mr = sdf["direction"].value_counts(normalize=True).iloc[0] if not sdf["direction"].value_counts().empty else 0
            pv = sdf["pnl_usd"].var()
            ad = sdf["duration_seconds"].mean()
            if mr >= 0.75 and pv < all_var: reg = "Trending"
            elif mr < 0.6 and ad < 600: reg = "Choppy"
            elif pv > 2*all_var: reg = "Volatile"
            else: reg = "Mixed"
        regimes.append({"date": date, "reg": reg, "trades": len(sdf), "pnl": f"{sdf['pnl_usd'].sum():.2f}", "color": "goodgreen" if sdf["pnl_usd"].sum() >= 0 else "badred"})
        
    pnl_samples = df["pnl_usd"].values
    sims, ruin_count, final_pnls = 10000, 0, []
    for _ in range(sims):
        sim = np.random.choice(pnl_samples, size=100, replace=True)
        eq = 10000 + np.cumsum(sim)
        if np.any(eq <= 9000): ruin_count += 1
        final_pnls.append(eq[-1] - 10000)
    plt.figure(figsize=(8, 3))
    plt.hist(final_pnls, bins=50, color='blue', alpha=0.7)
    plt.axvline(np.median(final_pnls), color='r', linestyle='dashed', linewidth=1)
    plt.title("Monte Carlo Final P&L Distribution")
    plt.tight_layout()
    plt.savefig("monte_carlo.png")
    plt.close()
    
    mc_metrics = {
        "med": f"{np.median(final_pnls):.2f}",
        "p5": f"{np.percentile(final_pnls, 5):.2f}",
        "p95": f"{np.percentile(final_pnls, 95):.2f}",
        "ruin": f"{(ruin_count/sims)*100:.1f}\\%"
    }
    
    rules_data = []
    try:
        with open(rules_file, "r") as f: rules_data = json.load(f).get("rules", [])
    except: pass
    rule_dict = {r["id"]: r for r in rules_data}
    v_df = []
    for date, sdf in df.groupby(df["entry_time"].dt.date):
        sdf = sdf.sort_values("entry_time")
        ls, tc, cp, llt = 0, 0, 0, None
        for idx, t in sdf.iterrows():
            tc += 1; cp += t["pnl_usd"]
            if "MAX_TRADES_PER_SESSION" in rule_dict and tc > rule_dict["MAX_TRADES_PER_SESSION"]["value"]:
                v_df.append({"rule": "MAX_TRADES_PER_SESSION", "id": t["trade_id"], "pnl": t["pnl_usd"]})
            if "DAILY_LOSS_LIMIT" in rule_dict and (cp - t["pnl_usd"]) <= -rule_dict["DAILY_LOSS_LIMIT"]["value"]:
                v_df.append({"rule": "DAILY_LOSS_LIMIT", "id": t["trade_id"], "pnl": t["pnl_usd"]})
            if "MAX_LOSSES_PER_SESSION" in rule_dict and ls >= rule_dict["MAX_LOSSES_PER_SESSION"]["value"]:
                v_df.append({"rule": "MAX_LOSSES_PER_SESSION", "id": t["trade_id"], "pnl": t["pnl_usd"]})
            if "NO_TRADE_AFTER_LOSS" in rule_dict and llt:
                mins = (t["entry_time"] - llt).total_seconds()/60
                if mins < rule_dict["NO_TRADE_AFTER_LOSS"]["minutes"]:
                    v_df.append({"rule": "NO_TRADE_AFTER_LOSS", "id": t["trade_id"], "pnl": t["pnl_usd"]})
            if "SIZE_LIMIT" in rule_dict and t["contracts"] > rule_dict["SIZE_LIMIT"]["value"]:
                v_df.append({"rule": "SIZE_LIMIT", "id": t["trade_id"], "pnl": t["pnl_usd"]})

            if not t["is_winner"]: ls += 1; llt = t["exit_time"]
            else: ls = 0
    rule_vio = []
    if v_df:
        rdf = pd.DataFrame(v_df).groupby("rule").agg(c=("id", "count"), p=("pnl", "sum")).reset_index()
        for _, r in rdf.iterrows():
            rule_name = r["rule"].replace("_", "\\_")
            rule_vio.append({"rule": rule_name, "count": r["c"], "pnl": f"{r['p']:.2f}", "color": "goodgreen" if r["p"] >= 0 else "badred"})

    df_sort["cum"] = df_sort["pnl_usd"].cumsum()
    eq_coords = " ".join([f"({r['trade_id']}, {r['cum']:.2f})" for _, r in df_sort.iterrows()])

    # ===== ACTIONABLE COACHING SUGGESTIONS =====
    suggestions = []
    
    if better_direction:
        suggestions.append(f"\\textbf{{Directional Bias:}} Your edge is heavily skewed towards \\textbf{{{better_direction}}} setups. Consider taking 50\\% size or skipping opposite direction signals completely.")
        
    if tilt_metrics["rapid"] > 0 or tilt_metrics["size"] > 0:
        suggestions.append(f"\\textbf{{Psychology Leak:}} Data shows revenge trading patterns ({tilt_metrics['rapid']} fast re-entries, {tilt_metrics['size']} size escalations). Implement a mandatory 15-minute screen break after any loss.")
        
    prob_ruin_float = (ruin_count/sims) * 100
    if prob_ruin_float > 10:
        suggestions.append(f"\\textbf{{Capital Preservation:}} Your Probability of Ruin is dangerously high ({prob_ruin_float:.1f}\\%!). To survive statistical variance, reduce your standard contract size immediately until the curve smooths out.")
        
    if rule_vio:
        violated_rules = [r["rule"] for r in rule_vio]
        suggestions.append(f"\\textbf{{Discipline Breach:}} You broke your system rules ({', '.join(violated_rules)}). An edge is mathematically meaningless without compliance. Focus solely on execution tomorrow, not P\\&L.")
        
    if not suggestions:
        suggestions.append("Your metrics are extremely solid. Maintain current sizing, stick to your hold times, and keep executing the system.")

    # ===== LATEX TEMPLATE =====
    latex_template = r'''\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[margin=1in]{geometry}
\usepackage{xcolor}
\usepackage{tcolorbox}
\usepackage{booktabs}
\usepackage{pgfplots}
\usepackage{graphicx}
\pgfplotsset{compat=1.18}
\usepackage{sectsty}
\usepackage{mathpazo} 

\definecolor{brandblue}{HTML}{0D47A1}
\definecolor{goodgreen}{HTML}{2E7D32}
\definecolor{badred}{HTML}{C62828}
\definecolor{surface}{HTML}{F8F9FA}
\sectionfont{\color{brandblue}}

\begin{document}
\begin{center}
{\Huge\bfseries\color{brandblue} Full-Spectrum Trading Analytics}\\[0.5em]
{\Large Complete Tier Analysis Report}\\[1em]
{\large Prepared for \textbf{Mission Credit Card}}\\[0.5em]
{\small Generated on \today}
\end{center}
\vspace{1em}

% >>> FREE TIER
\section*{Free Tier: Trade Log Transparency}
\begin{tcolorbox}[colframe=brandblue, colback=surface, title=Free Tier Headline, fonttitle=\bfseries]
\begin{tabular}{p{0.3\textwidth} p{0.3\textwidth} p{0.3\textwidth}}
\textbf{Total Net P\&L} & \textbf{Win Rate} & \textbf{Profit Factor} \\
{\Large \color{\VAR{pcolor}} \$\VAR{pnl}} & {\Large \VAR{wr}\%} & {\Large \VAR{pf}} \\
\end{tabular}\\[1em]
\textbf{Total Trades:} \VAR{trades} \quad \textbf{Expectancy:} \$\VAR{exp} \quad \textbf{Avg Win/Loss:} \$\VAR{aw} / \color{badred}\$\VAR{al}
\end{tcolorbox}

\vspace{0.5em}
\noindent\textbf{Direction Split:}\\
\begin{tabular}{@{} l r r l r @{}}
\toprule
\textbf{Direction} & \textbf{Trades} & \textbf{Win Rate} & \textbf{Net P\&L} & \textbf{Profit Factor} \\
\midrule
\BLOCK{for d in dstats}
\textbf{\VAR{d.dir}} & \VAR{d.trades} & \VAR{d.win_rate} & \color{\VAR{d.color}}\$\VAR{d.pnl} & \VAR{d.pf} \\
\BLOCK{endfor}
\bottomrule
\end{tabular}

\vspace{1em}
\noindent\textbf{Session Heatmap (Net P\&L by Entry Hour):}\\
\begin{center}
\includegraphics[width=0.9\textwidth]{session_heatmap.png}
\end{center}

\newpage
% >>> TIER 1
\section*{Tier 1: Edge Tracker}
\subsection*{Hold Time Analysis}
\begin{tabular}{@{} l r r r l r @{}}
\toprule
\textbf{Bucket} & \textbf{Trades} & \textbf{\% All} & \textbf{Win Rate} & \textbf{Net P\&L} & \textbf{Profit Factor} \\
\midrule
\BLOCK{for h in hold}
\textbf{\VAR{h.bucket}} & \VAR{h.trades} & \VAR{h.pct} & \VAR{h.wr} & \color{\VAR{h.color}}\$\VAR{h.pnl} & \VAR{h.pf} \\
\BLOCK{endfor}
\bottomrule
\end{tabular}

\vspace{1em}
\subsection*{Entry Quality Score (Proxy MFE/MAE)}
Average absolute friction (spread+slippage+fees) cost per trade: \textbf{\$\VAR{ev_fric} (\VAR{ev_pct}\% of gross move)}

\vspace{1em}
\subsection*{Streak Tracker}
\begin{tabular}{l l | l l}
\textbf{Max Win Streak:} & \VAR{s_mw} & \textbf{Avg Win Streak:} & \VAR{s_aw} \\
\textbf{Max Loss Streak:} & \VAR{s_ml} & \textbf{Avg Loss Streak:} & \VAR{s_al} \\
\end{tabular}
\vspace{1em}
\begin{center}
\begin{tikzpicture}
\begin{axis}[
    width=0.9\textwidth, height=4.5cm, grid=major,
    xlabel={Trade Number}, ylabel={Cumulative P\&L (\$)},
    axis line style={brandblue, thick}, x tick label style={font=\footnotesize}, y tick label style={font=\footnotesize}
]
\addplot[color=brandblue, mark=*, mark size=1.5pt] coordinates { (0, 0) \VAR{eq_coords} };
\end{axis}
\end{tikzpicture}
\end{center}

\vspace{1em}
% >>> TIER 2
\section*{Tier 2: Pattern Intelligence}
\subsection*{Best Setup Detector (N $\geq$ 3)}
\begin{tabular}{@{} l l l l r l r @{}}
\toprule
\textbf{Dir} & \textbf{Session} & \textbf{Duration} & \textbf{Size} & \textbf{Trades} & \textbf{Win Rate} & \textbf{Expectancy} \\
\midrule
\BLOCK{for s in setups}
\VAR{s.dir} & \VAR{s.session} & \VAR{s.dur} & \VAR{s.size} & \VAR{s.trades} & \VAR{s.wr} & \color{\VAR{s.color}}\$\VAR{s.exp} \\
\BLOCK{endfor}
\bottomrule
\end{tabular}

\vspace{1em}
\subsection*{Tilt Detection (Behavioral Flags)}
\begin{itemize}
\item \textbf{Rapid Re-entry Clusters} ($<$ 30m after loss): \VAR{t_rap}
\item \textbf{Size Escalations} (immediately after loss): \VAR{t_size}
\item \textbf{Est. P\&L Impact of Tilt Trades}: \color{\VAR{t_color}}\$\VAR{t_imp}
\end{itemize}

\newpage
% >>> TIER 3
\section*{Tier 3: Coaching Layer}
\subsection*{Personalised Regime Detection}
\begin{tabular}{@{} l l r l @{}}
\toprule
\textbf{Date} & \textbf{Regime} & \textbf{Trades} & \textbf{Session P\&L} \\
\midrule
\BLOCK{for r in regimes}
\VAR{r.date} & \VAR{r.reg} & \VAR{r.trades} & \color{\VAR{r.color}}\$\VAR{r.pnl} \\
\BLOCK{endfor}
\bottomrule
\end{tabular}

\vspace{1em}
\subsection*{Monte Carlo Risk Sizing}
Simulating 10,000 paths of 100 trades based on your historical P\&L distribution, with a \$10,000 starting account and \$1,000 drawdown threshold.\\

\vspace{0.5em}
\begin{tabular}{l l l l}
\textbf{Median Final P\&L:} & \$\VAR{mc_med} & \textbf{5th Percentile:} & \$\VAR{mc_p5} \\
\textbf{95th Percentile:} & \$\VAR{mc_p95} & \textbf{Prob of Ruin:} & \textbf{\color{badred}\VAR{mc_ruin}} \\
\end{tabular}
\begin{center}
\includegraphics[width=0.75\textwidth]{monte_carlo.png}
\end{center}

\vspace{1em}
\subsection*{Custom Rule Alerts}
\BLOCK{if r_vios}
The following system violations were flagged based on \texttt{rules.json}:\\

\begin{tabular}{@{} l r l @{}}
\toprule
\textbf{Rule Breached} & \textbf{Count} & \textbf{P\&L Impact} \\
\midrule
\BLOCK{for r in r_vios}
\VAR{r.rule} & \VAR{r.count} & \color{\VAR{r.color}}\$\VAR{r.pnl} \\
\BLOCK{endfor}
\bottomrule
\end{tabular}
\BLOCK{else}
\textbf{\color{goodgreen} Excellent discipline! Zero custom rule violations found.}
\BLOCK{endif}

\vspace{1em}
\subsection*{Actionable Coaching Directives}
\begin{tcolorbox}[colframe=badred!80!black, colback=surface, title=Critical Focus Areas]
\begin{itemize}
\BLOCK{for sug in suggestions}
\item \VAR{sug}
\BLOCK{endfor}
\end{itemize}
\end{tcolorbox}

\end{document}
'''
    
    env = jinja2.Environment(block_start_string='\BLOCK{', block_end_string='}', variable_start_string='\VAR{', variable_end_string='}', autoescape=False)
    template = env.from_string(latex_template)
    rendered = template.render(
        pnl=f"{total_pnl:.2f}", pcolor="goodgreen" if total_pnl >= 0 else "badred",
        wr=f"{win_rate:.1f}", pf=f"{profit_factor:.2f}", trades=total_trades, exp=f"{expectancy:.2f}",
        aw=f"{avg_win:.2f}", al=f"{abs(avg_loss):.2f}",
        dstats=direction_stats,
        hold=hold_stats, ev_fric=f"{avg_friction:.2f}", ev_pct=f"{avg_friction_pct:.1f}",
        s_mw=streak_metrics["max_win"], s_ml=streak_metrics["max_loss"],
        s_aw=f"{streak_metrics['avg_win']:.1f}", s_al=f"{streak_metrics['avg_loss']:.1f}",
        eq_coords=eq_coords,
        setups=setup_stats,
        t_rap=tilt_metrics["rapid"], t_size=tilt_metrics["size"], t_imp=tilt_metrics["impact"], t_color=tilt_metrics["color"],
        regimes=regimes,
        mc_med=mc_metrics["med"], mc_p5=mc_metrics["p5"], mc_p95=mc_metrics["p95"], mc_ruin=mc_metrics["ruin"],
        r_vios=rule_vio,
        suggestions=suggestions
    )
    
    with open(output_tex, "w") as f: f.write(rendered)
    print("Compiling Master PDF...")
    try:
        subprocess.run(["pdflatex", "-interaction=nonstopmode", output_tex], check=True)
        print("Success! Master PDF generated.")
    except Exception as e:
        print("Error during compilation:", e)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data.txt")
    parser.add_argument("--rules", default="rules.json")
    args = parser.parse_args()
    df = load_and_preprocess_data(args.input)
    render_full_report(df, rules_file=args.rules, output_tex="master_report.tex")
