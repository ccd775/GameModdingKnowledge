"""Rewrite slots of a KTID texture table to point at other CharacterEditor objects (resolved by their texture hash).
usage: ktid_repoint.py <package> <ktid hash> <out file> <slot>=<g1t hash> [...]
Each target texture must already be the first value of some CharacterEditor kidsobjdb object (a default texture)."""
import argparse, struct, sys
from pathlib import Path
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('package', help='package dir with root.rdb.original / root.rdx.original')
ap.add_argument('ktid', help='KTID hash'); ap.add_argument('out', help='output file (never overwritten)')
ap.add_argument('pairs', nargs='+', metavar='slot=g1t')
args = ap.parse_args()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ktdata
pk = Path(args.package); kh = int(args.ktid, 16); out = Path(args.out)
class G(ktdata.GameData):
    def __init__(self, d):
        self.dir = Path(d); self.records = ktdata.parse_rdb(self.dir / 'root.rdb.original', self.dir / 'root.rdx.original'); self._kids = None
g = G(pk); kids = g.kids
data = bytearray(g.read(kh)); before = ktdata.parse_ktid(bytes(data), kids)
objs = {}
for name in sorted(kids):
    e = kids[name]
    if e.first_value is not None:
        objs.setdefault(e.first_value, name)
for arg in args.pairs:
    slot, tex = arg.split('='); slot = int(slot); tex = int(tex, 16)
    ref = objs[tex]
    for p in range(0, len(data), 8):
        i, r = struct.unpack_from('<2I', data, p)
        if i == slot:
            struct.pack_into('<2I', data, p, i, ref)
            break
    else:
        raise SystemExit(f'slot {slot} not in the table')
after = ktdata.parse_ktid(bytes(data), kids)
for k in sorted(before):
    print(k, f'0x{before[k]:08X}', '->' if before[k] != after[k] else '  ', f'0x{after[k]:08X}')
if out.exists():
    raise SystemExit(f'{out} exists')
out.write_bytes(bytes(data))
