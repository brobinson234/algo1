# rl_pipeline3_rs_std_patched.py
# One-stop RL pipeline with prod/exp isolation, walkleader tagging, and promotion.

# # =========================
# # TRAIN / EVAL / COMPARE
# # =========================
# # Train a general 1y policy (PROD; writes to ./models)
# py rl_pipeline3_rs_std_patched.py train --episodes 250 --model models/dqn_policy_1y.pt

# # Train (EXPERIMENT; isolated under ./experiments/<exp-id>/)
# py rl_pipeline3_rs_std_patched.py train --profile exp --exp-id 2025-10-19_guard_sweep_A --episodes 250 --model models/dqn_policy_1y.pt

# # Evaluate a saved model (PROD)
# py rl_pipeline3_rs_std_patched.py eval --model models/dqn_policy_1y.pt

# # Compare RL vs Rule on same window (PROD)
# py rl_pipeline3_rs_std_patched.py compare --model models/dqn_policy_1y.pt


# # =========================
# # SPLIT-YEAR (per symbol)
# # =========================
# # Per-symbol train+OOS eval (PROD; updates ./models/<SYM>/LATEST.txt)
# py rl_pipeline3_rs_std_patched.py splityear --oos-days 42 --episodes 200 --model-prefix dqn_sy

# # Same, isolated EXPERIMENT (writes to ./experiments/<exp-id>/models)
# py rl_pipeline3_rs_std_patched.py splityear --profile exp --exp-id 2025-10-19_guard_sweep_A --oos-days 42 --episodes 200 --model-prefix dqn_sy


# # =========================
# # SPLIT-YEAR POOLED
# # =========================
# # Pooled cash run over a list (PROD)
# py rl_pipeline3_rs_std_patched.py splityear-pooled --symbols QS,MSFT,NVDA --oos-days 42 --episodes 200 --model-prefix dqn_sy --invest-per-symbol 100 --start-cash-extra 0 --mom-window 20 --mom-scale-low 0.8 --mom-scale-high 1.3

# # Same, isolated EXPERIMENT
# py rl_pipeline3_rs_std_patched.py splityear-pooled --profile exp --exp-id 2025-10-19_guard_sweep_A --symbols QS,MSFT,NVDA --oos-days 42 --episodes 200 --model-prefix dqn_sy


# # =========================
# # INFERENCE / EXPORT
# # =========================
# # Inference on the latest bar (PROD; uses prod LATEST by default)
# py rl_pipeline3_rs_std_patched.py infer --symbol NVDA --log-csv ./logs

# # Inference within an EXPERIMENT (uses that exp’s LATEST)
# py rl_pipeline3_rs_std_patched.py infer --profile exp --exp-id 2025-10-19_guard_sweep_A --symbol NVDA --log-csv ./logs

# # Export greedy actions per bar to CSV (PROD)
# py rl_pipeline3_rs_std_patched.py export-actions --symbol NVDA --model models/dqn_policy_1y.pt


# # =========================
# # WALK-FORWARD / LEADERBOARD
# # =========================
# # Rolling train->test (PROD)
# py rl_pipeline3_rs_std_patched.py walkforward --train-days 504 --test-days 21 --episodes 100 --model models/dqn_wf.pt --symbols QS,MSFT

# # Leaderboard (EXPERIMENT by tag; detail/summary auto to experiments/<tag>/logs/out)
# py rl_pipeline3_rs_std_patched.py walkleader --train-days 504 --test-days 21 --episodes 120 --symbols QS,MSFT,NVDA --tag weekly_run --detail "" --summary ""

# # (Optional helpers to match the tuning playbook; EXPERIMENT scope)
# py rl_pipeline3_rs_std_patched.py wl-analyze --profile exp --exp-id weekly_run
# py rl_pipeline3_rs_std_patched.py wl-apply-winners --profile exp --exp-id weekly_run
# py rl_pipeline3_rs_std_patched.py wl-retrain-winners --profile exp --exp-id weekly_run


# # =========================
# # LIVE DECISIONS (PROD ONLY)
# # =========================
# # 3pm ET decision: freeze features, inject live price; write MOC suggestions
# py rl_pipeline3_rs_std_patched.py live --symbols "IBM","RGTI","QBTS","QUBT",'IONQ', "QS", "AMD",    "SLDP",    "MSFT",    "CHGG",    "AI",    "NVDA",    "TSM",    "GOOGL",    "AMD",  "PAYO", "LCID",  "PLUG",    "BYND",    "IBM",     "TM","SPY","CHGG","AI","NKLA","AMC","BYND" ,    "TDC", "INFA","SNOW",    "PSTG","MDB", "FSLR",'ENPH','SEDG','ARRY','NXT','ENVX','MVST','EOSE','FLNC','EVGO','ITRI','AMSC','POWI','VICR','NVTS','CLNE','GEVO','MNTK','ELVA','XEL','AEP','RNW',"INTC", "ARQQ","MU","SMCI", "TRV","PGR","BHP","COST","MRK","NFLX","RMBS","ALB","VZ","SLDPW","AAPL","PG","ROP" --model-prefix dqn_splityear --cash-per-symbol 1000 --order-file orders_moc.csv --snapshot-file live_snapshot.csv --log-csv ./logs

# # Refresh data, retrain per symbol, and (optionally) place immediate orders
# py rl_pipeline3_rs_std_patched.py train-today-and-trade --symbols "IBM","RGTI","QBTS","QUBT",'IONQ', "QS", "AMD",    "SLDP",    "MSFT",    "CHGG",    "AI",    "NVDA",    "TSM",    "GOOGL",    "AMD",  "PAYO", "LCID",  "PLUG",    "BYND",    "IBM",     "TM","SPY","CHGG","AI","NKLA","AMC","BYND" ,    "TDC", "INFA","SNOW",    "PSTG","MDB", "FSLR",'ENPH','SEDG','ARRY','NXT','ENVX','MVST','EOSE','FLNC','EVGO','ITRI','AMSC','POWI','VICR','NVTS','CLNE','GEVO','MNTK','ELVA','XEL','AEP','RNW',"INTC", "ARQQ","MU","SMCI", "TRV","PGR","BHP","COST","MRK","NFLX","RMBS","ALB","VZ","SLDPW","AAPL","PG","ROP" --episodes 120 --model-prefix dqn_today --cash-per-symbol 1000 --tif ioc --order-file orders_immediate.csv --snapshot-file train_trade_snapshot.csv --dry-run


# # =========================
# # PROMOTE EXPERIMENT → PROD
# # =========================
# # Copy latest model for a symbol from experiments/<exp-id>/ into prod models/
# py rl_pipeline3_rs_std_patched.py promote --exp-id 2025-10-19_guard_sweep_A --symbol NVDA


# to clear cache run:
# Set-Location C:\Users\brobi\OneDrive\Desktop\Algo1
# Remove-Item -Recurse -Force .\daily_cache\

#RUN to train
# py .\rl_pipeline3_rs_std_patched.py splityear --oos-days 42 --episodes 200 --model-prefix dqn_sy --alpaca-update --since 2023-01-01

#RUN to infer
# $env:ALPACA_FEED="iex"; $syms=@("IBM","RGTI","QBTS","QUBT",'IONQ', "QS", "AMD",    "SLDP",    "MSFT",    "CHGG",    "AI",    "NVDA",    "TSM",    "GOOGL",    "AMD",  "PAYO", "LCID",  "PLUG",    "BYND", "TM","NKLAQ","AMC","BYND" ,    "TDC", "INFA","SNOW",    "PSTG","MDB", "FSLR",'ENPH','SEDG','ARRY','NXT','ENVX','MVST','EOSE','FLNC','EVGO','ITRI','AMSC','POWI','VICR','NVTS','CLNE','GEVO','MNTK','ELVA','XEL','AEP','RNW',"INTC", "ARQQ","MU","SMCI", "TRV","PGR","BHP","COST","MRK","NFLX","RMBS","ALB","VZ","SLDPW","AAPL","PG","ROP"); foreach($s in $syms){ py .\rl_pipeline3_rs_std_patched.py infer --symbol $s --alpaca-update --since 2025-08-05 --provisional-today --log-csv .\logs --debug; Start-Sleep -Milliseconds 400 }

from __future__ import annotations
import os, sys, math, time, random, argparse
from pathlib import Path
from typing import Dict, Tuple, List, Optional
from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo
import requests
import numpy as np
import pandas as pd
import csv
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import math

import torch
import torch.nn as nn
import torch.optim as optim
import inspect
from alpaca.common.exceptions import APIError
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

try:
    # preferred enums (newer alpaca-py)
    from alpaca.trading.enums import QueryOrderStatus
    HAS_QUERY_ENUM = True
except Exception:
    HAS_QUERY_ENUM = False

def trend_project_compat(bt_mod, base_mid, yoy, apply_trend=True):
    try:
        sig = inspect.signature(bt_mod.trend_project)
        if "apply_trend" in sig.parameters:
            return bt_mod.trend_project(base_mid, yoy, apply_trend=apply_trend)
    except Exception:
        pass
    # newer bt.trend_project(base_mid, yoy) with no flag
    return bt_mod.trend_project(base_mid, yoy) if apply_trend else base_mid

def _alp_side(side_str: str) -> OrderSide:
    s = side_str.strip().lower()
    if s == "buy":
        return OrderSide.BUY
    if s == "sell":
        return OrderSide.SELL
    raise ValueError(f"Unsupported side: {side_str}")

def _alp_tif(tif_str: str) -> TimeInForce:
    s = tif_str.strip().lower()
    # Common immediate options: IOC (Immediate-Or-Cancel) or DAY (regular day order)
    if s == "ioc":
        return TimeInForce.IOC
    if s == "day":
        return TimeInForce.DAY
    if s == "fok":
        return TimeInForce.FOK
    if s == "gtc":
        return TimeInForce.GTC
    raise ValueError(f"Unsupported time_in_force: {tif_str}")

def place_market_order_immediate(tc: TradingClient, symbol: str, side: str, qty: float, tif: str = "ioc"):
    """
    Submit a MARKET order with immediate-style TIF (default IOC).
    """
    if qty <= 0:
        print(f"[orders] skip {symbol} {side}: qty<=0")
        return None
    req = MarketOrderRequest(
        symbol=symbol,
        qty=float(qty),
        side=_alp_side(side),
        time_in_force=_alp_tif(tif)
    )
    try:
        o = tc.submit_order(order_data=req)
        print(f"[orders] submitted {symbol} {side} qty={qty:.4f} tif={tif} id={getattr(o,'id',None)}")
        return o
    except Exception as e:
        print(f"[orders] submit failed {symbol} {side} qty={qty:.4f}: {e}")
        return None

# ---- Funds config (percent-of-equity allocator) ------------------------------

def load_funds_config(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Funds config not found: {path}")
    with p.open("r", encoding="utf-8") as f:
        return json.load(f) or {}

def _account_equity_or_default(tc: TradingClient, explicit_equity: float = 0.0) -> float:
    """
    If explicit_equity > 0, use it. Else try TradingClient.get_account().equity.
    Fallback to 0. Raises if nothing is available.
    """
    if explicit_equity and explicit_equity > 0:
        return float(explicit_equity)
    try:
        acct = tc.get_account()
        # equity is a string in Alpaca; convert to float
        return float(getattr(acct, "equity", "0") or 0.0)
    except Exception:
        pass
    raise RuntimeError("No equity available (pass --equity or use --use-account-equity with valid APCA_* creds).")

def plan_symbol_budgets_from_funds(cfg: dict, total_equity: float) -> tuple[list[str], dict]:
    """
    Returns (symbols_list, per_symbol_budget_map).

    Rules:
      - Only 'percent_equity' budget_type supported here.
      - Enforce max_total_allocation (as % of equity).
      - Enforce min_cash_buffer ($) -> do not allocate beyond equity - buffer.
      - Per-fund weighting 'equal' -> equal $ per symbol inside each fund.
      - If total requested > max_total_allocation, scale funds proportionally.
    """
    funds = cfg.get("funds") or []
    if not funds:
        return [], {}

    # Sum requested percent (0..1) across funds (only percent_equity supported)
    req_pct = 0.0
    for f in funds:
        if str(f.get("budget_type","")).lower() != "percent_equity":
            raise ValueError(f"Unsupported budget_type in fund '{f.get('name','?')}' (only 'percent_equity').")
        req_pct += float(f.get("budget", 0.0))

    max_total_pct = float(cfg.get("max_total_allocation", 1.0))
    min_cash_buffer = float(cfg.get("min_cash_buffer", 0.0))

    # Target allocation dollars after caps/buffer
    target_alloc_dollars = min(req_pct, max_total_pct) * total_equity
    # Respect buffer: you must keep at least min_cash_buffer in cash
    target_alloc_dollars = min(target_alloc_dollars, max(0.0, total_equity - min_cash_buffer))

    if target_alloc_dollars <= 0:
        return [], {}

    # Proportional scaling factor if req_pct > 0
    scale = (target_alloc_dollars / (req_pct * total_equity)) if req_pct > 0 else 0.0

    per_symbol_budget: dict[str, float] = {}
    ordered_syms: list[str] = []

    for f in funds:
        pct = float(f.get("budget", 0.0))           # of equity
        fund_dollars = pct * total_equity * scale   # dollars allocated to this fund
        syms = [s.strip().upper() for s in (f.get("symbols") or []) if s and s.strip()]
        if not syms or fund_dollars <= 0:
            continue

        weighting = str(f.get("weighting","equal")).lower()
        if weighting != "equal":
            raise ValueError(f"Unsupported weighting '{weighting}' in fund '{f.get('name','?')}'. Only 'equal' is implemented.")

        per_sym = fund_dollars / len(syms)
        for s in syms:
            ordered_syms.append(s)
            per_symbol_budget[s] = per_symbol_budget.get(s, 0.0) + per_sym

    # De-dup ordered_syms but preserve first-seen order
    seen = set(); ordered_syms = [s for s in ordered_syms if not (s in seen or seen.add(s))]
    return ordered_syms, per_symbol_budget


def resolve_model_path_for_infer(args, symbol: str, *, model_prefix: str | None = None) -> tuple[str, str]:
    from pathlib import Path
    sym = symbol.upper()
    mp = (model_prefix or getattr(args, "model_prefix", None) or "dqn_sy")  # << default to dqn_sy

    # If user passed --model, always honor it
    if getattr(args, "model", None):
        p = Path(args.model)
        if p.exists():
            return (str(p), "--model")

    # --- PROD: prefer legacy flat file first ---
    if getattr(args, "profile", "prod") == "prod":
        legacy = Path("models") / f"{mp}_{sym}.pt"
        if legacy.exists():
            return (str(legacy), "legacy_prefix")

    # Per-symbol LATEST.txt (works for exp or prod)
    sym_dir = Path(args.paths["models_dir"]) / sym
    latest = sym_dir / "LATEST.txt"
    if latest.exists():
        name = latest.read_text().strip()
        candidate = sym_dir / name
        if candidate.exists():
            return (str(candidate), "LATEST.txt")

    # EXP: if not found yet, also try legacy (useful if you keep flat files only)
    legacy_fallback = Path("models") / f"{mp}_{sym}.pt"
    if legacy_fallback.exists():
        return (str(legacy_fallback), "legacy_prefix")

    # Generic fallback if present
    generic = Path("models") / "dqn_policy_1y.pt"
    if generic.exists():
        return (str(generic), "generic_policy")

    raise SystemExit(
        f"[infer] No model found for {sym}. Tried legacy='models/{mp}_{sym}.pt', "
        f"LATEST under {sym_dir}, and generic={generic}. "
        f"Fix: train with 'splityear --symbols {sym} --model-prefix {mp}' or "
        f"'train --model models/dqn_policy_1y.pt'."
    )



# =========================
# Import your backtester
# =========================
BACKTESTER_MODULE = "backtester_daily_ml"

try:
    bt = __import__(BACKTESTER_MODULE)
except Exception as e:
    raise SystemExit(f"Could not import {BACKTESTER_MODULE}. Ensure rl_pipeline2.py is next to {BACKTESTER_MODULE}.py. Error: {e}")

REQUIRED_ATTRS = [
    "load_30s_to_daily","add_smas","add_labels_and_vol",
    "composite_from_weights","per_day_buffer","trend_project",
    "PRICE_COL","SMA_COLS","SLIPPAGE_PCT","FEE_PCT","FEE_FIXED",
    "START_CASH","START_STOCK","PROJECT_DAYS","TRADING_DAYS"
]
for name in REQUIRED_ATTRS:
    if not hasattr(bt, name):
        raise SystemExit(f"Your backtester module is missing '{name}'.")

def get_open_moc_map(tc: TradingClient):
    """Return {(symbol, side): [order, ...]} for today's open MOC orders (time_in_force=cls)."""
    ny = ZoneInfo("America/New_York")
    today = datetime.now(ny).date()

    # Prefer server-side status filter if available
    req = GetOrdersRequest(
        status = QueryOrderStatus.OPEN if HAS_QUERY_ENUM else None,
        nested = True,
        # not filtering by time here; we filter locally by submitted_at date
        limit  = 500
    )
    orders = list(tc.get_orders(filter=req))

    open_like = {
        "new","accepted","open","partially_filled","pending_new","pending_cancel","replaced"
    }

    moc = {}
    for o in orders:
        try:
            tif = str(getattr(o, "time_in_force", "")).lower()
            if tif != "cls":   # MOC orders are 'cls'
                continue
            sym  = getattr(o, "symbol", "")
            side = str(getattr(o, "side", "")).lower()
            st   = str(getattr(o, "status", "")).lower()

            # only consider *today's* orders
            sub_dt = getattr(o, "submitted_at", None)
            sub_day = sub_dt.date() if sub_dt else None
            if sub_day != today:
                continue

            if st not in open_like:
                continue

            moc.setdefault((sym, side), []).append(o)
        except Exception:
            continue
    return moc

def cancel_orders(tc: TradingClient, orders):
    for o in orders:
        oid = getattr(o, "id", None)
        if oid:
            try:
                tc.cancel_order_by_id(oid)
                print(f"[idempotent] canceled existing MOC {o.symbol} {o.side} id={oid}")
            except APIError as e:
                print(f"[idempotent] cancel failed for {oid}: {e}")

def connect_trading_auto(key: str | None = None, sec: str | None = None):
    """
    Try paper first, then live. Returns (client, resolved_env_str).
    Uses env vars APCA_API_KEY_ID / APCA_API_SECRET_KEY if key/sec are None.
    """
    import os
    key = key or os.getenv("APCA_API_KEY_ID")
    sec = sec or os.getenv("APCA_API_SECRET_KEY")
    if not key or not sec:
        raise RuntimeError("Missing APCA_API_KEY_ID / APCA_API_SECRET_KEY")

    def _try(paper_flag: bool):
        c = TradingClient(key, sec, paper=paper_flag)
        c.get_account()  # lightweight auth check
        return c

    last_err = None
    for pf in (True, False):  # paper -> live
        try:
            cli = _try(pf)
            return cli, ("paper" if pf else "live")
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError("Alpaca authentication failed (paper & live).") from last_err

# Optional guard fallback
if not hasattr(bt, "add_guardrails_and_filters"):
    def _guards_fallback(df: pd.DataFrame) -> pd.DataFrame:
        d = df.copy()
        hi = d.get("high_max"); lo = d.get("low_min"); cl = d.get("close_last")
        if hi is not None and lo is not None and cl is not None:
            prev_close = cl.shift(1)
            tr = pd.DataFrame({
                "hl": (hi - lo).abs(),
                "hc": (hi - prev_close).abs(),
                "lc": (lo - prev_close).abs(),
            }).max(axis=1)
            atr14 = tr.rolling(14).mean()
            d["atr14_pct"] = (atr14 / cl).replace([np.inf, -np.inf], np.nan)
        else:
            d["atr14_pct"] = np.nan
        sma200 = d[bt.PRICE_COL].rolling(200, min_periods=200).mean()
        d["bear_state"] = (d[bt.PRICE_COL] < sma200).fillna(False).astype(bool)
        rolling_low = d[bt.PRICE_COL].rolling(252, min_periods=252).min()
        d["near_52w_low"] = (d[bt.PRICE_COL] <= rolling_low * 1.02).fillna(False).astype(bool)
        d["gap_crash"] = (d[bt.PRICE_COL].pct_change() <= -0.07).fillna(False).astype(bool)
        d["block_long_mr"] = ((d["gap_crash"]) | (d["near_52w_low"] & (d["ret_1"] < -0.03))).astype(bool)
        return d
    bt.add_guardrails_and_filters = _guards_fallback
# =========================
# User paths (EDIT THESE)
# =========================
DATA_SOURCES: Dict[str,str] = {
    "QS":   r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\QS_30s.csv",
    "SLDP": r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\SLDP_30s.csv",
    "MSFT": r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\MSFT_30s.csv",
    "CHGG": r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\CHGG_30s.csv",
    "AI":   r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\AI_30s.csv",
    "NVDA": r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\NVDA_30s.csv",
    "TSM":  r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\TSM_30s.csv",
    "GOOGL":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\GOOGL_30s.csv",
    "AMD":  r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\AMD_30s.csv",
    "PAYO": r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\PAYO_30s.csv",
    "LCID": r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\LCID_30s.csv",
    "PLUG": r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\PLUG_30s.csv",
    "BYND": r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\BYND_30s.csv",
    "IBM":  r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\IBM_30s.csv",
    "RGTI": r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\RGTI_30s.csv",
    "QBTS": r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\QBTS_30s.csv",
    "QUBT": r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\QUBT_30s.csv",
    "IONQ": r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\IONQ_30s.csv",
    "TM": r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\TM_30s.csv",
    "TDC":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\TDC_30s.csv",
    "INFA":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\INFA_30s.csv",
    "SNOW":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\SNOW_30s.csv",
    "PSTG":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\PSTG_30s.csv",
    "MDB":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\MDB_30s.csv",
    "FSLR":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\FSLR_30s.csv",
    "ENPH":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\ENPH_30s.csv",
    "SEDG":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\SEDG_30s.csv",
    "ARRY":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\ARRY_30s.csv",
    "NXT":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\NXT_30s.csv",
    "ENVX":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\ENVX_30s.csv",
    "MVST":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\MVST_30s.csv",
    "EOSE":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\EOSE_30s.csv",
    "FLNC":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\FLNC_30s.csv",
    "EVG0":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\EVGO_30s.csv",
    "ITRI":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\ITRI_30s.csv",
    "AMSC":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\AMSC_30s.csv",
    "POWI":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\INFA_30s.csv",
    "VICR":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\SNOW_30s.csv",
    "NVTS":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\PSTG_30s.csv",
    "CLNE":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\MDB_30s.csv",
    "GEVO":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\GEVO_30s.csv",
    "MNTK":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\MNTK_30s.csv",
    "ELVA":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\ELVA_30s.csv",
    "XEL":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\XEL_30s.csv",
    "AEP":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\AEP_30s.csv",
    "RNW":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\RNW_30s.csv",
    "INTC":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\INTC_30s.csv",
    "ARQQ":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\ARQQ_30s.csv",   
    "MU":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\MU_30s.csv",
    "SMCI":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\SMCI_30s.csv",
    "TRV":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\TRV_30s.csv",
    "PGR":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\PGR_30s.csv",
    "BHP":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\BHP_30s.csv",
    "COST":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\COST_30s.csv",
    "MRK":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\MRK_30s.csv",
    "NFLX":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\NFLX_30s.csv",
    "RMBS":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\RMBS_30s.csv",
    "ALB":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\ALB_30s.csv",
    "VZ":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\VZ_30s.csv",
    "AAPL":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\AAPL_30s.csv",
    "PG":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\PG_30s.csv",
    "ROP":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\ROP_30s.csv",
    "NKLAQ":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\NKLAQ_30s.csv",
    "KO":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\KO_30s.csv",
    "PEP":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\PEP_30s.csv",
    "T":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\T_30s.csv",
    "TMUS":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\TMUS_30s.csv",
    "CMCSA":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\CMCSA_30s.csv",
    "CCI":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\KR_30s.csv",
        
    "KR":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\KR_30s.csv",
    "MDLZ":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\MDLZ_30s.csv",
    "GIS":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\GIS_30s.csv",
    "CBP":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\CBP_30s.csv",
    "MKC":r"C:\Users\brobi\OneDrive\Desktop\Algo1\data\MKC_30s.csv"

}
DAILY_CACHE_DIR = Path("daily_cache")

# =========================
# RL config
# =========================
WINDOW_DAYS = 500
TURNOVER_PENALTY = 1e-4

BIAS_CHOICES = ["trend","revert"]
BUF_SCALES   = [0.8, 1.0, 1.2]
POS_FRACS    = [0.20, 0.30, 0.40]
N_ACTIONS    = len(BIAS_CHOICES)*len(BUF_SCALES)*len(POS_FRACS)

def encode_action(bias_idx, buf_idx, pos_idx):
    return bias_idx * (len(BUF_SCALES)*len(POS_FRACS)) + buf_idx * len(POS_FRACS) + pos_idx

def decode_action(action_idx):
    n_buf, n_pos = len(BUF_SCALES), len(POS_FRACS)
    bias_idx = action_idx // (n_buf*n_pos)
    r = action_idx % (n_buf*n_pos)
    buf_idx = r // n_pos
    pos_idx = r % n_pos
    return bias_idx, buf_idx, pos_idx

OBS_FEATURES = [
    "px_div_sma1m", "px_div_sma1w", "sma1m_div_sma1y",
    "vol_21", "atr14_pct",
    "bear_state", "near_52w_low", "gap_crash",
    "px_minus_mid_over_mid", "buf",
    "yoy_rate",
]

# -------- CSV helpers --------
def _csv_append(path: str, fieldnames: List[str], row: dict):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    write_header = not p.exists() or p.stat().st_size == 0
    with p.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in fieldnames})



def _resolve_log_target_dir(dir_or_file: str, prefix: str, day: date) -> Path:
    """
    If 'dir_or_file' is a directory (recommended), create <dir>/<prefix>_YYYY-MM-DD.csv.
    If it's a file with .csv, we still roll daily by putting it NEXT to that file in its folder.
    """
    p = Path(dir_or_file)
    base_dir = p if (p.suffix == "" or p.is_dir()) else p.parent
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / f"{prefix}_{day.isoformat()}.csv"

def _to_float(x):
    try: return float(x)
    except Exception: return np.nan

def make_observation(row, mid, buf, yoy_rate):
    px = _to_float(row[bt.PRICE_COL])
    sma1m = _to_float(row.get("SMA_1M", np.nan))
    sma1w = _to_float(row.get("SMA_1W", np.nan))
    sma1y = _to_float(row.get("SMA_1Y", np.nan))
    atrp  = _to_float(row.get("atr14_pct", np.nan))
    vol21 = _to_float(row.get("vol_21", np.nan))
    bear  = 1.0 if bool(row.get("bear_state", False)) else 0.0
    nearL = 1.0 if bool(row.get("near_52w_low", False)) else 0.0
    gapC  = 1.0 if bool(row.get("gap_crash", False)) else 0.0
    px_div_sma1m = (px / sma1m - 1.0) if (sma1m and np.isfinite(sma1m)) else 0.0
    px_div_sma1w = (px / sma1w - 1.0) if (sma1w and np.isfinite(sma1w)) else 0.0
    sma1m_div_sma1y = (sma1m / sma1y - 1.0) if (sma1m and sma1y and np.isfinite(sma1m) and np.isfinite(sma1y)) else 0.0
    px_minus_mid_over_mid = ((px - mid) / mid) if (mid and np.isfinite(mid) and mid != 0) else 0.0
    return np.array([
        px_div_sma1m, px_div_sma1w, sma1m_div_sma1y,
        0.0 if not np.isfinite(vol21) else vol21,
        0.0 if not np.isfinite(atrp)  else atrp,
        bear, nearL, gapC,
        px_minus_mid_over_mid,
        0.0 if not np.isfinite(buf) else buf,
        0.0 if not np.isfinite(yoy_rate) else yoy_rate,
    ], dtype=np.float32)

# --- backtester result unpacker ---
def _unpack_run_result(res):
    """
    Extract:
      summ (dict), signals (DataFrame), bias_series (Series), equity_df (DataFrame with 'equity')
    """
    import pandas as pd
    summ = None; signals = None; bias_series = None; equity_df = None

    if isinstance(res, dict):
        summ = res.get("summary") or res.get("summ") or res.get("stats") or res.get("result")
        signals = res.get("signals") or res.get("trades") or res.get("orders")
        bias_series = res.get("bias_series") or res.get("bias")
        equity_df = res.get("equity_df") or res.get("equity") or res.get("equity_curve")
        return summ, signals, bias_series, equity_df

    seq = list(res) if isinstance(res, (list, tuple)) else [res]

    for x in seq:
        if isinstance(x, dict):
            if ("buy_hold_100_stock" in x) or ("period" in x) or ("alpha" in x) or ("fees" in x):
                summ = x; break

    for x in seq:
        if isinstance(x, pd.DataFrame) and "equity" in x.columns:
            equity_df = x
    if equity_df is None:
        for x in reversed(seq):
            if isinstance(x, pd.DataFrame):
                equity_df = x; break

    for x in seq:
        if hasattr(pd, "Series") and isinstance(x, pd.Series) and (getattr(x, "name", None) in ("bias","bias_series")):
            bias_series = x; break
        if isinstance(x, pd.DataFrame) and "bias" in x.columns:
            bias_series = x["bias"]; break

    for x in seq:
        if isinstance(x, pd.DataFrame) and any(c in x.columns for c in ("side","action","signal","trade")):
            signals = x; break

    return summ, signals, bias_series, equity_df

# ======= CHART HELPERS =======
def _ensure_dir(path: str):
    from pathlib import Path
    if path:
        Path(path).mkdir(parents=True, exist_ok=True)

def plot_price_vs_equity_with_markers(df: pd.DataFrame,
                                      symbol: str,
                                      save_dir: str = "./out_charts",
                                      fname: str | None = None,
                                      title: str | None = None):
    """
    Expects df with columns: date, price, equity, signal (1=BUY,0=SELL,-1=HOLD).
    Saves PNG to save_dir.
    """
    _ensure_dir(save_dir)
    dd = df.copy()
    dd["date"] = pd.to_datetime(dd["date"])
    buys  = dd[dd["signal"] == 1]
    sells = dd[dd["signal"] == 0]

    fig, ax1 = plt.subplots(figsize=(12, 5))
    ax1.plot(dd["date"], dd["price"], label="Price")
    if not buys.empty:
        ax1.scatter(buys["date"], buys["price"], marker="^", s=60, label="BUY")
    if not sells.empty:
        ax1.scatter(sells["date"], sells["price"], marker="v", s=60, label="SELL")
    ax1.set_xlabel("Date"); ax1.set_ylabel("Price")

    ax2 = ax1.twinx()
    ax2.plot(dd["date"], dd["equity"], linestyle="--", label="Equity")
    ax2.set_ylabel("Equity ($)")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="best")

    ttl = title or f"{symbol} Price (left) vs Equity (right) with Trades"
    ax1.set_title(ttl)
    fig.tight_layout()

    out = Path(save_dir) / (fname or f"{symbol}_price_vs_equity.png")
    fig.savefig(out, dpi=150, bbox_inches="tight"); plt.close(fig)
    print(f"Saved {out.resolve()}")

def plot_price_vs_notional_with_markers(df: pd.DataFrame,
                                        symbol: str,
                                        save_dir: str = "./out_charts",
                                        fname: str | None = None,
                                        title: str | None = None):
    """
    Expects df with columns: date, price, controlled_value, signal.
    Saves PNG to save_dir.
    """
    _ensure_dir(save_dir)
    dd = df.copy()
    dd["date"] = pd.to_datetime(dd["date"])
    buys  = dd[dd["signal"] == 1]
    sells = dd[dd["signal"] == 0]

    fig, ax1 = plt.subplots(figsize=(12, 5))
    ax1.plot(dd["date"], dd["price"], label="Price")
    if not buys.empty:
        ax1.scatter(buys["date"], buys["price"], marker="^", s=60, label="BUY")
    if not sells.empty:
        ax1.scatter(sells["date"], sells["price"], marker="v", s=60, label="SELL")
    ax1.set_xlabel("Date"); ax1.set_ylabel("Price")

    ax2 = ax1.twinx()
    ax2.plot(dd["date"], dd["controlled_value"], linestyle="--", label="Total Value Controlled")
    ax2.set_ylabel("Total Value Controlled ($)")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="best")

    ttl = title or f"{symbol}  Price (left) vs Total Value Controlled (right) with Trades"
    ax1.set_title(ttl)
    fig.tight_layout()

    out = Path(save_dir) / (fname or f"{symbol}_price_vs_notional.png")
    fig.savefig(out, dpi=150, bbox_inches="tight"); plt.close(fig)
    print(f"Saved {out.resolve()}")


# =========================
# Alpaca (optional) daily & intraday fetch
# =========================
def _iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

def merge_daily(existing: pd.DataFrame, add: pd.DataFrame) -> pd.DataFrame:
    """
    Merge two daily dataframes on 'date', dedupe on date (keep last), and sort.
    Columns expected: ['date','open_first','high_max','low_min','close_last','volume'].
    """
    if existing is None or existing.empty:
        out = add.copy()
    else:
        e = existing.copy()
        a = add.copy()
        # normalize date dtype
        e["date"] = pd.to_datetime(e["date"])
        a["date"] = pd.to_datetime(a["date"])

        # ensure the standard columns exist (fill missing with NaN)
        cols = ["date","open_first","high_max","low_min","close_last","volume"]
        for c in cols:
            if c not in e.columns: e[c] = np.nan
            if c not in a.columns: a[c] = np.nan

        out = (
            pd.concat([e[cols], a[cols]], ignore_index=True)
              .drop_duplicates(subset=["date"], keep="last")
              .sort_values("date")
              .reset_index(drop=True)
        )
    return out

# ---------- Alpaca headers + resilient fetch across FEED x ADJUSTMENT ----------
def _alpaca_headers():
    key = os.getenv("ALPACA_KEY_ID")
    sec = os.getenv("ALPACA_SECRET_KEY")
    if not key or not sec:
        return None, None
    return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec}, key

def _try_bars(url, base_params, headers,
              feeds=("env","iex"),
              adjustments=("env","all","raw",None),
              timeout=30):
    """
    Try combinations of feed x adjustment until one works.
      - Feeds: env (ALPACA_FEED), then 'iex', then 'sip'
      - Adjustments: env (ALPACA_ADJUSTMENT), 'all', 'raw', then none
    Returns parsed JSON or None.
    """
    # Build feed chain with de-dup
    env_feed = os.getenv("ALPACA_FEED", "").strip().lower()
    feed_order = []
    for f in feeds:
        if f == "env":
            if env_feed: feed_order.append(env_feed)
        else:
            feed_order.append(f)
    seen = set(); feed_chain = [f for f in feed_order if not (f in seen or seen.add(f))]

    # Build adjustment chain with de-dup
    env_adj = os.getenv("ALPACA_ADJUSTMENT", "").strip().lower()
    adj_order = []
    for a in adjustments:
        if a == "env":
            if env_adj: adj_order.append(env_adj)
        else:
            adj_order.append(a)
    seen = set(); adj_chain = [a for a in adj_order if not (a in seen or seen.add(a))]

    last_err = None
    for feed in feed_chain:
        for adj in adj_chain:
            params = dict(base_params)
            if feed:
                params["feed"] = feed
            if adj is None:
                params.pop("adjustment", None)
                adj_label = "none"
            else:
                params["adjustment"] = adj
                adj_label = adj
            try:
                r = requests.get(url, params=params, headers=headers, timeout=timeout)
                if r.status_code == 403:
                    print(f"[Alpaca] 403 with feed={feed}, adjustment={adj_label}; trying next combo...")
                    continue
                r.raise_for_status()
                print(f"[Alpaca] ok with feed={feed}, adjustment={adj_label}")
                return r.json()
            except Exception as e:
                last_err = e
                # try next combo
                continue

    print(f"[Alpaca] all FEED/ADJUSTMENT combos failed. Last error: {last_err}")
    return None

def fetch_alpaca_daily_bars(symbol: str, start_iso: str, end_iso: str, adjustment: str = None) -> pd.DataFrame:
    headers, key = _alpaca_headers()
    if headers is None:
        return pd.DataFrame(columns=["date","open_first","high_max","low_min","close_last","volume"])
    print(f"[Alpaca] Using key: {key[:4]}...{key[-4:]} (len={len(key)})")

    url = f"https://data.alpaca.markets/v2/stocks/{symbol}/bars"
    base_params = {"timeframe":"1Day","start":start_iso,"end":end_iso,"limit":10000}
    if adjustment:
        base_params["adjustment"] = adjustment  # optional override

    js = _try_bars(url, base_params, headers, timeout=30)
    if not js:
        print(f"[Alpaca] fetch failed for {symbol}: all adjustment/feed modes blocked or error.")
        return pd.DataFrame(columns=["date","open_first","high_max","low_min","close_last","volume"])

    bars = js.get("bars", [])
    if not bars:
        return pd.DataFrame(columns=["date","open_first","high_max","low_min","close_last","volume"])

    df = (pd.DataFrame(bars)
            .rename(columns={"t":"date","o":"open_first","h":"high_max","l":"low_min","c":"close_last","v":"volume"}))
    df["date"] = pd.to_datetime(df["date"]).dt.tz_convert("UTC").dt.tz_localize(None)
    return df[["date","open_first","high_max","low_min","close_last","volume"]].sort_values("date").reset_index(drop=True)

def fetch_alpaca_intraday_bars(symbol: str, start_iso: str, end_iso: str,
                               timeframe: str = "1Min", adjustment: str = None) -> pd.DataFrame:
    headers, key = _alpaca_headers()
    if headers is None:
        return pd.DataFrame(columns=["t","o","h","l","c","v"])

    url = f"https://data.alpaca.markets/v2/stocks/{symbol}/bars"
    base_params = {"timeframe": timeframe, "start": start_iso, "end": end_iso, "limit": 10000}
    base_params["feed"] = os.getenv("ALPACA_FEED", "iex")   # <—    
    if adjustment:
        base_params["adjustment"] = adjustment  # optional override

    js = _try_bars(url, base_params, headers, timeout=20)
    if not js:
        print(f"[Alpaca] intraday fetch failed for {symbol}: adjustments/feeds blocked or error.")
        return pd.DataFrame(columns=["t","o","h","l","c","v"])

    bars = js.get("bars", [])
    return pd.DataFrame(bars) if bars else pd.DataFrame(columns=["t","o","h","l","c","v"])

def append_provisional_today_bar(base_daily: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """
    Aggregate today's 1-minute bars (09:30 ET -> now ET) into a provisional daily bar
    and merge into the daily df. If no minutes available (off-hours/blocked), returns base unchanged.
    """
    now_utc = datetime.now(timezone.utc)
    now_et  = now_utc.astimezone(ZoneInfo("America/New_York"))
    today_et = now_et.date()

    # 09:30 ET to 'now' ET
    start_et = datetime.combine(today_et, datetime.min.time(), tzinfo=ZoneInfo("America/New_York")).replace(hour=9, minute=30)
    end_et   = now_et
    if end_et <= start_et:
        return base_daily

    start_iso = _iso_utc(start_et.astimezone(timezone.utc))
    end_iso   = _iso_utc(end_et.astimezone(timezone.utc))

    # (Nice-to-have) print which key weâ€™re using, if helper is available
    try:
        _print_key_fingerprint_once()
    except NameError:
        pass

    # NOTE: call without passing adjustment/feed here
    mins = fetch_alpaca_intraday_bars(symbol, start_iso, end_iso, timeframe="1Min")
    if mins.empty:
        print(f"[Alpaca] No minute bars for {symbol} between {start_iso} and {end_iso}; skipping provisional.")
        return base_daily

    df = mins.rename(columns={"t":"date","o":"open","h":"high","l":"low","c":"close","v":"volume"}).copy()
    # Server returns UTC; convert to naive UTC timestamps for consistency with our daily schema
    df["date"] = pd.to_datetime(df["date"]).dt.tz_convert("UTC").dt.tz_localize(None)
    df = df.sort_values("date").reset_index(drop=True)

    open_first = float(df["open"].iloc[0])
    high_max   = float(df["high"].max())
    low_min    = float(df["low"].min())
    close_last = float(df["close"].iloc[-1])
    vol_sum    = float(df["volume"].sum())

    row = pd.DataFrame([{
        "date": pd.Timestamp(today_et),   # keep as ET calendar date
        "open_first": open_first,
        "high_max": high_max,
        "low_min": low_min,
        "close_last": close_last,
        "volume": vol_sum,
    }])

    return merge_daily(_normalize_daily_schema(base_daily), row)


def _normalize_daily_schema(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    if "date" not in d.columns:
        for c in d.columns:
            if "date" in c or "time" in c:
                d = d.rename(columns={c:"date"})
                break
    rename_map = {}
    if "open" in d.columns:  rename_map["open"]  = "open_first"
    if "high" in d.columns:  rename_map["high"]  = "high_max"
    if "low"  in d.columns:  rename_map["low"]   = "low_min"
    if "close" in d.columns: rename_map["close"] = "close_last"
    if rename_map: d = d.rename(columns=rename_map)

    keep = [c for c in ["date","open_first","high_max","low_min","close_last","volume"] if c in d.columns]
    d = d[keep].copy()
    d["date"] = pd.to_datetime(d["date"])
    d = d.sort_values("date").reset_index(drop=True)
    return d

def ensure_backtester_compat(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    for col in ["open_first","high_max","low_min","close_last","volume"]:
        if col not in d.columns:
            d[col] = np.nan
    if "close_mean" not in d.columns:
        d["close_mean"] = d["close_last"]
    if "vol_sum" not in d.columns:
        d["vol_sum"] = d["volume"] if "volume" in d.columns else np.nan
    if hasattr(bt, "PRICE_COL") and bt.PRICE_COL not in d.columns:
        d[bt.PRICE_COL] = d["close_last"]
    if "date" in d.columns:
        d["date"] = pd.to_datetime(d["date"])
        d = d.sort_values("date").reset_index(drop=True)
    for c in ["open_first","high_max","low_min","close_last","close_mean","volume","vol_sum"]:
        if c in d.columns:
            d[c] = pd.to_numeric(d[c], errors="coerce")
    return d

def load_or_refresh_daily(symbol: str,
                          thirtysec_csv: Optional[str],
                          since: Optional[str],
                          do_refresh: bool) -> pd.DataFrame:
    """
    Load cached daily bars (or build from 30s CSV once), then optionally refresh from Alpaca.
    This version avoids passing extra params that can trigger entitlements issues downstream.
    """
    DAILY_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = DAILY_CACHE_DIR / f"{symbol}_daily.csv"

    # Load existing cache or build from 30s CSV
    if cache_path.exists():
        daily = pd.read_csv(cache_path)
        daily["date"] = pd.to_datetime(daily["date"])
        daily = _normalize_daily_schema(daily)
    elif thirtysec_csv and os.path.exists(thirtysec_csv):
        daily = bt.load_30s_to_daily(Path(thirtysec_csv))
        daily = _normalize_daily_schema(daily)
        daily.to_csv(cache_path, index=False)
    else:
        daily = pd.DataFrame(columns=["date","open_first","high_max","low_min","close_last","volume"])

    # Optional online refresh
    if do_refresh:
        # (Nice-to-have) print which key weâ€™re using, if helper is available
        try:
            _print_key_fingerprint_once()
        except NameError:
            pass

        today = datetime.now(timezone.utc).date()
        if since:
            start_date = datetime.fromisoformat(since).date()
        elif not daily.empty:
            last_date = pd.to_datetime(daily["date"].iloc[-1]).date()
            start_date = (last_date + timedelta(days=1))
        else:
            start_date = today - timedelta(days=365*2)

        if start_date <= today:
            start_iso = _iso_utc(datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc))
            end_iso   = _iso_utc(datetime.combine(today + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc))

            # NOTE: call without passing adjustment/feed here
            add = fetch_alpaca_daily_bars(symbol, start_iso, end_iso)
            if not add.empty:
                daily = merge_daily(daily, add)
                daily.to_csv(cache_path, index=False)
                print(f"[Alpaca] Updated {symbol}: +{len(add)} bars â†’ {cache_path}")
            else:
                print(f"[Alpaca] No new bars for {symbol} (empty or blocked).")
        else:
            print(f"[Alpaca] {symbol} up-to-date.")

    return daily

# ---- Debug helper: print key fingerprint once ----
_ALPACA_FP_PRINTED = False
def _print_key_fingerprint_once():
    """Log a masked ALPACA_KEY_ID once per process to verify which key Python uses."""
    global _ALPACA_FP_PRINTED
    if _ALPACA_FP_PRINTED:
        return
    kid = os.getenv("ALPACA_KEY_ID", "")
    if kid:
        vis = kid if len(kid) <= 8 else f"{kid[:4]}...{kid[-4:]}"
        print(f"[Alpaca] Using key: {vis} (len={len(kid)})")
    else:
        print("[Alpaca] No ALPACA_KEY_ID found in env.")
    _ALPACA_FP_PRINTED = True
def get_daily_df(symbol: str, alpaca_update: bool = False, since: Optional[str] = None,
                 include_provisional_today: bool = False) -> pd.DataFrame:
    """
    Full prep for backtester:
      - load/refresh daily
      - optional: append a provisional 'today' bar aggregated from 1-minutes
      - ensure backtester compatibility
      - add SMAs, labels/vol, guardrails
    """
    base = load_or_refresh_daily(symbol, DATA_SOURCES.get(symbol), since, do_refresh=alpaca_update)
    if include_provisional_today:
        base = append_provisional_today_bar(base, symbol)
    base = ensure_backtester_compat(base)
    try:
        d = bt.add_smas(base.copy())
        d = bt.add_labels_and_vol(d)
        d = bt.add_guardrails_and_filters(d)
    except Exception as e:
        print(f"[{symbol}] add_* pipeline failed: {e}")
        raise
    return d

def assert_backtester_ready(df: pd.DataFrame):
    required = ["SMA_1Y","SMA_1M","SMA_1W","SMA_1D",
                "vol_21","atr14_pct","bear_state","near_52w_low","gap_crash"]
    missing = [c for c in required if c not in df.columns]
    assert not missing, f"DataFrame missing required columns: {missing}"

# =========================
# Environment
# =========================

class TradingEnv:
    def __init__(self, daily_df: pd.DataFrame, i0: int, iN: int,
                 regime_weights: dict, yoy_rate: float,
                 apply_trend=True, allow_bear_guard=True, allow_behavioral=True,
                 lambda_neg: float = 0.5,
                 lambda_dd: float  = 0.0,
                 turnover_penalty: float = None,
                 reward_clip: float = 0.03,
                 regime_penalty: float = 0.3,
                 high_atr_q: float = 0.67):
        self.d = daily_df.reset_index(drop=True)
        self.i0 = int(i0); self.iN = int(iN)
        self.w = regime_weights
        self.apply_trend = bool(apply_trend)
        self.yoy_rate = float(yoy_rate)
        self.allow_bear = bool(allow_bear_guard)
        self.allow_beh  = bool(allow_behavioral)
        self.lambda_neg = float(lambda_neg)
        self.lambda_dd  = float(lambda_dd)
        self.turnover_penalty_override = (None if turnover_penalty is None else float(turnover_penalty))
        self.reward_clip = None if reward_clip is None else float(reward_clip)
        self.regime_penalty = float(regime_penalty)
        self.high_atr_q = float(high_atr_q)
        self.t: Optional[int] = None
        self.cash: Optional[float] = None
        self.shares: Optional[float] = None
        self._peak_equity: float = 1.0
        self._atr_threshold: Optional[float] = None
        mids = []
        for _, row in self.d.iterrows():
            mids.append(bt.composite_from_weights(row, self.w))
        self.mid = np.array(mids, dtype=float)
        assert 0 <= self.i0 < self.iN < len(self.d), "Invalid window for env."
        try:
            atr_slice = pd.to_numeric(self.d.loc[self.i0:self.iN, "atr14_pct"], errors="coerce").dropna()
            self._atr_threshold = float(atr_slice.quantile(self.high_atr_q)) if len(atr_slice) > 50 else None
        except Exception:
            self._atr_threshold = None

    def reset(self):
        self.t = self.i0
        px0 = float(self.d.loc[self.i0, bt.PRICE_COL])
        self.shares = bt.START_STOCK / px0
        self.cash   = float(bt.START_CASH)
        self._peak_equity = self._equity(self.i0)
        mid, buf = self._bands(self.t, base_buf_scale=1.0)
        return make_observation(self.d.loc[self.t], mid, buf, self.yoy_rate)

    def _equity(self, t_idx):
        px = float(self.d.loc[t_idx, bt.PRICE_COL])
        return self.cash + self.shares * px

    def _bands(self, t_idx, base_buf_scale=1.0):
        base_mid = self.mid[t_idx]
        if not np.isfinite(base_mid):
            base_mid = float(self.d.loc[t_idx, bt.PRICE_COL])
        _yoy   = 0.0 if getattr(self, "yoy_rate", None) is None else float(self.yoy_rate)
        _apply = bool(getattr(self, "apply_trend", True))
        mid    = trend_project_compat(bt, base_mid, _yoy, apply_trend=_apply)
        vol = float(self.d.loc[t_idx, "vol_21"])
        K_BUFFER, MIN_BUF, MAX_BUF = 1.00, 0.010, 0.03
        buf = bt.per_day_buffer(vol, K_BUFFER * base_buf_scale, MIN_BUF, MAX_BUF)
        return mid, buf

    def _candidate_signal(self, t_idx, bias, upper, lower):
        px = float(self.d.loc[t_idx, bt.PRICE_COL])
        if bias == "trend":
            return 1 if px > upper else (0 if px < lower else -1)
        else:
            return 0 if px > upper else (1 if px < lower else -1)

    def _apply_guards(self, t_idx, bias, action_signal):
        if action_signal != 1:
            return action_signal
        if self.allow_bear and bias == "trend":
            if bool(self.d.loc[t_idx].get("bear_state", False)):
                return -1
        if self.allow_beh and bias == "revert":
            if bool(self.d.loc[t_idx].get("block_long_mr", False)):
                return -1
        return action_signal

    def _shape_reward(self, raw_ret: float, traded_notional: float, equity_t: float, row) -> float:
        
        # 1) Base reward (safe)
        r = float(raw_ret) if np.isfinite(raw_ret) else 0.0

        # 2) Clip (unchanged semantics)
        if self.reward_clip is not None:
            hi = self.reward_clip; lo = -self.reward_clip
            if r > hi: r = hi
            if r < lo: r = lo

        # 3) Negative-return penalty (unchanged semantics)
        if r < 0.0 and self.lambda_neg:
            r = r - self.lambda_neg * abs(r)

        # 4) Turnover penalty (same logic, but robust to NaN/Inf/<=0 override)
        eff_tp = self.turnover_penalty_override
        if eff_tp is None or not np.isfinite(eff_tp) or eff_tp <= 0:
            eff_tp = TURNOVER_PENALTY

        if (np.isfinite(traded_notional) and np.isfinite(equity_t)
            and traded_notional > 0.0 and equity_t > 1e-12
            and eff_tp and np.isfinite(eff_tp) and eff_tp > 0.0):
            r -= float(eff_tp) * float(traded_notional / equity_t)

        # 5) Peak equity / drawdown (unchanged semantics, but safe)
        if np.isfinite(equity_t):
            self._peak_equity = max(self._peak_equity, float(equity_t))
        if self.lambda_dd and self._peak_equity > 0.0 and np.isfinite(self._peak_equity) and np.isfinite(equity_t):
            dd = max(0.0, 1.0 - float(equity_t) / self._peak_equity)
            if np.isfinite(dd):
                r -= self.lambda_dd * dd

        # 6) Regime flags (unchanged semantics, but robust parsing)
        try:
            bear  = bool(row.get("bear_state", False))
            crash = bool(row.get("gap_crash", False))
            atr   = float(row.get("atr14_pct", 0.0))
            if not np.isfinite(atr):
                atr = 0.0
        except Exception:
            bear = crash = False; atr = 0.0

        regime_bad = False
        if bear or crash:
            regime_bad = True
        else:
            if self._atr_threshold is not None and np.isfinite(self._atr_threshold):
                regime_bad = atr >= self._atr_threshold
            else:
                regime_bad = atr > 0.06

        if regime_bad and 0.0 <= getattr(self, "regime_penalty", 0.0) < 1.0:
            # NOTE: keeps your original semantics (multiply by penalty factor in [0,1))
            r = r * self.regime_penalty

        # 7) Final safety
        if not math.isfinite(r):
            r = 0.0
        return float(r)


    def step(self, action_idx: int):
        assert self.t is not None, "Call reset() first."
        bias_idx, buf_idx, pos_idx = decode_action(action_idx)
        bias = BIAS_CHOICES[bias_idx]
        buf_scale = BUF_SCALES[buf_idx]
        pos_frac  = POS_FRACS[pos_idx]
        mid, base_buf = self._bands(self.t, base_buf_scale=buf_scale)
        upper = mid * (1.0 + base_buf)
        lower = mid * (1.0 - base_buf)
        pre_sig = self._candidate_signal(self.t, bias, upper, lower)
        sig = self._apply_guards(self.t, bias, pre_sig)
        px = float(self.d.loc[self.t, bt.PRICE_COL])
        traded_notional = 0.0
        if sig == 1 and self.cash > 0:
            exec_px = px * (1.0 + bt.SLIPPAGE_PCT)
            spend   = pos_frac * self.cash
            denom   = exec_px * (1.0 + bt.FEE_PCT)
            qty     = max(0.0, (spend - bt.FEE_FIXED) / denom) if denom > 0 else 0.0
            cost    = qty * exec_px
            fees    = cost * bt.FEE_PCT + bt.FEE_FIXED
            if cost + fees > self.cash:
                qty = max(0.0, (self.cash - bt.FEE_FIXED) / (exec_px * (1.0 + bt.FEE_PCT)))
                cost = qty * exec_px; fees = cost * bt.FEE_PCT + bt.FEE_FIXED
            if qty > 0:
                self.shares += qty; self.cash -= (cost + fees)
                traded_notional = qty * px
        elif sig == 0 and self.shares > 0:
            qty     = pos_frac * self.shares
            exec_px = px * (1.0 - bt.SLIPPAGE_PCT)
            gross   = qty * exec_px
            fees    = gross * bt.FEE_PCT + bt.FEE_FIXED
            net     = max(0.0, gross - fees)
            if qty > 0:
                self.shares -= qty; self.cash += net
                traded_notional = qty * px
        equity_t = self._equity(self.t)
        next_t   = self.t + 1
        if next_t <= self.iN:
            px2 = float(self.d.loc[next_t, bt.PRICE_COL])
            equity_next = self.cash + self.shares * px2
        else:
            equity_next = equity_t
        raw_ret = (equity_next / max(1e-9, equity_t)) - 1.0
        row_now = self.d.loc[self.t]
        reward  = self._shape_reward(raw_ret=raw_ret, traded_notional=traded_notional, equity_t=equity_t, row=row_now)
        self.t = next_t
        done = bool(self.t >= self.iN)
        if not done:
            mid_next, buf_next = self._bands(self.t, base_buf_scale=1.0)
            obs_next = make_observation(self.d.loc[self.t], mid_next, buf_next, self.yoy_rate)
        else:
            obs_next = np.zeros(len(OBS_FEATURES), dtype=np.float32)
        info = {"reward": float(reward), "raw_reward": float(raw_ret), "signal": int(sig), "bias": bias,
                "peak_equity": float(self._peak_equity)}
        return obs_next, float(reward), done, info

class QNet(nn.Module):
    def __init__(self, obs_dim, n_actions):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(obs_dim, 128), nn.ReLU(),
            nn.Linear(128, 128), nn.ReLU(),
            nn.Linear(128, n_actions)
        )
    def forward(self, x): return self.net(x)

class Replay:
    def __init__(self, capacity=200_000):
        self.cap = capacity; self.buf = []; self.pos = 0
    def push(self, s, a, r, s2, d):
        if len(self.buf) < self.cap: self.buf.append(None)
        self.buf[self.pos] = (s, a, r, s2, d)
        self.pos = (self.pos + 1) % self.cap
    def sample(self, batch):
        batch = random.sample(self.buf, batch)
        s,a,r,s2,d = zip(*batch)
        return (np.stack(s), np.array(a), np.array(r, dtype=np.float32),
                np.stack(s2), np.array(d, dtype=np.float32))
    def __len__(self): return len(self.buf)



# ---------- Device-safe Q helper ----------
def _q_argmax_device_safe(q_mod, obs_np_arr):
    dev = next(q_mod.parameters()).device
    x = torch.tensor(obs_np_arr, dtype=torch.float32, device=dev).unsqueeze(0)
    with torch.no_grad():
        return int(q_mod(x).argmax(dim=1).item())
# =========================
# Atomic model save (Windows safe)
# =========================
def safe_torch_save(obj, path, retries=8, delay=0.25):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    last_err = None
    for _ in range(retries):
        try:
            torch.save(obj, tmp)
            os.replace(tmp, path)
            return
        except Exception as e:
            last_err = e
            time.sleep(delay)
    fallback = path.with_name(f"{path.stem}_{int(time.time())}{path.suffix}")
    torch.save(obj, fallback)
    print(f"WARNING: could not write {path}. Wrote fallback {fallback}. Last error: {last_err}")

# =========================
# Training
# =========================
def train_dqn(envs: List[TradingEnv], episodes=250, gamma=0.99, lr=3e-4, batch=256,
              eps_start=1.0, eps_end=0.05, eps_decay=0.995,
              target_sync=500, update_after=1000, updates_per_step=1,
              device = torch.device("cuda" if torch.cuda.is_available() else "cpu"), seed=123, save_path="dqn_policy_1y.pt"):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    obs_dim = len(OBS_FEATURES)
    q = QNet(obs_dim, N_ACTIONS).to(device)
    q_tgt = QNet(obs_dim, N_ACTIONS).to(device)
    q_tgt.load_state_dict(q.state_dict())
    opt = optim.Adam(q.parameters(), lr=lr)
    rb  = Replay()
    eps = eps_start
    total_steps = 0
    best_eval = -1e18

    def _select_action(state_np):
        nonlocal eps
        if random.random() < eps:
            return random.randrange(N_ACTIONS)
        with torch.no_grad():
            s = torch.tensor(state_np, dtype=torch.float32, device=device).unsqueeze(0)
            return int(q(s).argmax(dim=1).item())

    for ep in range(1, episodes+1):
        env = envs[(ep-1) % len(envs)]
        s = env.reset(); ep_reward = 0.0; done = False
        while not done:
            a = _select_action(s)
            s2, r, done, info = env.step(a)
            rb.push(s, a, r, s2, float(done))
            s = s2; ep_reward += r; total_steps += 1

            if len(rb) >= update_after:
                for _ in range(updates_per_step):
                    ss, aa, rr, ss2, dd = rb.sample(batch)
                    ss  = torch.tensor(ss, dtype=torch.float32, device=device)
                    aa  = torch.tensor(aa, dtype=torch.int64,   device=device)
                    rr  = torch.tensor(rr, dtype=torch.float32, device=device)
                    ss2 = torch.tensor(ss2, dtype=torch.float32, device=device)
                    dd  = torch.tensor(dd, dtype=torch.float32, device=device)

                    with torch.no_grad():
                        q2 = q_tgt(ss2).max(dim=1).values
                        y  = rr + gamma * (1.0 - dd) * q2
                    qv = q(ss).gather(1, aa.view(-1,1)).squeeze(1)
                    loss = nn.functional.smooth_l1_loss(qv, y)

                    opt.zero_grad(); loss.backward()
                    nn.utils.clip_grad_norm_(q.parameters(), 1.0)
                    opt.step()

            if total_steps % target_sync == 0:
                q_tgt.load_state_dict(q.state_dict())

        eps = max(eps_end, eps * eps_decay)
        if ep_reward > best_eval:
            best_eval = ep_reward
            safe_torch_save({"model": q.state_dict(), "obs_features": OBS_FEATURES}, save_path)
        print(f"Episode {ep:4d} | steps={total_steps:6d} | eps={eps:5.3f} | ep_reward={ep_reward:,.5f} | best={best_eval:,.5f}")

    print(f"Saved best model to {save_path}")
    return save_path

# =========================
# Helpers
# =========================
def load_policy(model_path: str, device="cpu") -> QNet:
    # Use weights_only=True when available to avoid pickle execution and silence FutureWarning.
    try:
        state = torch.load(model_path, map_location=device, weights_only=True)
    except TypeError:
        # Older PyTorch: no weights_only param
        state = torch.load(model_path, map_location=device)
    q = QNet(len(OBS_FEATURES), N_ACTIONS).to(device)
    q.load_state_dict(state["model"])
    q.eval()
    return q.eval()
    return q

def rollout_greedy(env: TradingEnv, qnet: QNet, return_actions: bool=False):
    # ensure we use the model's device for all tensors
    dev = next(qnet.parameters()).device

    s = env.reset()
    dates = [pd.to_datetime(env.d.loc[env.t, "date"])]
    px0   = float(env.d.loc[env.t, bt.PRICE_COL])
    equities = [env._equity(env.t)]
    prices   = [px0]
    signals  = [-1]  # first step has no action yet
    shares_l = [float(env.shares)]
    notional = [abs(float(env.shares)) * px0]

    action_log = []

    while True:
        with torch.no_grad():
            s_t = torch.tensor(s, dtype=torch.float32, device=dev).unsqueeze(0)
            a = int(qnet(s_t).argmax(dim=1).item())
        b_idx, f_idx, p_idx = decode_action(a)
        action_log.append({
            "date": pd.to_datetime(env.d.loc[env.t, "date"]),
            "bias": BIAS_CHOICES[b_idx],
            "buf_scale": BUF_SCALES[f_idx],
            "pos_frac": POS_FRACS[p_idx],
        })

        s, r, done, info = env.step(a)

        t_mark = min(env.t, env.iN)
        dt  = pd.to_datetime(env.d.loc[t_mark, "date"])
        px  = float(env.d.loc[t_mark, bt.PRICE_COL])
        eq  = env._equity(t_mark)

        dates.append(dt)
        equities.append(eq)
        prices.append(px)
        signals.append(int(info.get("signal", -1)))
        shares_l.append(float(env.shares))
        notional.append(abs(float(env.shares)) * px)

        if done:
            break

    curve = pd.DataFrame({
        "date": dates,
        "equity": equities,
        "price": prices,
        "signal": signals,
        "shares": shares_l,
        "controlled_value": notional
    }).sort_values("date")

    if return_actions:
        return curve, pd.DataFrame(action_log)
    return curve


def score_equity(curve: pd.DataFrame, trading_days=252) -> Dict[str,float]:
    df = curve.copy().sort_values("date")
    ret = df["equity"].pct_change().dropna()
    if ret.empty:
        return {"cagr": np.nan, "sharpe": np.nan, "sortino": np.nan, "max_dd": np.nan,
                "calmar": np.nan, "final_equity": float(df["equity"].iloc[-1])}
    T_years = max(1e-9, (df["date"].iloc[-1] - df["date"].iloc[0]).days / 365.25)
    cagr = (df["equity"].iloc[-1] / df["equity"].iloc[0])**(1.0/T_years) - 1.0
    ann_vol = ret.std() * np.sqrt(trading_days)
    neg = ret[ret < 0]
    ann_down = (neg.std() * np.sqrt(trading_days)) if len(neg) else np.nan
    sharpe = (ret.mean()*trading_days) / ann_vol if ann_vol>0 else np.nan
    sortino = (ret.mean()*trading_days) / ann_down if (isinstance(ann_down, float) and ann_down>0) else np.nan
    cum = (1+ret).cumprod()
    peak = cum.cummax()
    dd = (cum/peak - 1.0).min() if len(cum) else np.nan
    calmar = (ret.mean()*trading_days) / abs(dd) if (isinstance(dd, float) and dd<0) else np.nan
    return {"cagr": float(cagr), "sharpe": float(sharpe) if sharpe==sharpe else np.nan,
            "sortino": float(sortino) if sortino==sortino else np.nan,
            "max_dd": float(dd) if dd==dd else np.nan, "calmar": float(calmar) if calmar==calmar else np.nan,
            "final_equity": float(df["equity"].iloc[-1])}

def _bh_pct_vs_100(summ: dict) -> float:
    bh_final = float(summ.get("buy_hold_100_stock", np.nan))
    return (bh_final / 100.0) - 1.0 if np.isfinite(bh_final) else np.nan

def _fmt_pct(x):
    return "NaN" if (x is None or not np.isfinite(x)) else f"{x*100:.2f}%"

def _fmt_num(x):
    return "NaN" if (x is None or not np.isfinite(x)) else f"{x:,.2f}"

def print_side_by_side_console(sym, m_rl_tr, m_rb_tr, m_rl_ts, m_rb_ts, summ_tr, summ_ts):
    bh_tr = _bh_pct_vs_100(summ_tr)
    bh_ts = _bh_pct_vs_100(summ_ts)
    rows = [
        ["TRAIN","RL",   _fmt_num(m_rl_tr["final_equity"]), _fmt_pct(m_rl_tr["cagr"]), _fmt_num(m_rl_tr["sharpe"]), _fmt_pct(m_rl_tr["max_dd"]), "—"],
        ["TRAIN","Rule", _fmt_num(m_rb_tr["final_equity"]), _fmt_pct(m_rb_tr["cagr"]), _fmt_num(m_rb_tr["sharpe"]), _fmt_pct(m_rb_tr["max_dd"]), _fmt_pct(bh_tr)],
        ["OOS",  "RL",   _fmt_num(m_rl_ts["final_equity"]), _fmt_pct(m_rl_ts["cagr"]), _fmt_num(m_rl_ts["sharpe"]), _fmt_pct(m_rl_ts["max_dd"]), "—"],
        ["OOS",  "Rule", _fmt_num(m_rb_ts["final_equity"]), _fmt_pct(m_rb_ts["cagr"]), _fmt_num(m_rb_ts["sharpe"]), _fmt_pct(m_rb_ts["max_dd"]), _fmt_pct(bh_ts)],
    ]
    headers = ["Slice","Policy","Final $","CAGR","Sharpe","MaxDD","Buy&Hold % (vs $100)"]
    widths = [6,7,12,8,8,9,20]
    line = " | ".join(h.ljust(w) for h,w in zip(headers, widths))
    bar  = "-+-".join("-"*w for w in widths)
    print(f"\n{sym} — RL vs Rule (Train & OOS)")
    print(line); print(bar)
    for r in rows:
        print(" | ".join(str(v).ljust(w) for v,w in zip(r, widths)))
    print()

# ============ Rule baseline wrappers ============
def _safe_run_days_window_for_symbol(symbol, daily, window_days):
    try:
        res = bt.run_days_window_for_symbol(symbol, daily, f"{window_days}d", window_days)
    except Exception as e:
        raise
    summ, signals, bias_series, equity_df = _unpack_run_result(res)
    if equity_df is None:
        raise ValueError(f"{symbol}: could not find equity curve in backtester result.")
    return equity_df, (summ or {})

def _safe_run_date_window_for_symbol(symbol, daily, name, start_str, end_str):
    try:
        res = bt.run_date_window_for_symbol(symbol, daily, name, start_str, end_str)
    except Exception as e:
        raise
    summ, signals, bias_series, equity_df = _unpack_run_result(res)
    if equity_df is None:
        raise ValueError(f"{symbol} {name}: could not find equity curve in backtester result.")
    return equity_df, (summ or {})

def run_rule_baseline(symbol: str, path: str, window_days=WINDOW_DAYS):
    daily = bt.load_30s_to_daily(Path(path))
    daily = ensure_backtester_compat(daily)
    daily = bt.add_smas(daily)
    daily = bt.add_labels_and_vol(daily)
    daily = bt.add_guardrails_and_filters(daily)
    need = ["SMA_1Y","SMA_1M","SMA_1W","SMA_1D", bt.PRICE_COL,
            "y","vol_21","adtv_21","ret_1","atr14_pct","block_long_mr","bear_state"]
    daily = daily.dropna(subset=need).reset_index(drop=True)
    if len(daily) <= window_days + 60:
        raise ValueError(f"{symbol}: insufficient history for {window_days}d")
    equity_df, summ = _safe_run_days_window_for_symbol(symbol, daily, window_days)
    return equity_df, summ

def run_rule_baseline_by_idx(symbol: str, daily: pd.DataFrame, i0: int, iN: int, label: str):
    start_str = str(pd.to_datetime(daily.loc[i0, "date"]).date())
    end_str   = str(pd.to_datetime(daily.loc[iN, "date"]).date())
    equity_df, summ = _safe_run_date_window_for_symbol(symbol, daily, label, start_str, end_str)
    return equity_df, summ

# =========================
# Pooled momentum scale
# =========================
def linear_scale(x: float, lo: float, hi: float) -> float:
    """x in [0,1] -> [lo,hi]"""
    return (hi - lo) * float(np.clip(x, 0.0, 1.0)) + lo

# =========================
# CLI actions
# =========================
def build_envs_one_year(alpaca_update=False, since=None):
    envs: List[TradingEnv] = []
    for sym in DATA_SOURCES.keys():
        try:
            daily = get_daily_df(sym, alpaca_update=alpaca_update, since=since)
            assert_backtester_ready(daily)
            if len(daily) <= WINDOW_DAYS + 60:
                print(f"skip {sym}: insufficient history for {WINDOW_DAYS}d"); continue
            i0 = len(daily) - WINDOW_DAYS
            iN = len(daily) - 1
            weights = {"SMA_1Y":0.50,"SMA_1M":0.30,"SMA_1W":0.15,"SMA_1D":0.05}
            pre = daily.iloc[:i0]
            if len(pre) >= bt.TRADING_DAYS:
                yoy = float(np.clip(pre[bt.PRICE_COL].iloc[-1] / pre[bt.PRICE_COL].iloc[-bt.TRADING_DAYS] - 1.0, -0.5, 0.5))
            else:
                yoy = 0.05
            env = TradingEnv(daily, i0, iN, weights, yoy, True, True, True)
            env.label = sym
            envs.append(env)
            print(f"env ready: {sym} window={WINDOW_DAYS}d, rows={len(daily)}")
        except Exception as e:
            print(f"skip {sym}: {e}")
    return envs

#####def the actions

def act_train_from_knobs(args):
    """
    Train per-symbol models using knobs selected by wl_analyze_robust.py.
    Expects a CSV like .\out\per_symbol_knobs.csv with columns:
      symbol, lambda_neg, lambda_dd, reward_clip, regime_penalty, high_atr_q, turnover_penalty
    """
    import math
    import numpy as np
    import pandas as pd
    from pathlib import Path

    knobs_path = Path(getattr(args, "knobs_csv", r".\out\per_symbol_knobs.csv"))
    if not knobs_path.exists():
        raise SystemExit(f"Knobs CSV not found: {knobs_path}")

    df = pd.read_csv(knobs_path)
    if getattr(args, "symbols", None):
        want = {s.strip().upper() for s in str(args.symbols).split(",") if s.strip()}
        df = df[df["symbol"].str.upper().isin(want)].copy()

    if df.empty:
        print("[knobs] Nothing to train (empty selection).")
        return

    models_dir = Path(getattr(args, "models_dir", "models")); models_dir.mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"

    for _, r in df.iterrows():
        sym = str(r["symbol"]).upper()
        try:
            daily = get_daily_df(sym, alpaca_update=args.alpaca_update, since=args.since)
            assert_backtester_ready(daily)
            N = len(daily)
            if N <= WINDOW_DAYS + 60:
                print(f"[knobs] skip {sym}: insufficient history"); continue

            i0 = N - WINDOW_DAYS
            iN = N - 1

            pre = daily.iloc[:i0]
            if len(pre) >= bt.TRADING_DAYS:
                yoy = float(np.clip(pre[bt.PRICE_COL].iloc[-1] / pre[bt.PRICE_COL].iloc[-bt.TRADING_DAYS] - 1.0, -0.5, 0.5))
            else:
                yoy = 0.05

            weights = {"SMA_1Y":0.50,"SMA_1M":0.30,"SMA_1W":0.15,"SMA_1D":0.05}
            kw = dict(
                lambda_neg=float(r.get("lambda_neg", 0.5)),
                lambda_dd=float(r.get("lambda_dd", 0.0)),
                reward_clip=float(r.get("reward_clip", 0.03)),
                regime_penalty=float(r.get("regime_penalty", 0.3)),
                high_atr_q=float(r.get("high_atr_q", 0.67)),
                turnover_penalty=(None if pd.isna(r.get("turnover_penalty", np.nan)) else float(r.get("turnover_penalty")))
            )

            env = TradingEnv(daily, i0, iN, weights, yoy, True, True, True, **kw); env.label = sym

            model_path = models_dir / f"{args.model_prefix}_{sym}.pt"
            print(f"[knobs] {sym}: training {args.episodes} eps → {model_path}")
            train_dqn([env], episodes=args.episodes, gamma=0.99, lr=3e-4, batch=256,
                      eps_start=1.0, eps_end=0.05, eps_decay=0.995, target_sync=500,
                      update_after=1000, updates_per_step=1, device=device, seed=123,
                      save_path=str(model_path))

        except Exception as e:
            print(f"[knobs] {sym}: {e}")

def act_train_today_and_trade(args):
    """
    For each symbol:
      - Refresh daily data (optionally include a provisional 'today' bar)
      - Train a fresh 1y model (episodes configurable)
      - Decide action using frozen features + live minute price (at current ET time)
      - Submit IMMEDIATE (non-MOC) MARKET orders via Alpaca (IOC/DAY/FOK/GTC selectable)
    Supports optional funds_config.json to drive symbol set and per-symbol BUY budgets.
    """
    # ----- funds config (optional) -----
    use_funds = bool(getattr(args, "funds_config", None))

    # Connect trading up-front (needed for orders and, optionally, to pull account equity)
    tc, which = connect_trading_auto()
    print(f"[alpaca] trading environment: {which}")

    # Determine symbol list and per-symbol BUY budgets
    per_symbol_budget = {}
    if use_funds:
        cfg = load_funds_config(args.funds_config)
        # If --use-account-equity: get it from Alpaca, else use --equity (if provided) or raise
        equity = _account_equity_or_default(
            tc,
            explicit_equity=(0.0 if getattr(args, "use_account_equity", False) else float(getattr(args, "equity", 0.0)))
        )
        print(f"[funds] Equity basis: ${equity:,.2f} ({'account' if getattr(args,'use_account_equity',False) else 'provided'})")
        syms_from_cfg, per_symbol_budget = plan_symbol_budgets_from_funds(cfg, equity)
        # If user also passed --symbols, intersect with configâ€™s list (config leads)
        if getattr(args, "symbols", None):
            wanted = set(s.strip().upper() for s in args.symbols.split(",") if s.strip())
            syms = [s for s in syms_from_cfg if s in wanted]
        else:
            syms = syms_from_cfg
        if not syms:
            print("[funds] No symbols after intersection / planning; exiting.")
            return
        print(f"[funds] Planned {len(syms)} symbols; sample budgets: " +
              ", ".join(f"{k}=${per_symbol_budget[k]:.2f}" for k in list(per_symbol_budget.keys())[:5]))
    else:
        # Fallback: use CLI symbols or everything in DATA_SOURCES
        if getattr(args, "symbols", None):
            syms = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
        else:
            syms = list(DATA_SOURCES.keys())

    # Holdings CSV for SELL sizing (optional)
    holdings = {}
    if getattr(args, "holdings", None) and os.path.exists(args.holdings):
        try:
            hdf = pd.read_csv(args.holdings)
            for _, r in hdf.iterrows():
                s = str(r["symbol"]).upper()
                holdings[s] = float(r.get("shares", 0.0))
            print(f"[holdings] Loaded positions for {len(holdings)} symbols from {args.holdings}")
        except Exception as e:
            print(f"[holdings] Failed to read {args.holdings}: {e}")

    # Setup
    models_dir = Path("models"); models_dir.mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    orders, decisions = [], []

    now_et = datetime.now(NY_TZ)  # current ET time; weâ€™ll fetch minute bar <= now
    cutoff_dt_et = now_et

    for sym in syms:
        # 1) Data refresh & features
        daily = get_daily_df(
            sym,
            alpaca_update=getattr(args, "alpaca_update", False),
            since=getattr(args, "since", None),
            include_provisional_today=getattr(args, "provisional_today", False)
        )
        try:
            assert_backtester_ready(daily)
        except AssertionError as e:
            print(f"[{sym}] skip: {e}")
            continue

        # Build 1-year env ending at the most recent row
        N = len(daily)
        if N <= WINDOW_DAYS + 60:
            print(f"[{sym}] skip: insufficient rows for 1y window")
            continue

        i0 = N - WINDOW_DAYS
        iN = N - 1
        pre = daily.iloc[:i0]
        if len(pre) >= bt.TRADING_DAYS:
            yoy = float(np.clip(pre[bt.PRICE_COL].iloc[-1] / pre[bt.PRICE_COL].iloc[-bt.TRADING_DAYS] - 1.0, -0.5, 0.5))
        else:
            yoy = 0.05
        weights = {"SMA_1Y":0.50, "SMA_1M":0.30, "SMA_1W":0.15, "SMA_1D":0.05}

        env_train = TradingEnv(daily, i0, iN, weights, yoy, True, True, True); env_train.label = sym

        # 2) Train fresh model
        model_path = models_dir / f"{getattr(args,'model_prefix','dqn_today')}_{sym}.pt"
        train_dqn(
            [env_train],
            episodes=int(getattr(args, "episodes", 120)),
            gamma=0.99, lr=3e-4, batch=256,
            eps_start=1.0, eps_end=0.05, eps_decay=0.995,
            target_sync=500, update_after=1000, updates_per_step=1,
            device=device, seed=123, save_path=str(model_path)
        )

        # 3) Live minute price at/just before now ET
        bar = fetch_alpaca_minute_last_before(sym, cutoff_dt_et)
        if bar is None:
            print(f"[{sym}] no live minute bar at/before {cutoff_dt_et.strftime('%H:%M')} ET; skipping.")
            continue
        px_live = float(bar["c"])

        # 4) Decision with frozen features + live price
        pol = RLPolicy(str(model_path), device=device)
        dec = decide_with_frozen_features(
            daily_df=daily, weights=weights, yoy_rate=yoy,
            policy=pol, cutoff_px=px_live, price_col=bt.PRICE_COL, apply_trend=True
        )
        side = dec["signal"]
        pos_frac = float(dec["pos_frac"])
        print(f"[decide] {sym} live_px={px_live:.2f} -> {side} (pos_frac={pos_frac:.2f}, bias={dec['bias']}, bufÃ—{dec['buf_scale']:.2f})")

        # 5) Size and place IMMEDIATE market orders
        # Choose budget: funds_config per-symbol if present, else CLI --cash-per-symbol
        fallback_budget = float(getattr(args, "cash_per_symbol", 0.0))
        cash_budget = float(per_symbol_budget.get(sym, fallback_budget)) if use_funds else fallback_budget

        qty = 0.0
        if side == "BUY" and cash_budget > 0:
            exec_px = px_live * (1.0 + bt.SLIPPAGE_PCT)
            denom   = exec_px * (1.0 + bt.FEE_PCT)
            spend   = pos_frac * cash_budget
            qty     = max(0.0, (spend - bt.FEE_FIXED) / denom) if denom > 0 else 0.0
        elif side == "SELL":
            sh = float(holdings.get(sym, 0.0))
            if sh > 0:
                qty = pos_frac * sh

        if side in ("BUY", "SELL") and qty > 0:
            if not getattr(args, "dry_run", False):
                o = place_market_order_immediate(tc, sym, side, qty, tif=str(getattr(args, "tif", "ioc")))
                if o is not None:
                    orders.append({"symbol": sym, "side": side, "qty": float(qty), "tif": str(getattr(args, "tif", "ioc"))})
            else:
                print(f"[dry-run] would submit {sym} {side} qty={qty:.4f} tif={getattr(args, 'tif', 'ioc')}")
                orders.append({"symbol": sym, "side": side, "qty": float(qty), "tif": str(getattr(args, "tif", "ioc"))})
        else:
            print(f"[orders] no order for {sym} (side={side}, qtyâ‰ˆ{qty:.4f})")

        decisions.append({
            "timestamp_et": now_et.isoformat(timespec="seconds"),
            "symbol": sym,
            "price_live": px_live,
            "cash_budget": cash_budget,
            **dec
        })

    # Output snapshot files
    if decisions:
        snap_path = Path(getattr(args, "snapshot_file", "train_trade_snapshot.csv"))
        snap_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(decisions).to_csv(snap_path, index=False)
        print(f"[out] Wrote snapshot to {snap_path.resolve()}")

    if orders:
        orders_path = Path(getattr(args, "order_file", "orders_immediate.csv"))
        orders_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(orders).to_csv(orders_path, index=False)
        print(f"[out] Wrote orders CSV to {orders_path.resolve()}")



def act_train(args):
    envs = build_envs_one_year(alpaca_update=args.alpaca_update, since=args.since)
    if not envs: raise SystemExit("No environments built.")
    kw = env_kwargs_from_args(args)
    for e in envs:
        apply_env_shaping_inplace(e, **kw)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    save_path = Path(args.model); save_path.parent.mkdir(parents=True, exist_ok=True)
    train_dqn(envs, episodes=args.episodes, gamma=0.99, lr=3e-4, batch=256,
              eps_start=1.0, eps_end=0.05, eps_decay=0.995, target_sync=500,
              update_after=1000, updates_per_step=1, device=device, seed=123,
              save_path=str(save_path))

def act_eval(args):
    envs = build_envs_one_year(alpaca_update=args.alpaca_update, since=args.since)
    if not envs: raise SystemExit("No environments built.")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    q = load_policy(args.model, device=device)
    for env in envs:
        curve = rollout_greedy(env, q)  # now contains price, signals, shares, controlled_value
        m = score_equity(curve[["date","equity"]])
        print(f"{env.label} — final=${m['final_equity']:.2f} | Sharpe={m['sharpe']:.2f} | CAGR={m['cagr']:.2%} | MaxDD={m['max_dd']:.2%}")

        # Save the two requested charts
        plot_price_vs_equity_with_markers(curve, env.label, save_dir="./out_charts")
        plot_price_vs_notional_with_markers(curve, env.label, save_dir="./out_charts")

        # (Optional: keep existing equity-only PNG)
        fig, ax = plt.subplots(figsize=(10,5))
        ax.plot(pd.to_datetime(curve["date"]), curve["equity"], label=f"RL ({env.label})")
        ax.set_title(f"RL policy equity (greedy) — {env.label} — 1y")
        ax.set_ylabel("Equity ($)"); ax.legend(); fig.tight_layout()
        out = Path(f"rl_equity_{env.label}_1y.png"); fig.savefig(out, dpi=150); plt.close(fig)
        print(f"Saved {out.resolve()}")

def act_compare(args):
    envs = build_envs_one_year(alpaca_update=args.alpaca_update, since=args.since)
    if not envs: raise SystemExit("No environments built.")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    q = load_policy(args.model, device=device)
    for env in envs:
        sym = env.label
        curve_rl = rollout_greedy(env, q)   # richer curve
        m_rl = score_equity(curve_rl[["date","equity"]])

        daily = get_daily_df(sym, alpaca_update=args.alpaca_update, since=args.since)
        eq_rule, summ = _safe_run_days_window_for_symbol(sym, daily, WINDOW_DAYS)
        m_rb = score_equity(eq_rule)

        bh_pct = _bh_pct_vs_100(summ)
        print(f"\n{sym} — 1y window")
        print(f" RL   final=${m_rl['final_equity']:.2f}  Sharpe={m_rl['sharpe']:.2f}  CAGR={m_rl['cagr']:.2%}  MaxDD={m_rl['max_dd']:.2%}")
        print(f" Rule final=${m_rb['final_equity']:.2f}  Sharpe={m_rb['sharpe']:.2f}  CAGR={m_rb['cagr']:.2%}  MaxDD={m_rb['max_dd']:.2%}  BH% (vs $100)={bh_pct:.2%}")

        # Existing compare chart
        fig, ax = plt.subplots(figsize=(10,5))
        ax.plot(pd.to_datetime(eq_rule["date"]), eq_rule["equity"], label=f"Rule ({sym})")
        ax.plot(pd.to_datetime(curve_rl["date"]), curve_rl["equity"], label=f"RL ({sym})")
        ax.set_title(f"{sym} — 1y: Rule vs RL")
        ax.set_ylabel("Equity ($)"); ax.legend(); fig.tight_layout()
        out = Path(f"compare_{sym}_1y.png"); fig.savefig(out, dpi=150); plt.close(fig)
        print(f"Saved {out.resolve()}")

        # NEW: save the two marker charts for RL
        plot_price_vs_equity_with_markers(curve_rl, sym, save_dir="./out_charts")
        plot_price_vs_notional_with_markers(curve_rl, sym, save_dir="./out_charts")

def act_export_actions(args):
    """
    Export a greedy action log for a symbol over the last 1y window (ending at the latest bar).
    Writes to ./out/actions_<SYMBOL>.csv
    """
    sym = str(args.symbol).upper()
    d = get_daily_df(sym, alpaca_update=args.alpaca_update, since=args.since)
    assert_backtester_ready(d)

    # Build a 1y window env ending at last row
    N = len(d)
    i0 = max(0, N - WINDOW_DAYS)
    iN = N - 1

    # YoY drift from pre-window
    pre = d.iloc[:i0]
    if len(pre) >= bt.TRADING_DAYS:
        yoy = float(np.clip(pre[bt.PRICE_COL].iloc[-1] / pre[bt.PRICE_COL].iloc[-bt.TRADING_DAYS] - 1.0, -0.5, 0.5))
    else:
        yoy = 0.05

    weights = {"SMA_1Y":0.50, "SMA_1M":0.30, "SMA_1W":0.15, "SMA_1D":0.05}
    try:
        kw = env_kwargs_from_args(args)   # reward-shaping knobs if wired
    except NameError:
        kw = {}

    env = TradingEnv(d, i0, iN, weights, yoy, True, True, True, **kw); env.label = sym

    # Load policy
    device = "cuda" if torch.cuda.is_available() else "cpu"
    policy = load_policy(args.model, device=device)

    # Iterate each bar in window and log greedy decision details
    rows = []
    for t in range(env.i0, env.iN + 1):
        row = env.d.loc[t]
        # observation for greedy choice uses base buffer=1.0
        mid_base, buf_base = env._bands(t, base_buf_scale=1.0)
        obs = make_observation(row, mid_base, buf_base, env.yoy_rate)

        with torch.no_grad():
            a = _q_argmax_device_safe(policy, obs)

        b_idx, f_idx, p_idx = decode_action(a)
        bias = BIAS_CHOICES[b_idx]; buf_scale = BUF_SCALES[f_idx]; pos_frac = POS_FRACS[p_idx]

        # decision thresholds for the chosen buffer scale
        mid_s, buf_s = env._bands(t, base_buf_scale=buf_scale)
        upper = mid_s * (1.0 + buf_s); lower = mid_s * (1.0 - buf_s)

        px = float(row[bt.PRICE_COL])
        pre_sig = env._candidate_signal(t, bias, upper, lower)
        sig = env._apply_guards(t, bias, pre_sig)
        side = {1: "BUY", 0: "SELL", -1: "HOLD"}[sig]

        # date string
        try:
            dstr = str(pd.to_datetime(row["date"]).date())
        except Exception:
            dstr = str(t)

        rows.append({
            "symbol": env.label, "date": dstr, "price": px,
            "action_idx": int(a), "bias_idx": int(b_idx), "buf_idx": int(f_idx), "pos_idx": int(p_idx),
            "bias": bias, "buf_scale": float(buf_scale), "pos_frac": float(pos_frac),
            "mid": float(mid_s), "upper": float(upper), "lower": float(lower),
            "pre_sig": int(pre_sig), "sig": int(sig), "side": side,
        })

    df = pd.DataFrame(rows)
    out = Path("out") / f"actions_{sym}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"Wrote {out.resolve()}")


def act_infer(args):
    import pandas as pd, numpy as np, torch
    from datetime import datetime, timezone

    if getattr(args, "debug", False):
        print("[infer] start")

    # Build enriched daily with optional provisional today bar
    d = get_daily_df(
        args.symbol,
        alpaca_update=getattr(args, "alpaca_update", False),
        since=getattr(args, "since", None),
        include_provisional_today=getattr(args, "provisional_today", False),
    )
    if getattr(args, "debug", False):
        print(f"[infer] got daily df for {args.symbol}: {0 if d is None else len(d)} rows")

    assert_backtester_ready(d)

    # 1y window ending at last row
    N = len(d)
    i0 = max(0, N - WINDOW_DAYS)
    iN = N - 1
    pre = d.iloc[:i0]

    if len(pre) >= bt.TRADING_DAYS:
        yoy = float(np.clip(
            pre[bt.PRICE_COL].iloc[-1] / max(1e-12, pre[bt.PRICE_COL].iloc[-bt.TRADING_DAYS]) - 1.0,
            -0.5, 0.5
        ))
        yoy_src = "estimated_from_pre_window"
    else:
        yoy = 0.05
        yoy_src = "fallback_5pct"

    weights = {"SMA_1Y":0.50,"SMA_1M":0.30,"SMA_1W":0.15,"SMA_1D":0.05}
    env = TradingEnv(d, i0, iN, weights, yoy, True, True, True); env.label = args.symbol

    if getattr(args, "debug", False):
        last_dt = str(pd.to_datetime(d.loc[iN, "date"]).date()) if "date" in d.columns else iN
        print(f"[infer] window {i0}->{iN} last={last_dt} yoy={yoy:.4f} ({yoy_src})")

    # Resolve which model file to load (and from where)
    model_file, model_source = resolve_model_path_for_infer(
        args, env.label, model_prefix=getattr(args, "model_prefix", None)
    )
    if getattr(args, "debug", False):
        print(f"[infer] profile={args.profile} exp_id={getattr(args,'exp_id',None)}")
        print(f"[infer] symbol={env.label.upper()}  model_source={model_source}  model_path={model_file}")

    # Load the policy
    device = "cuda" if torch.cuda.is_available() else "cpu"
    policy = load_policy(model_file, device=device)

    # Single last-bar observation
    mid, buf = env._bands(env.iN, base_buf_scale=1.0)
    row = env.d.loc[env.iN]
    obs = make_observation(row, mid, buf, env.yoy_rate)

    with torch.no_grad():
        a = _q_argmax_device_safe(policy, obs)
    b_idx, f_idx, p_idx = decode_action(a)
    bias = BIAS_CHOICES[b_idx]; buf_scale = BUF_SCALES[f_idx]; pos_frac = POS_FRACS[p_idx]
    mid_s, buf_s = env._bands(env.iN, base_buf_scale=buf_scale)
    upper = mid_s * (1.0 + buf_s); lower = mid_s * (1.0 - buf_s)
    px = float(row[bt.PRICE_COL])

    pre_sig = env._candidate_signal(env.iN, bias, upper, lower)
    sig = env._apply_guards(env.iN, bias, pre_sig)
    side = {1: "BUY", 0: "SELL", -1: "HOLD"}[sig]
    dstr = str(pd.to_datetime(row["date"]).date()) if "date" in row else str(env.iN)

    print(f"\n{env.label} — latest decision for {dstr}")
    print(f"  Price: {px:.2f}")
    print(f"  Bias: {bias}  |  Buffer scale: {buf_scale:.2f}  |  Position fraction: {pos_frac:.2f}")
    print(f"  Mid: {mid_s:.4f}  |  Upper: {upper:.4f}  |  Lower: {lower:.4f}")
    print(f"  Raw signal: {{1:'BUY',0:'SELL',-1:'HOLD'}}[{pre_sig}]  ->  After guards: {side}")

    # daily logging (one file per day)
    if getattr(args, "log_csv", None):
        # timezone-aware UTC stamp (fixes the utcnow deprecation)
        ts_utc = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        day = pd.to_datetime(row["date"]).date() if "date" in row else pd.Timestamp.now(tz="UTC").date()
        log_path = _resolve_log_target_dir(args.log_csv, prefix="infer", day=day)

        _csv_append(
            str(log_path),
            [
                "timestamp_utc","profile","exp_id",
                "symbol","date_bar","price",
                "bias","buf_scale","pos_frac",
                "pre_sig","sig","side",
                "mid","upper","lower",
                "model_source","model_path"
            ],
            {
                "timestamp_utc": ts_utc,
                "profile": args.profile,
                "exp_id": getattr(args, "exp_id", None),
                "symbol": env.label,
                "date_bar": str(day),
                "price": f"{px:.6f}",
                "bias": bias,
                "buf_scale": f"{buf_scale:.3f}",
                "pos_frac": f"{pos_frac:.3f}",
                "pre_sig": int(pre_sig),
                "sig": int(sig),
                "side": side,
                "mid": f"{mid_s:.6f}",
                "upper": f"{upper:.6f}",
                "lower": f"{lower:.6f}",
                "model_source": model_source,
                "model_path": model_file,
            }
        )
        print(f"(logged to {log_path})")



def act_walkforward(args):
    rows = []
    device = "cuda" if torch.cuda.is_available() else "cpu"
    for sym in DATA_SOURCES.keys():
        daily = get_daily_df(sym, alpaca_update=args.alpaca_update, since=args.since)
        assert_backtester_ready(daily)
        N = len(daily)
        if N <= args.train_days + args.test_days + 60:
            print(f"skip {sym}: not enough rows for walk-forward"); continue
        start = args.train_days
        while start + args.test_days < N:
            train_i0 = start - args.train_days
            train_iN = start - 1
            test_i0  = start
            test_iN  = start + args.test_days - 1

            pre = daily.iloc[:train_i0]
            if len(pre) >= bt.TRADING_DAYS:
                yoy = float(np.clip(pre[bt.PRICE_COL].iloc[-1]/pre[bt.PRICE_COL].iloc[-bt.TRADING_DAYS] - 1.0, -0.5, 0.5))
            else:
                yoy = 0.05
            weights = {"SMA_1Y":0.50,"SMA_1M":0.30,"SMA_1W":0.15,"SMA_1D":0.05}
            env_train = TradingEnv(daily, train_i0, train_iN, weights, yoy, True, True, True); env_train.label = sym
            env_test  = TradingEnv(daily, test_i0,  test_iN,  weights, yoy, True, True, True); env_test.label  = sym

            model_path = Path(args.model)
            train_dqn([env_train], episodes=args.episodes, gamma=0.99, lr=3e-4, batch=256,
                      eps_start=1.0, eps_end=0.05, eps_decay=0.995, target_sync=500,
                      update_after=args.update_after, updates_per_step=1, device=device, seed=123,
                      save_path=str(model_path))

            q = load_policy(str(model_path), device=device)
            curve = rollout_greedy(env_test, q)
            metrics = score_equity(curve)
            rows.append({"symbol": sym,
                         "train_idx": f"{train_i0}-{train_iN}",
                         "test_idx": f"{test_i0}-{test_iN}",
                         **metrics})
            print(f"[WF] {sym} {train_i0}-{train_iN} -> {test_i0}-{test_iN} | Sharpe={metrics['sharpe']:.2f} CAGR={metrics['cagr']:.2%}")
            start = test_iN + 1
    df = pd.DataFrame(rows)
    if not df.empty:
        out = Path("wf_results.csv"); df.to_csv(out, index=False); print(f"Wrote {out.resolve()}")

# --- Walk-forward leaderboard (tag-aware, experiment-isolated, robust metrics) ---
def act_walkleader(args):
    """
    Walk-forward training/testing by symbol with RL vs Rule comparison.
    - If run with --profile exp and --exp-id/--tag, artifacts are isolated under experiments/<exp-id>/.
    - If args.detail/args.summary are empty, they are defaulted to experiments/<exp-id>/logs/out/.
    - Drops a small manifest in args.paths["manifests"] for reproducibility.
    """
    import math, json, time
    from pathlib import Path
    import pandas as pd
    import numpy as np
    import torch

    # ----------------------------
    # Normalize outputs into exp
    # ----------------------------
    tag = str(getattr(args, "tag", "")).strip()
    exp_id = getattr(args, "exp_id", tag or "untagged")

    # Prefer placing CSVs into the experiment's logs/out unless user provided explicit paths
    outdir = args.paths["logs_dir"] / "out"
    outdir.mkdir(parents=True, exist_ok=True)
    if not getattr(args, "detail", None) or str(args.detail).strip() == "":
        args.detail = str(outdir / f"wl_{exp_id}.csv")
    if not getattr(args, "summary", None) or str(args.summary).strip() == "":
        args.summary = str(outdir / f"ws_{exp_id}.csv")

    # ----------------------------
    # Symbols
    # ----------------------------
    if getattr(args, "symbols", None):
        symbols = [s.strip().upper() for s in str(args.symbols).split(",") if s.strip()]
    else:
        symbols = list(DATA_SOURCES.keys())

    step_days = int(args.step_days) if args.step_days is not None else int(args.test_days)
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Temporary model path (kept inside the current profile folder)
    tmp_root = args.paths["models_dir"] / "_tmp"
    tmp_root.mkdir(parents=True, exist_ok=True)
    tmp_model = tmp_root / "dqn_wl_tmp.pt"

    # Fallbacks for bt constants if not imported
    try:
        TRD = bt.TRADING_DAYS
        PXC = bt.PRICE_COL
        STK = bt.START_STOCK
        CSC = bt.START_CASH
    except Exception:
        TRD = 252
        PXC = "close"
        STK = 1.0
        CSC = 0.0

    # ----------------------------
    # Metrics coercion (robust)
    # ----------------------------
    def _coerce_metrics_local(curve, m):
        import numpy as _np
        if not isinstance(m, dict):
            m = {}
        if "maxdd" not in m:
            for alt in ("max_dd", "maxDrawdown", "max_drawdown", "mdd"):
                if alt in m:
                    m["maxdd"] = m[alt]
                    break

        def _ok(v):
            try:
                return (v is not None) and _np.isfinite(float(v))
            except Exception:
                return False

        need = ("cagr", "sharpe", "maxdd", "calmar")
        have_all = all(_ok(m.get(k)) for k in need)
        if not have_all:
            try:
                # accept pd.Series/np.ndarray/list
                if hasattr(curve, "values"):
                    s = _np.asarray(curve.values, dtype=float)
                elif isinstance(curve, (list, tuple)):
                    s = _np.asarray(curve, dtype=float)
                else:
                    s = _np.asarray(curve, dtype=float)
                if len(s) < 2 or not _np.isfinite(s).all():
                    fb = {"cagr":0.0,"sharpe":0.0,"maxdd":0.0,"calmar":0.0}
                else:
                    rets = _np.diff(s) / _np.clip(s[:-1], 1e-12, None)
                    mu = float(_np.nanmean(rets)) * 252.0
                    sd = float(_np.nanstd(rets, ddof=1))
                    sharpe = (mu / (sd + 1e-12)) if _np.isfinite(sd) and sd > 0 else 0.0
                    cagr = (float(s[-1]) / float(s[0])) ** (252.0 / max(1.0, len(s))) - 1.0 if s[0] > 0 else 0.0
                    peak = _np.maximum.accumulate(s)
                    dd = s / _np.clip(peak, 1e-12, None) - 1.0
                    maxdd = float(_np.nanmin(dd))
                    calmar = (cagr / abs(maxdd)) if maxdd < 0 else 0.0
                    if not _np.isfinite(calmar):
                        calmar = 0.0
                    fb = {"cagr":cagr,"sharpe":sharpe,"maxdd":maxdd,"calmar":calmar}
            except Exception:
                fb = {"cagr":0.0,"sharpe":0.0,"maxdd":0.0,"calmar":0.0}
            for k in need:
                if not _ok(m.get(k)):
                    m[k] = fb[k]
        return {k: float(m.get(k, 0.0)) for k in ("cagr","sharpe","maxdd","calmar")}

    def _coerce(curve, raw):
        try:
            return _coerce_metrics(curve, raw)  # prefer project-wide helper if present
        except NameError:
            return _coerce_metrics_local(curve, raw)

    def _get4(m):
        cagr   = float(m.get("cagr",   m.get("CAGR",   0.0)))
        sharpe = float(m.get("sharpe", m.get("Sharpe", 0.0)))
        maxdd  = float(m.get("maxdd",  m.get("max_dd", m.get("mdd", 0.0))))
        calmar = float(m.get("calmar", m.get("Calmar", 0.0)))
        return cagr, sharpe, maxdd, calmar

    # ----------------------------
    # Loop
    # ----------------------------
    detail_rows = []
    for sym in symbols:
        daily = get_daily_df(sym, alpaca_update=args.alpaca_update, since=args.since)
        assert_backtester_ready(daily)
        N = len(daily)
        need = args.train_days + args.test_days + 60
        if N <= need:
            print(f"skip {sym}: not enough rows for walkleader (have {N}, need > {need})")
            continue

        start = args.train_days
        roll_id = 0

        while start + args.test_days <= N:
            train_i0 = start - args.train_days
            train_iN = start - 1
            test_i0  = start
            test_iN  = min(N - 1, start + args.test_days - 1)

            # YoY drift from pre-training period
            pre = daily.iloc[:max(0, train_i0)]
            if len(pre) >= TRD:
                yoy = float(np.clip(pre[PXC].iloc[-1] / max(1e-12, pre[PXC].iloc[-TRD]) - 1.0, -0.5, 0.5))
            else:
                yoy = 0.05

            weights = {"SMA_1Y":0.50, "SMA_1M":0.30, "SMA_1W":0.15, "SMA_1D":0.05}
            kw = env_kwargs_from_args(args)

            env_train = TradingEnv(daily, train_i0, train_iN, weights, yoy, True, True, True, **kw); env_train.label = sym
            env_test  = TradingEnv(daily, test_i0,  test_iN,  weights, yoy, True, True, True, **kw);  env_test.label  = sym

            # Train policy per roll
            train_dqn(
                [env_train],
                episodes=args.episodes, gamma=0.99, lr=3e-4, batch=256,
                eps_start=1.0, eps_end=0.05, eps_decay=0.995, target_sync=500,
                update_after=800, updates_per_step=1, device=device, seed=123,
                save_path=str(tmp_model)
            )
            q = load_policy(str(tmp_model), device=device)

            # --- RL metrics ---
            rl_curve = rollout_greedy(env_test, q)
            try:
                rl_raw = score_equity(rl_curve)
            except Exception:
                rl_raw = {}
            rl_series = rl_curve["equity"] if isinstance(rl_curve, pd.DataFrame) and "equity" in rl_curve else rl_curve
            rl_metrics = _coerce(rl_series, rl_raw)
            rl_cagr, rl_sharpe, rl_maxdd, rl_calmar = _get4(rl_metrics)

            # --- Rule baseline (helper if available; else Buy&Hold) ---
            rule_curve = None
            for cand in ("rollout_rule_equity", "rule_rollout_equity", "run_rule_equity"):
                fn = globals().get(cand, None)
                if callable(fn):
                    try:
                        rule_curve = fn(env_test)
                        break
                    except Exception:
                        rule_curve = None
            if rule_curve is None:
                px0 = float(daily.loc[test_i0, PXC])
                shares = STK / max(px0, 1e-12)
                cash = float(CSC)
                eq = [cash + shares * float(daily.loc[i, PXC]) for i in range(test_i0, test_iN + 1)]
                if "date" in daily.columns:
                    idx = pd.to_datetime(daily.loc[test_i0:test_iN, "date"].values)
                    rule_curve = pd.Series(eq, index=idx)
                else:
                    rule_curve = pd.Series(eq)

            try:
                rule_raw = score_equity(rule_curve if hasattr(rule_curve, "index") else pd.Series(rule_curve))
            except Exception:
                rule_raw = {}
            rule_series = rule_curve["equity"] if isinstance(rule_curve, pd.DataFrame) and "equity" in rule_curve else rule_curve
            rule_metrics = _coerce(rule_series, rule_raw)
            rule_cagr, rule_sharpe, rule_maxdd, rule_calmar = _get4(rule_metrics)

            # Normalize drawdown sign if both positive
            if rl_maxdd > 0 and rule_maxdd > 0:
                rl_maxdd   = -abs(rl_maxdd)
                rule_maxdd = -abs(rule_maxdd)

            # Uplifts
            upl_cagr       = rl_cagr   - rule_cagr
            upl_sharpe     = rl_sharpe - rule_sharpe
            upl_calmar     = rl_calmar - rule_calmar
            upl_dd_improve = rule_maxdd - rl_maxdd  # less negative is better

            def _d(i):
                try:
                    return str(pd.to_datetime(daily.loc[i, "date"]).date())
                except Exception:
                    return str(i)

            roll_id += 1
            # Echo the shaping/guard knobs used (if present in kw)
            def _g(name, default=None):
                v = kw.get(name, default)
                try:
                    return float(v) if v is not None else None
                except Exception:
                    return None

            detail_rows.append({
                "symbol": sym,
                "tag": tag,
                "roll_id": roll_id,
                "train_start": _d(train_i0),
                "train_end":   _d(train_iN),
                "test_start":  _d(test_i0),
                "test_end":    _d(test_iN),
                "bars_train": int(train_iN - train_i0 + 1),
                "bars_test":  int(test_iN - test_i0 + 1),
                "rl_cagr": float(rl_cagr),
                "rl_sharpe": float(rl_sharpe),
                "rl_maxdd": float(rl_maxdd),
                "rl_calmar": float(rl_calmar),
                "rule_cagr": float(rule_cagr),
                "rule_sharpe": float(rule_sharpe),
                "rule_maxdd": float(rule_maxdd),
                "rule_calmar": float(rule_calmar),
                "upl_cagr": float(upl_cagr),
                "upl_sharpe": float(upl_sharpe),
                "upl_calmar": float(upl_calmar),
                "upl_dd_improve": float(upl_dd_improve),
                # knobs snapshot
                "p_lambda_neg": _g("lambda_neg"),
                "p_lambda_dd": _g("lambda_dd"),
                "p_reward_clip": _g("reward_clip"),
                "p_turnover_penalty": _g("turnover_penalty"),
                "p_regime_penalty": _g("regime_penalty"),
                "p_high_atr_q": _g("high_atr_q"),
            })

            print(f"[WL] {sym} {train_i0}-{train_iN} -> {test_i0}-{test_iN} | "
                  f"RL S={rl_sharpe:.2f} CAGR={rl_cagr:.2%}  "
                  f"| Rule S={rule_sharpe:.2f} CAGR={rule_cagr:.2%}  "
                  f"| Uplift dCalmar={upl_calmar:+.2f} ddΔ={upl_dd_improve:+.3f}")

            start += step_days

    # ----------------------------
    # Write outputs
    # ----------------------------
    df = pd.DataFrame(detail_rows)
    if df.empty:
        print("No rows produced. Check data availability / window sizes.")
        return

    Path(args.detail).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.detail, index=False)

    agg = (df.groupby(["symbol","tag"], as_index=False)
             .agg({
                 "bars_train":"sum","bars_test":"sum",
                 "rl_cagr":"mean","rl_sharpe":"mean","rl_maxdd":"mean","rl_calmar":"mean",
                 "rule_cagr":"mean","rule_sharpe":"mean","rule_maxdd":"mean","rule_calmar":"mean",
                 "upl_cagr":"mean","upl_sharpe":"mean","upl_calmar":"mean","upl_dd_improve":"mean",
             }))

    Path(args.summary).parent.mkdir(parents=True, exist_ok=True)
    agg.to_csv(args.summary, index=False)

    print(f"Wrote detail -> {Path(args.detail).resolve()}")
    print(f"Wrote summary -> {Path(args.summary).resolve()}")

    # ----------------------------
    # Small manifest for reproducibility
    # ----------------------------
    mani = {
        "tag": tag,
        "profile": args.profile,
        "exp_id": exp_id,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "detail_csv": str(args.detail),
        "summary_csv": str(args.summary),
        "train_days": int(args.train_days),
        "test_days": int(args.test_days),
        "step_days": int(args.step_days) if args.step_days is not None else int(args.test_days),
        "episodes": int(args.episodes),
        "symbols": symbols,
        "kw_defaults": {  # snapshot of top-level shaping defaults used
            k: (float(v) if v is not None else None)
            for k, v in env_kwargs_from_args(args).items()
            if k in ("lambda_neg","lambda_dd","reward_clip","turnover_penalty","regime_penalty","high_atr_q")
        },
    }
    (args.paths["manifests"] / f"walkleader_{exp_id}.json").write_text(json.dumps(mani, indent=2))


# --- Fallback equity scorer (if project score_equity is missing) --------------
def _score_equity_fallback(equity_curve):
    try:
        s = np.asarray(list(equity_curve), dtype=float)
        if len(s) < 2 or not np.isfinite(s).all():
            return {"cagr": 0.0, "sharpe": 0.0, "maxdd": 0.0, "calmar": 0.0}
        rets = np.diff(s) / np.clip(s[:-1], 1e-12, None)
        mu = float(np.nanmean(rets)) * np.sqrt(252.0)
        sd = float(np.nanstd(rets, ddof=1))
        sharpe = (mu / (sd + 1e-12)) if np.isfinite(sd) and sd > 0 else 0.0
        cagr = (float(s[-1]) / float(s[0])) ** (252.0 / max(1.0, len(s))) - 1.0 if s[0] > 0 else 0.0
        peak = np.maximum.accumulate(s)
        dd = s / np.clip(peak, 1e-12, None) - 1.0
        maxdd = float(np.nanmin(dd))
        calmar = (cagr / abs(maxdd)) if maxdd < 0 else float("inf")
        if not np.isfinite(calmar): calmar = 0.0
        return {"cagr": float(cagr), "sharpe": float(sharpe), "maxdd": float(maxdd), "calmar": float(calmar)}
    except Exception:
        return {"cagr": 0.0, "sharpe": 0.0, "maxdd": 0.0, "calmar": 0.0}


def act_splityear(args):
    # --- optional per-symbol knobs loader (scoped to this function) ---
    def _load_knobs():
        from pathlib import Path
        import pandas as _pd
        p = Path("out/per_symbol_knobs.csv")
        if not p.exists():
            return {}
        df = _pd.read_csv(p)
        needed = {"symbol","lambda_neg","lambda_dd","reward_clip","regime_penalty","high_atr_q","turnover_penalty"}
        missing = needed - set(c.lower() for c in df.columns)
        # tolerant to slight column-case differences
        df.columns = [c.lower() for c in df.columns]
        if {"symbol"} - set(df.columns):
            return {}
        # coerce numeric if present
        for c in ["lambda_neg","lambda_dd","reward_clip","regime_penalty","high_atr_q","turnover_penalty"]:
            if c in df.columns:
                df[c] = _pd.to_numeric(df[c], errors="coerce")
        out = {}
        for _, r in df.iterrows():
            k = r["symbol"].strip().upper()
            out[k] = {k2: r.get(k2, None) for k2 in ["lambda_neg","lambda_dd","reward_clip","regime_penalty","high_atr_q","turnover_penalty"]}
        return out

    per_knobs = _load_knobs()
    base_env_kwargs = env_kwargs_from_args(args)

    oos_days = int(args.oos_days)
    year_days = WINDOW_DAYS
    train_days = year_days - oos_days
    assert train_days > 60, "Need enough train days (>60)."

    device = "cuda" if torch.cuda.is_available() else "cpu"
    rows = []
    models_dir = Path("models"); models_dir.mkdir(parents=True, exist_ok=True)

    # If future CLI adds --symbols, respect it; otherwise use DATA_SOURCES
    chosen_syms = []
    if hasattr(args, "symbols") and args.symbols:
        chosen_syms = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    if not chosen_syms:
        chosen_syms = list(DATA_SOURCES.keys())

    for sym in chosen_syms:
        if sym not in DATA_SOURCES:
            print(f"skip {sym}: not in DATA_SOURCES"); continue

        daily = get_daily_df(sym, alpaca_update=args.alpaca_update, since=args.since)
        assert_backtester_ready(daily)
        N = len(daily)
        if N <= year_days + 60:
            print(f"skip {sym}: not enough rows for 1y split"); continue

        year_i0 = N - year_days
        year_iN = N - 1
        train_i0 = year_i0
        train_iN = year_iN - oos_days
        oos_i0   = train_iN + 1
        oos_iN   = year_iN

        pre = daily.iloc[:train_i0]
        if len(pre) >= bt.TRADING_DAYS:
            yoy = float(np.clip(pre[bt.PRICE_COL].iloc[-1] / pre[bt.PRICE_COL].iloc[-bt.TRADING_DAYS] - 1.0, -0.5, 0.5))
        else:
            yoy = 0.05

        weights = {"SMA_1Y":0.50,"SMA_1M":0.30,"SMA_1W":0.15,"SMA_1D":0.05}
        env_train = TradingEnv(daily, train_i0, train_iN, weights, yoy, True, True, True); env_train.label = sym
        env_oos   = TradingEnv(daily, oos_i0,   oos_iN,   weights, yoy, True, True, True);   env_oos.label   = sym

        # -------- apply reward-shaping (CLI defaults overridden by per-symbol knobs if available) --------
        sym_over = per_knobs.get(sym, {})
        env_kw   = {**base_env_kwargs, **{k:v for k,v in sym_over.items() if v is not None}}
        apply_env_shaping_inplace(env_train, **env_kw)
        apply_env_shaping_inplace(env_oos,   **env_kw)

        print(f"{sym}: train idx [{train_i0}:{train_iN}]  OOS idx [{oos_i0}:{oos_iN}]  "
              f"| knobs λ-={env_kw.get('lambda_neg')} λdd={env_kw.get('lambda_dd')} "
              f"clip={env_kw.get('reward_clip')} reg={env_kw.get('regime_penalty')} "
              f"atrQ={env_kw.get('high_atr_q')} turn={env_kw.get('turnover_penalty')}")

        model_path = models_dir / f"{args.model_prefix}_{sym}.pt"
        train_dqn([env_train], episodes=args.episodes, gamma=0.99, lr=3e-4, batch=256,
                  eps_start=1.0, eps_end=0.05, eps_decay=0.995, target_sync=500,
                  update_after=1000, updates_per_step=1, device=device, seed=123,
                  save_path=str(model_path))

        q = load_policy(str(model_path), device=device)
        curve_rl_train = rollout_greedy(env_train, q)
        curve_rl_oos   = rollout_greedy(env_oos, q)

        eq_rule_train, summ_tr = run_rule_baseline_by_idx(sym, daily, train_i0, train_iN, "train")
        eq_rule_oos,   summ_ts = run_rule_baseline_by_idx(sym, daily, oos_i0,   oos_iN,   "oos")

        m_rl_tr  = score_equity(curve_rl_train); m_rl_ts  = score_equity(curve_rl_oos)
        m_rb_tr  = score_equity(eq_rule_train);  m_rb_ts  = score_equity(eq_rule_oos)

        print_side_by_side_console(sym, m_rl_tr, m_rb_tr, m_rl_ts, m_rb_ts, summ_tr, summ_ts)

        rows.append({
            "symbol": sym,
            "train_days": train_days, "oos_days": oos_days,
            "rl_train_final": m_rl_tr["final_equity"], "rl_train_sharpe": m_rl_tr["sharpe"], "rl_train_cagr": m_rl_tr["cagr"], "rl_train_maxdd": m_rl_tr["max_dd"],
            "rl_oos_final":   m_rl_ts["final_equity"], "rl_oos_sharpe":   m_rl_ts["sharpe"], "rl_oos_cagr":   m_rl_ts["cagr"], "rl_oos_maxdd":   m_rl_ts["max_dd"],
            "rule_train_final": m_rb_tr["final_equity"], "rule_train_sharpe": m_rb_tr["sharpe"], "rule_train_cagr": m_rb_tr["cagr"], "rule_train_maxdd": m_rb_tr["max_dd"],
            "rule_oos_final":   m_rb_ts["final_equity"], "rule_oos_sharpe":   m_rb_ts["sharpe"], "rule_oos_cagr":   m_rb_ts["cagr"], "rule_oos_maxdd":   m_rb_ts["max_dd"],
            "rule_train_bh_return_pct_100": _bh_pct_vs_100(summ_tr),
            "rule_oos_bh_return_pct_100":   _bh_pct_vs_100(summ_ts),
            "model_path": str(model_path),
            # record shaping actually used
            "p_lambda_neg": env_kw.get("lambda_neg"),
            "p_lambda_dd": env_kw.get("lambda_dd"),
            "p_reward_clip": env_kw.get("reward_clip"),
            "p_regime_penalty": env_kw.get("regime_penalty"),
            "p_high_atr_q": env_kw.get("high_atr_q"),
            "p_turnover_penalty": env_kw.get("turnover_penalty"),
        })

        # Save plots
        def _save_curve_png(curve, label):
            fig, ax = plt.subplots(figsize=(10,5))
            ax.plot(pd.to_datetime(curve["date"]), curve["equity"], label=label)
            ax.set_title(f"{sym} — {label}"); ax.set_ylabel("Equity ($)"); ax.legend(); fig.tight_layout()
            out = Path(f"{label.lower().replace(' ','_')}_{sym}.png")
            fig.savefig(out, dpi=150); plt.close(fig); print(f"Saved {out.resolve()}")

        _save_curve_png(curve_rl_train, "RL Train (greedy)")
        _save_curve_png(curve_rl_oos,   "RL OOS (greedy)")

        def _save_compare(curve_rl, curve_rule, label):
            fig, ax = plt.subplots(figsize=(10,5))
            ax.plot(pd.to_datetime(curve_rule["date"]), curve_rule["equity"], label="Rule")
            ax.plot(pd.to_datetime(curve_rl["date"]),   curve_rl["equity"],   label="RL")
            ax.set_title(f"{sym} — {label}"); ax.set_ylabel("Equity ($)"); ax.legend(); fig.tight_layout()
            out = Path(f"compare_{sym}_{label.replace(' ','_').lower()}.png")
            fig.savefig(out, dpi=150); plt.close(fig); print(f"Saved {out.resolve()}")

        _save_compare(curve_rl_train, eq_rule_train, "Train")
        _save_compare(curve_rl_oos,   eq_rule_oos,   "OOS")

    df = pd.DataFrame(rows)
    if not df.empty:
        out = Path("splityear_summary.csv")
        df.to_csv(out, index=False)
        print("\n=== SPLIT-YEAR SUMMARY ===")
        print(df.to_string(index=False))
        print(f"\nWrote {out.resolve()}")
    else:
        print("No symbols processed.")

def act_splityear_pooled(args):
    # --- optional per-symbol knobs loader (scoped) ---
    def _load_knobs():
        from pathlib import Path
        import pandas as _pd
        p = Path("out/per_symbol_knobs.csv")
        if not p.exists():
            return {}
        df = _pd.read_csv(p)
        df.columns = [c.lower() for c in df.columns]
        for c in ["lambda_neg","lambda_dd","reward_clip","regime_penalty","high_atr_q","turnover_penalty"]:
            if c in df.columns:
                df[c] = _pd.to_numeric(df[c], errors="coerce")
        out = {}
        if "symbol" in df.columns:
            for _, r in df.iterrows():
                k = r["symbol"].strip().upper()
                out[k] = {k2: r.get(k2, None) for k2 in ["lambda_neg","lambda_dd","reward_clip","regime_penalty","high_atr_q","turnover_penalty"]}
        return out

    per_knobs = _load_knobs()
    base_env_kwargs = env_kwargs_from_args(args)

    if args.symbols:
        chosen = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    else:
        chosen = list(DATA_SOURCES.keys())

    per = {}
    for sym in chosen:
        if sym not in DATA_SOURCES:
            print(f"skip {sym}: not in DATA_SOURCES"); continue
        daily = get_daily_df(sym, alpaca_update=args.alpaca_update, since=args.since)
        assert_backtester_ready(daily)
        if len(daily) <= WINDOW_DAYS + 60:
            print(f"skip {sym}: insufficient history"); continue
        N  = len(daily)
        y0 = N - WINDOW_DAYS; yN = N - 1
        trN = yN - args.oos_days
        if trN <= y0: print(f"skip {sym}: OOS too large"); continue
        o0 = trN + 1; oN = yN
        pre = daily.iloc[:y0]
        if len(pre) >= bt.TRADING_DAYS:
            yoy = float(np.clip(pre[bt.PRICE_COL].iloc[-1] / pre[bt.PRICE_COL].iloc[-bt.TRADING_DAYS] - 1.0, -0.5, 0.5))
        else:
            yoy = 0.05
        weights = {"SMA_1Y":0.50,"SMA_1M":0.30,"SMA_1W":0.15,"SMA_1D":0.05}
        env_train = TradingEnv(daily, y0, trN, weights, yoy, True, True, True); env_train.label = sym

        # apply shaping: CLI defaults overridden by per-symbol knobs
        sym_over = per_knobs.get(sym, {})
        env_kw   = {**base_env_kwargs, **{k:v for k,v in sym_over.items() if v is not None}}
        apply_env_shaping_inplace(env_train, **env_kw)

        print(f"{sym}: pooled train idx [{y0}:{trN}]  OOS [{o0}:{oN}]  "
              f"| knobs λ-={env_kw.get('lambda_neg')} λdd={env_kw.get('lambda_dd')} "
              f"clip={env_kw.get('reward_clip')} reg={env_kw.get('regime_penalty')} "
              f"atrQ={env_kw.get('high_atr_q')} turn={env_kw.get('turnover_penalty')}")

        per[sym] = dict(d=daily, y0=y0, yN=yN, trN=trN, o0=o0, oN=oN, yoy=yoy, weights=weights, env_train=env_train)

    if not per:
        raise SystemExit("No symbols available for pooled run.")

    envs = [per[sym]["env_train"] for sym in per.keys()]
    device = "cuda" if torch.cuda.is_available() else "cpu"
    models_dir = Path("models"); models_dir.mkdir(parents=True, exist_ok=True)
    model_path = models_dir / f"{args.model_prefix}_POOLED.pt"
    train_dqn(envs, episodes=args.episodes, gamma=0.99, lr=3e-4, batch=256,
              eps_start=1.0, eps_end=0.05, eps_decay=0.995, target_sync=500,
              update_after=1000, updates_per_step=1, device=device, seed=123,
              save_path=str(model_path))
    q = load_policy(str(model_path), device=device)

    # Build union OOS date index
    sym_dates = {}
    for sym, info in per.items():
        d = info["d"].iloc[info["o0"]:info["oN"]+1].copy()
        d["date"] = pd.to_datetime(d["date"])
        d = d.set_index("date")
        sym_dates[sym] = d
    all_idx = None
    for df in sym_dates.values():
        idx = pd.DatetimeIndex(df.index)
        all_idx = idx if all_idx is None else all_idx.union(idx)
    if all_idx is None or len(all_idx) == 0:
        raise SystemExit("No dates found across symbols for OOS.")
    all_dates = list(all_idx.sort_values())

    # Initial holdings
    cash = float(args.start_cash_extra)
    shares = {sym: 0.0 for sym in per.keys()}
    for sym, df in sym_dates.items():
        if df.empty: continue
        first_date = df.index[0]
        px = float(df.loc[first_date, bt.PRICE_COL])
        invest = float(args.invest_per_symbol)
        exec_px = px * (1.0 + bt.SLIPPAGE_PCT)
        qty = max(0.0, (invest - bt.FEE_FIXED) / (exec_px * (1.0 + bt.FEE_PCT)))
        cost = qty * exec_px
        fees = cost * bt.FEE_PCT + bt.FEE_FIXED
        cash -= (cost + fees)
        shares[sym] += qty

    def mom_rank_for_date(date_):
        vals = []
        for sym, df in sym_dates.items():
            if date_ not in df.index: continue
            i = df.index.get_loc(date_)
            if isinstance(i, slice): continue
            start_i = i - args.mom_window
            if start_i < 0: continue
            px_now = float(df.iloc[i][bt.PRICE_COL])
            px_prev = float(df.iloc[start_i][bt.PRICE_COL])
            if px_prev > 0:
                vals.append((sym, (px_now / px_prev) - 1.0))
        if not vals: return {}
        vals.sort(key=lambda x: x[1])  # ascending
        ranks = {sym: rank for rank, (sym, _) in enumerate(vals)}
        n = len(vals)
        scaled = {}
        for sym, _ret in vals:
            r = ranks[sym] / max(1, n-1)
            scaled[sym] = linear_scale(r, args.mom_scale_low, args.mom_scale_high)
        return scaled

    equity_rows = []
    trades = []
    for date_ in all_dates:
        mom_scale = mom_rank_for_date(date_)
        todays = [(sym, mom_scale.get(sym, 1.0)) for sym, df in sym_dates.items() if date_ in df.index]
        todays.sort(key=lambda x: x[1], reverse=True)

        for sym, scale in todays:
            row = sym_dates[sym].loc[date_]
            base_mid = bt.composite_from_weights(row, per[sym]["weights"])
            if not np.isfinite(base_mid): base_mid = float(row[bt.PRICE_COL])

            # Use compat wrapper for trend projection (for obs & for band calc)
            mid = trend_project_compat(bt, base_mid, per[sym]["yoy"], apply_trend=True)

            vol = float(row["vol_21"])
            buf = bt.per_day_buffer(vol, 1.0, 0.010, 0.03)
            obs = make_observation(row, mid, buf, per[sym]["yoy"])

            with torch.no_grad():
                a = _q_argmax_device_safe(q, obs)
            b_idx, f_idx, p_idx = decode_action(a)
            bias = BIAS_CHOICES[b_idx]
            buf_scale = BUF_SCALES[f_idx]
            pos_frac  = POS_FRACS[p_idx] * float(scale)

            mid_s = trend_project_compat(bt, base_mid, per[sym]["yoy"], apply_trend=True)
            buf_s = bt.per_day_buffer(vol, 1.0 * buf_scale, 0.010, 0.03)
            upper = mid_s * (1.0 + buf_s); lower = mid_s * (1.0 - buf_s)
            px = float(row[bt.PRICE_COL])

            pre_sig = 1 if (bias=="trend" and px>upper) or (bias=="revert" and px<lower) else (0 if (bias=="trend" and px<lower) or (bias=="revert" and px>upper) else -1)
            if pre_sig == 1 and bool(row.get("bear_state", False)) and bias=="trend":
                sig = -1
            elif pre_sig == 1 and bool(row.get("block_long_mr", False)) and bias=="revert":
                sig = -1
            else:
                sig = pre_sig

            traded_notional = 0.0
            side = None; qty = 0.0; exec_px = None; fees = 0.0
            if sig == 1 and cash > 0:
                exec_px = px * (1.0 + bt.SLIPPAGE_PCT)
                spend   = pos_frac * cash
                denom   = exec_px * (1.0 + bt.FEE_PCT)
                qty     = max(0.0, (spend - bt.FEE_FIXED) / denom) if denom > 0 else 0.0
                cost    = qty * exec_px
                fees    = cost * bt.FEE_PCT + bt.FEE_FIXED
                total   = cost + fees
                if total > cash and exec_px*(1.0+bt.FEE_PCT) > 0:
                    qty = max(0.0, (cash - bt.FEE_FIXED) / (exec_px*(1.0+bt.FEE_PCT)))
                    cost = qty * exec_px; fees = cost*bt.FEE_PCT + bt.FEE_FIXED
                if qty > 0:
                    shares[sym] += qty; cash -= (cost + fees); side = "BUY"; traded_notional = qty * px

            elif sig == 0 and shares[sym] > 0:
                qty = pos_frac * shares[sym]
                exec_px = px * (1.0 - bt.SLIPPAGE_PCT)
                gross   = qty * exec_px
                fees    = gross * bt.FEE_PCT + bt.FEE_FIXED
                net     = max(0.0, gross - fees)
                if qty > 0:
                    shares[sym] -= qty; cash += net; side = "SELL"; traded_notional = qty * px

            if side:
                trades.append({
                    "date": date_, "symbol": sym, "side": side, "bias": bias,
                    "buf_scale": float(buf_scale), "pos_frac_scaled": float(pos_frac),
                    "exec_price": float(exec_px) if exec_px is not None else np.nan,
                    "qty": float(qty), "fees": float(fees),
                    "cash_after": float(cash), "shares_after": float(shares[sym])
                })

        eq = cash
        for sym, df in sym_dates.items():
            if date_ in df.index:
                px = float(df.loc[date_, bt.PRICE_COL])
                eq += shares[sym] * px
        equity_rows.append({"date": date_, "equity": eq, "cash": cash, **{f"sh_{s}": shares[s] for s in shares}})

    eq_df = pd.DataFrame(equity_rows).sort_values("date")
    tr_df = pd.DataFrame(trades).sort_values("date")

    eq_out = Path("pooled_equity.csv"); tr_out = Path("pooled_trades.csv")
    eq_df.to_csv(eq_out, index=False); tr_df.to_csv(tr_out, index=False)
    print(f"Wrote {eq_out.resolve()} and {tr_out.resolve()}")

    fig, ax = plt.subplots(figsize=(10,5))
    ax.plot(pd.to_datetime(eq_df["date"]), eq_df["equity"], label="RL pooled (OOS)")
    ax.set_title(f"Pooled OOS equity — {', '.join(per.keys())}")
    ax.set_ylabel("Equity ($)"); ax.legend(); fig.tight_layout()
    png = Path("pooled_equity.png"); fig.savefig(png, dpi=150); plt.close(fig)
    print(f"Saved {png.resolve()}")

    m = score_equity(eq_df)
    print(f"POOLED — final=${m['final_equity']:.2f}  Sharpe={m['sharpe']:.2f}  CAGR={m['cagr']:.2%}  MaxDD={m['max_dd']:.2%}")

# ---------- Tiny wrapper so we can call .greedy_action(obs) ----------
class RLPolicy:
    def __init__(self, model_path: str, device="cpu"):
        self.device = device
        self.q = load_policy(model_path, device=device)

    def greedy_action(self, obs_np: np.ndarray) -> int:
        with torch.no_grad():
            x = torch.tensor(obs_np, dtype=torch.float32, device=self.device).unsqueeze(0)
            return int(self.q(x).argmax(dim=1).item())

# ---------- Time helpers ----------
NY_TZ = ZoneInfo("America/New_York")
def _today_ny():
    return datetime.now(NY_TZ).date()

# ---------- Alpaca minute fetch (last bar at/just before cutoff ET) ----------
def fetch_alpaca_minute_last_before(symbol: str, cutoff_dt_et: datetime,
                                    feed="iex") -> Optional[pd.Series]:
    key = os.environ.get("ALPACA_KEY_ID")
    sec = os.environ.get("ALPACA_SECRET_KEY")
    if not key or not sec:
        print("[Alpaca] Missing ALPACA_KEY_ID/ALPACA_SECRET_KEY.")
        return None

    _print_key_fingerprint_once()  # <- add this call (helper shown below)

    day = cutoff_dt_et.date()
    t0 = datetime(day.year, day.month, day.day, 14, 30, tzinfo=NY_TZ)  # 09:30 ET
    t1 = datetime(day.year, day.month, day.day, 15, 5,  tzinfo=NY_TZ)  # 15:05 ET

    url = f"https://data.alpaca.markets/v2/stocks/{symbol}/bars"
    # NOTE: no 'adjustment' and no 'feed' param — fewer entitlement pitfalls
    params = {"timeframe": "1Min", "start": _iso_utc(t0), "end": _iso_utc(t1), "limit": 1000}
    params["feed"] = os.getenv("ALPACA_FEED", "iex")
    headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec}

    try:
        r = requests.get(url, params=params, headers=headers, timeout=20)
        r.raise_for_status()
        js = r.json()
    except requests.HTTPError as e:
        body = ""
        try: body = e.response.text
        except Exception: pass
        print(f"[Alpaca] minute fetch failed for {symbol}: {e} | {body[:400]}")
        return None
    except Exception as e:
        print(f"[Alpaca] minute fetch failed for {symbol}: {e}")
        return None

    bars = js.get("bars", [])
    if not bars:
        return None

    df = pd.DataFrame(bars)
    df["t"] = pd.to_datetime(df["t"], utc=True).dt.tz_convert(NY_TZ)
    df = df[df["t"] <= cutoff_dt_et].sort_values("t")
    return None if df.empty else df.iloc[-1]

# ---------- Freeze indicators at yesterday, inject today's 3pm price ----------
def decide_with_frozen_features(daily_df: pd.DataFrame,
                                weights: dict,
                                yoy_rate: float,
                                policy: RLPolicy,
                                cutoff_px: float,
                                price_col: str,
                                apply_trend=True) -> dict:
    d = daily_df.copy()
    feat_cols = ["SMA_1D","SMA_1W","SMA_1M","SMA_1Y",
                 "vol_21","atr14_pct","bear_state","near_52w_low","gap_crash","block_long_mr"]
    for c in feat_cols:
        if c in d.columns:
            d[c] = d[c].shift(1)

    row = d.iloc[-1].copy()
    row[price_col] = float(cutoff_px)

    base_mid = bt.composite_from_weights(row, weights)
    if not np.isfinite(base_mid):
        base_mid = float(row[price_col])
    _yoy = 0.0 if yoy_rate is None else float(yoy_rate)
    mid  = trend_project_compat(bt, base_mid, _yoy, apply_trend=apply_trend)


    vol = float(row.get("vol_21", 0.0))
    base_buf = bt.per_day_buffer(vol, 1.0, 0.010, 0.03)
    obs = make_observation(row, mid, base_buf, yoy_rate)

    a = policy.greedy_action(obs)
    b_idx, f_idx, p_idx = decode_action(a)
    bias = BIAS_CHOICES[b_idx]
    buf_scale = BUF_SCALES[f_idx]
    pos_frac  = POS_FRACS[p_idx]

    buf_s = bt.per_day_buffer(vol, 1.0 * buf_scale, 0.010, 0.03)
    upper = mid * (1.0 + buf_s)
    lower = mid * (1.0 - buf_s)
    px = float(row[price_col])

    if bias == "trend":
        pre_sig = 1 if px > upper else (0 if px < lower else -1)
    else:
        pre_sig = 0 if px > upper else (1 if px < lower else -1)

    if pre_sig == 1 and bool(row.get("bear_state", False)) and bias == "trend":
        sig = -1
    elif pre_sig == 1 and bool(row.get("block_long_mr", False)) and bias == "revert":
        sig = -1
    else:
        sig = pre_sig

    return {
        "bias": bias,
        "buf_scale": float(buf_scale),
        "pos_frac": float(pos_frac),
        "mid": float(mid),
        "upper": float(upper),
        "lower": float(lower),
        "price": float(px),
        "signal": {1:"BUY", 0:"SELL", -1:"HOLD"}[sig],
        "raw_sig": int(pre_sig),
        "sig_code": int(sig),
    }

# ---------- LIVE CLI action (3pm ET decision; outputs MOC-style CSV) ----------
def act_live(args):
    """
    Live-style run at ~3:00pm ET (or any --cutoff):
      - Ensure daily data is present (optionally refresh from Alpaca)
      - Fetch the last minute bar at/before cutoff ET
      - Freeze indicators to yesterday, inject cutoff price, query RL action
      - Size BUY using funds_config-derived budgets (if provided) or --cash-per-symbol
      - Output Market-On-Close-like orders CSV + a snapshot CSV
    """
    # ----- funds config (optional) -----
    use_funds = bool(getattr(args, "funds_config", None))
    per_symbol_budget = {}

    # If using funds config, compute budgets up-front
    if use_funds:
        # Try to connect so we can use account equity if requested
        tc = None; which = "unknown"
        try:
            tc, which = connect_trading_auto()
            print(f"[alpaca] trading environment: {which}")
        except Exception as e:
            if getattr(args, "use_account_equity", False):
                raise
            print(f"[alpaca] trading connect skipped (not required if --equity provided): {e}")

        cfg = load_funds_config(args.funds_config)
        equity = _account_equity_or_default(
            tc,
            explicit_equity=(0.0 if getattr(args, "use_account_equity", False) else float(getattr(args, "equity", 0.0)))
        )
        print(f"[funds] Equity basis: ${equity:,.2f} ({'account' if getattr(args,'use_account_equity',False) else 'provided'})")
        syms_from_cfg, per_symbol_budget = plan_symbol_budgets_from_funds(cfg, equity)
        if getattr(args, "symbols", None):
            wanted = set(s.strip().upper() for s in args.symbols.split(",") if s.strip())
            syms = [s for s in syms_from_cfg if s in wanted]
        else:
            syms = syms_from_cfg
        if not syms:
            print("[funds] No symbols after intersection / planning; exiting.")
            return
        print(f"[funds] Planned {len(syms)} symbols; sample budgets: " +
              ", ".join(f"{k}=${per_symbol_budget[k]:.2f}" for k in list(per_symbol_budget.keys())[:5]))
    else:
        # Original symbol logic
        if getattr(args, "symbols", None):
            syms = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
        else:
            syms = list(DATA_SOURCES.keys())

    # Holdings CSV for SELL sizing (optional)
    holdings = {}
    if getattr(args, "holdings", None) and os.path.exists(args.holdings):
        try:
            hdf = pd.read_csv(args.holdings)
            for _, r in hdf.iterrows():
                s = str(r["symbol"]).upper()
                holdings[s] = float(r.get("shares", 0.0))
            print(f"[holdings] Loaded positions for {len(holdings)} symbols from {args.holdings}")
        except Exception as e:
            print(f"[holdings] Failed to read {args.holdings}: {e}")

    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Policy loader: prefer per-symbol model by prefix, else fallback model
    def _load_policy_for(sym):
        if getattr(args, "model_prefix", None):
            cand = Path("models") / f"{args.model_prefix}_{sym}.pt"
            if cand.exists():
                return RLPolicy(str(cand), device=device)
        return RLPolicy(str(getattr(args, "model", "models/dqn_policy_1y.pt")), device=device)

    # Cutoff decision time in ET
    today = _today_ny()
    hh, mm = map(int, str(getattr(args, "cutoff", "15:00")).split(":"))
    cutoff_dt_et = datetime(today.year, today.month, today.day, hh, mm, tzinfo=NY_TZ)

    orders, rows = [], []

    for sym in syms:
        # Build enriched daily (yesterdayâ€™s features)
        daily = get_daily_df(sym, alpaca_update=getattr(args, "alpaca_update", False), since=getattr(args, "since", None))
        if daily is None or daily.empty:
            print(f"[live] skip {sym}: no daily data.")
            continue
        if len(daily) < WINDOW_DAYS + 5:
            print(f"[live] {sym}: not enough history for stable features.")
            continue

        i0 = len(daily) - WINDOW_DAYS
        pre = daily.iloc[:i0]
        if len(pre) >= bt.TRADING_DAYS:
            yoy = float(np.clip(pre[bt.PRICE_COL].iloc[-1] / pre[bt.PRICE_COL].iloc[-bt.TRADING_DAYS] - 1.0, -0.5, 0.5))
        else:
            yoy = 0.05
        weights = {"SMA_1Y":0.50, "SMA_1M":0.30, "SMA_1W":0.15, "SMA_1D":0.05}

        # Price at/just before cutoff
        bar = fetch_alpaca_minute_last_before(sym, cutoff_dt_et)
        if bar is None:
            print(f"[live] skip {sym}: no minute bar at/before {getattr(args,'cutoff','15:00')} ET.")
            continue
        px_live = float(bar["c"])

        pol = _load_policy_for(sym)
        dec = decide_with_frozen_features(
            daily_df=daily, weights=weights, yoy_rate=yoy,
            policy=pol, cutoff_px=px_live, price_col=bt.PRICE_COL, apply_trend=True
        )
        side = dec["signal"]
        pos_frac = float(dec["pos_frac"])

        # BUY budget (funds_config or fallback)
        fallback_budget = float(getattr(args, "cash_per_symbol", 0.0))
        cash_budget = float(per_symbol_budget.get(sym, fallback_budget)) if use_funds else fallback_budget

        # SELL sizing from holdings
        sh = float(holdings.get(sym, 0.0))

        qty = 0.0
        if side == "BUY" and cash_budget > 0:
            exec_px = px_live * (1.0 + bt.SLIPPAGE_PCT)
            denom   = exec_px * (1.0 + bt.FEE_PCT)
            spend   = pos_frac * cash_budget
            qty     = max(0.0, (spend - bt.FEE_FIXED) / denom) if denom > 0 else 0.0
        elif side == "SELL" and sh > 0:
            qty = pos_frac * sh

        # Build MOC-like order row even if qty==0 (weâ€™ll filter later)
        orders.append({
            "symbol": sym,
            "side": side,
            "qty": float(qty),
            "order_type": "market",
            "tif": "cls",
            "comment": f"{getattr(args,'cutoff','15:00')} decision; pos_frac={pos_frac:.2f}; bias={dec['bias']}; buf_scale={dec['buf_scale']:.2f}"
        })
        rows.append({
            "symbol": sym,
            "price_cutoff": px_live,
            "signal": side,
            "pos_frac": pos_frac,
            "qty": float(qty),
            "cash_budget": cash_budget,
            "bias": dec["bias"],
            "buf_scale": dec["buf_scale"],
            "mid": dec["mid"], "upper": dec["upper"], "lower": dec["lower"]
        })
        print(f"[live] {sym}: px={px_live:.2f}  -> {side:<5}  qtyâ‰ˆ{qty:.4f}  " +
              f"(pos_frac={pos_frac:.2f}, bias={dec['bias']}, bufÃ—{dec['buf_scale']:.2f})")

    # Keep only orders with positive qty
    orders = [o for o in orders if float(o.get("qty", 0)) > 0]

    # Write orders CSV
    if orders:
        out_csv = Path(getattr(args, "order_file", "orders_moc.csv"))
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(orders).to_csv(out_csv, index=False)
        print(f"[live] Wrote orders to {out_csv.resolve()}")

    # Write decision snapshot CSV
    if rows:
        snap_csv = Path(getattr(args, "snapshot_file", "live_snapshot.csv"))
        snap_csv.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(snap_csv, index=False)
        print(f"[live] Wrote snapshot to {snap_csv.resolve()}")

    # Optional daily execution log
    if getattr(args, "log_csv", None) and rows:
        day = _today_ny()
        log_path = _resolve_log_target_dir(args.log_csv, prefix="live", day=day)
        for r in rows:
            _csv_append(
                str(log_path),
                ["timestamp_utc","symbol","price_cutoff","signal","pos_frac","qty","cash_budget","bias","buf_scale","mid","upper","lower"],
                {
                    "timestamp_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                    **{k: r[k] for k in ["symbol","price_cutoff","signal","pos_frac","qty","cash_budget","bias","buf_scale","mid","upper","lower"]}
                }
            )
        print(f"(execution log: {log_path})")

# =========================
# NEW: Weekly retrain (no orders) & Daily trade (immediate orders)
# =========================
def act_train_weekly(args):
    """
    Heavy(ish) weekly retrain: refresh data, train per-symbol models with more episodes.
    Saves models only (no orders).
    """
    syms = [s.strip().upper() for s in args.symbols.split(",")] if args.symbols else list(DATA_SOURCES.keys())
    device = "cuda" if torch.cuda.is_available() else "cpu"
    models_dir = Path(args.models_dir); models_dir.mkdir(parents=True, exist_ok=True)

    for sym in syms:
        try:
            daily = get_daily_df(sym, alpaca_update=args.alpaca_update, since=args.since,
                                 include_provisional_today=args.provisional_today)
            assert_backtester_ready(daily)
            N = len(daily)
            if N <= WINDOW_DAYS + 60:
                print(f"[weekly] skip {sym}: insufficient rows")
                continue

            i0 = N - WINDOW_DAYS
            iN = N - 1
            pre = daily.iloc[:i0]
            yoy = (float(np.clip(pre[bt.PRICE_COL].iloc[-1] / pre[bt.PRICE_COL].iloc[-bt.TRADING_DAYS] - 1.0, -0.5, 0.5))
                   if len(pre) >= bt.TRADING_DAYS else 0.05)
            weights = {"SMA_1Y":0.50,"SMA_1M":0.30,"SMA_1W":0.15,"SMA_1D":0.05}
            env_train = TradingEnv(daily, i0, iN, weights, yoy, True, True, True); env_train.label = sym

            model_path = models_dir / f"{args.model_prefix}_{sym}.pt"
            print(f"[weekly] {sym}: training {args.episodes} episodes â†’ {model_path}")
            train_dqn([env_train],
                      episodes=args.episodes, gamma=0.99, lr=3e-4, batch=256,
                      eps_start=1.0, eps_end=0.05, eps_decay=0.995, target_sync=500,
                      update_after=1000, updates_per_step=1, device=device, seed=123,
                      save_path=str(model_path))

            # quick sanity rollout & log
            q = load_policy(str(model_path), device=device)
            curve = rollout_greedy(env_train, q)
            m = score_equity(curve[["date","equity"]])
            print(f"[weekly] {sym} trained — final=${m['final_equity']:.2f} Sharpe={m['sharpe']:.2f} CAGR={m['cagr']:.2%} MaxDD={m['max_dd']:.2%}")

            if args.save_curve_png:
                fig, ax = plt.subplots(figsize=(10,5))
                ax.plot(pd.to_datetime(curve["date"]), curve["equity"], label=f"RL ({sym})")
                ax.set_title(f"Weekly retrain — {sym} ({args.episodes} eps)")
                ax.set_ylabel("Equity ($)"); ax.legend(); fig.tight_layout()
                out = Path(args.curve_dir) / f"weekly_{sym}.png"; out.parent.mkdir(parents=True, exist_ok=True)
                fig.savefig(out, dpi=150); plt.close(fig); print(f"[weekly] saved {out.resolve()}")

        except Exception as e:
            print(f"[weekly] {sym} error: {e}")

def act_trade_daily(args):
    """
    Daily execution: pull fresh data, load saved model(s), optional light finetune, decide, and submit IMMEDIATE orders.
    Uses current ET minute price; NOT MOC.
    """
    syms = [s.strip().upper() for s in args.symbols.split(",")] if args.symbols else list(DATA_SOURCES.keys())

    # Connect trading
    tc, which = connect_trading_auto()
    print(f"[trade] Alpaca env: {which}")

    # Optional holdings file for SELL sizing
    holdings = {}
    if args.holdings and os.path.exists(args.holdings):
        hdf = pd.read_csv(args.holdings)
        for _, r in hdf.iterrows():
            holdings[str(r["symbol"]).upper()] = float(r.get("shares", 0.0))

    device = "cuda" if torch.cuda.is_available() else "cpu"
    decisions, orders = [], []

    now_et = datetime.now(NY_TZ)
    cutoff_dt_et = now_et  # use current minute

    # Where models live
    primary_dir = Path(args.models_dir)
    fallback_model = Path(args.fallback_model) if args.fallback_model else None

    for sym in syms:
        try:
            # Refresh data (optionally add provisional bar)
            daily = get_daily_df(sym, alpaca_update=args.alpaca_update, since=args.since,
                                 include_provisional_today=args.provisional_today)
            if daily is None or daily.empty:
                print(f"[trade] skip {sym}: no daily data")
                continue
            assert_backtester_ready(daily)

            # YOY for obs construction
            i0 = max(0, len(daily) - WINDOW_DAYS)
            pre = daily.iloc[:i0]
            yoy = (float(np.clip(pre[bt.PRICE_COL].iloc[-1] / pre[bt.PRICE_COL].iloc[-bt.TRADING_DAYS] - 1.0, -0.5, 0.5))
                   if len(pre) >= bt.TRADING_DAYS else 0.05)
            weights = {"SMA_1Y":0.50,"SMA_1M":0.30,"SMA_1W":0.15,"SMA_1D":0.05}

            # Load per-symbol weekly model, else fallback
            model_path = primary_dir / f"{args.model_prefix}_{sym}.pt"
            if not model_path.exists():
                if fallback_model and fallback_model.exists():
                    model_path = fallback_model
                    print(f"[trade] {sym}: using fallback model {model_path}")
                else:
                    print(f"[trade] {sym}: no model found (expected {primary_dir}/{args.model_prefix}_{sym}.pt)")
                    continue

            # Optional light finetune on last year
            if args.finetune_episodes > 0:
                N = len(daily); 
                if N > WINDOW_DAYS + 60:
                    i0_ft = N - WINDOW_DAYS; iN_ft = N - 1
                    env_ft = TradingEnv(daily, i0_ft, iN_ft, weights, yoy, True, True, True); env_ft.label = sym
                    print(f"[trade] finetune {sym} for {args.finetune_episodes} eps")
                    train_dqn([env_ft],
                              episodes=args.finetune_episodes, gamma=0.99, lr=3e-4, batch=256,
                              eps_start=0.2, eps_end=0.05, eps_decay=0.995, target_sync=300,
                              update_after=800, updates_per_step=1, device=device, seed=123,
                              save_path=str(model_path))

            # Get current minute price
            bar = fetch_alpaca_minute_last_before(sym, cutoff_dt_et)
            if bar is None:
                print(f"[trade] {sym}: no minute bar at/before now ET; skipping")
                continue
            px_live = float(bar["c"])

            # Decide with frozen indicators + live price
            pol = RLPolicy(str(model_path), device=device)
            dec = decide_with_frozen_features(
                daily_df=daily, weights=weights, yoy_rate=yoy,
                policy=pol, cutoff_px=px_live, price_col=bt.PRICE_COL, apply_trend=True
            )
            side = dec["signal"]  # BUY/SELL/HOLD
            pos_frac = dec["pos_frac"]
            print(f"[trade] {sym}: px={px_live:.2f} -> {side} (pos_frac={pos_frac:.2f}, bias={dec['bias']}, bufÃ—{dec['buf_scale']:.2f})")

            # Size order
            qty = 0.0
            if side == "BUY" and args.cash_per_symbol > 0:
                exec_px = px_live * (1.0 + bt.SLIPPAGE_PCT)
                denom   = exec_px * (1.0 + bt.FEE_PCT)
                spend   = pos_frac * float(args.cash_per_symbol)
                qty     = max(0.0, (spend - bt.FEE_FIXED) / denom) if denom > 0 else 0.0
            elif side == "SELL":
                sh = float(holdings.get(sym, 0.0))
                if sh > 0:
                    qty = pos_frac * sh

            # Place order
            if side in ("BUY","SELL") and qty > 0:
                if not args.dry_run:
                    o = place_market_order_immediate(tc, sym, side, qty, tif=args.tif)
                    if o is not None:
                        orders.append({"symbol": sym, "side": side, "qty": qty, "tif": args.tif})
                else:
                    print(f"[dry-run] would submit {sym} {side} qty={qty:.4f} tif={args.tif}")
                    orders.append({"symbol": sym, "side": side, "qty": qty, "tif": args.tif})
            else:
                print(f"[trade] no order for {sym} (side={side}, qtyâ‰ˆ{qty:.4f})")

            decisions.append({
                "timestamp_et": now_et.isoformat(timespec="seconds"),
                "symbol": sym,
                "price_live": px_live,
                **dec
            })

        except Exception as e:
            print(f"[trade] {sym} error: {e}")

    # Outputs
    if decisions:
        snap = Path(args.snapshot_file); snap.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(decisions).to_csv(snap, index=False)
        print(f"[trade] wrote snapshot â†’ {snap.resolve()}")
    if orders:
        out_csv = Path(args.order_file); out_csv.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(orders).to_csv(out_csv, index=False)
        print(f"[trade] wrote orders â†’ {out_csv.resolve()}")

# =========================
# Main: argparse
# =========================
def add_common(ap: argparse.ArgumentParser) -> argparse.ArgumentParser:
    ap.add_argument("--alpaca-update", action="store_true", help="Fetch missing daily bars from Alpaca into daily_cache")
    ap.add_argument("--since", type=str, default=None, help="ISO date to start Alpaca refresh (overrides automatic)")
    return ap

def _add_parser_once(sub, name, help_text):
    # Simple guard so re-running / re-importing can't double-register a command
    if not hasattr(_add_parser_once, "_added"):
        _add_parser_once._added = set()
    if name in _add_parser_once._added:
        return None
    p = sub.add_parser(name, help=help_text)
    _add_parser_once._added.add(name)
    return p


# === Reward shaping CLI + env wiring helpers (added) ==========================

def add_reward_shaping_args(ap):
    ap.add_argument("--lambda-neg", type=float, default=0.5,
                    help="Penalty multiplier on negative per-step returns (e.g., 0.5)")
    ap.add_argument("--lambda-dd", type=float, default=0.0,
                    help="Penalty multiplier on drawdown vs running peak (0..1)")
    ap.add_argument("--turnover-penalty", type=float, default=None,
                    help="Override turnover penalty; None keeps env default")
    ap.add_argument("--reward-clip", type=float, default=0.03,
                    help="Clip |per-step raw return| before shaping (e.g., 0.03 = 3 percent)")
    ap.add_argument("--regime-penalty", type=float, default=0.3,
                    help="Multiply reward in bear/crash/high-ATR regimes (0=no reward, 1=no scaling)")
    ap.add_argument("--high-atr-q", type=float, default=0.67,
                    help="Quantile of atr14_pct considered 'high ATR' for regime penalty")

def env_kwargs_from_args(args):
    def _get(name, default=None):
        return getattr(args, name, default)
    return dict(
        lambda_neg=_get("lambda_neg", 0.5),
        lambda_dd=_get("lambda_dd", 0.0),
        turnover_penalty=_get("turnover_penalty", None),
        reward_clip=_get("reward_clip", 0.03),
        regime_penalty=_get("regime_penalty", 0.3),
        high_atr_q=_get("high_atr_q", 0.67),
    )

def apply_env_shaping_inplace(env, **kw):
    env.lambda_neg = float(kw.get("lambda_neg", getattr(env, "lambda_neg", 0.5)))
    env.lambda_dd  = float(kw.get("lambda_dd", getattr(env, "lambda_dd", 0.0)))
    env.turnover_penalty_override = kw.get("turnover_penalty", getattr(env, "turnover_penalty_override", None))
    env.reward_clip = kw.get("reward_clip", getattr(env, "reward_clip", 0.03))
    env.regime_penalty = float(kw.get("regime_penalty", getattr(env, "regime_penalty", 0.3)))
    env.high_atr_q = float(kw.get("high_atr_q", getattr(env, "high_atr_q", 0.67)))
    try:
        atr_slice = pd.to_numeric(env.d.loc[env.i0:env.iN, "atr14_pct"], errors="coerce").dropna()
        env._atr_threshold = float(atr_slice.quantile(env.high_atr_q)) if len(atr_slice) > 50 else None
    except Exception:
        env._atr_threshold = None

# === End helpers ===============================================================


# --- Fallback equity scorer (robust to NaNs/short curves) ---
def _score_equity_fallback(equity_curve):
    import numpy as _np
    try:
        if hasattr(equity_curve, "values"):
            s = np.asarray(list(equity_curve.values), dtype=float)
        else:
            s = np.asarray(list(equity_curve), dtype=float)
        if len(s) < 2 or not np.isfinite(s).all():
            return {"cagr": 0.0, "sharpe": 0.0, "maxdd": 0.0, "calmar": 0.0}
        rets = np.diff(s) / np.clip(s[:-1], 1e-12, None)
        mu = float(np.nanmean(rets)) * 252.0
        sd = float(np.nanstd(rets, ddof=1))
        sharpe = (mu / (sd + 1e-12)) if np.isfinite(sd) and sd > 0 else 0.0
        cagr = (float(s[-1]) / float(s[0])) ** (252.0 / max(1.0, len(s))) - 1.0 if s[0] > 0 else 0.0
        peak = np.maximum.accumulate(s)
        dd = s / np.clip(peak, 1e-12, None) - 1.0
        maxdd = float(np.nanmin(dd))
        calmar = (cagr / abs(maxdd)) if maxdd < 0 else 0.0
        if not np.isfinite(calmar): calmar = 0.0
        return {"cagr": float(cagr), "sharpe": float(sharpe), "maxdd": float(maxdd), "calmar": float(calmar)}
    except Exception:
        return {"cagr": 0.0, "sharpe": 0.0, "maxdd": 0.0, "calmar": 0.0}

# --- Normalize metrics dict from score_equity variants ---
def _coerce_metrics(curve, m):
    import numpy as _np
    needed = ("cagr", "sharpe", "maxdd", "calmar")
    if not isinstance(m, dict):
        m = {}
    if "maxdd" not in m:
        for alt in ("max_dd", "maxDrawdown", "max_drawdown", "mdd"):
            if alt in m:
                m["maxdd"] = m[alt]; break
    def _ok(v):
        try: return (v is not None) and np.isfinite(float(v))
        except Exception: return False
    if not all(_ok(m.get(k)) for k in needed):
        fb = _score_equity_fallback(curve)
        for k in needed:
            if not _ok(m.get(k)):
                m[k] = fb[k]
    return {k: float(m.get(k, 0.0)) for k in needed}


def resolve_paths(profile: str, exp_id: str | None):
    from pathlib import Path
    root = Path(".")
    if profile == "prod":
        return {
            "profile": "prod",
            "exp_id": None,
            "models_dir": root / "models",
            "logs_dir":   root / "logs",
            "config_dir": root / "config" / "prod",
            "manifests":  root / "manifests" / "prod",
        }
    base = root / "experiments" / (exp_id or "unspecified")
    return {
        "profile": "exp",
        "exp_id": exp_id or "unspecified",
        "models_dir": base / "models",
        "logs_dir":   base / "logs",
        "config_dir": root / "config" / "exp" / (exp_id or "unspecified"),
        "manifests":  base / "manifests",
    }

def ensure_dirs(paths: dict):
    for k in ("models_dir", "logs_dir", "manifests", "config_dir"):
        p = paths.get(k, None)
        if p is not None:
            p.mkdir(parents=True, exist_ok=True)

def cmd_promote(args):
    """
    Promote an experiment's latest model for a symbol into prod.
    Copies model and matching manifest; updates prod LATEST.txt.
    """
    import shutil, json
    from pathlib import Path

    # Resolve experiment and prod paths
    exp_paths  = resolve_paths("exp", args.exp_id)
    prod_paths = resolve_paths("prod", None)
    ensure_dirs(prod_paths)

    sym = args.symbol.upper()
    exp_sym_dir  = exp_paths["models_dir"] / sym
    prod_sym_dir = prod_paths["models_dir"] / sym
    prod_sym_dir.mkdir(parents=True, exist_ok=True)

    latest_file = exp_sym_dir / "LATEST.txt"
    if not latest_file.exists():
        raise SystemExit(f"[promote] No LATEST.txt found for {sym} in {exp_sym_dir}")

    model_name = latest_file.read_text().strip()
    src_model  = exp_sym_dir / model_name
    if not src_model.exists():
        raise SystemExit(f"[promote] Expected model missing: {src_model}")

    # Copy model
    dst_model = prod_sym_dir / model_name
    shutil.copy2(src_model, dst_model)

    # Try to copy matching manifest (best-effort)
    # Manifest naming here assumes "{symbol}_{timestamp}.json"
    # Extract timestamp suffix from model filename if present
    ts = None
    try:
        # e.g., dqn_sy_NVDA_20251019_132500.pt -> 20251019_132500
        base = Path(model_name).stem
        ts = base.split("_")[-2] + "_" + base.split("_")[-1] if base.count("_") >= 2 else None
    except Exception:
        ts = None

    mani_src = None
    if ts:
        cand = exp_paths["manifests"] / f"{sym}_{ts}.json"
        if cand.exists():
            mani_src = cand

    if mani_src and mani_src.exists():
        prod_paths["manifests"].mkdir(parents=True, exist_ok=True)
        shutil.copy2(mani_src, prod_paths["manifests"] / mani_src.name)

    # Update prod LATEST pointer
    (prod_sym_dir / "LATEST.txt").write_text(Path(model_name).name)
    print(f"[promote] {sym}: {model_name} → prod")

def main():
    import argparse, os, sys
    from pathlib import Path

    ap = argparse.ArgumentParser(description=f"RL Pipeline (1y) for {BACKTESTER_MODULE}.py")

    # ---- Global, top-level args for isolation profiles ----
    ap.add_argument(
        "--profile",
        choices=["prod", "exp"],
        default=os.getenv("ALGO_PROFILE", "prod"),
        help="Run context. 'prod' uses production models/logs/configs. 'exp' is isolated under ./experiments/<exp-id>/",
    )
    ap.add_argument(
        "--exp-id",
        type=str,
        default=None,
        help="Experiment namespace (e.g., 2025-10-19_guard_sweep_A). Required when --profile=exp.",
    )

    sub = ap.add_subparsers(dest="cmd")

    # --- core commands ---
    ap_train = _add_parser_once(sub, "train", "Train DQN on 1-year windows")
    if ap_train:
        add_common(ap_train)
        ap_train.add_argument("--episodes", type=int, default=250)
        ap_train.add_argument("--model", type=str, default="models/dqn_policy_1y.pt")
        add_reward_shaping_args(ap_train)
        ap_train.set_defaults(func=act_train)

    ap_eval = _add_parser_once(sub, "eval", "Evaluate saved model and plot RL equity")
    if ap_eval:
        add_common(ap_eval)
        ap_eval.add_argument("--model", type=str, default="models/dqn_policy_1y.pt")
        add_reward_shaping_args(ap_eval)
        ap_eval.set_defaults(func=act_eval)

    ap_cmp = _add_parser_once(sub, "compare", "Plot/print Rule vs RL on same 1y window")
    if ap_cmp:
        add_common(ap_cmp)
        ap_cmp.add_argument("--model", type=str, default="models/dqn_policy_1y.pt")
        add_reward_shaping_args(ap_cmp)
        ap_cmp.set_defaults(func=act_compare)

    ap_wf = _add_parser_once(sub, "walkforward", "Walk-forward eval (train->test roll)")
    if ap_wf:
        add_common(ap_wf)
        ap_wf.add_argument("--train-days", type=int, default=252*2)
        ap_wf.add_argument("--test-days", type=int, default=21)
        ap_wf.add_argument("--episodes", type=int, default=100)
        ap_wf.add_argument("--update-after", type=int, default=800)
        ap_wf.add_argument("--model", type=str, default="models/dqn_wf.pt")
        ap_wf.add_argument("--symbols", type=str, default=None, help="Comma-separated tickers; default = all")
        ap_wf.add_argument("--step-days", type=int, default=None, help="Advance per roll; default = --test-days")
        add_reward_shaping_args(ap_wf)
        ap_wf.set_defaults(func=act_walkforward)

    ap_exp = _add_parser_once(sub, "export-actions", "Export greedy action log to CSV for a symbol")
    if ap_exp:
        add_common(ap_exp)
        ap_exp.add_argument("--symbol", type=str, required=True)
        ap_exp.add_argument("--model", type=str, default="models/dqn_policy_1y.pt")
        add_reward_shaping_args(ap_exp)
        ap_exp.set_defaults(func=act_export_actions)

    ap_inf = _add_parser_once(sub, "infer", "Single-shot deterministic action for the latest bar")
    if ap_inf:
        add_common(ap_inf)
        ap_inf.add_argument("--symbol", type=str, required=True)
        ap_inf.add_argument("--model", type=str, default="models/dqn_policy_1y.pt")
        ap_inf.add_argument("--provisional-today", action="store_true",
                            help="Aggregate today's 1-minute bars into a provisional daily to make a same-day decision")
        ap_inf.add_argument("--save-csv", type=str, default="", help="Optional path to save/append the latest decision")
        ap_inf.add_argument("--log-csv", type=str, default=None, help="Directory for daily action logs (creates infer_YYYY-MM-DD.csv)")
        ap_inf.add_argument("--debug", action="store_true", help="Verbose debug prints for infer")
        add_reward_shaping_args(ap_inf)
        ap_inf.set_defaults(func=act_infer)

    ap_sy = _add_parser_once(sub, "splityear", "Per symbol: train on last 1y minus OOS, eval on reserved OOS")
    if ap_sy:
        add_common(ap_sy)
        ap_sy.add_argument("--oos-days", type=int, default=42)
        ap_sy.add_argument("--episodes", type=int, default=200)
        ap_sy.add_argument("--model-prefix", type=str, default="dqn_splityear")
        add_reward_shaping_args(ap_sy)
        ap_sy.set_defaults(func=act_splityear)

    ap_pool = _add_parser_once(sub, "splityear-pooled", "Pooled cash with momentum sizing over OOS")
    if ap_pool:
        add_common(ap_pool)
        ap_pool.add_argument("--symbols", type=str, default="", help="Comma-separated tickers (default: all in DATA_SOURCES)")
        ap_pool.add_argument("--oos-days", type=int, default=42)
        ap_pool.add_argument("--episodes", type=int, default=200)
        ap_pool.add_argument("--model-prefix", type=str, default="dqn_sy")
        ap_pool.add_argument("--invest-per-symbol", type=float, default=100.0)
        ap_pool.add_argument("--start-cash-extra", type=float, default=0.0)
        ap_pool.add_argument("--mom-window", type=int, default=20)
        ap_pool.add_argument("--mom-scale-low", type=float, default=0.8)
        ap_pool.add_argument("--mom-scale-high", type=float, default=1.3)
        add_reward_shaping_args(ap_pool)
        ap_pool.set_defaults(func=act_splityear_pooled)

    # --- LIVE (3pm ET) ---
    ap_live = _add_parser_once(sub, "live", "3pm ET decision: freeze features at yesterday, inject 3pm price, output MOC orders")
    if ap_live:
        add_common(ap_live)
        ap_live.add_argument("--symbols", type=str, default="", help="Comma-separated tickers (default: all in DATA_SOURCES)")
        ap_live.add_argument("--model", type=str, default="models/dqn_policy_1y.pt", help="Fallback model if per-symbol file missing")
        ap_live.add_argument("--model-prefix", type=str, default="dqn_splityear", help="Try models/{prefix}_{SYM}.pt first")
        ap_live.add_argument("--cash-per-symbol", type=float, default=1000.0, help="Sizing budget per symbol for BUY")
        ap_live.add_argument("--holdings", type=str, default="", help="Optional CSV with columns: symbol,shares (for SELL sizing)")
        ap_live.add_argument("--cutoff", type=str, default="15:00", help="Decision time ET, HH:MM")
        ap_live.add_argument("--order-file", type=str, default="orders_moc.csv", help="Output: suggested MOC orders")
        ap_live.add_argument("--snapshot-file", type=str, default="live_snapshot.csv", help="Output: decision details")
        ap_live.add_argument("--log-csv", type=str, default=None, help="Directory for daily execution logs (creates live_YYYY-MM-DD.csv)")
        ap_live.add_argument("--funds-config", type=str, default=None, help="Path to funds_config.json to plan per-symbol budgets")
        ap_live.add_argument("--use-account-equity", action="store_true", help="Use Alpaca account equity as the budget base")
        ap_live.add_argument("--equity", type=float, default=0.0, help="If not using account equity, supply total equity figure to budget against")
        add_reward_shaping_args(ap_live)
        ap_live.set_defaults(func=act_live)

    # --- TRAIN TODAY & TRADE (IMMEDIATE orders) ---
    ap_tt = _add_parser_once(sub, "train-today-and-trade", "Refresh data, retrain per symbol, and place immediate market orders")
    if ap_tt:
        add_common(ap_tt)
        ap_tt.add_argument("--symbols", type=str, default="", help="Comma-separated tickers (default: all in DATA_SOURCES)")
        ap_tt.add_argument("--episodes", type=int, default=120, help="Training episodes per symbol")
        ap_tt.add_argument("--model-prefix", type=str, default="dqn_today", help="Model filename prefix in ./models")
        ap_tt.add_argument("--cash-per-symbol", type=float, default=1000.0, help="Budget for BUY sizing per symbol ($)")
        ap_tt.add_argument("--holdings", type=str, default="", help="Optional CSV with columns: symbol,shares for SELL sizing")
        ap_tt.add_argument("--tif", type=str, default="ioc", help="Time-in-force for immediate orders: ioc|day|fok|gtc (default ioc)")
        ap_tt.add_argument("--order-file", type=str, default="orders_immediate.csv", help="CSV of orders submitted (or would-be in dry-run)")
        ap_tt.add_argument("--snapshot-file", type=str, default="train_trade_snapshot.csv", help="CSV of decisions and internals")
        ap_tt.add_argument("--provisional-today", action="store_true", help="Aggregate today's 1-min bars into a provisional daily bar before training/decision")
        ap_tt.add_argument("--dry-run", action="store_true", help="Do everything except submitting orders")
        ap_tt.add_argument("--funds-config", type=str, default=None, help="Path to funds_config.json to plan per-symbol budgets")
        ap_tt.add_argument("--use-account-equity", action="store_true", help="Use Alpaca account equity as the budget base")
        ap_tt.add_argument("--equity", type=float, default=0.0, help="If not using account equity, supply total equity figure to budget against")
        add_reward_shaping_args(ap_tt)
        ap_tt.set_defaults(func=act_train_today_and_trade)

    # --- PROMOTE (new) ---
    ap_prom = _add_parser_once(sub, "promote", "Promote an experiment model for a symbol into prod")
    if ap_prom:
        ap_prom.add_argument("--exp-id", required=True, help="Experiment id to promote from")
        ap_prom.add_argument("--symbol", required=True, help="Symbol to promote")
        ap_prom.set_defaults(func=cmd_promote)

    # ---- Parse & early help ----
    if len(sys.argv) == 1:
        ap.print_help()
        return
    args = ap.parse_args()

    # -------------------------------
    # Map walkleader --tag -> exp mode
    # -------------------------------
    if args.cmd == "walkleader":
        # default walkleader to exp profile unless user overrode
        if getattr(args, "profile", "prod") == "prod":
            args.profile = "exp"
        # use --tag as exp-id if not provided
        if not getattr(args, "exp_id", None):
            if getattr(args, "tag", ""):
                args.exp_id = args.tag
            else:
                raise SystemExit("walkleader requires --tag (used as exp-id for isolation)")

    # -------------------------------
    # Enforce exp-id presence in exp
    # -------------------------------
    if getattr(args, "profile", "prod") == "exp" and args.cmd != "promote" and not getattr(args, "exp_id", None):
        raise SystemExit("When --profile=exp, you must provide --exp-id.")

    # -------------------------------
    # Resolve paths & ensure folders
    # -------------------------------
    args.paths = resolve_paths(args.profile, getattr(args, "exp_id", None))
    ensure_dirs(args.paths)

    # --------------------------------------------
    # Default walkleader outputs into exp/logs/out
    # --------------------------------------------
    if args.cmd == "walkleader":
        outdir = args.paths["logs_dir"] / "out"
        outdir.mkdir(parents=True, exist_ok=True)
        if not getattr(args, "detail", None) or str(args.detail).strip() == "":
            args.detail = str(outdir / f"wl_{args.exp_id}.csv")
        if not getattr(args, "summary", None) or str(args.summary).strip() == "":
            args.summary = str(outdir / f"ws_{args.exp_id}.csv")

    # --------------------------------
    # Block live-style cmds in EXP mode
    # --------------------------------
    if args.cmd in ("live", "train-today-and-trade") and args.profile != "prod":
        raise SystemExit(f"Command '{args.cmd}' is disabled for profile='{args.profile}'. Use --profile prod.")

    # -------------------------------
    # Dispatch
    # -------------------------------
    if not hasattr(args, "func"):
        ap.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
