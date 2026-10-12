"""Send a Lua chunk to the in-game karin_dev console and print the result.

usage: python devcmd.py <file.lua | -e "lua code"> [--timeout 20] [--game-dir <Dragons Dogma 2 folder>]
  exit: 0 ok, 1 Lua error, 2 timeout, bad arguments or unreadable Lua file, 3 no usable game folder
  The game folder (the one with DD2.exe and reframework/) comes from --game-dir or the DD2_GAME_DIR environment
  variable; the console files are <game>/reframework/data/karin_dev/cmd.json and result.json.
"""
import argparse
import json
import os
import pathlib
import sys
import time


def data_dir(game_dir):
    """<game>/reframework/data/karin_dev, where karin_dev.lua polls cmd.json and writes result.json."""
    if not game_dir:
        print("devcmd: set --game-dir or DD2_GAME_DIR to the Dragon's Dogma 2 folder (the one with DD2.exe)", file=sys.stderr)
        raise SystemExit(3)
    game = pathlib.Path(game_dir)
    if not (game / "reframework").is_dir():
        print(f"devcmd: {game} has no reframework folder (install REFramework and karin_dev.lua first)", file=sys.stderr)
        raise SystemExit(3)
    return game / "reframework" / "data" / "karin_dev"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?")
    ap.add_argument("-e", dest="code")
    ap.add_argument("--timeout", type=float, default=20)
    ap.add_argument("--game-dir", default=os.environ.get("DD2_GAME_DIR"),
                    help="Dragon's Dogma 2 folder (default: the DD2_GAME_DIR environment variable)")
    a = ap.parse_args()
    if a.code is None and a.file is None:
        ap.error("give a Lua file or -e \"code\"")
    DATA = data_dir(a.game_dir)
    try:
        code = a.code if a.code is not None else pathlib.Path(a.file).read_text(encoding="utf-8")
    except OSError as e:
        ap.error(f"cannot read {a.file}: {e}")
    DATA.mkdir(parents=True, exist_ok=True)
    cid = f"{time.time():.6f}"
    tmp = DATA / "cmd.json.tmp"
    tmp.write_text(json.dumps({"id": cid, "lua": code}), encoding="utf-8")
    tmp.replace(DATA / "cmd.json")
    res = DATA / "result.json"
    end = time.time() + a.timeout
    while time.time() < end:
        try:
            r = json.loads(res.read_text(encoding="utf-8"))
            if str(r.get("id")) == cid:
                print(json.dumps(r, indent=1, ensure_ascii=False))
                return 0 if "error" not in r else 1
        except (OSError, ValueError):
            pass
        time.sleep(0.25)
    print("timeout waiting for result", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
