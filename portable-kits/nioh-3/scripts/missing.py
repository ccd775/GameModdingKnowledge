"""Which rdx containers are absent from the package dir, and which resource types live in them."""
import argparse, sys, collections
from pathlib import Path
ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('package', help='package dir (root.rdb / root.rdx)')
args = ap.parse_args()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ktdata
g = Path(args.package)
recs = ktdata.parse_rdb(g / 'root.rdb', g / 'root.rdx')
rdx = ktdata.parse_rdx(g / 'root.rdx')
missing = {h for h in rdx.values() if not (g / f'0x{h:08x}.fdata').exists()}
print('rdx', len(rdx), 'missing', len(missing))
by = collections.Counter(); tot = collections.Counter()
for r in recs.values():
    if r.internal:
        tot[r.type_hash] += 1
        if r.fdata_hash in missing:
            by[r.type_hash] += 1
for t, n in tot.most_common(25):
    print(f'{t:08X} total={n} missing={by[t]}')
