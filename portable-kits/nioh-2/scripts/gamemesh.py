"""Load the game's character draws (bind space, cm) with per-vertex global-bone weights."""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fa_mesh import load_draw
from bones import skin_arrays

def load(fadir, fajson, bonesjson, draws):
    fa = {d['draw']: d for d in json.load(open(fajson))}
    B = json.load(open(bonesjson))
    out = {}
    for di in draws:
        t = B['draws'][str(di)]
        m = load_draw(fadir, fa[di])
        P = m['POSITION0'][:, :3].astype(np.float64)
        idx, w = skin_arrays(m)
        e2g = {int(k): v['gid'] for k, v in t['entries'].items()}
        G = np.vectorize(lambda e: e2g.get(int(e), -1))(idx)
        w = np.where(G >= 0, w, 0)
        out[di] = {'P': P, 'gid': G, 'w': w, 'tris': m['tris'], 'm': m, 'ib': t['ib'], 'entries': t['entries']}
    return out
