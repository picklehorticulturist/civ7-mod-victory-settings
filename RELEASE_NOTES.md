# Release Notes

## v1.4.1 — Diagnostics & Code Cleanup

### Changes
- **Logging system**: In-game diagnostic logger is now **silent by default** for end users. Set `MOD_DEBUG = true` in `victory-settings-logger.js` to enable verbose output. One load-confirmation line is always written.
- **Logger isolation**: Logger now runs in its own isolated `ActionGroup` — `SOURCE ERROR` events in other scripts can no longer prevent it from loading.
- **DB query fix**: Fixed incorrect `'game'` database context — all queries now correctly use `'gameplay'` (confirmed from base game source).
- **Strategies query fix**: Corrected column names (`StrategyType` / `CountdownVictoryType` instead of the non-existent `LegacyPathType`).
- **Developer tools**: Added `tools/check_now.py` — instant live DB query against `gameplay-copy.sqlite` while the game is running.
- **Documentation**: Full rewrite of `README.md`, `MODDERS_GUIDE.md`, and `tools/README.md`.

---

## v1.4.0 — Compatibility Update ("Test of Time" patch)

### New Features
- **Localized UI**: Advanced Setup screen now shows proper English labels instead of raw `LOC_` tags.

### Fixes
- **Endless Turns restored**: Fully rewritten for the new point-based Age progression system. `AgeProgressionTurns` and `AgeProgressionEvents` rows are zeroed to maintain endless turns.
- **UNIQUE constraint fix**: Refactored to a single `always-active` ActionGroup for the requirements block — eliminates the `UNIQUE constraint failed` DB error that caused silent rollbacks of all mod logic.
- **Countdown victory system blocked**: Added `VictoryTypes` table updates with `PrereqRequirementSetId = REQSET_VICTORY_NEVER_MET` and `CountdownDuration = 99999` to block the v1.4.0 countdown victory layer.
- **Deprecated column removed**: Removed `AgeProgressionMilestones` references that caused `no such column: AgeProgressionAmount` errors.
- **Missing localization fixed**: Removed references to missing German localization files that prevented initialization.

### Developer Additions
- Added `MODDERS_GUIDE.md` with architecture documentation.
- Added Python diagnostic tools: `watch_logs.py`, `dump_db.py`, `analyze_session.py`.
