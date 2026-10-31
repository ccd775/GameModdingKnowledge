"""CharacterEditor kidsobjdb entries whose first value is a model hash, their props, and the resources they link.
usage: model_refs.py <package> <model hash>"""
import argparse, sys
from pathlib import Path
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('package', help='package dir with root.rdb.original / root.rdx.original'); ap.add_argument('model', help='model hash')
args = ap.parse_args()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ktdata
pk = Path(args.package); h = int(args.model, 16)
recs = ktdata.parse_rdb(pk / 'root.rdb.original', pk / 'root.rdx.original')
kids = ktdata.parse_kidsobjdb(ktdata.read_entry(recs[ktdata.CHARACTER_EDITOR_DB], pk))
def show(e, depth=0):
    print('  ' * depth + f'entry 0x{e.name_hash:08X} type 0x{e.type_hash:08X}')
    for pname, vt, vs in e.props:
        txt = []
        for v in vs[:12]:
            if isinstance(v, int):
                v &= 0xFFFFFFFF
                r = recs.get(v)
                txt.append(f'0x{v:08X}' + (f'[res type {r.type_hash:08X}]' if r else ('[obj]' if v in kids else '')))
            else:
                txt.append(str(v))
        print('  ' * depth + f'   prop 0x{pname:08X} vt{vt}: ' + ' '.join(txt))
for e in kids.values():
    if e.first_value == h:
        show(e)
        for v in e.singleton_ints:
            if v in kids and v != e.name_hash:
                show(kids[v], 1)
