# -*- coding: utf-8 -*-
"""
Backtester with:
- SMA combo signals (weighted or majority vote)
- Regime-aware buffers (vol/liquidity profiling)
- Regime/bias engine (trend vs mean-revert, incl. contrarian Markov/autocorr modes)
- YoY drift projection (growth-aware thresholds)
- Cooldown after any trade signal
- Behavioral "loss-pain" filters (gap crashes, near 52w lows)
- Downtrend guardrails (bear-state: don't follow trend downward)
- Official-close P&L tracking, per-window summaries, PNG plots

Extras in this version:
- FIX: plot signal marker indexing (no boolean-length error)
- Per-run printed summary lines with returns/fees/alpha
- VERBOSE_TRADES toggle to print each execution
- NEW: Model-ready datasets (per-run + combined) with decision features, reasons, and forward outcomes

Outputs per (symbol, window):
- daily_with_signals.csv, equity_curve.csv, trades.csv, diagnostics.csv, plot.png, ml_decisions.csv
Plus cross-ticker summary.csv, portfolio_totals.csv, and ml_dataset_all.csv (combined).

CSV inputs must contain at least: timestamp, open, high, low, close, volume
Optional: market_status ('regular' rows kept when USE_MARKET_STATUS=True)
"""

from pathlib import Path
import numpy as np
import pandas as pd
import os
import sys, subprocess
import matplotlib.pyplot as plt

# =========================
# USER: data sources
# =========================
DATA_SOURCES = {
    "QS":   r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\QS_30s.csv",
    "SLDP": r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\SLDP_30s.csv",
    "MSFT": r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\MSFT_30s.csv",
    "CHGG": r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\CHGG_30s.csv",
    "AI":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\AI_30s.csv",
    "NVDA":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\NVDA_30s.csv",
    "TSM":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\TSM_30s.csv",
    "GOOGL":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\GOOGL_30s.csv",
    "AMD":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\AMD_30s.csv",
    "PAYO":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\PAYO_30s.csv",
    "LCID":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\LCID_30s.csv",
    "PLUG":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\PLUG_30s.csv",
    "NKLA":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\NKLA_30s.csv",
    "BYND":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\BYND_30s.csv",
    "IBM":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\IBM_30s.csv",
    "RGTI":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\RGTI_30s.csv",
    "QBTS":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\QBTS_30s.csv",
    "QUBT":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\QUBT_30s.csv",
    "IONQ":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\IONQ_30s.csv"
    
}

# Rolling windows (name -> # trading days)
TEST_WINDOWS_DAYS = {"42d": 42, "1y": 252}

# Date-pinned windows (optional)
DATE_WINDOWS = [
    # {"name": "year_calendar", "start": "2024-08-01", "end": "2025-08-01"},
]

# =========================
# GLOBAL CONFIG
# =========================
USE_MARKET_STATUS   = True
TZ_MARKET           = "US/Eastern"
TRADING_DAYS        = 252

PRICE_COL           = "close_last"

# Strategy mode: "weighted" or "majority"
STRATEGY_MODE       = "weighted"
SMA_COLS            = ["SMA_1Y","SMA_1M","SMA_1W","SMA_1D"]
MIN_VOTES           = 3  # for "majority"

# Trend (YoY) projection
APPLY_TREND         = True
ASSUMED_TREND_YOY   = 0.05
PROJECT_DAYS        = 1

# Execution & costs
SLIPPAGE_PCT        = 0.0005
FEE_PCT             = 0.0002
FEE_FIXED           = 0.00
START_CASH          = 100.0
START_STOCK         = 100.0

# Cooldown
COOLDOWN_DAYS       = 1

# Pre-window regime thresholds
VOL_21_HIGH         = 0.03
ADTV_21_LOW         = 5e7

# Buffer presets
HV_K_BUFFER, HV_MIN_BUF, HV_MAX_BUF = 1.25, 0.02, 0.10
LV_K_BUFFER, LV_MIN_BUF, LV_MAX_BUF = 1.00, 0.010, 0.03

# Bias engine mode
BIAS_MODE      = "contrarian_markov_weekly"

# Autocorr params
BIAS_LOOKBACK  = 60
BIAS_THRESH    = 0.06
BIAS_STEP_DAYS = 5

# Markov params
MARKOV_LOOKBACK = 60
MARKOV_EDGE     = 0.04
MARKOV_EPS      = 0.001
MARKOV_ALPHA    = 1.0

# Behavioral filters & guardrails
ENABLE_BEHAVIORAL_FILTERS = True
ENABLE_BEAR_GUARD        = True

GAP_CRASH_MULT_ATR   = 1.5
NEAR_52W_LOW_BAND    = 0.01
FILTER_COOLDOWN_DAYS = 2

BEAR_RET63_THRESH      = -0.10
BEAR_MA200_SLOPE_MIN   = 0.0
BEAR_BLOCK_TREND_BUYS  = True

# Output directory
OUT_DIR = Path("multi_sma_contrarian_outputs")

# Printing toggles
PRINT_PER_RUN     = True   # one-liner summary per (symbol, window)
VERBOSE_TRADES    = False  # print each trade line

# Plot display options
OPEN_SAVED_PNG = True              # auto-open each plot.png in OS viewer
SHOW_MATPLOTLIB_WINDOWS = False    # optional plt.show()
MAX_AUTO_OPEN = 8
PRINT_PLOT_PATHS = True
_opened_count = 0  # internal counter; do not touch

# === ML dataset options ===
SAVE_ML_DATASETS   = True
ML_HORIZONS        = [1, 3, 5]     # forward-look horizons (trading days)
INCLUDE_MARKOV_EDGE_FEATURE = False  # turn on if you want per-day Markov edge (slower)

# =========================
# Tiny formatting helpers
# =========================
def _fmt_pct(x):
    try: return f"{float(x):.2%}"
    except: return "NaN"

def _fmt_money(x):
    try: return f"${float(x):,.2f}"
    except: return "NaN"

# =========================
# Data & feature engineering
# =========================
def load_30s_to_daily(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    if "timestamp" not in df.columns or "close" not in df.columns:
        raise ValueError(f"{csv_path} must include 'timestamp' and 'close' columns.")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp")
    if USE_MARKET_STATUS and "market_status" in df.columns:
        df = df[df["market_status"] == "regular"].copy()
    df["ts_local"] = df["timestamp"].dt.tz_convert(TZ_MARKET)
    df["date"] = df["ts_local"].dt.date
    daily = (
        df.groupby("date", as_index=False)
          .agg(
              close_mean=("close","mean"),
              close_last=("close","last"),
              high_max=("high","max"),
              low_min=("low","min"),
              vol_sum=("volume","sum"),
          )
          .sort_values("date")
          .reset_index(drop=True)
    )
    daily["date"] = pd.to_datetime(daily["date"])
    return daily

def add_smas(d: pd.DataFrame) -> pd.DataFrame:
    r = d["close_mean"]
    d["SMA_1Y"] = r.rolling(TRADING_DAYS, min_periods=TRADING_DAYS).mean()
    d["SMA_1M"] = r.rolling(21,            min_periods=21).mean()
    d["SMA_1W"] = r.rolling(5,             min_periods=5).mean()
    d["SMA_1D"] = r.rolling(1,             min_periods=1).mean()
    return d

def add_labels_and_vol(d: pd.DataFrame) -> pd.DataFrame:
    d["close_next"] = d[PRICE_COL].shift(-1)
    d["y"] = (d["close_next"] > d[PRICE_COL]).astype(int)
    d["ret_1"] = d[PRICE_COL].pct_change()
    d["vol_21"] = d["ret_1"].rolling(21).std()
    d["$vol"] = d["close_mean"] * d["vol_sum"]
    d["adtv_21"] = d["$vol"].rolling(21).mean()
    return d

def add_guardrails_and_filters(d: pd.DataFrame) -> pd.DataFrame:
    close = d[PRICE_COL].astype(float)
    prev_close = close.shift(1)
    high = d["high_max"].astype(float)
    low  = d["low_min"].astype(float)

    # ATR(14)
    tr1 = (high - low).abs()
    tr2 = (high - prev_close).abs()
    tr3 = (low  - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    d["atr14"]     = tr.rolling(14).mean()
    d["atr14_pct"] = d["atr14"] / close

    # Close-to-close "gap"
    d["gap_close"] = close.pct_change()

    # Behavioral triggers
    d["gap_crash"]    = (d["gap_close"] <= -GAP_CRASH_MULT_ATR * d["atr14_pct"]).astype(int)
    d["near_52w_low"] = (close <= close.rolling(252).min() * (1.0 + NEAR_52W_LOW_BAND)).astype(int)

    # Rolling cool-off mask for MR longs
    if FILTER_COOLDOWN_DAYS > 0:
        block_src = (d["gap_crash"] | d["near_52w_low"]).astype(int)
        d["block_long_mr"] = block_src.rolling(FILTER_COOLDOWN_DAYS, min_periods=1).max().astype(bool)
    else:
        d["block_long_mr"] = (d["gap_crash"] | d["near_52w_low"]).astype(bool)

    # Bear-state guardrail
    ma200    = close.rolling(200).mean()
    slope200 = ma200.diff(10) / 10.0
    ret63    = close.pct_change(63)
    d["bear_state"] = ((close < ma200) &
                       (slope200 < BEAR_MA200_SLOPE_MIN) &
                       (ret63 <= BEAR_RET63_THRESH)).fillna(False).astype(bool)
    return d

# =========================
# Profiling & helpers
# =========================
def profile_regime(vol_21, adtv_21):
    is_high_vol = (vol_21 is not None and np.isfinite(vol_21) and vol_21 >= VOL_21_HIGH)
    is_low_liq  = (adtv_21 is not None and np.isfinite(adtv_21) and adtv_21 <= ADTV_21_LOW)
    if is_high_vol or is_low_liq:
        return dict(
            WEIGHTS={"SMA_1Y":0.10,"SMA_1M":0.30,"SMA_1W":0.40,"SMA_1D":0.20},
            BUY_SELL_PCT=0.40,
            K_BUFFER=HV_K_BUFFER, MIN_BUF=HV_MIN_BUF, MAX_BUF=HV_MAX_BUF,
            REGIME="HighVol/LowLiq"
        )
    else:
        return dict(
            WEIGHTS={"SMA_1Y":0.50,"SMA_1M":0.30,"SMA_1W":0.15,"SMA_1D":0.05},
            BUY_SELL_PCT=0.20,
            K_BUFFER=LV_K_BUFFER, MIN_BUF=LV_MIN_BUF, MAX_BUF=LV_MAX_BUF,
            REGIME="LargeCap/Steady"
        )

def per_day_buffer(vol_21_today, K_BUFFER, MIN_BUF, MAX_BUF):
    if vol_21_today is None or not np.isfinite(vol_21_today) or vol_21_today <= 0:
        return MIN_BUF
    return float(np.clip(K_BUFFER * float(vol_21_today), MIN_BUF, MAX_BUF))

def daily_drift(yoy_rate, project_days=PROJECT_DAYS):
    return (1.0 + yoy_rate) ** (project_days / TRADING_DAYS) - 1.0

def trend_project(value, yoy_rate, apply=True):
    if not apply or not np.isfinite(value):
        return value
    return value * (1.0 + daily_drift(yoy_rate))

# =========================
# Bias engines
# =========================
def choose_bias_from_autocorr(series_returns, lookback=60, thresh=0.05):
    r = series_returns.dropna().iloc[-lookback:]
    if len(r) < 10:
        return "trend"
    acf1 = r.autocorr(lag=1)
    if acf1 <= -abs(thresh): return "revert"
    if acf1 >=  abs(thresh): return "trend"
    return "trend"

def _markov_counts_from_returns(r, eps=0.001):
    r = r.dropna()
    if len(r) < 2:
        return 0,0,0,0,0
    s = r.apply(lambda x: 1 if x > eps else (-1 if x < -eps else 0))
    uu = ud = du = dd = 0
    for a, b in zip(s[:-1], s[1:]):
        if a == 0 or b == 0: continue
        if   a== 1 and b== 1: uu += 1
        elif a== 1 and b==-1: ud += 1
        elif a==-1 and b== 1: du += 1
        elif a==-1 and b==-1: dd += 1
    s_last = s.iloc[-1] if len(s) > 0 else 0
    return uu, ud, du, dd, s_last

def _markov_edge(r, eps=0.001, alpha=1.0):
    uu, ud, du, dd, s_last = _markov_counts_from_returns(r, eps)
    puu = (uu + alpha) / (uu + ud + 2*alpha) if (uu + ud) >= 0 else 0.5
    pud = (ud + alpha) / (uu + ud + 2*alpha) if (uu + ud) >= 0 else 0.5
    pdd = (dd + alpha) / (dd + du + 2*alpha) if (dd + du) >= 0 else 0.5
    pdu = (du + alpha) / (dd + du + 2*alpha) if (dd + du) >= 0 else 0.5
    if s_last == 1:  p_trend, p_revert = puu, pud
    elif s_last == -1: p_trend, p_revert = pdd, pdu
    else:            p_trend = p_revert = 0.5
    return float(p_trend - p_revert), float(p_trend), float(p_revert), int(s_last)

def build_bias_series_autocorr(daily, base_bias,
                               mode="static", lookback=60, thresh=0.05, step_days=5):
    idx = daily.index
    if mode == "static":
        return pd.Series([base_bias]*len(idx), index=idx, dtype=object)
    r = daily["ret_1"].copy()
    acf1 = r.rolling(lookback).corr(r.shift(1))
    def decide(a):
        if not np.isfinite(a): return None
        if a <= -abs(thresh): return "revert"
        if a >=  abs(thresh): return "trend"
        return None
    bias_ser = pd.Series(index=idx, dtype=object)
    if mode == "adaptive_daily":
        last = base_bias
        for i in idx:
            d = decide(acf1.loc[i]); last = d if d is not None else last
            bias_ser.loc[i] = last
        return bias_ser
    if mode == "adaptive_weekly":
        last = base_bias; i0 = 0
        while i0 < len(idx):
            i1 = min(i0 + step_days, len(idx))
            d = decide(acf1.iloc[i1-1]); last = d if d is not None else last
            bias_ser.iloc[i0:i1] = last; i0 = i1
        return bias_ser
    raise ValueError("Invalid autocorr mode")

def build_bias_series_markov(daily, base_bias,
                             mode="markov_daily", lookback=60, edge_thresh=0.05,
                             eps=0.001, alpha=1.0, step_days=5):
    idx = daily.index; r = daily["ret_1"]
    if mode == "markov_static":
        return pd.Series([base_bias]*len(idx), index=idx, dtype=object)
    def decide(end_i, last_bias):
        seg = r.iloc[max(0, end_i - lookback + 1): end_i + 1]
        if len(seg.dropna()) < 10: return last_bias
        edge, _, _, _ = _markov_edge(seg, eps=eps, alpha=alpha)
        if edge >=  edge_thresh: return "trend"
        if edge <= -edge_thresh: return "revert"
        return last_bias
    bias_ser = pd.Series(index=idx, dtype=object)
    if mode == "markov_daily":
        last = base_bias
        for i in range(len(idx)):
            last = decide(i, last); bias_ser.iat[i] = last
        return bias_ser
    if mode == "markov_weekly":
        last = base_bias; i0 = 0
        while i0 < len(idx):
            i1 = min(i0 + step_days, len(idx))
            last = decide(i1-1, last)
            bias_ser.iloc[i0:i1] = last; i0 = i1
        return bias_ser
    raise ValueError("Invalid Markov mode")

def build_bias_series_contrarian_markov(daily, lookback=60, edge_thresh=0.05,
                                        eps=0.001, alpha=1.0, mode="contrarian_markov_daily",
                                        step_days=5) -> pd.Series:
    idx = daily.index
    r = daily["ret_1"]
    def decide(end_i):
        seg = r.iloc[max(0, end_i - lookback + 1): end_i + 1]
        if len(seg.dropna()) < 10: return "trend"
        edge, _, _, _ = _markov_edge(seg, eps=eps, alpha=alpha)
        return "revert" if abs(edge) >= edge_thresh else "trend"
    bias_ser = pd.Series(index=idx, dtype=object)
    if mode == "contrarian_markov_daily":
        for i in range(len(idx)): bias_ser.iat[i] = decide(i)
        return bias_ser
    if mode == "contrarian_markov_weekly":
        i0 = 0
        while i0 < len(idx):
            i1 = min(i0 + step_days, len(idx))
            b = decide(i1 - 1)
            bias_ser.iloc[i0:i1] = b
            i0 = i1
        return bias_ser
    raise ValueError("mode must be 'contrarian_markov_daily' or 'contrarian_markov_weekly'")

def build_bias_series_contrarian_autocorr(daily, lookback=60, thresh=0.05,
                                          mode="contrarian_autocorr_daily", step_days=5) -> pd.Series:
    idx = daily.index
    r = daily["ret_1"].copy()
    acf1 = r.rolling(lookback).corr(r.shift(1))
    def decide(val):
        if not np.isfinite(val): return "trend"
        return "revert" if abs(val) >= thresh else "trend"
    bias_ser = pd.Series(index=idx, dtype=object)
    if mode == "contrarian_autocorr_daily":
        for i in idx: bias_ser.loc[i] = decide(acf1.loc[i])
        return bias_ser
    if mode == "contrarian_autocorr_weekly":
        i0 = 0
        while i0 < len(idx):
            i1 = min(i0 + step_days, len(idx))
            b = decide(acf1.iloc[i1 - 1])
            bias_ser.iloc[i0:i1] = b
            i0 = i1
        return bias_ser
    raise ValueError("mode must be 'contrarian_autocorr_daily' or 'contrarian_autocorr_weekly'")

# =========================
# Signal construction
# =========================
def composite_from_weights(row, weights):
    smas = {k: row.get(k, np.nan) for k in weights.keys()}
    valid = {k: v for k, v in smas.items() if np.isfinite(v)}
    if not valid: return np.nan
    wsum = sum(weights[k] for k in valid.keys())
    if wsum == 0: return np.nan
    return sum(weights[k] * valid[k] for k in valid.keys()) / wsum

def make_signals_weighted(d, weights, bias_series,
                          apply_trend, yoy_rate,
                          K_BUFFER, MIN_BUF, MAX_BUF):
    sig = np.full(len(d), -1, dtype=np.int32)
    block = d["block_long_mr"] if ENABLE_BEHAVIORAL_FILTERS else pd.Series(False, index=d.index)
    bear  = d["bear_state"]    if ENABLE_BEAR_GUARD        else pd.Series(False, index=d.index)
    for i, row in d.iterrows():
        combo = composite_from_weights(row, weights)
        if not np.isfinite(combo): continue
        combo_proj = trend_project(combo, yoy_rate, apply_trend)
        buf = per_day_buffer(row.get("vol_21", np.nan), K_BUFFER, MIN_BUF, MAX_BUF)
        upper = combo_proj * (1.0 + buf)
        lower = combo_proj * (1.0 - buf)
        px = row[PRICE_COL]
        day_bias = bias_series.iat[i] if pd.notna(bias_series.iat[i]) else "trend"
        if day_bias == "trend":
            cand = 1 if px > upper else (0 if px < lower else -1)
            if cand == 1 and bear.iat[i] and BEAR_BLOCK_TREND_BUYS: cand = -1
        else:  # revert
            cand = 0 if px > upper else (1 if px < lower else -1)
            if cand == 1 and block.iat[i]: cand = -1
        sig[i] = cand
    return pd.Series(sig, index=d.index, name="signal")

def make_signals_majority(d, sma_cols, bias_series,
                          apply_trend, yoy_rate,
                          K_BUFFER, MIN_BUF, MAX_BUF,
                          min_votes: int = 3):
    sig = np.full(len(d), -1, dtype=np.int32)
    for i, row in d.iterrows():
        px = row[PRICE_COL]
        vol = row.get("vol_21", np.nan)
        buf = per_day_buffer(vol, K_BUFFER, MIN_BUF, MAX_BUF)
        up_votes = down_votes = 0
        for c in sma_cols:
            sma = row.get(c, np.nan)
            if not np.isfinite(sma): continue
            thr = trend_project(float(sma), yoy_rate, apply_trend)
            up_thr = thr * (1.0 + buf)
            dn_thr = thr * (1.0 - buf)
            if px > up_thr: up_votes += 1
            elif px < dn_thr: down_votes += 1
        day_bias = bias_series.iat[i] if pd.notna(bias_series.iat[i]) else "trend"
        if day_bias == "trend":
            if up_votes >= min_votes: cand = 1
            elif down_votes >= min_votes: cand = 0
            else: cand = -1
            if cand == 1 and ENABLE_BEAR_GUARD and d["bear_state"].iat[i] and BEAR_BLOCK_TREND_BUYS:
                cand = -1
        else:
            if up_votes >= min_votes: cand = 0
            elif down_votes >= min_votes: cand = 1
            else: cand = -1
            if cand == 1 and ENABLE_BEHAVIORAL_FILTERS and d["block_long_mr"].iat[i]:
                cand = -1
        sig[i] = cand
    return pd.Series(sig, index=d.index, name="signal")

# =========================
# Backtest, plotting & reporting
# =========================
def backtest(d, i0, iN, signals, buy_sell_pct):
    close = d[PRICE_COL].values
    dates = d["date"].values
    preds = signals.values

    price0 = close[i0]
    shares = START_STOCK / price0
    cash   = float(START_CASH)
    total_fees = 0.0

    curve_dates, curve_value, trades = [], [], []

    for i in range(i0, iN):  # last test day: value only
        px = close[i]; sig = preds[i]
        side = None; exec_price = None; qty = 0.0; fees = 0.0

        if sig == 1 and cash > 0:
            exec_price = px * (1.0 + SLIPPAGE_PCT)
            spend_target = buy_sell_pct * cash
            denom = exec_price * (1.0 + FEE_PCT)
            qty = max(0.0, (spend_target - FEE_FIXED) / denom) if denom > 0 else 0.0
            cost = qty * exec_price; fees = cost * FEE_PCT + FEE_FIXED
            if cost + fees > cash:
                qty = max(0.0, (cash - FEE_FIXED) / (exec_price * (1.0 + FEE_PCT)))
                cost = qty * exec_price; fees = cost * FEE_PCT + FEE_FIXED
            if qty > 0:
                shares += qty; cash -= (cost + fees); side = "BUY"

        elif sig == 0 and shares > 0:
            qty = buy_sell_pct * shares
            exec_price = px * (1.0 - SLIPPAGE_PCT)
            gross = qty * exec_price; fees = gross * FEE_PCT + FEE_FIXED
            net  = max(0.0, gross - fees)
            if qty > 0:
                shares -= qty; cash += net; side = "SELL"

        total_fees += float(fees)
        equity = cash + shares * px
        curve_dates.append(dates[i]); curve_value.append(equity)

        if side:
            trades.append({"date": pd.to_datetime(dates[i]), "side": side, "signal": int(sig),
                           "exec_price": float(exec_price), "trade_shares": float(qty),
                           "fees_paid": float(fees), "cash_after": float(cash),
                           "shares_after": float(shares), "equity_after": float(equity)})
            if VERBOSE_TRADES:
                print(f"  {pd.to_datetime(dates[i]).date()} {side:<4} "
                      f"px={_fmt_money(exec_price)} qty={qty:,.4f} "
                      f"fees={_fmt_money(fees)} cash={_fmt_money(cash)} shares={shares:,.4f} "
                      f"equity={_fmt_money(equity)}")

    final_equity = cash + shares * close[iN]
    curve_dates.append(dates[iN]); curve_value.append(final_equity)

    equity_df = pd.DataFrame({"date": pd.to_datetime(curve_dates), "equity": curve_value})
    trades_df = pd.DataFrame(trades)
    return equity_df, trades_df, final_equity, total_fees

def summarize(d, signals, i0, iN, final_equity, total_fees):
    y = d["y"].values; close = d[PRICE_COL].values; dates = d["date"].values; sig = signals.values
    idx = np.arange(len(y)); mask = (idx >= i0) & (idx <= iN) & (sig != -1)
    y_true = y[mask]; y_pred = sig[mask]
    total_n = int(mask.sum()); total_correct = int((y_true == y_pred).sum())
    acc = (total_correct / total_n) if total_n > 0 else np.nan

    buy_mask  = mask & (sig == 1); sell_mask = mask & (sig == 0)
    buy_n  = int(buy_mask.sum()); sell_n = int(sell_mask.sum())
    buy_acc  = (y[buy_mask]==1).mean() if buy_n>0 else np.nan
    sell_acc = (y[sell_mask]==0).mean() if sell_n>0 else np.nan

    start_price = float(close[i0]); end_price = float(close[iN])
    bh_final = (START_STOCK / start_price) * end_price

    return dict(
        test_start=str(pd.to_datetime(dates[i0]).date()),
        test_end=str(pd.to_datetime(dates[iN]).date()),
        start_price=start_price, end_price=end_price,
        buys=buy_n, buy_precision=float(buy_acc) if buy_n>0 else None,
        sells=sell_n, sell_precision=float(sell_acc) if sell_n>0 else None,
        overall_accuracy=float(acc) if total_n>0 else None,
        final_portfolio=float(final_equity),
        start_total=float(START_CASH + START_STOCK),
        buy_hold_100_stock=float(bh_final),
        total_fees=float(total_fees),
        decisions=total_n, correct=total_correct,
    )

def diagnostics(d, signals, i0, iN):
    df = d.loc[i0:iN, ["date",PRICE_COL,"y","ret_1","vol_21"]].copy()
    df["signal"] = signals.loc[i0:iN].values
    close = d[PRICE_COL].values
    df["ret_next"] = (pd.Series(close).shift(-1) / pd.Series(close) - 1).iloc[i0:iN+1].values
    out = {}
    for label, mask in {"BUY (1)": df["signal"]==1, "SELL (0)": df["signal"]==0}.items():
        n = int(mask.sum())
        if n:
            r = df.loc[mask, "ret_next"]; hit = (df.loc[mask, "y"] == (1 if "BUY" in label else 0)).mean()
            out[label] = {"n_trades": n, "hit_rate": float(hit),
                          "avg_ret_next": float(r.mean()), "median_ret_next": float(r.median()),
                          "avg_abs_ret_next": float(r.abs().mean())}
    out["HOLD (-1)"] = {"n_days": int((df["signal"]==-1).sum())}
    return pd.DataFrame(out).T

def _plot_backtest(sym, window_name, daily, equity_df, i0, iN, signals):
    out_dir = OUT_DIR / sym / window_name
    out_dir.mkdir(parents=True, exist_ok=True)

    seg = daily.iloc[i0:iN+1].copy().set_index("date")
    price = seg[PRICE_COL]

    # Align equity curve to daily dates
    eq = equity_df.set_index("date")["equity"].reindex(seg.index).ffill()

    # Buy & hold = $100 stock only (matches summary metric)
    shares_bh = START_STOCK / price.iloc[0]
    bh = shares_bh * price

    fig, ax1 = plt.subplots(figsize=(11, 6))
    ax1.plot(seg.index, eq, label="Algo Portfolio ($)")
    ax1.plot(seg.index, bh, label="Buy & Hold ($100 stock)", linestyle="--")
    ax1.set_ylabel("Portfolio Value ($)")
    ax1.set_xlabel("Date")

    ax2 = ax1.twinx()
    ax2.plot(seg.index, price, label=f"{sym} Price ($)", alpha=0.55)
    ax2.set_ylabel(f"{sym} Price ($)")

    # shape-aligned markers
    if signals is not None:
        s = signals.iloc[i0:iN]  # decisions happen on i0..iN-1
        s_aligned = pd.Series(s.values, index=seg.index[:-1])
        buy_idx  = s_aligned.index[s_aligned == 1]
        sell_idx = s_aligned.index[s_aligned == 0]
        ax2.scatter(buy_idx,  price.loc[buy_idx],  marker="^", s=36, alpha=0.7, label="Buy signal")
        ax2.scatter(sell_idx, price.loc[sell_idx], marker="v", s=36, alpha=0.7, label="Sell signal")

    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc="best", frameon=True)
    ax1.set_title(f"{sym} — {window_name}: Algo vs Buy&Hold vs Price")
    fig.tight_layout()

    # Save + print/open
    png_path = out_dir / "plot.png"
    fig.savefig(png_path, dpi=150)
    plt.close(fig)

    if PRINT_PLOT_PATHS:
        print(f"[{sym}:{window_name}] plot -> {png_path}")

    if OPEN_SAVED_PNG:
        global _opened_count
        if _opened_count < MAX_AUTO_OPEN:
            try:
                if os.name == "nt":
                    os.startfile(png_path)  # type: ignore[attr-defined]
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", str(png_path)])
                else:
                    subprocess.Popen(["xdg-open", str(png_path)])
                _opened_count += 1
            except Exception as e:
                print(f"  (could not auto-open plot: {e})")

    if SHOW_MATPLOTLIB_WINDOWS:
        try:
            import matplotlib.pyplot as _plt
            _plt.figure()
            _plt.show()
        except Exception as e:
            print(f"  (matplotlib show failed: {e})")

# =========================
# Window runners + ML dataset builder
# =========================
def build_bias_series_over_full_index(daily, pre_returns):
    if BIAS_MODE in ("static","adaptive_daily","adaptive_weekly"):
        base_bias = choose_bias_from_autocorr(pre_returns, lookback=BIAS_LOOKBACK, thresh=BIAS_THRESH)
        bias_series = build_bias_series_autocorr(daily, base_bias, mode=BIAS_MODE,
                                                 lookback=BIAS_LOOKBACK, thresh=BIAS_THRESH, step_days=BIAS_STEP_DAYS)
        info = f"{BIAS_MODE} (acf1) base={base_bias}"
    elif BIAS_MODE in ("markov_static","markov_daily","markov_weekly"):
        seg = pre_returns.dropna().iloc[-MARKOV_LOOKBACK:]
        edge, *_ = _markov_edge(seg, eps=MARKOV_EPS, alpha=MARKOV_ALPHA)
        base_bias = "trend" if edge >= 0 else "revert"
        bias_series = build_bias_series_markov(daily, base_bias, mode=BIAS_MODE, lookback=MARKOV_LOOKBACK,
                                               edge_thresh=MARKOV_EDGE, eps=MARKOV_EPS, alpha=MARKOV_ALPHA,
                                               step_days=BIAS_STEP_DAYS)
        info = f"{BIAS_MODE} (Markov) base={base_bias} edge≥{MARKOV_EDGE:.2f}"
    elif BIAS_MODE in ("contrarian_markov_daily","contrarian_markov_weekly"):
        bias_series = build_bias_series_contrarian_markov(daily, lookback=MARKOV_LOOKBACK, edge_thresh=MARKOV_EDGE,
                                                          eps=MARKOV_EPS, alpha=MARKOV_ALPHA,
                                                          mode=BIAS_MODE, step_days=BIAS_STEP_DAYS)
        info = f"{BIAS_MODE} (Markov contrarian) |edge|≥{MARKOV_EDGE:.2f} → revert"
    elif BIAS_MODE in ("contrarian_autocorr_daily","contrarian_autocorr_weekly"):
        bias_series = build_bias_series_contrarian_autocorr(daily, lookback=BIAS_LOOKBACK, thresh=BIAS_THRESH,
                                                            mode=BIAS_MODE, step_days=BIAS_STEP_DAYS)
        info = f"{BIAS_MODE} (acf1 contrarian) |acf1|≥{BIAS_THRESH:.2f} → revert"
    else:
        raise ValueError("Unknown BIAS_MODE")
    return bias_series, info

def _apply_cooldown_to_actions(actions, cooldown_days):
    # returns final_actions, cooldown_applied_flags
    if cooldown_days <= 0:
        return actions.copy(), [False]*len(actions)
    final = actions.copy()
    cool = 0
    applied = [False]*len(actions)
    for i in range(len(final)):
        if cool > 0:
            if final[i] in (0, 1):
                applied[i] = True
            final[i] = -1
            cool -= 1
            continue
        if final[i] in (0,1):
            cool = cooldown_days
    return final, applied

def _band_distance(px, upper, lower):
    # positive distance from nearest threshold when outside bands; 0 inside
    if np.isfinite(upper) and px > upper:
        return (px / upper) - 1.0
    if np.isfinite(lower) and px < lower:
        return (lower / px) - 1.0
    return 0.0

def build_decision_dataset(d, i0, iN, bias_series, regime, weights, apply_trend, yoy_rate,
                           K_BUFFER, MIN_BUF, MAX_BUF, min_votes, strategy_mode):
    """
    Build a per-day decision dataset including:
      - inputs: price, SMAs, buffer, upper/lower, votes, bias, vol/adtv/atr, regime info, YoY
      - pre_guard_action, guard blocks, final_action (after guards+cooldown)
      - forward returns for ML_HORIZONS and success/edge labels
    """
    close = d[PRICE_COL]
    vol21 = d["vol_21"]
    block = d["block_long_mr"] if ENABLE_BEHAVIORAL_FILTERS else pd.Series(False, index=d.index)
    bear  = d["bear_state"]    if ENABLE_BEAR_GUARD        else pd.Series(False, index=d.index)

    # forward returns for horizons
    fwd_map = {H: (close.shift(-H) / close - 1.0) for H in ML_HORIZONS}

    rows = []
    pre_actions = []
    post_guard_actions = []

    for i in range(i0, iN):  # decisions on i0..iN-1
        row = d.iloc[i]
        px = float(row[PRICE_COL])
        bias = bias_series.iat[i] if pd.notna(bias_series.iat[i]) else "trend"
        buf = per_day_buffer(row.get("vol_21", np.nan), K_BUFFER, MIN_BUF, MAX_BUF)

        # Defaults for fields
        upper = lower = combo_proj = np.nan
        up_votes = down_votes = np.nan
        band_pos = "inside"
        pre = -1
        blocked_bear = False
        blocked_behavior = False

        if strategy_mode == "weighted":
            combo = composite_from_weights(row, weights)
            if np.isfinite(combo):
                combo_proj = trend_project(combo, yoy_rate, apply_trend)
                upper = combo_proj * (1.0 + buf)
                lower = combo_proj * (1.0 - buf)
                if px > upper: band_pos = "above_upper"
                elif px < lower: band_pos = "below_lower"
                else: band_pos = "inside"

                if bias == "trend":
                    pre = 1 if px > upper else (0 if px < lower else -1)
                    if pre == 1 and bear.iat[i] and BEAR_BLOCK_TREND_BUYS:
                        blocked_bear = True
                else:  # revert
                    pre = 0 if px > upper else (1 if px < lower else -1)
                    if pre == 1 and block.iat[i]:
                        blocked_behavior = True

        else:  # majority
            for c in SMA_COLS:
                sma = row.get(c, np.nan)
                if not np.isfinite(sma): continue
                thr = trend_project(float(sma), yoy_rate, apply_trend)
                up_thr = thr * (1.0 + buf)
                dn_thr = thr * (1.0 - buf)
                if px > up_thr: up_votes = (0 if np.isnan(up_votes) else up_votes) + 1
                elif px < dn_thr: down_votes = (0 if np.isnan(down_votes) else down_votes) + 1
            up_votes = 0 if np.isnan(up_votes) else int(up_votes)
            down_votes = 0 if np.isnan(down_votes) else int(down_votes)

            if bias == "trend":
                pre = 1 if up_votes >= min_votes else (0 if down_votes >= min_votes else -1)
                if pre == 1 and ENABLE_BEAR_GUARD and d["bear_state"].iat[i] and BEAR_BLOCK_TREND_BUYS:
                    blocked_bear = True
            else:
                pre = 0 if up_votes >= min_votes else (1 if down_votes >= min_votes else -1)
                if pre == 1 and ENABLE_BEHAVIORAL_FILTERS and d["block_long_mr"].iat[i]:
                    blocked_behavior = True

            # For majority mode, define band_pos by tally if you want:
            if up_votes >= min_votes: band_pos = "above_upper"
            elif down_votes >= min_votes: band_pos = "below_lower"
            else: band_pos = "inside"

        post_guard = -1 if (blocked_bear or blocked_behavior) else pre

        pre_actions.append(pre)
        post_guard_actions.append(post_guard)

        # build record
        rec = {
            "idx": i,
            "date": pd.to_datetime(row["date"]),
            "price": px,
            "bias": bias,
            "buffer": float(buf) if np.isfinite(buf) else np.nan,
            "upper": float(upper) if np.isfinite(upper) else np.nan,
            "lower": float(lower) if np.isfinite(lower) else np.nan,
            "combo_proj": float(combo_proj) if np.isfinite(combo_proj) else np.nan,
            "up_votes": up_votes, "down_votes": down_votes, "min_votes": min_votes if strategy_mode=="majority" else np.nan,
            "band_pos": band_pos,
            "pre_guard_action": int(pre),
            "blocked_bear_guard": bool(blocked_bear),
            "blocked_behavioral": bool(blocked_behavior),
            "post_guard_action": int(post_guard),
            "cooldown_applied": False,   # set later
            "final_action": None,        # set later
            # context features
            "vol_21": float(row["vol_21"]),
            "adtv_21": float(row["adtv_21"]),
            "atr14_pct": float(row["atr14_pct"]),
            "ret_1": float(row["ret_1"]),
            "gap_close": float(row["gap_close"]),
            "near_52w_low": bool(row["near_52w_low"]),
            "gap_crash": bool(row["gap_crash"]),
            "block_long_mr": bool(row["block_long_mr"]),
            "bear_state": bool(row["bear_state"]),
            "regime": regime["REGIME"],
            "k_buffer": K_BUFFER, "min_buf": MIN_BUF, "max_buf": MAX_BUF,
            "buy_sell_pct": regime["BUY_SELL_PCT"],
            "apply_trend": bool(apply_trend),
            "yoy_rate": float(yoy_rate),
            "strategy_mode": strategy_mode,
        }

        # distance from nearest band (for aggression sizing features)
        rec["band_distance"] = _band_distance(px, upper, lower)

        # optional: include raw SMAs (useful features)
        for c in SMA_COLS:
            rec[c] = float(row[c]) if np.isfinite(row[c]) else np.nan

        # forward returns + labels
        for H, ser in fwd_map.items():
            fr = ser.iat[i] if i < len(ser) else np.nan
            rec[f"fwd_ret_{H}"] = float(fr) if pd.notna(fr) else np.nan
            # success label: buy wants +ret, sell wants -ret, hold = NaN
            if pre == -1:
                rec[f"success_pre_{H}"] = np.nan
            else:
                want = 1 if pre == 1 else -1
                rec[f"success_pre_{H}"] = float(1.0 if (pd.notna(fr) and np.sign(fr) == want) else 0.0)
            if post_guard == -1:
                rec[f"signed_edge_post_{H}"] = np.nan
                rec[f"success_post_{H}"] = np.nan
            else:
                sign = 1 if post_guard == 1 else -1
                rec[f"signed_edge_post_{H}"] = float(sign * fr) if pd.notna(fr) else np.nan
                rec[f"success_post_{H}"] = float(1.0 if (pd.notna(fr) and np.sign(fr) == sign) else 0.0)

        rows.append(rec)

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # apply cooldown to post_guard_action to get final_action
    final_actions, cd_flags = _apply_cooldown_to_actions(df["post_guard_action"].tolist(), COOLDOWN_DAYS)
    df["final_action"] = final_actions
    df["cooldown_applied"] = cd_flags

    # final-action labels, too
    for H in ML_HORIZONS:
        fr = df[f"fwd_ret_{H}"]
        def _succ_final(a, r):
            if a == -1 or not pd.notna(r): return np.nan
            return float(1.0 if (np.sign(r) == (1 if a==1 else -1)) else 0.0)
        df[f"success_final_{H}"] = [ _succ_final(a, r) for a, r in zip(df["final_action"], fr) ]
        df[f"signed_edge_final_{H}"] = [ ( (1 if a==1 else -1) * r if (a!=-1 and pd.notna(r)) else np.nan )
                                         for a, r in zip(df["final_action"], fr) ]

    return df

# NEW: single-line printed summary per run
def _print_run_summary_line(sym, window_name, summ):
    start_total = summ["start_total"]
    final       = summ["final_portfolio"]
    bh_final    = summ["buy_hold_100_stock"]
    ret         = (final / start_total) - 1.0 if start_total else np.nan
    bh_ret      = (bh_final / start_total) - 1.0 if start_total else np.nan
    alpha       = (final - bh_final)
    print(f"[{sym}:{window_name}] RESULT  "
          f"Period {summ['test_start']}→{summ['test_end']}  "
          f"Algo={_fmt_money(final)} ({_fmt_pct(ret)})  "
          f"BH={_fmt_money(bh_final)} ({_fmt_pct(bh_ret)})  "
          f"Alpha={_fmt_money(alpha)}  Fees={_fmt_money(summ['total_fees'])}  "
          f"Acc={_fmt_pct(summ['overall_accuracy']) if summ.get('overall_accuracy') is not None else 'NaN'}  "
          f"Buys={summ['buys']} Sells={summ['sells']}")

def run_window(sym, daily, window_name, i0, iN):
    # Profile on PRE-TEST window only
    pre = daily.iloc[:i0].copy()
    vol_21_train  = float(pre["vol_21"].iloc[-1])
    adtv_21_train = float(pre["adtv_21"].iloc[-1])
    regime = profile_regime(vol_21_train, adtv_21_train)
    weights = regime["WEIGHTS"]
    buy_sell_pct = regime["BUY_SELL_PCT"]
    K_BUFFER, MIN_BUF, MAX_BUF = regime["K_BUFFER"], regime["MIN_BUF"], regime["MAX_BUF"]

    # Per-day bias series across full index (base decisions from pre)
    bias_series, bias_info = build_bias_series_over_full_index(daily, pre["ret_1"])

    # Per-window YoY calibration (from pre-window segment)
    if len(pre) >= TRADING_DAYS:
        yoy_est = float(np.clip(pre[PRICE_COL].iloc[-1] / pre[PRICE_COL].iloc[-TRADING_DAYS] - 1.0, -0.5, 0.5))
        yoy_src = "estimated_from_pre_window"
    else:
        yoy_est = ASSUMED_TREND_YOY
        yoy_src = "fallback_ASSUMED_TREND_YOY"

    print(f"[{sym}:{window_name}] regime={regime['REGIME']}  vol_21_train={vol_21_train:.2%}  adtv_21_train=${adtv_21_train:,.0f}")
    print(f"[{sym}:{window_name}] mode={STRATEGY_MODE}  weights={weights}  buy_sell_pct={int(buy_sell_pct*100)}%  "
          f"buf=clip({K_BUFFER}*vol_21, {MIN_BUF:.2%}, {MAX_BUF:.2%})  min_votes={MIN_VOTES if STRATEGY_MODE=='majority' else '-'}")
    print(f"[{sym}:{window_name}] bias={bias_info}")
    print(f"[{sym}:{window_name}] trend apply={APPLY_TREND} YoY_used={yoy_est:.2%}  source={yoy_src}  project_days={PROJECT_DAYS}")
    print(f"[{sym}:{window_name}] guards: behavioral={ENABLE_BEHAVIORAL_FILTERS} "
          f"bear_guard={ENABLE_BEAR_GUARD} bear_block_trend_buys={BEAR_BLOCK_TREND_BUYS}")

    # Signals
    if STRATEGY_MODE == "weighted":
        signals = make_signals_weighted(daily, weights, bias_series, APPLY_TREND, yoy_est, K_BUFFER, MIN_BUF, MAX_BUF)
    elif STRATEGY_MODE == "majority":
        signals = make_signals_majority(daily, SMA_COLS, bias_series, APPLY_TREND, yoy_est,
                                        K_BUFFER, MIN_BUF, MAX_BUF, min_votes=MIN_VOTES)
    else:
        raise ValueError("STRATEGY_MODE must be 'weighted' or 'majority'.")

    # Cooldown
    signals = apply_cooldown(signals, COOLDOWN_DAYS)

    # Backtest
    equity_df, trades_df, final_equity, total_fees = backtest(daily, i0, iN, signals, buy_sell_pct)

    # Plot and save
    _plot_backtest(sym, window_name, daily, equity_df, i0, iN, signals)

    # Summary & diags
    summ = summarize(daily, signals, i0, iN, final_equity, total_fees)
    if PRINT_PER_RUN:
        _print_run_summary_line(sym, window_name, summ)
    diag = diagnostics(daily, signals, i0, iN)

    # ML dataset
    ml_df = pd.DataFrame()
    if SAVE_ML_DATASETS:
        ml_df = build_decision_dataset(daily, i0, iN, bias_series, regime, weights,
                                       APPLY_TREND, yoy_est, K_BUFFER, MIN_BUF, MAX_BUF,
                                       MIN_VOTES, STRATEGY_MODE)
        if not ml_df.empty:
            ml_df.insert(0, "symbol", sym)
            ml_df.insert(1, "window", window_name)

    return summ, signals, bias_series, equity_df, trades_df, diag, regime, weights, buy_sell_pct, (K_BUFFER, MIN_BUF, MAX_BUF), ml_df

def run_days_window_for_symbol(sym: str, daily: pd.DataFrame, window_name: str, window_days: int):
    if len(daily) <= window_days + 60:
        raise ValueError(f"{sym}:{window_name} not enough history (need > {window_days+60} days incl. warmups).")
    i0 = len(daily) - window_days
    iN = len(daily) - 1
    return run_window(sym, daily, window_name, i0, iN)

def run_date_window_for_symbol(sym: str, daily: pd.DataFrame, window_name: str, start_date: str, end_date: str):
    start = pd.Timestamp(start_date); end = pd.Timestamp(end_date)
    mask = (daily["date"] >= start) & (daily["date"] <= end)
    if not mask.any():
        raise ValueError(f"{sym}:{window_name} date range has no overlap with data.")
    i0 = int(mask.idxmax())
    iN = int(mask[::-1].idxmax())
    if iN - i0 < 5:
        raise ValueError(f"{sym}:{window_name} window too short after filters.")
    if i0 < 60:
        raise ValueError(f"{sym}:{window_name} insufficient pre-window history (need >=60 days before start).")
    return run_window(sym, daily, window_name, i0, iN)

# =========================
# IO helpers & summary
# =========================
def _save(sym, window_name, daily, signals, bias_series, equity_df, trades_df, diag, ml_df):
    out = OUT_DIR / sym / window_name
    out.mkdir(parents=True, exist_ok=True)
    daily.assign(signal=signals, bias=bias_series).to_csv(out / "daily_with_signals.csv", index=False)
    equity_df.to_csv(out / "equity_curve.csv", index=False)
    trades_df.to_csv(out / "trades.csv", index=False)
    diag.to_csv(out / "diagnostics.csv")
    if SAVE_ML_DATASETS and not ml_df.empty:
        ml_df.to_csv(out / "ml_decisions.csv", index=False)

def enrich_summary_row(summ, sym, window_name, regime, weights, buy_sell_pct, buf_tuple):
    K_BUFFER, MIN_BUF, MAX_BUF = buf_tuple
    summ.update(dict(
        symbol=sym, period=window_name, regime=regime["REGIME"], bias_mode=BIAS_MODE,
        buy_sell_pct=buy_sell_pct, weights=weights,
        trend_apply=APPLY_TREND, trend_yoy="per-window-estimated", project_days=PROJECT_DAYS,
        k_buffer=K_BUFFER, min_buf=MIN_BUF, max_buf=MAX_BUF,
        strategy_mode=STRATEGY_MODE, min_votes=MIN_VOTES if STRATEGY_MODE=="majority" else None,
    ))
    return summ

def _compute_portfolio_totals(df: pd.DataFrame):
    required = {"period","final_portfolio","start_total","buy_hold_100_stock","total_fees"}
    if not required.issubset(df.columns) or df.empty:
        print("! portfolio totals skipped (no successful runs).")
        return
    grp = (df.groupby("period", as_index=False)
             .agg(start_total=("start_total","sum"),
                  final_total=("final_portfolio","sum"),
                  bh_total=("buy_hold_100_stock","sum"),
                  fees_total=("total_fees","sum")))
    for frame in (grp,):
        frame["pnl"]         = frame["final_total"] - frame["start_total"]
        frame["bh_pnl"]      = frame["bh_total"] - frame["start_total"]
        frame["alpha_vs_bh"] = frame["pnl"] - frame["bh_pnl"]
        frame["return_%"]    = np.where(frame["start_total"]>0, frame["final_total"]/frame["start_total"] - 1, np.nan)
        frame["bh_return_%"] = np.where(frame["start_total"]>0, frame["bh_total"]/frame["start_total"] - 1, np.nan)
    overall = pd.DataFrame({
        "period":     ["ALL"],
        "start_total":[grp["start_total"].sum()],
        "final_total":[grp["final_total"].sum()],
        "bh_total":   [grp["bh_total"].sum()],
        "fees_total": [grp["fees_total"].sum()],
    })
    overall["pnl"]         = overall["final_total"] - overall["start_total"]
    overall["bh_pnl"]      = overall["bh_total"] - overall["start_total"]
    overall["alpha_vs_bh"] = overall["pnl"] - overall["bh_pnl"]
    overall["return_%"]    = np.where(overall["start_total"]>0, overall["final_total"]/overall["start_total"] - 1, np.nan)
    overall["bh_return_%"] = np.where(overall["start_total"]>0, overall["bh_total"]/overall["start_total"] - 1, np.nan)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = pd.concat([grp, overall], ignore_index=True)
    out = out[["period","start_total","final_total","pnl","return_%",
               "bh_total","bh_pnl","bh_return_%","alpha_vs_bh","fees_total"]]
    out.to_csv(OUT_DIR / "portfolio_totals.csv", index=False)
    printable = out.copy()
    printable["return_%"]    = printable["return_%"].apply(_fmt_pct)
    printable["bh_return_%"] = printable["bh_return_%"].apply(_fmt_pct)
    print("\n== PORTFOLIO TOTALS (Aggregated Across Tickers) ==")
    print(printable.to_string(index=False))
    print(f"\nWrote portfolio totals to {OUT_DIR / 'portfolio_totals.csv'}")

def _write_summary(summaries):
    if not summaries:
        print("\n== SUMMARY ==\n(no successful runs to summarize)")
        return
    cols = [
        "symbol","period","regime","strategy_mode","min_votes","bias_mode","buy_sell_pct",
        "test_start","test_end","start_price","end_price",
        "decisions","correct","overall_accuracy",
        "buys","buy_precision","sells","sell_precision",
        "final_portfolio","start_total","buy_hold_100_stock","total_fees",
        "k_buffer","min_buf","max_buf","trend_apply","trend_yoy","project_days","weights"
    ]
    df = pd.DataFrame(summaries)
    cols = [c for c in cols if c in df.columns] + [c for c in df.columns if c not in cols]
    df = df[cols]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_DIR / "summary.csv", index=False)
    print("\n== SUMMARY ==")
    view = df[["symbol","period","regime","strategy_mode","bias_mode",
               "final_portfolio","buy_hold_100_stock","overall_accuracy","buys","sells"]].copy()
    view["overall_accuracy"] = view["overall_accuracy"].apply(_fmt_pct)
    print(view.to_string(index=False))
    print(f"\nWrote cross-ticker summary to {OUT_DIR / 'summary.csv'}")
    _compute_portfolio_totals(df)

# =========================
# Main
# =========================
def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summaries = []
    ml_frames = []  # collect all per-run ML datasets

    for sym, path in DATA_SOURCES.items():
        if not os.path.exists(path):
            print(f"!! Skipping {sym}: file not found -> {path}")
            continue
        try:
            print(f"\n=== {sym} ===")
            daily = load_30s_to_daily(Path(path))
            daily = add_smas(daily)
            daily = add_labels_and_vol(daily)
            daily = add_guardrails_and_filters(daily)  # guards

            need = [
                "SMA_1Y","SMA_1M","SMA_1W","SMA_1D",
                PRICE_COL,"y","vol_21","adtv_21","ret_1",
                "atr14_pct","block_long_mr","bear_state"
            ]
            daily = daily.dropna(subset=need).reset_index(drop=True)

            # Rolling windows
            for wname, wdays in TEST_WINDOWS_DAYS.items():
                try:
                    (summ, signals, bias_series, equity_df, trades_df, diag, regime,
                     weights, buy_sell_pct, buf_tuple, ml_df) = run_days_window_for_symbol(sym, daily, wname, wdays)
                    _save(sym, wname, daily, signals, bias_series, equity_df, trades_df, diag, ml_df)
                    summaries.append(enrich_summary_row(summ, sym, wname, regime, weights, buy_sell_pct, buf_tuple))
                    if SAVE_ML_DATASETS and not ml_df.empty:
                        ml_frames.append(ml_df)
                except Exception as e:
                    print(f"!! {sym}:{wname} error: {e}")

            # Date-pinned windows
            for win in DATE_WINDOWS:
                try:
                    wname = win["name"]
                    (summ, signals, bias_series, equity_df, trades_df, diag, regime,
                     weights, buy_sell_pct, buf_tuple, ml_df) = run_date_window_for_symbol(
                        sym, daily, wname, win["start"], win["end"]
                    )
                    _save(sym, wname, daily, signals, bias_series, equity_df, trades_df, diag, ml_df)
                    summaries.append(enrich_summary_row(summ, sym, wname, regime, weights, buy_sell_pct, buf_tuple))
                    if SAVE_ML_DATASETS and not ml_df.empty:
                        ml_frames.append(ml_df)
                except Exception as e:
                    print(f"!! {sym}:{wname} error: {e}")

        except Exception as e:
            print(f"!! {sym} error: {e}")

    # Combined ML corpus
    if SAVE_ML_DATASETS and ml_frames:
        all_ml = pd.concat(ml_frames, ignore_index=True)
        all_ml.to_csv(OUT_DIR / "ml_dataset_all.csv", index=False)
        print(f"\n[ML] Wrote combined dataset with {len(all_ml):,} rows -> {OUT_DIR / 'ml_dataset_all.csv'}")
        # tiny peek
        print(all_ml.head(3).to_string(index=False))

    _write_summary(summaries)

# Cooldown wrapper to keep legacy name
def apply_cooldown(signals: pd.Series, cooldown_days: int) -> pd.Series:
    final, _ = _apply_cooldown_to_actions(signals.tolist(), cooldown_days)
    return pd.Series(final, index=signals.index, name="signal")

if __name__ == "__main__":
    main()
