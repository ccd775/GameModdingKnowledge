"""Most common tiny (default) textures per material slot type across CharacterEditor models, with the kidsobjdb
object that points at each (what a KTID payload stores). usage: slot_defaults.py <package> [type ...]"""
import argparse, struct, sys
from collections import Counter, defaultdict
from pathlib import Path
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('package', help='package dir with root.rdb.original / root.rdx.original')
ap.add_argument('types', nargs='*', type=int, metavar='type', help='material slot types (default 5 47 49 24)')
args = ap.parse_args()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ktdata, g1m_tool
pk = Path(args.package); want = set(args.types) or {5, 47, 49, 24}
class G(ktdata.GameData):
    def __init__(self, d):
        self.dir = Path(d); self.records = ktdata.parse_rdb(self.dir / 'root.rdb.original', self.dir / 'root.rdx.original'); self._kids = None
g = G(pk); kids = g.kids
obj_of = defaultdict(set)
for name, e in kids.items():
    if e.first_value is not None:
        obj_of[e.first_value].add(name)
count, refs = Counter(), defaultdict(Counter)
models = sorted({e.first_value for e in kids.values() if e.first_value in g.records and g.records[e.first_value].type_hash == ktdata.G1M_TYPE})
for mh in models[:400]:
    try:
        m = g1m_tool.embedded_models(g.read(mh))[-1]
        kt = ktdata.ktid_candidates(mh, kids, g.records)
        if not kt: continue
        d = g.read(kt[0]); pairs = [struct.unpack_from('<2I', d, p) for p in range(0, len(d) - len(d) % 8, 8)]
    except Exception:
        continue
    table = dict(pairs)
    for mat in m.materials:
        for s in mat:
            if s['type'] in want and s['index'] in table:
                ref = table[s['index']]; tex = kids[ref].first_value if ref in kids else None
                r = g.records.get(tex)
                if r and r.file_size < 2048:
                    count[(s['type'], tex)] += 1; refs[(s['type'], tex)][ref] += 1
for (t, tex), n in count.most_common(12):
    print(f'type {t} tex 0x{tex:08X} size {g.records[tex].file_size} used {n} objects', {f"0x{k:08X}": v for k, v in refs[(t, tex)].most_common(3)})
