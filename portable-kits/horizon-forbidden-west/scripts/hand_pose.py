"""Finger-curl test: skin Beta's vanilla upper-body skin and Karin builds on curled hands; count finger interpenetration
and write left-hand OBJs for rendering.

usage: hand_pose.py EXPORT OUTDIR NAME=WORK [NAME=WORK ...]
Builds are rendered without the cuff: only vertices of the fitted primitive SKIN_MESH (Karin's body skin) are written.
"""
import argparse
import os
import pickle
import sys

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hfwascii as H  # noqa: E402
from pose_preview import fk, rot, skin  # noqa: E402

ap = argparse.ArgumentParser(description='Curl the fingers of vanilla Beta and Karin builds; count vertices inside a '
                                         'neighbouring finger and write left-hand OBJs.')
ap.add_argument('export', help='h2 export folder with b2c4_skel_24.ascii and b2c4_3.ascii')
ap.add_argument('outdir', help='folder for <build>__<pose>.obj')
ap.add_argument('builds', nargs='+', metavar='NAME=WORK', help='build_hfw.py --work folders to compare')
args = ap.parse_args()
export, outdir = args.export, args.outdir
builds = dict(a.split('=', 1) for a in args.builds)
os.makedirs(outdir, exist_ok=True)
sk = H.read_skeleton(os.path.join(export, 'b2c4_skel_24.ascii'))
names = [b['name'] for b in sk]
idx = {n: i for i, n in enumerate(names)}
J = np.array([b['pos'] for b in sk])
FING = ('Index', 'Middle', 'Ring', 'Pinky')
SKIN_MESH = 'body_2'      # Karin_Original's body skin mesh (case constant)


def curl_axis(S, f):
    j = [J[idx[f'{S}_{f}_sjnt_{k}']] for k in range(3)]
    n = np.cross(j[1] - j[0], j[2] - j[1])
    return n / np.linalg.norm(n)


POSES = {'bind': (0, 0, 0, 0), 'relaxed': (25, 35, 20, 15), 'fist': (80, 95, 60, 35)}


def pose(angles):
    a0, a1, a2, th = angles
    d = {}
    for S in ('L', 'R'):
        for f in FING:
            n = curl_axis(S, f)
            for k, a in enumerate((a0, a1, a2)):
                if a:
                    d[f'{S}_{f}_sjnt_{k}'] = rot(n, a)
        if th:
            n = curl_axis(S, 'Thumb')
            for k in (1, 2):
                d[f'{S}_Thumb_sjnt_{k}'] = rot(n, th)
    return d


def finger_of(bi, bw):
    """dominant finger name per vertex if >= 0.6 of its weight is on that finger, else ''"""
    out = []
    for r_i, r_w in zip(bi, bw):
        acc = {}
        for b, w in zip(r_i, r_w):
            if w == w and w > 0:
                n = names[b]
                if n.startswith('L_') and any(f'_{f}_' in n for f in FING):
                    acc[n.split('_')[1]] = acc.get(n.split('_')[1], 0) + w
        f = max(acc, key=lambda k: acc[k]) if acc else ''
        out.append(f if f and acc[f] >= 0.6 else '')
    return np.array(out)


def axis_dist(P, M, f):
    """distance from posed points to finger f's posed bone polyline (j0, j1, j2, tip = j2 + 0.8 * (j2 - j1))"""
    j = [M[idx[f'L_{f}_sjnt_{k}']] @ np.append(J[idx[f'L_{f}_sjnt_{k}']], 1) for k in range(3)]
    j = [x[:3] for x in j]
    j.append(j[2] + 0.8 * (j[2] - j[1]))
    best = np.full(len(P), np.inf)
    for a, b in zip(j, j[1:]):
        ab = b - a
        t = np.clip(((P - a) @ ab) / (ab @ ab), 0, 1)
        best = np.minimum(best, np.linalg.norm(P - a - t[:, None] * ab, axis=1))
    return best


meshes = {}
_, van = H.read_meshes(os.path.join(export, 'b2c4_3.ascii'))
meshes['vanilla'] = [m for m in van if m['name'].startswith('mesh_215_sm_1')][0]
for name, work in builds.items():
    meshes[name] = H.read_meshes(os.path.join(work, 'ascii', 'lod0_215.ascii'), has_skeleton=True)[1][1]
    # skin only (the pullover cuff hides the hand): match vertices back to the fitted primitives
    pr = pickle.load(open(os.path.join(work, 'fit.pkl'), 'rb'))['prims']
    src = np.concatenate([q['P'] / 100.0 for q in pr])
    lab = np.concatenate([[q['mesh']] * len(q['P']) for q in pr])
    d, i = cKDTree(src).query(np.asarray(meshes[name]['pos'], float))
    meshes[name]['skin'] = (lab[i] == SKIN_MESH) & (d < 1e-5)

RADIUS = 0.0045   # m: inside another finger's core (vanilla finger radii are 0.40-0.86 cm)
for name, m in meshes.items():
    m['pos'] = np.asarray(m['pos'], float)
    fo = finger_of(m['bi'], m['bw'])
    for pname, ang in POSES.items():
        M = fk(sk, pose(ang))
        P = skin(m, M)
        line = []
        for fa, fb in (('Index', 'Middle'), ('Middle', 'Ring'), ('Ring', 'Pinky')):
            a_in_b = int((axis_dist(P[fo == fa], M, fb) < RADIUS).sum())
            b_in_a = int((axis_dist(P[fo == fb], M, fa) < RADIUS).sum())
            line.append(f'{fa[0]}{fb[0]} {a_in_b + b_in_a:3d}')
        print(f'{name:8s} {pname:8s} verts inside a neighbour finger core: ' + '  '.join(line))
        # left hand OBJ: triangles whose vertices all carry left wrist/finger weight
        hand = np.array([sum(w for b, w in zip(r_i, r_w) if w == w and w > 0 and
                             (names[b].startswith('L_') and (any(f'_{f}_' in names[b] for f in FING + ('Thumb',))
                                                             or names[b] == 'L_Wrist_sjnt_0')))
                         for r_i, r_w in zip(m['bi'], m['bw'])]) > 0.3
        faces = np.asarray(m['faces'])
        if 'skin' in m:
            hand &= m['skin']
        keep = hand[faces].all(1)
        with open(os.path.join(outdir, f'{name}__{pname}.obj'), 'w') as fo_:
            for p in P:
                fo_.write(f'v {p[0]:.5f} {p[1]:.5f} {p[2]:.5f}\n')
            for t in faces[keep] + 1:
                fo_.write(f'f {t[0]} {t[2]} {t[1]}\n')
