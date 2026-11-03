"""Blink from the BUILT g1m (not face.json): decode the face submesh's positions / weights / palette, pose them with the
game face poses, map onto the conformed Body vertices by position and compare with face_sim's displacement.
usage: readback_blink.py <out.png> <built.g1m> <model dir>  (face_render writes argv[1] on import)   (N3_BUILD)"""
import argparse
import sys
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('out_png'); ap.add_argument('built_g1m')
ap.add_argument('model_dir', help="source model folder, for face_render.py's textures")
args = ap.parse_args()

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
argv, sys.argv = sys.argv, [sys.argv[0], args.out_png, args.model_dir]     # face_render.py reads its own arguments
import face_render as fr  # noqa: E402
sys.argv = argv
fs = fr.fs
nf, gt = fs.nf, fs.gt
from scipy.spatial import cKDTree  # noqa: E402

data = Path(args.built_g1m).read_bytes()
m = gt.embedded_models(data)[-1]
joints, by_id = gt.skeleton(m)
rest = nf.world(joints, by_id, {})


def decode(s):
    a = m.attributes[s['vertex_buffer']]; vb = m.vertex_buffers[a['buffers'][0]]
    raw = np.frombuffer(data, np.uint8, vb['count'] * vb['stride'], vb['offset']).reshape(vb['count'], vb['stride'])
    W, I, pos = [], [], None
    for x in a['attrs']:
        if x['buffer'] != 0:
            continue
        if x['semantic'] == 'POSITION' and x['layer'] == 0:
            pos = raw[:, x['offset']:x['offset'] + 12].copy().view('<f4').astype(float)
        if x['semantic'] == 'BLENDWEIGHT':
            n = {0x0B: 4, 0x0A: 2}[x['type']]
            W.append(raw[:, x['offset']:x['offset'] + 2 * n].copy().view('<f2').astype(float).reshape(-1, n))
        if x['semantic'] == 'BLENDINDICES':
            I.append(raw[:, x['offset']:x['offset'] + 8].copy().view('<u2').astype(int) if x['type'] == 0x07
                     else raw[:, x['offset']:x['offset'] + 4].astype(int))
    W = np.concatenate(W, 1); I = np.concatenate(I, 1)
    v0, nv = s['vertex_offset'], s['vertex_count']
    return pos[v0:v0 + nv], W[v0:v0 + nv], I[v0:v0 + nv], m.palettes[s['palette']]


# the face submesh: the visible one whose vertices sit nearest the Body positions
tree = cKDTree(fs.P)
best = None
for s in m.submeshes:
    if gt.is_hidden(m, s):
        continue
    pos, W, I, pal = decode(s)
    d, _ = tree.query(pos)
    score = (d < 1e-3).mean()
    if best is None or score > best[0]:
        best = (score, s, pos, W, I, pal)
score, s, pos, W, I, pal = best
print('face submesh', s['id'], 'verts', len(pos), 'match frac', round(score, 4), 'palette', len(pal))
sid = {j: b for b, j in by_id.items()}   # palette 'joint' is the storage index
bone = np.array([[sid[pal[i // 3]['joint']] for i in row] for row in I])
print('weight sum range', W.sum(1).min().round(5), W.sum(1).max().round(5), 'w range', W.min().round(3), W.max().round(3))


def disp_rb(pose_w):
    mix = {}
    for p, a in pose_w.items():
        for b, r in fs.lib['poses'][p].items():
            mm = mix.setdefault(b, {'rot': np.zeros(3), 'loc': np.zeros(3), 'scale': np.ones(3)})
            mm['rot'] = mm['rot'] + a * r['rot']; mm['loc'] = mm['loc'] + a * r['loc']
            mm['scale'] = mm['scale'] * (1 + a * (r['scale'] - 1))
    wm = nf.world(joints, by_id, mix)
    H = np.c_[pos, np.ones(len(pos))]
    D = np.zeros_like(pos)
    for b in np.unique(bone):
        S = wm[by_id[b]] @ np.linalg.inv(rest[by_id[b]])
        moved = (H @ S.T)[:, :3] - pos
        D += (W * (bone == b)).sum(1)[:, None] * moved
    return D


# Body vertex -> g1m vertex by position (several g1m vertices per Body vertex at UV seams: all must agree)
tb = cKDTree(pos)
dist, near = tb.query(fs.P)
print('Body->g1m nearest dist max', dist.max().round(5))
for label, pw in (('41+42', {41: 1, 42: 1}), ('27+28', {27: 1, 28: 1}), ('1+2', {1: 1, 2: 1})):
    Dr = disp_rb(pw)[near]
    Ds = fs.disp(pw)
    err = np.linalg.norm(Dr - Ds, axis=1)
    print(f'{label:6s} readback vs face.json: max diff {err.max():.4f} cm  mean {err.mean():.5f}  '
          f'lid travel L {fs.travel(Dr, fs.blinkL, fs.lidL):.2f} R {fs.travel(Dr, fs.blinkR, fs.lidR):.2f}  '
          f'brow move max {np.linalg.norm(Dr[fs.brow], axis=1).max():.2f}')
# seam duplicates: do all g1m copies of a position move the same?
Dall = disp_rb({41: 1, 42: 1})
groups = {}
for k, n in enumerate(tb.query(pos)[1]):
    pass
dd, nn = tree.query(pos)
spread = np.zeros(len(fs.P))
for k in range(len(pos)):
    j = nn[k]
    spread[j] = max(spread[j], np.linalg.norm(Dall[k] - Dall[near[j]]))
print('max disagreement between seam copies', spread.max().round(4))
P = fs.P
cx, cy = P[fs.lidL, 0].mean(), P[fs.lidL, 1].mean()
box = (cx - 4.5, cx + 4.5, cy - 4, cy + 5)
imgs = [fr.render(P + fs.disp({41: 1, 42: 1}), box), fr.render(P + disp_rb({41: 1, 42: 1})[near], box)]
Image.fromarray(np.concatenate(imgs, 1)).save(args.out_png)
print('saved: face.json sim | g1m readback')
