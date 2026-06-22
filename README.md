# Victory Settings — Mod v1.5.1

> **Civilization VII mod** · Tested on game version 1.4.0 ("Test of Time")

Give yourself full control over how and when your game ends. Disable any combination of victory conditions, freeze age progression, and prevent the Modern Age from ever ending.

---

## Features

| Feature | Description |
|---|---|
| **Victory Toggles** | Enable or disable Military, Science, Economic, and Culture victories individually |
| **All-age victory blocking** *(new in v1.5.0)* | Disabled victories are now blocked in **every** age — including the Exploration-age victory countdown the game added in patch 1.4.0, so a runaway player can't win before the Modern Age |
| **Turn Counter Freeze** | Stop ages from advancing based on turn limits |
| **Elimination Freeze** | Stop ages from advancing when players are eliminated |
| **Disable Age Ending** *(new in v1.4.1)* | Modern Age never ends — no game-over screen regardless of game speed or age length |
| **Works on all speeds** | Online + Abbreviated, Standard, Epic, Marathon — all covered |

---

## Installation

1. Place this folder in your Mods directory:
   ```
   %LOCALAPPDATA%\Firaxis Games\Sid Meier's Civilization VII (Epic)\Mods\
   ```
2. Launch Civilization VII → **Content Manager** → enable **Victory Settings**
3. Start a new game → **Advanced Setup** → configure toggles under **Victory Options** and **Age Progression**

---

## Advanced Setup Toggles

### Victory Options

> **⚠️ Read the boxes carefully.** Each box shows whether that victory is **enabled**, and the game ships with all victories enabled — so the four boxes start **checked**. **To disable a victory, UNCHECK its box.** A checked box means that victory is still active. (This is the opposite of *Disable Age Ending* below, which you *check* to turn on.)

| Toggle | Default | Effect |
|---|---|---|
| Military Victory | ON (checked) | **Uncheck** to block military victory for all players |
| Science Victory | ON (checked) | **Uncheck** to block science victory |
| Economic Victory | ON (checked) | **Uncheck** to block economic victory |
| Culture Victory | ON (checked) | **Uncheck** to block culture victory |

### Age Progression
| Toggle | Default | Effect |
|---|---|---|
| Turn Counter | ON | Disable to stop turns from filling the age progression bar |
| Player Elimination | ON | Disable to stop eliminations from filling the age bar |
| **Disable Age Ending** | **OFF** | **Enable to prevent the Modern Age from ever ending** |

> **"Disable Age Ending"** is the key toggle for endless play. It sets the age bar's finish line to an unreachable value and blocks the score victory that fires at age end. Game speed and production pace are completely unchanged.

---

## How It Works

### Victory Blocking (double-layer)
When you disable a victory, the mod blocks it at both DB layers introduced in v1.4.0:

| Layer | Table | What changes |
|---|---|---|
| Legacy | `Victories` | `RequirementSetId` → `REQSET_VICTORY_NEVER_MET` |
| Countdown (v1.4.0+) | `VictoryTypes` | `PrereqRequirementSetId` → `REQSET_VICTORY_NEVER_MET`, `CountdownDuration` → 99999 |

`REQSET_VICTORY_NEVER_MET` is a requirement set that can never be satisfied — it uses `REQUIREMENT_ALWAYS_MET` with `Inverse=1`, which always fails.

**Applied in every age (v1.5.0):** Civ7's gameplay database is rebuilt per age, and patch 1.4.0 made the countdown victories triggerable from ~50% through the **Exploration** age — not just the Modern Age. The block is therefore loaded for the Antiquity, Exploration, *and* Modern age contexts (each gated by the same per-victory toggle), so a disabled victory stays unwinnable no matter which age you're in.

### Age Ending Prevention
When "Disable Age Ending" is ON:
1. `AgeProgressions.MaxPoints_*` set to `2147483647` for all game speed + age length combos
2. `VICTORY_SCORE` (the score/age-end victory that fires instantly when the age ends) is blocked via `REQSET_VICTORY_NEVER_MET`

---

## Troubleshooting

The mod ships with Python developer tools in `tools/`. **End users don't need these.**

```bash
# Check if mod is applied correctly (run while game is running)
python tools/check_now.py

# Watch logs in real time
python tools/watch_logs.py
```

See [`tools/README.md`](./tools/README.md) and [`docs/game-knowledge/debugging-workflow.md`](./docs/game-knowledge/debugging-workflow.md) for full documentation.

---

## Known Limitations

- The **AI will still pursue** disabled victories internally (strategies remain registered but unachievable). No gameplay impact.
- Requires a **new game** — settings do not apply to saves started without the mod.
- **"One More Turn"** after score victory in multiplayer is a base game bug — avoided entirely by enabling "Disable Age Ending".

---

## For Modders

See [`MODDERS_GUIDE.md`](./MODDERS_GUIDE.md) for architecture details, debug flag instructions, and how to extend the mod.

See [`docs/game-knowledge/`](./docs/game-knowledge/) for deep-dive documentation on the game's internal DB schema, XML rules, age progression system, and debugging workflows — useful when upgrading to new game versions.
