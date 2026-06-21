/**
 * @file victory-settings-logger.js
 * @mod  civ7-mod-victory-settings
 *
 * Lightweight diagnostic logger for the Victory Settings mod.
 *
 * BY DEFAULT THIS IS SILENT — it writes nothing to UI.log in normal play.
 * To enable full diagnostics, set MOD_DEBUG = true below.
 *
 * When enabled it logs one line at load confirming the mod is active,
 * and (in debug mode) a full table-by-table report of every DB value
 * the mod controls so developers can verify the mod applied correctly.
 *
 * Filter UI.log for:  [VictorySettings]
 * Or run:             python tools/check_now.py     (live DB query)
 *                     python tools/watch_logs.py    (real-time log watcher)
 */

// ─── CONFIG ──────────────────────────────────────────────────────────────────

/**
 * Set to true to enable verbose diagnostic output in UI.log.
 * Leave false for normal gameplay — no log spam for end users.
 *
 * @type {boolean}
 */
const MOD_DEBUG = false;

const MOD_TAG     = '[VictorySettings]';
const MOD_VERSION = '1.5.0';

// ─── Logging helpers ──────────────────────────────────────────────────────────

/** Always logs — used for the single load-confirmation line. */
function modLog(msg)  { console.log  (`${MOD_TAG} ${msg}`); }

/** Debug-only helpers — silent when MOD_DEBUG is false. */
function dbgLog(msg)  { if (MOD_DEBUG) console.log  (`${MOD_TAG} ${msg}`); }
function dbgWarn(msg) { if (MOD_DEBUG) console.warn (`${MOD_TAG} [WARN]  ${msg}`); }
function dbgErr(msg)  { if (MOD_DEBUG) console.error(`${MOD_TAG} [ERROR] ${msg}`); }
function dbgOk(msg)   { if (MOD_DEBUG) console.log  (`${MOD_TAG} [OK]    ${msg}`); }

function dbgSection(title) {
    if (!MOD_DEBUG) return;
    const pad = Math.max(0, 48 - title.length);
    console.log(`${MOD_TAG} --- ${title} ${'-'.repeat(pad)}`);
}

function dbgRow(label, value) {
    if (!MOD_DEBUG) return;
    const v = (value === null || value === undefined) ? 'NULL' : String(value);
    console.log(`${MOD_TAG}   ${label.padEnd(36)}: ${v}`);
}

// ─── Database helper ──────────────────────────────────────────────────────────

/**
 * Run a SQL query against the gameplay database.
 * Returns an array of row objects, or [] on error.
 * @param {string} sql
 * @returns {Array<object>}
 */
function gq(sql) {
    try {
        return Database.query('gameplay', sql) ?? [];
    } catch (e) {
        dbgWarn(`DB query failed: ${e} | SQL: ${sql.slice(0, 80)}`);
        return [];
    }
}

// ─── Diagnostic sections (debug-only) ────────────────────────────────────────

const MODERN_VICTORIES = [
    'VICTORY_MILITARY_MODERN',
    'VICTORY_SCIENCE_MODERN',
    'VICTORY_ECONOMIC_MODERN',
    'VICTORY_CULTURE_MODERN',
];

function diagGameState() {
    dbgSection('GAME STATE');
    try {
        const age = GameInfo.Ages.lookup(Game.age);
        dbgRow('Current Age',      age?.AgeType ?? 'Unknown');
        dbgRow('Is Final Age',     Game.AgeProgressManager?.isFinalAge);
        dbgRow('Is Extended Game', Game.AgeProgressManager?.isExtendedGame);
    } catch (e) {
        dbgWarn(`Could not read game state: ${e}`);
    }
}

function diagSetupParameters() {
    dbgSection('SETUP PARAMETERS');
    const params = [
        'MilitaryVictoryEnabled',
        'ScienceVictoryEnabled',
        'EconomicVictoryEnabled',
        'CultureVictoryEnabled',
        'AgeProgressionFromTurnCounterEnabled',
        'AgeProgressionFromPlayerEliminatedEnabled',
    ];
    for (const id of params) {
        try {
            const p = GameSetup.findGameParameter(id);
            if (p) {
                const val     = p.value?.value;
                const enabled = (val === 1 || val === true || val === '1' || val === 'true');
                dbgRow(id, `${val} (${enabled ? 'ENABLED' : 'DISABLED'})`);
            } else {
                dbgWarn(`Parameter not registered: ${id}`);
            }
        } catch (e) {
            dbgErr(`Reading ${id}: ${e}`);
        }
    }
}

function diagRequirementBlock() {
    dbgSection('REQUIREMENT BLOCK');

    const reqs = gq(
        "SELECT RequirementId, RequirementType, Inverse " +
        "FROM Requirements WHERE RequirementId = 'REQ_VICTORY_NEVER_MET'"
    );
    if (reqs.length === 0) {
        dbgErr('REQ_VICTORY_NEVER_MET missing — block NOT applied!');
    } else {
        dbgRow('RequirementType', reqs[0].RequirementType);
        dbgRow('Inverse',         reqs[0].Inverse);
        dbgOk('REQ_VICTORY_NEVER_MET present');
    }

    const sets = gq(
        "SELECT RequirementSetId FROM RequirementSets " +
        "WHERE RequirementSetId = 'REQSET_VICTORY_NEVER_MET'"
    );
    sets.length === 0
        ? dbgErr('REQSET_VICTORY_NEVER_MET missing!')
        : dbgOk('REQSET_VICTORY_NEVER_MET present');

    const links = gq(
        "SELECT RequirementSetId FROM RequirementSetRequirements " +
        "WHERE RequirementSetId = 'REQSET_VICTORY_NEVER_MET'"
    );
    links.length === 0
        ? dbgErr('RequirementSetRequirements link missing!')
        : dbgOk(`RequirementSetRequirements link present (${links.length} row(s))`);
}

function diagVictories() {
    dbgSection('VICTORIES TABLE');
    for (const vt of MODERN_VICTORIES) {
        const rows = gq(
            `SELECT EnabledByDefault, RequirementSetId FROM Victories WHERE VictoryType = '${vt}'`
        );
        if (rows.length === 0) {
            dbgWarn(`${vt}: not in Victories table`);
            continue;
        }
        const v       = rows[0];
        const blocked = v.RequirementSetId === 'REQSET_VICTORY_NEVER_MET';
        dbgRow(vt, `Enabled=${v.EnabledByDefault}  ReqSet=${v.RequirementSetId}  [${blocked ? 'BLOCKED' : 'NOT BLOCKED'}]`);
    }
}

function diagVictoryTypes() {
    dbgSection('VICTORY TYPES (countdown system)');
    for (const vt of MODERN_VICTORIES) {
        const rows = gq(
            `SELECT PrereqRequirementSetId, CountdownDuration FROM VictoryTypes WHERE VictoryType = '${vt}'`
        );
        if (rows.length === 0) {
            dbgWarn(`${vt}: not in VictoryTypes table`);
            continue;
        }
        const v       = rows[0];
        const blocked = v.PrereqRequirementSetId === 'REQSET_VICTORY_NEVER_MET';
        dbgRow(vt, `Prereq=${v.PrereqRequirementSetId}  Countdown=${v.CountdownDuration}  [${blocked ? 'BLOCKED' : 'NOT BLOCKED'}]`);
    }
}

function diagAgeProgression() {
    dbgSection('AGE PROGRESSION TURNS');
    const rows = gq('SELECT AgeProgressionTurnType, Points FROM AgeProgressionTurns');
    if (rows.length === 0) {
        dbgWarn('AgeProgressionTurns is empty (may be correct if turn counter is enabled)');
    } else {
        for (const r of rows) {
            const frozen = (r.Points === 0 || r.Points === '0');
            dbgRow(r.AgeProgressionTurnType, `Points=${r.Points}  [${frozen ? 'frozen' : 'ACTIVE'}]`);
        }
    }
}

function diagStrategies() {
    dbgSection('AI STRATEGIES (modern countdown)');
    const rows = gq(
        "SELECT StrategyType, CountdownVictoryType, MinNumConditionsNeeded, MaxNumConditionsNeeded " +
        "FROM Strategies WHERE CountdownVictoryType LIKE 'VICTORY_%_MODERN' " +
        "GROUP BY CountdownVictoryType ORDER BY CountdownVictoryType"
    );
    if (rows.length === 0) {
        dbgWarn('No modern countdown Strategies rows found');
    } else {
        for (const r of rows) {
            dbgRow(r.CountdownVictoryType,
                `Strategy=${r.StrategyType}  Min=${r.MinNumConditionsNeeded}  Max=${r.MaxNumConditionsNeeded}`
            );
        }
    }
}

// ─── Main diagnostic runner ───────────────────────────────────────────────────

function runDiagnostics(trigger) {
    if (MOD_DEBUG) {
        dbgLog('='.repeat(55));
        dbgLog(`DIAGNOSTIC REPORT  v${MOD_VERSION}  trigger=${trigger ?? 'game-start'}`);
        dbgLog(`Timestamp: ${new Date().toISOString()}`);
        dbgLog('='.repeat(55));
    }

    try { diagGameState();         } catch (e) { dbgErr(`diagGameState: ${e}`); }
    try { diagSetupParameters();   } catch (e) { dbgErr(`diagSetupParameters: ${e}`); }
    try { diagRequirementBlock();  } catch (e) { dbgErr(`diagRequirementBlock: ${e}`); }
    try { diagVictories();         } catch (e) { dbgErr(`diagVictories: ${e}`); }
    try { diagVictoryTypes();      } catch (e) { dbgErr(`diagVictoryTypes: ${e}`); }
    try { diagAgeProgression();    } catch (e) { dbgErr(`diagAgeProgression: ${e}`); }
    try { diagStrategies();        } catch (e) { dbgErr(`diagStrategies: ${e}`); }

    if (MOD_DEBUG) {
        dbgLog('='.repeat(55));
        dbgLog('Diagnostics complete. Run: python tools/check_now.py');
        dbgLog('='.repeat(55));
    }
}

// ─── Entry point ──────────────────────────────────────────────────────────────

// Always log one line so developers can confirm the script loaded.
modLog(`v${MOD_VERSION} loaded. MOD_DEBUG=${MOD_DEBUG}. Run python tools/check_now.py to inspect live DB.`);

// Run diagnostics at game start (silent unless MOD_DEBUG = true).
runDiagnostics('game-start');

// Re-run on age transitions so Modern Age tables are captured when they load.
try {
    engine.on('AgeChanged', () => { runDiagnostics('AgeChanged'); });
} catch (e) {
    try {
        engine.on('age-changed', () => { runDiagnostics('age-changed'); });
    } catch (e2) {
        dbgWarn(`Could not register AgeChanged listener: ${e2}`);
    }
}
