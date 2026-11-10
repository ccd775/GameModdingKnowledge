"""Conform Karin_Original onto the Nioh 2 female player skeleton recovered from frame dumps (n2_skel.py) and give every
vertex game skin weights.

Base space: the source scaled uniformly by HEAD_SCALE (m -> cm and anime proportions), translated so Karin's Neck
joint sits on the game neck joint. Head and neck stay rigid; every other humanoid bone gets an affine fitted to the game
joints (segment direction + length, cross-section kept), blended with Karin's own weights (LBS). Method from the Nioh 3 /
Rise of the Ronin Karin builds (n3_conform.py / ko_conform.py), re-targeted to joints solved from Nioh 2 skin matrices.

Weights are written as tokens, resolved to palette entries by the builder:
  g<gid>        global body bone (bones.py gid of the fa3 dump)
  pony<k>       k-th joint of the vanilla long ponytail chain (hair draw), root = 0
  face<e>       entry e of the face draw's own palette (face mesh only, transferred from the vanilla face)
usage: n2_conform.py <source dir> <joints.json> <out dir>
"""
import json
import os
import sys

import numpy as np
from scipy.spatial import cKDTree

HEAD_SCALE = float(os.environ.get('N2_HEAD_SCALE', '150'))
SIDES = (('Left', 'L'), ('Right', 'R'))
FING = ('Thumb', 'Index', 'Middle', 'Ring', 'Little')
SEGS = ('Proximal', 'Intermediate', 'Distal')
# finger gids (L, R) per finger, proximal..distal
FINGER_G = {'Thumb': ((36, 40, 45), (56, 64, 64)), 'Index': ((37, 41, 46), (57, 60, 65)),
            'Middle': ((38, 42, 47), (58, 61, 66)), 'Ring': ((43, 48, 50), (62, 67, 69)),
            'Little': ((44, 49, 51), (63, 68, 70))}
G = {'pelvis': 0, 'spine': 1, 'chest': 2, 'neck': 3, 'head': 8,
     'clav': (4, 5), 'uparm': (6, 7), 'fore': ((54, 52, 53), (73, 71, 72)), 'hand': (35, 55),
     'thigh': ((11, 13, 9), (12, 19, 17)), 'calf': (10, 18), 'ankle': (31, 34), 'foot': (29, 32), 'toe': (30, 33),
     'skirtF': ((23, 24, 25), (26, 27, 28))}
SPINE_IDS, SPINE_YS = (0, 1, 2), (104.0, 122.0, 142.0)
FORE_T = (0.32, 0.65, 0.86)          # forearm twist bone positions along elbow -> wrist
THIGH_T = (0.15, 0.49, 0.68)         # thigh twist bone positions along hip -> knee
HEAD_MESHES = ('hair', 'kemomimi')
SKIRT_PUSH = 1.0


def to_game_axes(p):
    """Blender (Z up, facing -Y, +X = character's left) -> game (Y up, facing +Z, +X = character's left)."""
    p = np.asarray(p, float)
    return np.stack([p[..., 0], p[..., 2], -p[..., 1]], -1)


def min_rotation(u, v):
    u = u / np.linalg.norm(u); v = v / np.linalg.norm(v)
    c = float(np.dot(u, v)); w = np.cross(u, v); s = np.linalg.norm(w)
    if s < 1e-9:
        if c > 0:
            return np.eye(3)
        k = np.cross(u, [1.0, 0, 0] if abs(u[0]) < 0.9 else [0, 1.0, 0]); k /= np.linalg.norm(k)
        return 2 * np.outer(k, k) - np.eye(3)
    k = w / s
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + s * K + (1 - c) * K @ K


def aim_transform(h, a, h2, a2, cross=1.0):
    u = (a - h) / np.linalg.norm(a - h)
    alpha = np.linalg.norm(a2 - h2) / np.linalg.norm(a - h)
    S = cross * np.eye(3) + (alpha - cross) * np.outer(u, u)
    A = min_rotation(a - h, a2 - h2) @ S
    return A, h2 - A @ h


def fit_affine(pairs, A0, lam):
    P = np.array([p for p, _, _ in pairs]); Q = np.array([q for _, q, _ in pairs])
    w = np.array([w for _, _, w in pairs], float)
    pc = (w[:, None] * P).sum(0) / w.sum(); qc = (w[:, None] * Q).sum(0) / w.sum()
    X = P - pc; Y = Q - qc
    A = (Y.T @ (w[:, None] * X) + lam * A0) @ np.linalg.inv(X.T @ (w[:, None] * X) + lam * np.eye(3))
    return A, qc - A @ pc


def build_transforms(bones, Q, base):
    J = {b['name']: base(np.array(b['head'])) for b in bones}
    T = {'__head__': (np.eye(3), np.zeros(3))}
    neck = J['Neck']
    ground_src, ground_dst = base(np.zeros(3))[1], 0.0
    A, t = fit_affine([(J['LeftUpperLeg'], Q['hip_L'], 1), (J['RightUpperLeg'], Q['hip_R'], 1), (neck, neck, 1)], np.eye(3), 50.0)
    T['pelvis'] = (A, t)
    pel = lambda p: A @ p + t  # noqa: E731
    A2, t2 = fit_affine([(J['Chest'], pel(J['Chest']), 1), (neck, neck, 2),
                         (J['LeftUpperArm'], Q['shoulder_L'], 0.3), (J['RightUpperArm'], Q['shoulder_R'], 0.3)], A, 50.0)
    T['chest'] = (A2, t2)
    chest = lambda p: A2 @ p + t2  # noqa: E731
    for pre, s in SIDES:
        T[pre + 'Shoulder'] = aim_transform(J[pre + 'Shoulder'], J[pre + 'UpperArm'], chest(J[pre + 'Shoulder']), Q['shoulder_' + s])
        T[pre + 'UpperArm'] = aim_transform(J[pre + 'UpperArm'], J[pre + 'LowerArm'], Q['shoulder_' + s], Q['elbow_' + s])
        T[pre + 'LowerArm'] = aim_transform(J[pre + 'LowerArm'], J[pre + 'Hand'], Q['elbow_' + s], Q['wrist_' + s])
        A0, _ = aim_transform(J[pre + 'Hand'], J[pre + 'MiddleProximal'], Q['wrist_' + s], Q['middle1_' + s])
        T[pre + 'Hand'] = fit_affine([(J[pre + 'Hand'], Q['wrist_' + s], 3)] +
                                     [(J[f'{pre}{f}Proximal'], Q[f.lower() + '1_' + s], 1) for f in ('Index', 'Middle', 'Ring', 'Little')],
                                     A0, 20.0)
        for f in FING:
            names = [f'{pre}{f}{x}' for x in SEGS]
            g = [np.array(Q[f'{f.lower()}{i}_{s}'], float) for i in (1, 2, 3)]
            tip = J[f'{pre}{f}Distal_end']
            seg = np.linalg.norm(g[2] - g[1]) / max(np.linalg.norm(J[names[2]] - J[names[1]]), 1e-6)
            gtip = g[2] + (g[2] - g[1]) / max(np.linalg.norm(g[2] - g[1]), 1e-6) * np.linalg.norm(tip - J[names[2]]) * seg
            for n, gp, (a, ga) in zip(names, g, [(J[names[1]], g[1]), (J[names[2]], g[2]), (tip, gtip)]):
                T[n] = aim_transform(J[n], a, gp, ga)
        T[pre + 'UpperLeg'] = aim_transform(J[pre + 'UpperLeg'], J[pre + 'LowerLeg'], Q['hip_' + s], Q['knee_' + s])
        T[pre + 'LowerLeg'] = aim_transform(J[pre + 'LowerLeg'], J[pre + 'Foot'], Q['knee_' + s], Q['ankle_' + s])
        foot, toe = J[pre + 'Foot'], J[pre + 'ToeBase']
        heel_src = np.array([foot[0], ground_src, foot[2]]); toe_src = np.array([toe[0], ground_src, toe[2]])
        fwd = np.array(Q['toe_' + s]) - np.array(Q['ankle_' + s]); fwd[1] = 0; fwd /= np.linalg.norm(fwd)
        src_fwd = toe - foot; src_fwd[1] = 0
        R0 = min_rotation(src_fwd, fwd)
        heel_dst = np.array([Q['ankle_' + s][0], ground_dst, Q['ankle_' + s][2]])
        toe_dst = heel_dst + R0 @ (toe_src - heel_src)
        T[pre + 'Foot'] = fit_affine([(foot, Q['ankle_' + s], 1), (toe, Q['toe_' + s], 0.5), (heel_src, heel_dst, 1),
                                      (toe_src, toe_dst, 1)], R0, 30.0)
        T[pre + 'ToeBase'] = T[pre + 'Foot']
    for name in ('Hips', 'Spine'):
        T[name] = T['pelvis']
    T['Chest'] = T['chest']
    for name in ('Neck', 'Head', 'LeftEye', 'RightEye'):
        T[name] = T['__head__']
    report = {k: {'det': round(float(np.linalg.det(A)), 4), 'sv': np.round(np.linalg.svd(A)[1], 3).tolist()}
              for k, (A, _) in T.items() if not k.startswith('_')}
    return J, T, report


def tent(x, ids, xs):
    if x <= xs[0]:
        return {ids[0]: 1.0}
    if x >= xs[-1]:
        return {ids[-1]: 1.0}
    k = int(np.searchsorted(xs, x)) - 1
    f = (x - xs[k]) / (xs[k + 1] - xs[k])
    return {ids[k]: 1 - f, ids[k + 1]: f}


def seg_t(p, a, b):
    d = np.asarray(b) - np.asarray(a)
    return float(np.dot(p - a, d) / np.dot(d, d))


def bone_target(name, p, Q):
    """Karin bone name -> {token: weight} at conformed position p (None = keep resolving via parent)."""
    if name in ('Hips', 'Spine', 'Chest'):
        return {f'g{b}': w for b, w in tent(p[1], SPINE_IDS, SPINE_YS).items()}
    if name == 'Neck':
        return {'g3': 1.0}
    if name in ('Head', 'LeftEye', 'RightEye'):
        return {'g8': 1.0}
    for pre, s in SIDES:
        i = 0 if s == 'L' else 1
        if name == pre + 'Shoulder':
            return {f'g{G["clav"][i]}': 1.0}
        if name == pre + 'UpperArm':
            return {f'g{G["uparm"][i]}': 1.0}
        if name == pre + 'LowerArm':
            t = seg_t(p, Q['elbow_' + s], Q['wrist_' + s])
            return {f'g{b}': w for b, w in tent(t, G['fore'][i], FORE_T).items()}
        if name == pre + 'Hand':
            return {f'g{G["hand"][i]}': 1.0}
        for f in FING:
            for k, seg in enumerate(SEGS):
                if name == f'{pre}{f}{seg}':
                    return {f'g{FINGER_G[f][i][k]}': 1.0}
        if name == pre + 'UpperLeg':
            t = seg_t(p, Q['hip_' + s], Q['knee_' + s])
            return {f'g{b}': w for b, w in tent(t, G['thigh'][i], THIGH_T).items()}
        if name == pre + 'LowerLeg':
            return {f'g{G["calf"][i]}': 1.0}
        if name == pre + 'Foot':
            return {f'g{G["ankle"][i]}': 1.0} if p[1] > 8.0 else {f'g{G["foot"][i]}': 1.0}
        if name == pre + 'ToeBase':
            return {f'g{G["toe"][i]}': 1.0}
    return None


def main(src, jointsjson, outdir):
    meta = json.load(open(os.path.join(src, 'source.json'), encoding='utf-8'))
    arr = dict(np.load(os.path.join(src, 'source.npz')))
    Q = {k: np.array(v, float) for k, v in json.load(open(jointsjson))['joints'].items()}
    bones = meta['bones']
    parent = {b['name']: b['parent'] for b in bones}
    neck_src = to_game_axes(np.array(next(b for b in bones if b['name'] == 'Neck')['head']))
    t0 = Q['neck'] - HEAD_SCALE * neck_src
    base = lambda p: HEAD_SCALE * to_game_axes(p) + t0  # noqa: E731
    J, T, report = build_transforms(bones, Q, base)
    xf = {}
    for b in bones:
        cur = b['name']
        while cur is not None and cur not in T:
            cur = parent[cur]
        xf[b['name']] = T[cur] if cur is not None else T['__head__']
    out = {}
    summary = {'head_scale': HEAD_SCALE, 't0': t0.tolist(), 'transforms': report, 'meshes': {}}
    for m in meta['meshes']:
        k = m['key']; groups = m['groups']; name = m['name']
        co = base(arr[k + '__co']); nv = len(co)
        W = np.zeros((nv, len(groups)))
        W[arr[k + '__w_vertex'], arr[k + '__w_group']] = arr[k + '__w_weight']
        s = W.sum(1); assert (s > 0).all(), name
        W /= s[:, None]
        newp = np.zeros_like(co); Ab = np.zeros((nv, 3, 3))
        for gi, g in enumerate(groups):
            w = W[:, gi]
            if w.any():
                A, t = xf[g]
                newp += w[:, None] * (co @ A.T + t); Ab += w[:, None, None] * A
        lv = arr[k + '__loop_vertex']
        newn = np.einsum('nji,nj->ni', np.linalg.inv(Ab)[lv], to_game_axes(arr[k + '__loop_normal']))
        ln = np.linalg.norm(newn, axis=1)
        bad = ln < 1e-8
        if bad.any():
            tri = lv[arr[k + '__tris']]
            fn = np.cross(newp[tri[:, 1]] - newp[tri[:, 0]], newp[tri[:, 2]] - newp[tri[:, 0]])
            vn = np.zeros_like(newp)
            for c in range(3):
                np.add.at(vn, tri[:, c], fn)
            newn[bad] = vn[lv[bad]]
            ln = np.linalg.norm(newn, axis=1)
        newn /= np.maximum(ln, 1e-12)[:, None]
        # weights: walk each Karin bone up to the nearest mapped ancestor
        gw = [dict() for _ in range(nv)]
        for gi, g in enumerate(groups):
            vs = np.nonzero(W[:, gi])[0]
            if not len(vs):
                continue
            cur = g
            while cur is not None and bone_target(cur, newp[vs[0]], Q) is None:
                cur = parent[cur]
            for v in vs:
                tgt = bone_target(cur, newp[v], Q) if cur is not None else {'g8': 1.0}
                for tok, f in tgt.items():
                    gw[v][tok] = gw[v].get(tok, 0) + W[v, gi] * f
        if name in HEAD_MESHES:
            gw = [{'g8': 1.0} for _ in range(nv)]
        elif name == 'tail':
            gw = [{'g0': 1.0} for _ in range(nv)]
        out[k + '__pos'] = newp.astype(np.float32)
        out[k + '__loop_normal'] = newn.astype(np.float32)
        out[k + '__gw'] = np.array([json.dumps({b: round(float(w), 6) for b, w in d.items()}) for d in gw])
        summary['meshes'][name] = {'bbox_min': np.round(newp.min(0), 2).tolist(), 'bbox_max': np.round(newp.max(0), 2).tolist(),
                                   'groups': len(groups)}
    for key in arr:
        if key.endswith(('__loop_uv', '__loop_vertex', '__tris', '__tri_material')):
            out[key] = arr[key]
    summary['karin_joints_game'] = {n: np.round(p, 2).tolist() for n, p in J.items()}
    os.makedirs(outdir, exist_ok=True)
    np.savez_compressed(os.path.join(outdir, 'conformed.npz'), **out)
    json.dump(summary, open(os.path.join(outdir, 'conform.json'), 'w'), indent=1)
    for n, v in summary['meshes'].items():
        print(n, v)


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src', metavar='source_dir', help='source.json / source.npz'); ap.add_argument('jointsjson', metavar='joints.json')
    ap.add_argument('outdir', metavar='out_dir', help='conformed.npz, conform.json')
    a = ap.parse_args()
    main(a.src, a.jointsjson, a.outdir)
