"""Set raw (slot -> object name) pairs of a KTID table. usage: ktid_setref.py <package> <ktid hash> <out file> <slot>=<object hash> [...]"""
import argparse, struct, sys
from pathlib import Path
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('package', help='package dir with root.rdb.original / root.rdx.original')
ap.add_argument('ktid', help='KTID hash'); ap.add_argument('out', help='output file (never overwritten)')
ap.add_argument('pairs', nargs='+', metavar='slot=object')
args = ap.parse_args()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ktdata
pk = Path(args.package); h = int(args.ktid, 16); out = Path(args.out)
recs = ktdata.parse_rdb(pk / 'root.rdb.original', pk / 'root.rdx.original')
d = bytearray(ktdata.read_entry(recs[h], pk))
want = {int(k): int(v, 16) for k, v in (a.split('=') for a in args.pairs)}
for p in range(0, len(d), 8):
    i, r = struct.unpack_from('<2I', d, p)
    if i in want:
        new = want.pop(i)
        struct.pack_into('<I', d, p + 4, new)
        print(f'slot {i}: 0x{r:08X} -> 0x{new:08X}')
if want:
    raise SystemExit(f'slots not found: {sorted(want)}')
if out.exists():
    raise SystemExit(f'{out} exists')
out.write_bytes(bytes(d))
