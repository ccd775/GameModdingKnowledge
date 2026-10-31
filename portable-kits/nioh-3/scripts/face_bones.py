"""Per-bone skin weight mass and weighted centroid of a G1M (visible submeshes), with the joint position and parent.
usage: face_bones.py <file.g1m> [min bone id]      -> one line per bone id that carries weight"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import g1m_tool as gt  # noqa: E402


def vertex_weights(d, m, s):
    a = m.attributes[s['vertex_buffer']]
    pos, W, I = None, [], []
    for x in a['attrs']:
        vb = m.vertex_buffers[a['buffers'][x['buffer']]]
        raw = np.frombuffer(d, np.uint8, vb['count'] * vb['stride'], vb['offset']).reshape(vb['count'], vb['stride'])
        if x['semantic'] == 'POSITION' and x['layer'] == 0:
            pos = raw[:, x['offset']:x['offset'] + 12].copy().view('<f4').reshape(-1, 3)
        elif x['semantic'] == 'BLENDWEIGHT':
            if x['type'] == 0x03:
                W.append(raw[:, x['offset']:x['offset'] + 16].copy().view('<f4').reshape(-1, 4))
            else:
                n = {0x0B: 4, 0x0A: 2}[x['type']]
                W.append(raw[:, x['offset']:x['offset'] + 2 * n].copy().view('<f2').astype(float).reshape(-1, n))
        elif x['semantic'] == 'BLENDINDICES':
            if x['type'] == 0x07:     # u16 x 4 (palettes over 85 joints)
                I.append(raw[:, x['offset']:x['offset'] + 8].copy().view('<u2').astype(int))
            else:
                I.append(raw[:, x['offset']:x['offset'] + 4].astype(int))
    if pos is None or not W:
        return None
    W = np.concatenate(W, 1); I = np.concatenate(I, 1)
    k = min(W.shape[1], I.shape[1])
    return pos, W[:, :k], I[:, :k]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('file', help='.g1m'); ap.add_argument('min_bone', nargs='?', type=int, default=0, help='lowest bone id listed')
    args = ap.parse_args()
    f = args.file; lo = args.min_bone
    d = Path(f).read_bytes(); m = gt.embedded_models(d)[-1]
    joints, by_id = gt.skeleton(m); st2id = {s: b for b, s in by_id.items()}
    mass, cen = {}, {}
    for s in m.submeshes:
        if gt.is_hidden(m, s):
            continue
        r = vertex_weights(d, m, s)
        if r is None:
            continue
        pos, W, I = r
        pal = m.palettes[s['palette']]
        sl = slice(s['vertex_offset'], s['vertex_offset'] + s['vertex_count'])
        for P, w, i in zip(pos[sl], W[sl], I[sl]):
            for wk, ik in zip(w, i):
                if not wk > 0 or ik // 3 >= len(pal):
                    continue
                b = st2id.get(pal[ik // 3]['joint'], -1)
                mass[b] = mass.get(b, 0) + wk; cen[b] = cen.get(b, 0) + wk * P
    for b in sorted(mass):
        if b < lo:
            continue
        st = by_id.get(b)
        jp = np.round(joints[st]['world_p'], 2).tolist() if st is not None else None
        par = st2id.get(joints[st]['parent']) if st is not None else None
        print(b, 'parent', par, 'joint', jp, 'mass', round(float(mass[b]), 1), 'centroid', np.round(cen[b] / mass[b], 2).tolist())


if __name__ == '__main__':
    main()
