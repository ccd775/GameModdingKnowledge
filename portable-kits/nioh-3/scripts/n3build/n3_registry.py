"""Register a built chest's type-4 entries in its physics registry (resource type 0xB340861A, linked from the model's
CharacterEditor entry, prop 0x7F0DE9A3; each chest's registry is used by that chest alone).
usage: n3_registry.py [ninja|samurai] [--g1m <built model>] [--no-counts]
  reads BUILD/orig/<registry>.bin and the built model (default BUILD/g1m/<model>.g1m); a model without MESH_LOD
  type-2 groups (build11 layout) registers its entries with x = entry index (all on material 0)

Registry layout (v2.0.0.2, 2101 vanilla samples): u32 sets, materials, type-5 count, type-4 count; sets x (hash, n,
n material indices); type-5 entries x (x, id); type-4 entries x (x, id) in ONUN order, x = index of the entry among
the type-4 entries whose mesh uses the same material (vanilla up to 60 entries, x up to 59, ids up to 200).
Registering alone draws nothing more (build15); registered entries without type-2 groups do not simulate (build19).
Also the model's per-material count resource (type 0x56EFE45C, prop 0x3BBFD9A5): one 32-byte record per material
(hash, 0, submeshes, 0, 0, vertex buffers, 0, 0 for chests; other models also fill +12 / +24: 13259 vanilla
resources, none with an all-zero record), matching vanilla chests / waist / hakama exactly. Type-2 meshes beyond a
material's count are not drawn (build12-15); counts above what a material has crashed the game (build16-18, RVA
0x195297 of Nioh3.exe 2.0.0.2, a null per-slot pointer). Each count is therefore the built model's exact number, and a
material without submeshes is an error (n3_build_g1m.py keeps every vanilla submesh). The ninja chest's count
resource is shared with 0x1af713a6 (same submesh layout, own registry 0x1b322be4): it then over-counts material 0.
Output: BUILD/g1m/<registry>.bin, BUILD/g1m/<counts>.bin.
"""
import argparse
import struct
from pathlib import Path

from n3_common import BUILD, ORIG, gt
import nuno4  # noqa: E402  (tools/ is on sys.path via n3_common)

REGISTRY = {'ninja': ('0x5548953f', '0x5583ad7d', '0x5c3826bd'), 'samurai': ('0xed9b4309', '0xedd65b47', '0xf48ad487')}
CHAIN_NUN = 0x2710


def parse(b):
    w = list(struct.unpack_from(f'<{len(b) // 4}I', b))
    ns, nm, n5, n4 = w[:4]
    p = 4
    for _ in range(ns):
        p += 2 + w[p + 1]
    assert p + 2 * (n5 + n4) == len(w), 'registry layout'
    return w, p + 2 * n5, n4


def chain_materials(d, m):
    """type-4 entry index -> material of the submeshes its MESH_LOD type-2 group names"""
    sec = m.section('MESH_LOD'); body = d[sec['offset'] + 12:sec['offset'] + sec['size']]
    out, q = {}, 0
    for _ in range(sec['count']):
        c1, c2 = struct.unpack_from('<2I', body, q + 12); q += 36
        for _ in range(c1 + c2):
            typ, _unk, nun, ic = struct.unpack_from('<HHII', body, q + 16)
            idx = struct.unpack_from(f'<{ic}I', body, q + 28)
            if typ == 2:
                mats = {m.submeshes[i]['material'] for i in idx}
                assert len(mats) == 1 and nun - CHAIN_NUN not in out, f'group {nun:#x}'
                out[nun - CHAIN_NUN] = mats.pop()
            q += 28 + 4 * max(ic, 1)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('target', nargs='?', default='ninja', choices=sorted(REGISTRY))
    ap.add_argument('--g1m', help='built model (default BUILD/g1m/<model>.g1m)')
    ap.add_argument('--no-counts', action='store_true', help='only the physics registry, not the material counts')
    args = ap.parse_args()
    tname = args.target
    model, reg, counts = REGISTRY[tname]
    src = Path(args.g1m) if args.g1m else BUILD / 'g1m' / f'{model}.g1m'
    w, end5, n4 = parse((ORIG / f'{reg}.bin').read_bytes())
    assert n4 == 0, 'vanilla registry already lists type-4 entries'
    d = src.read_bytes(); m = gt.embedded_models(d)[-1]
    ids = [e['id'] for s in nuno4.parse_onun(d, m)['subs'] if s['type'] == 0x30004 for e in s['entries']]
    mats = chain_materials(d, m) or {k: 0 for k in range(len(ids))}
    assert sorted(mats) == list(range(len(ids))), 'every type-4 entry needs exactly one type-2 group'
    pairs, seen = [], {}
    for k, i in enumerate(ids):
        x = seen.get(mats[k], 0); seen[mats[k]] = x + 1
        pairs += [x, i]
    w[3] = len(ids)
    out = struct.pack(f'<{len(w) + len(pairs)}I', *w[:end5], *pairs)
    (BUILD / 'g1m' / f'{reg}.bin').write_bytes(out)
    print(tname, reg, 'type-4 entries', len(ids), 'pairs', list(zip(pairs[::2], pairs[1::2])), 'bytes', len(out))
    if args.no_counts:
        return
    c = list(struct.unpack_from(f'<{len((ORIG / f"{counts}.bin").read_bytes()) // 4}I', (ORIG / f'{counts}.bin').read_bytes()))
    assert len(c) % 8 == 0 and all(c[r + 2] > 0 and not any(c[r + i] for i in (1, 3, 4, 6, 7))
                                   for r in range(0, len(c), 8)), 'count layout'
    assert {s['material'] for s in m.submeshes} <= set(range(len(c) // 8)), 'a submesh material without a count record'
    vanilla = [(c[r + 2], c[r + 5]) for r in range(0, len(c), 8)]
    for r in range(len(c) // 8):
        subs = [s for s in m.submeshes if s['material'] == r]
        assert subs, f'material {r} has no submeshes (no vanilla count record is empty)'
        c[8 * r + 2] = len(subs); c[8 * r + 5] = len({m.attributes[s['vertex_buffer']]['buffers'][0] for s in subs})
    (BUILD / 'g1m' / f'{counts}.bin').write_bytes(struct.pack(f'<{len(c)}I', *c))
    print(tname, counts, 'per material (submeshes, vertex buffers)', [(c[r + 2], c[r + 5]) for r in range(0, len(c), 8)],
          'vanilla', vanilla)


if __name__ == '__main__':
    main()
