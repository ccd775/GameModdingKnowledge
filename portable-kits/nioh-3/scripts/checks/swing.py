"""Skin a built G1M's visible submeshes with its own palettes / MM1G binds: bind-pose drift, then swing every chain
rigidly about its root (all its joints) and check only that chain's vertices move; render side views.
usage: swing.py <file.g1m> [angle deg] [--png swing.png]   (chain list: N3_BUILD/g1m/build_report[_samurai].json)"""
import argparse, sys, json
from pathlib import Path
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('file', help='built .g1m'); ap.add_argument('angle', nargs='?', type=float, default=30, help='degrees (default 30)')
ap.add_argument('--png', default='swing.png', help='side / front views (default: swing.png in the current folder)')
args = ap.parse_args()
import numpy as np
T = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(T)); sys.path.insert(0, str(T / 'n3build'))
import g1m_tool as gt, face_bones as fb
from n3_common import BUILD
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
f = Path(args.file); ang = np.radians(args.angle)
d = f.read_bytes(); m = gt.embedded_models(d)[-1]
rep = json.loads((BUILD / 'g1m' / ('build_report.json' if '5548953f' in f.name else 'build_report_samurai.json')).read_text())
joints, by_id = gt.skeleton(m); mats = gt.binds(m)
W0 = [np.array(j['world'], float) for j in joints]
def rot(axis, a):
    k = np.array(axis, float); k /= np.linalg.norm(k); K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.sin(a) * K + (1 - np.cos(a)) * K @ K
subs, seen = [], {}
for s in m.submeshes:                      # submeshes sharing a vertex buffer + palette (chain splits) merge
    if gt.is_hidden(m, s): continue
    tris = np.array(gt.submesh_indices(m, s)[2]).reshape(-1, 3) - s['vertex_offset']
    key = (s['vertex_buffer'], s['palette'], s['vertex_offset'], s['vertex_count'])
    if key in seen:
        i = seen[key]; subs[i] = subs[i][:5] + (np.r_[subs[i][5], tris],); continue
    pos, W, I = fb.vertex_weights(d, m, s)
    sl = slice(s['vertex_offset'], s['vertex_offset'] + s['vertex_count'])
    seen[key] = len(subs)
    subs.append((s, pos[sl].astype(float), W[sl], I[sl], m.palettes[s['palette']], tris))
print('visible vertex sets', len(subs), 'triangles', sum(len(x[5]) for x in subs))
def skin(Wm):
    out = []
    for s, pos, W, I, pal, tris in subs:
        M = np.stack([Wm[e['joint']] @ np.array(mats[e['g1mm']], float).reshape(4, 4).T for e in pal])
        H = np.c_[pos, np.ones(len(pos))]; v = np.zeros_like(pos)
        for k in range(W.shape[1]):
            v += W[:, k:k + 1] * np.einsum('nij,nj->ni', M[I[:, k] // 3], H)[:, :3]
        out.append(v)
    return out
rest = skin(W0)
print('bind drift max', max(np.abs(r - s[1]).max() for r, s in zip(rest, subs)).round(6))
st = {b: s for b, s in by_id.items()}
swung = [r.copy() for r in rest]
bad = 0
for c in rep['physics']:
    p0 = np.array(joints[c['storages'][0]]['world_p'])
    axis = [1, 0, 0] if abs(p0[0]) < 3 or c['name'].startswith(('Tail', 'Hair_tail', 'Skirt')) else [0, 0, 1]
    R = np.eye(4); R[:3, :3] = rot(axis, ang); R[:3, 3] = p0 - R[:3, :3] @ p0
    Wm = list(W0)
    for stg in c['storages']:
        Wm[stg] = R @ W0[stg]
    v = skin(Wm)
    own = set(c['storages'])
    for (s, pos, W, I, pal, tris), a, b, sw in zip(subs, rest, v, swung):
        moved = np.linalg.norm(b - a, axis=1) > 1e-4
        onit = np.array([any(W[i, k] != 0 and pal[I[i, k] // 3]['joint'] in own for k in range(W.shape[1])) for i in range(len(pos))])
        if (moved != onit).any():
            bad += 1; print('MISMATCH', c['name'], 'sub', s['id'], 'moved', moved.sum(), 'weighted', onit.sum())
        sw += b - a
    print(f"{c['name']:16s} moved {sum(int((np.linalg.norm(b - a, axis=1) > 1e-4).sum()) for a, b in zip(rest, v)):5d} max {max(np.linalg.norm(b - a, axis=1).max() for a, b in zip(rest, v)):6.2f} cm")
print('chains', len(rep['physics']), 'mismatches', bad)
fig, axs = plt.subplots(1, 4, figsize=(22, 9))
for ax, (V, title, dims) in zip(axs, ((rest, 'rest side', (2, 1)), (swung, f'all chains +{np.degrees(ang):.0f} deg side', (2, 1)),
                                       (rest, 'rest front', (0, 1)), (swung, 'swung front', (0, 1)))):
    for (s, pos, W, I, pal, tris), v in zip(subs, V):
        P2 = v[tris][:, :, list(dims)]
        depth = v[tris][:, :, 0 if dims[0] == 2 else 2].mean(1)
        n = np.cross(v[tris[:, 1]] - v[tris[:, 0]], v[tris[:, 2]] - v[tris[:, 0]]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
        shade = np.clip(np.abs(n[:, 0 if dims[0] == 2 else 2]), 0.15, 1)
        o = np.argsort(depth if dims[0] == 2 else depth)
        ax.add_collection(PolyCollection(P2[o], facecolors=plt.cm.gray(shade[o]), edgecolors='none'))
    ax.set_xlim(-60, 60); ax.set_ylim(0, 200); ax.set_aspect('equal'); ax.set_title(title)
plt.tight_layout(); plt.savefig(args.png, dpi=60)
