#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, io, sqlite3, os, datetime, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

APPDATA = os.environ.get("LOCALAPPDATA", "")
CIV7    = os.path.join(APPDATA, "Firaxis Games", "Sid Meier's Civilization VII (Epic)")
DB_PATH = os.path.join(CIV7, "Debug", "gameplay-copy.sqlite")
LOGS    = os.path.join(CIV7, "Logs")

class C:
    R='\033[0m'; B='\033[1m'; DIM='\033[2m'
    RED='\033[91m'; GRN='\033[92m'; YLW='\033[93m'; CYN='\033[96m'

def enable_ansi():
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.kernel32.SetConsoleMode(ctypes.windll.kernel32.GetStdHandle(-11), 7)

def q(sql):
    try:
        con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=3)
        con.row_factory = sqlite3.Row
        rows = [dict(r) for r in con.execute(sql).fetchall()]
        con.close()
        return rows
    except Exception as e:
        return f"ERROR: {e}"

def p(s=""): print(s)

def header(title):
    p(f"\n{C.CYN}{C.B}  {title}{C.R}")
    p(f"  {'─'*55}")

def row_status(label, ok, detail=""):
    icon = f"{C.GRN}PASS{C.R}" if ok is True else f"{C.RED}FAIL{C.R}" if ok is False else f"{C.YLW}INFO{C.R}"
    p(f"  [{icon}]  {label}")
    if detail: p(f"          {C.DIM}{detail}{C.R}")

enable_ansi()
p(f"\n{C.B}{'='*60}{C.R}")
p(f"{C.B}  Civ7 Victory Settings -- Live DB Check{C.R}")
p(f"{C.B}  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{C.R}")
p(f"{C.B}{'='*60}{C.R}")

# ── DB file check ──────────────────────────────────────────────────────────────
header("Database File")
if not os.path.exists(DB_PATH):
    p(f"  {C.RED}NOT FOUND: {DB_PATH}{C.R}")
    p(f"  {C.YLW}Ensure AppOptions.txt has 'CopyDatabasesToDisk 1' and game was restarted.{C.R}")
    sys.exit(1)

sz    = os.path.getsize(DB_PATH)
mtime = datetime.datetime.fromtimestamp(os.path.getmtime(DB_PATH)).strftime("%H:%M:%S")
p(f"  {C.GRN}Found:{C.R} {DB_PATH}")
p(f"  {C.DIM}Size: {sz:,} bytes   Last modified: {mtime}{C.R}")

# ── Victories ──────────────────────────────────────────────────────────────────
header("Victories (Modern Age)")
rows = q("SELECT VictoryType, EnabledByDefault, RequirementSetId FROM Victories WHERE VictoryType LIKE '%MODERN%' ORDER BY VictoryType")
if isinstance(rows, str):
    p(f"  {C.RED}{rows}{C.R}")
else:
    for r in rows:
        blocked = r["RequirementSetId"] == "REQSET_VICTORY_NEVER_MET"
        tag = f"{C.GRN}BLOCKED{C.R}" if blocked else f"{C.RED}NOT BLOCKED{C.R}"
        p(f"  [{tag}]  {r['VictoryType']}  EnabledByDefault={r['EnabledByDefault']}  ReqSet={r['RequirementSetId']}")

# ── VictoryTypes ───────────────────────────────────────────────────────────────
header("VictoryTypes (Prereq + Countdown)")
rows = q("SELECT VictoryType, PrereqRequirementSetId, CountdownDuration FROM VictoryTypes WHERE VictoryType LIKE '%MODERN%' ORDER BY VictoryType")
if isinstance(rows, str):
    p(f"  {C.RED}{rows}{C.R}")
else:
    for r in rows:
        blocked = r["PrereqRequirementSetId"] == "REQSET_VICTORY_NEVER_MET"
        tag = f"{C.GRN}BLOCKED{C.R}" if blocked else f"{C.RED}NOT BLOCKED{C.R}"
        p(f"  [{tag}]  {r['VictoryType']}  Prereq={r['PrereqRequirementSetId']}  Countdown={r['CountdownDuration']}")

# ── Requirement block ──────────────────────────────────────────────────────────
header("Requirement Block (REQ_VICTORY_NEVER_MET)")
reqs = q("SELECT RequirementId, RequirementType, Inverse FROM Requirements WHERE RequirementId='REQ_VICTORY_NEVER_MET'")
sets = q("SELECT RequirementSetId, RequirementSetType FROM RequirementSets WHERE RequirementSetId='REQSET_VICTORY_NEVER_MET'")
link = q("SELECT RequirementSetId, RequirementId FROM RequirementSetRequirements WHERE RequirementSetId='REQSET_VICTORY_NEVER_MET'")
row_status("REQ_VICTORY_NEVER_MET in Requirements",   isinstance(reqs, list) and len(reqs) > 0, str(reqs))
row_status("REQSET_VICTORY_NEVER_MET in RequirementSets", isinstance(sets, list) and len(sets) > 0, str(sets))
row_status("RequirementSetRequirements link",         isinstance(link, list) and len(link) > 0, str(link))

# ── Age progression ────────────────────────────────────────────────────────────
header("AgeProgressionTurns")
rows = q("SELECT AgeProgressionTurnType, Points FROM AgeProgressionTurns")
if isinstance(rows, str):
    p(f"  {C.RED}{rows}{C.R}")
elif not rows:
    p(f"  {C.YLW}(empty){C.R}")
else:
    for r in rows:
        frozen = str(r["Points"]) == "0"
        tag = f"{C.GRN}frozen{C.R}" if frozen else f"{C.YLW}ACTIVE{C.R}"
        p(f"  [{tag}]  {r['AgeProgressionTurnType']}  Points={r['Points']}")

header("Age Bar MaxPoints (Modern Age — AgeEndingDisabled)")
rows = q("SELECT MaxPoints_Abbreviated, MaxPoints_Standard, MaxPoints_Long FROM AgeProgressions WHERE AgeType='AGE_MODERN'")
if isinstance(rows, str):
    p(f"  {C.RED}{rows}{C.R}")
elif not rows:
    p(f"  {C.YLW}(no Modern Age row){C.R}")
else:
    r = rows[0]
    MAX = 2147483647
    for col, val in r.items():
        disabled = val == MAX
        tag = f"{C.GRN}DISABLED (never fills){C.R}" if disabled else f"{C.RED}ACTIVE = {val}{C.R}"
        p(f"  [{tag}]  {col}")

header("VICTORY_SCORE (score/age-end victory)")
rows_v = q("SELECT VictoryType, RequirementSetId FROM Victories WHERE VictoryType='VICTORY_SCORE'")
rows_vt = q("SELECT VictoryType, PrereqRequirementSetId, CountdownDuration FROM VictoryTypes WHERE VictoryType='VICTORY_SCORE'")
if isinstance(rows_v, list) and rows_v:
    r = rows_v[0]
    blocked = r["RequirementSetId"] == "REQSET_VICTORY_NEVER_MET"
    tag = f"{C.GRN}BLOCKED{C.R}" if blocked else f"{C.RED}NOT BLOCKED{C.R}"
    p(f"  [{tag}]  Victories.RequirementSetId = {r['RequirementSetId']}")
if isinstance(rows_vt, list) and rows_vt:
    r = rows_vt[0]
    blocked = r["PrereqRequirementSetId"] == "REQSET_VICTORY_NEVER_MET"
    tag = f"{C.GRN}BLOCKED{C.R}" if blocked else f"{C.RED}NOT BLOCKED{C.R}"
    p(f"  [{tag}]  VictoryTypes.PrereqRequirementSetId = {r['PrereqRequirementSetId']}  CountdownDuration={r['CountdownDuration']}")

# ── AI Strategies ──────────────────────────────────────────────────────────────
header("Strategies (Modern Countdown AI)")
rows = q("SELECT StrategyType, CountdownVictoryType, MinNumConditionsNeeded, MaxNumConditionsNeeded FROM Strategies WHERE CountdownVictoryType LIKE '%MODERN%' GROUP BY CountdownVictoryType ORDER BY CountdownVictoryType")
if isinstance(rows, str):
    p(f"  {C.RED}{rows}{C.R}")
elif not rows:
    p(f"  {C.YLW}(no rows){C.R}")
else:
    for r in rows:
        p(f"  {r['CountdownVictoryType']}  Strategy={r['StrategyType']}  Min={r['MinNumConditionsNeeded']}  Max={r['MaxNumConditionsNeeded']}")

# ── Database errors ────────────────────────────────────────────────────────────
header("Database.log Errors")
try:
    lines = open(os.path.join(LOGS, "Database.log"), encoding="utf-8", errors="replace").readlines()
    errs  = [l.strip() for l in lines if "ERROR" in l]
    mod_e = [l for l in errs if any(x in l for x in ["VICTORY_NEVER_MET","victory-req","UNIQUE constraint"])]
    row_status("No mod-related DB errors", len(mod_e) == 0,
               f"{len(errs)} total errors, {len(mod_e)} mod-related")
    for l in mod_e[:3]: p(f"    {C.RED}{l}{C.R}")
except Exception as e:
    p(f"  {C.YLW}Could not read: {e}{C.R}")

# ── Logger output ──────────────────────────────────────────────────────────────
header("[VictorySettings] Logger Lines in UI.log")
try:
    lines  = open(os.path.join(LOGS, "UI.log"), encoding="utf-8", errors="replace").readlines()
    vs     = [l.strip() for l in lines if "[VictorySettings]" in l]
    if vs:
        p(f"  {C.GRN}Logger fired — {len(vs)} lines{C.R}")
        for l in vs[:25]:
            clean = re.sub(r'.*\[VictorySettings\]\s*', '', l)
            col   = C.GRN if any(x in l for x in ['blocked','BLOCKED','frozen','exists','PASS']) else \
                    C.RED if any(x in l for x in ['NOT BLOCKED','not found','ERROR','FAIL']) else C.DIM
            p(f"  {col}{clean}{C.R}")
    else:
        p(f"  {C.YLW}Logger has not fired this session yet.{C.R}")
except Exception as e:
    p(f"  {C.YLW}Could not read: {e}{C.R}")

p(f"\n{C.B}{'='*60}{C.R}\n")
