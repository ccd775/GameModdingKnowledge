"""Find every KTID texture table that references given G1T hashes (through CharacterEditor kidsobjdb objects).
usage: ktid_find.py <package> <g1t hash> [...]   -> prints each matching KTID with its full slot -> G1T table"""
import argparse, struct, sys
from pathlib import Path
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('package'); ap.add_argument('hashes', nargs='+', metavar='g1t_hash')
args = ap.parse_args()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ktdata
g = ktdata.GameData(args.package) if not (Path(args.package) / 'root.rdb.original').exists() else None
if g is None:   # read through the vanilla table
    class G(ktdata.GameData):
        def __init__(self, d):
            self.dir = Path(d); self.records = ktdata.parse_rdb(self.dir / 'root.rdb.original', self.dir / 'root.rdx.original'); self._kids = None
    g = G(args.package)
targets = {int(a, 16) for a in args.hashes}
kids = g.kids
objs = {name: e.first_value for name, e in kids.items() if e.first_value in targets}
print('objects pointing at targets:', {f'0x{k:08X}': f'0x{v:08X}' for k, v in objs.items()})
n = 0
for h, r in g.records.items():
    if r.type_hash not in ktdata.KTID_TYPES or not r.internal:
        continue
    try:
        d = g.read(h)
    except Exception:
        continue
    pairs = [struct.unpack_from('<2I', d, p) for p in range(0, len(d) - len(d) % 8, 8)]
    if any(ref in objs for _, ref in pairs):
        n += 1
        table = {i: (f'0x{kids[ref].first_value:08X}' if ref in kids and kids[ref].first_value is not None else f'?0x{ref:08X}') for i, ref in pairs}
        print(f'KTID 0x{h:08X}', table)
print('matches', n)
