"""Facial test poses on the 719 skeleton: skin Beta's vanilla face (625 sm0) and a build's face (lod0_625) and write OBJs.

usage: face_pose.py EXPORT OUTDIR NAME=WORK [NAME=WORK ...]
Poses move Beta's controller joints (jaw rotation, lip corners, forehead, upper lids) as test deltas, not game
animation; they show whether Karin's face follows the same joints as Beta's (blink: her eyes are meant to stay open).
"""
import argparse
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hfwascii as H  # noqa: E402
from pose_preview import rot  # noqa: E402

ap = argparse.ArgumentParser(description="Skin Beta's vanilla face and builds' faces on facial test poses and write "
                                         'OBJs (with the build UVs).')
ap.add_argument('export', help='h2 export folder with 719_skel_0.ascii and b2c4_1.ascii')
ap.add_argument('outdir', help='folder for <build>__<pose>.obj')
ap.add_argument('builds', nargs='+', metavar='NAME=WORK', help='build_hfw.py --work folders to compare')
args = ap.parse_args()
export, outdir = args.export, args.outdir
builds = dict(a.split('=', 1) for a in args.builds)
os.makedirs(outdir, exist_ok=True)
sk = H.read_skeleton(os.path.join(export, '719_skel_0.ascii'))
names = [b['name'] for b in sk]
J = np.array([b['pos'] for b in sk])


def fk(deltas):
    """deltas: name -> (3x3 rotation about the bind pivot, translation) in world bind space; children inherit"""
    M = [None] * len(sk)
    for i, b in enumerate(sk):
        D = np.eye(4)
        if b['name'] in deltas:
            R, t = deltas[b['name']]
            D[:3, :3] = R
            D[:3, 3] = J[i] - R @ J[i] + np.asarray(t) / 100.0
        M[i] = D if b['parent'] < 0 else M[b['parent']] @ D
    return np.array(M)


def by(pattern):
    return [n for n in names if re.search(pattern, n)]


I3 = np.eye(3)
POSES = {
    'neutral': {},
    'jaw_open': {'FACIAL_C_Jaw': (rot([1, 0, 0], -14), (0, 0, 0)), 'FACIAL_C_LowerLipRotation': (rot([1, 0, 0], -14), (0, 0, 0))},
    'smile': {**{n: (I3, (-0.35, 0.1, 0.45)) for n in by(r'^FACIAL_L_LipCorner$')},
              **{n: (I3, (0.35, 0.1, 0.45)) for n in by(r'^FACIAL_R_LipCorner$')}},
    'lips_apart': {**{n: (I3, (0, 0.1, 0.35)) for n in by(r'^FACIAL_[LCR]_LipUpper$|^FACIAL_C_MouthUpper$')},
                   **{n: (I3, (0, 0.1, -0.6)) for n in by(r'^FACIAL_C_LowerLipRotation$')}},
    'brow_up': {n: (I3, (0, 0, 0.5)) for n in by(r'Forehead[A-Za-z]*$') if '12IPV' not in n},
    'blink': {n: (I3, (0, 0, -0.8)) for n in by(r'EyelidUpper[A-Za-z]*$') if '12IPV' not in n},
}


def skin(m, M):
    P = np.c_[np.asarray(m['pos'], float), np.ones(len(m['pos']))]
    out = np.zeros((len(P), 3))
    bi = np.asarray(m['bi'])
    bw = np.nan_to_num(np.asarray(m['bw'], float))
    for k in range(bi.shape[1]):
        out += bw[:, k, None] * np.einsum('vij,vj->vi', M[bi[:, k]], P)[:, :3]
    return out


meshes = {}
_, van = H.read_meshes(os.path.join(export, 'b2c4_1.ascii'))
meshes['beta'] = [m for m in van if m['name'].startswith('mesh_625_sm_0')][0]
for name, work in builds.items():
    meshes[name] = H.read_meshes(os.path.join(work, 'ascii', 'lod0_625.ascii'), has_skeleton=True)[1][0]
for pname, d in POSES.items():
    M = fk(d)
    for name, m in meshes.items():
        P = skin(m, M)
        rest = np.asarray(m['pos'], float)
        faces = np.asarray(m['faces'])
        faces = faces[(rest[faces][:, :, 2] > 1.3).all(1)]
        print(f'{name:8s} {pname:10s} max move {np.linalg.norm(P - rest, axis=1).max() * 100:5.2f} cm')
        with open(os.path.join(outdir, f'{name}__{pname}.obj'), 'w') as fo:
            for p in P:
                fo.write(f'v {p[0]:.5f} {p[1]:.5f} {p[2]:.5f}\n')
            for u in m['uv'][0]:
                fo.write(f'vt {u[0]:.5f} {u[1]:.5f}\n')
            for t in faces + 1:
                fo.write(f'f {t[0]}/{t[0]} {t[2]}/{t[2]} {t[1]}/{t[1]}\n')
