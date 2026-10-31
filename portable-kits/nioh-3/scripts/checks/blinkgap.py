"""Fitted vs target displacement for the blink poses, from a face json: along-target ratio and perpendicular error.
usage: blinkgap.py <face.json>   (conformed.npz / conform.json / source / face from N3_BUILD)"""
import argparse, sys, json
from pathlib import Path
ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('face_json', help='n3_face.py output')
args = ap.parse_args()
import numpy as np
T = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(T)); sys.path.insert(0, str(T / 'n3build'))
import fpose, n3_face as nf
from n3_common import BUILD, CHEST, gt, load_model
fj = json.loads(Path(args.face_json).read_text())['weights']
conf = np.load(BUILD / 'conformed.npz'); P = conf['Body__pos'].astype(float)
key = nf.shape_keys(json.loads((BUILD / 'conform.json').read_text())['head_scale'])
_, chest = load_model(CHEST); joints, by_id = gt.skeleton(chest)
lib = fpose.parse_pose(nf.POSE_LIB.read_bytes())
rest = nf.world(joints, by_id, {}); H = np.c_[P, np.ones(len(P))]
for p, name in ((41, 'blink_L'), (42, 'blink_R'), (187, 'kuchi_A')):
    t = key(name); wm = nf.world(joints, by_id, lib['poses'][p])
    got = np.zeros_like(P)
    for v, pairs in fj.items():
        v = int(v)
        for b, w in pairs:
            if b in by_id:
                S = wm[by_id[b]] @ np.linalg.inv(rest[by_id[b]])
                got[v] += w * ((S @ H[v])[:3] - P[v])
    n = np.linalg.norm(t, axis=1); big = n > 0.5 * n.max()
    along = (got[big] * t[big]).sum(1) / n[big] ** 2
    perp = np.linalg.norm(got[big] - along[:, None] * t[big], axis=1)
    print(p, name, 'verts', big.sum(), 'travel max', n.max().round(2), 'along ratio min/mean', along.min().round(3), along.mean().round(3),
          'perp max', perp.max().round(3), 'gap(cm) max', ((1 - along) * n[big]).max().round(3))
    worst = np.argsort(along)[:5]; idx = np.where(big)[0][worst]
    for i, a in zip(idx, along[worst]): print('   v', i, 'pos', P[i].round(2), 'target', t[i].round(2), 'got', got[i].round(2))
