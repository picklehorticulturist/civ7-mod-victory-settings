# Civ7 Age Progression System — Internal Reference

> Last verified: 2026-06-01 against game version 1.4.0 (Build 11252419)

This document explains how the age progression bar fills, which DB tables control it, and how to freeze it via mod.

---

## How the Bar Fills

The Modern Age has a single progression timer: `AGE_PROGRESSION_MODERN_AGE_TIMER`. Points accumulate from two sources:

| Source | Table | Default Points | Notes |
|---|---|---|---|
| Every turn | `AgeProgressionTurns` | `1` per turn | `GameSpeedScaling=false` — NOT scaled by game speed |
| Player milestones | `AgeProgressionEvents` | 5 / 10 / 0 pts | `GameSpeedScaling=true` — scaled by speed (but ×0 = 0) |
| Future Civic researched | `AgeProgressionEvents` | 10 pts | Per player who researches it |
| Future Tech researched | `AgeProgressionEvents` | 10 pts | Per player who researches it |
| Player eliminated | `AgeProgressionEvents` / `AgeProgressionEventMapSizeOverrides` | 0 (overridden per map size) | Originally had non-zero values |

When total accumulated points ≥ `MaxPoints` → age ends → `VICTORY_SCORE` fires.

---

## Key DB Tables

### `AgeProgressions`

One row per age that has a timer.

| Column | Type | Description |
|---|---|---|
| `AgeProgressionType` | TEXT PK | e.g. `AGE_PROGRESSION_MODERN_AGE_TIMER` |
| `AgeType` | TEXT FK | `AGE_MODERN` / `AGE_ANTIQUITY` / `AGE_EXPLORATION` |
| `EndsAge` | INT | `1` = bar reaching MaxPoints ends the age |
| `MaxPoints_Abbreviated` | INT | Points needed on **Online + Quick** speeds with **Abbreviated** age length |
| `MaxPoints_Standard` | INT | Points needed on **Standard** speed |
| `MaxPoints_Long` | INT | Points needed on **Epic + Marathon** speeds |

> **Critical**: There is NO `MaxPoints_Marathon` column. Marathon and Epic both use `MaxPoints_Long`.

**Default values (Modern Age):**
```
MaxPoints_Abbreviated = 120
MaxPoints_Standard    = 140  
MaxPoints_Long        = 160
```

**To freeze (never fills):**
```xml
<AgeProgressions>
    <Update><Where AgeType="AGE_MODERN"/><Set MaxPoints_Abbreviated="2147483647"/></Update>
    <Update><Where AgeType="AGE_MODERN"/><Set MaxPoints_Standard="2147483647"/></Update>
    <Update><Where AgeType="AGE_MODERN"/><Set MaxPoints_Long="2147483647"/></Update>
</AgeProgressions>
```
> ⚠️ One `<Set>` per `<Update>` — the Civ7 XML serializer rejects duplicate `<Set>` elements.

---

### `AgeProgressionTurns`

Points added per game turn.

| Column | Type | Description |
|---|---|---|
| `AgeProgressionTurnType` | TEXT PK | e.g. `AGE_PROGRESSION_PER_TURN_BASE` |
| `AgeProgressionType` | TEXT FK | Links to `AgeProgressions` |
| `Points` | INT | Points per turn (default: `1`) |
| `GameSpeedScaling` | INT | `0` = not scaled, `1` = scaled by CostMultiplier/100 |

**Default:** `Points=1, GameSpeedScaling=0` (1 point per turn on ALL speeds).

**To freeze:**
```xml
<AgeProgressionTurns>
    <Update>
        <Where AgeProgressionTurnType="AGE_PROGRESSION_PER_TURN_BASE"/>
        <Set Points="0"/>
    </Update>
</AgeProgressionTurns>
```

---

### `AgeProgressionEvents`

Points added when specific events occur.

| `AgeProgressionEventType` | Default Points | `GameSpeedScaling` | Trigger |
|---|---|---|---|
| `AGE_PROGRESSION_PLAYER_MILESTONE_1` | `5` | `1` (scaled) | Player hits first milestone on any Legacy Path |
| `AGE_PROGRESSION_PLAYER_MILESTONE_2` | `10` | `1` (scaled) | Player hits second milestone |
| `AGE_PROGRESSION_PLAYER_MILESTONE_3` | `0` | `1` (scaled) | Player hits third milestone |
| `AGE_PROGRESSION_FUTURE_CIVIC` | `10` | `1` (scaled) | Player researches a Future Civic |
| `AGE_PROGRESSION_FUTURE_TECH` | `10` | `1` (scaled) | Player researches a Future Tech |
| `AGE_PROGRESSION_PLAYER_ELIMINATED` | `0` | `1` (scaled) | A player is eliminated |

> **Note**: `GameSpeedScaling=1` multiplies Points by `CostMultiplier/100`. For Online speed (CostMultiplier=50), `10pts × 0.5 = 5pts`.

**To freeze all events:**
```xml
<AgeProgressionEvents>
    <Update><Where AgeProgressionEventType="AGE_PROGRESSION_PLAYER_MILESTONE_1"/><Set Points="0"/></Update>
    <Update><Where AgeProgressionEventType="AGE_PROGRESSION_PLAYER_MILESTONE_2"/><Set Points="0"/></Update>
    <Update><Where AgeProgressionEventType="AGE_PROGRESSION_PLAYER_MILESTONE_3"/><Set Points="0"/></Update>
    <Update><Where AgeProgressionEventType="AGE_PROGRESSION_FUTURE_TECH"/><Set Points="0"/></Update>
    <Update><Where AgeProgressionEventType="AGE_PROGRESSION_FUTURE_CIVIC"/><Set Points="0"/></Update>
</AgeProgressionEvents>
```

---

### `AgeProgressionMilestones`

Defines which in-game achievements trigger each milestone event.

| Column | Description |
|---|---|
| `AgeProgressionMilestoneType` | Unique ID e.g. `MODERN_SCIENCE_MILESTONE_1` |
| `AgeProgressionEventType` | Which event fires e.g. `AGE_PROGRESSION_PLAYER_MILESTONE_1` |
| `LegacyPathType` | Which Legacy Path e.g. `LEGACY_PATH_MODERN_SCIENCE` |
| `RequiredPathPoints` | Path points needed to trigger this milestone |
| `FinalMilestone` | `1` if this is the last milestone on this path |

---

### `AgeProgressionEventMapSizeOverrides`

Overrides `AgeProgressionEvents.Points` for specific map sizes.

As of v1.4.0, all `AGE_PROGRESSION_PLAYER_ELIMINATED` overrides are `Points=0` for all map sizes (Tiny/Small/Standard/Large/Huge).

---

## Age Length vs Game Speed Mapping

The in-game **Age Length** setting maps to which `MaxPoints_*` column is used:

| Age Length (UI) | DB Column | Game Speeds that use this |
|---|---|---|
| Abbreviated | `MaxPoints_Abbreviated` | Online, Quick |
| Standard | `MaxPoints_Standard` | Standard |
| Long | `MaxPoints_Long` | Epic, Marathon |

The **Game Speed** setting (Online/Standard/Epic/Marathon) controls `CostMultiplier` for scaling, NOT the MaxPoints column. The MaxPoints column is determined by Age Length.

---

## Why 60 Turns on Online + Abbreviated

```
Settings: Online speed, Abbreviated age length, 6 players

Points per turn:        1 pt (GameSpeedScaling=false, no speed effect)
Milestone_1 per player: 5 pts × 6 players = 30 pts
Milestone_2 per player: 10 pts × 0.5 (Online) × 6 players = 30 pts
FutureCivic per player: 10 pts × 0.5 (Online) = 5 pts each

Approx at turn 30: milestones done = 60 pts
Remaining:         60 pts ÷ 1pt/turn = ~60 more turns? No...

Actual: milestones fire early (turn 10-20 for fast AI)
  30 milestone pts + 30 future pts + 60 turn pts = 120 = MaxPoints_Abbreviated
  + 10-turn countdown = game over at turn ~60
```

---

## Scope: Each Age Has Its Own Timer — in Its Own Per-Age DB

The gameplay DB is **rebuilt per age**, and each age's DB carries only *its own* timer:
- Antiquity DB → `AGE_PROGRESSION_ANTIQUITY_AGE_TIMER`
- Exploration DB → `AGE_PROGRESSION_EXPLORATION_AGE_TIMER` (verified 2026-06-21: `EndsAge=1`,
  `MaxPoints_Abbreviated/Standard/Long = 120/140/160`)
- Modern DB → `AGE_PROGRESSION_MODERN_AGE_TIMER`

> ⚠️ Earlier notes said "only the Modern Age has a timer row." That was an artifact of only
> ever dumping the Modern-age DB. In the Exploration-age DB, the **only** `AgeProgressions`
> row is the Exploration one — there is no Modern row to update. A DB change therefore only
> applies to the age whose DB is currently loaded, which is why `<AgeInUse>` criteria on the
> ActionGroup matters. This is also why the v1.5.0 victory blocks had to be loaded for the
> Exploration (and Antiquity) age contexts, not just Modern.
