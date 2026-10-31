"""Skin the built chest's face submesh with facial poses using the file's own palettes / MM1G binds; render + stats.
usage: facecheck.py <model>[.g1m] <submesh> [preset hash] [--png facecheck.png]
reads N3_BUILD/g1m/<model>.g1m, N3_BUILD/face/0xc76b3a43.g1fpose and N3_BUILD/face/<preset>.g1frani"""
import argparse, sys, json
from pathlib import Path
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('model', help='0x5548953f or 0x5548953f.g1m (in N3_BUILD/g1m)'); ap.add_argument('submesh', type=int, help='face submesh index')
ap.add_argument('preset', nargs='?', default='0x7c836955', help='expression preset g1frani (default 0x7c836955)')
ap.add_argument('--png', default='facecheck.png', help='renders (default: facecheck.png in the current folder)')
args = ap.parse_args()
import numpy as np
T = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(T)); sys.path.insert(0, str(T / 'n3build'))
import g1m_tool as gt, fpose, face_bones as fb
from n3_face import world
from n3_common import BUILD as S
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
model, sub = args.model, args.submesh
d = (S / 'g1m' / f'{model}.g1m').read_bytes() if not model.endswith('.g1m') else (S / 'g1m' / model).read_bytes(); m = gt.embedded_models(d)[-1]
joints, by_id = gt.skeleton(m)
mats = gt.binds(m)
s = m.submeshes[sub]; pal = m.palettes[s['palette']]
pos, W, I = fb.vertex_weights(d, m, s)
sl = slice(s['vertex_offset'], s['vertex_offset'] + s['vertex_count']); pos, W, I = pos[sl].astype(float), W[sl], I[sl]
tris = np.array(gt.submesh_indices(m, s)[2]).reshape(-1, 3) - s['vertex_offset']
lib = fpose.parse_pose((S / 'face/0xc76b3a43.g1fpose').read_bytes())
IB = [np.array(mats[e['g1mm']], float).reshape(4, 4) for e in pal]
def skin(pose):
    wm = world(joints, by_id, pose)
    Mk = [wm[e['joint']] @ IB[k].T if False else None for k, e in enumerate(pal)]
    return wm
# figure out the bind convention: rest pose must reproduce pos
wm0 = world(joints, by_id, {})
def skinned(wm):
    out = np.zeros_like(pos); H = np.c_[pos, np.ones(len(pos))]
    cache = {}
    for k in range(W.shape[1]):
        idx = I[:, k] // 3
        for pi in np.unique(idx):
            if pi not in cache:
                e = pal[pi]; A = np.array(mats[e['g1mm']], float).reshape(4, 4)
                cand = [wm[e['joint']] @ A, wm[e['joint']] @ A.T, (A @ wm[e['joint']].T).T, (A.T @ wm[e['joint']].T).T]
                cache[pi] = cand
        for c in range(4):
            pass
    return cache
cache = skinned(wm0)
# choose the convention whose rest skin matrix is identity for the most entries
best = min(range(4), key=lambda c: sum(np.abs(v[c] - np.eye(4)).max() for v in cache.values()))
print('bind convention', best, 'max rest deviation', max(np.abs(v[best] - np.eye(4)).max() for v in cache.values()))
def deform(pose):
    wm = world(joints, by_id, pose)
    H = np.c_[pos, np.ones(len(pos))]; out = np.zeros_like(pos)
    Sm = {}
    for pi, e in enumerate(pal):
        A = np.array(mats[e['g1mm']], float).reshape(4, 4)
        Sm[pi] = [wm[e['joint']] @ A, wm[e['joint']] @ A.T, (A @ wm[e['joint']].T).T, (A.T @ wm[e['joint']].T).T][best]
    for k in range(W.shape[1]):
        M = np.stack([Sm[i] for i in I[:, k] // 3])
        out += W[:, k:k+1] * np.einsum('nij,nj->ni', M, H)[:, :3]
    return out
rest = deform({})
print('rest drift max', np.abs(rest - pos).max())
head = pos[:, 1] > 158
def mixw(ws):
    acc = {}
    for p, w in ws.items():
        if p >= len(lib['poses']): continue
        for b, r in lib['poses'][p].items():
            a = acc.setdefault(b, {'rot': np.zeros(3), 'loc': np.zeros(3), 'scale': np.ones(3)})
            a['rot'] = a['rot'] + w * r['rot']; a['loc'] = a['loc'] + w * r['loc']
    return acc
def mix(*ps):
    return mixw({p: 1.0 for p in ps})
preset = fpose.parse_anim((S / 'face' / args.preset).with_suffix('.g1frani').read_bytes())['frames'][0]
views = [('rest', {}), ('blink 41+42', mix(41, 42)), ('jaw 187', mix(187)), ('brow up 1+2', mix(1, 2)), ('27+28', mix(27, 28)), ('39+40', mix(39, 40)), ('smile 59+60', mix(59, 60)), ('preset', mixw(preset))]
fig, axs = plt.subplots(2, len(views), figsize=(4 * len(views), 8))
keep = head[tris].all(1)
for col, (name, pose) in enumerate(views):
    V = deform(pose)
    print(name, 'max move', np.linalg.norm(V - rest, axis=1).max().round(2))
    for row, ax_ in enumerate(((0, 1), (2, 1))):
        ax = axs[row, col]
        t = tris[keep]
        P2 = V[t][:, :, list(ax_)]
        depth = V[t][:, :, 2 if row == 0 else 0].mean(1)
        order = np.argsort(depth if row == 0 else -depth)
        n = np.cross(V[t[:, 1]] - V[t[:, 0]], V[t[:, 2]] - V[t[:, 0]]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
        shade = np.clip(np.abs(n[:, 2 if row == 0 else 0]), 0.15, 1)
        ax.add_collection(PolyCollection(P2[order], facecolors=plt.cm.gray(shade[order]), edgecolors='none'))
        ax.set_xlim(-14, 14) if row == 0 else ax.set_xlim(-14, 14); ax.set_ylim(158, 190); ax.set_aspect('equal'); ax.set_title(name)
plt.tight_layout(); plt.savefig(args.png, dpi=70)
