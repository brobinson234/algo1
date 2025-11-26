from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict

import numpy as np
import pandas as pd

EPS = 1e-9

# -----------------------------
# S11 / S12 knobs (from notebook)
# -----------------------------
S11_ACTIVATION_GOOD = 5   # correct non-HOLDs in a row to activate
S11_DEACTIVATION_BAD = 3  # consecutive wrong non-HOLDs to deactivate
S11_AGE_CAP = 60.0
S11_AGE_DIV = 10.0

S12_ACTIVATION_GOOD = 5   # correct in a row to activate
S12_DEACTIVATION_BAD = 4  # total wrong while active to deactivate
S12_AGE_CAP = 60.0
S12_AGE_DIV = 10.0


# ============================================================================
# 1. BASE BUILDER (extracted from Cell D in review_infers4.ipynb)
# ============================================================================

# ============================================================================
# 1. BASE BUILDER (UPDATED loader that handles daily + intraday variants)
# ============================================================================

# Map many historical names → unified schema (from review_infers4)
RENAME_MAP = {
    # date/time
    "date_bar": "date",
    "bar_date": "date",
    "date_iso": "date",
    "day": "date",
    "timestamp": "timestamp_utc",
    "time_utc": "timestamp_utc",
    "ts_utc": "timestamp_utc",
    "ts": "timestamp_utc",
    # price fields
    "close": "price",
    "last": "price",
    "last_price": "price",
    "price_3pm": "price",
    "price_cutoff": "price",
    "price_live": "price",
    # bands
    "m": "mid",
    "u": "upper",
    "l": "lower",
    # policy / signals
    "policy": "bias",
    "regime": "bias",
    "pre_signal": "pre_sig",
    "presig": "pre_sig",
    "signal": "sig",
    "signal_final": "sig",
    "action": "side",
    "sig_text": "side",
}


def _normalize_side(val: object) -> str | float:
    """Normalize side-like values into 'BUY'/'SELL'/'HOLD' or NaN."""
    if pd.isna(val):
        return np.nan
    s = str(val).strip().upper()
    if s in {"BUY", "B", "LONG", "+1", "1"}:
        return "BUY"
    if s in {"SELL", "S", "SHORT", "0"}:
        return "SELL"
    if s in {"HOLD", "H", "NEUTRAL", "FLAT", "-1"}:
        return "HOLD"
    # last-ditch numeric
    try:
        i = int(float(s))
        return {1: "BUY", 0: "SELL", -1: "HOLD"}.get(i, np.nan)
    except Exception:
        return np.nan


def _normalize_infer_df(df: pd.DataFrame) -> pd.DataFrame:
    """Apply RENAME_MAP and basic hygiene so we end up with date/price/side/pos_frac."""
    df = df.copy()

    # rename known variants
    overlap = set(RENAME_MAP) & set(df.columns)
    if overlap:
        df = df.rename(columns={k: RENAME_MAP[k] for k in overlap})

    # 🔧 if there's no explicit date but we have UTC timestamps, convert to US/Eastern
    if "date" not in df.columns and "timestamp_utc" in df.columns:
        dt_utc = pd.to_datetime(df["timestamp_utc"], errors="coerce", utc=True)
        # trading calendar: US Eastern
        dt_ny = dt_utc.dt.tz_convert("America/New_York")
        # strip timezone & keep the calendar day (midnight local)
        df["date"] = dt_ny.dt.normalize().dt.tz_localize(None)

    # normalize side if present
    if "side" in df.columns:
        df["side"] = df["side"].map(_normalize_side)

    # pos_frac default
    if "pos_frac" not in df.columns:
        df["pos_frac"] = 1.0

    return df


def load_all_inf_from_logs(logs_dir: Path, src_kind: str) -> pd.DataFrame:
    """
    Load and concatenate all infer_*.csv from a logs directory, normalizing columns.

    src_kind is just a label: 'daily', 'intraday', etc.
    """
    logs_dir = Path(logs_dir)
    pattern = "infer_*.csv"
    files = sorted(logs_dir.glob(pattern))
    print(f"[load_all_inf] dir={logs_dir.resolve()} pattern={pattern} files={len(files)} ({src_kind})")

    if not files:
        return pd.DataFrame()

    dfs = []
    for p in files:
        try:
            df = pd.read_csv(p)
            df["source_file"] = p.name
            df["src_kind"] = src_kind
            df = _normalize_infer_df(df)
            dfs.append(df)
        except Exception as e:
            print(f"[load_all_inf] ERROR reading {p}: {e}")

    if not dfs:
        return pd.DataFrame()

    all_inf = pd.concat(dfs, ignore_index=True, sort=False)

    # 🔧 FIX: normalize all dates to tz-naive midnight so we don't mix tz-aware/naive
    if "date" in all_inf.columns:
        all_inf["date"] = pd.to_datetime(all_inf["date"], errors="coerce")
        all_inf["date"] = all_inf["date"].dt.normalize()  # just midnight, no tz
        all_inf = all_inf.dropna(subset=["symbol", "date"], how="any")
        print(
            f"[load_all_inf] {src_kind}: rows={len(all_inf)}, "
            f"date_range={all_inf['date'].min().date()}→{all_inf['date'].max().date()}"
        )
    else:
        print(f"[load_all_inf] {src_kind}: WARNING no 'date' column after normalization.")
    return all_inf


def load_inf_from_daily_and_intraday(
    daily_logs_dir: Path,
    intraday_logs_dir: Path | None = None,
) -> pd.DataFrame:
    """
    Load infer history from daily + optional intraday logs and stack them.
    """
    daily = load_all_inf_from_logs(daily_logs_dir, src_kind="daily")

    if intraday_logs_dir is None:
        print(f"[load_inf_combined] only daily logs used: rows={len(daily)}")
        return daily

    intraday = load_all_inf_from_logs(intraday_logs_dir, src_kind="intraday")

    if intraday.empty:
        print(f"[load_inf_combined] intraday empty; using only daily rows={len(daily)}")
        return daily

    all_inf = pd.concat([daily, intraday], ignore_index=True, sort=False)
    print(
        f"[load_inf_combined] daily={len(daily)}, intraday={len(intraday)}, combined={len(all_inf)}"
    )
    return all_inf

def build_simple_allocation_from_signals(signals: pd.DataFrame) -> pd.DataFrame:
    """
    Simple allocator:
      - take the most recent row per symbol (by timestamp or date),
      - allocate only across BUYs, proportional to pos_frac (or 1.0 if pos_frac <= 0).

    Returns DataFrame[date, symbol, pct_simple].
    """
    if signals.empty:
        return pd.DataFrame(columns=["date", "symbol", "pct_simple"])

    sig = signals.copy()
    sig["symbol"] = sig["symbol"].astype(str)

    # ordering key
    if "timestamp_utc" in sig.columns:
        sig["order_ts"] = pd.to_datetime(sig["timestamp_utc"], errors="coerce", utc=True)
    else:
        sig["order_ts"] = pd.to_datetime(sig["date"], errors="coerce")

    sig["date"] = pd.to_datetime(sig["date"], errors="coerce")
    sig["side"] = sig["side"].astype(str).str.upper()
    if "pos_frac" not in sig.columns:
        sig["pos_frac"] = 1.0

    sig = sig.dropna(subset=["symbol", "order_ts"])

    # latest row per symbol
    last = (
        sig.sort_values(["symbol", "order_ts"])
           .groupby("symbol", as_index=False)
           .tail(1)
           .copy()
    )

    buys = last[last["side"] == "BUY"].copy()
    if buys.empty:
        return pd.DataFrame(columns=["date", "symbol", "pct_simple"])

    base_w = pd.to_numeric(buys["pos_frac"], errors="coerce").fillna(0.0)
    # floor: if <= 0, treat as 1.0 so every BUY gets some weight
    base_w = np.where(base_w <= 0.0, 1.0, base_w)

    weights = pd.Series(base_w, index=buys["symbol"]).groupby(level=0).sum()
    weights = weights[weights > 0]
    if weights.empty:
        return pd.DataFrame(columns=["date", "symbol", "pct_simple"])

    total = float(weights.sum())
    if not np.isfinite(total) or total <= 0:
        return pd.DataFrame(columns=["date", "symbol", "pct_simple"])

    pct = weights / total
    d = buys["date"].max()

    out = pd.DataFrame(
        {
            "date": pd.to_datetime(d).normalize(),
            "symbol": pct.index.astype(str),
            "pct_simple": pct.values,
        }
    ).sort_values("pct_simple", ascending=False).reset_index(drop=True)

    return out


def build_base_and_today(all_inf: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Build:
      - base: historical rows with a next price, for the *current universe*
              (symbols that appear on the most recent trading day);
              includes all infers up to but not including the latest snapshot.
      - today_inf: for that same universe, the *latest* infer row per symbol
                   on the most recent trading day (live predictions).

    Uses intraday ordering if timestamp_utc is present; otherwise falls back to date.
    """
    if all_inf.empty:
        return (
            pd.DataFrame(columns=[
                "date","symbol","side","ret_next","bh_ret","realized_ret",
                "buy_correct","sell_correct","hold_correct","correct",
                "pos_frac","score"
            ]),
            pd.DataFrame(columns=["date","symbol","side","pos_frac","score"]),
        )

    df = all_inf.copy()

    # Core hygiene
    df["symbol"] = df["symbol"].astype(str)
    df["side"] = df["side"].astype(str).str.upper()

    # Ordering key: intraday timestamp if available, else date
    if "timestamp_utc" in df.columns:
        order_ts = pd.to_datetime(df["timestamp_utc"], errors="coerce", utc=True)
        df["order_ts"] = order_ts
    else:
        df["order_ts"] = pd.to_datetime(df["date"], errors="coerce")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["symbol", "order_ts", "price"])

    if df.empty:
        return (
            pd.DataFrame(columns=[
                "date","symbol","side","ret_next","bh_ret","realized_ret",
                "buy_correct","sell_correct","hold_correct","correct",
                "pos_frac","score"
            ]),
            pd.DataFrame(columns=["date","symbol","side","pos_frac","score"]),
        )

    # --- 1) Determine latest trading day and current universe ---
    latest_date = df["date"].max()
    universe_syms = df.loc[df["date"] == latest_date, "symbol"].unique()

    # Keep only symbols that are present on the most recent day
    df = df[df["symbol"].isin(universe_syms)].copy()

    # --- 2) Within that universe, choose "today" rows and "history" ---
    df = df.sort_values(["symbol", "order_ts"]).reset_index(drop=True)

    # For each symbol, the latest row on the latest_date is "today"
    mask_latest_day = df["date"].eq(latest_date)
    df_latest = df[mask_latest_day].copy()

    if df_latest.empty:
        # Shouldn't happen given universe_syms, but guard anyway
        # In this edge case, treat everything as history and leave today_inf empty
        hist = df.copy()
        today_inf = pd.DataFrame(columns=["date","symbol","side","pos_frac","score"])
    else:
        last_today_idx = (
            df_latest.sort_values(["symbol", "order_ts"])
                     .groupby("symbol", as_index=False)
                     .tail(1)
                     .index
        )

        df["is_today"] = False
        df.loc[last_today_idx, "is_today"] = True

        hist = df[~df["is_today"]].copy()
        today_inf = df[df["is_today"]].copy()

    # --- 3) Build historical base from all history rows ---
    if hist.empty:
        base = pd.DataFrame(columns=[
            "date","symbol","side","ret_next","bh_ret","realized_ret",
            "buy_correct","sell_correct","hold_correct","correct",
            "pos_frac","score"
        ])
    else:
        # next price within history per symbol
        hist["price_next"] = hist.groupby("symbol", sort=False)["price"].shift(-1)
        hist["ret_next"] = (hist["price_next"] / hist["price"]) - 1.0

        is_buy  = hist["side"].eq("BUY")
        is_sell = hist["side"].eq("SELL")
        is_hold = hist["side"].eq("HOLD")

        HOLD_THR = 0.005
        hist["buy_correct"]  = is_buy  & (hist["ret_next"] > 0)
        hist["sell_correct"] = is_sell & (hist["ret_next"] < 0)
        hist["hold_correct"] = is_hold & (hist["ret_next"].abs() <= HOLD_THR)

        hist["bh_ret"] = hist["ret_next"]
        hist["realized_ret"] = np.where(is_buy | is_hold, hist["ret_next"], 0.0)

        base = hist.dropna(subset=["price_next"]).copy()
        base["correct"] = base[["buy_correct","sell_correct","hold_correct"]].any(axis=1)

        cols_keep = [
            "date","symbol","side","ret_next","bh_ret","realized_ret",
            "buy_correct","sell_correct","hold_correct","correct",
        ]
        for extra in ["pos_frac", "score"]:
            if extra in base.columns:
                cols_keep.append(extra)

        base = (
            base[cols_keep]
            .sort_values(["symbol","date"])
            .reset_index(drop=True)
        )

    # --- 4) Trim today_inf to the fields needed for allocations ---
    if not today_inf.empty:
        tcols = ["date","symbol","side","pos_frac"]
        if "score" in today_inf.columns:
            tcols.append("score")
        today_inf = (
            today_inf[tcols]
            .sort_values(["symbol"])
            .reset_index(drop=True)
        )
    else:
        today_inf = pd.DataFrame(columns=["date","symbol","side","pos_frac","score"])

    return base, today_inf



# ============================================================================
# 2. COMMON PREP FOR STRATEGIES (same as notebook)
# ============================================================================

def build_s11_allocation_for_signals(
    base: pd.DataFrame,
    signals: pd.DataFrame,
) -> pd.DataFrame:
    """
    Live-style S11 allocation:

    - Use `base` (historical, with ret_next/correct) to compute S11 state per symbol
      as of the last date in `base`.
    - Apply that state (elig_s11, active_age_s11) to today's infer rows in `signals`.
    - Return normalized weights over today's BUY signals for S11-eligible symbols.

    If all weights are zero after S11 gating, fall back to a simple
    latest-infer allocation across BUYs.
    """
    if base.empty or signals.empty:
        return pd.DataFrame(columns=["date", "symbol", "pct_S11"])

    # 1) historical S11 state from base
    ev = _prep_ev(base)
    ev = _eligibility_columns(ev)

    ev_sorted = ev.sort_values(["symbol", "date"])
    last_state = (
        ev_sorted.groupby("symbol", as_index=False)[["date", "elig_s11", "active_age_s11"]]
        .last()
        .set_index("symbol")[["elig_s11", "active_age_s11"]]
    )

    # 2) normalize today's signals
    sig = signals.copy()
    sig["symbol"] = sig["symbol"].astype(str)
    sig["date"] = pd.to_datetime(sig["date"], errors="coerce")
    sig["side"] = sig["side"].astype(str).str.upper()
    if "pos_frac" not in sig.columns:
        sig["pos_frac"] = 1.0

    # 3) join S11 state onto today's signals
    sig = sig.join(last_state, on="symbol", how="left")
    sig["elig_s11"] = sig["elig_s11"].fillna(False)
    sig["active_age_s11"] = sig["active_age_s11"].fillna(0.0)

    # only BUY signals participate in new allocations
    buys = sig[sig["side"] == "BUY"].copy()
    if buys.empty:
        # no BUYs at all → nothing to do
        return pd.DataFrame(columns=["date", "symbol", "pct_S11"])

    # 4) S11 weighting: floor pos_frac for eligible BUYs
    base_w = pd.to_numeric(buys["pos_frac"], errors="coerce").fillna(0.0)
    elig = buys["elig_s11"].astype(bool).to_numpy()
    ages = pd.to_numeric(buys["active_age_s11"], errors="coerce").fillna(0.0)
    ages = np.clip(ages, 0.0, S11_AGE_CAP)
    mult = 1.0 + ages / S11_AGE_DIV

    # floor: for S11-eligible rows, if pos_frac <= 0, treat as 1.0
    base_w = np.where((elig) & (base_w <= 0.0), 1.0, base_w)

    w = base_w * elig * mult

    weights = pd.Series(w, index=buys["symbol"]).groupby(level=0).sum()
    weights = weights[weights > 0]

    if weights.empty:
        # S11 gating + pos_frac still killed everything — fall back to "simple latest" logic
        simple = build_simple_allocation_from_signals(signals)
        simple = simple.rename(columns={"pct_simple": "pct_S11"})
        return simple

    total = float(weights.sum())
    if not np.isfinite(total) or total <= 0:
        simple = build_simple_allocation_from_signals(signals)
        simple = simple.rename(columns={"pct_simple": "pct_S11"})
        return simple

    pct = weights / total
    d = sig["date"].max()
    out = pd.DataFrame(
        {
            "date": pd.to_datetime(d).normalize(),
            "symbol": pct.index.astype(str),
            "pct_S11": pct.values,
        }
    ).sort_values("pct_S11", ascending=False).reset_index(drop=True)

    return out


def score_to_weight(score: pd.Series) -> pd.Series:
    """
    Map a score in ~[0,1] to a multiplicative weight in ~[0.5,1.5].
    Same formula as in the notebook.
    """
    s = pd.to_numeric(score, errors="coerce")
    w = 1.0 + 0.5 * np.clip((s - 0.5) / 0.4, -1, 1)
    return w.fillna(1.0)


def _prep_ev(base_df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare the evaluation frame EV from the forward-evaluable base.
    """
    ev = base_df.copy()
    ev["date"] = pd.to_datetime(ev["date"])
    ev = ev.sort_values(["date", "symbol"]).reset_index(drop=True)

    ev["side"] = ev["side"].astype(str).str.upper()
    ev["is_buy"]  = ev["side"].eq("BUY")
    ev["is_hold"] = ev["side"].eq("HOLD")
    ev["is_sell"] = ev["side"].eq("SELL")

    if "pos_frac" not in ev.columns:
        ev["pos_frac"] = 1.0

    ev["score"] = ev["score"] if "score" in ev.columns else np.nan
    ev["dyn_weight_base"] = score_to_weight(ev["score"])
    ev["n_seen_prior"] = ev.groupby("symbol").cumcount()

    return ev


def _eligibility_columns(ev: pd.DataFrame) -> pd.DataFrame:
    """
    Add S8/S9/S11/S12 eligibility columns to EV.
    """
    ev = ev.sort_values(["symbol", "date"]).copy()
    grp = ev.groupby("symbol", sort=False, group_keys=False)

    # S8: prior cumulative realized TWR
    twr_cum = grp["realized_ret"].apply(
        lambda s: (1.0 + s.fillna(0.0)).cumprod()
    )
    ev["twr_cum_prior"] = twr_cum.groupby(ev["symbol"]).shift(1) - 1.0

    # S9: rolling-10 realized TWR prior
    def _roll_twr(x: np.ndarray) -> float:
        y = np.nan_to_num(x, nan=0.0)
        return float(np.prod(1.0 + y) - 1.0)

    roll10 = grp["realized_ret"].apply(
        lambda s: s.rolling(window=10, min_periods=10).apply(_roll_twr, raw=True)
    )
    ev["twr_roll10_prior"] = roll10.groupby(ev["symbol"]).shift(1)

    ev["elig_s8"] = (ev["twr_cum_prior"] >= -EPS).fillna(False)
    ev["elig_s9"] = (ev["twr_roll10_prior"] > EPS).fillna(False)

    # S11: streak-based activation, consecutive wrongs to deactivate
    if "correct" in ev.columns:
        ev["elig_s11"] = False
        ev["active_age_s11"] = 0.0

        for sym, df_sym in ev.groupby("symbol", sort=False):
            active = False
            good_streak = 0
            bad_streak = 0
            age = 0.0

            for idx, row in df_sym.iterrows():
                ev.at[idx, "elig_s11"] = active
                ev.at[idx, "active_age_s11"] = age

                is_signal = bool(row.get("is_buy", False)) or bool(row.get("is_sell", False))
                if not is_signal:
                    if active:
                        age += 1.0
                    continue

                is_corr = bool(row["correct"])
                if is_corr:
                    good_streak += 1
                    bad_streak = 0
                    if (not active) and good_streak >= S11_ACTIVATION_GOOD:
                        active = True
                        age = 0.0
                else:
                    bad_streak += 1
                    good_streak = 0
                    if active and bad_streak >= S11_DEACTIVATION_BAD:
                        active = False
                        age = 0.0

                if active:
                    age += 1.0

        ev["elig_s11"] = ev["elig_s11"].fillna(False)
        ev["active_age_s11"] = ev["active_age_s11"].fillna(0.0)
    else:
        ev["elig_s11"] = False
        ev["active_age_s11"] = 0.0

    # S12: streak-based activation, TOTAL wrong while active to deactivate
    if "correct" in ev.columns:
        ev["elig_s12"] = False
        ev["active_age_s12"] = 0.0

        for sym, df_sym in ev.groupby("symbol", sort=False):
            active = False
            good_streak = 0
            wrong_since_activation = 0
            age = 0.0

            for idx, row in df_sym.iterrows():
                ev.at[idx, "elig_s12"] = active
                ev.at[idx, "active_age_s12"] = age

                is_signal = bool(row.get("is_buy", False)) or bool(row.get("is_sell", False))
                if not is_signal:
                    if active:
                        age += 1.0
                    continue

                is_corr = bool(row["correct"])
                if is_corr:
                    good_streak += 1
                    if (not active) and good_streak >= S12_ACTIVATION_GOOD:
                        active = True
                        age = 0.0
                        wrong_since_activation = 0
                else:
                    good_streak = 0
                    if active:
                        wrong_since_activation += 1
                        if wrong_since_activation >= S12_DEACTIVATION_BAD:
                            active = False
                            age = 0.0
                            wrong_since_activation = 0

                if active:
                    age += 1.0

        ev["elig_s12"] = ev["elig_s12"].fillna(False)
        ev["active_age_s12"] = ev["active_age_s12"].fillna(0.0)
    else:
        ev["elig_s12"] = False
        ev["active_age_s12"] = 0.0

    return ev


# ============================================================================
# 3. S11 & S12 allocation for a single date
# ============================================================================

def _s11_raw_weights_for_date(ev: pd.DataFrame, date: pd.Timestamp) -> pd.Series:
    day = ev.loc[ev["date"] == pd.to_datetime(date)].copy()
    if day.empty:
        return pd.Series(dtype=float)

    buys = day[day["is_buy"]].copy()
    if buys.empty:
        return pd.Series(dtype=float)

    w = np.maximum(pd.to_numeric(buys["pos_frac"], errors="coerce").fillna(0.0), 0.0)

    active_mask = buys.get("elig_s11", False).astype(bool)
    ages = pd.to_numeric(buys.get("active_age_s11", 0.0), errors="coerce").fillna(0.0)
    ages = np.clip(ages, 0.0, S11_AGE_CAP)
    mult = 1.0 + ages / S11_AGE_DIV

    w = w * active_mask.to_numpy() * mult

    weights = pd.Series(w, index=buys["symbol"]).groupby(level=0).sum()
    weights = weights[weights > 0]
    return weights


def _s12_raw_weights_for_date(ev: pd.DataFrame, date: pd.Timestamp) -> pd.Series:
    day = ev.loc[ev["date"] == pd.to_datetime(date)].copy()
    if day.empty:
        return pd.Series(dtype=float)

    buys = day[day["is_buy"]].copy()
    if buys.empty:
        return pd.Series(dtype=float)

    w = np.maximum(pd.to_numeric(buys["pos_frac"], errors="coerce").fillna(0.0), 0.0)

    active_mask = buys.get("elig_s12", False).astype(bool)
    ages = pd.to_numeric(buys.get("active_age_s12", 0.0), errors="coerce").fillna(0.0)
    ages = np.clip(ages, 0.0, S12_AGE_CAP)
    mult = 1.0 + ages / S12_AGE_DIV

    w = w * active_mask.to_numpy() * mult

    weights = pd.Series(w, index=buys["symbol"]).groupby(level=0).sum()
    weights = weights[weights > 0]
    return weights


def build_s11_live_allocation_from_snapshot(
    base: pd.DataFrame,
    today_inf: pd.DataFrame,
) -> pd.DataFrame:
    """
    Simple, explicit S11 live allocator using the strategy snapshot.

    - base: historical, forward-evaluable rows (from build_base_and_today)
    - today_inf: latest infer per symbol on the latest trading day
                 (also from build_base_and_today)

    Logic:
      1) Build snapshot = per-symbol S11 state (active flag + age).
      2) Join snapshot onto today's signals.
      3) Filter to BUY & s11_active == True.
      4) Weight ~ pos_frac * (1 + s11_age / S11_AGE_DIV).
      5) Normalize to get pct_S11_live.

    Returns DataFrame[date, symbol, pct_S11_live].
    """
    if base.empty or today_inf.empty:
        return pd.DataFrame(columns=["date", "symbol", "pct_S11_live"])

    # 1) Per-symbol state snapshot (uses _prep_ev/_eligibility_columns internally)
    snap = build_strategy_state_snapshot(base)
    if snap.empty:
        return pd.DataFrame(columns=["date", "symbol", "pct_S11_live"])

    state = (
        snap.set_index("symbol")[["s11_active", "s11_age"]]
             .copy()
    )

    # 2) Join snapshot onto today's signals
    sig = today_inf.copy()
    sig["symbol"] = sig["symbol"].astype(str)
    sig["side"] = sig["side"].astype(str).str.upper()
    sig["date"] = pd.to_datetime(sig["date"], errors="coerce")
    if "pos_frac" not in sig.columns:
        sig["pos_frac"] = 1.0

    sig = sig.join(state, on="symbol", how="left")
    sig["s11_active"] = sig["s11_active"].fillna(False)
    sig["s11_age"] = pd.to_numeric(sig["s11_age"], errors="coerce").fillna(0.0)

    # 3) Filter to BUY & S11-active
    buys = sig[(sig["side"] == "BUY") & (sig["s11_active"])].copy()
    if buys.empty:
        return pd.DataFrame(columns=["date", "symbol", "pct_S11_live"])

    # 4) Compute raw weights
    base_w = pd.to_numeric(buys["pos_frac"], errors="coerce").fillna(0.0)
    # Floor: if S11 says active but pos_frac <= 0, treat as 1.0 so it can't vanish
    base_w = np.where(base_w <= 0.0, 1.0, base_w)

    ages = np.clip(
        pd.to_numeric(buys["s11_age"], errors="coerce").fillna(0.0),
        0.0,
        S11_AGE_CAP,
    )
    mult = 1.0 + ages / S11_AGE_DIV

    w = base_w * mult

    weights = pd.Series(w, index=buys["symbol"]).groupby(level=0).sum()
    weights = weights[weights > 0]

    if weights.empty:
        return pd.DataFrame(columns=["date", "symbol", "pct_S11_live"])

    total = float(weights.sum())
    if not np.isfinite(total) or total <= 0:
        return pd.DataFrame(columns=["date", "symbol", "pct_S11_live"])

    pct = weights / total
    d = sig["date"].max()

    out = pd.DataFrame(
        {
            "date": pd.to_datetime(d).normalize(),
            "symbol": pct.index.astype(str),
            "pct_S11_live": pct.values,
        }
    ).sort_values("pct_S11_live", ascending=False).reset_index(drop=True)

    return out



def build_s12_allocation(base: pd.DataFrame, on_date: Optional[pd.Timestamp] = None) -> pd.DataFrame:
    """
    Build S12 allocation percents for a single date.

    Returns: DataFrame[date, symbol, pct_S12]
    """
    if base.empty:
        return pd.DataFrame(columns=["date", "symbol", "pct_S12"])

    ev = _prep_ev(base)
    ev = _eligibility_columns(ev)

    date = pd.to_datetime(on_date) if on_date is not None else ev["date"].max()

    weights = _s12_raw_weights_for_date(ev, date)
    if weights.empty:
        return pd.DataFrame(columns=["date", "symbol", "pct_S12"])

    total = float(weights.sum())
    if not np.isfinite(total) or total <= 0:
        return pd.DataFrame(columns=["date", "symbol", "pct_S12"])

    pct = weights / total
    out = pd.DataFrame({
        "date": pd.to_datetime(date).normalize(),
        "symbol": pct.index.astype(str),
        "pct_S12": pct.values,
    }).sort_values("pct_S12", ascending=False).reset_index(drop=True)

    return out


# ============================================================================
# 4. S13: pooled, S12-gated equity simulation → pct_S13 for a date
# ============================================================================

def _simulate_s13_per_symbol(ev: pd.DataFrame) -> pd.DataFrame:
    """
    Simulate S13 equity index and return a per-symbol ledger with alloc_w, contrib_ret, etc.
    Mirrors the notebook's S13 simulation logic (simplified to core behaviour).
    """
    ev = ev.sort_values(["date", "symbol"]).copy()
    ev["date"] = pd.to_datetime(ev["date"])
    dates = np.sort(ev["date"].unique())

    equity_idx = 1.0
    exposure: Dict[str, float] = {sym: 0.0 for sym in ev["symbol"].unique()}

    rows_sym = []

    for d in dates:
        day = ev.loc[ev["date"] == d].copy()
        if day.empty:
            continue

        day["has_pos"] = day["symbol"].map(lambda s: exposure.get(s, 0.0) > 1e-9)

        def _raw_w(row) -> float:
            if not bool(row.get("elig_s12", False)):
                return 0.0

            sym = row["symbol"]
            side = row["side"]

            # Only BUYs, plus HOLDs where we already have money, can get weight
            if side == "BUY":
                pass
            elif side == "HOLD" and exposure.get(sym, 0.0) > 1e-9:
                pass
            else:
                return 0.0

            base_w = max(float(row.get("pos_frac", 0.0)), 0.0)
            age = float(row.get("active_age_s12", 0.0))
            age_eff = max(0.0, min(age, S12_AGE_CAP))
            mult = 1.0 + age_eff / S12_AGE_DIV
            return base_w * mult

        day["raw_w"] = day.apply(_raw_w, axis=1)
        tot_raw = float(day["raw_w"].sum())

        if tot_raw > 0:
            day["w"] = day["raw_w"] / tot_raw
        else:
            day["w"] = 0.0

        day["ret"] = day["ret_next"].astype(float)

        twr_ret = float((day["w"] * day["ret"]).sum())
        equity_next = equity_idx * (1.0 + twr_ret)

        w_sum = float(day["w"].sum())
        cash_after = equity_next * max(0.0, 1.0 - w_sum)

        for _, r in day.iterrows():
            sym = r["symbol"]
            w = float(r["w"])
            ret = float(r["ret"])

            rows_sym.append(
                {
                    "date": d,
                    "symbol": sym,
                    "alloc_w": w,
                    "contrib_ret": w * ret,
                    "invested_after": equity_next * w,
                    "cash_after": cash_after,
                }
            )

            exposure[sym] = w

        equity_idx = equity_next

    per_symbol = (
        pd.DataFrame(rows_sym)
          .sort_values(["date", "symbol"])
          .reset_index(drop=True)
    )
    return per_symbol


def build_s13_allocation(base: pd.DataFrame, on_date: Optional[pd.Timestamp] = None) -> pd.DataFrame:
    """
    Build S13 allocation for a single date, using the S12-gated pooled equity simulation.

    Returns: DataFrame[date, symbol, pct_S13]
    """
    if base.empty:
        return pd.DataFrame(columns=["date", "symbol", "pct_S13"])

    ev = _prep_ev(base)
    ev = _eligibility_columns(ev)

    per_sym = _simulate_s13_per_symbol(ev)
    if per_sym.empty:
        return pd.DataFrame(columns=["date", "symbol", "pct_S13"])

    per_sym["date"] = pd.to_datetime(per_sym["date"])
    date = pd.to_datetime(on_date) if on_date is not None else per_sym["date"].max()

    day = per_sym.loc[per_sym["date"] == date].copy()
    if day.empty:
        return pd.DataFrame(columns=["date", "symbol", "pct_S13"])

    weights = day.set_index("symbol")["alloc_w"]
    weights = weights[weights > 0]
    if weights.empty:
        return pd.DataFrame(columns=["date", "symbol", "pct_S13"])

    total = float(weights.sum())
    if not np.isfinite(total) or total <= 0:
        return pd.DataFrame(columns=["date", "symbol", "pct_S13"])

    pct = weights / total
    out = pd.DataFrame({
        "date": pd.to_datetime(date).normalize(),
        "symbol": pct.index.astype(str),
        "pct_S13": pct.values,
    }).sort_values("pct_S13", ascending=False).reset_index(drop=True)

    return out

def build_strategy_state_snapshot(base: pd.DataFrame) -> pd.DataFrame:
    """
    Build a per-symbol snapshot of strategy state using historical base:

      - s11_active, s11_age
      - s12_active, s12_age
      - twr_cum, twr_roll10 (S8/S9-style metrics)
      - s13_alloc_w, s13_invested (from pooled S13 simulation)

    Returns a DataFrame with one row per symbol:

      symbol, last_hist_date,
      s11_active, s11_age,
      s12_active, s12_age,
      twr_cum, twr_roll10,
      s13_last_date, s13_alloc_w, s13_invested
    """
    if base.empty:
        return pd.DataFrame(
            columns=[
                "symbol", "last_hist_date",
                "s11_active", "s11_age",
                "s12_active", "s12_age",
                "twr_cum", "twr_roll10",
                "s13_last_date", "s13_alloc_w", "s13_invested",
            ]
        )

    # 1) Historical S11/S12/S8/S9 state from base
    ev = _prep_ev(base)
    ev = _eligibility_columns(ev)
    ev = ev.sort_values(["symbol", "date"]).reset_index(drop=True)

    # last historical row per symbol
    last_ev = (
        ev.groupby("symbol", as_index=False)
          .tail(1)
          .set_index("symbol")
    )

    cols = [
        "date",
        "elig_s11", "active_age_s11",
        "elig_s12", "active_age_s12",
        "twr_cum_prior", "twr_roll10_prior",
    ]
    # some safety if cols got changed
    cols = [c for c in cols if c in last_ev.columns]

    snapshot = last_ev[cols].copy()
    snapshot = snapshot.rename(
        columns={
            "date": "last_hist_date",
            "elig_s11": "s11_active",
            "active_age_s11": "s11_age",
            "elig_s12": "s12_active",
            "active_age_s12": "s12_age",
            "twr_cum_prior": "twr_cum",
            "twr_roll10_prior": "twr_roll10",
        }
    )

    # 2) S13 pooled equity state: last alloc and invested per symbol
    per_sym = _simulate_s13_per_symbol(ev)
    if not per_sym.empty:
        per_sym = per_sym.sort_values(["symbol", "date"])
        last_s13 = (
            per_sym.groupby("symbol", as_index=False)
                   .tail(1)
                   .set_index("symbol")[["date", "alloc_w", "invested_after"]]
        )
        last_s13 = last_s13.rename(
            columns={
                "date": "s13_last_date",
                "alloc_w": "s13_alloc_w",
                "invested_after": "s13_invested",
            }
        )
        snapshot = snapshot.join(last_s13, how="left")
    else:
        snapshot["s13_last_date"] = pd.NaT
        snapshot["s13_alloc_w"] = 0.0
        snapshot["s13_invested"] = 0.0

    # 3) Clean up, fill defaults
    snapshot.index.name = "symbol"
    snapshot = snapshot.reset_index()

    # Fill NaNs for booleans and numeric fields
    for col in ["s11_active", "s12_active"]:
        if col in snapshot.columns:
            snapshot[col] = snapshot[col].fillna(False).astype(bool)

    for col in ["s11_age", "s12_age", "twr_cum", "twr_roll10", "s13_alloc_w", "s13_invested"]:
        if col in snapshot.columns:
            snapshot[col] = pd.to_numeric(snapshot[col], errors="coerce").fillna(0.0)

    snapshot = snapshot.sort_values("symbol").reset_index(drop=True)
    return snapshot

def list_active_models(base: pd.DataFrame) -> dict[str, list[str]]:
    """
    Convenience helper: return lists of symbols that are currently active
    under each strategy (S11, S12, S13).

    Uses the snapshot from build_strategy_state_snapshot(base).
    """
    snap = build_strategy_state_snapshot(base)
    if snap.empty:
        return {"S11": [], "S12": [], "S13": []}

    active_s11 = sorted(snap.loc[snap["s11_active"], "symbol"].astype(str).unique().tolist())
    active_s12 = sorted(snap.loc[snap["s12_active"], "symbol"].astype(str).unique().tolist())
    # for S13, treat symbols with nonzero alloc or invested as active
    active_s13 = sorted(
        snap.loc[(snap["s13_alloc_w"] > 0) | (snap["s13_invested"] > 0), "symbol"]
            .astype(str)
            .unique()
            .tolist()
    )

    return {
        "S11": active_s11,
        "S12": active_s12,
        "S13": active_s13,
    }

