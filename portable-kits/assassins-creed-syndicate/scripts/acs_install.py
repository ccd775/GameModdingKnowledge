"""Install replacement data files into AC Syndicate forges in place (Syndicate fork of ACU/scripts/acu_install.py).

  python acs_install.py install <payload_dir | payload.tar.xz> [--game <game dir>]
  python acs_install.py uninstall [--game <game dir>]   restore every touched index row and truncate the appended tails
  python acs_install.py status [--game <game dir>]

Game folder: --game, else env ACS_GAME_DIR, else every folder holding ACS.exe found in the Steam libraries,
Ubisoft Connect (Uplay), the Windows uninstall entries and the Epic manifests: one is used directly, several are listed
to choose from (uninstall / status take the one that has the state file). Steam / Ubisoft install under Program Files
by default: without write access nothing is touched and the user is told to run the .cmd as administrator.
A .tar.xz payload (make_release.py) is unpacked to a temporary folder for the install.

Payload:
  <payload_dir>/<IDHEX>[_anything].data                 one packed data file for EVERY copy of that ID
  <payload_dir>/forge/<forge>/<IDHEX>[_anything].data   variant for one forge (<forge> = game-relative path with "\\"
                                                        written as "__"); wins over the generic file. The world
                                                        forges and their dlc_20 / dlc_21 patch forges carry different
                                                        revisions of the same file, so edits are built per copy.
  <payload_dir>/skip.tsv                                IDHEX <tab> forge copies to leave vanilla
  <payload_dir>/vanilla.tsv                             forge <tab> IDHEX <tab> size:sha1 of the vanilla copy every
                                                        forge variant / skip line was built from (make_release.py)
2026-10-30 (user): no lock to one game version (the Steam / Ubisoft copies could not be tested). Copies are matched by
ID and content, never by forge size: every copy of a payload ID in any forge of this game gets the variant built from
the same bytes (its own forge's, else any forge's), else its own forge's variant even though it differs (another
version, or another mod changed it: listed, uninstall restores it), else the generic file; with none of these it stays
vanilla (listed). Payload copies of forges this game lacks (DLC not installed) are skipped.
The bytes are appended at the end of each forge; its 20-byte index row (offset, id, size) and the size field of its
name-table row are repointed. Uninstall writes the original rows back and truncates every forge to its original length.
State: <game>\\.karin_acs_state.json (install refuses to run over an existing state).
"""
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import tarfile
import tempfile

GAME_NAME = "Assassin's Creed Syndicate"
EXE = "ACS.exe"
STEAM_APP = "368500"
REG_VIEWS = (0x200, 0x100)  # KEY_WOW64_32KEY, KEY_WOW64_64KEY: Ubisoft / Steam write the 32-bit view


def reg(hive, path, value=None, view=0):
    """a registry value as str, or with value None the subkey names; None / [] when missing (or not on Windows)"""
    try:
        import winreg
        with winreg.OpenKey(getattr(winreg, hive), path, 0, winreg.KEY_READ | view) as k:
            if value is not None:
                return str(winreg.QueryValueEx(k, value)[0])
            out = []
            while True:
                try:
                    out.append(winreg.EnumKey(k, len(out)))
                except OSError:
                    return out
    except (ImportError, OSError):
        return None if value is not None else []


def candidates():
    """[(folder, source)] of every folder holding EXE: Steam, Ubisoft Connect, uninstall entries, Epic"""
    found = []

    def add(d, source):
        if d and os.path.isfile(os.path.join(d, EXE)):
            d = os.path.normpath(d)
            if all(os.path.normcase(d) != os.path.normcase(f) for f, _ in found):
                found.append((d, source))

    steam = reg("HKEY_CURRENT_USER", r"Software\Valve\Steam", "SteamPath") or \
        next(filter(None, (reg("HKEY_LOCAL_MACHINE", r"SOFTWARE\Valve\Steam", "InstallPath", v) for v in REG_VIEWS)), None)
    if steam:  # every library; the app manifest names the folder under steamapps\common
        libs = [steam]
        try:
            vdf = open(os.path.join(steam, "steamapps", "libraryfolders.vdf"), encoding="utf-8", errors="replace").read()
            libs += [p.replace("\\\\", "\\") for p in re.findall(r'"path"\s+"([^"]+)"', vdf)]
        except OSError:
            pass
        for lib in libs:
            sub = GAME_NAME
            try:
                acf = open(os.path.join(lib, "steamapps", f"appmanifest_{STEAM_APP}.acf"), encoding="utf-8", errors="replace").read()
                sub = re.search(r'"installdir"\s+"([^"]+)"', acf).group(1)
            except (OSError, AttributeError):
                pass
            add(os.path.join(lib, "steamapps", "common", sub), "Steam")
    base = r"SOFTWARE\Ubisoft\Launcher\Installs"  # Ubisoft Connect (Uplay): one subkey per game, InstallDir "<drive>:/Games/x/"
    for v in REG_VIEWS:
        for gid in reg("HKEY_LOCAL_MACHINE", base, view=v):
            add(reg("HKEY_LOCAL_MACHINE", base + "\\" + gid, "InstallDir", v), "Ubisoft Connect")
    base = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"  # "Steam App 368500", "Uplay Install <id>", others
    for hive in ("HKEY_LOCAL_MACHINE", "HKEY_CURRENT_USER"):
        for v in REG_VIEWS:
            for k in reg(hive, base, view=v):
                if "syndicate" in (reg(hive, base + "\\" + k, "DisplayName", v) or "").lower():
                    add(reg(hive, base + "\\" + k, "InstallLocation", v), "installed programs")
    pd = os.environ.get("PROGRAMDATA")
    man = os.path.join(pd, "Epic", "EpicGamesLauncher", "Data", "Manifests") if pd else ""
    for f in sorted(os.listdir(man)) if os.path.isdir(man) else []:
        try:
            add(json.load(open(os.path.join(man, f), encoding="utf-8")).get("InstallLocation"), "Epic Games")
        except (OSError, ValueError, AttributeError):
            pass
    return found


def find_game(argv, cmd=""):
    """--game <dir>, env ACS_GAME_DIR, or the install found by candidates() (asks when there are several)"""
    if "--game" in argv:
        return argv[argv.index("--game") + 1]
    if os.environ.get("ACS_GAME_DIR"):
        return os.environ["ACS_GAME_DIR"]
    found = candidates()
    if cmd in ("uninstall", "status"):
        done = [c for c in found if os.path.exists(os.path.join(c[0], ".karin_acs_state.json"))]
        found = done if len(done) == 1 else found
    if not found:
        raise SystemExit(f"{GAME_NAME} not found (looked in Steam, Ubisoft Connect, the installed programs, Epic); "
                         f"pass --game <folder that holds {EXE}>")
    if len(found) == 1:
        print(f"found ({found[0][1]}): {found[0][0]}")
        return found[0][0]
    print("several installs found:")
    for i, (d, source) in enumerate(found, 1):
        print(f"  {i}. {d}  ({source})")
    try:
        n = int(input(f"which one [1-{len(found)}]? "))
    except (EOFError, ValueError):
        n = 0
    if not 1 <= n <= len(found):
        raise SystemExit(f"no folder chosen; pass --game <folder that holds {EXE}>")
    return found[n - 1][0]


GAME = os.environ.get("ACS_GAME_DIR", "")  # find_game() in __main__; build_mod.py / make_release.py set it
STATE = os.path.join(GAME, ".karin_acs_state.json")


def all_forges():
    """game-relative paths of every forge: the root ones and dlc_<n>\\*.forge"""
    out = [n for n in sorted(os.listdir(GAME)) if n.endswith(".forge")]
    for d in sorted(os.listdir(GAME)):
        if d.startswith("dlc_") and os.path.isdir(os.path.join(GAME, d)):
            out += [os.path.join(d, n) for n in sorted(os.listdir(os.path.join(GAME, d))) if n.endswith(".forge")]
    return out


def game_stopped():
    out = subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower()
    if EXE.lower() in out:
        raise SystemExit("close the game first")


def rows_with_pos(path):
    """index rows with their file positions: {id: (row_pos, name_pos, offset, size)}"""
    out = {}
    with open(path, "rb") as f:
        if f.read(9) != b"scimitar\0":
            raise SystemExit(f"{path}: not a forge")
        version, hdr = struct.unpack("<IQ", f.read(12))
        if version not in (27, 28):  # AnvilNext 2.0 index layout (Syndicate 27)
            raise SystemExit(f"{path}: forge version {version}, not AC Syndicate")
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


def fingerprint(f, off, size):
    """size:sha1 of the bytes of one index row"""
    h = hashlib.sha1()
    f.seek(off)
    left = size
    while left > 0:
        b = f.read(min(left, 1 << 22))
        if not b:
            break
        h.update(b)
        left -= len(b)
    return f"{size}:{h.hexdigest()}"


def check_writable(forges):
    """fail before anything is written when the game folder needs admin rights (Steam / Ubisoft under Program Files)"""
    try:
        with open(STATE + ".tmp", "w"):
            pass
        os.remove(STATE + ".tmp")
        for fg in forges:
            with open(os.path.join(GAME, fg), "r+b"):
                pass
    except PermissionError:
        raise SystemExit(f"no write access to {GAME}: run the .cmd as administrator "
                         "(right-click > Run as administrator); nothing was changed")


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
        with tempfile.TemporaryDirectory(prefix="karin_acs_") as tmp:
            print(f"unpacking {src} ...", flush=True)
            with tarfile.open(src) as t:
                if hasattr(tarfile, "data_filter"):
                    t.extractall(tmp, filter="data")
                else:
                    t.extractall(tmp)
            return install(os.path.join(tmp, "payload"))
    prints = {}  # (normcase forge, id) -> fingerprint of the vanilla copy its variant / skip line was built from
    if os.path.exists(os.path.join(src, "vanilla.tsv")):
        for line in open(os.path.join(src, "vanilla.tsv"), encoding="utf-8"):
            fg, i, fp = line.rstrip("\n").split("\t")
            prints[(os.path.normcase(fg), int(i, 16))] = fp
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
    by_print = {}  # (id, vanilla fingerprint) -> the variant built from those bytes, None = a skip line
    for (fg, oid), fp in prints.items():
        if (oid, fg) in skip or oid in variants.get(fg, {}):
            by_print.setdefault((oid, fp), variants.get(fg, {}).get(oid))
    plan, seen, same, moved, differs, kept = {}, set(), 0, [], [], []
    print("checking the game's copies of the payload data files ...", flush=True)
    for fg in all_forges():
        path, nfg = os.path.join(GAME, fg), os.path.normcase(fg)
        rows = rows_with_pos(path)
        files = {}
        with open(path, "rb") as f:
            for oid in sorted(ids & rows.keys()):
                seen.add((nfg, oid))
                if (oid, nfg) in skip:
                    continue
                fp = fingerprint(f, *rows[oid][2:])
                own = variants.get(nfg, {}).get(oid)
                if own and prints.get((nfg, oid), fp) == fp:
                    files[oid] = own
                    same += 1
                elif (oid, fp) in by_print:
                    if by_print[(oid, fp)]:
                        files[oid] = by_print[(oid, fp)]
                        moved.append(f"{oid:016X} in {fg}: {os.path.relpath(files[oid], src)}")
                elif own:
                    files[oid] = own
                    differs.append(f"{oid:016X} in {fg}")
                elif oid in generic:
                    files[oid] = generic[oid]
                else:
                    kept.append(f"{oid:016X} in {fg}")
        if files:
            plan[fg] = {"rows": rows, "files": files}
    gone = sorted(f"{fg}: {os.path.basename(p)}" for fg, v in variants.items() for oid, p in v.items()
                  if (fg, oid) not in seen)
    for head, lst in (("payload copies whose forge or row this game does not have (DLC not installed?), skipped:", gone),
                      ("copies matched by content to another forge's variant:", moved),
                      ("copies that differ from the vanilla ones the payload was built from (another game version, or "
                       "another mod changed them), replaced anyway (uninstall restores them):", differs),
                      ("copies with no payload, left vanilla:", kept)):
        if lst:
            print(f"{head} {len(lst)}\n  " + "\n  ".join(lst[:20]) + ("\n  ..." if len(lst) > 20 else ""))
    if not plan:
        raise SystemExit(f"none of the payload's data files is in {GAME}: nothing to install")
    for oid in sorted(ids):
        where = [fg for fg, p in plan.items() if oid in p["files"]]
        print(f"{oid:016X}\t{len(where)} copies")
    print(f"{sum(len(p['files']) for p in plan.values())} copies to replace, {same} identical to the build source")
    check_writable(plan)
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
    check_writable(st["forges"])
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
    if sys.argv[1:2] in (["-h"], ["--help"]):
        print(__doc__)
        sys.exit(0)
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd in ("install", "uninstall", "status"):
        GAME = find_game(sys.argv, cmd)
        STATE = os.path.join(GAME, ".karin_acs_state.json")
        print("game:", GAME)
    if cmd == "install":
        install(sys.argv[2])
    elif cmd == "uninstall":
        uninstall()
    elif cmd == "status":
        print(open(STATE).read() if os.path.exists(STATE) else "vanilla (no state)")
    else:
        sys.exit(__doc__)
