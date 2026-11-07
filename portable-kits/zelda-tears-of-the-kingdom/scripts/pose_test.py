"""Linear-blend-skin TotkMdl export JSONs with a test pose (local rotations in degrees, applied in bone space).
usage: python pose_test.py <out_dir> <check_*.json ...>
Writes posed_<name>.json with the same layout (pos replaced) for blender_preview.py.
"""
import json, os, sys, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from retarget import quat_to_mat

def axis_angle(axis, deg):
    axis = np.asarray(axis, float); axis /= np.linalg.norm(axis); a = math.radians(deg)
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + math.sin(a) * K + (1 - math.cos(a)) * K @ K

# rotations about *world* axes at the bone pivot (simple and readable for tests)
POSE = {
    'Arm_1_L': ([0, 0, 1], -55),      # lower the left arm
    'Arm_2_L': ([0, 1, 0], 80),       # bend left elbow forward
    'Wrist_Assist_L': ([1, 0, 0], 30),
    'Wrist_L': ([1, 0, 0], 60),       # twist wrist
    'Arm_1_R': ([0, 0, 1], 55),
    'Arm_2_R': ([0, 1, 0], -80),
    'Leg_1_L': ([1, 0, 0], -60),      # lift left thigh
    'Leg_2_L': ([1, 0, 0], 90),       # bend left knee
    'Neck': ([1, 0, 0], 15), 'Head': ([0, 1, 0], 30),
    'Spine_2': ([0, 1, 0], 15),
    'Skirt_1_FL_Armor': ([1, 0, 0], -40), 'Skirt_1_FC_Armor': ([1, 0, 0], -40), 'Skirt_1_FR_Armor': ([1, 0, 0], -40),
    'Hair_Back_L_1': ([0, 0, 1], 35), 'Hair_Back_R_1': ([0, 0, 1], -35),
    'Skirt_1_BC_Armor': ([1, 0, 0], 40),
}
for f in 'BCDE':
    for j in (1, 2, 3): POSE[f'Finger_{f}_{j}_L'] = ([0, 0, 1], -50)

def world(model, pose):
    bones = model['bones']
    bind, posed = [None] * len(bones), [None] * len(bones)
    def local(b):
        L = np.eye(4); L[:3, :3] = quat_to_mat(b['quat']) * np.array(b['scale'])[None, :]; L[:3, 3] = b['pos']; return L
    def get(i):
        if bind[i] is not None: return
        b = bones[i]; L = local(b)
        if b['parent'] >= 0:
            get(b['parent']); bind[i] = bind[b['parent']] @ L; P = posed[b['parent']] @ L
        else:
            bind[i] = L; P = L.copy()
        if b['name'] in pose:
            axis, deg = pose[b['name']]
            R = np.eye(4); R[:3, :3] = axis_angle(axis, deg)
            piv = P[:3, 3].copy(); P = P.copy(); P[:3, 3] = 0; P = R @ P; P[:3, 3] = piv
        posed[i] = P
    for i in range(len(bones)): get(i)
    return {bones[i]['name']: (bind[i], posed[i]) for i in range(len(bones))}

def main(out_dir, paths):
    global POSE
    if paths and paths[0].endswith('.pose.json'):
        POSE = {k: tuple(v) for k, v in json.load(open(paths[0])).items()}; paths = paths[1:]
    os.makedirs(out_dir, exist_ok=True)
    for p in paths:
        d = json.load(open(p, encoding='utf-8'))
        for mdl in d['models']:
            W = world(mdl, POSE)
            skin = {n: posed @ np.linalg.inv(bind) for n, (bind, posed) in W.items()}
            for s in mdl['shapes']:
                P = np.c_[np.array(s['pos']), np.ones(len(s['pos']))]
                out = np.zeros((len(P), 3))
                for v, (names, ws) in enumerate(zip(s['boneNames'], s['boneWeights'])):
                    acc = np.zeros(3); tot = 0
                    for n, w in zip(names, ws):
                        if w <= 0 or n not in skin: continue
                        acc += w * (skin[n] @ P[v])[:3]; tot += w
                    out[v] = acc / tot if tot > 0 else P[v, :3]
                s['pos'] = out.tolist()
        json.dump(d, open(os.path.join(out_dir, 'posed_' + os.path.basename(p)), 'w'))
        print('posed', p)

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out_dir'); ap.add_argument('paths', nargs='+', help='[pose.json] check_*.json ...')
    a = ap.parse_args()
    main(a.out_dir, a.paths)
