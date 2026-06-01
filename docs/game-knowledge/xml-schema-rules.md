# Civ7 XML Schema Rules — Internal Reference

> Last verified: 2026-06-01 against game version 1.4.0 (Build 11252419)

Rules discovered through trial, error, and Database.log errors. Critical for anyone writing mod XML.

---

## Rule 1: One `<Set>` per `<Update>` block

**CRITICAL.** The Civ7 XML serializer rejects multiple `<Set>` elements inside one `<Update>`.

```xml
<!-- ❌ WRONG — causes: "Duplicate <Set> elements are not allowed" -->
<AgeProgressions>
    <Update>
        <Where AgeType="AGE_MODERN"/>
        <Set MaxPoints_Abbreviated="2147483647"/>
        <Set MaxPoints_Standard="2147483647"/>    <!-- ERROR -->
        <Set MaxPoints_Long="2147483647"/>         <!-- ERROR -->
    </Update>
</AgeProgressions>

<!-- ✅ CORRECT — one Set per Update -->
<AgeProgressions>
    <Update><Where AgeType="AGE_MODERN"/><Set MaxPoints_Abbreviated="2147483647"/></Update>
    <Update><Where AgeType="AGE_MODERN"/><Set MaxPoints_Standard="2147483647"/></Update>
    <Update><Where AgeType="AGE_MODERN"/><Set MaxPoints_Long="2147483647"/></Update>
</AgeProgressions>
```

**Error message in Database.log:**
```
ERROR: Database::XMLSerializer (filename.xml): Duplicate <Set> elements are not allowed.
```

---

## Rule 2: Valid XML root elements

The root element must be `<Database>` or `<GameEffects>`. Any other root (including `<GameInfo>`) causes:
```
Database XML root elements must start with either <Database> or <GameEffects>.
```
This is a soft warning, not a hard error, but the file will not be processed.

```xml
<!-- ✅ Correct -->
<?xml version="1.0" encoding="utf-8"?>
<Database>
    ...
</Database>
```

---

## Rule 3: UNIQUE constraint on INSERT

If you `<Row>` (INSERT) a row that already exists, the DB throws:
```
UNIQUE constraint failed: TableName.ColumnName
```
This **rolls back the entire transaction** for that ActionGroup load — silently failing all DB changes in that XML file.

**Prevention:** Use `<Update>` instead of `<Row>` when modifying existing data. Only use `<Row>` for genuinely new data. If multiple ActionGroups might load the same new row, isolate the INSERT into a single `always-active` ActionGroup.

---

## Rule 4: ActionGroup load order

ActionGroups within the same scope (e.g., `game`) load in the order they appear in the `.modinfo` file. If file B depends on a row created by file A, A's ActionGroup must appear first.

Example: `victory-requirements-block.xml` (inserts `REQ_VICTORY_NEVER_MET`) must load before any file that references `REQSET_VICTORY_NEVER_MET`.

---

## Rule 5: `<Where>` matches are case-sensitive

String comparisons in `<Where>` are case-sensitive. `AgeType="AGE_MODERN"` ≠ `AgeType="age_modern"`.

---

## Rule 6: `DeprecatedColumn` causes silent failure

If you reference a column that doesn't exist in the current game version, the DB logs:
```
no such column: ColumnName
```
And rolls back that block. Known deprecated columns (removed in v1.4.0):
- `AgeProgressionMilestones.AgeProgressionAmount` (caused the original `[gameplay] ERROR` bug)

---

## Rule 7: Shell vs Game scope

| Scope | When it loads | Use for |
|---|---|---|
| `shell` | Game launcher / main menu | Setup parameters, UI scripts, localization |
| `game` | When a game session starts | DB updates (gameplay tables), in-game UI |

DB tables like `AgeProgressions`, `Victories`, `VictoryTypes` are **gameplay** tables — must be in `game` scope.
Setup parameters (`Parameters` table) and localization must be in `shell` scope.

---

## Rule 8: `<ConfigurationValueMatches>` checks string equality

```xml
<ConfigurationValueMatches>
    <Group>Game</Group>
    <ConfigurationId>AgeEndingDisabled</ConfigurationId>
    <Value>1</Value>   <!-- string "1", not integer -->
</ConfigurationValueMatches>
```

For `Domain="bool"` parameters, `0` = off, `1` = on.

---

## Common Database.log Error Reference

| Error | Cause | Fix |
|---|---|---|
| `Duplicate <Set> elements are not allowed` | Multiple `<Set>` in one `<Update>` | One `<Set>` per `<Update>` block |
| `UNIQUE constraint failed` | Inserting a row that already exists | Use `<Update>` or isolate INSERT to `always-active` group |
| `no such column: X` | Column removed/renamed in this game version | Check current game XML for correct column name |
| `no such table: X` | Table removed or wrong DB context | Verify table exists in gameplay DB; check scope |
| `Database XML root elements must start with...` | Wrong root element | Use `<Database>` or `<GameEffects>` |
| `SOURCE ERROR` (in UI.log) | JS file has syntax/runtime error | Check the JS file; error is non-fatal if isolated in own ActionGroup |
