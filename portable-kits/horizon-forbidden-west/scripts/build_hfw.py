"""Build Karin_Original -> HFW Beta (group b2c4) replacement meshes and texture pages.

Stage outputs (in --work):
  fit.npz / fit.pkl   fitted primitives in HFW space (cm) with weights
  ascii/*.ascii       meshes ready for h2_pc_mi_091 (skeleton prepended)
  pages/*.png         texture pages
"""
import argparse
import json
import os
import pickle
import sys
import time

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hfwascii as H  # noqa: E402
import fit_hfw as F  # noqa: E402
from atlas import build_page  # noqa: E402
from vrm import Vrm  # noqa: E402

# ---------------------------------------------------------------- Beta (b2c4) layout
# body skin material pages: page B (1036 set: albedo 1036_2), face skin page A (b2c4 set 19: albedo 240)
BODY_UPPER = ('215', 1)      # mesh 215 sm1, skin material 66 (8 weights)
BODY_LOWER = ('260', 0)      # mesh 260 sm0, skin material 21C (4 weights)
FACE_SKIN = ['625', '109', '419', '206', '243', '380', '529', '50']   # face skin LOD0..7 (material uses b2c4 set 19)
LOD_FACE_FILES = {0: '625', 1: '109', 2: '419', 3: '206', 4: '243', 5: '380', 6: '529', 7: '50'}
# meshes skinned to the facial skeleton group 719 (from the h2 export log, LOD0..7)
FACE719 = {'625', '514', '160', '109', '644', '537', '419', '267', '240', '206', '193', '117', '82', '611',
           '243', '643', '165', '522', '380', '157', '529', '50'}
HEAD_BONES = ('head', 'leftEye', 'rightEye', 'jaw')
COVERED_BODY = ('body_2', 'knee-socks')
COVER_MARGIN = 1.0
LEG_BONES = tuple(f'{s}{b}' for s in ('left', 'right') for b in ('UpperLeg', 'LowerLeg', 'Foot', 'Toes'))
SKIRT_MAX_LEG = 0.45
LOWER_MESHES = ('skirt', 'tail', 'knee-socks', 'shoes')
UPPER_MESHES = ('pullover', 'hair', 'kemomimi')
# Karin meshes on the face skin page. Hair and ears sit on the body skin page: the face shader's subsurface
# scattering turned shadowed hair red-brown in game (v3)
FACE_PAGE_MESHES = {'Body'}
# skin normal map (1036_1) blue channel ~ gloss (vanilla skin median 64, nails brighter): per mesh / material
GLOSS = {'Karin_Body': 64, 'Karin_Costume': 40, 'Karin_Hair': 80, 'shoes': 72, 'Karin_Face': 64}


def keep_triangles(p, keep):
    used, inv = np.unique(p['tris'][keep], return_inverse=True)
    for k in ('pos', 'normal', 'uv', 'joints', 'weights'):
        if p.get(k) is not None:
            p[k] = p[k][used]
    p['tris'] = inv.reshape(-1, 3)


def hide_under_cover(prims, anc_cache):
    body, cover = COVERED_BODY
    socks = [p for p in prims if p['mesh'] == cover]
    top = min(p['pos'][:, 1].max() for p in socks) * 100.0 - COVER_MARGIN
    dropped = 0
    for p in prims:
        if p['mesh'] != body:
            continue
        dom = p['joints'][np.arange(len(p['pos'])), p['weights'].argmax(1)]
        leg = np.isin(np.vectorize(anc_cache.get, otypes=[object])(dom), LEG_BONES)
        hidden = leg & (p['pos'][:, 1] * 100.0 < top)
        keep = ~hidden[p['tris']].all(1)
        dropped += int((~keep).sum())
        keep_triangles(p, keep)
    return dropped


def _cone(n, deg, k):
    a = np.cross(n, [0.0, 1.0, 0.0])
    if np.linalg.norm(a) < 1e-3:
        a = np.cross(n, [1.0, 0.0, 0.0])
    a /= np.linalg.norm(a)
    b = np.cross(n, a)
    t = np.radians(deg)
    ph = np.linspace(0, 2 * np.pi, k + 1)[:-1]
    ring = np.cos(t) * n + np.sin(t) * (np.cos(ph)[:, None] * a + np.sin(ph)[:, None] * b)
    return np.concatenate([n[None], ring])


def enclosed(P, N, tri_xyz, dist, cone_deg=40.0, rays=6):
    """Per vertex: every ray of a cone around its normal hits one of the triangles within dist."""
    v0 = tri_xyz[:, 0]
    e1 = tri_xyz[:, 1] - v0
    e2 = tri_xyz[:, 2] - v0
    C = tri_xyz.mean(1)
    reach = dist + np.linalg.norm(tri_xyz - C[:, None], axis=2).max()
    tree = cKDTree(C)
    out = np.zeros(len(P), bool)
    for i, cand in enumerate(tree.query_ball_point(P, reach)):
        if not cand:
            continue
        c = np.asarray(cand)
        d = _cone(N[i], cone_deg, rays)[:, None, :]
        pv = np.cross(d, e2[c][None])
        det = (e1[c][None] * pv).sum(2)
        ok = np.abs(det) > 1e-12
        inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
        tv = P[i] - v0[c]
        u = (tv[None] * pv).sum(2) * inv
        qv = np.cross(tv, e1[c])
        w = (qv[None] * d).sum(2) * inv
        t = (e2[c] * qv).sum(1)[None] * inv
        hit = ok & (u >= 0) & (w >= 0) & (u + w <= 1) & (t > 1e-6) & (t < dist)
        out[i] = hit.any(1).all()
    return out


COVER_RULES = [   # (mesh, covering meshes, max distance cm in source scale)
    ('body_2', ('pullover', 'underwear', 'skirt', 'knee-socks', 'shoes'), 4.0),
    ('underwear', ('pullover', 'skirt'), 3.0),
]


def hide_covered(prims, rules):
    out = {}
    for mesh, covers, dist in rules:
        targets = [p for p in prims if p['mesh'] == mesh]
        cov = [p for p in prims if p['mesh'] in covers]
        X = np.concatenate([p['pos'][p['tris']] for p in cov])
        n = 0
        for p in targets:
            hidden = enclosed(p['pos'], p['normal'], X, dist / 100.0)
            keep = ~hidden[p['tris']].all(1)
            n += int((~keep).sum())
            keep_triangles(p, keep)
        out[mesh] = n
    return out


# ---------------------------------------------------------------- weights
REGION_ROOTS = {'hipsBone': 'torso', 'C_Spine_sjnt_0': 'torso', 'C_Neck_sjnt_0': 'neck', 'C_Head_sjnt_0': 'head',
                'L_Clavicle_sjnt_0': 'torso', 'R_Clavicle_sjnt_0': 'torso',
                'L_Arm_sjnt_0': 'L_upper', 'L_Arm_sjnt_1': 'L_fore', 'L_Wrist_sjnt_0': 'L_hand',
                'R_Arm_sjnt_0': 'R_upper', 'R_Arm_sjnt_1': 'R_fore', 'R_Wrist_sjnt_0': 'R_hand',
                'L_Leg_sjnt_0': 'L_thigh', 'L_Leg_sjnt_1': 'L_shin', 'L_Foot_sjnt_0': 'L_foot',
                'R_Leg_sjnt_0': 'R_thigh', 'R_Leg_sjnt_1': 'R_shin', 'R_Foot_sjnt_0': 'R_foot'}
HUMAN_REGION = {'hips': 'torso', 'spine': 'torso', 'chest': 'torso', 'upperChest': 'torso', 'neck': 'neck',
                'leftShoulder': 'torso', 'rightShoulder': 'torso',
                'leftUpperArm': 'L_upper', 'leftLowerArm': 'L_fore', 'leftHand': 'L_hand',
                'rightUpperArm': 'R_upper', 'rightLowerArm': 'R_fore', 'rightHand': 'R_hand',
                'leftUpperLeg': 'L_thigh', 'leftLowerLeg': 'L_shin', 'leftFoot': 'L_foot', 'leftToes': 'L_foot',
                'rightUpperLeg': 'R_thigh', 'rightLowerLeg': 'R_shin', 'rightFoot': 'R_foot', 'rightToes': 'R_foot'}


def is_pbd(name):
    return 'PBD' in name or 'Pbd' in name


def bone_region(names, parents, b):
    while b >= 0:
        n = names[b]
        if n in REGION_ROOTS:
            return REGION_ROOTS[n]
        if n.startswith('C_Spine') or n.startswith('C_Neck'):
            return 'torso' if n.startswith('C_Spine') else 'neck'
        b = parents[b]
    return None


class Donors:
    """Vanilla Beta LOD0 skin/cloth vertices (PBD weights removed) grouped by body region."""

    def __init__(self, meshes, names, parents, k=4):
        nb = len(names)
        pbd = np.array([is_pbd(n) for n in names])
        P, W = [], []
        for m in meshes:
            for pos, bi, bw in zip(m['pos'], m['bi'], m['bw']):
                w = np.zeros(nb)
                for b, x in zip(bi, bw):
                    if x == x and x > 0:
                        w[b] += x
                w[pbd] = 0
                s = w.sum()
                if s < 0.4:
                    continue
                P.append(pos * 100.0)
                W.append(w / s)
        P, W = np.array(P), np.array(W)
        reg = np.array([bone_region(names, parents, int(np.argmax(w))) for w in W], dtype=object)
        self.k = k
        self.pools = {}
        for r in set(reg) - {None}:
            sel = reg == r
            self.pools[r] = (cKDTree(P[sel]), W[sel])

    def query(self, region, X):
        tree, W = self.pools[region]
        d, i = tree.query(X, k=self.k)
        wd = 1.0 / np.maximum(d, 0.3) ** 2
        wd /= wd.sum(1, keepdims=True)
        return np.einsum('vk,vkb->vb', wd, W[i])


def map_weights(p, vrm_names, node_human, human_nodes, donors, idx, J, skirt_z, nb):
    """Per Karin influence: humanoid region -> nearest vanilla donors of that region (weights incl. roll and
    helper bones); fingers / head direct; skirt panels between the waist and the thighs; tail on the hips."""
    P = p['P']
    V = len(P)
    acc = np.zeros((V, nb))
    for k in range(4):
        jk = p['joints'][:, k]
        wk = p['weights'][:, k]
        for j in np.unique(jk[wk > 0]):
            sel = np.where((jk == j) & (wk > 0))[0]
            w = wk[sel]
            x = P[sel]
            name = vrm_names[j]
            h = p['hanc_of'][j]
            if name.startswith('Skirt'):
                zw, zh = skirt_z
                t = np.clip((zw - x[:, 2]) / max(zw - zh, 1e-3), 0, 1)
                a = SKIRT_MAX_LEG * t * t * (3 - 2 * t)
                s_left = 1 / (1 + np.exp(x[:, 0] / 4.0))     # HFW: model left is -x
                acc[sel] += (w * (1 - a))[:, None] * donors.query('torso', x)
                acc[sel] += (w * a * s_left)[:, None] * donors.query('L_thigh', x)
                acc[sel] += (w * a * (1 - s_left))[:, None] * donors.query('R_thigh', x)
            elif name.startswith('Tail') or (h == 'hips' and j != human_nodes['hips']):
                acc[sel, idx['hipsBone']] += w
            elif h in HEAD_BONES:
                acc[sel, idx['C_Head_sjnt_0']] += w
            elif h in F.HUMAN2GOT and h in F.HUMAN2NAME and h not in HUMAN_REGION:   # fingers
                acc[sel, F.HUMAN2GOT[h]] += w
            elif h in HUMAN_REGION:
                acc[sel] += w[:, None] * donors.query(HUMAN_REGION[h], x)
            else:
                raise ValueError(f'no Beta bone for joint {name} (humanoid {h})')
    return acc


def quantize(acc, nmax):
    top = np.argsort(-acc, axis=1)[:, :nmax]
    tw = np.take_along_axis(acc, top, 1)
    tw[tw < 0.5 / 255] = 0
    s = tw.sum(1, keepdims=True)
    if (s <= 0).any():
        raise ValueError('vertex without weights')
    return top.astype(np.int64), tw / s


def load_skel(path):
    sk = H.read_skeleton(path)
    names = [b['name'] for b in sk]
    parents = [b['parent'] for b in sk]
    pos = np.array([b['pos'] for b in sk]) * 100.0
    return sk, names, parents, pos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vrm', required=True)
    ap.add_argument('--export', required=True, help='h2 export folder with b2c4_skel_24.ascii, 719_skel_0.ascii, b2c4_*.ascii')
    ap.add_argument('--work', required=True)
    ap.add_argument('--scale', type=float, default=1.3)
    ap.add_argument('--head-scale', type=float, default=None)
    ap.add_argument('--neck-drop', type=float, default=0.0)
    ap.add_argument('--shoulder-fit', type=float, default=0.3)
    ap.add_argument('--arm-drop', type=float, default=2.0)
    ap.add_argument('--stage', default='fit')
    ap.add_argument('--src-max', type=int, default=2048, help='downsample source images above this size first')
    ap.add_argument('--z-split', type=float, default=90.0, help='cm: body triangles above go to mesh 215, below to 260')
    ap.add_argument('--lods', required=True, help='folder with lod1..lod7 h2 exports of b2c4')
    ap.add_argument('--hide', choices=('tri', 'collapse'), default='collapse',
                    help='hidden submeshes: one tiny triangle, or the vanilla topology collapsed to a point')
    ap.add_argument('--max-lod', type=int, default=7, help='write meshes of LOD 0..N only (higher LODs stay vanilla)')
    args = ap.parse_args()
    os.makedirs(args.work, exist_ok=True)
    t0 = time.time()
    report = vars(args).copy()

    sk, names, parents, J = load_skel(os.path.join(args.export, 'b2c4_skel_24.ascii'))
    F.set_skeleton(names)
    world = np.tile(np.eye(4), (len(names), 1, 1))
    world[:, :3, 3] = J

    vrm = Vrm(args.vrm)
    prims = [p for p in vrm.primitives() if p['mat_name'] != 'Karin_Alpha']
    for p in prims:
        keep_triangles(p, np.ones(len(p['tris']), bool))
    anc_cache = {j: F.humanoid_ancestor(vrm, j) or '' for j in range(len(vrm.nodes))}
    report['hidden_leg_tris'] = hide_under_cover(prims, anc_cache)
    report['hidden_covered_tris'] = hide_covered(prims, COVER_RULES)
    print('[cull]', report['hidden_leg_tris'], report['hidden_covered_tris'])

    tps, info = F.build_warp(vrm, world, scale=args.scale, head_scale=args.head_scale, neck_drop=args.neck_drop,
                             shoulder_fit=args.shoulder_fit, arm_drop=args.arm_drop, prims=prims)
    report['ring_r'] = {k: round(v, 2) for k, v in info['ring_r'].items()}
    hs, hn, A_head = info['maps']['head']
    kj, tgt = info['kj'], info['tgt']
    for p in prims:
        p['hanc'] = np.vectorize(anc_cache.get, otypes=[object])(p['joints'])
        P0 = F.gltf_to_got(p['pos'])
        N0 = np.stack([-p['normal'][:, 0], p['normal'][:, 2], p['normal'][:, 1]], 1)
        P = tps(P0)
        Jac = tps.jacobian(P0)
        f = sum(np.where(np.isin(p['hanc'][:, k], HEAD_BONES), p['weights'][:, k], 0) for k in range(4))
        P = f[:, None] * (hn + (P0 - hs) @ A_head.T) + (1 - f[:, None]) * P
        Jac = f[:, None, None] * A_head + (1 - f[:, None, None]) * Jac
        p['P'], p['P0'], p['N0'] = P, P0, N0
        N = np.einsum('vji,vj->vi', np.linalg.inv(Jac), N0)
        p['N'] = N / np.linalg.norm(N, axis=1, keepdims=True).clip(1e-12)

    # ground contact: lowest vanilla foot point (mesh 260 sm0 skin feet + sandals)
    _, low = H.read_meshes(os.path.join(args.export, 'b2c4_0.ascii'))
    floor = min(float(m['pos'][np.unique(m['faces']), 2].min()) for m in low) * 100.0
    report['floor_cm'] = floor
    for side in ('left', 'right'):
        leg_nodes = [f'{side}{b}' for b in ('UpperLeg', 'LowerLeg', 'Foot', 'Toes')]
        foot_nodes = [f'{side}Foot', f'{side}Toes']

        def frac(p, nn):
            return sum(np.where(np.isin(p['hanc'][:, k], nn), p['weights'][:, k], 0) for k in range(4))
        sole = min(p['P'][frac(p, foot_nodes) > 0.5, 2].min() for p in prims if (frac(p, foot_nodes) > 0.5).any())
        lift = floor - sole
        zk = J[F.HUMAN2GOT[f'{side}UpperLeg'], 2]
        za = J[F.HUMAN2GOT[f'{side}Foot'], 2]
        for p in prims:
            m = frac(p, leg_nodes)
            zb = p['P'][:, 2].copy()
            ramp = np.clip((zk - zb) / (zk - za), 0, 1)
            p['P'][:, 2] += lift * ramp * m
            dramp = np.where((zb > za) & (zb < zk), -1.0 / (zk - za), 0.0)
            s = 1 + lift * m * dramp
            N = p['N'].copy()
            N[:, 2] /= s
            p['N'] = N / np.linalg.norm(N, axis=1, keepdims=True).clip(1e-12)
        report[f'{side}_foot_lift_cm'] = float(lift)
    print(f'[fit] done {time.time() - t0:.0f}s lifts', report['left_foot_lift_cm'], report['right_foot_lift_cm'])

    # ---- weights (b2c4 skeleton indices)
    idx = {n: i for i, n in enumerate(names)}
    donor_meshes = []
    for f in ('b2c4_3.ascii', 'b2c4_0.ascii'):
        donor_meshes += H.read_meshes(os.path.join(args.export, f))[1]
    donors = Donors(donor_meshes, names, parents)
    skirt = [p['P'][:, 2] for p in prims if p['mesh'] == 'skirt']
    skirt_z = (max(z.max() for z in skirt), min(z.min() for z in skirt))
    report['skirt_z_cm'] = [float(z) for z in skirt_z]
    for p in prims:
        p['hanc_of'] = anc_cache
        p['acc'] = map_weights(p, vrm.names, vrm.node_human, vrm.human, donors, idx, J, skirt_z, len(names))
    print(f'[weights] done {time.time() - t0:.0f}s')

    # ---- pages
    def img(i, size=None):
        im = vrm.image(vrm.js['textures'][vrm.js['materials'][i]['pbrMetallicRoughness']['baseColorTexture']['index']]['source']).convert('RGBA')
        return im.resize((size, size), Image.LANCZOS) if size and im.size[0] > size else im
    mat_index = {m['name']: i for i, m in enumerate(vrm.js['materials'])}
    imgs = {}
    for name in ('Karin_Face', 'Karin_Body', 'Karin_Hair', 'Karin_Costume'):
        imgs[name] = img(mat_index[name], args.src_max)
    imgs['Karin_Hair_Transparent'] = imgs['Karin_Hair']

    def page_of(p):
        if p['mesh'] in FACE_PAGE_MESHES and p['mat_name'] != 'Karin_Costume':
            return 'A'
        return 'B'
    pages = {}
    for pg in ('A', 'B'):
        items = [p for p in prims if page_of(p) == pg]
        key = {'Karin_Hair_Transparent': 'Karin_Hair'}
        page, uvs, st = build_page([dict(img=imgs[p['mat_name']], uv=p['uv'], tris=p['tris'],
                                         key=key.get(p['mat_name'], p['mat_name'])) for p in items], (2048, 2048), mask_merge=True)
        for p, uv in zip(items, uvs):
            p['page'], p['puv'] = pg, uv
        page.convert('RGB').save(os.path.join(args.work, f'page_{pg}.png'))
        # gloss page (skin normal map B channel): per material, background = skin
        from PIL import ImageDraw
        gl = Image.new('L', (2048, 2048), GLOSS['Karin_Body'])
        dr = ImageDraw.Draw(gl)
        for p in items:
            g = GLOSS.get(p['mesh'], GLOSS.get(p['mat_name'], GLOSS['Karin_Body']))
            uv = p['puv'] * 2048
            for t in p['tris']:
                dr.polygon([(float(uv[k][0]), float(uv[k][1])) for k in t], fill=g, outline=g)
        gl.save(os.path.join(args.work, f'gloss_{pg}.png'))
        pages[pg] = st
        print(f'[page {pg}] scale {st["scale"]:.3f} pieces {st["pieces"]} fill {st["fill"]:.2f}')
    report['pages'] = pages

    # ---- assemble target meshes
    sk719 = H.read_skeleton(os.path.join(args.export, '719_skel_0.ascii'))
    names719 = [b['name'] for b in sk719]
    idx719 = {n: i for i, n in enumerate(names719)}
    to719 = np.zeros(len(names), int)
    for i in range(len(names)):
        b = i
        while names[b] not in idx719 and parents[b] >= 0:
            b = parents[b]
        to719[i] = idx719.get(names[b], idx719['C_Spine_sjnt_4'])

    def merge(items):
        P, N, UV, A, T, LO = [], [], [], [], [], []
        off = 0
        for p in items:
            P.append(p['P']); N.append(p['N']); UV.append(p['puv']); A.append(p['acc']); T.append(p['tris'] + off)
            # lower body (mesh 260, 4 weights): legs, hips, skirt, tail, socks, shoes; arms and hands stay upper
            dom = p['hanc'][np.arange(len(p['P'])), p['weights'].argmax(1)]
            lo = np.isin(dom, LEG_BONES + ('hips',)) | (p['mesh'] in LOWER_MESHES)
            if p['mesh'] in UPPER_MESHES:
                lo[:] = False
            LO.append(lo[p['tris']].sum(1) >= 2)
            off += len(p['P'])
        return dict(P=np.concatenate(P), N=np.concatenate(N), UV=np.concatenate(UV), A=np.concatenate(A),
                    T=np.concatenate(T), LO=np.concatenate(LO))

    def sub(m, tsel):
        used, inv = np.unique(m['T'][tsel], return_inverse=True)
        return dict(P=m['P'][used], N=m['N'][used], UV=m['UV'][used], A=m['A'][used], T=inv.reshape(-1, 3))
    faceM = merge([p for p in prims if p.get('page') == 'A'])
    A719 = np.zeros((len(faceM['A']), len(names719)))
    for i in range(len(names)):
        if faceM['A'][:, i].any():
            A719[:, to719[i]] += faceM['A'][:, i]
    faceM['A'] = A719
    bodyM = merge([p for p in prims if p.get('page') == 'B'])
    upper = sub(bodyM, ~bodyM['LO'])
    lower = sub(bodyM, bodyM['LO'])
    report['verts'] = dict(face=len(faceM['P']), upper=len(upper['P']), lower=len(lower['P']))
    print('[meshes]', report['verts'])
    out_dir = os.path.join(args.work, 'ascii')
    os.makedirs(out_dir, exist_ok=True)

    def to_sub(m, tmpl, root_bone):
        """Karin part m as a submesh shaped like vanilla template tmpl (uv count, colour, weight slots)."""
        nw = len(tmpl['bi'][0])
        bi, bw = quantize(m['A'], nw)
        nv = len(m['P'])
        col = np.tile(np.array(tmpl['col'][0]), (nv, 1))
        uv0 = np.stack([m['UV'][:, 0], 1.0 - m['UV'][:, 1]], 1)
        uvs = [uv0] + [np.zeros((nv, 2)) for _ in range(tmpl['nuv'] - 1)]
        BI = [[int(x) for x in r] for r in bi]
        BW = [[float(x) for x in r] for r in bw]
        for r_i, r_w in zip(BI, BW):   # pad unused slots with the last used bone at weight 0
            last = r_i[0]
            for k in range(nw):
                if r_w[k] > 0:
                    last = r_i[k]
                else:
                    r_i[k] = last
        # glTF triangles are counter-clockwise around the outward normal; the h2 ascii (and the game) wind clockwise
        return dict(name=tmpl['name'], nuv=tmpl['nuv'], textures=tmpl['textures'], pos=m['P'] / 100.0,
                    nrm=m['N'], col=col, uv=uvs, bi=BI, bw=BW, faces=m['T'][:, [0, 2, 1]])

    def hidden_sub(tmpl, at, bone):
        nw = len(tmpl['bi'][0])
        if args.hide == 'collapse':   # keep the vanilla vertex/index counts, collapse every vertex to one point
            nv = len(tmpl['pos'])
            return dict(name=tmpl['name'], nuv=tmpl['nuv'], textures=tmpl['textures'],
                        pos=np.tile(np.array(at) / 100.0, (nv, 1)), nrm=np.tile([0, 0, 1.0], (nv, 1)),
                        col=np.array(tmpl['col']), uv=[np.full((nv, 2), 0.5) for _ in range(tmpl['nuv'])],
                        bi=[[bone] * nw] * nv, bw=[[1.0] + [0.0] * (nw - 1)] * nv, faces=tmpl['faces'])
        P = np.array(at) / 100.0 + np.array([[0, 0, 0], [1e-4, 0, 0], [0, 0, 1e-4]])
        return dict(name=tmpl['name'], nuv=tmpl['nuv'], textures=tmpl['textures'], pos=P,
                    nrm=np.tile([0, 0, 1.0], (3, 1)), col=np.tile(np.array(tmpl['col'][0]), (3, 1)),
                    uv=[np.full((3, 2), 0.5) for _ in range(tmpl['nuv'])], bi=[[bone] * nw] * 3,
                    bw=[[1.0] + [0.0] * (nw - 1)] * 3, faces=np.array([[0, 1, 2]]))
    hips_at = J[idx['hipsBone']]
    head_at = J[idx['C_Head_sjnt_0']]
    lod_dirs = {0: args.export}
    for lod in range(1, 8):
        lod_dirs[lod] = os.path.join(args.lods, f'lod{lod}')
    skel_b2c4 = os.path.join(args.export, 'b2c4_skel_24.ascii')
    skel_719 = os.path.join(args.export, '719_skel_0.ascii')
    sk_b, _ = H.read_skeleton(skel_b2c4), None
    jobs = []
    for lod, d in lod_dirs.items():
        if lod > args.max_lod:
            continue
        tm = {}
        for f in sorted(os.listdir(d)):
            if f.startswith('b2c4_') and f.endswith('.ascii') and 'skel' not in f:
                for m in H.read_meshes(os.path.join(d, f))[1]:
                    tm.setdefault(m['name'].split('_')[1], []).append(m)
        for mid, subs in tm.items():
            is719 = mid in FACE719
            out = []
            for si, s in enumerate(subs):
                if mid == LOD_FACE_FILES.get(lod):
                    out.append(to_sub(faceM, s, None))
                elif lod == 0 and (mid, si) == BODY_UPPER:
                    out.append(to_sub(upper, s, None))
                elif lod == 0 and (mid, si) == BODY_LOWER:
                    out.append(to_sub(lower, s, None))
                elif lod == 0 or is719:
                    out.append(hidden_sub(s, head_at if is719 else hips_at,
                                          idx719['C_Head_sjnt_0'] if is719 else idx['hipsBone']))
                else:
                    out = None   # body LOD1+ stays vanilla
                    break
            if out is None:
                continue
            path = os.path.join(out_dir, f'lod{lod}_{mid}.ascii')
            H.write(path, out, bones=H.read_skeleton(skel_719 if is719 else skel_b2c4))
            jobs.append(dict(lod=lod, mesh=mid, file=os.path.basename(path), skel='719_skel_0.ascii' if is719 else 'b2c4_skel_24.ascii',
                             subs=[(s['name'], len(o['pos'])) for s, o in zip(subs, out)]))
    json.dump(jobs, open(os.path.join(args.work, 'jobs.json'), 'w'), indent=1)
    print('[ascii]', len(jobs), 'meshes')
    info_s = {k: info[k] for k in ('kj', 'tgt')}
    pickle.dump(dict(prims=prims, info=info_s, report=report, J=J, names=names, parents=parents,
                     human_nodes=dict(vrm.human), node_names=vrm.names, node_human=vrm.node_human),
                open(os.path.join(args.work, 'fit.pkl'), 'wb'))
    json.dump(report, open(os.path.join(args.work, 'fit_report.json'), 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
