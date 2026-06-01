# Gameplay DB Tables — Reference

> Last verified: 2026-06-01 against game version 1.4.0 (Build 11252419)
> DB file: `%LOCALAPPDATA%\Firaxis Games\Sid Meier's Civilization VII (Epic)\Debug\gameplay-copy.sqlite`

All tables relevant to victory conditions and age progression, with column descriptions and sample values.

---

## Age Progression Tables

### `AgeProgressions`
| Column | Sample Value | Notes |
|---|---|---|
| `AgeProgressionType` | `AGE_PROGRESSION_MODERN_AGE_TIMER` | PK |
| `AgeType` | `AGE_MODERN` | FK → `Ages` |
| `EndsAge` | `1` | 1 = age ends when bar hits MaxPoints |
| `MaxPoints_Abbreviated` | `120` → mod: `2147483647` | Online + Quick + Abbreviated |
| `MaxPoints_Standard` | `140` → mod: `2147483647` | Standard speed |
| `MaxPoints_Long` | `160` → mod: `2147483647` | Epic + Marathon |

### `AgeProgressionTurns`
| Column | Sample Value | Notes |
|---|---|---|
| `AgeProgressionTurnType` | `AGE_PROGRESSION_PER_TURN_BASE` | PK |
| `AgeProgressionType` | `AGE_PROGRESSION_MODERN_AGE_TIMER` | FK |
| `Points` | `1` → mod: `0` | Points added per game turn |
| `GameSpeedScaling` | `0` | 0=not scaled, 1=×(CostMultiplier/100) |

### `AgeProgressionEvents`
| `AgeProgressionEventType` | Default Points | Mod Points | Trigger |
|---|---|---|---|
| `AGE_PROGRESSION_PLAYER_MILESTONE_1` | `5` | `0` | First milestone on any Legacy Path |
| `AGE_PROGRESSION_PLAYER_MILESTONE_2` | `10` | `0` | Second milestone |
| `AGE_PROGRESSION_PLAYER_MILESTONE_3` | `0` | `0` | Third milestone (already 0) |
| `AGE_PROGRESSION_FUTURE_CIVIC` | `10` | `0` | Future Civic researched |
| `AGE_PROGRESSION_FUTURE_TECH` | `10` | `0` | Future Tech researched |
| `AGE_PROGRESSION_PLAYER_ELIMINATED` | `0` | `0` | Player eliminated (already 0) |

### `AgeProgressionMilestones`
| Column | Notes |
|---|---|
| `AgeProgressionMilestoneType` | PK e.g. `MODERN_SCIENCE_MILESTONE_1` |
| `AgeProgressionEventType` | Which event fires |
| `LegacyPathType` | Which Legacy Path triggers this |
| `RequiredPathPoints` | Path points needed |
| `FinalMilestone` | `1` if last milestone on this path |

### `AgeProgressionEventMapSizeOverrides`
Overrides points per map size for `AGE_PROGRESSION_PLAYER_ELIMINATED`. All currently `Points=0`.

---

## Victory Tables

### `Victories`
| Column | Notes |
|---|---|
| `VictoryType` | PK e.g. `VICTORY_SCIENCE_MODERN` |
| `VictoryClassType` | e.g. `VICTORY_CLASS_SCIENCE` |
| `EnabledByDefault` | `1`=enabled, `0`=disabled |
| `RequirementSetId` | Must pass for victory to fire. Mod sets `REQSET_VICTORY_NEVER_MET` |
| `LegacyPathClassType` | Legacy path association |

### `VictoryTypes` (added v1.4.0)
| Column | Notes |
|---|---|
| `VictoryType` | PK |
| `PrereqRequirementSetId` | Must pass before countdown starts. Mod sets `REQSET_VICTORY_NEVER_MET` |
| `CountdownDuration` | Turns in countdown. Mod sets `99999`. `VICTORY_SCORE` is `0` (instant) |
| `ScoringType` | e.g. `COUNTDOWN_VICTORY_SCORING_TYPE_END_AGE` |
| `FinalAge` | Age this applies to. `VICTORY_SCORE` = `AGE_MODERN` |
| `MinimumPoints` | Min score to claim victory |

---

## Requirement Tables

### `Requirements`
| Column | Notes |
|---|---|
| `RequirementId` | PK e.g. `REQ_VICTORY_NEVER_MET` |
| `RequirementType` | e.g. `REQUIREMENT_ALWAYS_MET` |
| `Inverse` | `1` = invert result (ALWAYS_MET + Inverse=1 = ALWAYS FAILS) |

### `RequirementSets`
| Column | Notes |
|---|---|
| `RequirementSetId` | PK e.g. `REQSET_VICTORY_NEVER_MET` |
| `RequirementSetType` | `REQUIREMENTSET_TEST_ALL` = all must pass, `TEST_ANY` = any must pass |

### `RequirementSetRequirements`
Junction table linking sets to individual requirements.
| Column | Notes |
|---|---|
| `RequirementSetId` | FK → `RequirementSets` |
| `RequirementId` | FK → `Requirements` |

---

## Game Config Tables

### `Ages`
| Column | Notes |
|---|---|
| `AgeType` | PK e.g. `AGE_MODERN` |
| `Active` | `1` = currently active age |
| `ChronologyIndex` | `0`=Antiquity, `1`=Exploration, `2`=Modern |

### `GameSpeeds`
| Column | Notes |
|---|---|
| `GameSpeedType` | PK e.g. `GAMESPEED_ONLINE` |
| `CostMultiplier` | Percentage. Online=50, Standard=100, Epic=150, Marathon=300 |

> **Note**: `GameSpeeds` has NO turn count column. Turn limits and speed scaling for age progression are handled separately via `AgeProgressionTurns.GameSpeedScaling` and `AgeProgressions.MaxPoints_*`.

### `Strategies` (AI victory planning)
| Column | Notes |
|---|---|
| `StrategyType` | PK |
| `CountdownVictoryType` | FK → `VictoryTypes` |
| `MinNumConditionsNeeded` | Min conditions AI needs to pursue this strategy |
| `MaxNumConditionsNeeded` | Max conditions |

> AI strategies still register for blocked victories. AI pursues them but can never complete them — no gameplay impact.
