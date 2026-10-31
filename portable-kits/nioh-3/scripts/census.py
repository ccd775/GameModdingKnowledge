"""Census of Nioh 3 root.rdb: counts by type hash, internal/external, and a sample of records."""
import argparse, sys, collections, json
from pathlib import Path
ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('package', help='package dir (root.rdb / root.rdx)')
args = ap.parse_args()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ktdata

g = Path(args.package)
recs = ktdata.parse_rdb(g / 'root.rdb', g / 'root.rdx')
c = collections.Counter(r.type_hash for r in recs.values())
print('records', len(recs))
for t, n in c.most_common(40):
    print(f'{t:08X} {n}')
ext = [r for r in recs.values() if not r.internal]
print('external', len(ext), [hex(r.file_hash) for r in ext[:10]])
g1m = [r for r in recs.values() if r.type_hash == 0x563BDEF1]
print('g1m', len(g1m), 'total size', sum(r.file_size for r in g1m))
