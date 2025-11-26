"""
intraday_allocator_from_infers.py

Allocator that:
  - Periodically runs an inference pipeline to create timestamped alloc-percent CSVs.
  - Uses the latest of those CSVs to rebalance an Alpaca account intraday.

You MUST edit `run_intraday_inference()` to plug in your real inference command.
"""

from __future__ import annotations

import asyncio
import math
import os
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, time as dtime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from dateutil import tz

# -----------------------------------------------------------------------------
# Alpaca config & basic settings
# -----------------------------------------------------------------------------

# Prefer allocator-specific env vars; fall back to generic ones.
ALP_KEY = os.getenv("APCA_ALLOC_API_KEY_ID") or os.getenv("APCA_API_KEY_ID")
ALP_SEC = os.getenv("APCA_ALLOC_API_SECRET_KEY") or os.getenv("APCA_API_SECRET_KEY")

if not ALP_KEY or not ALP_SEC:
    raise RuntimeError(
        "Missing APCA_ALLOC_API_KEY_ID / APCA_ALLOC_API_SECRET_KEY "
        "(or APCA_API_KEY_ID / APCA_API_SECRET_KEY). "
        "Set these env vars to the Alpaca paper account you want to use."
    )

TRADING_BASE = "https://paper-api.alpaca.markets"
DATA_BASE = "https://data.alpaca.markets"

APCA_HEADERS = {
    "APCA-API-KEY-ID": ALP_KEY,
    "APCA-API-SECRET-KEY": ALP_SEC,
}

print("[config] Using Alpaca key prefix:", ALP_KEY[:4], "...")

# Timezone & RTH window (adjust if needed)
TZ = tz.gettz("America/Los_Angeles")
MARKET_START_PT = dtime(6, 30)  # 9:30 ET
MARKET_END_PT = dtime(13, 0)    # 16:00 ET

# -----------------------------------------------------------------------------
# Allocation knobs
# -----------------------------------------------------------------------------

ALLOC = {
    "use_broker_equity": True,     # True: use /v2/account.equity, False: use assumed_equity
    "assumed_equity": 30000.0,     # Fallback / simulated equity if broker call fails or disabled
    "cash_buffer": 2000.0,         # Dollars to hold in cash (not allocated)
    "max_symbols": 60,             # Max number of symbols to hold
    "min_order_notional": 25.0,    # Skip trades smaller than this (in dollars)
    "rebalance_threshold": 0.03,   # Rebalance if |delta| > 3% of target_value
}

# -----------------------------------------------------------------------------
# Intraday inference config
# -----------------------------------------------------------------------------

INFER_STRATEGY = "S8"  # Strategy / column name (e.g. S8, S12)
INFER_OUT_DIR = Path("./alpaca/intraday_infers")
INFER_OUT_DIR.mkdir(parents=True, exist_ok=True)

INFER_REFRESH_HOURS: float = 2.0  # "Every other hour" during RTH
_last_infer_ts: Optional[datetime] = None


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def is_rth(now: Optional[datetime] = None) -> bool:
    """Return True if now is within regular trading hours (Mon–Fri, between MARKET_START_PT and MARKET_END_PT in TZ)."""
    if now is None:
        now = datetime.now(TZ)
    if now.weekday() >= 5:  # 5=Sat, 6=Sun
        return False
    t = now.timetz().replace(tzinfo=None)
    return MARKET_START_PT <= t <= MARKET_END_PT


def broker_account() -> Dict[str, Any]:
    """Fetch Alpaca account JSON for the configured keys."""
    url = f"{TRADING_BASE}/v2/account"
    r = requests.get(url, headers=APCA_HEADERS, timeout=10)
    r.raise_for_status()
    js = r.json()
    print(
        "[account] number:", js.get("account_number"),
        "equity:", js.get("equity"),
        "cash:", js.get("cash"),
    )
    return js


def broker_positions_df() -> pd.DataFrame:
    """Return current positions as a DataFrame with ['symbol','qty','avg_entry_price']."""
    url = f"{TRADING_BASE}/v2/positions"
    r = requests.get(url, headers=APCA_HEADERS, timeout=10)
    if r.status_code == 404:
        return pd.DataFrame(columns=["symbol", "qty", "avg_entry_price"])
    r.raise_for_status()
    js = r.json()
    if isinstance(js, dict):
        js = [js]
    if not js:
        return pd.DataFrame(columns=["symbol", "qty", "avg_entry_price"])
    df = pd.DataFrame(js)
    for col in ["symbol", "qty", "avg_entry_price"]:
        if col not in df.columns:
            df[col] = None
    return df[["symbol", "qty", "avg_entry_price"]]


def last_price(symbol: str) -> Optional[float]:
    """
    Fetch latest bar close from Alpaca for `symbol`.
    Uses /v2/stocks/{symbol}/bars/latest with feed='iex'.
    """
    url = f"{DATA_BASE}/v2/stocks/{symbol}/bars/latest"
    params = {"feed": "iex"}

    try:
        resp = requests.get(url, headers=APCA_HEADERS, params=params, timeout=10)
        if not resp.ok:
            print(f"[last_price] {symbol} error {resp.status_code}: {resp.text[:200]}")
            return None
        data = resp.json()
        bar = data.get("bar")
        if not bar or "c" not in bar:
            print(f"[last_price] {symbol} no bar in response: {data}")
            return None
        px = float(bar["c"])
        return px
    except Exception as e:
        print(f"[last_price] {symbol} EXCEPTION:", e)
        return None


def asset_info(symbol: str) -> Optional[Dict[str, Any]]:
    """Fetch asset metadata from Alpaca /v2/assets/{symbol}."""
    url = f"{TRADING_BASE}/v2/assets/{symbol}"
    try:
        r = requests.get(url, headers=APCA_HEADERS, timeout=10)
        if not r.ok:
            print(f"[asset_info] {symbol} error {r.status_code}: {r.text[:200]}")
            return None
        return r.json()
    except Exception as e:
        print(f"[asset_info] {symbol} EXCEPTION:", e)
        return None


def deployable_equity(acct_json: Dict[str, Any], alloc: Dict[str, Any]) -> float:
    """Total equity to deploy into strategy after subtracting cash buffer."""
    if alloc.get("use_broker_equity", True):
        try:
            eq = float(acct_json.get("equity", alloc["assumed_equity"]))
        except Exception:
            eq = float(alloc["assumed_equity"])
    else:
        eq = float(alloc["assumed_equity"])
    dep = max(0.0, eq - float(alloc.get("cash_buffer", 0.0)))
    return dep


def build_targets_from_pct(csv_path: Path, strategy: str, acct_json: Dict[str, Any]) -> pd.DataFrame:
    """
    Read an alloc-percent CSV and build target dollar allocation per symbol.

    Expected columns:
      - 'date'
      - 'symbol'
      - One of: pct_port_{strategy}, pct_{strategy}, {strategy}
    """
    df = pd.read_csv(csv_path, parse_dates=["date"])
    if df.empty:
        raise ValueError(f"{csv_path} is empty.")

    latest_date = df["date"].max()
    day = df.loc[df["date"] == latest_date].copy()

    if "symbol" not in day.columns:
        raise ValueError(f"{csv_path} must have a 'symbol' column.")

    day["symbol"] = day["symbol"].astype(str).str.upper().str.strip()

    # Find weight column
    candidates = [f"pct_port_{strategy}", f"pct_{strategy}", strategy]
    wcol = None
    for c in candidates:
        if c in day.columns:
            wcol = c
            break
    if wcol is None:
        raise ValueError(f"No weight column found for strategy '{strategy}' in {csv_path}")

    day[wcol] = pd.to_numeric(day[wcol], errors="coerce").fillna(0.0)
    day = day[day[wcol] > 0].copy()
    if day.empty:
        raise ValueError(f"No positive weights for {strategy} in {csv_path} on {latest_date}.")

    weights = day[wcol].clip(lower=0.0)
    wsum = float(weights.sum())
    if wsum <= 0.0:
        raise ValueError(f"Sum of weights for {strategy} is non-positive in {csv_path}.")

    dep = deployable_equity(acct_json, ALLOC)

    day["weight"] = weights / wsum
    day["target_value"] = day["weight"] * dep
    day = day.sort_values("target_value", ascending=False).head(int(ALLOC.get("max_symbols", 60)))

    out = day[["symbol", "weight", "target_value"]].copy()
    out["latest_date"] = latest_date.date().isoformat()

    print(
        f"[targets] {len(out)} symbols | deployable=${dep:,.2f} | "
        f"sum(target)=${out['target_value'].sum():,.2f} | latest={latest_date.date()}"
    )
    return out.reset_index(drop=True)


def current_values(prices: Dict[str, float], pos_df: pd.DataFrame) -> Dict[str, float]:
    """Map symbol -> current dollar value using last prices and position qty."""
    vals: Dict[str, float] = {}
    if pos_df is None or pos_df.empty:
        return vals
    for _, r in pos_df.iterrows():
        sym = str(r["symbol"]).upper()
        try:
            qty = float(r["qty"])
        except Exception:
            continue
        px = prices.get(sym)
        if px is None:
            continue
        vals[sym] = qty * px
    return vals


def plan_rebalance_pct(targets_usd: pd.DataFrame, pos_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a rebalance plan comparing target dollar values vs current dollar values.

    - Any symbol with a positive target gets equity.
    - If currently unheld and target>0, create an entry trade (even if below min_order_notional).
    - If target==0 and currently held, create an exit trade (subject to min_order_notional).
    - Otherwise, trade only if both:
        * |delta| >= min_order_notional
        * |delta| / target_value >= rebalance_threshold
    """
    if targets_usd is None or targets_usd.empty:
        print("[plan] Empty targets_usd; nothing to do.")
        return pd.DataFrame()

    target_map = dict(zip(targets_usd["symbol"], targets_usd["target_value"]))
    target_syms = set(target_map)
    held_syms: set[str] = set()

    if pos_df is not None and not pos_df.empty:
        held_syms = set(str(s).upper() for s in pos_df["symbol"].tolist())

    syms = sorted(target_syms | held_syms)
    print(f"[plan] evaluating {len(syms)} symbols")

    # Get prices
    prices: Dict[str, float] = {}
    for s in syms:
        px = last_price(s)
        if px is not None and px > 0:
            prices[s] = px

    cur_vals = current_values(prices, pos_df)
    plans: List[Dict[str, Any]] = []

    min_notional = float(ALLOC.get("min_order_notional", 0.0))
    thr = float(ALLOC.get("rebalance_threshold", 0.0))

    for s in syms:
        px = prices.get(s)
        if px is None or px <= 0:
            print(f"[plan] {s}: SKIP (no price)")
            continue

        tgt = float(target_map.get(s, 0.0))
        cur = float(cur_vals.get(s, 0.0))
        delta = tgt - cur

        info = asset_info(s) or {}
        fractionable = bool(info.get("fractionable", False))

        # New entry
        if cur <= 0 and tgt > 0:
            dv = tgt
            print(f"[plan] {s}: NEW ENTRY, target=${tgt:,.2f}")
            plan: Dict[str, Any] = {
                "symbol": s,
                "side": "buy",
                "delta_value": dv,
                "target_value": tgt,
                "current_value": cur,
                "price": px,
                "fractionable": fractionable,
            }
            if fractionable:
                plan["notional"] = round(abs(dv), 2)
                plan["qty"] = None
            else:
                qty = max(1, int(abs(dv) // px))
                plan["qty"] = qty
                plan["notional"] = None
            plans.append(plan)
            continue

        # Already holding or no target
        if abs(delta) < min_notional and tgt <= 0:
            print(f"[plan] {s}: SKIP flatten (|delta|<{min_notional}) tgt={tgt:.2f} cur={cur:.2f}")
            continue

        if abs(delta) < min_notional and tgt > 0:
            print(f"[plan] {s}: SKIP small rebalance (|delta|<{min_notional})")
            continue

        if tgt > 0:
            rel = abs(delta) / max(tgt, 1e-9)
            if rel < thr:
                print(f"[plan] {s}: SKIP small rel delta (rel={rel:.3f} < {thr})")
                continue

        if delta == 0:
            print(f"[plan] {s}: already at target")
            continue

        side = "buy" if delta > 0 else "sell"
        dv = float(delta)

        plan = {
            "symbol": s,
            "side": side,
            "delta_value": dv,
            "target_value": tgt,
            "current_value": cur,
            "price": px,
            "fractionable": fractionable,
        }

        if fractionable:
            plan["notional"] = round(abs(dv), 2)
            plan["qty"] = None
        else:
            qty = int(abs(dv) // px)
            if qty <= 0:
                print(f"[plan] {s}: SKIP (non-fractionable, qty would be 0)")
                continue
            plan["qty"] = qty
            plan["notional"] = None

        plans.append(plan)

    plans_df = pd.DataFrame(plans)
    if plans_df.empty:
        print("[plan] No orders needed.")
        return plans_df

    # Sells first, then buys
    return plans_df.sort_values(["side", "delta_value"], ascending=[True, False]).reset_index(drop=True)


def submit_order(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Submit a single order to Alpaca /v2/orders."""
    p = dict(payload)
    p.setdefault("client_order_id", f"alloc-{uuid.uuid4().hex[:12]}")
    url = f"{TRADING_BASE}/v2/orders"
    try:
        r = requests.post(url, headers=APCA_HEADERS, json=p, timeout=10)
        if not r.ok:
            print(f"[order error] status={r.status_code} body={r.text[:500]}")
            r.raise_for_status()
        js = r.json()
        print(f"[order ok] {js.get('symbol')} {js.get('side')} {js.get('qty') or js.get('notional')}")
        return js
    except Exception as e:
        print("[order EXCEPTION]", e)
        raise


def execute_plans(plans_df: pd.DataFrame, dry_run: bool = False) -> List[Dict[str, Any]]:
    """Execute a rebalance plan: sells first, then buys. If dry_run=True, only print what would be done."""
    if plans_df is None or plans_df.empty:
        print("[exec] Nothing to do.")
        return []

    SAFETY = 0.999  # trim sells slightly to avoid overselling due to rounding
    results: List[Dict[str, Any]] = []

    for side in ["sell", "buy"]:
        subset = plans_df[plans_df["side"].eq(side)].copy()
        if subset.empty:
            continue

        for _, r in subset.iterrows():
            sym = r["symbol"]
            fractionable = bool(r.get("fractionable"))
            notional = r.get("notional")
            qty = r.get("qty")

            if fractionable and pd.notna(notional):
                val = float(notional)
                if side == "sell":
                    val = val * SAFETY
                if val <= 0:
                    continue
                payload = {
                    "symbol": sym,
                    "side": side,
                    "type": "market",
                    "time_in_force": "day",
                    "notional": round(val, 2),
                }
            else:
                q = int(qty or 0)
                if q <= 0:
                    continue
                if side == "sell":
                    q = max(1, math.floor(q * SAFETY))
                payload = {
                    "symbol": sym,
                    "side": side,
                    "type": "market",
                    "time_in_force": "day",
                    "qty": str(q),
                }

            print(f"[exec] {side.upper()} {sym} payload={payload}")
            if dry_run:
                continue

            js = submit_order(payload)
            results.append(js)

    return results


# -----------------------------------------------------------------------------
# Intraday inference helpers
# -----------------------------------------------------------------------------

def run_intraday_inference() -> Path:
    """
    Run your inference pipeline and write a timestamped alloc-percent CSV
    into INFER_OUT_DIR. Returns the path of the new CSV.

    YOU MUST EDIT THE `cmd` LIST BELOW to match your real inference command.
    """
    global _last_infer_ts

    now = datetime.now(TZ)
    ts = now.strftime("%Y%m%d_%H%M")
    out_csv = INFER_OUT_DIR / f"alloc_percent_{INFER_STRATEGY}_intraday_{ts}.csv"

    # ------------------------------------------------------------------
    # TODO: EDIT THIS COMMAND to call your real inference script.
    # It should produce a CSV with columns: date, symbol, and a weight
    # column for your strategy (pct_port_{INFER_STRATEGY} / pct_{INFER_STRATEGY} / INFER_STRATEGY).
    # And it should write that file to `out_csv`.
    # ------------------------------------------------------------------

    cmd = [
        r".\.venv\Scripts\python.exe",
        r".\rl_pipeline3_rs_std_patched.py",
        "--profile", "prod",
        "--exp-id", f"intraday_{INFER_STRATEGY}_{ts}",
        "infer-day",                        # <-- adjust to your actual subcommand
        "--strategy", INFER_STRATEGY,       # <-- if your script supports this
        "--summary-out", str(out_csv),      # <-- make your script write the CSV here
    ]

    print("[infer] running:", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print("[infer] ERROR running intraday inference:", e)
        raise

    print(f"[infer] wrote {out_csv}")
    _last_infer_ts = now
    return out_csv


def get_latest_infer_csv() -> Optional[Path]:
    """Return the most recent intraday inference CSV in INFER_OUT_DIR, or None if none exist."""
    files = sorted(INFER_OUT_DIR.glob("alloc_percent_*.csv"))
    return files[-1] if files else None


# -----------------------------------------------------------------------------
# Allocator loop (intraday)
# -----------------------------------------------------------------------------

async def allocator_once_intraday(dry_run: bool = False):
    """
    Intraday allocator:
      - Only runs during RTH.
      - Every INFER_REFRESH_HOURS, run a new intraday inference.
      - Use the latest inference CSV to build targets and rebalance the account.
    """
    global _last_infer_ts

    now = datetime.now(TZ)
    print(f"[allocator] run at {now:%Y-%m-%d %H:%M:%S} PT")

    if not is_rth(now):
        print("[allocator] outside RTH; skipping (no orders, no new inference).")
        return

    # 1) Refresh inference periodically
    need_new_infer = (
        _last_infer_ts is None
        or (now - _last_infer_ts) >= timedelta(hours=INFER_REFRESH_HOURS)
    )

    if need_new_infer:
        print("[allocator] INFER_REFRESH_HOURS elapsed (or first run) — running new intraday inference...")
        try:
            run_intraday_inference()
        except Exception as e:
            print("[allocator] ERROR running intraday inference:", e)
            # Fall through and try using the previous latest file, if any

    # 2) Use latest inference CSV
    csv_path = get_latest_infer_csv()
    if csv_path is None:
        print("[allocator] no intraday inference files found; skipping.")
        return

    print(f"[allocator] using inference file: {csv_path}")

    # 3) Build targets
    acct = broker_account()
    try:
        targets_usd = build_targets_from_pct(csv_path, INFER_STRATEGY, acct)
    except Exception as e:
        print(f"[allocator] ERROR building targets from {csv_path}: {e}")
        return

    if targets_usd is None or targets_usd.empty:
        print("[allocator] no targets in CSV; skipping.")
        return

    # 4) Plan + execute rebalance
    pos = broker_positions_df()
    plans = plan_rebalance_pct(targets_usd, pos)

    if plans is None or plans.empty:
        print("[allocator] no rebalance needed (PLANS empty).")
        return

    print("[allocator] executing plans...")
    execute_plans(plans, dry_run=dry_run)


async def _sleep_to_top_of_hour():
    """Sleep until the top of the next hour (at least 5 seconds)."""
    now = datetime.now(TZ)
    next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    delay = max(5.0, (next_hour - now).total_seconds())
    print(f"[allocator] next run at {next_hour.strftime('%H:%M:%S')} (~{int(delay)}s)")
    await asyncio.sleep(delay)


async def allocator_loop_intraday(dry_run: bool = False):
    """Run allocator_once_intraday() every hour (RTH-gated)."""
    print("✅ Intraday allocator started (hourly, RTH-only).")
    while True:
        try:
            await allocator_once_intraday(dry_run=dry_run)
        except Exception as e:
            print("[allocator_loop] error:", e)
        await _sleep_to_top_of_hour()


# -----------------------------------------------------------------------------
# CLI entry point
# -----------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Intraday Alpaca allocator from inference CSVs.")
    parser.add_argument(
        "--strategy",
        default=INFER_STRATEGY,
        help="Strategy name/column to use (e.g. S8, S12).",
    )
    parser.add_argument(
        "--infer-refresh-hours",
        type=float,
        default=INFER_REFRESH_HOURS,
        help="Hours between intraday inference refreshes during RTH.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single allocator cycle instead of hourly loop.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not actually place orders; just print planned actions.",
    )

    args = parser.parse_args()

    global INFER_STRATEGY, INFER_REFRESH_HOURS
    INFER_STRATEGY = args.strategy
    INFER_REFRESH_HOURS = args.infer_refresh_hours

    print(f"[main] INFER_STRATEGY={INFER_STRATEGY} INFER_REFRESH_HOURS={INFER_REFRESH_HOURS}")

    if args.once:
        asyncio.run(allocator_once_intraday(dry_run=args.dry_run))
    else:
        asyncio.run(allocator_loop_intraday(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
