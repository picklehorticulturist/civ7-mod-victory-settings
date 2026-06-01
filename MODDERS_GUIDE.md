# Victory Settings — Modder's Guide

This document covers the internal architecture, debug tooling, and extension points for the **Victory Settings** mod.

---

## Architecture Overview

```
victory-settings.modinfo
│
├── [shell scope]  core-shell-victory-settings
│   ├── data/core/config/SetupParameters.xml   — registers 6 game parameters
│   ├── text/en_us/PanelText.xml               — UI labels for setup screen
│   └── ui/core/create-panels/advanced-options-panel.js  — injects toggles into setup UI
│
├── [game scope, always]
│   ├── base-standard-victory-advisor          — overrides victory advisor panel
│   └── victory-settings-diagnostics           — logger (silent by default)
│
├── [game scope, conditional on parameters]
│   ├── age-progression-turn-counter-disable   — freezes AgeProgressionTurns Points=0
│   ├── age-progression-player-eliminated-disable
│   ├── modern-age-current-victory-*-disabled  — per-victory XML blocks (4 total)
│   └── modern-age-victory-requirements-block  — injects REQ_VICTORY_NEVER_MET
```

---

## How Victories Are Blocked

Two layers are required for Civ7 v1.4.0+:

### Layer 1 — Legacy `Victories` table
`data/age-modern/victory-*-disable.xml` updates:
```xml
<Victories>
  <Update>
    <Where VictoryType="VICTORY_CULTURE_MODERN"/>
    <Set EnabledByDefault='0'/>
    <Set RequirementSetId='REQSET_VICTORY_NEVER_MET'/>
  </Update>
</Victories>
```

### Layer 2 — Countdown `VictoryTypes` table (added in v1.4.0)
```xml
<VictoryTypes>
  <Update>
    <Where VictoryType="VICTORY_CULTURE_MODERN"/>
    <Set PrereqRequirementSetId='REQSET_VICTORY_NEVER_MET'/>
    <Set CountdownDuration='99999'/>
  </Update>
</VictoryTypes>
```

### The Shared Requirement Block
Defined in `data/age-modern/victory-requirements-block.xml`:
```xml
<Requirements>
  <Row RequirementId="REQ_VICTORY_NEVER_MET"
       RequirementType="REQUIREMENT_ALWAYS_MET"
       Inverse="1"/>   <!-- Inverse=1 means this ALWAYS FAILS -->
</Requirements>
```
This single block is reused by all 4 victory types.

---

## Age Progression Freeze

`data/age-progression-turn-counter-disabled.xml` sets `Points="0"` on `AgeProgressionTurns` rows, which stops the turn-based age advancement counter from filling. This is guarded by the `age-progression-turn-counter-disabled` ActionCriteria so it only applies when the user enables that option.

---

## Enabling Debug Logging

The in-game logger (`ui/core/victory-settings-logger.js`) is **silent by default**.
To enable full diagnostic output in `UI.log`:

1. Open `ui/core/victory-settings-logger.js`
2. Change line 29:
   ```js
   // Before (silent — for end users)
   const MOD_DEBUG = false;

   // After (verbose — for development)
   const MOD_DEBUG = true;
   ```
3. Restart the game — search `UI.log` for `[VictorySettings]`

Even with `MOD_DEBUG = false`, one load-confirmation line is always written:
```
[VictorySettings] v1.4.1 loaded. MOD_DEBUG=false. Run python tools/check_now.py to inspect live DB.
```

---

## Developer Tools

All tools require Python 3.10+ and only standard library packages.

| Tool | Purpose |
|---|---|
| `tools/check_now.py` | **Primary tool.** Live DB query — reads `gameplay-copy.sqlite` written by `CopyDatabasesToDisk`. Run any time during gameplay. |
| `tools/watch_logs.py` | Real-time log tail — shows `[VictorySettings]` lines as they appear |
| `tools/analyze_session.py` | Post-session health report from saved log data |
| `tools/dump_db.py` | Full SQLite table dump for deep inspection |

### Enabling Live DB Access (one-time setup)
Add to `%LOCALAPPDATA%\Firaxis Games\Sid Meier's Civilization VII (Epic)\AppOptions.txt`:
```ini
CopyDatabasesToDisk 1
```
The game will then write `Debug/gameplay-copy.sqlite` on every load — queryable with `check_now.py` while the game is running.

---

## Key Database Tables

| Table | Relevant Columns | What to check |
|---|---|---|
| `Victories` | `VictoryType`, `RequirementSetId` | Should be `REQSET_VICTORY_NEVER_MET` for disabled victories |
| `VictoryTypes` | `PrereqRequirementSetId`, `CountdownDuration` | Should be `REQSET_VICTORY_NEVER_MET` / `99999` |
| `Requirements` | `RequirementId`, `RequirementType`, `Inverse` | `REQ_VICTORY_NEVER_MET` with `Inverse=1` |
| `RequirementSets` | `RequirementSetId` | `REQSET_VICTORY_NEVER_MET` must exist |
| `RequirementSetRequirements` | `RequirementSetId`, `RequirementId` | Link between the above two must exist |
| `AgeProgressionTurns` | `Points` | Should be `0` when turn counter is frozen |

---

## Common Issues

| Symptom | Cause | Fix |
|---|---|---|
| Victory screen appears despite mod | Mod DB failed to apply | Check `Database.log` for `ERROR` lines |
| `[VictorySettings]` missing from `UI.log` | Logger script not loaded | Check if it has its own ActionGroup in `.modinfo` (not bundled with erroring scripts) |
| `UNIQUE constraint failed` error | Duplicate row insertion | Ensure the ActionGroup registering block XML fires only once (`always-active` criteria) |
| `no such column` error | Wrong table column name for this game version | Check base game XML in `D:\Games\CivilizationVII\Base\modules\base-standard\data\` |
