"""
allocator_once.py

Single-shot allocator: read latest S13 portfolio percentages from
alloc_percent_all_with_today.csv, compute target dollar values
per symbol, diff against current Alpaca positions, and submit
rebalance orders.

Designed to be called by the orchestrator like:

    python allocator_once.py

Assumptions:
  - Runs against Alpaca PAPER API.
  - Allocation file is produced by review_infers4.ipynb and lives at:
        ./logs/out/alloc_percent_all_with_today.csv
  - Strategy column is determined below.
"""

from __future__ import annotations

import os
from datetime import datetime, time as dtime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

import pandas as pd
import requests
from dateutil import tz
from dotenv import load_dotenv

# ---------------------------------------------------------------------
# Project root & env loading
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent
ENV_PATH = PROJECT_ROOT / ".env"

# If .env exists, load it. Use override=False so orchestrator's env wins if present.
if ENV_PATH.exists():
    load_dotenv(ENV_PATH, override=True)
else:
    print(f"[allocator_once] WARNING: .env not found at {ENV_PATH}")

# Base URLs: pull from env if set (orchestrator sets these), otherwise default to paper.
TRADING_BASE = os.getenv("APCA_API_BASE_URL", "https://paper-api.alpaca.markets")
DATA_BASE    = os.getenv("APCA_DATA_BASE_URL", "https://data.alpaca.markets")

# ---------------------------------------------------------------------
# Alpaca auth + timezone config
# ---------------------------------------------------------------------

APCA_KEY_ID = (
    os.getenv("APCA_API_KEY_ID")
    or os.getenv("ALPACA_API_KEY_ID")
    or os.getenv("ALPACA_KEY_ID")
    or os.getenv("APCA_KEY_ID")
)
APCA_SECRET_KEY = (
    os.getenv("APCA_API_SECRET_KEY")
    or os.getenv("ALPACA_API_SECRET_KEY")
    or os.getenv("ALPACA_SECRET_KEY")
    or os.getenv("APCA_SECRET_KEY")
)

if not APCA_KEY_ID or not APCA_SECRET_KEY:
    raise RuntimeError(
        "[allocator_once] Alpaca API keys not set. Expected APCA_API_KEY_ID/APCA_API_SECRET_KEY "
        "or ALPACA_KEY_ID/ALPACA_SECRET_KEY in environment. Check .env / orchestrator._init_alpaca_env()."
    )

APCA_HEADERS = {
    "APCA-API-KEY-ID": APCA_KEY_ID,
    "APCA-API-SECRET-KEY": APCA_SECRET_KEY,
    "Content-Type": "application/json",
}

TZ = tz.gettz("America/Los_Angeles")
MARKET_START_PT = dtime(6, 35)   # 09:35 ET
MARKET_END_PT   = dtime(13, 0)   # 16:00 ET


def _is_rth(now_local) -> bool:
    t = now_local.timetz().replace(tzinfo=None)
    return MARKET_START_PT <= t <= MARKET_END_PT


# ---------------------------------------------------------------------
# Strategy & allocation knobs
# ---------------------------------------------------------------------

# review_infers4 writes this file; adjust path if needed.
STRAT_CSV = PROJECT_ROOT / "logs" / "out" / "alloc_percent_all_with_today.csv"

# Use pct_S13 column from alloc file
STRATEGY = "S11"

ALLOC = {
    "use_broker_equity": True,   # use Alpaca /v2/account equity
    "assumed_equity": 30000.0,   # fallback if broker call fails
    "cash_buffer": 2000.0,       # dollars to hold out of the market
    "max_symbols": 60,           # cap names to hold (after sorting by weight)
    "min_order_notional": 25.0,  # skip dust trades
    "rebalance_threshold": 0.03, # rebalance if |delta| > 3% of target value
    "rth_only": True,            # act only during regular trading hours
}

# ---------------------------------------------------------------------
# Optional shared trade logger (allocator vs guardian)
# ---------------------------------------------------------------------

try:
    from trade_logger import log_trade as _log_trade_external
except Exception:
    _log_trade_external = None


def cancel_all_open_orders() -> None:
    """
    Best-effort cancel of all open orders.

    This frees up 'held_for_orders' so we can rebalance cleanly.
    We rely on guardian to re-establish fresh exits after
    the ledger reset.
    """
    try:
        r = requests.delete(
            f"{TRADING_BASE}/v2/orders",
            headers=APCA_HEADERS,
            timeout=10,
        )
        if r.status_code in (200, 204, 207):  # 207 = multi-status
            print("[orders] cancel_all_open_orders(): requested cancel of all open orders.")
        else:
            print(f"[orders] cancel_all_open_orders(): unexpected {r.status_code} {r.text[:300]}")
    except Exception as e:
        print(f"[orders] cancel_all_open_orders(): EXCEPTION {e}")


def log_trade(
    source: str,
    symbol: str,
    side: str,
    notional: float,
    reason: str,
    extra: Optional[str] = None,
) -> None:
    if _log_trade_external is None:
        return
    _log_trade_external(
        source=source,
        symbol=symbol,
        side=side,
        qty=None,
        price=None,
        reason=reason,
        extra=f"notional={notional:.2f}; {extra or ''}",
    )


# ---------------------------------------------------------------------
# Broker helpers
# ---------------------------------------------------------------------

def broker_account() -> dict:
    r = requests.get(f"{TRADING_BASE}/v2/account", headers=APCA_HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()


def broker_positions_df() -> pd.DataFrame:
    r = requests.get(f"{TRADING_BASE}/v2/positions", headers=APCA_HEADERS, timeout=10)
    if r.status_code == 404:
        return pd.DataFrame(columns=["symbol", "qty", "avg_entry_price"])
    r.raise_for_status()
    js = r.json()
    if isinstance(js, dict):
        js = js.get("positions", [])
    if not js:
        return pd.DataFrame(columns=["symbol", "qty", "avg_entry_price"])
    rows = []
    for p in js:
        try:
            rows.append(
                {
                    "symbol": str(p.get("symbol", "")).upper(),
                    "qty": float(p.get("qty", 0.0)),
                    "avg_entry_price": float(p.get("avg_entry_price", 0.0)),
                }
            )
        except Exception:
            continue
    return pd.DataFrame.from_records(rows)


def last_price(symbol: str) -> Optional[float]:
    sym = symbol.upper()
    # Try snapshot first
    try:
        r = requests.get(
            f"{DATA_BASE}/v2/stocks/{sym}/snapshot",
            headers=APCA_HEADERS,
            params={"feed": "iex"},
            timeout=10,
        )
        if r.status_code == 200:
            js = r.json() or {}
            trade = (js.get("latestTrade") or {}).get("p")
            if trade is not None:
                return float(trade)
            bar = js.get("minuteBar") or js.get("MinuteBar") or {}
            if bar:
                return float(bar.get("c") or bar.get("close"))
    except Exception:
        pass
    # Fallback: last 1-min bar
    try:
        rr = requests.get(
            f"{DATA_BASE}/v2/stocks/{sym}/bars",
            headers=APCA_HEADERS,
            params={"timeframe": "1Min", "limit": 1, "feed": "iex"},
            timeout=10,
        )
        if rr.status_code == 200:
            bars = rr.json().get("bars", [])
            if bars:
                return float(bars[-1]["c"])
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------
# Targets from allocation CSV
# ---------------------------------------------------------------------

def deployable_equity(acct_json: dict, alloc: dict = ALLOC) -> float:
    if alloc["use_broker_equity"]:
        try:
            eq = float(acct_json.get("equity", alloc["assumed_equity"]))
        except Exception:
            eq = alloc["assumed_equity"]
    else:
        eq = alloc["assumed_equity"]
    return max(0.0, eq - float(alloc["cash_buffer"]))


def build_targets_from_pct(csv_path: Path, strategy: str, acct_json: dict) -> pd.DataFrame:
    """
    Read alloc_percent_*_with_today.csv, pull the latest date,
    use pct_<strategy> as weights, and convert to target dollar
    values based on deployable equity.
    """
    if not csv_path.exists():
        print(f"[targets] CSV not found: {csv_path}")
        return pd.DataFrame(columns=["symbol", "target_value", "weight", "latest_date"])

    df = pd.read_csv(csv_path)
    if df.empty:
        print("[targets] CSV is empty; no targets.")
        return pd.DataFrame(columns=["symbol", "target_value", "weight", "latest_date"])

    if "date" not in df.columns or "symbol" not in df.columns:
        raise ValueError(f"[targets] Expected 'date' and 'symbol' columns in {csv_path}")

    pct_col = f"pct_{strategy}"
    if pct_col not in df.columns:
        raise ValueError(f"[targets] Expected '{pct_col}' column in {csv_path}")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    if df.empty:
        print("[targets] No valid date rows after parsing; no targets.")
        return pd.DataFrame(columns=["symbol", "target_value", "weight", "latest_date"])

    latest_date = df["date"].max()
    day = df[df["date"].eq(latest_date)].copy()
    if day.empty:
        print("[targets] Latest-date slice empty; no targets.")
        return pd.DataFrame(columns=["symbol", "target_value", "weight", "latest_date"])

    # Keep only symbols with a positive pct allocation
    day[pct_col] = pd.to_numeric(day[pct_col], errors="coerce").fillna(0.0)
    day = day[day[pct_col] > 0.0].copy()
    if day.empty:
        print(f"[targets] All {pct_col} <= 0; no targets.")
        return pd.DataFrame(columns=["symbol", "target_value", "weight", "latest_date"])

    # Cap to max_symbols
    day = day.sort_values(pct_col, ascending=False).head(int(ALLOC["max_symbols"]))

    # Normalize to weights
    w = day[pct_col].astype(float)
    total_w = float(w.sum())
    if total_w <= 0:
        print(f"[targets] Sum of {pct_col} is zero; no targets.")
        return pd.DataFrame(columns=["symbol", "target_value", "weight", "latest_date"])

    w = w / total_w
    dep = deployable_equity(acct_json, ALLOC)
    day["weight"] = w
    day["target_value"] = w * dep

    out = day[["symbol", "target_value", "weight"]].copy()
    out["latest_date"] = latest_date.date().isoformat()
    print(f"[targets] {len(out)} symbols | deployable=${dep:,.2f} | latest={latest_date.date()}")
    return out.reset_index(drop=True)


# ---------------------------------------------------------------------
# Planning orders
# ---------------------------------------------------------------------

def close_position(symbol: str) -> None:
    """
    Tell Alpaca to close 100% of the position for this symbol,
    cancelling open orders for it if needed.
    """
    sym = symbol.upper()
    try:
        r = requests.delete(
            f"{TRADING_BASE}/v2/positions/{sym}",
            headers=APCA_HEADERS,
            params={"percentage": "100", "cancel_orders": "true"},
            timeout=10,
        )
        if r.status_code >= 400:
            print(f"[close_position] ERROR {sym}: {r.status_code} {r.text[:300]}")
        else:
            print(f"[close_position] OK {sym} (requested full close)")
    except Exception as e:
        print(f"[close_position] EXCEPTION {sym}: {e}")


def current_values(prices: Dict[str, float], pos_df: pd.DataFrame) -> Dict[str, float]:
    vals: Dict[str, float] = {}
    for _, r in pos_df.iterrows():
        sym = str(r["symbol"]).upper()
        px = prices.get(sym)
        if px is not None:
            vals[sym] = float(r["qty"]) * float(px)
    return vals


def plan_rebalance_pct(targets_usd: pd.DataFrame, pos_df: pd.DataFrame) -> pd.DataFrame:
    """
    - Any symbol with a positive target in targets_usd gets equity (BUY/hold included).
    - If currently unheld (cur==0) and target>0, place the entry even if delta < min_order_notional.
    - If target==0 but currently held, plan a SELL to flatten (subject to min_order_notional).
    - Otherwise use min_order_notional + rebalance_threshold to avoid tiny churn.
    """
    empty_cols = ["symbol", "side", "delta_value", "target_value", "cur_value", "notional", "action"]

    if targets_usd is None or targets_usd.empty:
        print("[plan] No targets; nothing to do.")
        return pd.DataFrame(columns=empty_cols)

    # Build price map for all symbols in targets + held
    target_syms = set(targets_usd["symbol"].astype(str).str.upper())
    held_syms = set(pos_df["symbol"].astype(str).str.upper()) if not pos_df.empty else set()
    all_syms = sorted(target_syms | held_syms)

    prices: Dict[str, float] = {}
    for sym in all_syms:
        px = last_price(sym)
        if px is not None:
            prices[sym] = px

    cur_vals = current_values(prices, pos_df)

    # Map of symbol -> target_value
    tgt_vals: Dict[str, float] = {}
    for _, r in targets_usd.iterrows():
        sym = str(r["symbol"]).upper()
        tgt_vals[sym] = float(r["target_value"])

    min_notional = float(ALLOC["min_order_notional"])
    thr_pct      = float(ALLOC["rebalance_threshold"])

    plans: List[Dict[str, Any]] = []

    for sym in all_syms:
        px = prices.get(sym)
        tgt = tgt_vals.get(sym, 0.0)
        cur = cur_vals.get(sym, 0.0)

        if px is None:
            # Can't trade without a price
            continue

        # Nothing to do if no target and no position
        if tgt <= 0 and cur <= 0:
            continue

        delta_value = tgt - cur
        abs_delta   = abs(delta_value)

        # --- Case 1: flatten old positions (target <= 0, currently held) ---
        if tgt <= 0 and cur > 0:
            # This is a "flatten" – target is zero.
            # Mark it specially so execute_plans can use close-position API.
            if cur < min_notional:
                continue

            plans.append(
                {
                    "symbol": sym,
                    "side": "sell",
                    "price": px,
                    "target_value": tgt,
                    "cur_value": cur,
                    "delta_value": -cur,
                    "notional": cur,
                    "action": "close",   # tell execute_plans to call close_position(sym)
                }
            )
            continue

        # --- Case 2: tgt > 0 (we want some equity here) ---
        if cur == 0:
            # Fresh entry even if small (you could enforce min_notional here if you prefer)
            side = "buy"
            notional = tgt
        else:
            # Existing position; decide if we need to rebalance
            threshold = max(min_notional, tgt * thr_pct)
            if abs_delta < threshold:
                # Skip tiny churn
                continue
            side = "buy" if delta_value > 0 else "sell"
            notional = abs_delta

        if notional <= 0:
            continue

        plans.append(
            {
                "symbol": sym,
                "side": side,
                "price": px,
                "target_value": tgt,
                "cur_value": cur,
                "delta_value": delta_value,
                "notional": notional,
                "action": "trade",   # normal partial rebalance / fresh entry
            }
        )

    if not plans:
        print("[plan] No orders needed after thresholds.")
        return pd.DataFrame(columns=empty_cols)

    plans_df = pd.DataFrame.from_records(plans)
    # Sells first, then buys (cash-friendly), largest notional first
    plans_df = plans_df.sort_values(["side", "notional"], ascending=[True, False]).reset_index(drop=True)

    print("Number of planned trades:", len(plans_df))
    print("\nBy side:")
    print(plans_df["side"].value_counts())

    return plans_df


# ---------------------------------------------------------------------
# Execute orders
# ---------------------------------------------------------------------

def submit_order(payload: Dict[str, Any]) -> Dict[str, Any]:
    sym = payload.get("symbol", "").upper()
    try:
        r = requests.post(
            f"{TRADING_BASE}/v2/orders",
            headers=APCA_HEADERS,
            json=payload,
            timeout=10,
        )
        if r.status_code >= 400:
            print(f"[order] ERROR {sym}: {r.status_code} {r.text[:300]}")
            r.raise_for_status()
        data = r.json()
        print(
            f"[order] OK {sym} side={payload.get('side')} "
            f"notional={payload.get('notional')} qty={payload.get('qty')}"
        )
        return data
    except Exception as e:
        print(f"[order] EXCEPTION {sym}: {e}")
        raise


def execute_plans(plans: pd.DataFrame) -> List[Dict[str, Any]]:
    if plans is None or plans.empty:
        print("[exec] No plans to execute.")
        return []

    results: List[Dict[str, Any]] = []
    for _, row in plans.iterrows():
        sym    = str(row["symbol"]).upper()
        side   = str(row["side"]).lower()
        action = row.get("action", "trade")

        if action == "close":
            # Use close-position endpoint for full flatten; cancels symbol's orders.
            close_position(sym)
            # You could also log_trade here with reason="close_position"
            continue

        # normal "trade" path
        notional = float(row["notional"])

        payload: Dict[str, Any] = {
            "symbol": sym,
            "side": side,
            "type": "market",
            "time_in_force": "day",
            "notional": f"{notional:.2f}",
        }

        try:
            res = submit_order(payload)
            results.append(res)
            log_trade(
                source="allocator",
                symbol=sym,
                side=side.upper(),
                notional=notional,
                reason="rebalance",
                extra="allocator_once",
            )
        except Exception:
            continue

    return results


# ---------------------------------------------------------------------
# Top-level allocator
# ---------------------------------------------------------------------

def allocator_once() -> None:
    now = datetime.now(TZ)
    if ALLOC["rth_only"] and not _is_rth(now):
        print(f"[allocator] outside RTH; skipping run at {now.strftime('%Y-%m-%d %H:%M:%S')}")
        return

    print(f"[allocator] running at {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[allocator] STRATEGY={STRATEGY} CSV={STRAT_CSV}")

    # Blow away open orders so held_for_orders goes to zero
    cancel_all_open_orders()

    acct = broker_account()
    print("Broker equity from Alpaca:", acct.get("equity"))

    # --- 1) Read S13 targets from CSV ---
    targets_usd = build_targets_from_pct(STRAT_CSV, STRATEGY, acct)
    if targets_usd is None or targets_usd.empty:
        print("[allocator] no targets; skipping rebalance.")
        return

    print(f"[allocator] targets rows = {len(targets_usd)}")
    print("[allocator] top 15 targets by weight:")
    print(
        targets_usd.sort_values("weight", ascending=False)
        .head(15)
        .to_string(index=False)
    )

    # --- 2) Pull current positions ---
    pos = broker_positions_df()
    if pos is None or pos.empty:
        print("[allocator] note: no current positions; treating all as fresh entries.")
    else:
        print(f"[allocator] existing positions: {len(pos)} symbols")

    # --- 3) Plan trades ---
    plans = plan_rebalance_pct(targets_usd, pos)
    if plans is None or plans.empty:
        print("[allocator] nothing to trade after planning.")
        return

    print(f"[allocator] plans rows = {len(plans)}")
    print("[allocator] sample plans (first 20):")
    print(
        plans.head(20)[
            ["symbol", "side", "action", "cur_value", "target_value", "delta_value", "notional"]
        ].to_string(index=False)
    )

    # --- 4) Execute trades ---
    exec_results = execute_plans(plans)
    print(f"[allocator] completed; orders sent: {len(exec_results)}")


if __name__ == "__main__":
    allocator_once()
