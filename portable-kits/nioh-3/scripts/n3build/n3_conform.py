"""Conform Karin_Original onto the Nioh 3 player skeleton and give every vertex game skin weights (bone ids).

Base space: the source scaled uniformly by HEAD_SCALE, translated so Karin's Neck joint sits on game bone 11 (neck).
Head and neck stay rigid in base space; every other humanoid bone gets an affine fitted to the game bind joints
(segment direction + length, cross-section kept), blended with Karin's own weights (LBS). Method from the Rise of the
Ronin Karin_Original build (ko_conform.py), re-targeted to the Nioh 3 bone ids.

Weights:
- mapped: Karin's weights moved to the game bone each source bone maps to (torso split over the spine by height);
- transfer: skin-tight meshes take the vanilla female base body's weights (its twist/helper bones) from the nearest
  body vertices, ramped out with distance; hands keep the mapped finger weights; sleeves never use hand/finger bones;
- head, hair and ears ride the head bone, the tail the hips, the skirt blends hips -> nearest leg skin towards the hem.
Output: BUILD/conformed.npz + BUILD/conform.json
usage: n3_conform.py   (BUILD = N3_BUILD; N3_HEAD_SCALE, default 150)
"""
import argparse
import json
import os

import numpy as np
from scipy.spatial import cKDTree

from n3_common import BODY, BUILD, CHEST, load_model, load_source, skeleton, to_game_axes

HEAD_SCALE = float(os.environ.get('N3_HEAD_SCALE', '150'))
SIDES = (('Left', 0), ('Right', 1))
FINGERS = {'Thumb': (100, 108, 118), 'Index': (102, 110, 120), 'Middle': (104, 112, 122),
           'Ring': (114, 124, 128), 'Little': (116, 126, 130)}
SEGS = ('Proximal', 'Intermediate', 'Distal')
SPINE = (2, 9, 10)
HEAD_MESHES = ('Body', 'hair', 'kemomimi')
TRANSFER_MESHES = ('body_2', 'pullover', 'underwear', 'knee_socks', 'shoes')
TRANSFER_DIST = (2.0, 7.0)   # full body-weight transfer within the first distance (cm), none beyond the second
TRANSFER_K = 6
SKIRT_FMAX, SKIRT_PUSH = 0.75, 1.5


def humanoid_map():
    m = {'Head': 12, 'LeftEye': 12, 'RightEye': 12, 'Neck': 11, 'Hips': 'torso', 'Spine': 'torso', 'Chest': 'torso'}
    for pre, off in SIDES:
        m.update({pre + 'Shoulder': 13 + off, pre + 'UpperArm': 15 + off, pre + 'LowerArm': 17 + off,
                  pre + 'Hand': 19 + off, pre + 'UpperLeg': 3 + off, pre + 'LowerLeg': 5 + off,
                  pre + 'Foot': 7 + off, pre + 'ToeBase': 23 + off})
        for f, ids in FINGERS.items():
            for seg, g in zip(SEGS, ids):
                m[f'{pre}{f}{seg}'] = g + off
    return m


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
    """Rotate h->a onto h2->a2 with axial stretch; cross-section scaled by `cross`."""
    u = (a - h) / np.linalg.norm(a - h)
    alpha = np.linalg.norm(a2 - h2) / np.linalg.norm(a - h)
    S = cross * np.eye(3) + (alpha - cross) * np.outer(u, u)
    A = min_rotation(a - h, a2 - h2) @ S
    return A, h2 - A @ h


def fit_affine(pairs, A0, lam):
    """min sum w|A p + t - q|^2 + lam |A - A0|^2 (t unregularised)."""
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
    A, t = fit_affine([(J['LeftUpperLeg'], Q[3], 1), (J['RightUpperLeg'], Q[4], 1), (neck, neck, 1)], np.eye(3), 50.0)
    T['pelvis'] = (A, t)
    pel = lambda p: A @ p + t  # noqa: E731
    A2, t2 = fit_affine([(J['Chest'], pel(J['Chest']), 1), (neck, neck, 2),
                         (J['LeftUpperArm'], Q[15], 0.3), (J['RightUpperArm'], Q[16], 0.3)], A, 50.0)
    T['chest'] = (A2, t2)
    chest = lambda p: A2 @ p + t2  # noqa: E731
    for pre, off in SIDES:
        T[pre + 'Shoulder'] = aim_transform(J[pre + 'Shoulder'], J[pre + 'UpperArm'], chest(J[pre + 'Shoulder']), Q[15 + off])
        T[pre + 'UpperArm'] = aim_transform(J[pre + 'UpperArm'], J[pre + 'LowerArm'], Q[15 + off], Q[17 + off])
        T[pre + 'LowerArm'] = aim_transform(J[pre + 'LowerArm'], J[pre + 'Hand'], Q[17 + off], Q[19 + off])
        A0, _ = aim_transform(J[pre + 'Hand'], J[pre + 'MiddleProximal'], Q[19 + off], Q[104 + off])
        T[pre + 'Hand'] = fit_affine([(J[pre + 'Hand'], Q[19 + off], 3)] +
                                     [(J[f'{pre}{f}Proximal'], Q[FINGERS[f][0] + off], 1) for f in ('Index', 'Middle', 'Ring', 'Little')],
                                     A0, 20.0)
        for f, ids in FINGERS.items():
            names = [f'{pre}{f}{s}' for s in SEGS]
            g = [Q[i + off] for i in ids]
            tip = J[f'{pre}{f}Distal_end']
            gtip = g[2] + (g[2] - g[1]) / np.linalg.norm(g[2] - g[1]) * np.linalg.norm(tip - J[names[2]]) * \
                np.linalg.norm(g[2] - g[1]) / np.linalg.norm(J[names[2]] - J[names[1]])
            for n, gp, (a, ga) in zip(names, g, [(J[names[1]], g[1]), (J[names[2]], g[2]), (tip, gtip)]):
                T[n] = aim_transform(J[n], a, gp, ga)
        T[pre + 'UpperLeg'] = aim_transform(J[pre + 'UpperLeg'], J[pre + 'LowerLeg'], Q[3 + off], Q[5 + off])
        T[pre + 'LowerLeg'] = aim_transform(J[pre + 'LowerLeg'], J[pre + 'Foot'], Q[5 + off], Q[7 + off])
        foot, toe = J[pre + 'Foot'], J[pre + 'ToeBase']
        heel_src = np.array([foot[0], ground_src, foot[2]]); toe_src = np.array([toe[0], ground_src, toe[2]])
        fwd = Q[23 + off] - Q[7 + off]; fwd[1] = 0; fwd /= np.linalg.norm(fwd)
        src_fwd = toe - foot; src_fwd[1] = 0
        R0 = min_rotation(src_fwd, fwd)
        heel_dst = np.array([Q[7 + off][0], ground_dst, Q[7 + off][2]])
        toe_dst = heel_dst + R0 @ (toe_src - heel_src)
        T[pre + 'Foot'] = fit_affine([(foot, Q[7 + off], 1), (toe, Q[23 + off], 0.5), (heel_src, heel_dst, 1),
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


def resolve(bones, T, hmap):
    parent = {b['name']: b['parent'] for b in bones}
    xf, gmap = {}, {}
    for b in bones:
        n = b['name']; cur = n
        while cur is not None and cur not in T:
            cur = parent[cur]
        xf[n] = T[cur] if cur is not None else T['__head__']
        cur = n
        while cur is not None and cur not in hmap:
            cur = parent[cur]
        gmap[n] = hmap[cur] if cur is not None else 'torso'
    return xf, gmap


ARM_SIDE = {'L': {'root': 13, 'fore': 17}, 'R': {'root': 14, 'fore': 18}}


def side_of(sk, b):
    """'L' / 'R' if bone b hangs under that clavicle (13 left, 14 right), else None."""
    while b is not None:
        if b == 13:
            return 'L'
        if b == 14:
            return 'R'
        b = sk[b]['parent']
    return None


def cross_side(sk, pos, gws):
    """Vertices on one side (|x| > 12) carrying weight on the other arm's chain - must be none."""
    bad = 0
    for p, d in zip(pos, gws):
        if abs(p[0]) <= 12:
            continue
        side = 'L' if p[0] > 0 else 'R'          # +X is the character's left
        if any(side_of(sk, b) not in (None, side) for b, w in d.items() if w > 1e-4):
            bad += 1
    return bad


def tent(y, ids, ys):
    if y <= ys[0]:
        return {ids[0]: 1.0}
    if y >= ys[-1]:
        return {ids[-1]: 1.0}
    k = int(np.searchsorted(ys, y)) - 1
    f = (y - ys[k]) / (ys[k + 1] - ys[k])
    return {ids[k]: 1 - f, ids[k + 1]: f}


def body_reference():
    """Vanilla female base body in bind pose: positions and per-vertex {bone id: weight} (all LOD0 submeshes)."""
    data, m = load_model(BODY)
    sk = skeleton(m); st2id = {v['storage']: b for b, v in sk.items()}
    P, Wd = [], []
    for s in m.submeshes:
        a = m.attributes[s['vertex_buffer']]; vb = m.vertex_buffers[a['buffers'][0]]
        raw = np.frombuffer(data, np.uint8, vb['count'] * vb['stride'], vb['offset']).reshape(vb['count'], vb['stride'])
        get = lambda sem, layer=0: next((x for x in a['attrs'] if x['semantic'] == sem and x['layer'] == layer), None)  # noqa: E731
        pos = get('POSITION'); P.append(raw[:, pos['offset']:pos['offset'] + 12].copy().view('<f4').reshape(-1, 3))
        ws, ids = [], []
        for layer in (0, 1):
            w, i = get('BLENDWEIGHT', layer), get('BLENDINDICES', layer)
            if w is None:
                continue
            n = {0x0B: 4, 0x0A: 2}[w['type']]
            ws.append(raw[:, w['offset']:w['offset'] + 2 * n].copy().view('<f2').astype(float).reshape(-1, n))
            ids.append(raw[:, i['offset']:i['offset'] + 4].astype(int)[:, :n])
        W = np.concatenate(ws, 1); I = np.concatenate(ids, 1)
        if W.shape[1] < I.shape[1]:
            pass
        rest = 1 - W.sum(1)
        pal = m.palettes[s['palette']]
        for v in range(len(W)):
            d = {}
            for k in range(W.shape[1]):
                if W[v, k] > 0:
                    b = st2id[pal[I[v, k] // 3]['joint']]
                    d[b] = d.get(b, 0) + W[v, k]
            if rest[v] > 1e-3:      # implicit remainder goes to the last stored index
                b = st2id[pal[I[v, -1] // 3]['joint']]
                d[b] = d.get(b, 0) + rest[v]
            Wd.append(d)
    return np.concatenate(P), Wd


def main():
    meta, arr = load_source()
    bones = meta['bones']
    _, chest = load_model(CHEST)
    sk = skeleton(chest)
    Q = {b: v['pos'] for b, v in sk.items()}
    neck_src = to_game_axes(np.array(next(b for b in bones if b['name'] == 'Neck')['head']))
    t0 = Q[11] - HEAD_SCALE * neck_src
    base = lambda p: HEAD_SCALE * to_game_axes(p) + t0  # noqa: E731
    J, T, report = build_transforms(bones, Q, base)
    hmap = humanoid_map()
    xf, gmap = resolve(bones, T, hmap)
    spine_ys = [Q[i][1] for i in SPINE]
    body_P, body_W = body_reference()
    body_tree = cKDTree(body_P)
    hand_bones = {19, 20} | {g + o for ids in FINGERS.values() for g in ids for o in (0, 1)}
    out = {}
    summary = {'head_scale': HEAD_SCALE, 't0': t0.tolist(), 'transforms': report, 'meshes': {}}
    skin_ref = None
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
        bad = ln < 1e-8                      # the source has zero-length loop normals (body_2: 1568 loops)
        if bad.any():
            tri = lv[arr[k + '__tris']]
            fn = np.cross(newp[tri[:, 1]] - newp[tri[:, 0]], newp[tri[:, 2]] - newp[tri[:, 0]])
            vn = np.zeros_like(newp)
            for c in range(3):
                np.add.at(vn, tri[:, c], fn)
            newn[bad] = vn[lv[bad]]
            ln = np.linalg.norm(newn, axis=1)
            summary['meshes'].setdefault(name, {})['geometric_normals'] = int(bad.sum())
        newn /= np.maximum(ln, 1e-12)[:, None]
        # mapped weights
        gw = [dict() for _ in range(nv)]
        for gi, g in enumerate(groups):
            target = gmap[g]
            for v in np.nonzero(W[:, gi])[0]:
                parts = tent(newp[v, 1], SPINE, spine_ys) if target == 'torso' else {target: 1.0}
                for b, f in parts.items():
                    gw[v][b] = gw[v].get(b, 0) + W[v, gi] * f
        if name in HEAD_MESHES:
            gw = [{12: 1.0} for _ in range(nv)]
        elif name == 'tail':
            gw = [{2: 1.0} for _ in range(nv)]
        elif name in TRANSFER_MESHES:
            d, idx = body_tree.query(newp, k=TRANSFER_K)
            iw = 1 / (d + 0.3); iw /= iw.sum(1, keepdims=True)
            f = 1 - np.clip((d[:, 0] - TRANSFER_DIST[0]) / (TRANSFER_DIST[1] - TRANSFER_DIST[0]), 0, 1)
            moved = 0
            for v in range(nv):
                hand = sum(w for b, w in gw[v].items() if b in hand_bones)
                if name == 'body_2' and hand >= 0.3:
                    continue                       # fingers stay on Karin's own mapped finger weights
                if f[v] <= 0:
                    continue
                acc = {b: (1 - f[v]) * w for b, w in gw[v].items()}
                for j in range(TRANSFER_K):
                    for b, w in body_W[idx[v, j]].items():
                        acc[b] = acc.get(b, 0) + f[v] * iw[v, j] * w
                gw[v] = acc; moved += 1
            summary['meshes'].setdefault(name, {})['transferred'] = moved
            summary['meshes'][name]['body_dist_p50_p95'] = np.round(np.percentile(d[:, 0], [50, 95]), 2).tolist()
        if name == 'pullover':     # sleeves follow the forearm, never the hand (Ronin round-2 lesson)
            for dct in gw:          # side from the skeleton, not id parity (left fingers are EVEN ids under wrist 19)
                for b in [b for b in dct if b in hand_bones]:
                    dct[ARM_SIDE[side_of(sk, b)]['fore']] = dct.get(ARM_SIDE[side_of(sk, b)]['fore'], 0) + dct.pop(b)
        if name == 'body_2':
            skin_ref = (newp.copy(), gw)
        xs = cross_side(sk, newp, gw)
        summary['meshes'].setdefault(name, {})['cross_side_vertices'] = xs
        assert xs == 0, f'{name}: {xs} vertices weighted to the opposite arm'
        out[k + '__pos'] = newp.astype(np.float32)
        out[k + '__loop_normal'] = newn.astype(np.float32)
        out[k + '__gw'] = np.array([json.dumps({str(b): round(float(w), 6) for b, w in dct.items()}) for dct in gw])
        summary['meshes'].setdefault(name, {}).update({'bbox_min': np.round(newp.min(0), 2).tolist(),
                                                       'bbox_max': np.round(newp.max(0), 2).tolist()})
    # skirt: hips weights blend toward the nearest leg skin as the hem is approached, hem pushed outward
    sm = next(m for m in meta['meshes'] if m['name'] == 'skirt')
    sp = out[sm['key'] + '__pos'].astype(float); sgw = [{int(b): w for b, w in json.loads(x).items()} for x in out[sm['key'] + '__gw']]
    _, near = cKDTree(skin_ref[0]).query(sp, k=8)
    ytop, yhem = sp[:, 1].max(), sp[:, 1].min()
    tt = np.clip((ytop - sp[:, 1]) / (ytop - yhem), 0, 1)
    blended = []
    for v in range(len(sp)):
        f = SKIRT_FMAX * tt[v]
        acc = {b: (1 - f) * w for b, w in sgw[v].items()}
        for n in near[v]:
            for b, w in skin_ref[1][n].items():
                acc[b] = acc.get(b, 0) + f * w / len(near[v])
        blended.append(json.dumps({str(b): round(float(w), 6) for b, w in acc.items()}))
    out[sm['key'] + '__gw'] = np.array(blended)
    radial = sp - np.array([0.0, 0.0, sp[:, 2].mean()]); radial[:, 1] = 0
    radial /= np.linalg.norm(radial, axis=1, keepdims=True) + 1e-9
    out[sm['key'] + '__pos'] = (sp + SKIRT_PUSH * tt[:, None] * radial).astype(np.float32)
    for key in arr:
        if key.endswith(('__loop_uv', '__loop_vertex', '__tris', '__tri_material')):
            out[key] = arr[key]
    used = set()
    for key in out:
        if key.endswith('__gw'):
            for x in out[key]:
                used |= {int(b) for b in json.loads(x)}
    missing = sorted(b for b in used if b not in sk)
    assert not missing, f'bones not in the chest skeleton: {missing}'
    summary['bones_used'] = sorted(used)
    summary['karin_joints_game'] = {n: np.round(p, 2).tolist() for n, p in J.items() if n in hmap}
    np.savez_compressed(BUILD / 'conformed.npz', **out)
    (BUILD / 'conform.json').write_text(json.dumps(summary, indent=1), encoding='utf-8')
    for n, v in summary['meshes'].items():
        print(n, v)
    print('bones used', len(used))


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    main()
