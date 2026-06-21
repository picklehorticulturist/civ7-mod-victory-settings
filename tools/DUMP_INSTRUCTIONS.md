# How to Dump the Victory Tables (for the Exploration-age win fix)

Goal: capture the exact `Victories` / `VictoryTypes` / `AgeProgressions` rows from
**your** Civ 7 1.4.0 database so the mod fix targets the real row names. Takes ~5 min
on the **Windows PC** that runs the game. Everything here is read-only and safe.

---

## Step 0 — Install Python (one time)

Windows does **not** come with Python. If you've never installed it:

1. Open the **Microsoft Store**, search **"Python 3.12"** (or 3.11/3.13), click **Get**.
   - Or download from <https://www.python.org/downloads/> and, in the installer,
     **check "Add python.exe to PATH"** before clicking Install.
2. Verify: open **Command Prompt** (Win+R → type `cmd` → Enter) and run:
   ```
   python --version
   ```
   You should see `Python 3.x.x`. If it says it's not recognized, try `py --version`
   instead — use whichever works in the steps below.

No extra packages are needed (the script uses only Python's standard library).

---

## Step 1 — Tell the game to write its database to disk

1. Press **Win + R**, paste this, press Enter:
   ```
   %LOCALAPPDATA%\Firaxis Games\Sid Meier's Civilization VII (Epic)
   ```
2. Open **`AppOptions.txt`** in Notepad. By default the line reads:
   ```
   ;CopyDatabasesToDisk 0
   ```
   The leading `;` is a comment marker, so it's currently **disabled**. Change the line to
   (remove the `;` AND set the value to `1`), then **save**:
   ```
   CopyDatabasesToDisk 1
   ```
   Leave every other `;`-prefixed line alone.

This makes the game write `Debug\gameplay-copy.sqlite` every time it loads.
**If the game was open while you edited this, fully quit and relaunch** so it re-reads the file.

---

## Step 2 — Put the dump script on the PC

Copy this one file from the Mac to the PC (the Desktop is fine — it's self-contained):

```
tools\dump_all_victories.py
```

---

## Step 3 — Load an Exploration-age save

Launch Civ 7 and **load a save that's in the Exploration age**. Let it finish loading.
You can leave the game running for the next step.

---

## Step 4 — Run the script

Open **Command Prompt** (Win+R → `cmd` → Enter) and run it against wherever you saved it,
e.g. if it's on the Desktop:

```
python %USERPROFILE%\Desktop\dump_all_victories.py
```

- If `python` isn't recognized, use `py` instead:
  ```
  py %USERPROFILE%\Desktop\dump_all_victories.py
  ```
- It prints the tables on screen **and** saves a file named **`victory_dump.txt`**
  next to the script.

---

## Step 5 — Send the result back

Send / paste the contents of **`victory_dump.txt`** (or the on-screen output).

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `'python' is not recognized` | Use `py` instead, or reinstall Python with "Add to PATH" checked. |
| Script prints **"DATABASE NOT FOUND"** | `CopyDatabasesToDisk 1` wasn't set before launch. Set it (Step 1), then launch the game once and re-run. |
| Microsoft Store opens when you type `python` | Python isn't installed yet — do Step 0. |
| Output looks empty / only Modern rows | Make sure you loaded an **Exploration-age** save, not the main menu. |

---

### What this is for

Civ 7 **1.4.0** made the four victories triggerable starting at **50% through the
Exploration age** (previously Modern only). The mod blocks victories only for
`VICTORY_*_MODERN` rows; its Exploration files only edit the AI `Strategies` table, so
the real countdown victory is never blocked in Exploration — which is why the game ends
before the Modern age. This dump reveals the exact Exploration-age victory row names so
the fix can block them the same way the Modern age already is.
