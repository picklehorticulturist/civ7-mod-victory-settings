# Game Knowledge DB — Index

Internal reference documentation for the Victory Settings mod. Captures everything learned about the Civ7 engine during development of v1.4.0 and v1.4.1.

> **Purpose**: Reduce time-to-diagnosis when the game updates and breaks things. Read these before diving into Database.log.

---

## Documents

| File | What it answers |
|---|---|
| [`age-progression-system.md`](./age-progression-system.md) | How does the age bar fill? Which tables? Why did the game end at 60 turns? |
| [`victory-system.md`](./victory-system.md) | How are victories registered? What is VICTORY_SCORE? How does REQSET_VICTORY_NEVER_MET work? |
| [`xml-schema-rules.md`](./xml-schema-rules.md) | Why did my XML cause a DB error? What are the serializer rules? |
| [`database-tables-reference.md`](./database-tables-reference.md) | What columns does table X have? What are the default vs mod values? |
| [`debugging-workflow.md`](./debugging-workflow.md) | How do I diagnose a broken mod? What to check when a new patch drops? |

---

## Quick Reference — Key Facts

### Age Progression
- **Only Modern Age has a timer row** in `AgeProgressionTurns` (v1.4.0 DB)
- **No `MaxPoints_Marathon` column** — Marathon uses `MaxPoints_Long` (same as Epic)
- `GameSpeedScaling=0` on `AgeProgressionTurns` means per-turn points are NOT scaled by game speed
- Default: `1pt/turn` + `5/10pts per milestone` × number of players = bar fills in ~60 turns (Online + Abbreviated)
- Our fix: `MaxPoints_* = 2147483647` (SQLite max int) = bar never fills

### Victory System
- v1.4.0 added a second layer: `VictoryTypes` table with `CountdownDuration` + `PrereqRequirementSetId`
- Both layers must be blocked — `Victories.RequirementSetId` AND `VictoryTypes.PrereqRequirementSetId`
- `VICTORY_SCORE` fires instantly (`CountdownDuration=0`) when Modern Age ends — must be blocked separately
- `REQSET_SCORE_PREREQ` is `REQUIREMENT_ALWAYS_MET` (not inverted) — score victory always active

### Critical XML Rules
- **One `<Set>` per `<Update>` block** — serializer rejects duplicates
- Root element must be `<Database>` or `<GameEffects>`
- `UNIQUE constraint` on INSERT → entire ActionGroup transaction rolls back silently
- `always-active` ActionGroup for shared rows (like `REQ_VICTORY_NEVER_MET`) to avoid constraint errors

### Log Locations
```
Logs:  %LOCALAPPDATA%\Firaxis Games\Sid Meier's Civilization VII (Epic)\Logs\
Debug: %LOCALAPPDATA%\Firaxis Games\Sid Meier's Civilization VII (Epic)\Debug\
```
Enable live DB: `CopyDatabasesToDisk 1` in `AppOptions.txt`

---

## Version History of This Knowledge Base

| Version | Date | What was learned |
|---|---|---|
| v1.4.0 | 2025 | Age progression point system, localization injection, UNIQUE constraint bug |
| v1.4.1 | 2026-06-01 | VICTORY_SCORE mechanism, MaxPoints columns, XML duplicate Set rule, 60-turn root cause, Marathon = MaxPoints_Long |
