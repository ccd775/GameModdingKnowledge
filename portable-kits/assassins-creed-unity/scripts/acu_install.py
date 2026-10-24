"""Install replacement data files into AC Unity forges in place (ACU copy of ACOd/scripts/aco_install.py).

  python acu_install.py install <payload_dir | payload.tar.xz> [--game <game dir>]
  python acu_install.py uninstall [--game <game dir>]   restore every touched index row and truncate the appended tails
  python acu_install.py status [--game <game dir>]

Game folder: --game, else env ACU_GAME_DIR, else the Steam libraries (registry SteamPath + libraryfolders.vdf).
Portable kit: no written-in default folder; not found -> stop before anything is touched.
A .tar.xz payload (make_release.py) is unpacked to a temporary folder for the install.

Payload:
  <payload_dir>/<IDHEX>[_anything].data                 one packed data file for EVERY copy of that ID
  <payload_dir>/forge/<forge>/<IDHEX>[_anything].data   variant for one forge (<forge> = game-relative path with "\\"
                                                        written as "__"); wins over the generic file. Unity's world
                                                        forges carry different revisions of the same file (CN_P_Arno:
                                                        21 copies, 13 sizes), so table edits are built per copy.
  <payload_dir>/skip.tsv                                IDHEX <tab> forge copies to leave vanilla
  <payload_dir>/vanilla_sizes.tsv                       forge <tab> size of the vanilla game the payload was built
                                                        from; install refuses to touch a forge of another size
                                                        (other game version, or another mod already in it)
Every copy of an ID (root forges and dlc_<n>/*.forge) must get a payload, otherwise nothing is written.
The bytes are appended at the end of each forge; its 20-byte index row (offset, id, size) and the size field of its
name-table row are repointed. Uninstall writes the original rows back and truncates every forge to its original length.
State: <game>\\.karin_acu_state.json (install refuses to run over an existing state).
"""
import json
import os
import re
import struct
import subprocess
import tarfile
import tempfile

GAME_NAME = "Assassin's Creed Unity"


def find_game(argv):
    """--game <dir>, env ACU_GAME_DIR, or <Steam library>/steamapps/common/Assassin's Creed Unity"""
    if "--game" in argv:
        return argv[argv.index("--game") + 1]
    if os.environ.get("ACU_GAME_DIR"):
        return os.environ["ACU_GAME_DIR"]
    libs = []
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
            steam = winreg.QueryValueEx(k, "SteamPath")[0]
        libs.append(steam)
        vdf = open(os.path.join(steam, "steamapps", "libraryfolders.vdf"), encoding="utf-8", errors="replace").read()
        libs += [p.replace("\\\\", "\\") for p in re.findall(r'"path"\s+"([^"]+)"', vdf)]
    except OSError:
        pass
    for lib in libs:
        g = os.path.join(lib, "steamapps", "common", GAME_NAME)
        if os.path.exists(os.path.join(g, "ACU.exe")):
            return os.path.normpath(g)
    raise SystemExit(f"{GAME_NAME} not found in the Steam libraries; pass --game <folder that holds ACU.exe>")


GAME = os.environ.get("ACU_GAME_DIR") or ""  # build_mod.py / make_release.py set it with find_game()
STATE = os.path.join(GAME, ".karin_acu_state.json")


def all_forges():
    """game-relative paths of every forge: the root ones and dlc_<n>\\*.forge"""
    out = [n for n in sorted(os.listdir(GAME)) if n.endswith(".forge")]
    for d in sorted(os.listdir(GAME)):
        if d.startswith("dlc_") and os.path.isdir(os.path.join(GAME, d)):
            out += [os.path.join(d, n) for n in sorted(os.listdir(os.path.join(GAME, d))) if n.endswith(".forge")]
    return out


def game_stopped():
    out = subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower()
    if "acu.exe" in out:
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


def scan(d):
    return {int(n[:16], 16): os.path.join(d, n) for n in sorted(os.listdir(d)) if n.endswith(".data")} if os.path.isdir(d) else {}


def install(src):
    game_stopped()
    if os.path.exists(STATE):
        raise SystemExit("already installed; uninstall first")
    if src.endswith((".tar.xz", ".txz")):
        with tempfile.TemporaryDirectory(prefix="karin_acu_") as tmp:
            print(f"unpacking {src} ...", flush=True)
            with tarfile.open(src) as t:
                if hasattr(tarfile, "data_filter"):
                    t.extractall(tmp, filter="data")
                else:
                    t.extractall(tmp)
            return install(os.path.join(tmp, "payload"))
    vanilla = {}
    if os.path.exists(os.path.join(src, "vanilla_sizes.tsv")):
        for line in open(os.path.join(src, "vanilla_sizes.tsv"), encoding="utf-8"):
            fg, size = line.rstrip("\n").split("\t")
            vanilla[os.path.normcase(fg)] = int(size)
    generic = scan(src)
    variants = {}  # normcase forge -> {id: path}
    vroot = os.path.join(src, "forge")
    if os.path.isdir(vroot):
        for d in sorted(os.listdir(vroot)):
            variants[os.path.normcase(d.replace("__", os.sep))] = scan(os.path.join(vroot, d))
    ids = set(generic) | {i for v in variants.values() for i in v}
    skip = set()
    if os.path.exists(os.path.join(src, "skip.tsv")):
        for line in open(os.path.join(src, "skip.tsv")):
            if line.strip() and not line.startswith("#"):
                i, fg = line.rstrip("\n").split("\t")
                skip.add((int(i, 16), os.path.normcase(fg)))
    plan, missing = {}, []
    for fg in all_forges():
        rows = rows_with_pos(os.path.join(GAME, fg))
        files = {}
        for oid in ids:
            if oid not in rows or (oid, os.path.normcase(fg)) in skip:
                continue
            p = variants.get(os.path.normcase(fg), {}).get(oid) or generic.get(oid)
            if p is None:
                missing.append(f"{oid:016X} in {fg}")
            else:
                files[oid] = p
        if files:
            plan[fg] = {"rows": rows, "files": files}
    if missing:
        raise SystemExit("no payload for these copies (add a forge variant or a skip.tsv line):\n  " + "\n  ".join(missing))
    wrong = [f"{fg}: {os.path.getsize(os.path.join(GAME, fg))} bytes, payload built for {vanilla.get(os.path.normcase(fg))}"
             for fg in plan if vanilla and vanilla.get(os.path.normcase(fg)) != os.path.getsize(os.path.join(GAME, fg))]
    if wrong:
        raise SystemExit("these forges differ from the vanilla game the payload was built for (other game version, or "
                         "modified; Steam > Verify integrity restores them):\n  " + "\n  ".join(wrong))
    unused = [f"{fg}: {os.path.basename(p)}" for fg, v in variants.items() for oid, p in v.items()
              if not any(os.path.normcase(f) == fg and oid in q["files"] for f, q in plan.items())]
    if unused:
        raise SystemExit("forge variants that match no index row:\n  " + "\n  ".join(unused))
    for oid in sorted(ids):
        where = [fg for fg, p in plan.items() if oid in p["files"]]
        if not where:
            raise SystemExit(f"{oid:016X} not found in any forge")
        print(f"{oid:016X}\t{len(where)} copies")
    st = {"source": os.path.abspath(src), "forges": {}}
    for fg, p in plan.items():
        path = os.path.join(GAME, fg)
        st["forges"][fg] = {"size": os.path.getsize(path), "rows": {}}
        with open(path, "rb") as f:
            for oid in p["files"]:
                row_pos, name_pos, _, _ = p["rows"][oid]
                f.seek(row_pos)
                row = f.read(20)
                f.seek(name_pos)
                name_row = f.read(4)
                st["forges"][fg]["rows"][f"{oid:016X}"] = [row_pos, row.hex(), name_pos, name_row.hex()]
    save_state(st)  # state first: an interrupted install can still be undone
    for fg, p in plan.items():
        path = os.path.join(GAME, fg)
        with open(path, "r+b") as f:
            for oid, src_file in p["files"].items():
                row_pos, name_pos, _, _ = p["rows"][oid]
                data = open(src_file, "rb").read()
                f.seek(0, 2)
                at = f.tell()
                f.write(data)
                f.seek(row_pos)
                f.write(struct.pack("<qQi", at, oid, len(data)))
                f.seek(name_pos)
                f.write(struct.pack("<I", len(data)))
                print(f"{fg}\t{oid:016X}\t{os.path.relpath(src_file, src)}\t{len(data)} bytes at {at}")
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
    os.remove(STATE)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("install", "uninstall", "status"))
    ap.add_argument("payload", nargs="?", help="install: payload folder or payload_<label>.tar.xz (make_release.py)")
    ap.add_argument("--game", help="game folder with ACU.exe (default: ACU_GAME_DIR, else the Steam libraries)")
    a = ap.parse_args()
    if a.cmd == "install" and not a.payload:
        ap.error("install needs <payload_dir | payload.tar.xz>")
    GAME = find_game(["--game", a.game] if a.game else [])
    STATE = os.path.join(GAME, ".karin_acu_state.json")
    print("game:", GAME)
    if a.cmd == "install":
        install(a.payload)
    elif a.cmd == "uninstall":
        uninstall()
    else:
        print(open(STATE).read() if os.path.exists(STATE) else "vanilla (no state)")
