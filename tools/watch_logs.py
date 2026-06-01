#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
"""
watch_logs.py — Real-time Civ7 Victory Settings Mod Log Watcher
================================================================
Tails UI.log, Database.log, and Modding.log simultaneously during a gameplay
session. Highlights [VictorySettings] lines, DB errors, and mod events.

Usage:
    python tools/watch_logs.py
    python tools/watch_logs.py --log-dir "C:/path/to/Logs"
    python tools/watch_logs.py --save-session  (also writes session_YYYYMMDD_HHMMSS.txt)

Output is colour-coded:
    GREEN  — mod OK / success confirmations
    RED    — errors (UNIQUE constraint, NOT blocked, etc.)
    YELLOW — warnings
    CYAN   — section headers / diagnostic blocks
    WHITE  — raw DB/Modding lines for context
"""

import os
import sys
import time
import datetime
import argparse
import re

# ── Paths ────────────────────────────────────────────────────────────────────

DEFAULT_LOG_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "Firaxis Games",
    "Sid Meier's Civilization VII (Epic)",
    "Logs",
)

WATCH_FILES = ["UI.log", "Database.log", "Modding.log"]

# ── ANSI colours (Windows 10+ supports these natively) ───────────────────────

class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    WHITE  = "\033[97m"
    DIM    = "\033[2m"

def enable_ansi():
    """Enable ANSI escape codes on Windows."""
    if sys.platform == "win32":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

# ── Classifier ───────────────────────────────────────────────────────────────

VS_TAG = "[VictorySettings]"

def classify_line(filename: str, line: str):
    """Return (colour, prefix, should_print)."""
    l = line.strip()
    if not l:
        return None, None, False

    # Our mod's tagged output — always print, colour by content
    if VS_TAG in l:
        if any(x in l for x in ["✖", "ERROR", "NOT BLOCKED", "not found", "failed", "FATAL"]):
            return C.RED,    "MOD-ERR", True
        if any(x in l for x in ["✔", "exists", "frozen", "OK", "blocked", "BLOCKED"]):
            return C.GREEN,  "MOD-OK ", True
        if any(x in l for x in ["⚠", "warn", "WARN", "NULL", "empty"]):
            return C.YELLOW, "MOD-WRN", True
        if any(x in l for x in ["═══", "┌───", "└───", "ℹ", "REPORT", "START", "END"]):
            return C.CYAN,   "MOD-INF", True
        return C.WHITE, "MOD    ", True

    # Database errors — always print
    if filename == "Database.log":
        if "UNIQUE constraint failed" in l:
            return C.RED, "DB-ERR ", True
        if "ERROR" in l:
            return C.RED, "DB-ERR ", True
        if "victory-requirements-block" in l or "REQ_VICTORY_NEVER_MET" in l:
            return C.YELLOW, "DB-WRN ", True
        if "victory-settings" in l or "VictorySettings" in l:
            return C.CYAN, "DB-MOD ", True
        # Skip routine DB rebuild lines to reduce noise
        if any(x in l for x in ["Rebuilding database", "Passed Validation",
                                  "UpdateAggregateData", "Validating Foreign"]):
            return C.DIM, "DB     ", False   # suppress
        return C.DIM, "DB     ", False       # suppress other DB noise

    # Modding.log — show mod registration lines
    if filename == "Modding.log":
        if "victory-settings" in l.lower():
            return C.CYAN, "MOD-REG", True
        if any(x in l for x in ["ERROR", "Failed", "failed"]):
            return C.RED, "MOD-ERR", True
        return None, None, False   # skip most modding noise

    return None, None, False

# ── Tail manager ─────────────────────────────────────────────────────────────

class FileTailer:
    def __init__(self, path: str):
        self.path = path
        self.name = os.path.basename(path)
        self._pos  = 0
        self._inode = None
        # Start at end of file so we only see new lines
        try:
            self._pos = os.path.getsize(path)
        except FileNotFoundError:
            pass

    def read_new_lines(self):
        """Yield new lines since last read, handle log rotation."""
        try:
            stat = os.stat(self.path)
        except FileNotFoundError:
            return

        # Detect log rotation (new file written)
        if self._inode is not None and stat.st_ino != self._inode:
            self._pos = 0
        self._inode = stat.st_ino

        if stat.st_size < self._pos:
            # File was truncated/rotated
            self._pos = 0

        if stat.st_size == self._pos:
            return

        try:
            with open(self.path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self._pos)
                for line in f:
                    yield line.rstrip("\r\n")
                self._pos = f.tell()
        except (OSError, PermissionError):
            pass

# ── Main loop ─────────────────────────────────────────────────────────────────

def format_line(ts: str, filename: str, colour: str, prefix: str, line: str) -> str:
    name = filename.replace(".log", "").ljust(8)
    return f"{C.DIM}{ts}{C.RESET} {colour}{C.BOLD}{prefix}{C.RESET} {C.DIM}[{name}]{C.RESET} {colour}{line}{C.RESET}"

def run(log_dir: str, save_session: bool, poll_interval: float = 0.25):
    enable_ansi()

    print(f"{C.CYAN}{C.BOLD}")
    print("=" * 60)
    print("  Civ7 Victory Settings -- Real-time Log Watcher")
    print("=" * 60)
    print(f"{C.RESET}")
    print(f"  Log dir : {C.CYAN}{log_dir}{C.RESET}")
    print(f"  Watching: {', '.join(WATCH_FILES)}")
    print(f"  Filter  : {C.GREEN}{VS_TAG}{C.RESET} + DB errors + mod events")
    print(f"  Press Ctrl+C to stop.\n")

    session_lines = []
    session_file = None
    if save_session:
        ts_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        session_file = os.path.join(
            os.path.dirname(__file__), f"session_{ts_str}.txt"
        )
        print(f"  Session : {C.CYAN}{session_file}{C.RESET}\n")

    tailers = {}
    for fname in WATCH_FILES:
        path = os.path.join(log_dir, fname)
        tailers[fname] = FileTailer(path)

    try:
        while True:
            for fname, tailer in tailers.items():
                for line in tailer.read_new_lines():
                    colour, prefix, should_print = classify_line(fname, line)
                    if should_print:
                        ts = datetime.datetime.now().strftime("%H:%M:%S")
                        formatted = format_line(ts, fname, colour, prefix, line)
                        print(formatted)
                        if save_session:
                            session_lines.append(f"{ts} [{fname}] {line}")
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        print(f"\n{C.CYAN}Stopped.{C.RESET}")

    if save_session and session_lines:
        with open(session_file, "w", encoding="utf-8") as f:
            f.write(f"Victory Settings Log Session — {datetime.datetime.now().isoformat()}\n")
            f.write("=" * 70 + "\n\n")
            f.write("\n".join(session_lines))
        print(f"Session saved to: {C.CYAN}{session_file}{C.RESET}")

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Real-time Civ7 mod log watcher")
    parser.add_argument(
        "--log-dir",
        default=DEFAULT_LOG_DIR,
        help=f"Path to Civ7 Logs folder (default: {DEFAULT_LOG_DIR})"
    )
    parser.add_argument(
        "--save-session",
        action="store_true",
        help="Save all matched lines to a timestamped session file"
    )
    parser.add_argument(
        "--poll",
        type=float,
        default=0.25,
        help="Poll interval in seconds (default: 0.25)"
    )
    args = parser.parse_args()

    if not os.path.isdir(args.log_dir):
        print(f"{C.RED}ERROR: Log directory not found: {args.log_dir}{C.RESET}")
        print("Use --log-dir to specify the correct path.")
        sys.exit(1)

    run(args.log_dir, args.save_session, args.poll)
