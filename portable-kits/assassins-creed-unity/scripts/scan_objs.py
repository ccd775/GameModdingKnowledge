"""Find every data file that embeds objects with given IDs (AcuHarness scan-objs over cache/index.tsv).

  python scan_objs.py <out.log> <IDHEX,IDHEX,...> <forge|substring> [...] [--game <game dir>]

Forge arguments select index rows whose forge column equals or contains them (e.g. "dlc_11\\", "Paris.forge").
The log format is the one objs_to_tsv.py reads ("== forge" headers, OBJ / ERR / DONE lines).
Machine paths (portable kit): ACU_DOTNET, ACU_HARNESS and ACU_CACHE (folder with index.tsv) are checked first; game
folder --game, ACU_GAME_DIR or the Steam libraries.
"""
import argparse
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
# machine paths (portable kit): environment variables, checked in main() before anything is written
ENV = ("ACU_DOTNET", "ACU_HARNESS", "ACU_CACHE")
DOTNET = os.environ.get("ACU_DOTNET", "")    # dotnet.exe of the .NET 9 runtime
HARNESS = os.environ.get("ACU_HARNESS", "")  # AcuHarness.dll
CACHE = os.environ.get("ACU_CACHE", "")      # folder with index.tsv (acu_forge.py index)
sys.path.insert(0, HERE)
import acu_install  # noqa: E402  (find_game)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out_log")
    ap.add_argument("ids", help="object IDs (hex, comma-separated)")
    ap.add_argument("forges", nargs="+", help="forge names or substrings of the index's forge column")
    ap.add_argument("--game", help="game folder with ACU.exe (default: ACU_GAME_DIR, else the Steam libraries)")
    a = ap.parse_args()
    missing = [n for n in ENV if not os.environ.get(n)]
    if missing:
        raise SystemExit("set " + ", ".join(missing) + " (see the kit README)")
    game = acu_install.find_game(["--game", a.game] if a.game else [])
    out, ids, sel = a.out_log, a.ids, a.forges
    rows = {}
    for line in open(os.path.join(CACHE, "index.tsv"), encoding="utf-8", errors="replace"):
        fg, _, oid, off, size, name = line.rstrip("\n").split("\t", 5)
        if any(s == fg or s in fg for s in sel):
            rows.setdefault(fg, []).append(f"{off}\t{size}\t{oid}_{name}\n")
    with open(out, "w", encoding="utf-8") as log:
        for fg, lst in rows.items():
            with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False, encoding="utf-8") as t:
                t.writelines(lst)
            r = subprocess.run([DOTNET, HARNESS, "scan-objs", os.path.join(game, fg), t.name, ids],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            os.remove(t.name)
            keep = [l for l in r.stdout.splitlines() if l.startswith(("OBJ", "ERR", "DONE"))]
            log.write(f"== {fg}\n" + "".join(l + "\n" for l in keep))
            log.flush()
            print(fg, keep[-1] if keep else r.stderr[-300:])


if __name__ == "__main__":
    main()
