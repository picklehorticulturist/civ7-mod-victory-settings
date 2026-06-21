# Victory Settings — Developer Tools

Python tools for inspecting and debugging the `civ7-mod-victory-settings` mod.

> **End users do not need these tools.** The mod works silently — these are for developers verifying the mod applied correctly.

---

## Requirements

- Python 3.10+
- No third-party packages — standard library only

---

## Quick Start

```bash
# While the game is running — instant live DB check (recommended)
python tools/check_now.py

# Real-time log watcher (start before launching the game)
python tools/watch_logs.py --save-session

# Full session health report (after playing)
python tools/analyze_session.py --report report.txt
```

---

## One-Time Setup: Enable Live DB Access

Add this line to `AppOptions.txt`:
```
%LOCALAPPDATA%\Firaxis Games\Sid Meier's Civilization VII (Epic)\AppOptions.txt
```
```ini
CopyDatabasesToDisk 1
```

This makes the game write `Debug/gameplay-copy.sqlite` on every load. `check_now.py` reads it directly — no game restart needed to query.

---

## Tools

### `check_now.py` — Live DB Check ⭐ Primary Tool

Queries the live `gameplay-copy.sqlite` database and checks `UI.log` / `Database.log`. Run at any time while the game is running.

```bash
python tools/check_now.py
```

**What it checks:**

| Section | Pass condition |
|---|---|
| Victories (Modern) | `RequirementSetId = REQSET_VICTORY_NEVER_MET` |
| VictoryTypes | `PrereqRequirementSetId = REQSET_VICTORY_NEVER_MET`, `CountdownDuration = 99999` |
| REQ_VICTORY_NEVER_MET | Row exists with `Inverse = 1` |
| REQSET_VICTORY_NEVER_MET | Row exists and is linked |
| AgeProgressionTurns | `Points = 0` (frozen) |
| Database.log | Zero mod-related errors |
| UI.log | `[VictorySettings]` load-confirmation line present |

---

### `watch_logs.py` — Real-time Log Watcher

Tails `UI.log`, `Database.log`, and `Modding.log` live. Start this before launching Civ7.

```bash
python tools/watch_logs.py                        # live output only
python tools/watch_logs.py --save-session         # also saves a session file
python tools/watch_logs.py --log-dir "D:\path"    # custom log directory
```

**Output legend:**

| Prefix | Meaning |
|---|---|
| `[VictorySettings]` | In-game logger output (requires `MOD_DEBUG = true`) |
| `DB-ERR` | Database error (bad — our mod or game bug) |
| `DB-OK` | Database validation passed |

---

### `analyze_session.py` — Session Health Report

Reads a saved session file or live logs and produces a structured pass/fail report.

```bash
python tools/analyze_session.py                              # from live logs
python tools/analyze_session.py --session session.txt        # from saved file
python tools/analyze_session.py --report report.txt          # save report to file
```

---

### `dump_db.py` — Full SQLite Table Dump

Dumps all mod-relevant tables from an on-disk SQLite file. Run while game is running (reads `gameplay-copy.sqlite`) or after quitting.

```bash
python tools/dump_db.py                            # pretty table
python tools/dump_db.py --json --out dump.json
python tools/dump_db.py --csv  --out dump.csv
python tools/dump_db.py --db-path "C:\path\to\gameplay-copy.sqlite"
```

---

## Enabling Verbose In-Game Logging

By default, the in-game logger (`ui/core/victory-settings-logger.js`) writes only one line to `UI.log`:
```
[VictorySettings] v1.5.0 loaded. MOD_DEBUG=false. Run python tools/check_now.py to inspect live DB.
```

To enable the full diagnostic dump, edit the logger and set:
```js
const MOD_DEBUG = true;   // line 29
```

Then restart the game. All `[VictorySettings]` lines will appear in `UI.log`.

---

## Log File Locations

```
%LOCALAPPDATA%\Firaxis Games\Sid Meier's Civilization VII (Epic)\Logs\
```

| File | Contents |
|---|---|
| `UI.log` | JS console output — `[VictorySettings]` lines appear here |
| `Database.log` | DB operations and errors |
| `Modding.log` | Mod loading and registration events |

```
%LOCALAPPDATA%\Firaxis Games\Sid Meier's Civilization VII (Epic)\Debug\
```

| File | Contents |
|---|---|
| `gameplay-copy.sqlite` | Live gameplay DB snapshot (requires `CopyDatabasesToDisk 1`) |
| `frontend-copy.sqlite` | Frontend/config DB snapshot |
