# Victory Settings — Mod v1.4.1

> **Civilization VII mod** · Tested on game version 1.4.0 ("Test of Time")

Give yourself full control over how and when your game ends. Disable any combination of victory conditions, freeze age progression, and play as long as you want.

---

## Features

| Feature | Description |
|---|---|
| **Victory Toggles** | Enable or disable Military, Science, Economic, and Culture victories individually |
| **Turn Counter Freeze** | Stop ages from advancing based on turn limits |
| **Elimination Freeze** | Stop ages from advancing when players are eliminated |
| **Works in Modern Age** | All blocks apply across Antiquity, Exploration, and Modern ages |

---

## Installation

1. Place this folder in your Mods directory:
   ```
   %LOCALAPPDATA%\Firaxis Games\Sid Meier's Civilization VII (Epic)\Mods\
   ```
2. Launch Civilization VII → **Content Manager** → enable **Victory Settings**
3. Start a new game → **Advanced Setup** → configure Victory and Age Progression options

---

## How It Works

When you disable a victory, the mod:
- Sets `EnabledByDefault = 0` on the `Victories` row
- Applies `REQSET_VICTORY_NEVER_MET` as the `RequirementSetId` — a requirement set that can never be satisfied (always fails)
- Sets `CountdownDuration = 99999` and blocks the `PrereqRequirementSetId` on `VictoryTypes` to disable the 1.4.0 countdown system as well

This double-layer approach ensures victories are blocked at both the legacy and the new countdown layers introduced in v1.4.0.

---

## Troubleshooting & Diagnostics

The mod ships with Python developer tools in the `tools/` folder. **These are for developers only — end users do not need them.**

```bash
# Instantly check if the mod applied correctly to the live running game
python tools/check_now.py

# Watch logs in real time during gameplay
python tools/watch_logs.py

# Full session health report
python tools/analyze_session.py
```

See [`tools/README.md`](./tools/README.md) for full documentation.

---

## For Modders

See [`MODDERS_GUIDE.md`](./MODDERS_GUIDE.md) for architecture details, how to enable in-game debug logging, and how to extend the mod.

---

## Known Limitations

- The **AI will still internally plan** toward disabled victories (strategies are registered but unachievable). This has no gameplay effect — the AI simply cannot complete them.
- The **"One More Turn" button** in multiplayer is a base game bug unrelated to this mod.
- Requires a **new game** — changes do not apply to saves started without the mod.
