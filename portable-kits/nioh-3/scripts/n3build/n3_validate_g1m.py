"""Read back a built G1M with g1m_tool (independent of the writer) and check the contract.
usage: n3_validate_g1m.py <built.g1m> <template.g1m> [--layout-changed] [--physics]
Checks: chunk/section parse, per-submesh index range, palette size <= 85 (<= 128 with u16 blend indices) and entries
native-bound, weight sums == 1,
blend indices multiple of 3 and inside the palette (visible submeshes), unchanged sections/chunks other than the
expected ones (VERTEX_ATTRIBUTES too with --layout-changed, SM1G / ONUN with --physics)."""
import argparse
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import g1m_tool as gt  # noqa: E402

EXPECT_CHANGED = {'VERTEX_BUFFERS', 'INDEX_BUFFER', 'JOINT_PALETTES', 'SUBMESH', 'MESH_LOD'}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('built'); ap.add_argument('template')
    ap.add_argument('--layout-changed', action='store_true', help='VERTEX_ATTRIBUTES may change')
    ap.add_argument('--physics', action='store_true', help='SM1G / ONUN / LLOC may change')
    args = ap.parse_args()
    new_d = Path(args.built).read_bytes(); old_d = Path(args.template).read_bytes()
    expect = EXPECT_CHANGED | ({'VERTEX_ATTRIBUTES'} if args.layout_changed else set())
    m, o = gt.embedded_models(new_d)[-1], gt.embedded_models(old_d)[-1]
    bad = []
    assert struct.unpack_from('<I', new_d, 8)[0] == len(new_d), 'file size field'
    for so, sn in zip(o.sections, m.sections):
        same = old_d[so['offset'] + 12:so['offset'] + so['size']] == new_d[sn['offset'] + 12:sn['offset'] + sn['size']]
        if not same and sn['name'] not in expect:
            bad.append(f"section {sn['name']} changed unexpectedly")
    may_change = ('GM1G', 'MM1G', 'FM1G') + (('SM1G', 'ONUN', 'LLOC') if args.physics else ())
    for k in o.chunks:
        if k not in may_change and old_d[o.chunks[k].offset:o.chunks[k].end] != new_d[m.chunks[k].offset:m.chunks[k].end]:
            bad.append(f'chunk {k} changed')
    joints, _ = gt.skeleton(m)
    mats = gt.binds(m)
    for s in m.submeshes:
        a = m.attributes[s['vertex_buffer']]; vb = m.vertex_buffers[a['buffers'][0]]
        ib = m.index_buffers[s['index_buffer']]
        idx = np.frombuffer(new_d, '<u2' if ib['stride'] == 2 else '<u4', s['index_count'], ib['offset'] + ib['stride'] * s['index_offset'])
        hidden = gt.is_hidden(m, s)
        line = f"sub{s['id']} v={s['vertex_count']} i={s['index_count']} hidden={hidden}"
        if idx.max() >= s['vertex_offset'] + s['vertex_count'] or idx.min() < s['vertex_offset']:
            bad.append(f"sub{s['id']} index out of range")
        pal = m.palettes[s['palette']]
        cap = 128 if any(x['semantic'] == 'BLENDINDICES' and x['type'] == 0x07 for x in a['attrs']) else 85
        if len(pal) > cap:
            bad.append(f"sub{s['id']} palette {len(pal)} > {cap}")
        nonnative = 0
        for k, e in enumerate(pal):
            want = np.array(gt.native_bind(joints[e['joint']]['world']))
            if np.abs(np.array(mats[e['g1mm']]) - want).max() > 1e-3:
                nonnative += 1
        raw = np.frombuffer(new_d, np.uint8, vb['count'] * vb['stride'], vb['offset']).reshape(vb['count'], vb['stride'])
        W, I = [np.zeros((vb['count'], 0))], [np.zeros((vb['count'], 0), int)]
        for x in (a['attrs'] if not hidden else []):
            if x['semantic'] == 'BLENDWEIGHT':
                n = {0x0B: 4, 0x0A: 2}[x['type']]
                W.append(raw[:, x['offset']:x['offset'] + 2 * n].copy().view('<f2').astype(float).reshape(-1, n))
            if x['semantic'] == 'BLENDINDICES':
                if x['type'] == 0x07:
                    I.append(raw[:, x['offset']:x['offset'] + 8].copy().view('<u2').astype(int))
                else:
                    I.append(raw[:, x['offset']:x['offset'] + 4].astype(int))
        W = np.concatenate(W, 1); I = np.concatenate(I, 1)
        if not hidden:
            ws = W.sum(1)
            line += f' wsum[{ws.min():.4f},{ws.max():.4f}] idx%3={bool((I % 3 == 0).all())} idx<3*pal={bool((I < 3 * len(pal)).all())} non-native binds={nonnative}'
            if abs(ws - 1).max() > 2e-3 or (I % 3).any() or (I >= 3 * len(pal)).any() or nonnative:
                bad.append(f"sub{s['id']} weights/indices/binds")
        print(line)
    fm = m.chunks['FM1G']
    print('FM1G mm count', gt.u32(new_d, fm.offset + 24), 'MM1G', gt.u32(new_d, m.chunks['MM1G'].offset + 12),
          'palette total', gt.u32(new_d, fm.offset + 68), sum(len(p) for p in m.palettes))
    if gt.u32(new_d, fm.offset + 24) != gt.u32(new_d, m.chunks['MM1G'].offset + 12) or gt.u32(new_d, fm.offset + 68) != sum(len(p) for p in m.palettes):
        bad.append('FM1G counts')
    print('FAIL' if bad else 'PASS', bad)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
