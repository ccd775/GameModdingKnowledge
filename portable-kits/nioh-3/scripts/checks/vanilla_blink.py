"""How far the VANILLA female head's upper lid closes under each face animation's blink frames, vs pose 41 at 1.
Upper lid = the head vertices that pose 41 (left) moves down the most. usage: vanilla_blink.py   (N3_BUILD)"""
import argparse
import sys
from pathlib import Path

argparse.ArgumentParser(description=__doc__).parse_args()

import numpy as np  # noqa: E402

T = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(T))
sys.path.insert(0, str(T / 'n3build'))
import fpose  # noqa: E402
import g1m_tool as gt  # noqa: E402
import n3_face as nf  # noqa: E402
from n3_common import BUILD as B  # noqa: E402
data = (B / 'orig' / '0xb24cac84.g1m').read_bytes()
m = gt.embedded_models(data)[-1]
joints, by_id = gt.skeleton(m)
sid = {j: b for b, j in by_id.items()}
rest = nf.world(joints, by_id, {})
lib = fpose.parse_pose((B / 'face' / '0xc76b3a43.g1fpose').read_bytes())

pos_l, W_l, bone_l = [], [], []
for s in m.submeshes:
    if gt.is_hidden(m, s):
        continue
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
    if pos is None or not W:
        continue
    W = np.concatenate(W, 1); I = np.concatenate(I, 1)
    W = np.c_[W, 1 - W.sum(1)] if W.shape[1] < I.shape[1] else W     # implicit last weight
    v0, nv = s['vertex_offset'], s['vertex_count']
    pal = m.palettes[s['palette']]
    pos_l.append(pos[v0:v0 + nv]); W_l.append(W[v0:v0 + nv, :I.shape[1]])
    bone_l.append(np.array([[sid[pal[i // 3]['joint']] for i in row] for row in I[v0:v0 + nv]]))
k = max(w.shape[1] for w in W_l)
pos = np.concatenate(pos_l)
W = np.concatenate([np.pad(w, ((0, 0), (0, k - w.shape[1]))) for w in W_l])
bone = np.concatenate([np.pad(b, ((0, 0), (0, k - b.shape[1])), constant_values=bone_l[0][0, 0]) for b in bone_l])
print('vanilla head verts', len(pos), 'weight sum', W.sum(1).min().round(3), W.sum(1).max().round(3))


def disp(pose_w):
    mix = {}
    for p, a in pose_w.items():
        for b, r in lib['poses'][p].items():
            mm = mix.setdefault(b, {'rot': np.zeros(3), 'loc': np.zeros(3), 'scale': np.ones(3)})
            mm['rot'] = mm['rot'] + a * r['rot']; mm['loc'] = mm['loc'] + a * r['loc']
            mm['scale'] = mm['scale'] * (1 + a * (r['scale'] - 1))
    wm = nf.world(joints, by_id, mix)
    H = np.c_[pos, np.ones(len(pos))]
    D = np.zeros_like(pos)
    for b in np.unique(bone):
        if b not in by_id:
            continue
        S = wm[by_id[b]] @ np.linalg.inv(rest[by_id[b]])
        D += (W * (bone == b)).sum(1)[:, None] * ((H @ S.T)[:, :3] - pos)
    return D


D41 = disp({41: 1.0, 42: 1.0})
for side, sgn in (('L', 1), ('R', -1)):
    eye = np.sign(pos[:, 0]) == sgn
    dy = -D41[:, 1] * eye
    lid = dy > 0.7 * dy.max()
    print(f'{side}: upper lid verts {lid.sum()}, 41/42 drop mean {dy[lid].mean():.2f} max {dy.max():.2f} cm')
    if side == 'L':
        LID, REF = lid, dy[lid].mean()


def closure(pw):
    D = disp(pw)
    return float((-D[LID, 1]).mean() / REF)


for p in (27, 39, 41):
    print(f'pose {p} @1: {closure({p: 1.0, p + 1: 1.0}):.2f} of 41@1')
for f in sorted((B / 'face').glob('*.g1frani')):
    a = fpose.parse_anim(f.read_bytes())
    fr = a['frames']
    if len(fr) < 2:
        continue
    lidw = np.array([max(x.get(41, 0), x.get(39, 0), x.get(27, 0)) for x in fr])
    peaks = [i for i in range(1, len(fr) - 1) if lidw[i] >= lidw[i - 1] and lidw[i] > lidw[i + 1] and lidw[i] > 0.3]
    print(f'{f.stem}: frames {len(fr)} bound {a["bound"]}, blink peaks at {peaks[:8]}')
    for i in peaks[:3]:
        pw = {p: w for p, w in fr[i].items() if p < len(lib['poses'])}
        main = {p: round(w, 2) for p, w in fr[i].items() if w > 0.15}
        print(f'   frame {i}: vanilla closure {closure(pw):.2f}   poses>0.15 {main}')

