"""Find and extract Odyssey data files by name or ID using the forge indexes (aco_forge.py index output).

  python aco_locate.py find <name|idhex|/regex/> [...]          every forge holding it (winner first)
  python aco_locate.py extract <out_dir> <name|idhex> [...]    winner -> <out_dir>/<forge stem>/<index>_-_<name>.data

Winner (main world) = DataPC_patch_01, then the other main forges, then DLC patch / DLC forges (DLC areas load their
own copies of many character files: DataPC_<n>_dlc, DataPC_ACD_Connection, ...).
Indexes: ACO_CACHE (or --cache) = the folder holding main_index.tsv / dlc_index.tsv. extract reads the forges from the
game folder ACO_GAME_DIR (or --game). Portable kit: neither has a written-in default; a missing one stops with its name.
"""
import os
import re
import sys

CACHE = os.environ.get("ACO_CACHE")
GAME = os.environ.get("ACO_GAME_DIR")

_rows = None


def rows():
    global _rows
    if _rows is None:
        _rows = []
        for n in ("main_index.tsv", "dlc_index.tsv"):
            p = os.path.join(CACHE, n)
            if not os.path.exists(p):
                continue
            with open(p, encoding="utf-8", errors="replace") as f:
                for line in f:
                    fg, i, oid, off, size, name = line.rstrip("\n").split("\t", 5)
                    _rows.append((fg, int(i), int(oid, 16), int(off), int(size), name))
    return _rows


def rank(fg):
    f = fg.lower()
    dlc = "_dlc" in f or "connection" in f or "throneroom" in f
    return (2 if dlc else 0) + (0 if "patch" in f else 1)


def forge_path(fg):
    if os.path.exists(os.path.join(GAME, fg)):
        return os.path.join(GAME, fg)
    for d in os.listdir(GAME):
        p = os.path.join(GAME, d, fg)
        if d.startswith("dlc_") and os.path.exists(p):
            return p
    raise FileNotFoundError(fg)


def resolve(key):
    if key.startswith("/") and key.endswith("/"):
        rx = re.compile(key[1:-1], re.I)
        hits = [r for r in rows() if rx.search(r[5])]
    else:
        try:
            oid = int(key, 16) if re.fullmatch(r"[0-9A-Fa-f]{16}", key) else None
        except ValueError:
            oid = None
        hits = [r for r in rows() if (r[2] == oid if oid is not None else r[5] == key)]
    by_id = {}
    for r in sorted(hits, key=lambda r: rank(r[0])):
        by_id.setdefault(r[2], []).append(r)
    return by_id


def main():
    global CACHE, GAME
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", default=CACHE, help="folder with main_index.tsv / dlc_index.tsv (default: ACO_CACHE)")
    ap.add_argument("--game", default=GAME, help="game folder, used by extract (default: ACO_GAME_DIR)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("find", help="every forge holding it (winner first)")
    p.add_argument("keys", nargs="*", help="data file name, 16-digit hex ID or /regex/")
    p = sub.add_parser("extract", help="winner -> <out_dir>/<forge stem>/<index>_-_<name>.data")
    p.add_argument("out_dir")
    p.add_argument("keys", nargs="*", help="data file name or 16-digit hex ID")
    a = ap.parse_args()
    CACHE, GAME = a.cache, a.game
    if not CACHE:
        raise SystemExit("set ACO_CACHE (folder with main_index.tsv / dlc_index.tsv) or pass --cache")
    if a.cmd == "extract" and not GAME:
        raise SystemExit("set ACO_GAME_DIR (the game folder) or pass --game")
    cmd = a.cmd
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if cmd == "find":
        for k in a.keys:
            for oid, rs in resolve(k).items():
                for j, r in enumerate(rs):
                    print(("*" if j == 0 else " ") + f"\t{r[2]:016X}\t{r[0]}\t{r[1]}\t{r[4]}\t{r[5]}")
    elif cmd == "extract":
        out = a.out_dir
        for k in a.keys:
            res = resolve(k)
            if not res:
                print("NOT FOUND", k)
            for oid, rs in res.items():
                fg, i, oid, off, size, name = rs[0]
                d = os.path.join(out, os.path.splitext(fg)[0])
                os.makedirs(d, exist_ok=True)
                safe = "".join(c if c not in '<>:"/\\|?*' else "_" for c in name) or f"{oid:016X}"
                p = os.path.join(d, f"{i}_-_{safe}.data")
                with open(forge_path(fg), "rb") as f:
                    f.seek(off)
                    data = f.read(size)
                with open(p, "wb") as o:
                    o.write(data)
                print(f"{oid:016X}\t{fg}\t{p}")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
