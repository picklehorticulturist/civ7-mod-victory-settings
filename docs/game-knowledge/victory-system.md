# Civ7 Victory System — Internal Reference

> Last verified: 2026-06-01 against game version 1.4.0 (Build 11252419)

This document explains how victories are registered, checked, and how to block them via mod.

---

## Two Victory Layers (v1.4.0+)

Civ7 v1.4.0 added a second victory tracking layer. Both must be blocked:

| Layer | Table | Column to block | Mechanism |
|---|---|---|---|
| Legacy | `Victories` | `RequirementSetId` | Points-based victory check |
| Countdown (new in 1.4.0) | `VictoryTypes` | `PrereqRequirementSetId` | Countdown timer system |

---

## `Victories` Table

The original victory registration table.

| Column | Description |
|---|---|
| `VictoryType` | PK e.g. `VICTORY_SCIENCE_MODERN` |
| `VictoryClassType` | e.g. `VICTORY_CLASS_SCIENCE` |
| `EnabledByDefault` | `1` = enabled, `0` = disabled |
| `RequirementSetId` | Set that must pass for victory to be achievable |
| `LegacyPathClassType` | Legacy path this victory is tied to |

**To block:** Set `RequirementSetId` to `REQSET_VICTORY_NEVER_MET`.

---

## `VictoryTypes` Table (added v1.4.0)

The countdown victory system introduced in "Test of Time" patch.

| Column | Description |
|---|---|
| `VictoryType` | PK e.g. `VICTORY_SCIENCE_MODERN` |
| `PrereqRequirementSetId` | Prereq must pass before countdown can start |
| `CountdownDuration` | Turns in countdown. `0` = instant, `99999` = effectively never |
| `ScoringType` | How the winner is chosen during countdown |
| `FinalAge` | Which age this victory applies to |
| `MinimumPoints` | Min score points to win |

**To block:** Set `PrereqRequirementSetId` to `REQSET_VICTORY_NEVER_MET` AND `CountdownDuration` to `99999`.

---

## VICTORY_SCORE — The Age-End Victory

This is the score/turn-limit victory that triggers when the Modern Age ends.

```
Victories table:
  VictoryType       = VICTORY_SCORE
  RequirementSetId  = REQSET_SCORE_VICTORY
  EnabledByDefault  = 1

VictoryTypes table:
  VictoryType              = VICTORY_SCORE
  ScoringType              = COUNTDOWN_VICTORY_SCORING_TYPE_END_AGE
  CountdownDuration        = 0       ← fires INSTANTLY when age ends
  FinalAge                 = AGE_MODERN
  PrereqRequirementSetId   = REQSET_SCORE_PREREQ
    → REQSET_SCORE_PREREQ contains REQUIREMENT_ALWAYS_MET (Inverse=0)
    → This prereq ALWAYS passes — score victory is always pending
```

This means: the moment `AGE_MODERN` ends (bar fills) → `VICTORY_SCORE` triggers with a 0-turn countdown → game over.

**To block:**
```xml
<Victories>
    <Update>
        <Where VictoryType="VICTORY_SCORE"/>
        <Set RequirementSetId="REQSET_VICTORY_NEVER_MET"/>
    </Update>
</Victories>
<VictoryTypes>
    <Update>
        <Where VictoryType="VICTORY_SCORE"/>
        <Set PrereqRequirementSetId="REQSET_VICTORY_NEVER_MET"/>
    </Update>
</VictoryTypes>
```

---

## The REQSET_VICTORY_NEVER_MET Block Mechanism

Our mod creates a requirement set that can **never** be satisfied:

```xml
<!-- A requirement that is ALWAYS_MET but with Inverse=1 → ALWAYS FAILS -->
<Requirements>
    <Row RequirementId="REQ_VICTORY_NEVER_MET"
         RequirementType="REQUIREMENT_ALWAYS_MET"
         Inverse="1"/>
</Requirements>
<RequirementSets>
    <Row RequirementSetId="REQSET_VICTORY_NEVER_MET"
         RequirementSetType="REQUIREMENTSET_TEST_ALL"/>
</RequirementSets>
<RequirementSetRequirements>
    <Row RequirementSetId="REQSET_VICTORY_NEVER_MET"
         RequirementId="REQ_VICTORY_NEVER_MET"/>
</RequirementSetRequirements>
```

Logic: `REQUIREMENT_ALWAYS_MET` + `Inverse=1` = always fails. `REQUIREMENTSET_TEST_ALL` means ALL requirements must pass. So the set always fails → victory condition always blocked.

> ⚠️ **Critical bug history**: This block XML must be loaded exactly ONCE via an `always-active` ActionGroup. If each victory's ActionGroup loaded it separately, the second load would trigger `UNIQUE constraint failed` on `REQ_VICTORY_NEVER_MET`, causing a DB rollback that silently un-blocks that victory.

---

## Modern Age Victory Types

| VictoryType | VictoryClass | Legacy Path | Default Countdown |
|---|---|---|---|
| `VICTORY_MILITARY_MODERN` | `VICTORY_CLASS_MILITARY` | `LEGACY_PATH_MODERN_MILITARY` | 99999 (when enabled) |
| `VICTORY_SCIENCE_MODERN` | `VICTORY_CLASS_SCIENCE` | `LEGACY_PATH_MODERN_SCIENCE` | 99999 |
| `VICTORY_ECONOMIC_MODERN` | `VICTORY_CLASS_ECONOMIC` | `LEGACY_PATH_MODERN_ECONOMIC` | 99999 |
| `VICTORY_CULTURE_MODERN` | `VICTORY_CLASS_CULTURE` | `LEGACY_PATH_MODERN_CULTURE` | 99999 |
| `VICTORY_SCORE` | `VICTORY_CLASS_SCORE` | (none) | **0** (instant) |
