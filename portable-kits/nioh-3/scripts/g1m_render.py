"""Quick look at G1M models: front and side orthographic views, one colour per submesh, flat shaded.
usage: g1m_render.py <out.png> <file.g1m> [...]    (several models -> one row each)
Bind pose as stored (no skinning). Draws every visible submesh, so LODs overlap; this is for identification only.
"""
import argparse
import glob
import struct
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import g1m_tool as gt  # noqa: E402

MAX_TRIS = 60000


def submesh_tris(m, s):
    a = m.attributes[s['vertex_buffer']] if s['vertex_buffer'] < len(m.attributes) else None
    if a is None:
        return None
    pos = next((x for x in a['attrs'] if x['semantic'] == 'POSITION' and x['layer'] == 0), None)
    if pos is None or pos['type'] not in (0x02, 0x03):
        return None
    vb = m.vertex_buffers[a['buffers'][pos['buffer']]]
    raw = np.frombuffer(m.data, np.uint8, vb['count'] * vb['stride'], vb['offset']).reshape(vb['count'], vb['stride'])
    P = raw[:, pos['offset']:pos['offset'] + 12].copy().view('<f4').reshape(-1, 3)
    ib = m.index_buffers[s['index_buffer']]
    fmt = {1: '<u1', 2: '<u2', 4: '<u4'}[ib['stride']]
    idx = np.frombuffer(m.data, fmt, s['index_count'], ib['offset'] + s['index_offset'] * ib['stride']).astype(np.int64)
    if s['primitive'] != 3 or len(idx) < 3:
        return None
    T = idx[:len(idx) // 3 * 3].reshape(-1, 3)
    T = T[(T < len(P)).all(1)]
    return P[T]


def draw(ax, tris_list, axes):
    polys, depth, colors = [], [], []
    cmap = plt.get_cmap('tab20')
    light = np.array([0.3, 0.5, 0.8]); light /= np.linalg.norm(light)
    for k, tri in enumerate(tris_list):
        if tri is None or not len(tri):
            continue
        if len(tri) > MAX_TRIS:
            tri = tri[np.linspace(0, len(tri) - 1, MAX_TRIS).astype(int)]
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
        h, v, d = axes
        view_n = np.zeros(3); view_n[abs(d)] = 1.0 if d >= 0 else -1.0
        shade = 0.35 + 0.65 * np.abs(n @ (light if d == 2 else light[[2, 1, 0]]))
        base = np.array(cmap(k % 20)[:3])
        polys.append(tri[:, :, [h, v]])
        depth.append(tri[:, :, abs(d)].mean(1) * (1 if d >= 0 else -1))
        colors.append(base[None] * shade[:, None])
    if not polys:
        return
    P = np.concatenate(polys); D = np.concatenate(depth); C = np.concatenate(colors)
    o = np.argsort(D)
    ax.add_collection(PolyCollection(P[o], facecolors=np.clip(C[o], 0, 1), edgecolors='none'))
    ax.autoscale(); ax.set_aspect('equal'); ax.tick_params(labelsize=6)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out', help='output PNG'); ap.add_argument('files', nargs='+', metavar='file.g1m', help='files or glob patterns')
    args = ap.parse_args()
    out = args.out
    files = [g for a in args.files for g in (sorted(glob.glob(a)) or [a])]
    fig, axs = plt.subplots(len(files), 2, figsize=(6, 3.2 * len(files)), squeeze=False)
    for row, f in enumerate(files):
        m = gt.embedded_models(Path(f).read_bytes())[-1]
        tris = [None if gt.is_hidden(m, s) else submesh_tris(m, s) for s in m.submeshes]
        draw(axs[row][0], tris, (0, 1, 2))        # front: x right, y up, nearer = +z
        draw(axs[row][1], tris, (2, 1, 0))        # side
        axs[row][0].set_title(f'{Path(f).stem} front ({len(m.submeshes)} subs)', fontsize=7)
        axs[row][1].set_title('side (+z right)', fontsize=7)
    fig.tight_layout(); fig.savefig(out, dpi=80)


if __name__ == '__main__':
    main()
