"""Linear-blend-skin the written ascii meshes on test poses and dump OBJs for rendering.

usage: pose_preview.py WORK EXPORT OUTDIR
Poses rotate bones about their bind pivots (world axes); child bones inherit (FK in bind space).
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hfwascii as H  # noqa: E402


def rot(axis, deg):
    a = np.asarray(axis, float)
    a /= np.linalg.norm(a)
    t = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(t) * K + (1 - np.cos(t)) * K @ K


def fk(sk, deltas):
    """deltas: {bone name: 3x3 world rotation about its bind pivot}. Returns per-bone 4x4 skinning matrices."""
    n = len(sk)
    M = [None] * n
    for i, b in enumerate(sk):   # parents precede children in the export order
        D = np.eye(4)
        if b['name'] in deltas:
            R = deltas[b['name']]
            p = np.array(b['pos'])
            D[:3, :3] = R
            D[:3, 3] = p - R @ p
        par = b['parent']
        M[i] = D if par < 0 else M[par] @ D
    return np.array(M)


def skin(m, M):
    P = np.concatenate([m['pos'], np.ones((len(m['pos']), 1))], 1)
    out = np.zeros((len(P), 3))
    for k in range(len(m['bi'][0])):
        bi = np.array([r[k] for r in m['bi']])
        bw = np.array([r[k] for r in m['bw']])
        out += bw[:, None] * np.einsum('vij,vj->vi', M[bi], P)[:, :3]
    return out


POSES = {
    'bind': {},
    'arms_down': {'L_Arm_sjnt_0': rot([0, 1, 0], -40), 'R_Arm_sjnt_0': rot([0, 1, 0], 40)},
    'arms_up': {'L_Arm_sjnt_0': rot([0, 1, 0], 75), 'R_Arm_sjnt_0': rot([0, 1, 0], -75),
                'L_Arm_sjnt_1': rot([0, 0, 1], 30), 'R_Arm_sjnt_1': rot([0, 0, 1], -30)},
    'crouch': {'L_Leg_sjnt_0': rot([1, 0, 0], 70), 'R_Leg_sjnt_0': rot([1, 0, 0], 70),
               'L_Leg_sjnt_1': rot([1, 0, 0], -110), 'R_Leg_sjnt_1': rot([1, 0, 0], -110),
               'C_Spine_sjnt_2': rot([1, 0, 0], -20)},
    'head_turn': {'C_Neck_sjnt_1': rot([0, 0, 1], 35), 'C_Head_sjnt_0': rot([1, 0, 0], 20),
                  'L_Arm_sjnt_1': rot([0, 0, 1], -60)},
}


def main():
    ap = argparse.ArgumentParser(description='Skin the written LOD0 ascii meshes on test poses and write OBJs.')
    ap.add_argument('work', help='build_hfw.py --work folder')
    ap.add_argument('export', help='h2 export folder with b2c4_skel_24.ascii and 719_skel_0.ascii')
    ap.add_argument('outdir', help='folder for <pose>__<mesh>.obj')
    a = ap.parse_args()
    work, export, outdir = a.work, a.export, a.outdir
    os.makedirs(outdir, exist_ok=True)
    skb = H.read_skeleton(os.path.join(export, 'b2c4_skel_24.ascii'))
    sk7 = H.read_skeleton(os.path.join(export, '719_skel_0.ascii'))
    files = [('lod0_215.ascii', skb, 1), ('lod0_260.ascii', skb, 0), ('lod0_625.ascii', sk7, 0)]
    for pose, deltas in POSES.items():
        Mb = fk(skb, deltas)
        # the facial skeleton shares names with the body for neck/head: drive it with the same world deltas,
        # rooted at C_Spine_sjnt_4 whose body transform it inherits
        root = [i for i, b in enumerate(skb) if b['name'] == 'C_Spine_sjnt_4'][0]
        M7 = fk(sk7, deltas)
        M7 = np.einsum('ij,njk->nik', Mb[root], M7)
        for f, sk, si in files:
            bones, ms = H.read_meshes(os.path.join(work, 'ascii', f), has_skeleton=True)
            m = ms[si]
            P = skin(m, M7 if sk is sk7 else Mb)
            name = os.path.join(outdir, f'{pose}__{f[:-6]}.obj')
            with open(name, 'w') as fo:
                fo.write(f'mtllib none\nusemtl {"A" if sk is sk7 else "B"}\n')
                for p in P:
                    fo.write(f'v {p[0]:.5f} {p[1]:.5f} {p[2]:.5f}\n')
                for u in m['uv'][0]:
                    fo.write(f'vt {u[0]:.5f} {u[1]:.5f}\n')
                for t in m['faces'] + 1:
                    fo.write(f'f {t[0]}/{t[0]} {t[1]}/{t[1]} {t[2]}/{t[2]}\n')
    print('ok')


if __name__ == '__main__':
    main()
