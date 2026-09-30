"""Build a Karin replacement for Jin's Tadayori armour (hero_kamakura_armor) set.

Same delivery shape as "JP - Karin Ghost of Tsushima v1.0": one plain PSARC overriding
hero.xpps, the all-ranks armour mesh (Karin written into 8 LOD0 parts), the hidden Jin
meshes, and the 5 armour material texture sets.

    python build_karin.py --profile original|picodra --vrm MODEL.vrm [--game DIR] [--texconv texconv.exe]
                          [--work DIR] --out FILE

Profiles: original = Karin_Original (VRM 1.0), picodra = Karin_PicodraTech (VRM 0.x, PicodraTech outfit). Their
mesh names, cover rules and parameters are case-specific; a new model needs its own profile.
--game defaults to the GOT_GAME_DIR environment variable. Without --texconv every page is compressed with etcpak;
the project builds compressed the colour pages with DirectXTex texconv (pass it to reproduce them byte for byte).
"""
import argparse
import hashlib
import json
import os
import struct
import subprocess
import sys
import time

import etcpak
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from atlas import build_page  # noqa: E402
from decimate import decimate  # noqa: E402
from fit import HUMAN2GOT, build_warp, gltf_to_got, humanoid_ancestor, rot_between  # noqa: E402
from gotarc import Psarc, extract_to, write_psarc  # noqa: E402
from gotfmt import (FMT_BONE_U16, FMT_HALF, FMT_N10, FMT_POS_S16, FMT_U8X4, FMT_UV_H2,  # noqa: E402
                    Xmesh, Xpps, decode_record, encode_record, mip_sizes, skeleton_world, sps_header)

# <Steam library>\steamapps\common\Ghost of Tsushima DIRECTOR'S CUT
GAME_DEFAULT = os.environ.get('GOT_GAME_DIR')
ARCHIVES = ('gapack_misc_h', 'gapack_meshes', 'gapack_bitmaps_h_armor_0', 'gapack_misc_g')

ALL_RANKS = '/meshes/hero_kamakura_armor_all_ranks.xmesh'
# Jin meshes hidden by the v1.0 mod (body, head, hair, beard, masks, helmets, other armour pieces)
HIDE_MESHES = [
    'hero_body_feet', 'hero_body_fingers_1_l', 'hero_body_fingers_1_r', 'hero_body_fingers_2_l',
    'hero_body_fingers_2_r', 'hero_body_hands', 'hero_body_legs', 'hero_body_lowerbody',
    'hero_body_l_lower_arm', 'hero_body_l_upper_arm', 'hero_body_r_lower_arm', 'hero_body_r_upper_arm',
    'hero_body_shoulders', 'hero_body_torso', 'hero_hair_archer_rank2', 'hero_hair_archer_rank2_bun',
    'hero_hair_archer_rank3', 'hero_hair_beard', 'hero_hair_ronin', 'hero_hair_sakai_rank1',
    'hero_hair_tsurimanako_mask', 'hero_head', 'hero_kamakura_armor_helmet',
    'hero_kamakura_armor_jacket_rank1', 'hero_kamakura_armor_jacket_rank2', 'hero_kamakura_armor_mask',
    'hero_kamakura_armor_rank2_3', 'hero_kamakura_armor_rank2_hat', 'hero_kamakura_armor_rank3',
    'hero_kamakura_armor_shin_wrap_rank1_2', 'hero_kamakura_hair_rank3', 'hero_kamakura_helmet_crest_base',
    'hero_kamakura_helmet_crest_legend', 'hero_kamakura_helmet_crest_shared', 'hero_mask_half_big_mustache',
    'hero_shimura_rank2_hair_ponytail', 'hero_underwear', 'hero_underwear_belt',
]

# LOD0 parts of the all-ranks mesh that carry Karin (same 8 parts as v1.0) and their materials
ROLES = {
    'chest': ('hero_kamakura_armor_chest_mtl', [0x05f3d808d1d07571]),
    'details': ('hero_kamakura_armor_details_mtl', [0xbf32ddfb4b8f330d]),
    'pants': ('hero_kamakura_armor_pants_mtl', [0xa4ecaac5f4281b2e]),
    'shoulder': ('hero_kamakura_armor_shoulder_armor_mtl', [0xd39e21393bd07695]),
    'thigh': ('hero_kamakura_armor_thigh_armor_mtl',
              [0xffd1a194b32682da, 0xbf7cc70482fc9b95, 0x7a88d4218625e3a7, 0xbaecef61fcdefbe6]),
}
# vertex stream layout every written part must have
SLOT_FORMATS = [FMT_POS_S16, FMT_HALF, FMT_N10, FMT_N10, FMT_UV_H2, FMT_BONE_U16, FMT_U8X4]
# cloth-simulation switches of the five swinging parts used above (v1.0: 0x12a9 -> 0x12a8)
CLOTH_FLAG = (bytes.fromhex('1510a912'), bytes.fromhex('1510a812'), 5)

# material constants (0..255) per role: specular, gloss
MATERIAL = {'chest': (36, 64), 'details': (36, 64), 'pants': (40, 80), 'shoulder': (48, 110), 'thigh': (40, 80)}

# ---------------------------------------------------------------- weights
# z = measured peak height (cm) of each bone's weight profile on vanilla hero body/head, not the joint height
SPINE_NODES = [(3, 95.0), (4, 102.5), (5, 112.0), (7, 121.0), (10, 137.0)]
NECK_NODES = [(12, 152.8), (14, 158.5)]
LIMBS = {
    'leftUpperArm': (499, 505, [(500, 0.0), (501, 0.25), (502, 0.5), (503, 0.75)]),
    'leftLowerArm': (505, 513, [(505, 0.0), (508, 0.25), (509, 0.5), (510, 0.75)]),
    'rightUpperArm': (546, 553, [(547, 0.0), (548, 0.25), (549, 0.5), (550, 0.75)]),
    'rightLowerArm': (553, 561, [(553, 0.0), (556, 0.25), (557, 0.5), (558, 0.75)]),
    'leftLowerLeg': (596, 597, [(596, 0.1), (607, 0.35), (608, 0.62), (609, 0.88)]),
    'rightLowerLeg': (617, 618, [(617, 0.1), (628, 0.35), (629, 0.62), (630, 0.88)]),
}
# thigh: (main, child joint, twist0, twist1) with keyframes t -> {role: share}
THIGHS = {'leftUpperLeg': (595, 596, 612, 613), 'rightUpperLeg': (616, 617, 633, 634)}
THIGH_KEYS = [(0.10, (0.2, 0.6, 0.2)), (0.35, (0.55, 0.0, 0.45)), (0.60, (1.0, 0.0, 0.0))]
HEAD_BONES = ('head', 'leftEye', 'rightEye', 'jaw')
NBONES = 655
SKIRT_MAX_LEG = 0.45
# body mesh whose legs the socks cover; body triangles fully below the sock top minus the margin are dropped
COVERED_BODY = ('body_2', 'knee-socks')
COVER_MARGIN = 1.0    # cm, source scale (x1.45 in game)
LEG_BONES = tuple(f'{s}{b}' for s in ('left', 'right') for b in ('UpperLeg', 'LowerLeg', 'Foot', 'Toes'))
# a role split over several parts duplicates the vertices on each cut and may leave a part short of full
MULTI_SLOT_MARGIN = (0.95, 0.98)   # (vertices, triangles)
HAND_WORDS = ('Hand', 'Thumb', 'Index', 'Middle', 'Ring', 'Little')


# ---------------------------------------------------------------- per-model profiles
def role_original(p):
    mat = p['mat_name']
    if mat == 'Karin_Costume':
        return 'details' if p['mesh'] == 'underwear' else 'chest'
    return {'Karin_Face': 'pants', 'Karin_Body': 'thigh', 'Karin_Hair': 'shoulder',
            'Karin_Hair_Transparent': 'shoulder'}.get(mat)


# PicodraTech: every part has to share 8 slots (46.5k vertices) and 5 texture pages. Face, hair, hands and
# ornaments stay whole; the reductions land in the two big cloth slots (jacket/shoes/headphones, and
# top/shorts/socks/sleeve bands with the hands) and on the rest of the visible skin, which shares the small
# slot with the halo and the leg ring
PICODRA_ROLES = {
    'RETARGETED__Outer.baked': 'chest', 'RETARGETED__Shoes.baked': 'chest', 'RETARGETED__Head Acc.baked': 'chest',
    'RETARGETED__Inner.baked': 'thigh', 'RETARGETED__Pants.baked': 'thigh', 'RETARGETED__Socks.baked': 'thigh',
    'RETARGETED__Arm Cover.baked': 'thigh', 'Body_base.baked#hands': 'thigh',
    'Hair.baked': 'shoulder', 'hair.baked': 'shoulder', 'kemomimi.baked': 'shoulder', 'tail.baked': 'shoulder',
    'Body.baked': 'pants', 'Costume_Ornaments.baked': 'pants',
    'Body_base.baked': 'details', 'RETARGETED__Halo.baked': 'details', 'RETARGETED__Leg Ring.baked': 'details',
}


def role_picodra(p):
    if p['mesh'] == 'hair.baked' and p['mat_name'] == 'Karin_Costume':   # hair ribbons
        return 'pants'
    return PICODRA_ROLES.get(p['mesh'])


# (mesh, meshes that cover it, max distance cm): skin under the outfit, sock feet in the shoes, sleeve
# bands inside the jacket sleeves, scalp under the hair
PICODRA_COVER = [
    ('Body_base.baked', ('RETARGETED__Socks.baked', 'RETARGETED__Pants.baked', 'RETARGETED__Inner.baked',
                         'RETARGETED__Arm Cover.baked', 'RETARGETED__Shoes.baked', 'RETARGETED__Outer.baked',
                         'RETARGETED__Leg Ring.baked', 'Body.baked'), 7.0),
    ('RETARGETED__Socks.baked', ('RETARGETED__Shoes.baked',), 4.0),
    ('RETARGETED__Arm Cover.baked', ('RETARGETED__Outer.baked',), 7.0),
    ('Body.baked', ('hair.baked', 'Hair.baked', 'kemomimi.baked', 'RETARGETED__Head Acc.baked'), 3.0),   # scalp
]

PROFILES = {
    # vrm: always passed with --vrm (the project used Karin(Clone).vrm, VRM 1.0)
    'original': dict(vrm=None, role=role_original, cover='sock_top', pages='source',
                     skirt_bones=('Skirt',), skirt_mesh='skirt', ctrl_policy='all', ring_radii='culled',
                     decimatable=(), split_hands=None, skirt_front_only=False, own_feet=False,
                     shoulder_fit=0.0, arm_drop=5.0, foot_scale=None, arm_hang=None),
    # vrm: always passed with --vrm (the project used karin_picodra.vrm, VRM 0.x)
    'picodra': dict(vrm=None,
                    role=role_picodra, cover=PICODRA_COVER, pages='atlas',
                    # jacket hem panels hang from spine bones down to mid-thigh: treated like a skirt
                    skirt_bones=('OuterA', 'OuterB', 'OuterC', 'OuterD', 'Pocket String'), skirt_mesh=None,
                    skirt_front_only=True,
                    own_feet=True,   # shoes keep Karin's shape; only the toe joint bends the sole
                    # platform sneakers at the body's 1.45 looked oversized in game; the lower shin with its
                    # leg warmer and sock tops follows the shoe down to this size (fit step in main)
                    foot_scale=1.3,
                    ctrl_policy='skinned', ring_radii='uncut', split_hands='Body_base.baked',
                    # bare shoulders: fitted in the T pose her arm root rose past the shoulder whenever the arm
                    # hung (shrug at 0 / 5, spikes at 0.5 / 8 in game). The shoulders keep her own shape and
                    # the arms are fitted for hanging 75 degrees down (see hang_pose)
                    shoulder_fit=0.0, arm_drop=0.0, arm_hang=75.0,
                    decimatable=('Body_base.baked', 'RETARGETED__Outer.baked', 'RETARGETED__Shoes.baked',
                                 'RETARGETED__Inner.baked', 'RETARGETED__Pants.baked', 'RETARGETED__Socks.baked')),
}


def hat(x, nodes):
    """Partition of unity over sorted 1-D nodes: returns (V, len(nodes))."""
    pos = np.array([p for _, p in nodes])
    out = np.zeros((len(x), len(nodes)))
    xc = np.clip(x, pos[0], pos[-1])
    i = np.clip(np.searchsorted(pos, xc, side='right') - 1, 0, len(pos) - 2)
    t = (xc - pos[i]) / (pos[i + 1] - pos[i])
    out[np.arange(len(x)), i] = 1 - t
    out[np.arange(len(x)), i + 1] += t
    return out


def hide_under_cover(prims, anc_cache):
    """Drop body leg triangles that the over-knee socks cover (the model's kisekae_* shape keys mark the
    same region): skinned separately, the skin pokes through the socks at bent knees."""
    body, cover = COVERED_BODY
    socks = [p for p in prims if p['mesh'] == cover]
    if not socks or not any(p['mesh'] == body for p in prims):
        raise ValueError(f'covered-body meshes {COVERED_BODY} not found in the VRM')
    top = min(p['pos'][:, 1].max() for p in socks) * 100.0 - COVER_MARGIN   # glTF y up, m -> cm
    dropped = 0
    for p in prims:
        if p['mesh'] != body:
            continue
        dom = p['joints'][np.arange(len(p['pos'])), p['weights'].argmax(1)]
        leg = np.isin(np.vectorize(anc_cache.get, otypes=[object])(dom), LEG_BONES)
        hidden = leg & (p['pos'][:, 1] * 100.0 < top)
        keep = ~hidden[p['tris']].all(1)
        dropped += int((~keep).sum())
        used, inv = np.unique(p['tris'][keep], return_inverse=True)
        for k in ('pos', 'normal', 'uv', 'joints', 'weights'):
            if p.get(k) is not None:
                p[k] = p[k][used]
        p['tris'] = inv.reshape(-1, 3)
    if not dropped:
        raise ValueError('no body triangles under the socks: check COVERED_BODY / COVER_MARGIN')
    return dropped


def keep_triangles(p, keep):
    """Keep the given triangles of a primitive and drop the vertices no triangle uses any more."""
    used, inv = np.unique(p['tris'][keep], return_inverse=True)
    for k in ('pos', 'normal', 'uv', 'joints', 'weights'):
        if p.get(k) is not None:
            p[k] = p[k][used]
    p['tris'] = inv.reshape(-1, 3)


def split_hands(prims, mesh, anc_cache):
    """Move the triangles of `mesh` that touch a hand or finger vertex into their own primitive
    (mesh name + '#hands'), so the hands can sit in a slot with room to spare."""
    out = []
    for p in prims:
        out.append(p)
        if p['mesh'] != mesh:
            continue
        dom = p['joints'][np.arange(len(p['pos'])), p['weights'].argmax(1)]
        anc = np.vectorize(anc_cache.get, otypes=[object])(dom)
        hand = np.array([any(k in a for k in HAND_WORDS) for a in anc])
        th = hand[p['tris']].any(1)
        if th.any():
            h = dict(p, mesh=mesh + '#hands')
            keep_triangles(h, th)
            keep_triangles(p, ~th)
            out.append(h)
    prims[:] = out


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
        d = _cone(N[i], cone_deg, rays)[:, None, :]          # (k,1,3)
        pv = np.cross(d, e2[c][None])                          # (k,m,3)
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


def hide_covered(prims, rules):
    """Drop triangles whose three vertices are enclosed by covering meshes (rules: mesh, cover meshes, max
    distance cm). Skinned separately, covered skin and inner layers poke through at bent joints."""
    out = {}
    for mesh, covers, dist in rules:
        targets = [p for p in prims if p['mesh'] == mesh]
        cov = [p for p in prims if p['mesh'] in covers]
        missing = set(covers) - {p['mesh'] for p in cov}
        if not targets or missing:
            raise ValueError(f'cover rule {mesh}: meshes not found in the VRM ({missing or mesh})')
        X = np.concatenate([p['pos'][p['tris']] for p in cov])
        n = 0
        for p in targets:
            hidden = enclosed(p['pos'], p['normal'], X, dist / 100.0)   # glTF metres
            keep = ~hidden[p['tris']].all(1)
            n += int((~keep).sum())
            keep_triangles(p, keep)
        out[mesh] = n
    return out


def fit_capacity(prims, caps, decimatable):
    """Reduce the decimatable meshes of any role whose vertex/triangle total exceeds its slots.
    caps: role -> (max vertices, max triangles). Returns {role: (verts before, after, tris before, after)}."""
    out = {}
    for role, (cv, ct) in caps.items():
        ps = [p for p in prims if p['role'] == role]
        nv0 = sum(len(p['pos']) for p in ps)
        nt0 = sum(len(p['tris']) for p in ps)
        for attempt in range(9):
            nv = sum(len(p['pos']) for p in ps)
            nt = sum(len(p['tris']) for p in ps)
            if nv <= cv and nt <= ct:
                break
            if attempt == 8:
                raise ValueError(f'role {role}: cannot reduce to {cv} verts / {ct} tris')
            dec = [p for p in ps if p['mesh'] in decimatable]
            if not dec:
                raise ValueError(f'role {role}: {nv} verts / {nt} tris over {cv} / {ct}, nothing to reduce')
            # one reduction over all of the role's reducible meshes, cheapest collapses first wherever they
            # are (flat cloth before fingers); a collapse removes one vertex and, inside a surface, two triangles
            need = max(nv - cv, (nt - ct + 1) // 2) + 1
            merged = {k: np.concatenate([q[k] for q in dec]) for k in ('pos', 'normal', 'uv', 'joints', 'weights')}
            base = np.cumsum([0] + [len(q['pos']) for q in dec])
            merged['tris'] = np.concatenate([q['tris'] + b for q, b in zip(dec, base)])
            merged['owner'] = np.repeat(np.arange(len(dec)), np.diff(base))
            new, st = decimate(merged, len(merged['pos']) - need)
            if not st['collapsed']:
                raise ValueError(f'role {role}: {nv} verts / {nt} tris over {cv} / {ct}, nothing left to reduce')
            for i, q in enumerate(dec):
                sel = (new['owner'][new['tris']] == i).all(1)
                used, inv = np.unique(new['tris'][sel], return_inverse=True)
                for k in ('pos', 'normal', 'uv', 'joints', 'weights'):
                    q[k] = new[k][used]
                q['tris'] = inv.reshape(-1, 3)
        if (nv, nt) != (nv0, nt0):
            out[role] = (nv0, nv, nt0, nt)
    return out


def role_texture_names(xp, texnames, role):
    mtl, hashes = ROLES[role]
    names = sorted({texnames.get(t, '') for t in xp.mesh(hashes[0]).textures} - {''})
    return [n for n in names if n.startswith(mtl + '.msac.')]


def subtree(parents, root):
    out, grew = {root}, True
    while grew:
        grew = False
        for i, par in enumerate(parents):
            if par in out and i not in out:
                out.add(i)
                grew = True
    return out


def hang_pose(info, J, parents, deg, scale):
    """Upper-arm maps for a fit that is exact with the arms hanging deg below the T pose.

    The hero arm turns about its pivot, about 8 cm outside her shoulder joint. Fitted in the T pose, the part
    of her arm inside the pivot swings up past the shoulder as the arm drops (the shrug, then the spikes of
    skin, sleeve band and jacket seen in game). Here each upper arm is placed so that, turned deg down about
    the pivot, its root lands on the shoulder joint the torso was fitted to (her own with shoulder_fit and
    arm_drop 0) and its elbow on the hero elbow. Returns ({upper arm: map}, hero skinning matrices of that
    pose, the bones it moves)."""
    kj, tgt = info['kj'], info['tgt']
    c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
    S = np.tile(np.eye(4), (NBONES, 1, 1))
    maps, moving = {}, set()
    for h, sgn in (('leftUpperArm', 1), ('rightUpperArm', -1)):
        piv = J[LIMBS[h][0]]
        R = np.array([[1, 0, 0], [0, c, sgn * s], [0, -sgn * s, c]])   # arm tip (+-y) turns down (-z)
        root = piv + R.T @ (tgt[h] - piv)
        la = h.replace('Upper', 'Lower')
        a_s, a_n = kj[la] - kj[h], tgt[la] - root
        k = np.linalg.norm(a_n) / (np.linalg.norm(a_s) * scale)
        an = a_n / np.linalg.norm(a_n)
        maps[h] = (kj[h], root, (np.eye(3) + (k - 1) * np.outer(an, an)) @ rot_between(a_s, a_n) * scale)
        sub = sorted(subtree(parents, LIMBS[h][0]))
        assert {b for b, _ in LIMBS[h][2]} <= set(sub), f'{h}: weight nodes outside the arm subtree'
        moving.update(sub)
        S[sub, :3, :3] = R
        S[sub, :3, 3] = piv - R @ piv
    return maps, S, moving


def rest_from_hang(P, N, bones, weights, S, moving, arm):
    """Bind positions and normals that the hero skinning, in the hang pose S, carries onto the fitted shape:
    torso and forearm parts onto P / N, upper-arm parts onto their hanging-arm map (arm: {hero bone: (P, N)}).
    Only vertices weighted to a bone the pose moves change."""
    m = (np.isin(bones, sorted(moving)) & (weights > 0)).any(1)
    b, w = bones[m], weights[m]
    L = np.zeros((len(b), 3, 3))
    t = np.zeros((len(b), 3))
    D = np.zeros((len(b), 3))
    Dn = np.zeros((len(b), 3))
    for k in range(4):
        X, Xn = P[m].copy(), N[m].copy()
        for jb, (Pa, Na) in arm.items():
            sel = b[:, k] == jb
            X[sel], Xn[sel] = Pa[m][sel], Na[m][sel]
        R, tk = S[b[:, k], :3, :3], S[b[:, k], :3, 3]
        wk = w[:, k]
        L += wk[:, None, None] * R
        t += wk[:, None] * tk
        D += wk[:, None] * (np.einsum('vij,vj->vi', R, X) + tk)
        Dn += wk[:, None] * np.einsum('vij,vj->vi', R, Xn)
    P, N = P.copy(), N.copy()
    P[m] = np.linalg.solve(L, (D - t)[..., None])[..., 0]
    n = np.linalg.solve(L, Dn[..., None])[..., 0]
    N[m] = n / np.linalg.norm(n, axis=1, keepdims=True).clip(1e-12)
    return P, N, int(m.sum())


def seg_t(P, a, b):
    d = b - a
    return ((P - a) @ d) / (d @ d)


def map_weights(vrm, prim, P, J, skirt_z, skirt_bones=('Skirt',), skirt_front=None, arm_pos=None):
    V = len(P)
    acc = np.zeros((V, NBONES), np.float64)
    names = vrm.names
    for k in range(4):
        jk = prim['joints'][:, k]
        wk = prim['weights'][:, k]
        for j in np.unique(jk[wk > 0]):
            sel = np.where((jk == j) & (wk > 0))[0]
            w = wk[sel]
            p = P[sel]
            name = names[j]
            h = vrm.node_human.get(j) or humanoid_ancestor(vrm, j)
            if name.startswith(skirt_bones):
                zw, zh = skirt_z
                t = np.clip((zw - p[:, 2]) / max(zw - zh, 1e-3), 0, 1)
                a = SKIRT_MAX_LEG * t * t * (3 - 2 * t)
                if skirt_front is not None:   # open garment: only panels in front of the hips meet the thighs
                    x0, width = skirt_front
                    a = a / (1 + np.exp(-(p[:, 0] - x0) / width))
                s_left = 1 / (1 + np.exp(-p[:, 1] / 4.0))
                hw = hat(p[:, 2], SPINE_NODES)   # waistband follows the body at its height
                for c, (b, _) in enumerate(SPINE_NODES):
                    acc[sel, b] += w * (1 - a) * hw[:, c]
                acc[sel, 595] += w * a * s_left
                acc[sel, 616] += w * a * (1 - s_left)
            elif name.startswith('Tail') or (h == 'hips' and j != vrm.human['hips']):
                acc[sel, 3] += w
            elif h in ('hips', 'spine', 'chest', 'upperChest'):
                hw = hat(p[:, 2], SPINE_NODES)
                for c, (b, _) in enumerate(SPINE_NODES):
                    acc[sel, b] += w * hw[:, c]
            elif h == 'neck':
                hw = hat(p[:, 2], NECK_NODES)
                for c, (b, _) in enumerate(NECK_NODES):
                    acc[sel, b] += w * hw[:, c]
            elif h in HEAD_BONES:
                acc[sel, 17] += w
            elif h in LIMBS:
                a_, b_, nodes = LIMBS[h]
                q = arm_pos[h][sel] if arm_pos and h in arm_pos else p   # upper arm fitted for the hang pose
                hw = hat(seg_t(q, J[a_], J[b_]), nodes)
                for c, (b, _) in enumerate(nodes):
                    acc[sel, b] += w * hw[:, c]
            elif h in THIGHS:
                main, child, tw0, tw1 = THIGHS[h]
                t = np.clip(seg_t(p, J[main], J[child]), THIGH_KEYS[0][0], THIGH_KEYS[-1][0])
                shares = np.stack([np.interp(t, [kk[0] for kk in THIGH_KEYS], [kk[1][c] for kk in THIGH_KEYS])
                                   for c in range(3)], 1)
                shares /= shares.sum(1, keepdims=True)
                acc[sel, main] += w * shares[:, 0]
                acc[sel, tw0] += w * shares[:, 1]
                acc[sel, tw1] += w * shares[:, 2]
            elif h in HUMAN2GOT:
                acc[sel, HUMAN2GOT[h]] += w
            else:
                raise ValueError(f'no GoT bone for joint {name} (humanoid {h})')
    top = np.argsort(-acc, axis=1)[:, :4]
    tw = np.take_along_axis(acc, top, 1)
    tw[tw < 0.5 / 255] = 0
    s = tw.sum(1, keepdims=True)
    if (s <= 0).any():
        raise ValueError('vertex without weights')
    tw /= s
    return top.astype(np.int64), tw


# ---------------------------------------------------------------- geometry helpers
def tangents(P, N, UV, T):
    e1 = P[T[:, 1]] - P[T[:, 0]]
    e2 = P[T[:, 2]] - P[T[:, 0]]
    d1 = UV[T[:, 1]] - UV[T[:, 0]]
    d2 = UV[T[:, 2]] - UV[T[:, 0]]
    r = d1[:, 0] * d2[:, 1] - d2[:, 0] * d1[:, 1]
    ok = (np.abs(r) >= 1e-12)[:, None]
    r = np.where(ok[:, 0], r, 1.0)
    tan = np.where(ok, (e1 * d2[:, 1:2] - e2 * d1[:, 1:2]) / r[:, None], 0.0)
    bit = np.where(ok, (e2 * d1[:, 0:1] - e1 * d2[:, 0:1]) / r[:, None], 0.0)
    ta = np.zeros_like(P)
    ba = np.zeros_like(P)
    for c in range(3):
        np.add.at(ta, T[:, c], tan)
        np.add.at(ba, T[:, c], bit)
    t = ta - N * (N * ta).sum(1, keepdims=True)
    ln = np.linalg.norm(t, axis=1)
    bad = ln < 1e-8
    if bad.any():
        alt = np.cross(N[bad], [0, 0, 1.0])
        alt[np.linalg.norm(alt, axis=1) < 1e-6] = [1, 0, 0]
        t[bad] = alt
        ln = np.linalg.norm(t, axis=1)
    t /= ln[:, None]
    sign = np.where((np.cross(N, t) * ba).sum(1) < 0, -1.0, 1.0)
    return t, sign


def split_to_capacity(mesh, caps, key):
    """Split a mesh into len(caps) chunks by triangle order `key`; caps = [(maxV, maxT)]."""
    order = np.argsort(key)
    chunks = []
    ci = 0
    cur = []
    used = set()
    for ti in order:
        vs = set(mesh['tris'][ti].tolist())
        new = len(vs - used)
        if len(cur) + 1 > caps[ci][1] or len(used) + new > caps[ci][0]:
            chunks.append(cur)
            ci += 1
            if ci >= len(caps):
                raise ValueError('mesh does not fit the slot capacities')
            cur, used = [], set()
        cur.append(ti)
        used |= vs
    chunks.append(cur)
    return [submesh(mesh, np.array(c)) for c in chunks]


def submesh(mesh, tri_ids):
    tris = mesh['tris'][tri_ids]
    used, inv = np.unique(tris, return_inverse=True)
    out = {k: v[used] for k, v in mesh.items() if k != 'tris'}
    out['tris'] = inv.reshape(-1, 3)
    return out


def concat(meshes):
    out = {}
    base = 0
    tris = []
    for m in meshes:
        tris.append(m['tris'] + base)
        base += len(m['pos'])
    for k in meshes[0]:
        if k != 'tris':
            out[k] = np.concatenate([m[k] for m in meshes])
    out['tris'] = np.concatenate(tris)
    return out


# ---------------------------------------------------------------- textures
def _mip_chain(img, w, h, mips):
    levels = []
    for i in range(mips):
        mw, mh = max(1, w >> i), max(1, h >> i)
        lv = img.resize((mw, mh), Image.LANCZOS) if img.size != (mw, mh) else img
        levels.append(np.asarray(lv.convert('RGBA'), np.uint8))
    return levels


def _encode(kind, rgba):
    h, w = rgba.shape[:2]
    if w < 4 or h < 4:
        pad = np.zeros((max(4, h), max(4, w), 4), np.uint8)
        pad[:h, :w] = rgba
        pad[h:, :w] = rgba[-1:, :]
        pad[:, w:] = pad[:, w - 1:w]
        rgba, w, h = pad, pad.shape[1], pad.shape[0]
    raw = np.ascontiguousarray(rgba).tobytes()
    fn = {'BC1': etcpak.compress_bc1, 'BC3': etcpak.compress_bc3, 'BC4': etcpak.compress_bc4,
          'BC5': etcpak.compress_bc5, 'BC7': etcpak.compress_bc7}[kind]
    return fn(raw, w, h)


TEXCONV = None   # DirectXTex texconv.exe from --texconv; None compresses every page with etcpak
TEXCONV_FMT = {'BC1': 'BC1_UNORM', 'BC3': 'BC3_UNORM', 'BC4': 'BC4_UNORM', 'BC5': 'BC5_UNORM', 'BC7': 'BC7_UNORM'}


def _texconv(rgba, kind, mips, tmp):
    """Compress with DirectXTex texconv from an R8G8B8A8_UNORM DDS (no colour-space conversion)."""
    h, w = rgba.shape[:2]
    src_dir = os.path.join(tmp, 'in')
    out_dir = os.path.join(tmp, 'out')
    os.makedirs(src_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)
    src = os.path.join(src_dir, 'tex.dds')
    hdr = b'DDS ' + struct.pack('<7I', 124, 0x100F, h, w, w * 4, 0, 1) + bytes(44)
    hdr += struct.pack('<2I4s5I', 32, 0x4, b'DX10', 0, 0, 0, 0, 0) + struct.pack('<5I', 0x1000, 0, 0, 0, 0)
    hdr += struct.pack('<5I', 28, 3, 0, 1, 0)
    with open(src, 'wb') as f:
        f.write(hdr + np.ascontiguousarray(rgba, np.uint8).tobytes())
    r = subprocess.run([TEXCONV, '-nologo', '-nogpu', '-y', '-f', TEXCONV_FMT[kind], '-m', str(mips), '-dx10',
                        '-o', out_dir, src], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f'texconv failed: {r.stdout} {r.stderr}')
    data = open(os.path.join(out_dir, 'tex.dds'), 'rb').read()
    if data[84:88] != b'DX10':
        raise RuntimeError('texconv output lacks DX10 header')
    return data[148:]


def make_sps(vanilla, img, tmp=None):
    h = sps_header(vanilla)
    kind = h['kind']
    sizes = mip_sizes(kind, h['w'], h['h'], h['mips'])
    if tmp is not None:
        top = np.asarray(img.convert('RGBA').resize((h['w'], h['h']), Image.LANCZOS)
                         if img.size != (h['w'], h['h']) else img.convert('RGBA'), np.uint8)
        body = _texconv(top, kind, h['mips'], tmp)
        if len(body) != sum(sizes):
            raise ValueError(f'texconv body {len(body)} != {sum(sizes)}')
    else:
        body = bytearray()
        for lv, expect in zip(_mip_chain(img, h['w'], h['h'], h['mips']), sizes):
            blk = _encode(kind, lv)
            if len(blk) != expect:
                raise ValueError(f'mip size {len(blk)} != {expect}')
            body += blk
    out = bytes(vanilla[:h['data_offset']]) + bytes(body)
    if len(out) != len(vanilla):
        raise ValueError(f'sps size {len(out)} != vanilla {len(vanilla)}')
    return out


def load_texmeshman(path):
    names = {}
    with open(path, 'rb') as f:
        if f.read(4) != b'NAMS':
            raise ValueError('bad texmeshman')
        f.read(4 + 8 + 8 + 4 + 4)
        off = struct.unpack('<I', f.read(4))[0]
        f.read(4)
        f.seek(off + 40)
        n = struct.unpack('<I', f.read(4))[0]
        f.read(4)
        for _ in range(n):
            ln = struct.unpack('<I', f.read(4))[0]
            name = ''
            if ln != 255 and ln > 0:
                name = f.read(ln).decode('utf-8', 'ignore').replace('\x00', '')
            f.read(16)
            h = struct.unpack('<Q', f.read(8))[0]
            f.read(11)
            if f.read(1)[0] == 1:
                f.read(108)
            f.read(20)
            names[h] = name
    return names


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--profile', choices=sorted(PROFILES), default='original')
    ap.add_argument('--game', default=GAME_DEFAULT, help='game folder; default: GOT_GAME_DIR')
    ap.add_argument('--vrm', default=None, help='source VRM (required)')
    ap.add_argument('--texconv', default=None, help='DirectXTex texconv.exe for the colour pages; default: etcpak')
    ap.add_argument('--expected-texconv-sha256', default=None, help='refuse a texconv binary with another hash')
    ap.add_argument('--work', default=os.path.join(os.environ.get('TEMP', '.'), 'got_karin_original_work'))
    ap.add_argument('--out', required=True)
    ap.add_argument('--scale', type=float, default=1.45)
    ap.add_argument('--chest-share', type=float, default=0.0)   # 0 = uniform torso stretch
    ap.add_argument('--head-scale', type=float, default=None)
    ap.add_argument('--neck-drop', type=float, default=5.0)
    ap.add_argument('--shoulder-fit', type=float, default=None, help='default: the profile\'s value')
    ap.add_argument('--arm-drop', type=float, default=None, help='default: the profile\'s value')
    ap.add_argument('--foot-scale', type=float, default=None, help='own-shape feet only; default: the profile\'s value')
    ap.add_argument('--arm-hang', type=float, default=None, help='degrees; default: the profile\'s value')
    args = ap.parse_args()
    prof = PROFILES[args.profile]
    args.vrm = args.vrm or prof['vrm']
    if not args.vrm or not os.path.isfile(args.vrm):
        ap.error('--vrm must name the source VRM file')
    if not args.game or not os.path.isdir(os.path.join(args.game, 'cache_pc', 'psarc')):
        ap.error('--game (or GOT_GAME_DIR) must be the game folder containing cache_pc\\psarc')
    global TEXCONV
    TEXCONV, texconv_sha256 = None, None
    if args.expected_texconv_sha256 and not args.texconv:
        ap.error('--expected-texconv-sha256 needs --texconv')
    if args.texconv:
        args.texconv = os.path.abspath(args.texconv)   # hash and run the same file, never a PATH lookup
        if not os.path.isfile(args.texconv):
            ap.error(f'--texconv {args.texconv} is not a file')
        texconv_sha256 = hashlib.sha256(open(args.texconv, 'rb').read()).hexdigest()
        if args.expected_texconv_sha256 and texconv_sha256 != args.expected_texconv_sha256.lower():
            ap.error(f'texconv sha256 {texconv_sha256} does not match --expected-texconv-sha256')
        TEXCONV = args.texconv
    for k in ('shoulder_fit', 'arm_drop', 'foot_scale', 'arm_hang'):
        if getattr(args, k) is None:
            setattr(args, k, prof[k])
    if args.foot_scale is not None and (not prof['own_feet'] or not 0 < args.foot_scale < 10):
        ap.error('--foot-scale needs a profile with own-shape feet and a value in (0, 10)')
    if args.arm_hang is not None and not 0 < args.arm_hang <= 120:
        # the rest solve divides by (1 - w) I + w R: near 180 degrees half-arm vertices blow up
        ap.error('--arm-hang needs a value in (0, 120]')
    t0 = time.time()
    arc_dir = os.path.join(args.game, 'cache_pc', 'psarc')
    van = os.path.join(args.work, 'vanilla')
    report = {'vrm': args.vrm, 'vrm_md5': hashlib.md5(open(args.vrm, 'rb').read()).hexdigest(),
              'scale': args.scale, 'chest_share': args.chest_share, 'neck_drop': args.neck_drop,
              'shoulder_fit': args.shoulder_fit, 'arm_drop': args.arm_drop, 'foot_scale': args.foot_scale,
              'arm_hang': args.arm_hang, 'texconv_sha256': texconv_sha256}

    # 1. vanilla assets
    need_meshes = [ALL_RANKS] + [f'/meshes/{n}.xmesh' for n in HIDE_MESHES]
    idx_path = os.path.join(args.work, 'index.json')
    if os.path.exists(idx_path):
        index = json.load(open(idx_path))
    else:
        index = {}
        for a in ARCHIVES:
            for n in Psarc(os.path.join(arc_dir, a + '.psarc')).files:
                index.setdefault(n, a)
        os.makedirs(args.work, exist_ok=True)
        json.dump(index, open(idx_path, 'w'))
    extract_to(arc_dir, ['/hero.xpps', '/game.sprig.texmeshman'] + need_meshes, van, index)
    xpps_raw = open(os.path.join(van, 'hero.xpps'), 'rb').read()
    xp = Xpps(xpps_raw)
    J = skeleton_world(xp.skeleton(0))[:, :3, 3]
    texnames = load_texmeshman(os.path.join(van, 'game.sprig.texmeshman'))
    print(f'[1] vanilla ready ({time.time() - t0:.0f}s)')

    # 2. Karin: load, fit, lift feet
    from vrm import Vrm
    vrm = Vrm(args.vrm)
    prims = [p for p in vrm.primitives() if p['mat_name'] != 'Karin_Alpha']
    for p in prims:   # primitives of one glTF mesh may share a vertex buffer: keep only their own vertices
        keep_triangles(p, np.ones(len(p['tris']), bool))
    uncut = [dict(p) for p in prims]
    anc_cache = {j: humanoid_ancestor(vrm, j) or '' for j in range(len(vrm.nodes))}
    if prof['cover'] == 'sock_top':
        report['hidden_leg_tris'] = hide_under_cover(prims, anc_cache)
    else:
        report['hidden_tris'] = hide_covered(prims, prof['cover'])
    if prof['split_hands']:
        split_hands(prims, prof['split_hands'], anc_cache)
    for p in prims:
        p['role'] = prof['role'](p)
        if p['role'] not in ROLES:
            raise ValueError(f"no armour slot for mesh {p['mesh']} ({p['mat_name']})")
    caps = {}
    for role, (_mtl, hashes) in ROLES.items():
        cv = sum(xp.mesh(h).vertex_count for h in hashes)
        ct = sum(xp.mesh(h).index_count // 3 for h in hashes)
        # a multi-part role loses room at the cuts; only a profile that can reduce needs the head room
        mv, mt = MULTI_SLOT_MARGIN if len(hashes) > 1 and prof['decimatable'] else (1.0, 1.0)
        caps[role] = (int(cv * mv), int(ct * mt))
    reduced = fit_capacity(prims, caps, prof['decimatable'])
    if reduced:
        report['reduced'] = reduced
    tps, info = build_warp(vrm, skeleton_world(xp.skeleton(0)), scale=args.scale,
                           head_scale=args.head_scale, chest_share=args.chest_share,
                           neck_drop=args.neck_drop, shoulder_fit=args.shoulder_fit,
                           arm_drop=args.arm_drop, prims=prims,
                           radius_prims=uncut if prof['ring_radii'] == 'uncut' else None,
                           ctrl_policy=prof['ctrl_policy'], own_feet=prof['own_feet'],
                           foot_scale=args.foot_scale)
    report['ring_r'] = {k: round(v, 2) for k, v in info['ring_r'].items()}
    hs, hn, A_head = info['maps']['head']
    kj, tgt = info['kj'], info['tgt']
    foot_scale = args.foot_scale if args.foot_scale is not None else args.scale
    for p in prims:
        p['hanc'] = np.vectorize(anc_cache.get, otypes=[object])(p['joints'])
        P0 = gltf_to_got(p['pos'])
        N0 = np.stack([p['normal'][:, 2], p['normal'][:, 0], p['normal'][:, 1]], 1)
        P = tps(P0)
        Jac = tps.jacobian(P0)
        # skin on the head subtree (face, hair, ears) moves rigidly with the head, as it is skinned in game;
        # the spatial warp would drag hair hanging by the neck/shoulders along with the torso fit
        f = sum(np.where(np.isin(p['hanc'][:, k], HEAD_BONES), p['weights'][:, k], 0) for k in range(4))
        P = f[:, None] * (hn + (P0 - hs) @ A_head.T) + (1 - f[:, None]) * P
        Jac = f[:, None, None] * A_head + (1 - f[:, None, None]) * Jac
        if prof['own_feet']:
            # the shoe and what hangs over it (leg warmer, sock tops) share the foot's size about the ankle,
            # blending in from mid-shin: the warp keeps loose cloth far from the bone rings at the body scale,
            # and the warmer hem outgrew the smaller shoe
            for side in ('left', 'right'):
                knee, ank = kj[f'{side}LowerLeg'], kj[f'{side}Foot']
                a = ank - knee
                t = np.clip(2 * ((P0 - knee) @ a) / (a @ a) - 1, 0, 1)
                chain = [f'{side}LowerLeg', f'{side}Foot', f'{side}Toes']
                m = sum(np.where(np.isin(p['hanc'][:, k], chain), p['weights'][:, k], 0) for k in range(4))
                b = m * t * t * (3 - 2 * t)
                F = tgt[f'{side}Foot'] + foot_scale * (P0 - ank)
                grad_b = (m * 6 * t * (1 - t))[:, None] * (2 * a / (a @ a))   # zero outside the blend band
                Jac = ((1 - b[:, None, None]) * Jac + b[:, None, None] * foot_scale * np.eye(3)
                       + (F - P)[:, :, None] * grad_b[:, None, :])
                P = (1 - b[:, None]) * P + b[:, None] * F
        p['P'], p['P0'], p['N0'] = P, P0, N0
        N = np.einsum('vji,vj->vi', np.linalg.inv(Jac), N0)
        p['N'] = N / np.linalg.norm(N, axis=1, keepdims=True).clip(1e-12)
    # ground contact: sole lowest point -> vanilla foot floor
    # vanilla contact height: lowest LOD0 point of Jin's feet and of the armour's sandals
    floor = np.inf
    for fn in ('hero_body_feet.xmesh', ALL_RANKS.split('/')[-1]):
        x = Xmesh(open(os.path.join(van, 'meshes', fn), 'rb').read())
        for r in x.records:
            if (r.lod & 0xff) == 0:
                d = decode_record(x, r, xp.mesh(r.hash))
                floor = min(floor, d['pos'][np.unique(d['tris']), 2].min())
    report['floor_cm'] = float(floor)
    for side in ('left', 'right'):
        leg_nodes = {vrm.human[f'{side}{b}'] for b in ('UpperLeg', 'LowerLeg', 'Foot', 'Toes')}
        foot_nodes = {vrm.human[f'{side}Foot'], vrm.human[f'{side}Toes']}

        def frac(p, nodes):
            names_ = [vrm.node_human[n] for n in nodes]
            return sum(np.where(np.isin(p['hanc'][:, k], names_), p['weights'][:, k], 0) for k in range(4))
        sole = min(p['P'][frac(p, foot_nodes) > 0.5, 2].min() for p in prims if (frac(p, foot_nodes) > 0.5).any())
        lift = floor - sole
        # spread over hip joint -> ankle so thigh and shin share it (knee -> ankle alone shortens the shin)
        zk = J[595 if side == 'left' else 616, 2]
        za = J[597 if side == 'left' else 618, 2]
        for p in prims:
            m = frac(p, leg_nodes)
            z_before = p['P'][:, 2].copy()
            ramp = np.clip((zk - z_before) / (zk - za), 0, 1)
            p['P'][:, 2] += lift * ramp * m
            # normals: inverse-transpose of the local z-scale dz'/dz = 1 + lift * m * dramp/dz
            dramp = np.where((z_before > za) & (z_before < zk), -1.0 / (zk - za), 0.0)
            s = 1 + lift * m * dramp
            N = p['N'].copy()
            N[:, 2] /= s
            p['N'] = N / np.linalg.norm(N, axis=1, keepdims=True).clip(1e-12)
        report[f'{side}_foot_lift_cm'] = float(lift)
    print(f'[2] fitted ({time.time() - t0:.0f}s) lifts', report['left_foot_lift_cm'], report['right_foot_lift_cm'])

    # 3. weights, tangents, per-role meshes
    skirt_bones = prof['skirt_bones']
    if prof['skirt_mesh']:
        skirt = [p['P'][:, 2] for p in prims if p['mesh'] == prof['skirt_mesh']]
    else:   # vertices a skirt bone dominates
        skirt = []
        for p in prims:
            dom = p['joints'][np.arange(len(p['P'])), p['weights'].argmax(1)]
            m = np.array([vrm.names[j].startswith(skirt_bones) for j in dom])
            if m.any():
                skirt.append(p['P'][m, 2])
    skirt_z = (max(z.max() for z in skirt), min(z.min() for z in skirt)) if skirt else (100, 60)
    report['skirt_z_cm'] = [round(float(z), 2) for z in skirt_z]
    # x (forward) of the hip joints: the hem behind them stays with the pelvis instead of folding under the seat
    skirt_front = ((J[595, 0] + J[616, 0]) / 2, 3.0) if prof['skirt_front_only'] else None
    role_meshes = {r: [] for r in ROLES}
    img_of = {}
    src_of = {}
    page_items = {r: [] for r in ROLES}
    hang = hang_pose(info, J, xp.skeleton(0)['parents'], args.arm_hang, args.scale) if args.arm_hang else None
    hung = 0
    for p in prims:
        arm_pos = arm = None
        if hang:
            arm_pos, arm = {}, {}
            for h, (hs_, hn_, A) in hang[0].items():
                arm_pos[h] = hn_ + (p['P0'] - hs_) @ A.T
                Na = p['N0'] @ np.linalg.inv(A)
                Na /= np.linalg.norm(Na, axis=1, keepdims=True).clip(1e-12)
                arm.update({b: (arm_pos[h], Na) for b, _ in LIMBS[h][2]})
        bones, weights = map_weights(vrm, p, p['P'], J, skirt_z, skirt_bones, skirt_front, arm_pos)
        if hang:
            p['P'], p['N'], n = rest_from_hang(p['P'], p['N'], bones, weights, hang[1], hang[2], arm)
            hung += n
        T = p['tris']
        tan, sign = tangents(p['P'], p['N'], p['uv'], T)
        mesh = dict(pos=p['P'], normal=p['N'], tangent=tan, tsign=sign, uv=p['uv'].astype(np.float64),
                    bones=bones, weights=weights, tris=T)
        mat = p['mat_name']
        role = p['role']
        role_meshes[role].append(mesh)
        tex_idx = vrm.js['materials'][p['material']]['pbrMetallicRoughness']['baseColorTexture']['index']
        src = vrm.js['textures'][tex_idx]['source']
        if prof['pages'] == 'atlas':
            page_items[role].append((mesh, src))
            continue
        if src_of.setdefault(role, src) != src:
            raise ValueError(f'role {role}: baseColor image {src} differs from {src_of[role]} ({mat})')
        img_of.setdefault(role, vrm.image(src).convert('RGBA'))

    if prof['pages'] == 'atlas':
        # every role page packs the used UV regions of all its meshes' source images
        images = {}
        for role, items in page_items.items():
            d_name = [n for n in role_texture_names(xp, texnames, role) if '.msac.d.' in n][0]
            extract_to(arc_dir, [f'/bitmaps/{d_name}'], van, index)
            hd = sps_header(open(os.path.join(van, 'bitmaps', d_name), 'rb').read())
            for _, src in items:
                if src not in images:
                    images[src] = vrm.image(src).convert('RGBA')
            page, uvs, st = build_page([dict(img=images[src], uv=m['uv'], tris=m['tris'], key=src)
                                        for m, src in items], (hd['w'], hd['h']))
            for (m, _), uv in zip(items, uvs):
                m['uv'] = uv
            img_of[role] = page
            report.setdefault('pages', {})[role] = dict(size=[hd['w'], hd['h']], sources=sorted({s for _, s in items}),
                                                        **{k: round(v, 4) if isinstance(v, float) else v
                                                           for k, v in st.items()})
    else:
        # details page: 1024 window of the costume texture around the underwear UVs (1:1 texels)
        dm = concat(role_meshes['details'])
        cw, ch = img_of['details'].size
        u0, v0 = dm['uv'].min(0)
        u1, v1 = dm['uv'].max(0)
        if (u1 - u0) * cw > 1008 or (v1 - v0) * ch > 1008:
            raise ValueError('details UV island does not fit a 1024 page')
        x0 = int(np.clip(round((u0 + u1) / 2 * cw) - 512, 0, cw - 1024))
        y0 = int(np.clip(round((v0 + v1) / 2 * ch) - 512, 0, ch - 1024))
        img_of['details'] = img_of['details'].crop((x0, y0, x0 + 1024, y0 + 1024))
        for m in role_meshes['details']:
            m['uv'] = (m['uv'] * [cw, ch] - [x0, y0]) / 1024.0
        report['details_window_px'] = [x0, y0]
    if hang:
        report['arm_hang_verts'] = hung
    print(f'[3] weights/tangents ({time.time() - t0:.0f}s)')

    # 4. all-ranks mesh: write Karin into the 8 parts, hide the rest
    xm = Xmesh(open(os.path.join(van, ALL_RANKS.lstrip('/')), 'rb').read())
    rec = {r.hash: r for r in xm.records}
    written = set()
    report['slots'] = {}
    for role, (_mtl, hashes) in ROLES.items():
        mesh = concat(role_meshes[role])
        parts = [xp.mesh(h) for h in hashes]
        for m in parts:
            if m.asset != 0 or m.textures != parts[0].textures:
                raise ValueError(f'role {role}: part {m.hash:016x} asset {m.asset} or textures differ')
        if len(parts) == 1:
            chunks = [mesh]
        else:
            cent_z = mesh['pos'][mesh['tris']].mean(1)[:, 2]
            chunks = split_to_capacity(mesh, [(m.vertex_count, m.index_count // 3) for m in parts], -cent_z)
        for h, m, c in zip(hashes, parts, chunks + [None] * (len(parts) - len(chunks))):
            r = rec[h]
            if c is None:
                xm.clear(r)
                xp.hide(m)
                continue
            if [a[0] for a in m.attrs] != SLOT_FORMATS:
                raise ValueError(f'{h:016x}: unexpected attribute formats {[a[0] for a in m.attrs]}')
            off, scl, bmin, bmax = encode_record(xm, r, m, c)
            xp.set_quant(m, off, scl)   # bbox stays vanilla, as in the working v1.0 hero.xpps
            written.add(h)
            report['slots'][f'{h:016x}'] = dict(role=role, verts=len(c['pos']), tris=len(c['tris']),
                                                 cap_verts=m.vertex_count, cap_tris=m.index_count // 3)
    for r in xm.records:
        if r.hash not in written:
            xm.clear(r)
            for m in xp.by_hash.get(r.hash, []):
                xp.hide(m)
    out_files = {ALL_RANKS: bytes(xm.data)}
    for n in HIDE_MESHES:
        path = f'/meshes/{n}.xmesh'
        x = Xmesh(open(os.path.join(van, path.lstrip('/')), 'rb').read())
        for r in x.records:
            x.clear(r)
            for m in xp.by_hash.get(r.hash, []):
                xp.hide(m)
        out_files[path] = bytes(x.data)
    old, new, count = CLOTH_FLAG
    if xp.data.count(old) != count:
        raise ValueError(f'cloth flag pattern found {xp.data.count(old)} times, expected {count}')
    xp.data[:] = xp.data.replace(old, new)
    # package identity at 0x98: v1.0 shipped a non-vanilla value and loads fine; derive a new one from content
    xp.data[0x98:0xa8] = bytes(16)
    xp.data[0x98:0xa8] = hashlib.md5(bytes(xp.data)).digest()
    print(f'[4] meshes/xpps ({time.time() - t0:.0f}s)')

    # 5. textures
    tex_files = {}
    for role in ROLES:
        names = role_texture_names(xp, texnames, role)
        spec, gloss = MATERIAL[role]
        for n in names:
            path = f'/bitmaps/{n}'
            if path not in index:
                raise KeyError(f'{path} missing from archives')
            extract_to(arc_dir, [path], van, index)
            vanilla = open(os.path.join(van, path.lstrip('/')), 'rb').read()
            ch_ = n.split('.msac.')[1].split('.')[0]
            hd = sps_header(vanilla)
            size = (hd['w'], hd['h'])
            if ch_ == 'd':
                img = img_of[role].copy()
                img.putalpha(255)
            else:
                val = {'n': (128, 128, 255, 255), 'ao': (255,) * 4, 's': (spec,) * 4, 'g': (gloss,) * 4}.get(
                    ch_, (0, 0, 0, 255))
                img = Image.new('RGBA', size, val)
            tex_files[path] = make_sps(vanilla, img,
                                       os.path.join(args.work, 'texconv') if ch_ == 'd' and TEXCONV else None)
        report.setdefault('textures', {})[role] = names
    print(f'[5] textures ({time.time() - t0:.0f}s)')

    # 6. package (same order as v1.0: xpps, bitmaps, meshes)
    files = [('/hero.xpps', bytes(xp.data))] + sorted(tex_files.items()) + sorted(out_files.items())
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    size = write_psarc(args.out, files)
    report['files'] = len(files)
    report['psarc_bytes'] = size
    report['psarc_md5'] = hashlib.md5(open(args.out, 'rb').read()).hexdigest()
    json.dump(report, open(os.path.splitext(args.out)[0] + '.build.json', 'w'), indent=1)
    print(f'[6] wrote {args.out} ({size / 1e6:.1f} MB, {len(files)} files, {time.time() - t0:.0f}s)')


if __name__ == '__main__':
    main()
