"""Cross-draw bone identity from frame-analysis cb0 skinning matrices.
cb0 layout (Nioh 2 skinned VS): 5 header float4, then 3 float4 rows per palette entry (3x4 row-major skin matrix).
Vertex BLENDINDICES are palette index * 3.
usage: bones.py <FrameAnalysis dir> <fa.json> <out.json> draw [draw ...]"""
import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fa_mesh import load_draw  # noqa: E402

HDR = 5


def palette(fadir, draw):
    f = glob.glob(os.path.join(fadir, f'{draw:06d}-vs-cb0=*.buf'))[0]
    a = np.fromfile(f, '<f4').reshape(-1, 4)
    n = (len(a) - HDR) // 3
    return a[HDR:HDR + 3 * n].reshape(n, 3, 4).astype(np.float64)


def skin_arrays(m):
    """(idx[n,k] palette entries, w[n,k]) from a decoded draw (handles 4 or 8 influences, implicit last weight)."""
    idx, w = [], []
    for layer in ('0', '1'):
        bi, bw = m.get('BLENDINDICES' + layer), m.get('BLENDWEIGHT' + layer)
        if bi is None:
            continue
        bi = bi.astype(np.int64)
        if bw is None:
            bw = np.zeros((len(bi), 0))
        bw = bw.astype(np.float64)
        k = bi.shape[1]
        if bw.shape[1] < k:  # implicit remaining weight on the last used slot
            rest = 1.0 - bw.sum(1, keepdims=True) - (sum(x.sum(1, keepdims=True) for x in w) if w else 0)
            bw = np.concatenate([bw, np.clip(rest, 0, 1), np.zeros((len(bw), k - bw.shape[1] - 1))], 1)
        idx.append(bi // 3)
        w.append(bw[:, :k])
    return np.concatenate(idx, 1), np.concatenate(w, 1)


def main(fadir, fajson, out, draws):
    fa = {d['draw']: d for d in json.load(open(fajson))}
    glob_mats = []          # list of 3x4
    table = {}
    for di in draws:
        m = load_draw(fadir, fa[di])
        P = m['POSITION0'][:, :3].astype(np.float64)
        used = np.unique(m['tris'])
        idx, w = skin_arrays(m)
        idx, w, Pu = idx[used], w[used], P[used]
        pal = palette(fadir, di)
        entries = {}
        for e in np.unique(idx[w > 1e-3]):
            mask = (idx == e) & (w > 1e-3)
            wsum = (w * mask).sum(1)
            sel = wsum > 0
            c = (Pu[sel] * wsum[sel, None]).sum(0) / wsum[sel].sum()
            M = pal[e]
            gid = None
            for g, G in enumerate(glob_mats):
                if np.abs(G - M).max() < 2e-3:
                    gid = g
                    break
            if gid is None:
                gid = len(glob_mats)
                glob_mats.append(M)
            entries[int(e)] = {'gid': gid, 'center': np.round(c, 2).tolist(), 'mass': round(float(wsum.sum()), 1)}
        table[di] = {'vs': fa[di]['vs'], 'ps': fa[di]['ps'], 'ib': fa[di]['ib']['hash'], 'nverts': int(len(P)),
                     'palette_len': int(len(pal)), 'entries': entries}
        print(di, 'entries', len(entries), 'gids', sorted(v['gid'] for v in entries.values()), flush=True)
    json.dump({'draws': table, 'mats': [g.tolist() for g in glob_mats]}, open(out, 'w'))


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('fadir', metavar='FrameAnalysis_dir'); ap.add_argument('fajson', metavar='fa.json')
    ap.add_argument('out', metavar='out.json'); ap.add_argument('draws', nargs='+', type=int, metavar='draw')
    a = ap.parse_args()
    main(a.fadir, a.fajson, a.out, a.draws)
