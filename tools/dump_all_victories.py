#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dump_all_victories.py — Full victory / age dump (ALL ages, no Modern filter)
============================================================================
Civ7 1.4.0 made victories fire as early as the Exploration age. The other
tools only inspect '%MODERN%' rows, so an Exploration-age win is invisible to
them. This script dumps the COMPLETE Victories / VictoryTypes / AgeProgressions
tables (every column, every age) plus anything that looks like a victory-unlock
threshold, so the exact row names + columns can be confirmed before writing the
mod fix.

Read-only. Safe to run while the game is running.

USAGE (Windows, from the mod folder):
    python tools/dump_all_victories.py

It writes a file `victory_dump.txt` next to the script AND prints to screen.
Send / paste the contents of victory_dump.txt back.

If it can't find the database, see the printed instructions (you need
`CopyDatabasesToDisk 1` in AppOptions.txt, then launch the game once).
"""

import os, sys, io, glob, sqlite3, datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

APPDATA = os.environ.get("LOCALAPPDATA", "")
CIV7    = os.path.join(APPDATA, "Firaxis Games", "Sid Meier's Civilization VII (Epic)")

# Most reliable source first, then fall back to a recursive search.
CANDIDATES = [
    os.path.join(CIV7, "Debug", "gameplay-copy.sqlite"),
    os.path.join(CIV7, "Cache", "gameplay.sqlite"),
]
SEARCH_DIRS = [os.path.join(CIV7, "Debug"), os.path.join(CIV7, "Cache"), os.path.join(CIV7, "Saves")]


def find_db(explicit=None):
    if explicit:
        return explicit if os.path.isfile(explicit) else None
    for c in CANDIDATES:
        if os.path.isfile(c):
            return c
    # recursive fallback: any sqlite that has a Victories table
    for d in SEARCH_DIRS:
        if not os.path.isdir(d):
            continue
        for f in glob.glob(os.path.join(d, "**", "*.sqlite"), recursive=True) + \
                 glob.glob(os.path.join(d, "**", "*.db"), recursive=True):
            try:
                con = sqlite3.connect(f"file:{f}?mode=ro", uri=True, timeout=2)
                names = {r[0] for r in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")}
                con.close()
                if "Victories" in names:
                    return f
            except Exception:
                pass
    return None


def main():
    out = []
    def w(s=""):
        out.append(s)

    explicit = sys.argv[1] if len(sys.argv) > 1 else None
    db = find_db(explicit)

    w("=" * 70)
    w("  Civ7 — FULL Victory / Age dump (all ages)")
    w(f"  {datetime.datetime.now():%Y-%m-%d %H:%M:%S}")
    w("=" * 70)

    if not db:
        w("")
        w("  DATABASE NOT FOUND.")
        w("  To create it:")
        w("   1. Open this file in a text editor:")
        w(f"      {os.path.join(CIV7, 'AppOptions.txt')}")
        w("   2. Add a line (if not already present):  CopyDatabasesToDisk 1")
        w("   3. Save, launch Civ7, LOAD a save that's in the Exploration age,")
        w("      then alt-tab out and re-run this script (no need to quit the game).")
        w("")
        print("\n".join(out))
        return

    w(f"  DB: {db}")
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=3)
    con.row_factory = sqlite3.Row

    def dump_select(title, sql):
        w("")
        w("-" * 70)
        w(f"  {title}")
        w("-" * 70)
        try:
            cur = con.execute(sql)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            if not rows:
                w("  (no rows)")
                return
            w("  COLUMNS: " + " | ".join(cols))
            for r in rows:
                w("  " + " | ".join(f"{c}={r[c]}" for c in cols))
        except Exception as e:
            w(f"  ERROR: {e}")

    def dump_schema(table):
        w("")
        w(f"  SCHEMA {table}:")
        try:
            cols = con.execute(f"PRAGMA table_info({table})").fetchall()
            w("    " + ", ".join(c[1] for c in cols))
        except Exception as e:
            w(f"    ERROR: {e}")

    # Full schemas so we see any new 1.4.0 columns (FinalAge / StartingAge / etc.)
    for t in ("Victories", "VictoryTypes", "AgeProgressions"):
        dump_schema(t)

    # ALL victory rows, every age, every column
    dump_select("Victories — ALL rows (every age)",
                "SELECT * FROM Victories ORDER BY VictoryType")
    dump_select("VictoryTypes — ALL rows (every age)",
                "SELECT * FROM VictoryTypes ORDER BY VictoryType")
    dump_select("AgeProgressions — ALL rows (every age)",
                "SELECT * FROM AgeProgressions ORDER BY AgeProgressionType")

    # Strategies for the exploration legacy paths (what the mod already touches)
    dump_select("Strategies — Exploration legacy paths",
                "SELECT LegacyPathType, MinNumConditionsNeeded, MaxNumConditionsNeeded, "
                "MinConditionPercentage FROM Strategies "
                "WHERE LegacyPathType LIKE 'LEGACY_PATH_EXPLORATION_%' ORDER BY LegacyPathType")

    # Anything that looks like the new 50%-unlock / score-multiplier threshold.
    # These live in a parameters-style table; we probe a few likely names.
    for tbl in ("GlobalParameters", "Parameters", "VictoryProgressRequirements",
                "AgeVictoryRequirements"):
        try:
            con.execute(f"SELECT 1 FROM {tbl} LIMIT 1")
        except Exception:
            continue
        dump_select(f"{tbl} — victory/age threshold rows",
                    f"SELECT * FROM {tbl} WHERE "
                    f"CAST({_first_text_col(con, tbl)} AS TEXT) LIKE '%VICTORY%' "
                    f"OR CAST({_first_text_col(con, tbl)} AS TEXT) LIKE '%AGE_PROGRESS%'")

    con.close()
    text = "\n".join(out)
    print(text)
    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "victory_dump.txt")
    try:
        with open(dest, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"\n  >> Saved to: {dest}")
        print("  >> Send/paste the contents of that file back.")
    except Exception as e:
        print(f"\n  (could not write file: {e} — just copy the text above)")


def _first_text_col(con, tbl):
    """Best-effort: the PK / first column to LIKE-match against."""
    cols = con.execute(f"PRAGMA table_info({tbl})").fetchall()
    return cols[0][1] if cols else "rowid"


if __name__ == "__main__":
    main()
