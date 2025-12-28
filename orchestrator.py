# orchestrator.py
#
# High-level orchestration loop for live trading:
#
# Every 90 minutes (while running):
#     1) Guardian (stop-loss / take-profit) keeps running.
#     2) Run RL inference for all symbols -> logs/infer_YYYY-MM-DD.csv
#     3) Run review_infers4.ipynb to rebuild S11 allocations.
#     4) Stop guardian.
#     5) Run allocator_once (S11-based rebalance).
#     6) Reset ledger from positions.
#     7) Restart guardian.
#
# Assumptions:
#   - Project root is C:\Users\brobi\OneDrive\Desktop\Algo1
#   - venv Python is .venv\Scripts\python.exe
#   - RL pipeline script is rl_pipeline3_rs_std_patched.py
#   - review_infers4.ipynb lives in the project root and reads logs\infer_*.csv
#   - Allocator entrypoint is allocator_once.py
#   - Ledger reset entrypoint is reset_ledger_after_rebalance.py
#   - Guardian script is paper2_guardian.py


from __future__ import annotations

import sys
import os
import time
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, field   # <-- NEW

from dotenv import load_dotenv  # <-- NEW
from email_reports import send_reports


# at top of orchestrator.py
from pathlib import Path
import os

def _load_local_email_env():
    env_file = Path(__file__).with_name("email_secrets.txt")
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

_load_local_email_env()

# Load Alpaca credentials and other secrets from .env in project root
ENV_PATH = Path(__file__).resolve().parent / ".env"
if ENV_PATH.exists():
    # override=True so .env beats any stale OS-level values
    load_dotenv(ENV_PATH, override=True)
else:
    print(f"[orchestrator] WARNING: .env not found at {ENV_PATH}")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Central Alpaca config for ALL child processes (rl_pipeline, guardian, etc.)
# ---------------------------------------------------------------------------


ALPACA_PAPER_BASE = "https://paper-api.alpaca.markets"
ALPACA_DATA_BASE  = "https://data.alpaca.markets"



def _init_alpaca_env() -> None:
    """
    Force all Alpaca-related env vars to use the same PAPER credentials.

    Source of truth: ALPACA_KEY_ID / ALPACA_SECRET_KEY / ALPACA_FEED
    loaded from .env above.
    """
    key = os.getenv("ALPACA_KEY_ID")
    sec = os.getenv("ALPACA_SECRET_KEY")

    if not key or not sec:
        raise RuntimeError(
            "Missing ALPACA_KEY_ID / ALPACA_SECRET_KEY in environment. "
            "Set them in .env in the project root."
        )

    feed = os.getenv("ALPACA_FEED", "iex")

    env_updates = {
        # Official Alpaca env names
        "APCA_API_KEY_ID": key,
        "APCA_API_SECRET_KEY": sec,
        "APCA_API_BASE_URL": ALPACA_PAPER_BASE,
        "APCA_DATA_BASE_URL": ALPACA_DATA_BASE,

        # Common alternate names used elsewhere
        "ALPACA_KEY_ID": key,
        "ALPACA_SECRET_KEY": sec,
        "ALPACA_API_KEY_ID": key,
        "ALPACA_API_SECRET_KEY": sec,
        "ALPACA_BASE_URL": ALPACA_PAPER_BASE,
        "APCA_KEY_ID": key,
        "APCA_SECRET_KEY": sec,

        # Feed
        "ALPACA_FEED": feed,
    }

    for k, v in env_updates.items():
        os.environ[k] = v


# Call this ONCE at startup so every subprocess sees correct keys
_init_alpaca_env()

# Root of your Algo project
PROJECT_ROOT = Path(r"C:\Users\brobi\OneDrive\Desktop\Algo1")  # ### ADJUST IF NEEDED

# venv Python
VENV_PY = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"

# RL pipeline script (used for inference)
RL_PIPELINE = PROJECT_ROOT / "rl_pipeline3_rs_std_patched.py"

# Logs dir where infer_YYYY-MM-DD.csv get written
INFER_LOG_DIR = PROJECT_ROOT / "logs"

# Review notebook (S11 / allocation logic) — must read logs/infer_*.csv
REVIEW_NB_DIR = PROJECT_ROOT  / "logs"                    # ### ADJUST IF NEEDED
REVIEW_NB_NAME = "review_infers4.ipynb"           # ### ADJUST IF NEEDED

# Allocator script: should implement the actual S11-based allocation + rebalance
# e.g., allocator_once.py with a main() that:
#   - reads logs/out/alloc_percent_*_with_today.csv
#   - uses STRATEGY = "S11"
#   - calls broker_account / build_targets_from_pct / plan_rebalance_pct / execute_plans
ALLOCATOR_SCRIPT = PROJECT_ROOT / "allocator_once.py"

# Ledger reset script: should rebuild alpaca_paper/ledger.csv using current positions
RESET_LEDGER_SCRIPT = PROJECT_ROOT / "reset_ledger_after_rebalance.py"  # ### ADJUST IF NEEDED

# Guardian / stop-loss monitor script: 2-min loop watching ledger.csv
GUARDIAN_SCRIPT = PROJECT_ROOT / "paper2_guardian.py"  # ### ADJUST IF NEEDED

# Universe used for inference (you can expand this to your full list)
SYMBOLS = ["T"
           ,"TMUS","CMCSA",
    "IBM","RGTI","QBTS","QUBT","IONQ","QS","AMD","SLDP","MSFT","CHGG","AI","NVDA","TSM","GOOGL",
    "PAYO","LCID","PLUG","BYND","TM","SPY","NKLAQ","AMC","TDC","INFA","SNOW","PSTG","MDB","FSLR",
    "ENPH","SEDG",
    
    "ARRY","NXT","ENVX","MVST","EOSE","FLNC","EVGO","ITRI","AMSC","POWI","VICR",
    "NVTS","CLNE","GEVO","MNTK","ELVA","XEL","AEP","RNW","INTC","ARQQ","MU","SMCI","TRV","PGR",
    "BHP","COST","MRK","NFLX","RMBS","ALB","VZ","AAPL","PG","ROP","KO","PEP",
    "CCI","KR","MDLZ","GIS","CBP","MKC",
    "NOK","ASMC",
    # Added missing Nasdaq-100 constituents
    "AVGO",
    "ASML","CSCO","AZN","SHOP","APP","LIN","LRCX","QCOM","PDD",
    "ISRG","INTU","ARM","AMAT","BKNG","KLAC","AMGN","TXN","PANW","ADBE","GILD","CRWD","HON","CEG",
    "ADI","MELI","ADP","DASH","VRTX","SBUX","CDNS","SNPS","MSTR","ORLY","ABNB","MRVL","CTAS","MAR",
    "TRI","PYPL","REGN","MNST","CSX","ADSK","FTNT","WDAY","AXON","DDOG","NXPI","ROST","ZS","WBD",
    "PCAR","IDXX","EA","EXC","FAST","BKR","TTWO","PAYX","TEAM","CPRT","CCEP","FANG","KDP","GEHC",
    "MCHP","CHTR","CTSH","VRSK","CSGP","KHC","ODFL","DXCM","TTD","BIIB","LULU","ON","CDW","GFS",
    # Adding non tech s&p 
    'ATO','EVRG','WEC','COR','JNJ','TJX','CMS','PPL','DUK'
 ]

# Rebalance frequency
REBALANCE_INTERVAL_SECONDS = 90 * 60  # 90 minutes


# ---------------------------------------------------------------------------
# Global guardian process handle
# ---------------------------------------------------------------------------

guardian_proc: subprocess.Popen | None = None


# ---------------------------------------------------------------------------
# 1) Inference for all symbols
# ---------------------------------------------------------------------------

def run_infer_for_all_symbols() -> None:
    """
    Call rl_pipeline3_rs_std_patched.py infer once per symbol.

    Assumes rl_pipeline3 supports a CLI like:
        python rl_pipeline3_rs_std_patched.py infer
            --symbol <SYM>
            --model <path-to-model>
            --alpaca-update
            --provisional-today
            --log-csv logs
    """
    INFER_LOG_DIR.mkdir(parents=True, exist_ok=True)

    today = datetime.now(timezone.utc).date()
    print(f"[infer] Running inference for {len(SYMBOLS)} symbols on {today}...")

    for sym in SYMBOLS:
        # Per-symbol model, fallback to generic policy if missing
        model_path = PROJECT_ROOT / "models" / f"dqn_sy_{sym}.pt"
        if not model_path.exists():
            model_path = PROJECT_ROOT / "models" / "dqn_policy_1y.pt"

        cmd = [
            str(VENV_PY),
            str(RL_PIPELINE),
            "infer",
            "--symbol", sym,
            "--model", str(model_path),
            "--alpaca-update",
            "--provisional-today",
            "--log-csv", str(INFER_LOG_DIR),
        ]
        print("[infer]", " ".join(cmd))
        # If one symbol fails, keep going; don't crash the entire cycle
        subprocess.run(cmd, cwd=str(PROJECT_ROOT), check=False)

    print("[infer] Done for all symbols.")


# ---------------------------------------------------------------------------
# 2) Run review_infers4 headless (rebuild S11 allocations)
# ---------------------------------------------------------------------------

def run_review_infers4() -> None:
    """
    Execute review_infers4.ipynb headless using nbconvert.

    - Working dir = REVIEW_NB_DIR (e.g., project root).
    - review_infers4.ipynb should read logs/infer_*.csv.
    - It should write allocation CSVs (e.g., alloc_percent_*_with_today.csv)
      to something like logs/out/ or out/ (depending on how it's coded).
    """
    nb_path = REVIEW_NB_DIR / REVIEW_NB_NAME
    if not nb_path.exists():
        raise FileNotFoundError(f"[review] Notebook not found: {nb_path}")

    cmd = [
        str(VENV_PY),
        "-m", "jupyter", "nbconvert",
        "--to", "notebook",
        "--execute", nb_path.name,
        "--output", "review_infers4_executed.ipynb",
    ]
    print(f"[review] Running {REVIEW_NB_NAME} via nbconvert...")
    subprocess.run(cmd, cwd=str(REVIEW_NB_DIR), check=True)
    print("[review] review_infers4 completed; allocation CSVs refreshed.")


# ---------------------------------------------------------------------------
# 3) Run allocator once (S11-based rebalance)
# ---------------------------------------------------------------------------

def run_allocator_once() -> None:
    """
    Run your allocator_once entrypoint, which:
        - Reads the allocation breakdown produced by review_infers4
        - Uses STRATEGY = 'S11'
        - Plans and submits rebalance orders via Alpaca

    Example allocator_once.py structure:

        from broker_lib import (
            broker_account,
            broker_positions_df,
            build_targets_from_pct,
            plan_rebalance_pct,
            execute_plans,
        )
        from pathlib import Path

        PROJECT_ROOT = Path(r"...")
        STRAT_CSV = PROJECT_ROOT / "logs" / "out" / "alloc_percent_select_with_today.csv"
        STRATEGY  = "S11"

        def allocator_once():
            acct = broker_account()
            targets_usd = build_targets_from_pct(STRAT_CSV, STRATEGY, acct)
            pos = broker_positions_df()
            plans = plan_rebalance_pct(targets_usd, pos)
            execute_plans(plans)

        if __name__ == "__main__":
            allocator_once()
    """
    if not ALLOCATOR_SCRIPT.exists():
        raise FileNotFoundError(f"[alloc] Allocator script not found: {ALLOCATOR_SCRIPT}")

    cmd = [str(VENV_PY), str(ALLOCATOR_SCRIPT)]
    print("[alloc] Running allocator_once...")
    subprocess.run(cmd, cwd=str(PROJECT_ROOT), check=True)
    print("[alloc] allocator_once completed.")


# ---------------------------------------------------------------------------
# 4) Reset ledger after rebalance
# ---------------------------------------------------------------------------

def reset_ledger_after_rebalance() -> None:
    """
    Run a script that rebuilds alpaca_paper/ledger.csv from current positions.

    That script (reset_ledger_after_rebalance.py) should:
        - Query Alpaca for current open positions
        - For each position, determine buy_price / basis
        - Write alpaca_paper/ledger.csv in the format guardian expects
    """
    if not RESET_LEDGER_SCRIPT.exists():
        print(f"[ledger] WARNING: Ledger reset script not found: {RESET_LEDGER_SCRIPT}")
        return

    cmd = [str(VENV_PY), str(RESET_LEDGER_SCRIPT)]
    print("[ledger] Running reset_ledger_after_rebalance...")
    subprocess.run(cmd, cwd=str(PROJECT_ROOT), check=True)
    print("[ledger] Ledger reset completed.")


# ---------------------------------------------------------------------------
# 5) Guardian / stop-loss monitor control
# ---------------------------------------------------------------------------

def start_guardian() -> None:
    """
    Start the guardian (paper2 stop-loss / take-profit monitor) if not running.

    GUARDIAN_SCRIPT should be a long-running process that:
        - Loops every 2 minutes
        - Reads alpaca_paper/ledger.csv
        - Checks for stop-loss / take-profit
        - Submits exit orders
        - Logs its own output
    """
    global guardian_proc

    # If already running, don't start a second one
    if guardian_proc and guardian_proc.poll() is None:
        print(f"[guardian] Already running (pid={guardian_proc.pid})")
        return

    if not GUARDIAN_SCRIPT.exists():
        print(f"[guardian] WARNING: Guardian script not found: {GUARDIAN_SCRIPT}")
        return

    cmd = [str(VENV_PY), str(GUARDIAN_SCRIPT)]
    print("[guardian] Starting:", " ".join(cmd))

    # ⬇️ Key change: no redirection → inherit orchestrator's console
    guardian_proc = subprocess.Popen(
        cmd,
        cwd=str(PROJECT_ROOT),
        stdout=None,
        stderr=None,
    )

    print(f"[guardian] Started (pid={guardian_proc.pid})")


def stop_guardian() -> None:
    """
    Stop the guardian if it's running.
    """
    global guardian_proc

    if not guardian_proc or guardian_proc.poll() is not None:
        guardian_proc = None
        return

    print(f"[guardian] Stopping (pid={guardian_proc.pid})")
    guardian_proc.terminate()
    try:
        guardian_proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        print("[guardian] Did not exit; killing...")
        guardian_proc.kill()

    guardian_proc = None
    print("[guardian] Stopped.")


# ---------------------------------------------------------------------------
# 6) One 90-minute rebalance cycle
# ---------------------------------------------------------------------------

def one_rebalance_cycle() -> None:
    """
    One full 90-min orchestration cycle:

        1) Guardian keeps running.
        2) Run inference for all symbols (writes to logs/infer_*.csv).
        3) Run review_infers4.ipynb to rebuild S11 allocations.
        4) Stop guardian.
        5) Run allocator_once (S11-based rebalance).
        6) Reset ledger.
        7) Restart guardian.
    """
    now = datetime.now().astimezone()
    print("\n" + "=" * 72)
    print(f"[cycle] Starting 90-min cycle at {now.isoformat(timespec='seconds')}")
    print("=" * 72)

    # 1) Guardian stays running while we generate new predictions and review
    run_infer_for_all_symbols()

    # 2) Rebuild S11 allocation breakdown from all logs
    run_review_infers4()

    # 3) Pause guardian while we rebalance + reset ledger
    stop_guardian()

    # 4) Allocator: use S11 allocation CSV to rebalance portfolio
    run_allocator_once()

    # 5) Reset ledger based on new positions & basis prices
    reset_ledger_after_rebalance()

    # 6) Restart guardian with fresh ledger
    start_guardian()
    
    # Send email summary for this cycle
    try:
        print("[email] Sending cycle report email...")
        send_reports()
    except Exception as e:
        print(f"[email] ERROR sending report: {e}")

    now2 = datetime.now().astimezone()
    print(f"[cycle] Finished at {now2.isoformat(timespec='seconds')}")


# ---------------------------------------------------------------------------
# 7) Main loop
# ---------------------------------------------------------------------------

def main() -> None:
    # Optional: start guardian immediately when orchestrator launches
    start_guardian()

    # Run first cycle immediately
    one_rebalance_cycle()

    # Then every 90 minutes
    while True:
        mins = int(REBALANCE_INTERVAL_SECONDS / 60)
        print(f"[cycle] Sleeping for {mins} minutes...")
        time.sleep(REBALANCE_INTERVAL_SECONDS)
        one_rebalance_cycle()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[orchestrator] Interrupted; shutting down...")
        stop_guardian()
        sys.exit(0)
