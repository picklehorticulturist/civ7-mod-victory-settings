#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
"""
analyze_session.py — Victory Settings Session Analyzer
=======================================================
Reads a saved session file (produced by watch_logs.py --save-session)
OR scans the live log files directly, then produces a full health report
on whether the mod is working correctly.

What it checks:
    ✔ Were the DB errors we fixed (UNIQUE constraint) actually gone?
    ✔ Did the logger fire and report correct DB state?
    ✔ Were all selected victories confirmed as BLOCKED?
    ✔ Were age progression tables correctly frozen?
    ✔ Did any unexpected DB errors appear?

Usage:
    # Analyze live logs (last session)
    python tools/analyze_session.py

    # Analyze a saved session file
    python tools/analyze_session.py --session tools/session_20260601_123456.txt

    # Save report to file
    python tools/analyze_session.py --report report.txt
"""

import os
import sys
import re
import glob
import argparse
import datetime
from collections import defaultdict

# ── Paths ────────────────────────────────────────────────────────────────────

APPDATA = os.environ.get("LOCALAPPDATA", "")
CIV7_LOGS = os.path.join(
    APPDATA, "Firaxis Games",
    "Sid Meier's Civilization VII (Epic)", "Logs"
)

VS_TAG = "[VictorySettings]"

# ── ANSI ─────────────────────────────────────────────────────────────────────

class C:
    RESET  = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"
    RED    = "\033[91m"; GREEN = "\033[92m"; YELLOW = "\033[93m"; CYAN = "\033[96m"

def enable_ansi():
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.kernel32.SetConsoleMode(
            ctypes.windll.kernel32.GetStdHandle(-11), 7
        )

# ── Log reader ───────────────────────────────────────────────────────────────

def read_log(path: str) -> list[str]:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.readlines()
    except FileNotFoundError:
        return []

def collect_lines(session_file: str | None) -> dict[str, list[str]]:
    """Return dict of {source_name: [lines]}."""
    if session_file:
        lines = read_log(session_file)
        return {"session": lines}
    # Live logs
    result = {}
    for fname in ["UI.log", "Database.log", "Modding.log"]:
        path = os.path.join(CIV7_LOGS, fname)
        result[fname] = read_log(path)
    return result

# ── Extractors ────────────────────────────────────────────────────────────────

def extract_mod_lines(all_lines: dict) -> list[str]:
    out = []
    for src, lines in all_lines.items():
        for l in lines:
            if VS_TAG in l:
                out.append(l.strip())
    return out

def extract_db_errors(all_lines: dict) -> list[str]:
    out = []
    for src, lines in all_lines.items():
        if "Database.log" not in src and "session" not in src:
            continue
        for l in lines:
            if "ERROR" in l or "UNIQUE constraint" in l:
                out.append(l.strip())
    return out

# ── Checkers ─────────────────────────────────────────────────────────────────

class Check:
    def __init__(self, name: str):
        self.name   = name
        self.passed = None   # True / False / None (inconclusive)
        self.detail = ""

def check_unique_constraint_errors(db_errors: list[str]) -> Check:
    c = Check("No UNIQUE constraint errors in Database.log")
    unique_errs = [l for l in db_errors if "UNIQUE constraint" in l
                   and "REQ_VICTORY_NEVER_MET" in l]
    if unique_errs:
        c.passed = False
        c.detail = f"{len(unique_errs)} UNIQUE constraint error(s) found — requirements block is STILL being loaded multiple times!"
    elif not db_errors and not unique_errs:
        c.passed = True
        c.detail = "No UNIQUE constraint errors detected."
    else:
        c.passed = True
        c.detail = "No UNIQUE constraint errors for REQ_VICTORY_NEVER_MET."
    return c

def check_logger_fired(mod_lines: list[str]) -> Check:
    c = Check("In-game diagnostic logger ran")
    fired = any("DIAGNOSTIC REPORT" in l or "VICTORY SETTINGS MOD" in l for l in mod_lines)
    if fired:
        c.passed = True
        c.detail = "Logger ran and produced output in UI.log."
    else:
        c.passed = None
        c.detail = "No logger output found — game may not have been launched in this session, or logger script failed to load."
    return c

def check_requirement_block(mod_lines: list[str]) -> Check:
    c = Check("REQ_VICTORY_NEVER_MET block applied to DB")
    ok_lines  = [l for l in mod_lines if "REQ_VICTORY_NEVER_MET" in l and ("✔" in l or "exists" in l)]
    err_lines = [l for l in mod_lines if "REQ_VICTORY_NEVER_MET" in l and ("✖" in l or "not found" in l or "NOT applied" in l)]
    if err_lines:
        c.passed = False
        c.detail = f"Block NOT applied: {err_lines[0]}"
    elif ok_lines:
        c.passed = True
        c.detail = "Requirements and RequirementSets rows confirmed present."
    else:
        c.passed = None
        c.detail = "No logger output about requirement block — logger may not have run."
    return c

def check_victories_blocked(mod_lines: list[str]) -> Check:
    c = Check("All disabled victories confirmed BLOCKED in Victories table")
    victory_lines = [l for l in mod_lines if "VICTORY_" in l and "MODERN" in l]
    blocked   = [l for l in victory_lines if "✔ BLOCKED" in l]
    unblocked = [l for l in victory_lines if "✖ NOT BLOCKED" in l or "NOT BLOCKED" in l]

    if unblocked:
        c.passed = False
        c.detail = f"{len(unblocked)} victory/ies NOT blocked: " + " | ".join(unblocked[:3])
    elif blocked:
        c.passed = True
        c.detail = f"{len(blocked)} victory/ies confirmed blocked."
    else:
        c.passed = None
        c.detail = "No victory state lines in logger output."
    return c

def check_progression_frozen(mod_lines: list[str]) -> Check:
    c = Check("Age progression tables frozen (Points=0 where expected)")
    frozen = [l for l in mod_lines if "frozen" in l and "✔" in l]
    active = [l for l in mod_lines if "[active]" in l and (
        "AGE_PROGRESSION_PER_TURN_BASE" in l
        or "AGE_PROGRESSION_PLAYER_MILESTONE" in l
        or "AGE_PROGRESSION_FUTURE" in l
    )]
    if active:
        c.passed = False
        c.detail = f"{len(active)} progression row(s) still active when they should be frozen: " + active[0]
    elif frozen:
        c.passed = True
        c.detail = f"{len(frozen)} progression row(s) confirmed frozen."
    else:
        c.passed = None
        c.detail = "No progression state lines in logger output."
    return c

def check_no_unexpected_db_errors(db_errors: list[str]) -> Check:
    c = Check("No other unexpected DB errors")
    others = [l for l in db_errors if "victory-settings" in l.lower()
              or "victory-requirements" in l.lower()
              or "victory_never" in l.lower()]
    general_errs = [l for l in db_errors
                    if "ERROR" in l and "UNIQUE constraint" not in l]
    if others:
        c.passed = False
        c.detail = f"Mod-related DB errors: {others[0]}"
    elif general_errs:
        c.passed = None  # inconclusive — might not be our mod
        c.detail = f"{len(general_errs)} DB errors (may not be from this mod). First: {general_errs[0][:100]}"
    else:
        c.passed = True
        c.detail = "No unexpected DB errors."
    return c

# ── Report renderer ───────────────────────────────────────────────────────────

STATUS = {True: f"{C.GREEN}✔ PASS{C.RESET}", False: f"{C.RED}✖ FAIL{C.RESET}", None: f"{C.YELLOW}? INFO{C.RESET}"}

def render_report(checks: list[Check], mod_lines: list[str], db_errors: list[str]) -> str:
    lines = []

    def p(s=""): lines.append(s)

    p(f"{C.CYAN}{C.BOLD}")
    p("=" * 60)
    p("  Victory Settings Mod -- Session Analysis Report")
    p(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    p("=" * 60)
    p(f"{C.RESET}")

    # Checks
    p(f"  {C.BOLD}Health Checks{C.RESET}")
    p("  " + "─" * 55)
    all_passed = True
    for ch in checks:
        st = STATUS[ch.passed]
        p(f"  {st}  {ch.name}")
        p(f"        {C.DIM}{ch.detail}{C.RESET}")
        if ch.passed is False:
            all_passed = False
    p()

    # Overall verdict
    if all_passed:
        p(f"  {C.GREEN}{C.BOLD}Overall: MOD APPEARS TO BE WORKING CORRECTLY ✔{C.RESET}")
    else:
        p(f"  {C.RED}{C.BOLD}Overall: ISSUES DETECTED — see FAIL items above ✖{C.RESET}")
    p()

    # Raw mod log lines summary
    p(f"  {C.BOLD}Mod Logger Output ({len(mod_lines)} tagged lines){C.RESET}")
    p("  " + "─" * 55)
    if mod_lines:
        for l in mod_lines[:60]:
            # Strip tag for brevity
            clean = l.replace(VS_TAG, "").strip()
            p(f"  {C.DIM}{clean[:120]}{C.RESET}")
        if len(mod_lines) > 60:
            p(f"  {C.DIM}... and {len(mod_lines) - 60} more lines{C.RESET}")
    else:
        p(f"  {C.YELLOW}No [VictorySettings] lines found. Game may not have been launched.{C.RESET}")
    p()

    # DB errors
    p(f"  {C.BOLD}Database Errors ({len(db_errors)} total){C.RESET}")
    p("  " + "─" * 55)
    if db_errors:
        for l in db_errors[:20]:
            p(f"  {C.RED}{l[:120]}{C.RESET}")
    else:
        p(f"  {C.GREEN}No database errors found.{C.RESET}")
    p()

    return "\n".join(lines)

# ── Main ──────────────────────────────────────────────────────────────────────

def run(session_file: str | None, report_file: str | None):
    enable_ansi()

    all_lines = collect_lines(session_file)
    mod_lines = extract_mod_lines(all_lines)
    db_errors = extract_db_errors(all_lines)

    checks = [
        check_unique_constraint_errors(db_errors),
        check_logger_fired(mod_lines),
        check_requirement_block(mod_lines),
        check_victories_blocked(mod_lines),
        check_progression_frozen(mod_lines),
        check_no_unexpected_db_errors(db_errors),
    ]

    report = render_report(checks, mod_lines, db_errors)
    print(report)

    if report_file:
        # Strip ANSI for file output
        ansi_escape = re.compile(r'\033\[[0-9;]*m')
        clean = ansi_escape.sub("", report)
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(clean)
        print(f"\n  Report saved to: {C.CYAN}{report_file}{C.RESET}")

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze a Victory Settings mod session")
    parser.add_argument(
        "--session",
        help="Path to a session file saved by watch_logs.py --save-session"
    )
    parser.add_argument(
        "--report",
        help="Save the report to a file (ANSI stripped)"
    )
    args = parser.parse_args()
    run(args.session, args.report)
