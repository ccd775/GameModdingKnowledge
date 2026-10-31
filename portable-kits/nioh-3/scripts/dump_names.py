"""Extract every NameDatabaseFile (.name, type 0xBF6B52C7) and write all printable strings found per file.
usage: dump_names.py <package dir> <out txt> [type hex]"""
import argparse, sys, re
from pathlib import Path
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('package', help='package dir (root.rdb / root.rdx)'); ap.add_argument('out', help='output text file')
ap.add_argument('type', nargs='?', default='BF6B52C7', help='resource type hash (default BF6B52C7, NameDatabaseFile)')
args = ap.parse_args()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ktdata

g, out = Path(args.package), Path(args.out)
t = int(args.type, 16)
recs = ktdata.parse_rdb(g / 'root.rdb', g / 'root.rdx')
sel = [r for r in recs.values() if r.type_hash == t and r.internal]
print('selected', len(sel), 'bytes', sum(r.file_size for r in sel))
with out.open('w', encoding='utf-8') as f:
    for i, r in enumerate(sorted(sel, key=lambda r: (r.fdata_hash, r.fdata_offset))):
        try:
            d = ktdata.read_entry(r, g)
        except Exception as e:
            f.write(f'## {r.file_hash:08X} ERROR {e}\n'); continue
        strs = [m.group().decode('utf-8', 'replace') for m in re.finditer(rb'[\x20-\x7e]{4,}', d)]
        f.write(f'## {r.file_hash:08X} size={len(d)} ' + ' | '.join(strs[:400]) + '\n')
