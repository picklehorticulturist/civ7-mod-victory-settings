# Release Notes

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
