"""Apply game facial poses to the fitted face weights (face.json) and measure: blink closure (travel along the blink
target), brow movement, per pose. usage: face_sim.py  (N3_BUILD)"""
import argparse
import json
import sys
from pathlib import Path

if __name__ == '__main__':          # face_render.py and readback_blink.py import it
    argparse.ArgumentParser(description=__doc__).parse_args()

import numpy as np  # noqa: E402

T = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(T / 'n3build'))
sys.path.insert(0, str(T))
from n3_common import BUILD, CHEST, gt, load_model  # noqa: E402
import n3_face as nf  # noqa: E402
import fpose  # noqa: E402

conf = np.load(BUILD / 'conformed.npz')
hs = json.loads((BUILD / 'conform.json').read_text(encoding='utf-8'))['head_scale']
P = conf['Body__pos'].astype(float)
key = nf.shape_keys(hs)
face = json.loads((BUILD / 'face.json').read_text())['weights']
_, chest = load_model(CHEST)
joints, by_id = gt.skeleton(chest)
lib = fpose.parse_pose((BUILD / 'face' / '0xc76b3a43.g1fpose').read_bytes())
rest = nf.world(joints, by_id, {})
H = np.c_[P, np.ones(len(P))]
bones = sorted({b for v in face.values() for b, _ in v if b in by_id})
inv = {b: np.linalg.inv(rest[by_id[b]]) for b in bones}

blinkL, blinkR = key('blink_L'), key('blink_R')
browU = key('mayu_up_L') + key('mayu_up_R')
brow = np.linalg.norm(browU, axis=1) > 0.3
lidL = np.linalg.norm(blinkL, axis=1) > 0.5 * np.linalg.norm(blinkL, axis=1).max()
lidR = np.linalg.norm(blinkR, axis=1) > 0.5 * np.linalg.norm(blinkR, axis=1).max()
print('brow verts', brow.sum(), 'strong lid verts L/R', lidL.sum(), lidR.sum(), 'blink max', np.linalg.norm(blinkL, axis=1).max().round(2))


def disp(pose_w):
    """pose_w: {pose: weight}; linear blend of pose deltas is what the game does? -> evaluate each pose's bone delta scaled."""
    mix = {}
    for p, a in pose_w.items():
        for b, r in lib['poses'][p].items():
            m = mix.setdefault(b, {'rot': np.zeros(3), 'loc': np.zeros(3), 'scale': np.ones(3)})
            m['rot'] = m['rot'] + a * r['rot']; m['loc'] = m['loc'] + a * r['loc']
            m['scale'] = m['scale'] * (1 + a * (r['scale'] - 1))
    wm = nf.world(joints, by_id, mix)
    S = {b: wm[by_id[b]] @ inv[b] for b in bones}
    D = np.zeros_like(P)
    for v, lst in face.items():
        v = int(v)
        acc = np.zeros(3)
        for b, w in lst:
            if b in S:
                acc += w * ((S[b] @ H[v])[:3] - P[v])
        D[v] = acc
    return D


def travel(D, T, sel):
    t = T[sel]; d = D[sel]
    return float(((d * t).sum(1) / (t * t).sum(1)).mean())


for label, pw in [('41+42', {41: 1, 42: 1}), ('41', {41: 1}), ('27+28', {27: 1, 28: 1}), ('39+40', {39: 1, 40: 1}),
                  ('1+2 brow up', {1: 1, 2: 1}), ('3+4 brow down', {3: 1, 4: 1}), ('5+6 knit', {5: 1, 6: 1})]:
    D = disp(pw)
    print(f'{label:14s} lid travel L {travel(D, blinkL, lidL):5.2f} R {travel(D, blinkR, lidR):5.2f}   '
          f'brow move mean {np.linalg.norm(D[brow], axis=1).mean():.2f} max {np.linalg.norm(D[brow], axis=1).max():.2f} cm  '
          f'brow dy {D[brow, 1].mean():+.2f}')
