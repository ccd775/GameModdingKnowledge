"""Decode KTID tables whose objects live in the TextureAlias kidsobjdb, and list alias objects for given textures.
usage: alias_ktid.py <package> <alias db hash> --ktid <hash> [...] --tex <hash> [...]"""
import argparse, struct, sys
from pathlib import Path
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('package', help='package dir with root.rdb.original / root.rdx.original')
ap.add_argument('db', help='TextureAlias kidsobjdb hash')
ap.add_argument('--ktid', nargs='*', required=True, default=[], metavar='hash')
ap.add_argument('--tex', nargs='*', required=True, default=[], metavar='hash')
args = ap.parse_args()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ktdata
pk = Path(args.package)
kt = [int(x, 16) for x in args.ktid]; tex = {int(x, 16) for x in args.tex}
recs = ktdata.parse_rdb(pk / 'root.rdb.original', pk / 'root.rdx.original')
db = ktdata.parse_kidsobjdb(ktdata.read_entry(recs[int(args.db, 16)], pk))
for h in kt:
    d = ktdata.read_entry(recs[h], pk)
    pairs = [struct.unpack_from('<2I', d, p) for p in range(0, len(d), 8)]
    print(f'KTID 0x{h:08X}', [(i, f'0x{r:08X}', f'0x{db[r].first_value:08X}' if r in db and db[r].first_value is not None else None) for i, r in pairs])
for name, e in sorted(db.items()):
    if e.first_value in tex:
        print(f'alias object 0x{name:08X} -> 0x{e.first_value:08X}')
