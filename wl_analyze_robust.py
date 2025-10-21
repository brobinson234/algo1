# wl_analyze_robust.py
import glob, numpy as np, pandas as pd

DETAIL_GLOB = r'.\out\wl_*.csv'  # adjust if needed
MIN_ROLLS   = 60                 # require enough rolls per (symbol, tag)
DD_FLOOR    = 0.05               # 5% dd floor when computing Calmar
WINSOR_Q    = 0.01               # winsorize 1% tails

def winsorize(s, q=WINSOR_Q):
    lo, hi = s.quantile(q), s.quantile(1-q)
    return s.clip(lower=lo, upper=hi)

def robust_calmar(cagr, maxdd, dd_floor=DD_FLOOR):
    return cagr / np.maximum(np.abs(maxdd), dd_floor)

def main():
    files = glob.glob(DETAIL_GLOB)
    if not files:
        raise SystemExit("No detail CSVs found.")
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)

    # Recompute calmars with dd floor (more stable), then uplifts
    df["rl_calmar_adj"]   = robust_calmar(df["rl_cagr"],   df["rl_maxdd"])
    df["rule_calmar_adj"] = robust_calmar(df["rule_cagr"], df["rule_maxdd"])
    df["upl_calmar_adj"]  = df["rl_calmar_adj"] - df["rule_calmar_adj"]

    # Winsorize uplifts (robust to single blow-ups)
    for col in ["upl_calmar_adj","upl_cagr","upl_sharpe","upl_dd_improve"]:
        if col in df.columns:
            df[col + "_w"] = winsorize(df[col])

    # Only consider combos with sufficient coverage
    g = (df.groupby(["symbol","tag"])
            .agg(
                rolls=("upl_calmar_adj","count"),
                median_upl_calmar=("upl_calmar_adj","median"),
                mean_upl_calmar_w=("upl_calmar_adj_w","mean"),
                hit_calmar=("upl_calmar_adj", lambda s: (s > 0).mean()),
                mean_upl_dd_w=("upl_dd_improve_w","mean"),
                hit_dd=("upl_dd_improve", lambda s: (s > 0).mean()),
                median_upl_sharpe=("upl_sharpe","median"),
                median_upl_cagr=("upl_cagr","median"),
            )
            .reset_index()
       )

    g = g[g["rolls"] >= MIN_ROLLS].copy()

    # Select BEST tag per symbol by robust calmar (median first, then winsorized mean as tiebreak)
    g["_rank"] = g.groupby("symbol")["median_upl_calmar"].rank(ascending=False, method="first")
    best = (g.sort_values(["symbol","median_upl_calmar","mean_upl_calmar_w"], ascending=[True,False,False])
              .groupby("symbol", as_index=False)
              .head(1))

    print("\n=== RECOMMENDED TAG PER SYMBOL (robust) ===")
    print(best[["symbol","tag","rolls","median_upl_calmar","hit_calmar","mean_upl_dd_w","hit_dd","median_upl_sharpe"]].to_string(index=False))

    # Pull the median knobs for each winning (symbol, tag)
    df_knobs = (df.merge(best[["symbol","tag"]], on=["symbol","tag"]))
    knobs = (df_knobs.groupby(["symbol","tag"], as_index=False)
             .agg(lambda_neg=("p_lambda_neg","median"),
                  lambda_dd=("p_lambda_dd","median"),
                  reward_clip=("p_reward_clip","median"),
                  regime_penalty=("p_regime_penalty","median"),
                  high_atr_q=("p_high_atr_q","median"),
                  turnover_penalty=("p_turnover_penalty","median"))
            )
    knobs.to_csv(".\\out\\per_symbol_knobs.csv", index=False)
    print("\nWrote .\\out\\per_symbol_knobs.csv")

if __name__ == "__main__":
    main()
