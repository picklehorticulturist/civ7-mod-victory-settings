# Victory Settings — Modder's Guide

This document covers the internal architecture, debug tooling, and extension points for the **Victory Settings** mod.

For deep-dive game engine knowledge, see [`docs/game-knowledge/`](./docs/game-knowledge/).

---

## Architecture Overview

```
victory-settings.modinfo
│
├── [shell scope]  core-shell-victory-settings
│   ├── data/core/config/SetupParameters.xml     — 7 game parameters
│   ├── text/en_us/PanelText.xml                 — UI labels
│   └── ui/core/create-panels/advanced-options-panel.js
│
├── [game scope, always]
│   ├── modern-age-victory-requirements-block    — inserts REQSET_VICTORY_NEVER_MET (once)
│   ├── base-standard-victory-advisor            — overrides victory advisor panel
│   └── victory-settings-diagnostics             — logger (silent by default)
│
├── [game scope, conditional — Age Progression]
│   ├── age-progression-turn-counter-disable     — AgeProgressionTurns Points=0
│   ├── age-progression-player-eliminated-disable
│   └── age-modern-ending-disable                — MaxPoints=max_int + VICTORY_SCORE blocked
│
└── [game scope, conditional — Victories per age × 4 victory types]
    ├── antiquity-age-current-victory-*-disable  (×4)
    ├── exploration-age-current-victory-*-disable (×4)
    └── modern-age-current-victory-*-disable     (×4)
```

---

## Setup Parameters

| ParameterID | Default | Effect when OFF (0) |
|---|---|---|
| `MilitaryVictoryEnabled` | 1 | Military victory blocked in all ages |
| `ScienceVictoryEnabled` | 1 | Science victory blocked |
| `EconomicVictoryEnabled` | 1 | Economic victory blocked |
| `CultureVictoryEnabled` | 1 | Culture victory blocked |
| `AgeProgressionFromTurnCounterEnabled` | 1 | Turns add 0 points to age bar |
| `AgeProgressionFromPlayerEliminatedEnabled` | 1 | Eliminations add 0 points |
| `AgeEndingDisabled` | **0** | **When ON (1): Modern Age never ends** |

---

## How Victories Are Blocked (Double-Layer)

### Layer 1 — Legacy `Victories` table
```xml
<Victories>
  <Update>
    <Where VictoryType="VICTORY_CULTURE_MODERN"/>
    <Set RequirementSetId="REQSET_VICTORY_NEVER_MET"/>
  </Update>
</Victories>
```

### Layer 2 — Countdown `VictoryTypes` table (v1.4.0+)
```xml
<VictoryTypes>
  <Update>
    <Where VictoryType="VICTORY_CULTURE_MODERN"/>
    <Set PrereqRequirementSetId="REQSET_VICTORY_NEVER_MET"/>
  </Update>
  <Update>
    <Where VictoryType="VICTORY_CULTURE_MODERN"/>
    <Set CountdownDuration="99999"/>
  </Update>
</VictoryTypes>
```

### The Shared Requirement Block (`victory-requirements-block.xml`)
```xml
<Requirements>
  <Row RequirementId="REQ_VICTORY_NEVER_MET"
       RequirementType="REQUIREMENT_ALWAYS_MET"
       Inverse="1"/>
</Requirements>
```
`REQUIREMENT_ALWAYS_MET` + `Inverse=1` = always fails. Loaded **once** via `always-active` ActionGroup to prevent `UNIQUE constraint failed` when multiple victories are disabled simultaneously.

---

## How Age Ending Is Prevented (`age-modern-ending-disabled.xml`)

Two changes when `AgeEndingDisabled=1`:

### 1. MaxPoints set to impossible value
```xml
<AgeProgressions>
    <Update><Where AgeType="AGE_MODERN"/><Set MaxPoints_Abbreviated="2147483647"/></Update>
    <Update><Where AgeType="AGE_MODERN"/><Set MaxPoints_Standard="2147483647"/></Update>
    <Update><Where AgeType="AGE_MODERN"/><Set MaxPoints_Long="2147483647"/></Update>
</AgeProgressions>
```
Covers all speed + age length combos. Modern Age only — Antiquity/Exploration have separate `AgeProgressionType` rows and are untouched.

> ⚠️ **XML Rule**: One `<Set>` per `<Update>` block. The Civ7 serializer rejects duplicates.

### 2. VICTORY_SCORE blocked
```xml
<Victories>
    <Update><Where VictoryType="VICTORY_SCORE"/><Set RequirementSetId="REQSET_VICTORY_NEVER_MET"/></Update>
</Victories>
<VictoryTypes>
    <Update><Where VictoryType="VICTORY_SCORE"/><Set PrereqRequirementSetId="REQSET_VICTORY_NEVER_MET"/></Update>
</VictoryTypes>
```
`VICTORY_SCORE` fires instantly (`CountdownDuration=0`) when the Modern Age ends. Without this block, even with MaxPoints at max int, if the age somehow ended (e.g., via a future game update), the score victory would trigger.

---

## Age Progression Freeze

`data/age-progression-turn-counter-disabled.xml` zeros:
- `AgeProgressionTurns.Points` (per-turn contribution)
- All `AgeProgressionEvents.Points` (milestone, future tech/civic contributions)

These are separate from the MaxPoints fix — they reduce point input to 0, while MaxPoints raises the bar to unreachable. Both together = completely frozen age bar.

---

## Enabling Debug Logging

`ui/core/victory-settings-logger.js` is **silent by default** (`MOD_DEBUG = false`).

To enable:
1. Open `ui/core/victory-settings-logger.js`
2. Change line 29:
   ```js
   const MOD_DEBUG = true;
   ```
3. Restart game — search `UI.log` for `[VictorySettings]`

One load-confirmation line always prints regardless of `MOD_DEBUG`:
```
[VictorySettings] v1.5.0 loaded. MOD_DEBUG=false. Run python tools/check_now.py to inspect live DB.
```

---

## Developer Tools

| Tool | Command | Purpose |
|---|---|---|
| **Live DB check** | `python tools/check_now.py` | Primary. Checks all mod values in live `gameplay-copy.sqlite` |
| **Log watcher** | `python tools/watch_logs.py --save-session` | Real-time `UI.log` / `Database.log` tail |
| **Session report** | `python tools/analyze_session.py` | Post-session pass/fail report |
| **DB dump** | `python tools/dump_db.py --json --out dump.json` | Mod-relevant tables (Modern-filtered) |
| **All-age victory dump** | `python tools/dump_all_victories.py` | Full Victories/VictoryTypes/AgeProgressions for **every** age |

### Enable live DB access (one-time)
```ini
# %LOCALAPPDATA%\Firaxis Games\Sid Meier's Civilization VII (Epic)\AppOptions.txt
CopyDatabasesToDisk 1
EnableTuner 1
```

---

## Common Issues

| Symptom | Cause | Fix |
|---|---|---|
| "Content Configuration Validation Failed" | XML error in shell-scope file | Check `Database.log` for `ERROR` at startup time |
| Victories not blocked | `UNIQUE constraint` caused rollback | Ensure `victory-requirements-block.xml` is in a single `always-active` group |
| Game ends at 60 turns | `AgeEndingDisabled` toggle not ON, or XML not applied | Check `check_now.py` → Age Bar MaxPoints section |
| `Duplicate <Set> elements` error | Multiple `<Set>` in one `<Update>` block | Split into one `<Update>` per `<Set>` |
| `no such column` error | Column removed in this game version | Check base game XML for current schema |
| `SOURCE ERROR` in UI.log | JS file runtime error | Non-fatal if script is in isolated ActionGroup |

---

## Game Knowledge Reference

Deep-dive documentation in `docs/game-knowledge/`:

| File | Contents |
|---|---|
| [`age-progression-system.md`](./docs/game-knowledge/age-progression-system.md) | All age progression tables, default values, how the bar fills, 60-turn math |
| [`victory-system.md`](./docs/game-knowledge/victory-system.md) | Both victory layers, VICTORY_SCORE, REQSET_VICTORY_NEVER_MET mechanism |
| [`xml-schema-rules.md`](./docs/game-knowledge/xml-schema-rules.md) | Civ7 XML rules, common errors, scope rules |
| [`database-tables-reference.md`](./docs/game-knowledge/database-tables-reference.md) | All relevant DB tables with columns and sample values |
| [`debugging-workflow.md`](./docs/game-knowledge/debugging-workflow.md) | Step-by-step debug guide, version upgrade checklist |
