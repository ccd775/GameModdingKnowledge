"""Raw search: which resources (of the given types) contain the 4-byte little-endian value of each hash.
usage: raw_ref.py <package> <type hex,type hex|all> <hash> [...]"""
import argparse, struct, sys
from pathlib import Path
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('package', help='package dir with root.rdb.original / root.rdx.original')
ap.add_argument('types', help="comma-separated type hashes, or 'all'"); ap.add_argument('hashes', nargs='+', metavar='hash')
args = ap.parse_args()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ktdata
pk = Path(args.package)
recs = ktdata.parse_rdb(pk / 'root.rdb.original', pk / 'root.rdx.original')
types = None if args.types == 'all' else {int(t, 16) for t in args.types.split(',')}
needles = {struct.pack('<I', int(a, 16)): a for a in args.hashes}
hits = 0
for h, r in recs.items():
    if not r.internal or (types and r.type_hash not in types) or r.file_size > 50_000_000:
        continue
    try:
        d = ktdata.read_entry(r, pk)
    except Exception:
        continue
    for n, a in needles.items():
        i = d.find(n)
        if i >= 0:
            hits += 1
            print(f'{a} in 0x{h:08X} type 0x{r.type_hash:08X} size {r.file_size} at {i:#x} (count {d.count(n)})')
print('hits', hits)
