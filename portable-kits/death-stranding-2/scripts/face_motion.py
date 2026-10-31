"""World-space joint motion of Sam's facial rig (skeleton 67711) for single RigLogic raw controls at 1.0.

python face_motion.py <out.json>
For each control in CONTROLS: {joint index: 4x4 delta in model space, cm} = W_posed @ inv(W_bind), joints that move
more than 0.01 mm / 0.01 deg only. Posed local transforms are the DNA neutral values plus the control's column of the
joint matrix (rigdec.py); joints outside the DNA keep their bind locals (67692 skeleton = the first 299 joints of
67711, same order, binds identical to the face meshes' inverse bind matrices).
"""
import argparse
import json
import sys

import numpy as np
from scipy.spatial.transform import Rotation as Rot

from rigdec import load

# raw controls in MetaHuman order, checked on the joint deltas (2026-10-30): 10 / 11 eyeBlinkL / R (upper lid A
# +32 deg, eyeball 2 deg), 32 / 33 eyeLookDownL / R (eyeball 40 deg, both lids down; v17f fitted the blink to these by
# mistake), 200 jawOpen (jaw 24 deg). Value: control index, or (index, amount played). The auto blink
# (BlinkSettingResource 74336:1: DS1TargetValue 0.7, DS1TargetRandomValue 0.3) peaks below 1: v17f closed a third and
# v18f half, and the rig predicts 0.64 / 0.97 of their shape at a full blink -> both give a blink of ~0.52 in game, so
# her lids are fitted at BLINK (a full 1.0 blink, eyes shut, then over-closes). look_* (32 / 33 down, 34 / 35 left,
# 36 / 37 right) and blink1_* (the full blink) only feed build_ds2's report.
BLINK = 0.55
CONTROLS = {'blink_L': (10, BLINK), 'blink_R': (11, BLINK), 'jaw': 200, 'look_L': 32, 'look_R': 33,
            'lookl_L': 34, 'lookl_R': 35, 'lookr_L': 36, 'lookr_R': 37, 'blink1_L': 10, 'blink1_R': 11}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out', help='face_motion.json')
    out_path = ap.parse_args().out
    g, rl, M, names, d2s, sk = load()
    nv = rl['joints']['neutral_values'].reshape(-1, 9)
    par = [j['ParentIndex'] for j in sk['Joints']]
    bind_local = []
    for b in sk['BindPose']:
        L = np.eye(4)
        q, t = b['Rotation'], b['Translation']
        L[:3, :3] = Rot.from_quat([q['X'], q['Y'], q['Z'], q['W']]).as_matrix()
        L[:3, 3] = [t['X'], t['Y'], t['Z']]
        bind_local.append(L)

    def world(delta):
        loc = [m.copy() for m in bind_local]
        for k, j in d2s.items():
            v = nv[k] + delta[k * 9:k * 9 + 9]
            L = np.eye(4)
            L[:3, :3] = Rot.from_euler('xyz', v[3:6]).as_matrix() * v[6:9]
            L[:3, 3] = v[:3]
            loc[j] = L
        W = []
        for j, L in enumerate(loc):
            W.append(L if par[j] < 0 else W[par[j]] @ L)
        return np.array(W)
    W0 = world(np.zeros(len(nv) * 9))
    out = {}
    for name, spec in CONTROLS.items():
        c, amount = spec if isinstance(spec, tuple) else (spec, 1.0)
        W1 = world(amount * M[:len(nv) * 9, c])
        moved = {}
        for j in range(len(W0)):
            D = W1[j] @ np.linalg.inv(W0[j])
            D[:3, 3] *= 100.0     # cm, model space
            ang = np.degrees(np.arccos(np.clip((np.trace(D[:3, :3]) - 1) / 2, -1, 1)))
            if np.abs(D[:3, 3] + D[:3, :3] @ (W0[j][:3, 3] * 100) - W0[j][:3, 3] * 100).max() > 1e-3 or ang > 1e-2:
                moved[j] = D.tolist()
        out[name] = moved
        top = sorted(moved, key=lambda j: -np.linalg.norm(np.array(moved[j])[:3, :3] @ (W0[j][:3, 3] * 100) + np.array(moved[j])[:3, 3] - W0[j][:3, 3] * 100))[:8]
        print(name, 'control', c, 'moves', len(moved), 'joints; largest:', ', '.join(
            f'{names[j]} {np.linalg.norm(np.array(moved[j])[:3, :3] @ (W0[j][:3, 3] * 100) + np.array(moved[j])[:3, 3] - W0[j][:3, 3] * 100):.2f}cm' for j in top))
    json.dump(out, open(out_path, 'w'))


if __name__ == '__main__':
    main()
