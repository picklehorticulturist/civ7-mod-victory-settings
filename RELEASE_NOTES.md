# Release Notes

## v1.5.1 — Keep Domination (Last-Civ-Standing) Win

### 🛠 Fix: conquering all rivals ends the game again

v1.5.0 over-reached by also blocking `VICTORY_DOMINATION` inside the Military blocks. That is
the engine's *last-team-standing* condition (`REQUIREMENT_TEAM_DOMINATION_VICTORY`), distinct
from the points-based military countdown victory — blocking it meant eliminating every other
civilization would **not** end the game.

- Removed the `VICTORY_DOMINATION` updates from the Antiquity / Exploration / Modern Military
  files. It is now left at the game default (enabled).
- The points-based Military *countdown* victory (`VICTORY_MILITARY_MODERN`) is still blocked
  when Military Victory is disabled — you still can't win on military score, but wiping out
  all rivals ends the game normally.

> If you want play to continue even after you're the last civ standing, that's a different
> goal — open an issue and it can be added as its own toggle.

---

## v1.5.0 — All-Age Victory Blocking

### ✨ Enhancement: disabled victories are now blocked in *every* age

Victory blocking now covers the Antiquity, Exploration, **and** Modern age contexts —
previously it only took effect once you reached the Modern Age. This closes a gap opened
by game patch 1.4.0, which made the countdown victories triggerable as early as the
Exploration age, letting a runaway player win before Modern.

**Background — what changed in the game:**
- Civ7 **1.4.0** made the countdown victories achievable starting **~50% through the
  Exploration age** (previously Modern-only). When a player's score exceeds the threshold
  vs. 2nd place, a **5-turn "victory imminent" countdown** starts, then the game ends.
- The gameplay database is **rebuilt per age**. The same `VICTORY_*_MODERN` rows (with
  `CountdownDuration=5`) are present in the Exploration-age database, so a disabled victory
  could still be won there.

**What this release does:**
- All four `data/age-exploration/victory-*-disable.xml` and four
  `data/age-antiquity/victory-*-disable.xml` files now perform the full victory block
  (`Victories.RequirementSetId` + `VictoryTypes.PrereqRequirementSetId` →
  `REQSET_VICTORY_NEVER_MET`, `CountdownDuration` → `99999`), mirroring the Modern-age
  files. They load under the existing per-age + per-toggle ActionGroups — no modinfo
  change required.
- Removed stale `Strategies` updates from those files (they referenced a `LegacyPathType`
  column that doesn't exist — the real column is `CountdownVictoryType` — so they were
  no-ops; AI tuning only, no gameplay impact).
- Added blocking for **`VICTORY_DOMINATION`** (a legacy-layer military/domination victory
  previously not covered) to the Military blocks in all three ages.

**Net effect:** a disabled victory now stays unwinnable in every age the toggle is set
for — no more early Exploration-age wins.

### 🛠 Developer Additions
- `tools/dump_all_victories.py` — dumps the **complete** Victories / VictoryTypes /
  AgeProgressions tables for **all ages** (the older tools filtered to `%MODERN%`, which
  is why this bug was invisible to them).
- `tools/DUMP_INSTRUCTIONS.md` — step-by-step guide for capturing the live database.

---

## v1.4.1 — Age Ending Fix, Logging System & Developer Tools

### 🎮 New Feature: "Disable Age Ending" Toggle

The Modern Age will never end when this toggle is ON. Previously, the game always ended after ~60 turns on Online + Abbreviated settings regardless of victory settings.

**Root cause (fixed):**
- `AgeProgressions.MaxPoints_Abbreviated = 120` — age bar had a reachable finish line
- `VICTORY_SCORE` was never blocked — fires instantly when the Modern Age ends
- With 6 players on Online speed, milestones + turn points filled the bar in exactly 60 turns

**Fix:**
- `MaxPoints_Abbreviated/Standard/Long` all set to `2147483647` (unreachable) for Modern Age
- `VICTORY_SCORE` blocked via `REQSET_VICTORY_NEVER_MET` at both DB layers
- Game speed and production pace completely unchanged — only the bar's finish line is removed

**Verified:** Played past turn 60 on Online + Abbreviated with no game-end screen. All DB checks green. Zero errors.

### 🔇 Logging System

- In-game diagnostic logger (`ui/core/victory-settings-logger.js`) is now **silent by default**
- Set `const MOD_DEBUG = true;` on line 29 to enable verbose output in `UI.log`
- One load-confirmation line always prints: `[VictorySettings] v1.4.1 loaded.`
- Logger isolated in its own ActionGroup — `SOURCE ERROR` events in other scripts cannot prevent it from loading

### 🛠 Fixes

- **UNIQUE constraint fix**: `victory-requirements-block.xml` now loads exactly once via `always-active` ActionGroup, preventing silent DB rollbacks when multiple victories were disabled simultaneously
- **CountdownDuration blocked**: Added `VictoryTypes` table updates (`PrereqRequirementSetId=REQSET_VICTORY_NEVER_MET`, `CountdownDuration=99999`) to block the v1.4.0 countdown victory layer
- **XML duplicate Set fix**: `AgeProgressions` update split into one `<Update>` per column — Civ7 serializer rejects multiple `<Set>` elements per `<Update>` block
- **DB query context**: Fixed JS logger from `'game'` → `'gameplay'` database context
- **Strategies query**: Fixed column names (`CountdownVictoryType` not `LegacyPathType`)

### 👨‍💻 Developer Additions

- `tools/check_now.py` — live DB query via `gameplay-copy.sqlite` (primary debug tool)
- `tools/watch_logs.py` — real-time log watcher with session save
- `tools/analyze_session.py` — post-session health report
- `tools/dump_db.py` — full SQLite table dump
- `docs/game-knowledge/` — internal reference documentation (see below)
- `docs/test-report-age-ending-fix.md` — full verified test report for this fix

---

## v1.4.0 — Compatibility Update ("Test of Time" patch)

### 🌟 New Features
- **Localized UI**: Advanced Setup screen now shows proper English labels instead of raw `LOC_` tags

### 🛠 Fixes
- **Endless Turns restored**: Rewritten for new point-based Age progression system. `AgeProgressionTurns` and `AgeProgressionEvents` rows zeroed
- **Deprecated column removed**: Removed `AgeProgressionMilestones` references (`no such column: AgeProgressionAmount`)
- **Missing localization fixed**: Removed references to missing German localization files

### 👨‍💻 Developer Additions
- Added `MODDERS_GUIDE.md` with architecture documentation

---

## Game Knowledge DB (`docs/game-knowledge/`)

Added in v1.4.1. Documents internal Civ7 engine behaviour discovered during development:

| File | Contents |
|---|---|
| `age-progression-system.md` | All age progression tables, default values, speed/age-length mapping, 60-turn math |
| `victory-system.md` | Both victory DB layers, VICTORY_SCORE, REQSET_VICTORY_NEVER_MET mechanism |
| `xml-schema-rules.md` | Civ7 XML rules — duplicate Set, root elements, UNIQUE constraints, scope |
| `database-tables-reference.md` | All relevant tables with columns, sample values, mod vs default |
| `debugging-workflow.md` | Step-by-step debug guide, version upgrade checklist |
