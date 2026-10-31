"""Karin_Original for Nioh 3 (v2.0.0.2): install / uninstall / verify.

usage: python karin_install.py install   "<Nioh 3 folder>"
       python karin_install.py uninstall "<Nioh 3 folder>"
       python karin_install.py verify    "<Nioh 3 folder>"

install: stages files/ (Karin's chest models, physics registries, material counts, textures, texture tables) plus
the vanilla models named in collapse.txt with every triangle collapsed, made from this game's own data (the package
carries no copies of them). Every vanilla resource the mod replaces must match vanilla.json (the v2.0.0.2 originals
it was built on) and every staged file package.json; then tools/n3inject.py rewrites package/root.rdb and root.rdx
(first-use backups root.rdb.original / root.rdx.original) and adds the container package/0x4b415249.fdata.
uninstall puts the backups back and deletes the container. The game must be closed. Python 3.8+, standard library.

The package data (files/, collapse.txt, vanilla.json, package.json; staging/ is made there) is read from --data,
default the folder of this script (the release layout). ktdata / n3inject / g1m_tool come from tools/ next to this
script when it exists (release), else from this script's folder (portable kit: scripts/).
"""
import argparse
import dataclasses
import hashlib
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE / 'tools' if (HERE / 'tools' / 'n3inject.py').is_file() else HERE
DATA = HERE                     # set from --data in main()
sys.path.insert(0, str(TOOLS))
import ktdata  # noqa: E402
import n3inject  # noqa: E402


def sha(b):
    return hashlib.sha256(b).hexdigest()


def game_running():
    out = subprocess.run(['tasklist', '/fi', 'imagename eq Nioh3.exe', '/fo', 'csv', '/nh'],
                         capture_output=True, text=True).stdout
    return 'nioh3.exe' in out.lower()


def package_dir(game):
    pkg = Path(game) / 'package'
    if not (pkg / 'root.rdb').exists():
        raise SystemExit(f'{pkg} has no root.rdb: pass the Nioh 3 folder (the one holding Nioh3.exe)')
    if game_running():
        raise SystemExit('Nioh 3 is running: close the game first')
    return pkg


def reader(pkg, original=True):
    """hash -> decoded resource, from the vanilla backups (original) or the live root.rdb."""
    if original:
        rdb, rdx = n3inject.originals(pkg)       # first use creates them; refreshed if the game replaced root.rdb
    else:
        rdb, rdx = pkg / 'root.rdb', pkg / 'root.rdx'
    recs = ktdata.parse_rdb(rdb, rdx)

    def read(h):
        r = recs[h]
        try:
            return ktdata.read_entry(r, pkg)
        except ValueError:
            # models (type 0x563BDEF1) store the packed size in root.rdb: take the fdata entry header's size
            with (pkg / f'0x{r.fdata_hash:08x}.fdata').open('rb') as f:
                f.seek(r.fdata_offset)
                size = struct.unpack_from('<3Q', f.read(48), 8)[2]
            return ktdata.read_entry(dataclasses.replace(r, file_size=size), pkg)
    return read


def collapse_list():
    return (DATA / 'collapse.txt').read_text().split()


def stage(pkg, staging):
    read = reader(pkg)
    vanilla = json.loads((DATA / 'vanilla.json').read_text())
    bad = [h for h, want in vanilla.items() if sha(read(int(h, 16))) != want]
    if bad:
        raise SystemExit(f'{len(bad)} vanilla resources differ from Nioh 3 v2.0.0.2 ({", ".join(bad[:5])}...): '
                         'this package does not fit this game version')
    shutil.rmtree(staging, ignore_errors=True)
    (staging / 'vanilla').mkdir(parents=True)
    for p in (DATA / 'files').iterdir():
        shutil.copy2(p, staging / p.name)
    tool = TOOLS / 'g1m_tool.py'
    for h in collapse_list():
        src = staging / 'vanilla' / f'{h}.g1m'
        src.write_bytes(read(int(h, 16)))
        r = subprocess.run([sys.executable, '-B', str(tool), 'hide', str(src), '--all', '--output',
                            str(staging / f'{h}.g1m')], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f'collapsing {h} failed: {r.stderr[-500:]}')
    shutil.rmtree(staging / 'vanilla')
    want = json.loads((DATA / 'package.json').read_text())
    got = {p.stem: sha(p.read_bytes()) for p in staging.iterdir()}
    wrong = sorted(h for h in want if got.get(h) != want[h]) + sorted(set(got) - set(want))
    if wrong:
        raise SystemExit(f'staged files do not match package.json: {wrong}')
    print(f'staged {len(got)} overrides ({len(collapse_list())} collapsed from this game\'s files)')


def cmd_install(game):
    pkg = package_dir(game)
    staging = DATA / 'staging'
    stage(pkg, staging)
    try:
        rc = n3inject.main(['install', str(pkg), str(staging)])
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    print('install', 'OK' if rc == 0 else 'FAILED (run uninstall to restore the backups)')
    return rc


def cmd_uninstall(game):
    return n3inject.main(['restore', str(package_dir(game))])


def cmd_verify(game):
    pkg = package_dir(game)
    want = json.loads((DATA / 'package.json').read_text())
    read = reader(pkg, original=False)
    bad = [h for h, w in want.items() if sha(read(int(h, 16))) != w]
    print(f'{len(want) - len(bad)} of {len(want)} overrides in place' + (f', different: {bad}' if bad else ''))
    return 1 if bad else 0


def cmd_manifest(game, ref_dir):
    """(packaging) vanilla.json from this game's backups, package.json from a reference build dir."""
    pkg = package_dir(game)
    files = {p.stem: p for p in Path(ref_dir).iterdir() if p.stem.startswith('0x')}
    read = reader(pkg)
    (DATA / 'vanilla.json').write_text(json.dumps({h: sha(read(int(h, 16))) for h in sorted(files)}, indent=1))
    (DATA / 'package.json').write_text(json.dumps({h: sha(p.read_bytes()) for h, p in sorted(files.items())}, indent=1))
    print('manifests for', len(files), 'resources')
    return 0


def main(argv):
    global DATA
    cmds = {'install': cmd_install, 'uninstall': cmd_uninstall, 'verify': cmd_verify, '_manifest': cmd_manifest}
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--data', default=str(HERE),
                        help='package data folder: files/, collapse.txt, vanilla.json, package.json (default: %(default)s)')
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True, metavar='{install,uninstall,verify}')
    for name in ('install', 'uninstall', 'verify'):
        sub.add_parser(name, parents=[common]).add_argument('game', help='Nioh 3 folder (the one holding Nioh3.exe)')
    p = sub.add_parser('_manifest', parents=[common])    # packaging: vanilla.json / package.json from a reference build
    p.add_argument('game'); p.add_argument('ref_dir')
    a = ap.parse_args(argv)
    DATA = Path(a.data)
    return cmds[a.cmd](a.game, *([a.ref_dir] if a.cmd == '_manifest' else []))


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
