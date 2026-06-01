#!/usr/bin/env python3
"""
dump_db.py — Civ7 Game Database Dumper
=======================================
Finds Civ7's SQLite databases on disk and dumps the tables that the
Victory Settings mod reads and writes, so you can inspect the exact state
of the database independently of the game's own logging.

What it dumps:
    gameplay DB  → Victories, VictoryTypes, Requirements, RequirementSets,
                   RequirementSetRequirements, AgeProgressionTurns,
                   AgeProgressionEvents, Strategies
    config DB    → Parameters (our SetupParameters entries)

Output formats: pretty console table (default), JSON (--json), CSV (--csv)

Usage:
    python tools/dump_db.py
    python tools/dump_db.py --json --out dump.json
    python tools/dump_db.py --csv --out dump.csv
    python tools/dump_db.py --db-path "C:/path/to/gameplay.db"

NOTE: The game must NOT be running when you dump (SQLite exclusive lock).
      Dump right after the game exits to capture the last session's state.
"""

import os
import sys
import json
import glob
import sqlite3
import argparse
import datetime
import csv
import io

# ── Paths ────────────────────────────────────────────────────────────────────

APPDATA = os.environ.get("LOCALAPPDATA", "")
CIV7_BASE = os.path.join(APPDATA, "Firaxis Games", "Sid Meier's Civilization VII (Epic)")

# Common locations where Civ7 writes SQLite databases
DB_SEARCH_PATHS = [
    os.path.join(CIV7_BASE, "Cache"),
    os.path.join(CIV7_BASE, "Saves"),
    os.path.join(CIV7_BASE, "Cache", "gameplay"),
    os.path.join(CIV7_BASE, "Cache", "config"),
    os.path.join(os.environ.get("TEMP", ""), "Civ7"),
]

# ── Tables we care about ─────────────────────────────────────────────────────

GAMEPLAY_QUERIES = {
    "Victories_Modern": (
        "SELECT VictoryType, EnabledByDefault, RequirementSetId "
        "FROM Victories WHERE VictoryType LIKE '%MODERN%' "
        "ORDER BY VictoryType"
    ),
    "VictoryTypes_Modern": (
        "SELECT VictoryType, PrereqRequirementSetId, CountdownDuration "
        "FROM VictoryTypes WHERE VictoryType LIKE '%MODERN%' "
        "ORDER BY VictoryType"
    ),
    "Requirements_NeverMet": (
        "SELECT RequirementId, RequirementType, Inverse "
        "FROM Requirements WHERE RequirementId = 'REQ_VICTORY_NEVER_MET'"
    ),
    "RequirementSets_NeverMet": (
        "SELECT RequirementSetId, RequirementSetType "
        "FROM RequirementSets WHERE RequirementSetId = 'REQSET_VICTORY_NEVER_MET'"
    ),
    "RequirementSetRequirements_NeverMet": (
        "SELECT RequirementSetId, RequirementId "
        "FROM RequirementSetRequirements WHERE RequirementSetId = 'REQSET_VICTORY_NEVER_MET'"
    ),
    "AgeProgressionTurns": (
        "SELECT AgeProgressionTurnType, Points FROM AgeProgressionTurns ORDER BY AgeProgressionTurnType"
    ),
    "AgeProgressionEvents": (
        "SELECT AgeProgressionEventType, Points FROM AgeProgressionEvents ORDER BY AgeProgressionEventType"
    ),
    "Strategies_Modern": (
        "SELECT LegacyPathType, MinNumConditionsNeeded, MaxNumConditionsNeeded, MinConditionPercentage "
        "FROM Strategies WHERE LegacyPathType LIKE 'LEGACY_PATH_MODERN_%' "
        "ORDER BY LegacyPathType"
    ),
    "Strategies_Antiquity": (
        "SELECT LegacyPathType, MinNumConditionsNeeded, MaxNumConditionsNeeded, MinConditionPercentage "
        "FROM Strategies WHERE LegacyPathType LIKE 'LEGACY_PATH_ANTIQUITY_%' "
        "ORDER BY LegacyPathType"
    ),
    "Strategies_Exploration": (
        "SELECT LegacyPathType, MinNumConditionsNeeded, MaxNumConditionsNeeded, MinConditionPercentage "
        "FROM Strategies WHERE LegacyPathType LIKE 'LEGACY_PATH_EXPLORATION_%' "
        "ORDER BY LegacyPathType"
    ),
}

CONFIG_QUERIES = {
    "Parameters_VictorySettings": (
        "SELECT ParameterID, Name, Domain, DefaultValue, ConfigurationKey, SortIndex "
        "FROM Parameters WHERE ParameterID IN ("
        "  'MilitaryVictoryEnabled','ScienceVictoryEnabled',"
        "  'EconomicVictoryEnabled','CultureVictoryEnabled',"
        "  'AgeProgressionFromTurnCounterEnabled','AgeProgressionFromPlayerEliminatedEnabled'"
        ") ORDER BY SortIndex"
    ),
}

# ── DB finder ────────────────────────────────────────────────────────────────

def find_db_files():
    """Search common locations for Civ7 SQLite databases."""
    found = []
    patterns = ["*.db", "*.sqlite", "gameplay", "config", "game"]
    for base in DB_SEARCH_PATHS:
        if not os.path.isdir(base):
            continue
        for pat in patterns:
            for f in glob.glob(os.path.join(base, "**", pat), recursive=True):
                if os.path.isfile(f) and f not in found:
                    found.append(f)
    return found

def probe_db(path: str):
    """Return list of table names if this is a valid SQLite DB we care about."""
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)
        cur = con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = {row[0] for row in cur.fetchall()}
        con.close()
        return tables
    except Exception:
        return set()

def classify_db(tables: set):
    """Identify whether this is a gameplay or config database."""
    gameplay_indicators = {"Victories", "VictoryTypes", "AgeProgressionTurns", "Strategies"}
    config_indicators   = {"Parameters", "GameSetup"}
    if gameplay_indicators & tables:
        return "gameplay"
    if config_indicators & tables:
        return "config"
    return None

# ── Query runner ─────────────────────────────────────────────────────────────

def run_query(path: str, sql: str):
    """Run a query against a read-only SQLite DB. Returns (columns, rows)."""
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)
        con.row_factory = sqlite3.Row
        cur = con.execute(sql)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        con.close()
        return cols, [dict(r) for r in rows]
    except sqlite3.OperationalError as e:
        return [], f"ERROR: {e}"
    except Exception as e:
        return [], f"ERROR: {e}"

# ── Formatters ────────────────────────────────────────────────────────────────

def print_table(label: str, cols, rows):
    SEP = "─"
    print(f"\n  ┌─ {label} {'─' * max(0, 55 - len(label))}┐")
    if isinstance(rows, str):
        print(f"  │  {rows}")
        print(f"  └{'─' * 57}┘")
        return
    if not rows:
        print("  │  (no rows)")
        print(f"  └{'─' * 57}┘")
        return
    # column widths
    widths = {c: len(c) for c in cols}
    for r in rows:
        for c in cols:
            widths[c] = max(widths[c], len(str(r.get(c, ""))))
    header = "  │  " + "  ".join(c.ljust(widths[c]) for c in cols)
    divider = "  │  " + "  ".join(SEP * widths[c] for c in cols)
    print(header)
    print(divider)
    for r in rows:
        print("  │  " + "  ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols))
    print(f"  └{'─' * 57}┘")

def annotate_rows(label: str, rows):
    """Add a human-readable status annotation to well-known tables."""
    if "Victories_Modern" in label:
        for r in rows:
            blocked = r.get("RequirementSetId") == "REQSET_VICTORY_NEVER_MET"
            enabled = r.get("EnabledByDefault")
            r["_status"] = "✔ BLOCKED" if blocked else ("ENABLED" if enabled else "disabled-default")
    if "VictoryTypes_Modern" in label:
        for r in rows:
            prereq = r.get("PrereqRequirementSetId") == "REQSET_VICTORY_NEVER_MET"
            r["_status"] = "✔ prereq blocked" if prereq else "✖ prereq NOT blocked"
    if "AgeProgressionTurns" in label or "AgeProgressionEvents" in label:
        for r in rows:
            pts = r.get("Points", 1)
            r["_status"] = "✔ frozen" if (pts == 0 or pts == "0") else "active"
    if "Strategies_" in label:
        for r in rows:
            mn = r.get("MinNumConditionsNeeded", 0)
            r["_status"] = "✔ AI blocked" if (mn is not None and int(mn) >= 100) else "✖ AI active"
    return rows

# ── Main ─────────────────────────────────────────────────────────────────────

def run(db_path: str | None, output_format: str, out_file: str | None):
    print("\n  Civ7 Victory Settings — Database Dumper")
    print("  " + "=" * 55)

    dump = {
        "timestamp": datetime.datetime.now().isoformat(),
        "db_path": None,
        "gameplay": {},
        "config": {},
    }

    # Find or use the provided DB path
    if db_path:
        targets = {"gameplay": db_path, "config": db_path}
        print(f"  Using explicit path: {db_path}\n")
    else:
        print("  Searching for Civ7 SQLite databases...\n")
        found = find_db_files()
        targets = {}
        for f in found:
            tables = probe_db(f)
            kind = classify_db(tables)
            if kind and kind not in targets:
                targets[kind] = f
                print(f"  Found {kind:8s} DB: {f}")

        if not targets:
            print("\n  ✖ No Civ7 databases found.")
            print("    • The game writes them dynamically — run this after a game session.")
            print("    • Or specify a path: python tools/dump_db.py --db-path path/to/file.db")
            sys.exit(1)

    print()

    # Run gameplay queries
    if "gameplay" in targets:
        gpath = targets["gameplay"]
        dump["db_path"] = gpath
        print(f"  Gameplay DB: {gpath}")
        for label, sql in GAMEPLAY_QUERIES.items():
            cols, rows = run_query(gpath, sql)
            if isinstance(rows, str):
                dump["gameplay"][label] = {"error": rows}
                if output_format == "console":
                    print_table(label, [], rows)
            else:
                rows = annotate_rows(label, rows)
                dump["gameplay"][label] = rows
                if output_format == "console":
                    print_table(label, cols + (["_status"] if rows and "_status" in rows[0] else []), rows)

    # Run config queries
    if "config" in targets:
        cpath = targets["config"]
        print(f"\n  Config DB:   {cpath}")
        for label, sql in CONFIG_QUERIES.items():
            cols, rows = run_query(cpath, sql)
            if isinstance(rows, str):
                dump["config"][label] = {"error": rows}
                if output_format == "console":
                    print_table(label, [], rows)
            else:
                dump["config"][label] = rows
                if output_format == "console":
                    print_table(label, cols, rows)

    # Output
    if output_format == "json":
        content = json.dumps(dump, indent=2)
        if out_file:
            with open(out_file, "w") as f:
                f.write(content)
            print(f"\n  JSON saved to: {out_file}")
        else:
            print("\n" + content)

    elif output_format == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        for section in ["gameplay", "config"]:
            for label, rows in dump[section].items():
                if isinstance(rows, list) and rows:
                    writer.writerow([f"### {label} ###"])
                    writer.writerow(rows[0].keys())
                    for r in rows:
                        writer.writerow(r.values())
                    writer.writerow([])
        content = buf.getvalue()
        if out_file:
            with open(out_file, "w", newline="") as f:
                f.write(content)
            print(f"\n  CSV saved to: {out_file}")
        else:
            print(content)

    print("\n  Done.\n")

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dump Civ7 victory-settings-relevant DB tables")
    parser.add_argument("--db-path", help="Explicit path to a Civ7 SQLite .db file")
    parser.add_argument("--json",    action="store_true", help="Output as JSON")
    parser.add_argument("--csv",     action="store_true", help="Output as CSV")
    parser.add_argument("--out",     help="Output file path (default: stdout)")
    args = parser.parse_args()

    fmt = "json" if args.json else ("csv" if args.csv else "console")
    run(args.db_path, fmt, args.out)
