"""Nioh 2 female player skeleton (bind space, cm; Y up, +Z forward, +X = character's left) recovered from a frame
analysis: global bone ids (gid, matrices matched across draws by bones.py) labelled by hand from their weighted centres,
joints solved from parent/child skinning matrices (the point both map to the same world position), regularised towards
the weight-blend boundary.
usage: n2_skel.py <bones.json> <out joints.json>"""
import json
import sys

import numpy as np

# gid labels for the fa3 dump (equipment screen, 2026-11-07). R side gids in the second element.
LABEL = {
    'pelvis': 0, 'spine': 1, 'chest': 2, 'neck': 3, 'head': 8,
    'clav': (4, 5), 'uparm': (6, 7), 'elbow_a': (96, 99), 'elbow_b': (97, 100), 'uparm_tw': (101, 102),
    'fore1': (54, 73), 'fore2': (52, 71), 'fore3': (53, 72), 'hand': (35, 55),
    'thumb': ((36, 40, 45), (56, 64, None)), 'index': ((37, 41, 46), (57, 60, 65)), 'middle': ((38, 42, 47), (58, 61, 66)),
    'ring': ((43, 48, 50), (62, 67, 69)), 'little': ((44, 49, 51), (63, 68, 70)), 'palm': (39, 59),
    'thigh1': (11, 12), 'thigh2': (13, 19), 'thigh3': (9, 17), 'calf': (10, 18), 'ankle': (31, 34), 'foot': (29, 32), 'toe': (30, 33),
    'hip_side': (15, 21), 'hip_back': (16, 22), 'skirt_front': ((23, 24, 25), (26, 27, 28)), 'knee_front': (14, 20),
    'scarf': ((74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84), (85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95)),
}

# (joint name, parent gid, child gid, seed point)
JOINTS_L = [
    ('neck', 2, 3, (0.0, 157.1, 0.7)), ('head', 3, 8, (0.0, 162.2, -3.0)),
    ('clav', 2, 4, (4.0, 150.0, 0.0)), ('shoulder', 4, 6, (15.2, 149.9, -3.8)),
    ('elbow', 6, 54, (31.5, 127.5, -3.2)), ('wrist', 53, 35, (53.0, 107.9, -3.2)),
    ('thumb1', 35, 36, (54.5, 104.5, 0.8)), ('thumb2', 36, 40, (53.9, 102.1, 2.4)), ('thumb3', 40, 45, (53.9, 100.1, 3.8)),
    ('index1', 35, 37, (60.0, 101.7, 0.1)), ('index2', 37, 41, (62.5, 99.7, 0.4)), ('index3', 41, 46, (64.5, 97.8, 0.8)),
    ('middle1', 35, 38, (60.7, 101.7, -1.8)), ('middle2', 38, 42, (63.0, 99.5, -2.4)), ('middle3', 42, 47, (65.1, 97.2, -2.4)),
    ('ring1', 39, 43, (60.0, 101.8, -4.7)), ('ring2', 43, 48, (62.4, 99.4, -4.8)), ('ring3', 48, 50, (64.4, 97.6, -5.1)),
    ('little1', 39, 44, (58.3, 101.9, -6.7)), ('little2', 44, 49, (60.4, 100.2, -7.3)), ('little3', 49, 51, (61.8, 98.8, -7.8)),
    ('hip', 0, 11, (9.5, 93.0, 1.0)), ('knee', 9, 10, (10.5, 53.0, 0.0)), ('ankle', 10, 31, (10.0, 11.0, -3.0)),
    ('foot', 31, 29, (9.3, 7.0, -2.0)), ('toe', 29, 30, (10.5, 2.1, 7.0)),
]
MIRROR = {4: 5, 6: 7, 54: 73, 53: 72, 52: 71, 35: 55, 36: 56, 40: 64, 45: None, 37: 57, 41: 60, 46: 65, 38: 58, 42: 61, 47: 66,
          39: 59, 43: 62, 48: 67, 50: 69, 44: 63, 49: 68, 51: 70, 11: 12, 9: 17, 10: 18, 31: 34, 29: 32, 30: 33, 2: 2, 3: 3, 0: 0, 8: 8}


def solve(M, p, c, seed, lam=0.05):
    if p not in M or c not in M:
        return np.array(seed, float), None
    A = M[p][:, :3] - M[c][:, :3]
    b = M[p][:, 3] - M[c][:, 3]
    j0 = np.array(seed, float)
    H = A.T @ A + lam * np.eye(3)
    j = np.linalg.solve(H, -A.T @ b + lam * j0)
    res = float(np.linalg.norm(A @ j + b))
    return j, res


def main(bonesjson, out):
    B = json.load(open(bonesjson))
    M = {g: np.array(m) for g, m in enumerate(B['mats'])}
    J = {}
    for name, p, c, seed in JOINTS_L:
        j, res = solve(M, p, c, seed)
        J[name + ('_L' if name not in ('neck', 'head') else '')] = {'pos': np.round(j, 2).tolist(), 'res': res, 'seed': seed}
        if name in ('neck', 'head'):
            continue
        pr, cr = MIRROR.get(p, p), MIRROR.get(c, c)
        seed_r = (-seed[0], seed[1], seed[2])
        if pr is None or cr is None:
            J[name + '_R'] = {'pos': list(seed_r), 'res': None, 'seed': seed_r}
            continue
        j, res = solve(M, pr, cr, seed_r)
        J[name + '_R'] = {'pos': np.round(j, 2).tolist(), 'res': res, 'seed': seed_r}
    for k, v in J.items():
        print(f"{k:10s} {v['pos']}  seed {list(v['seed'])}  res {v['res'] if v['res'] is None else round(v['res'], 3)}")
    json.dump({'joints': {k: v['pos'] for k, v in J.items()}, 'labels': LABEL}, open(out, 'w'), indent=1)


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('bonesjson', metavar='bones.json'); ap.add_argument('out', metavar='joints.json')
    a = ap.parse_args()
    main(a.bonesjson, a.out)
