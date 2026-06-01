#!/usr/bin/env python3
"""
live_query.py — Direct live query of Civ7 gameplay DB via Tuner WebSocket
=========================================================================
Civ7's Tuner exposes a WebSocket on port 9444 (or 9180).
We send JS snippets to it and get the results back — exactly like the
Firaxis Live Tuner tool, but from Python.

Usage:
    python tools/live_query.py                  # run full victory diagnostics
    python tools/live_query.py --port 9180      # try alternate port
    python tools/live_query.py --js "Database.query('gameplay','SELECT * FROM Victories')"
"""

import sys, io, json, socket, struct, hashlib, base64, time, argparse, random, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

DEFAULT_PORTS = [9444, 9180]

# ── WebSocket handshake + frame helpers ──────────────────────────────────────

def ws_connect(host, port, timeout=5):
    key = base64.b64encode(bytes(random.randint(0,255) for _ in range(16))).decode()
    sock = socket.create_connection((host, port), timeout=timeout)
    handshake = (
        f"GET / HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        f"Upgrade: websocket\r\n"
        f"Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        f"Sec-WebSocket-Version: 13\r\n\r\n"
    )
    sock.sendall(handshake.encode())
    resp = b""
    while b"\r\n\r\n" not in resp:
        resp += sock.recv(1024)
    if b"101" not in resp:
        raise ConnectionError(f"WebSocket upgrade failed: {resp[:200]}")
    return sock

def ws_send(sock, msg: str):
    data = msg.encode('utf-8')
    length = len(data)
    mask_key = bytes(random.randint(0,255) for _ in range(4))
    masked = bytes(data[i] ^ mask_key[i % 4] for i in range(length))
    if length < 126:
        header = bytes([0x81, 0x80 | length]) + mask_key
    elif length < 65536:
        header = bytes([0x81, 0xFE]) + struct.pack('>H', length) + mask_key
    else:
        header = bytes([0x81, 0xFF]) + struct.pack('>Q', length) + mask_key
    sock.sendall(header + masked)

def ws_recv(sock, timeout=5):
    sock.settimeout(timeout)
    chunks = []
    try:
        while True:
            header = sock.recv(2)
            if not header or len(header) < 2:
                break
            opcode = header[0] & 0x0F
            fin    = (header[0] & 0x80) != 0
            length = header[1] & 0x7F
            if length == 126:
                length = struct.unpack('>H', sock.recv(2))[0]
            elif length == 127:
                length = struct.unpack('>Q', sock.recv(8))[0]
            payload = b""
            while len(payload) < length:
                payload += sock.recv(length - len(payload))
            chunks.append(payload.decode('utf-8', errors='replace'))
            if fin:
                break
    except socket.timeout:
        pass
    return ''.join(chunks)

# ── Query runner ─────────────────────────────────────────────────────────────

def run_js(sock, js: str, wait=2.0) -> str:
    ws_send(sock, js)
    time.sleep(wait)
    return ws_recv(sock, timeout=wait)

# ── Victory diagnostics ───────────────────────────────────────────────────────

QUERIES = {
    "Victories (Modern)": (
        "Database.query('gameplay',"
        "\"SELECT VictoryType, EnabledByDefault, RequirementSetId "
        "FROM Victories WHERE VictoryType LIKE '%MODERN%'\")"
    ),
    "VictoryTypes (Modern)": (
        "Database.query('gameplay',"
        "\"SELECT VictoryType, PrereqRequirementSetId, CountdownDuration "
        "FROM VictoryTypes WHERE VictoryType LIKE '%MODERN%'\")"
    ),
    "REQ_VICTORY_NEVER_MET in Requirements": (
        "Database.query('gameplay',"
        "\"SELECT RequirementId, RequirementType, Inverse "
        "FROM Requirements WHERE RequirementId = 'REQ_VICTORY_NEVER_MET'\")"
    ),
    "REQSET_VICTORY_NEVER_MET in RequirementSets": (
        "Database.query('gameplay',"
        "\"SELECT RequirementSetId, RequirementSetType "
        "FROM RequirementSets WHERE RequirementSetId = 'REQSET_VICTORY_NEVER_MET'\")"
    ),
    "AgeProgressionTurns": (
        "Database.query('gameplay',"
        "\"SELECT AgeProgressionTurnType, Points FROM AgeProgressionTurns\")"
    ),
    "Strategies (Modern countdown)": (
        "Database.query('gameplay',"
        "\"SELECT StrategyType, CountdownVictoryType, MinNumConditionsNeeded, MaxNumConditionsNeeded "
        "FROM Strategies WHERE CountdownVictoryType LIKE '%MODERN%' "
        "GROUP BY CountdownVictoryType ORDER BY CountdownVictoryType\")"
    ),
    "Current Age": (
        "JSON.stringify({age: Game?.age, isFinalAge: Game?.AgeProgressManager?.isFinalAge})"
    ),
}

# ── Pretty printer ────────────────────────────────────────────────────────────

class C:
    R='\033[0m'; B='\033[1m'; RED='\033[91m'; GRN='\033[92m'
    YLW='\033[93m'; CYN='\033[96m'; DIM='\033[2m'

def enable_ansi():
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.kernel32.SetConsoleMode(ctypes.windll.kernel32.GetStdHandle(-11), 7)

def annotate(label, rows):
    if not isinstance(rows, list): return str(rows)
    lines = []
    for r in rows:
        if isinstance(r, dict):
            parts = []
            for k,v in r.items():
                # Annotate key values
                if k == 'RequirementSetId':
                    blocked = v == 'REQSET_VICTORY_NEVER_MET'
                    tag = f"{C.GRN}[BLOCKED]{C.R}" if blocked else f"{C.RED}[NOT BLOCKED]{C.R}"
                    parts.append(f"{k}={v} {tag}")
                elif k == 'Points':
                    frozen = (v == 0 or v == '0')
                    tag = f"{C.GRN}[frozen]{C.R}" if frozen else f"{C.YLW}[active]{C.R}"
                    parts.append(f"{k}={v} {tag}")
                elif k == 'MinNumConditionsNeeded':
                    blocked = isinstance(v, (int,float)) and v >= 100
                    tag = f"{C.GRN}[AI blocked]{C.R}" if blocked else f"{C.YLW}[AI active]{C.R}"
                    parts.append(f"{k}={v} {tag}")
                else:
                    parts.append(f"{k}={v}")
            lines.append("  " + "  |  ".join(parts))
        else:
            lines.append(f"  {r}")
    return '\n'.join(lines) if lines else f"  {C.YLW}(empty){C.R}"

def print_result(label, raw):
    print(f"\n{C.CYN}{C.B}-- {label} --{C.R}")
    if not raw:
        print(f"  {C.YLW}(no response){C.R}")
        return
    # Try to parse as JSON
    try:
        parsed = json.loads(raw)
        print(annotate(label, parsed))
    except:
        # Raw string result (e.g. Game.age)
        print(f"  {C.DIM}{raw[:500]}{C.R}")

# ── Main ──────────────────────────────────────────────────────────────────────

def run(host, ports, custom_js=None):
    enable_ansi()
    sock = None
    connected_port = None

    for port in ports:
        try:
            print(f"Connecting to Tuner on {host}:{port}...", end=' ', flush=True)
            sock = ws_connect(host, port)
            connected_port = port
            print(f"{C.GRN}Connected!{C.R}")
            break
        except Exception as e:
            print(f"{C.RED}Failed ({e}){C.R}")

    if not sock:
        print(f"\n{C.RED}Could not connect to Civ7 Tuner on any port.{C.R}")
        print("Make sure the game is running and Tuner is enabled.")
        print("You may need to launch Civ7 with '-Tuner' flag or enable it in AppOptions.txt")
        return

    if custom_js:
        print(f"\nRunning: {custom_js}")
        result = run_js(sock, custom_js, wait=3)
        print(result)
    else:
        print(f"\n{C.B}{'='*60}{C.R}")
        print(f"{C.B}  Civ7 Victory Settings -- Live DB Query (port {connected_port}){C.R}")
        print(f"{C.B}{'='*60}{C.R}")
        for label, js in QUERIES.items():
            result = run_js(sock, js, wait=1.5)
            print_result(label, result)

    sock.close()
    print(f"\n{C.DIM}Done.{C.R}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=None)
    parser.add_argument('--js', help='Run a single JS expression and print result')
    args = parser.parse_args()
    ports = [args.port] if args.port else DEFAULT_PORTS
    run(args.host, ports, args.js)
