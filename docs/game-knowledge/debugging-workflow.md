# Debugging Workflow — Victory Settings Mod

> A step-by-step guide for diagnosing issues with this mod in any game version.

---

## One-Time Setup

### 1. Enable live DB writing
Add to `%LOCALAPPDATA%\Firaxis Games\Sid Meier's Civilization VII (Epic)\AppOptions.txt`:
```ini
CopyDatabasesToDisk 1
EnableTuner 1
```
This makes the game write `Debug/gameplay-copy.sqlite` on every game load. **Must be done before launching the game.**

### 2. Verify Python is available
```bash
python --version   # needs 3.10+
```
All tools use only standard library — no pip installs needed.

---

## Standard Debugging Session

```bash
# Terminal 1 — start BEFORE launching Civ7
python tools/watch_logs.py --save-session

# Launch Civ7, enable mod, create game with toggles ON, play

# At any point during gameplay — Terminal 2
python tools/check_now.py

# After quitting — Terminal 3 (optional deep dump)
python tools/dump_db.py --json --out dump_$(date +%Y%m%d).json
python tools/analyze_session.py --session tools/session_*.txt --report report.txt
```

---

## check_now.py Output Guide

Run `python tools/check_now.py` while the game is running.

| Section | Green = Good | Red = Problem |
|---|---|---|
| Victories (Modern Age) | `[BLOCKED]` with `REQSET_VICTORY_NEVER_MET` | Any other RequirementSetId |
| VictoryTypes | `[BLOCKED]` with `REQSET_VICTORY_NEVER_MET`, Countdown=99999 | Default values or unblocked |
| Requirement Block | `[PASS]` for all 3 rows | `[FAIL]` = INSERT didn't fire |
| AgeProgressionTurns | `[frozen]` Points=0 | `[ACTIVE]` Points=1 |
| Age Bar MaxPoints | `[DISABLED (never fills)]` = 2147483647 | `[ACTIVE = 120]` = not applied |
| VICTORY_SCORE | `[BLOCKED]` on both rows | `[NOT BLOCKED]` |
| Database.log Errors | `0 total errors` | Any mod-related errors |

---

## Diagnosing Specific Failures

### "Content Configuration Validation Failed" at main menu
**Cause**: Shell-scope XML error in `SetupParameters.xml` or localization.  
**Check**: `Database.log` — look for `ERROR` lines at the timestamp of the popup.

Common causes:
- Duplicate `<Set>` elements in an XML file
- Wrong root element (`<GameInfo>` instead of `<Database>`)
- Invalid column name referenced in an `<Update>`

### Victories not blocked (game-end screen appears)
**Check**:
1. `check_now.py` → are Victories showing `[BLOCKED]`?
2. `Database.log` → any `UNIQUE constraint failed` error?
   - If yes: `victory-requirements-block.xml` is being loaded multiple times → check modinfo ActionGroup structure
3. `Modding.log` → did the ActionGroup for the specific victory even load?

### Game still ends after 60 turns (MaxPoints not applied)
**Check**:
1. `check_now.py` → Age Bar MaxPoints section → showing `[ACTIVE = 120]`?
2. In-game Advanced Setup: is **"Disable Age Ending"** toggle set to ON?
3. `Modding.log` → did `age-modern-ending-disable` ActionGroup load?
4. `Database.log` → any error in `age-modern-ending-disabled.xml`?

### `SOURCE ERROR` in UI.log
**Cause**: A JavaScript file failed to load/execute.  
**Impact**: Isolated per ActionGroup. If the erroring script is in its own ActionGroup, other scripts are unaffected.  
**Check**: Is `[VictorySettings]` load line present? If not, the logger JS errored.

---

## Log File Quick Reference

| File | Location | Contains |
|---|---|---|
| `UI.log` | `...\Logs\UI.log` | JS console output. Filter for `[VictorySettings]` |
| `Database.log` | `...\Logs\Database.log` | All DB operations and errors |
| `Modding.log` | `...\Logs\Modding.log` | Mod loading, ActionGroup execution |
| `gameplay-copy.sqlite` | `...\Debug\gameplay-copy.sqlite` | Live gameplay DB (requires `CopyDatabasesToDisk 1`) |

---

## Upgrading to a New Game Version

When Civ7 releases a patch, run this checklist:

1. **Check `Database.log` for `no such column` errors** — columns may have been renamed/removed
2. **Run `check_now.py`** — any section showing red needs investigation
3. **Check `AgeProgressions` schema** — Firaxis may add new `MaxPoints_*` columns for new game speeds
4. **Check `VictoryTypes` schema** — new columns or renamed `ScoringType` values
5. **Check `Victories` table** — new victory types added for new DLC
6. **Verify `REQSET_SCORE_PREREQ`** — its contents determine when `VICTORY_SCORE` is active
7. **Run a test game** to turn 60+ and confirm no game-end screen
