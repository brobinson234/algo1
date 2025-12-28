"""
email_reports.py

Send key Algo1 report files via Gmail.

Requires these env vars to be set (DO NOT hard-code your real password):
    REPORT_GMAIL_USER        = your full Gmail address
    REPORT_GMAIL_APP_PASSWORD= an app password for that account

Gmail SMTP:
    - Enable 2FA on the account.
    - Create an "App password" for "Mail".
"""

from __future__ import annotations
from datetime import datetime, time as dtime, timezone  # <-- added time as dtime

import os
import mimetypes
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from datetime import datetime


# ---------- Config ----------

from pathlib import Path
# ... you already have this line:
PROJECT_ROOT = Path(__file__).resolve().parent

OUT_DIR = PROJECT_ROOT / "out"
FIGS_DIR = OUT_DIR / "figs"

# New logs/out dirs where review_infers4 seems to be writing charts
LOGS_OUT_DIR = PROJECT_ROOT / "logs" / "out"
LOGS_FIGS_DIR = LOGS_OUT_DIR / "figs"

# Adjust this list to whatever you want mailed
def _collect_attachments() -> list[Path]:
    """Collect CSV + PNG files we want to email."""
    files: list[Path] = []

    # --- Core CSVs ---
    csv_candidates = [
        PROJECT_ROOT / "alpaca_paper" / "ledger.csv",
        # PROJECT_ROOT / "alpaca_paper" / "guardian_actions.csv",
    ]
    for p in csv_candidates:
        if p.exists():
            files.append(p)
            print(f"[email_reports] Attached {p.name}")
        else:
            print(f"[email_reports] Attachment missing, skipping: {p}")

    # --- Stable allocation pies for S11, S12, S13 (ALL & SELECT) ---
    pie_names = [
        "s11_allocation_pie.png",
        "s11_allocation_select_pie.png",
        "s12_allocation_pie.png",
        "s12_allocation_select_pie.png",
        "s13_allocation_pie.png",
        "s13_allocation_select_pie.png",
    ]

    for name in pie_names:
        # Prefer logs/out, fall back to out
        candidates = [
            LOGS_OUT_DIR / name,
            OUT_DIR / name,
        ]
        found = False
        for p in candidates:
            if p.exists():
                files.append(p)
                print(f"[email_reports] Attached {p.name} from {p.parent}")
                found = True
                break
        if not found:
            print(f"[email_reports] Pie missing, skipping: {candidates[0]} and {candidates[1]}")

    # --- Equity & CAGR/MaxDD charts for ALL / SELECT ---
    fig_names = [
        "equity_curves_all.png",
        # "cagr_maxdd_all.png",
        "equity_curves_select.png",
        # "cagr_maxdd_select.png",
    ]
    for name in fig_names:
        # Prefer logs/out/figs, fall back to out/figs
        candidates = [
            LOGS_FIGS_DIR / name,
            FIGS_DIR / name,
        ]
        found = False
        for p in candidates:
            if p.exists():
                files.append(p)
                print(f"[email_reports] Attached {p.name} from {p.parent}")
                found = True
                break
        if not found:
            print(f"[email_reports] Figure missing, skipping: {candidates[0]} and {candidates[1]}")

    return files



# Where to send
DEFAULT_TO = ["brobinson234@gmail.com"]  # <- change this


def build_message(
    subject: str,
    body: str,
    to_addrs: list[str],
    attachments: list[Path],
) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ["REPORT_GMAIL_USER"]
    msg["To"] = ", ".join(to_addrs)
    msg.set_content(body)

    for path in attachments:
        if not path.exists():
            print(f"[email_reports] Attachment missing, skipping: {path}")
            continue

        ctype, encoding = mimetypes.guess_type(str(path))
        if ctype is None or encoding is not None:
            ctype = "application/octet-stream"
        maintype, subtype = ctype.split("/", 1)

        with open(path, "rb") as f:
            data = f.read()

        msg.add_attachment(
            data,
            maintype=maintype,
            subtype=subtype,
            filename=path.name,
        )
        print(f"[email_reports] Attached {path.name}")

    return msg


def send_reports() -> None:
    user = os.getenv("REPORT_GMAIL_USER")
    pwd = os.getenv("REPORT_GMAIL_APP_PASSWORD")
    if not user or not pwd:
        print("[email_reports] REPORT_GMAIL_USER / REPORT_GMAIL_APP_PASSWORD not set; skipping email.")
        return

    now = datetime.now()
    subject = f"[Algo1] Cycle report {now.strftime('%Y-%m-%d %H:%M')}"
    body = (
        "Automated Algo1 report.\n\n"
        "Attached:\n"
        " - Latest S11 allocation CSV\n"
        " - Current ledger.csv\n"
        " - guardian_actions.csv (if present)\n"
        " - S11 allocation pie chart (latest)\n"
        #" - Equity curves and CAGR/MaxDD charts (ALL/SELECT, if present)\n\n"
        f"Timestamp: {now.isoformat(timespec='seconds')}"
    )


    attachments = _collect_attachments()
    msg = build_message(subject, body, DEFAULT_TO, attachments)


    context = ssl.create_default_context()
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls(context=context)
        server.login(user, pwd)
        server.send_message(msg)

    print("[email_reports] Report email sent.")


if __name__ == "__main__":
    send_reports()
