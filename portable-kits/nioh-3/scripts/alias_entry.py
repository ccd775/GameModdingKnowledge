"""Print the kidsobjdb entries (and their referencing entries) that hold given values. usage: alias_entry.py <package> <db hash> <value hex> [...]"""
import argparse, sys
from pathlib import Path
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('package', help='package dir with root.rdb.original / root.rdx.original')
ap.add_argument('db', help='kidsobjdb hash'); ap.add_argument('values', nargs='+', metavar='value_hex')
args = ap.parse_args()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ktdata
pk = Path(args.package)
recs = ktdata.parse_rdb(pk / 'root.rdb.original', pk / 'root.rdx.original')
db = ktdata.parse_kidsobjdb(ktdata.read_entry(recs[int(args.db, 16)], pk))
vals = {int(a, 16) for a in args.values}
def flat(props):
    for pname, vt, vs in props:
        for v in vs:
            yield pname, vt, v
hit = [e for e in db.values() if any(isinstance(v, int) and (v & 0xFFFFFFFF) in vals for _, _, v in flat(e.props))]
for e in hit:
    print(f'entry 0x{e.name_hash:08X} type 0x{e.type_hash:08X}')
    for pname, vt, vs in e.props:
        print(f'   prop 0x{pname:08X} vt{vt} ' + ' '.join(f'0x{v & 0xFFFFFFFF:08X}' if isinstance(v, int) else str(v) for v in vs[:24]))
    refs = [r for r in db.values() if any(isinstance(v, int) and (v & 0xFFFFFFFF) == e.name_hash for _, _, v in flat(r.props))]
    for r in refs[:5]:
        print(f'   referenced by 0x{r.name_hash:08X} type 0x{r.type_hash:08X}: ' + '; '.join(f'0x{p:08X}=' + ','.join(f'0x{v & 0xFFFFFFFF:08X}' if isinstance(v, int) else str(v) for v in vs[:8]) for p, _, vs in r.props))
