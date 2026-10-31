"""Collapse (hide) every triangle of the listed models into an output dir, reading originals from search dirs.
usage: collapse_set.py <out dir> <hash> [<hash> ...] --from <dir> [<dir> ...]"""
import argparse, subprocess, sys
from pathlib import Path
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('out', help='output dir'); ap.add_argument('hashes', nargs='+', metavar='hash')
ap.add_argument('--from', dest='dirs', nargs='+', required=True, metavar='dir', help='dirs holding <hash>.g1m originals')
args = ap.parse_args()
out, hashes, dirs = Path(args.out), args.hashes, [Path(x) for x in args.dirs]
tool = Path(__file__).resolve().parent / 'g1m_tool.py'
for h in hashes:
    src = next((d / f'{h}.g1m' for d in dirs if (d / f'{h}.g1m').exists()), None)
    dst = out / f'{h}.g1m'
    if src is None:
        print(h, 'MISSING'); continue
    if dst.exists():
        dst.unlink()
    r = subprocess.run([sys.executable, '-B', str(tool), 'hide', str(src), '--all', '--output', str(dst)], capture_output=True, text=True)
    tail = r.stdout[r.stdout.find('"triangles_collapsed"'):][:60].replace('\n', ' ')
    print(h, 'ok' if r.returncode == 0 else 'FAIL ' + r.stderr[-300:], tail)
