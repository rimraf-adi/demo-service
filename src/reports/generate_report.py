import pandas as pd
import jinja2
import os
import subprocess
import glob

DATA_FILE = "data.txt"

def load_and_preprocess_data(filepath):
    print("Loading and preprocessing data...")
    data_lines = []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("Serial"):
                continue
            parts = line.split('\t')
            # Extract just the expected 10 columns
            if len(parts) >= 10:
                data_lines.append(parts[:10])
    
    df = pd.DataFrame(data_lines, columns=[
        "Serial", "Symbol", "Direction", "Contracts", "Open_Price", 
        "Open_Time", "Close_Price", "Close_Time", "Duration", "Net_PNL"
    ])
    
    # Deduplicate by Serial
    df['Serial'] = df['Serial'].astype(int)
    df = df.drop_duplicates(subset=["Serial"]).sort_values("Serial")
    
    # Clean Net PNL
    df["Net_PNL"] = df["Net_PNL"].astype(str).str.replace("$", "").str.replace(",", "").astype(float)
    
    # Dates
    df["Open_Time"] = pd.to_datetime(df["Open_Time"], format="%B %d, %Y at %I:%M:%S %p")
    df["Close_Time"] = pd.to_datetime(df["Close_Time"], format="%B %d, %Y at %I:%M:%S %p")
    df["Contracts"] = df["Contracts"].astype(int)
    
    return df

def generate_latex(df, output_tex):
    print("Computing metrics...")
    
    total_pnl = df["Net_PNL"].sum()
    total_trades = len(df)
    wins = df[df["Net_PNL"] > 0]
    losses = df[df["Net_PNL"] <= 0]
    
    win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
    profit_factor = round(wins["Net_PNL"].sum() / abs(losses["Net_PNL"].sum()), 2) if len(losses) > 0 else "Inf"
    avg_win = wins["Net_PNL"].mean() if len(wins) > 0 else 0
    avg_loss = losses["Net_PNL"].mean() if len(losses) > 0 else 0
    
    def get_color(val):
        return "goodgreen" if val > 0 else ("badred" if val < 0 else "black")
    
    direction_stats = []
    for d in ["Buy", "Sell"]:
        ddf = df[df["Direction"] == d]
        if len(ddf) > 0:
            d_pnl = ddf["Net_PNL"].sum()
            d_wins = ddf[ddf["Net_PNL"] > 0]
            d_losses = ddf[ddf["Net_PNL"] <= 0]
            d_wr = len(d_wins) / len(ddf) * 100
            
            d_pf = round(d_wins["Net_PNL"].sum() / abs(d_losses["Net_PNL"].sum()), 2) if len(d_losses) > 0 else "Inf"
            direction_stats.append({
                "dir": d, 
                "trades": len(ddf), 
                "pnl": f"{d_pnl:.2f}",
                "color": get_color(d_pnl),
                "win_rate": f"{d_wr:.1f}", 
                "pf": d_pf
            })

    # Equity Curve Coordinates for pgfplots
    df = df.sort_values("Serial", ascending=True)
    df["Cum_PNL"] = df["Net_PNL"].cumsum()
    equity_coords = " ".join([f"({row['Serial']}, {row['Cum_PNL']:.2f})" for _, row in df.iterrows()])
    
    # Recent trades table
    recent_trades = df.sort_values("Serial", ascending=False).head(15).copy()
    recent_trades["pnl_color"] = recent_trades["Net_PNL"].apply(get_color)
    recent_trades["Net_PNL"] = recent_trades["Net_PNL"].apply(lambda x: f"{x:.2f}")
    
    # -----------------------------
    # AI Explainability & Insights
    # -----------------------------
    explanations = []
    if len(wins) > 0 and len(losses) > 0:
        # Avoid ValueError if direction_stats is empty or 'pnl' strings fail floats
        try:
            best_dir = max(direction_stats, key=lambda x: float(x['pnl']))
            explanations.append(f"Your most profitable direction is \\textbf{{{best_dir['dir']}}} netting \\${best_dir['pnl']}. Consider focusing your specific setups here.")
        except Exception:
            pass
        
        # Duration analysis (approximate)
        df["Dur_Seconds"] = (pd.to_datetime(df["Close_Time"]) - pd.to_datetime(df["Open_Time"])).dt.total_seconds()
        fast_trades = df[df["Dur_Seconds"] < 300]
        slow_trades = df[df["Dur_Seconds"] >= 300]
        fast_pnl = fast_trades["Net_PNL"].sum()
        slow_pnl = slow_trades["Net_PNL"].sum()
        if fast_pnl > slow_pnl:
            explanations.append(f"Short duration trades ($<$ 5 min) generated \${fast_pnl:.2f} compared to \${slow_pnl:.2f} for longer holds. Scalping aligns better with your current edge.")
        else:
            explanations.append(f"Longer duration trades ($\\geq$ 5 min) outearned scalps (\${slow_pnl:.2f} vs \${fast_pnl:.2f}). Let winners run.")

    # Suggested improvements
    improvements = []
    if total_pnl < 0:
        improvements.append("Net P\\&L is negative. Consider cutting your sizing down to 1 contract exclusively until consistency improves.")
    if abs(avg_loss) > avg_win * 1.5 and avg_win > 0:
        improvements.append(f"Your average loss (\\${abs(avg_loss):.2f}) is significantly larger than your average win (\\${avg_win:.2f}). Implement a strict stop-loss rule to improve Expected Value.")
    if win_rate < 40 and total_trades >= 5:
        improvements.append(f"With a {win_rate:.1f}\\% win rate, try reducing trade frequency and only taking A+ setups. Patience will naturally lift this metric.")
    if not improvements:
        improvements.append("Solid underlying performance. Consider slowly scaling your contract size on your highest-conviction 'Buy' or 'Sell' setups while keeping risk parameters tight.")

    print("Rendering LaTeX...")
    latex_template = r'''\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[margin=1in]{geometry}
\usepackage{xcolor}
\usepackage{tcolorbox}
\usepackage{booktabs}
\usepackage{pgfplots}
\pgfplotsset{compat=1.18}
\usepackage{sectsty}

\usepackage{mathpazo} % nice font

% Define colors
\definecolor{brandblue}{HTML}{0D47A1}
\definecolor{goodgreen}{HTML}{2E7D32}
\definecolor{badred}{HTML}{C62828}
\definecolor{surface}{HTML}{F8F9FA}

\sectionfont{\color{brandblue}}

\begin{document}

\begin{center}
{\Huge\bfseries\color{brandblue} Trading Performance Analytics}\\[0.5em]
{\Large Executive Summary Report}\\[1em]
{\large Prepared for \textbf{Mission Credit Card}}\\[0.5em]
{\small Generated on \today}
\end{center}
\vspace{1em}

% Headline stats
\begin{tcolorbox}[colframe=brandblue, colback=surface, title=Free Tier --- Trade Log Transparency, title filled=true, fonttitle=\bfseries\large]
\begin{center}
\renewcommand{\arraystretch}{1.5}
\begin{tabular}{p{0.3\textwidth} p{0.3\textwidth} p{0.3\textwidth}}
\textbf{Total Net P\&L} & \textbf{Win Rate} & \textbf{Profit Factor} \\
{\Large \color{\VAR{pnl_color}} \$\VAR{total_pnl}} & {\Large \VAR{win_rate}\%} & {\Large \VAR{profit_factor}} \\
\end{tabular}
\end{center}
\vspace{0.5em}
\hrule
\vspace{0.5em}
\begin{center}
\renewcommand{\arraystretch}{1.2}
\begin{tabular}{cccc}
\textbf{Total Trades:} & \VAR{total_trades} & & \\
\textbf{Average Win:} & \color{goodgreen} \$\VAR{avg_win} & \textbf{Average Loss:} & \color{badred} \$\VAR{avg_loss} \\
\end{tabular}
\end{center}
\end{tcolorbox}

\vspace{1.5em}
\begin{tcolorbox}[colframe=brandblue, colback=white, title=Explainability \& Core Insights, fonttitle=\bfseries]
\begin{itemize}
\setlength\itemsep{0.3em}
\BLOCK{for exp in explanations}
\item \VAR{exp}
\BLOCK{endfor}
\end{itemize}
\end{tcolorbox}

\vspace{1.5em}
\begin{tcolorbox}[colframe=goodgreen!80!black, colback=white, title=Suggested Improvements, fonttitle=\bfseries]
\begin{itemize}
\setlength\itemsep{0.3em}
\BLOCK{for imp in improvements}
\item \VAR{imp}
\BLOCK{endfor}
\end{itemize}
\end{tcolorbox}

\vspace{1.5em}
\subsection*{Directional Split}
\begin{center}
\renewcommand{\arraystretch}{1.2}
\begin{tabular}{@{} l r r r r @{}}
\toprule
\textbf{Direction} & \textbf{Trades} & \textbf{Win Rate} & \textbf{Profit Factor} & \textbf{Net P\&L} \\
\midrule
\BLOCK{for d in direction_stats}
\textbf{\VAR{d.dir}} & \VAR{d.trades} & \VAR{d.win_rate}\% & \VAR{d.pf} & \color{\VAR{d.color}} \$\VAR{d.pnl} \\
\BLOCK{endfor}
\bottomrule
\end{tabular}
\end{center}

\vspace{1em}
\subsection*{Equity Curve}
\begin{center}
\begin{tikzpicture}
\begin{axis}[
    width=0.9\textwidth,
    height=6.5cm,
    grid=major,
    grid style={dashed, gray!30},
    xlabel={Trade Number (Serial)},
    ylabel={Cumulative P\&L (\$)},
    tick label style={font=\footnotesize},
    axis line style={brandblue, thick},
]
\addplot[
    color=brandblue,
    mark=*,
    mark size=1.5pt,
    thick
] coordinates {
    (0, 0) \VAR{equity_coords}
};
\end{axis}
\end{tikzpicture}
\end{center}

\vspace{1em}
\subsection*{Recent Trades Review}
\begin{center}
\renewcommand{\arraystretch}{1.1}
\begin{tabular}{@{} c c c c l r @{}}
\toprule
\textbf{Serial} & \textbf{Symbol} & \textbf{Dir} & \textbf{Qty} & \textbf{Duration} & \textbf{Net P\&L} \\
\midrule
\BLOCK{for t in recent_trades}
\VAR{t.Serial} & \VAR{t.Symbol} & \VAR{t.Direction} & \VAR{t.Contracts} & \VAR{t.Duration} & \color{\VAR{t.pnl_color}} \$\VAR{t.Net_PNL} \\
\BLOCK{endfor}
\bottomrule
\end{tabular}
\end{center}

\end{document}
'''
    
    env = jinja2.Environment(
        block_start_string='\BLOCK{',
        block_end_string='}',
        variable_start_string='\VAR{',
        variable_end_string='}',
        comment_start_string='\#{',
        comment_end_string='}',
        line_statement_prefix='%%',
        line_comment_prefix='%#',
        trim_blocks=True,
        autoescape=False,
    )
    
    template = env.from_string(latex_template)
    rendered_tex = template.render(
        total_pnl=f"{total_pnl:.2f}",
        pnl_color=get_color(total_pnl),
        win_rate=f"{win_rate:.1f}",
        profit_factor=profit_factor,
        total_trades=total_trades,
        avg_win=f"{avg_win:.2f}",
        avg_loss=f"{avg_loss:.2f}",
        direction_stats=direction_stats,
        equity_coords=equity_coords,
        recent_trades=recent_trades.to_dict('records'),
        explanations=explanations,
        improvements=improvements
    )
    
    with open(output_tex, "w") as f:
        f.write(rendered_tex)
    print(f"LaTeX written to {output_tex}")

def compile_pdf(tex_file):
    print("Compiling PDF...")
    try:
        subprocess.run(["pdflatex", "-interaction=nonstopmode", tex_file], check=True)
        print("Success! PDF generated.")
    except subprocess.CalledProcessError as e:
        print("Error during pdflatex compilation.")
        print(e)
    # Clean up aux files
    for ext in ["aux", "log", "out"]:
        f = tex_file.replace(".tex", f".{ext}")
        if os.path.exists(f):
            os.remove(f)

if __name__ == "__main__":
    tex_filename = "report.tex"
    df = load_and_preprocess_data(DATA_FILE)
    generate_latex(df, tex_filename)
    compile_pdf(tex_filename)
