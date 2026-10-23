"""Install replacement data files into AC Odyssey forges in place (the Forger / BFR v2 method).

  python aco_install.py install <payload_dir>    files named <IDHEX>[_anything].data (packed data containers);
                                                 <payload_dir>/root/* replace game-root files (e.g. .prefetch), backed up
  python aco_install.py uninstall                restore every touched index row and truncate the appended tails
  python aco_install.py status

Each payload replaces EVERY copy of the data file with that ID (root forges and dlc_<n>/*.forge; DLC forges repackage
character files and win over DataPC_SharedGroup_00): the bytes are appended at the end of each forge, its 20-byte index row (offset, id, size) and
the size field of its name-table row are repointed. Uninstall writes the original rows back and truncates the forge to
its original length, so the forge is byte-identical to vanilla again. Root files are copied over the game's own after
a backup to <game>\\.karin_aco_backup\\ (hash-checked and restored on uninstall).
State: <game>\\.karin_aco_state.json (install refuses to run over an existing state).
Game folder: --game or ACO_GAME_DIR (the redeployable package's _env.cmd sets it, falling back to the Ubisoft Connect
registry); portable kit: no written-in default, a missing folder stops before anything is touched.
"""
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys

GAME = os.environ.get("ACO_GAME_DIR") or ""
STATE = os.path.join(GAME, ".karin_aco_state.json")
BACKUP = os.path.join(GAME, ".karin_aco_backup")


def set_game(path):
    """game folder from --game / ACO_GAME_DIR (portable kit: no written-in default)"""
    global GAME, STATE, BACKUP
    if not path:
        raise SystemExit("set ACO_GAME_DIR (the game folder with ACOdyssey.exe) or pass --game")
    GAME = path
    STATE = os.path.join(GAME, ".karin_aco_state.json")
    BACKUP = os.path.join(GAME, ".karin_aco_backup")
def all_forges():
    """game-relative paths of every forge: the root ones and dlc_<n>\\*.forge"""
    out = [n for n in sorted(os.listdir(GAME)) if n.endswith(".forge")]
    for d in sorted(os.listdir(GAME)):
        if d.startswith("dlc_") and os.path.isdir(os.path.join(GAME, d)):
            out += [os.path.join(d, n) for n in sorted(os.listdir(os.path.join(GAME, d))) if n.endswith(".forge")]
    return out


def game_stopped():
    out = subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower()
    if "acodyssey" in out:
        raise SystemExit("close the game first")


def rows_with_pos(path):
    """index rows with their file positions: {id: (row_pos, name_pos, offset, size)}"""
    out = {}
    with open(path, "rb") as f:
        f.read(9)
        _, hdr = struct.unpack("<IQ", f.read(12))
        f.seek(hdr)
        count, _, _, _, _, _, _, pos = struct.unpack("<IIqqiIIq", f.read(44))
        while pos != -1:
            f.seek(pos)
            n, _, idx_off, nxt, _, _, name_off, _ = struct.unpack("<IIqqIIqq", f.read(48))
            f.seek(idx_off)
            raw = f.read(20 * n)
            for i in range(n):
                off, oid, size = struct.unpack_from("<qQi", raw, 20 * i)
                out[oid] = (idx_off + 20 * i, name_off + 0xC0 * i, off, size)
            pos = nxt
    return out


def save_state(st):
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, STATE)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while b := f.read(1 << 24):
            h.update(b)
    return h.hexdigest()


def install(src):
    game_stopped()
    if os.path.exists(STATE):
        raise SystemExit("already installed; uninstall first")
    payloads = {}
    for n in sorted(os.listdir(src)):
        if n.endswith(".data"):
            payloads[int(n[:16], 16)] = os.path.join(src, n)
    # every copy: DLC forges (dlc_*\) repackage many character files and override DataPC_SharedGroup_00 in the main
    # world (2026-10-19 test: the dlc_58 VisualMaster/container copies won), patch_01 overrides them all
    skip = set()  # <payload>/skip.tsv: IDHEX <tab> forge (game-relative) copies to leave vanilla
    if os.path.exists(os.path.join(src, "skip.tsv")):
        for line in open(os.path.join(src, "skip.tsv")):
            if line.strip() and not line.startswith("#"):
                i, fg = line.rstrip("\n").split("\t")
                skip.add((int(i, 16), os.path.normcase(fg)))
    plan = {}
    for fg in all_forges():
        rows = rows_with_pos(os.path.join(GAME, fg))
        ids = [oid for oid in payloads if oid in rows and (oid, os.path.normcase(fg)) not in skip]
        if ids:
            plan[fg] = {"rows": rows, "ids": ids}
    for oid in payloads:
        where = [fg for fg, p in plan.items() if oid in p["ids"]]
        if not where:
            raise SystemExit(f"{oid:016X} not found in any forge")
        print(f"{oid:016X}\t" + ", ".join(where))
    root_src = os.path.join(src, "root")
    roots = sorted(os.listdir(root_src)) if os.path.isdir(root_src) else []
    for n in roots:
        if not os.path.exists(os.path.join(GAME, n)):
            raise SystemExit(f"root file {n} has no game original")
    st = {"source": os.path.abspath(src), "forges": {}, "root": {}}
    for fg, p in plan.items():
        path = os.path.join(GAME, fg)
        st["forges"][fg] = {"size": os.path.getsize(path), "rows": {}}
        for oid in p["ids"]:
            row_pos, name_pos, off, size = p["rows"][oid]
            with open(path, "rb") as f:
                f.seek(row_pos)
                row = f.read(20)
                f.seek(name_pos)
                name_row = f.read(4)
            st["forges"][fg]["rows"][f"{oid:016X}"] = [row_pos, row.hex(), name_pos, name_row.hex()]
    os.makedirs(BACKUP, exist_ok=True)
    for n in roots:
        shutil.copy2(os.path.join(GAME, n), os.path.join(BACKUP, n))
        st["root"][n] = sha(os.path.join(BACKUP, n))
    save_state(st)  # state first: an interrupted install can still be undone
    for n in roots:
        shutil.copy2(os.path.join(root_src, n), os.path.join(GAME, n))
        print(f"root	{n}	replaced (backup {st['root'][n][:12]})")
    for fg, p in plan.items():
        path = os.path.join(GAME, fg)
        with open(path, "r+b") as f:
            for oid in p["ids"]:
                row_pos, name_pos, _, _ = p["rows"][oid]
                data = open(payloads[oid], "rb").read()
                f.seek(0, 2)
                at = f.tell()
                f.write(data)
                f.seek(row_pos)
                f.write(struct.pack("<qQi", at, oid, len(data)))
                f.seek(name_pos)
                f.write(struct.pack("<I", len(data)))
                print(f"{fg}\t{oid:016X}\t{len(data)} bytes at {at}")
            f.flush()
            os.fsync(f.fileno())


def uninstall():
    game_stopped()
    if not os.path.exists(STATE):
        print("nothing installed")
        return
    st = json.load(open(STATE))
    for fg, s in st["forges"].items():
        path = os.path.join(GAME, fg)
        with open(path, "r+b") as f:
            for oid, (row_pos, row, name_pos, name_row) in s["rows"].items():
                f.seek(row_pos)
                f.write(bytes.fromhex(row))
                f.seek(name_pos)
                f.write(bytes.fromhex(name_row))
            f.truncate(s["size"])
        print(f"{fg}: {len(s['rows'])} rows restored, size {s['size']}")
    for n, h in st.get("root", {}).items():
        b = os.path.join(BACKUP, n)
        if sha(b) != h:
            raise SystemExit(f"backup of {n} does not match its recorded hash; not restoring")
        shutil.copy2(b, os.path.join(GAME, n))
        os.remove(b)
        print(f"root	{n}	restored")
    os.remove(STATE)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("install", "uninstall", "status"))
    ap.add_argument("payload_dir", nargs="?", help="install: folder with the <IDHEX>_*.data payloads (+ skip.tsv, root/)")
    ap.add_argument("--game", default=os.environ.get("ACO_GAME_DIR"), help="game folder (default: ACO_GAME_DIR)")
    a = ap.parse_args()
    if a.cmd == "install" and not a.payload_dir:
        ap.error("install needs <payload_dir>")
    set_game(a.game)
    cmd = a.cmd
    if cmd == "install":
        install(a.payload_dir)
    elif cmd == "uninstall":
        uninstall()
    elif cmd == "status":
        print(open(STATE).read() if os.path.exists(STATE) else "vanilla (no state)")
