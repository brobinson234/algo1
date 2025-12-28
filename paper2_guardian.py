# paper2_guardian.py
# Guardian stop-loss / take-profit monitor for Alpaca paper account.
#
# Standalone Python script version of the paper2 Jupyter notebook, simplified
# for use under an external orchestrator. It:
#   * Connects to Alpaca using API keys from environment variables
#   * Maintains a CSV ledger of open positions and thresholds
#   * Every GUARD_INTERVAL_MIN minutes:
#       - Refreshes ledger from current broker positions
#       - Checks stop-loss / trailing stop / take-profit thresholds
#       - Submits sell orders when conditions are hit
#
# The orchestrator should start this script as a long-running process:
#   python paper2_guardian.py
#
# When the orchestrator wants to pause guardian activity, it should
# terminate the process (SIGTERM / .terminate()) and restart later.

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, time as dtime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import asyncio
import math
import csv

import pandas as pd
import requests
from dateutil import tz
from dotenv import load_dotenv

# ---------------------------------------------------------------------
# Load Alpaca config from .env / environment
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent
ENV_PATH = PROJECT_ROOT / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH, override=True)
else:
    print(f"[guardian] WARNING: .env not found at {ENV_PATH}")

TRADING_BASE = os.getenv("APCA_API_BASE_URL", "https://paper-api.alpaca.markets")
DATA_BASE    = os.getenv("APCA_DATA_BASE_URL", "https://data.alpaca.markets")

TZ = tz.gettz("America/Los_Angeles")

# Trading headers (Alpaca)
APCA_KEY = os.getenv("APCA_API_KEY_ID") or os.getenv("ALPACA_KEY_ID")
APCA_SEC = os.getenv("APCA_API_SECRET_KEY") or os.getenv("ALPACA_SECRET_KEY")

if not APCA_KEY or not APCA_SEC:
    raise RuntimeError(
        "[guardian] Missing APCA_API_KEY_ID / APCA_API_SECRET_KEY (or ALPACA_* fallback) "
        "in environment. Check .env / orchestrator._init_alpaca_env()."
    )

APCA_HEADERS = {
    "APCA-API-KEY-ID": APCA_KEY,
    "APCA-API-SECRET-KEY": APCA_SEC,
}

# -------------------------------------------------------------------------
# Session / market phase utils (mirrors notebook logic)
# -------------------------------------------------------------------------

# 'RTH' = regular hours only
# 'EXT' = pre/post + RTH
# 'ALWAYS' = no time gating
SESSION_MODE = os.getenv("GUARDIAN_SESSION_MODE", "ALWAYS")  # 'RTH' | 'EXT' | 'ALWAYS'

# PT times (market session in your local time)
PRE_START_PT = dtime(1, 0)   # 04:00 ET
RTH_START_PT = dtime(6, 30)  # 09:30 ET
RTH_END_PT   = dtime(13, 0)  # 16:00 ET
POST_END_PT  = dtime(17, 0)  # 20:00 ET


def within_session(now_local) -> bool:
    """Return True if we should act at this local time given SESSION_MODE."""
    if SESSION_MODE == "ALWAYS":
        return True
    t = now_local.timetz().replace(tzinfo=None)
    in_rth = RTH_START_PT <= t <= RTH_END_PT
    if SESSION_MODE == "RTH":
        return in_rth
    in_pre = PRE_START_PT <= t < RTH_START_PT
    in_post = RTH_END_PT < t <= POST_END_PT
    return in_pre or in_rth or in_post


def market_phase(now_local) -> str:
    """
    Return one of: "pre", "rth", "post", "closed".

    - Weekends (Sat/Sun) are always treated as "closed".
    - On weekdays, we use the pre/RTH/post windows in local time.
    """
    # 0 = Monday, 6 = Sunday
    if now_local.weekday() >= 5:  # Saturday (5) or Sunday (6)
        return "closed"

    t = now_local.timetz().replace(tzinfo=None)

    if RTH_START_PT <= t <= RTH_END_PT:
        return "rth"
    if PRE_START_PT <= t < RTH_START_PT:
        return "pre"
    if RTH_END_PT < t <= POST_END_PT:
        return "post"
    return "closed"


def _is_rth(now_local) -> bool:
    if RTH_START_PT is None or RTH_END_PT is None:
        return False
    t = now_local.timetz().replace(tzinfo=None)
    return RTH_START_PT <= t <= RTH_END_PT


# -------------------------------------------------------------------------
# Logging helpers (guardian + optional global trade log)
# -------------------------------------------------------------------------

GUARDIAN_LOG_DIR = Path("./alpaca_paper")
GUARDIAN_LOG_DIR.mkdir(parents=True, exist_ok=True)

# Detailed guardian actions log (per-event)
ACTIONS_LOG = GUARDIAN_LOG_DIR / "guardian_actions.csv"

# Optional shared trade log (allocator + guardian)
try:
    from trade_logger import log_trade as _log_trade_external
except Exception:
    _log_trade_external = None


def log_trade(
    source: str,
    symbol: str,
    side: str,
    qty: float,
    price: float,
    reason: str,
    extra: Optional[str] = None,
) -> None:
    """Send trade info to shared trade log if available."""
    if _log_trade_external is None:
        return
    _log_trade_external(
        source=source,
        symbol=symbol,
        side=side,
        qty=qty,
        price=price,
        reason=reason,
        extra=extra,
    )


def log_action(row: Dict[str, Any]) -> None:
    """Append a row to guardian_actions.csv for debugging / audit."""
    ACTIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
    write_header = not ACTIONS_LOG.exists()
    with ACTIONS_LOG.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=sorted(row.keys()))
        if write_header:
            w.writeheader()
        w.writerow(row)


# -------------------------------------------------------------------------
# Price & market data helpers
# -------------------------------------------------------------------------


def last_px(symbol: str) -> Optional[float]:
    """Latest tradable price using Alpaca snapshot, falling back to last 1-min bar."""
    sym = symbol.upper()
    try:
        r = requests.get(
            f"{DATA_BASE}/v2/stocks/{sym}/snapshot",
            headers=APCA_HEADERS,
            params={"feed": "iex"},
            timeout=10,
        )
        if r.status_code == 200:
            js = r.json() or {}
            latest_trade = (js.get("latestTrade") or {}).get("p")
            if latest_trade is not None:
                return float(latest_trade)
            minute_bar = (js.get("minuteBar") or js.get("MinuteBar") or {})
            if minute_bar:
                return float(minute_bar.get("c") or minute_bar.get("close"))
    except Exception:
        pass

    # Fallback: last 1-minute bar
    try:
        rr = requests.get(
            f"{DATA_BASE}/v2/stocks/{sym}/bars",
            headers=APCA_HEADERS,
            params={"timeframe": "1Min", "limit": 1, "feed": "iex"},
            timeout=10,
        )
        rr.raise_for_status()
        bars = rr.json().get("bars", [])
        return float(bars[-1]["c"]) if bars else None
    except Exception:
        return None


def last_minute_low(symbol: str) -> Optional[float]:
    """Low of the last 1-minute bar (helps catch intraminute breaches)."""
    sym = symbol.upper()
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
                return float(bars[-1]["l"])
    except Exception:
        pass
    return None


def _tick_for_price(price: float) -> float:
    """Pick a reasonable price tick based on price level."""
    if price < 1:
        return 0.0001
    if price < 10:
        return 0.01
    return 0.05


def _floor_to_tick(price: float, tick: float) -> float:
    n = int(price / tick)
    return max(tick, n * tick)


def _fmt_price(p: float) -> str:
    return f"{p:.4f}" if p < 1 else f"{p:.2f}"


# -------------------------------------------------------------------------
# Broker helpers and ledger maintenance
# -------------------------------------------------------------------------

LEDGER_PATH = GUARDIAN_LOG_DIR / "ledger.csv"

REQUIRED_LEDGER_COLS = [
    "symbol",
    "entry_time_utc",
    "shares",
    "entry_px",
    "peak_px",
    "stop_pct",
    "trail_pct",
    "tp_pct",
]

# Default risk knobs if row has NaN
DEFAULT_STOP_PCT = float(os.getenv("GUARDIAN_STOP_PCT", "0.05"))   # 5%
DEFAULT_TRAIL_PCT = float(os.getenv("GUARDIAN_TRAIL_PCT", "0.04"))  # 4%
DEFAULT_TP_PCT = float(os.getenv("GUARDIAN_TP_PCT", "0.10"))        # 10%


def _broker_positions_df() -> pd.DataFrame:
    """Return current Alpaca positions as a DataFrame."""
    r = requests.get(f"{TRADING_BASE}/v2/positions", headers=APCA_HEADERS, timeout=10)
    if r.status_code != 200:
        return pd.DataFrame(columns=["symbol", "qty", "avg_entry_price"])
    try:
        js = r.json() or []
    except Exception:
        js = []
    if not js:
        return pd.DataFrame(columns=["symbol", "qty", "avg_entry_price"])
    recs = []
    for p in js:
        try:
            recs.append(
                {
                    "symbol": str(p.get("symbol", "")).upper(),
                    "qty": float(p.get("qty", 0.0)),
                    "avg_entry_price": float(p.get("avg_entry_price", 0.0)),
                }
            )
        except Exception:
            continue
    return pd.DataFrame.from_records(recs)


def _load_ledger() -> pd.DataFrame:
    if not LEDGER_PATH.exists():
        df = pd.DataFrame(columns=REQUIRED_LEDGER_COLS)
        df.to_csv(LEDGER_PATH, index=False)
        return df
    df = pd.read_csv(LEDGER_PATH)
    for c in REQUIRED_LEDGER_COLS:
        if c not in df.columns:
            df[c] = pd.NA
    # Force dtypes
    df["symbol"] = df["symbol"].astype(str)
    df["entry_time_utc"] = df["entry_time_utc"].astype(str)
    for c in ["shares", "entry_px", "peak_px", "stop_pct", "trail_pct", "tp_pct"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    if df["peak_px"].isna().any():
        df["peak_px"] = df["peak_px"].fillna(df["entry_px"])
    return df[REQUIRED_LEDGER_COLS]


LEDGER = _load_ledger()


def _save_ledger() -> None:
    LEDGER.to_csv(LEDGER_PATH, index=False)


def record_entry(symbol: str, shares: float, entry_px: float) -> None:
    """Add or update a ledger row when we open a position externally."""
    global LEDGER
    sym = symbol.upper()
    now = datetime.utcnow().isoformat(timespec="seconds")
    mask = LEDGER["symbol"].str.upper() == sym
    if mask.any():
        idx = LEDGER.index[mask][0]
        LEDGER.at[idx, "shares"] = float(shares)
        LEDGER.at[idx, "entry_px"] = float(entry_px)
        LEDGER.at[idx, "peak_px"] = float(entry_px)
        LEDGER.at[idx, "entry_time_utc"] = now
    else:
        LEDGER = pd.concat(
            [
                LEDGER,
                pd.DataFrame(
                    [
                        {
                            "symbol": sym,
                            "entry_time_utc": now,
                            "shares": float(shares),
                            "entry_px": float(entry_px),
                            "peak_px": float(entry_px),
                            "stop_pct": DEFAULT_STOP_PCT,
                            "trail_pct": DEFAULT_TRAIL_PCT,
                            "tp_pct": DEFAULT_TP_PCT,
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )
    _save_ledger()


def reconcile_ledger_with_broker() -> None:
    """Align LEDGER with actual broker positions (add new, drop closed, update qty)."""
    global LEDGER
    df = _broker_positions_df()
    held = set(df["symbol"].astype(str).str.upper()) if not df.empty else set()

    # prune symbols no longer held
    LEDGER = LEDGER[LEDGER["symbol"].astype(str).str.upper().isin(held)].reset_index(drop=True)

    # ensure entries exist / update share qty to match broker
    idx_map = {s: i for i, s in enumerate(LEDGER["symbol"].astype(str).str.upper())}
    for _, r in df.iterrows():
        sym = str(r["symbol"]).upper()
        qty = float(r["qty"])
        aep = float(r["avg_entry_price"])
        if sym in idx_map:
            i = idx_map[sym]
            LEDGER.at[i, "shares"] = qty
            if pd.isna(LEDGER.at[i, "entry_px"]) or float(LEDGER.at[i, "entry_px"]) <= 0:
                LEDGER.at[i, "entry_px"] = aep
            if pd.isna(LEDGER.at[i, "peak_px"]) or float(LEDGER.at[i, "peak_px"]) <= 0:
                LEDGER.at[i, "peak_px"] = aep
        else:
            record_entry(sym, qty, aep)

    _save_ledger()


def _safe_update_peak(symbol: str, new_price: float) -> None:
    """Update peak price for a symbol, preserving types and saving ledger."""
    global LEDGER
    sym = symbol.upper()
    mask = LEDGER["symbol"].astype(str).str.upper() == sym
    if not mask.any():
        return
    idx = LEDGER.index[mask][0]
    prev = float(LEDGER.at[idx, "peak_px"])
    if new_price > prev:
        LEDGER.at[idx, "peak_px"] = float(new_price)
        LEDGER.at[idx, "entry_time_utc"] = datetime.utcnow().isoformat(timespec="seconds")
        _save_ledger()


# -------------------------------------------------------------------------
# Order helpers + dust cleanup
# -------------------------------------------------------------------------

def get_open_orders_for_symbol(symbol: str) -> list[dict]:
    sym = symbol.upper()
    try:
        r = requests.get(
            f"{TRADING_BASE}/v2/orders",
            headers=APCA_HEADERS,
            params={"status": "open", "limit": 500, "symbols": sym},
            timeout=10,
        )
        if r.status_code != 200:
            print(f"[guardian] get_open_orders_for_symbol: {sym} -> {r.status_code} {r.text[:200]}")
            return []
        return r.json() or []
    except Exception as e:
        print(f"[guardian] get_open_orders_for_symbol: EXCEPTION {sym}: {e}")
        return []


def cancel_symbol_orders(symbol: str) -> None:
    sym = symbol.upper()
    orders = get_open_orders_for_symbol(sym)
    if not orders:
        return
    for o in orders:
        oid = o.get("id")
        if not oid:
            continue
        try:
            rr = requests.delete(f"{TRADING_BASE}/v2/orders/{oid}", headers=APCA_HEADERS, timeout=10)
            print(f"[guardian] cancel {sym} order {oid}: {rr.status_code}")
        except Exception as e:
            print(f"[guardian] EXCEPTION cancel {sym} order {oid}: {e}")


def submit_order(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Submit an order to Alpaca and log the action."""
    sym = payload.get("symbol", "").upper()

    # --- Alpaca extended-hours rule ---
    # If we set extended_hours=True, Alpaca requires DAY limit orders.
    if payload.get("extended_hours"):
        payload["time_in_force"] = "day"
        if payload.get("type") != "limit":
            payload["type"] = "limit"

    try:
        r = requests.post(
            f"{TRADING_BASE}/v2/orders",
            headers=APCA_HEADERS,
            json=payload,
            timeout=10,
        )
        if r.status_code >= 400:
            log_action(
                {
                    "ts": datetime.utcnow().isoformat(timespec="seconds"),
                    "event": "order_submit_error",
                    "symbol": sym,
                    "status_code": r.status_code,
                    "body": r.text,
                }
            )
            print("[order error]", r.status_code, r.text)
            r.raise_for_status()
        data = r.json()
        log_action(
            {
                "ts": datetime.utcnow().isoformat(timespec="seconds"),
                "event": "order_submit_ok",
                "symbol": sym,
                "order_id": data.get("id"),
                "side": payload.get("side"),
                "qty": payload.get("qty"),
                "type": payload.get("type"),
                "limit_price": payload.get("limit_price"),
                "time_in_force": payload.get("time_in_force"),
                "extended_hours": payload.get("extended_hours"),
            }
        )
        return data
    except Exception as e:
        log_action(
            {
                "ts": datetime.utcnow().isoformat(timespec="seconds"),
                "event": "order_submit_exception",
                "symbol": sym,
                "error": str(e),
            }
        )
        raise


def cancel_all_orders_for_symbol(symbol: str) -> int:
    """Cancel all open orders for a symbol. Return count cancelled."""
    sym = symbol.upper()
    try:
        r = requests.get(
            f"{TRADING_BASE}/v2/orders?status=open",
            headers=APCA_HEADERS,
            timeout=10,
        )
        r.raise_for_status()
        open_orders = [o for o in r.json() if str(o.get("symbol", "")).upper() == sym]
    except Exception:
        return 0

    cancelled = 0
    for o in open_orders:
        oid = o.get("id")
        try:
            rr = requests.delete(
                f"{TRADING_BASE}/v2/orders/{oid}",
                headers=APCA_HEADERS,
                timeout=10,
            )
            if rr.status_code in (200, 204):
                cancelled += 1
        except Exception:
            continue
    return cancelled


def close_position(sym: str) -> bool:
    """Try to close the entire position via Alpaca's close endpoint."""
    try:
        r = requests.delete(
            f"{TRADING_BASE}/v2/positions/{sym}",
            headers=APCA_HEADERS,
            timeout=10,
        )
        return r.status_code == 200
    except Exception:
        return False


def get_position_status(symbol: str) -> Dict[str, float]:
    """Return qty/held_for_orders/available for a symbol from positions API."""
    sym = symbol.upper()
    try:
        r = requests.get(
            f"{TRADING_BASE}/v2/positions/{sym}",
            headers=APCA_HEADERS,
            timeout=10,
        )
        if r.status_code != 200:
            return {"qty": 0.0, "held_for_orders": 0.0, "available": 0.0}
        js = r.json() or {}
        def _f(k: str) -> float:
            try:
                return float(js.get(k, 0))
            except Exception:
                return 0.0
        return {
            "qty": _f("qty"),
            "held_for_orders": _f("held_for_orders"),
            "available": _f("available"),
        }
    except Exception:
        return {"qty": 0.0, "held_for_orders": 0.0, "available": 0.0}


def is_dust(symbol: str, qty: float) -> bool:
    """Heuristic for tiny residual positions that Alpaca often won't let you trade."""
    return abs(qty) < 1e-4


async def sweep_dust(symbol: str) -> None:
    """Best-effort clean-up for dust positions."""
    sym = symbol.upper()
    cancel_all_orders_for_symbol(sym)
    st = get_position_status(sym)
    if st["qty"] <= 0:
        return
    if not is_dust(sym, st["qty"]):
        return
    try:
        rr = requests.delete(
            f"{TRADING_BASE}/v2/positions/{sym}",
            headers=APCA_HEADERS,
            timeout=10,
        )
        log_action(
            {
                "ts": datetime.utcnow().isoformat(timespec="seconds"),
                "event": "dust_sweep",
                "symbol": sym,
                "status_code": rr.status_code,
            }
        )
    except Exception as e:
        log_action(
            {
                "ts": datetime.utcnow().isoformat(timespec="seconds"),
                "event": "dust_sweep_error",
                "symbol": sym,
                "error": str(e),
            }
        )


# -------------------------------------------------------------------------
# Guardian core: thresholds and exits
# -------------------------------------------------------------------------


@dataclass
class Thresholds:
    hard_stop_px: float
    trail_stop_px: float
    tp_px: float


def current_thresholds(row: pd.Series) -> Optional[Thresholds]:
    entry = float(row["entry_px"])
    peak = float(row["peak_px"])
    stop_pct = float(row["stop_pct"]) if not pd.isna(row["stop_pct"]) else DEFAULT_STOP_PCT
    trail_pct = float(row["trail_pct"]) if not pd.isna(row["trail_pct"]) else DEFAULT_TRAIL_PCT
    tp_pct = float(row["tp_pct"]) if not pd.isna(row["tp_pct"]) else DEFAULT_TP_PCT

    if entry <= 0 or peak <= 0:
        return None

    hard = entry * (1.0 - stop_pct)
    trail = peak * (1.0 - trail_pct)
    tp = entry * (1.0 + tp_pct)
    return Thresholds(hard_stop_px=hard, trail_stop_px=trail, tp_px=tp)


def _safe_exit_qty(row: pd.Series, st: Dict[str, float], decimals: int = 6) -> float:
    """
    Compute a sell quantity that will never exceed Alpaca's 'available' shares.

    - Use the smaller of:
        * ledger 'shares'
        * broker 'qty'
        * broker 'available' (if present)
    - Floor to the given number of decimal places (default 6) to avoid rounding UP.
    """
    try:
        ledger_shares = float(row.get("shares", 0.0))
    except Exception:
        ledger_shares = 0.0

    broker_qty = float(st.get("qty", 0.0))
    available = float(st.get("available", broker_qty))

    candidates = [q for q in (ledger_shares, broker_qty, available) if q > 0]
    if not candidates:
        return 0.0

    base = min(candidates)

    factor = 10 ** decimals
    floored = math.floor(base * factor) / factor

    # Treat ultra-tiny amounts as zero
    if floored < 1e-6:
        return 0.0

    return floored


GUARD_INTERVAL_MIN = int(os.getenv("GUARDIAN_CADENCE_MIN", "2"))


async def guard_once(verbose: bool = True) -> None:
    """Single guardian tick: reconcile ledger, check exits, submit orders."""
    global LEDGER

    now_local = datetime.now(TZ)
    if not within_session(now_local):
        if verbose:
            print(f"[guardian] outside session ({SESSION_MODE}); skipping @ {now_local}")
        return

    reconcile_ledger_with_broker()
    if LEDGER.empty:
        if verbose:
            print("[guardian] LEDGER empty; nothing to do.")
        return

    phase = market_phase(now_local)
    total, checked, exits = len(LEDGER), 0, []

    for _, r in LEDGER.copy().iterrows():
        sym = str(r["symbol"]).upper()
        checked += 1

        px = last_px(sym)
        low = last_minute_low(sym)
        eff = px if (low is None or (px is not None and px <= low)) else low
        if eff is None:
            continue

        _safe_update_peak(sym, px if px is not None else eff)

        th = current_thresholds(r)
        if th is None:
            continue

        reasons: List[str] = []
        if eff <= th.hard_stop_px:
            reasons.append("hard")
        if eff <= th.trail_stop_px:
            reasons.append("trail")
        if px is not None and px >= th.tp_px:
            reasons.append("tp")
        if not reasons:
            continue

        # Determine effective qty based on broker state + ledger, with safe flooring
        st = get_position_status(sym)
        safe_qty = _safe_exit_qty(r, st)  # r is the ledger row
        if safe_qty <= 0:
            continue

        qty_str = f"{safe_qty:.6f}".rstrip("0").rstrip(".")
        reason_label = "+".join(reasons)

        if phase == "rth":
            order = {
                "symbol": sym,
                "side": "sell",
                "type": "market",
                "time_in_force": "day",
                "qty": qty_str,
            }
        elif phase in ("pre", "post"):
            ref_candidates: List[float] = []
            if px is not None:
                ref_candidates.append(px)
            if low is not None:
                ref_candidates.append(low)
            ref = min(ref_candidates) if ref_candidates else eff
            tick = _tick_for_price(ref)
            limit = _floor_to_tick(ref - tick, tick)
            order = {
                "symbol": sym,
                "side": "sell",
                "type": "limit",
                "time_in_force": "day",
                "qty": qty_str,
                "limit_price": _fmt_price(limit),
                "extended_hours": True,
            }
        else:
            # market closed: GTC limit that will be live at next session
            ref = px if px is not None else eff
            tick = _tick_for_price(ref)
            limit = _floor_to_tick(ref - tick, tick)
            order = {
                "symbol": sym,
                "side": "sell",
                "type": "limit",
                "time_in_force": "gtc",
                "qty": qty_str,
                "limit_price": _fmt_price(limit),
                "extended_hours": True,
            }

        if verbose:
            print(
                f"[plan] {sym} phase={phase} reasons={reason_label} -> "
                f"type={order['type']} tif={order['time_in_force']} "
                f"limit={order.get('limit_price')}"
            )

        # Cancel any existing guardian orders and submit new one
        cancel_symbol_orders(sym)
        cancel_all_orders_for_symbol(sym)
        submit_order(order)
        log_trade(
            source="guardian",
            symbol=sym,
            side="SELL",
            qty=safe_qty,
            price=px or eff,
            reason=reason_label,
            extra=f"phase={phase}",
        )

        await sweep_dust(sym)
        exits.append((sym, reason_label))

    if verbose:
        print(
            f"[guardian] checked {checked}/{total} tracked symbols, exits={len(exits)} "
            f"@ {now_local.strftime('%H:%M:%S')}"
        )


async def _sleep_to_next_interval() -> None:
    now = datetime.now(TZ)
    step = int(GUARD_INTERVAL_MIN)
    next_min = ((now.minute // step) + 1) * step
    next_tick = now.replace(minute=next_min % 60, second=0, microsecond=0)
    if next_min >= 60:
        next_tick += timedelta(hours=1)
    delay = max(5.0, (next_tick - now).total_seconds())
    print(f"[guardian] next check at {next_tick.strftime('%H:%M:%S')} (~{int(delay)}s)")
    await asyncio.sleep(delay)


async def guard_loop() -> None:
    cadence = int(GUARD_INTERVAL_MIN)
    mode = SESSION_MODE
    print(f"✅ guardian started (cadence={cadence} min, mode={mode}).")
    while True:
        try:
            await guard_once(verbose=True)
        except Exception as e:
            print("[guard_loop] error:", e)
        await _sleep_to_next_interval()


# -------------------------------------------------------------------------
# Main entrypoint
# -------------------------------------------------------------------------

def main() -> None:
    # Ensure initial alignment of ledger with broker before starting loop
    reconcile_ledger_with_broker()
    try:
        asyncio.run(guard_loop())
    except KeyboardInterrupt:
        print("\n[guardian] interrupted; exiting.")


if __name__ == "__main__":
    main()
