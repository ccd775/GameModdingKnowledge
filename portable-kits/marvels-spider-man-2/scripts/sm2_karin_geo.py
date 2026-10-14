"""Karin VRM -> Spider-Man 2 hero bind space: repose, fit, weights.

  python sm2_karin_geo.py --target peter|miles [--vrm ...] [--scale 1.45 --head-scale 1.45 --neck-drop 3] [--skirt-height]
Writes Work/build_<target>/karin_geo.npz (+ report json, preview png).

Steps
 1. LBS-repose Karin (T-pose) so every limb segment points like the hero's A-pose bind skeleton
    (shoulder, upper/lower arm with half the hand twist, hand, fingers, thumb, legs, feet).
 2. TPS warp of the reposed mesh onto the hero joints (sm2_fit = Ghost of Tsushima fitter, cm, x fwd/y left/z up);
    head subtree (face, hair, ears) moves rigidly with the head map; sole lifted to the hero's floor.
 3. Weights onto the hero deform joints (u2 & 0x80): spine chain / limb twist helpers by position along the bone,
    skirt copies the hip / thigh surface under it (skirt_transfer / skirt_rows), tail -> pelvis, head subtree -> head.
"""
import argparse, json, os, sys, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vrm as vrmmod          # noqa: E402
import sm2_fit as F           # noqa: E402
import i30_model as M         # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.environ.get('SM2_WORK') or os.path.dirname(HERE)     # same rule as sm2_common.WORK
VRM_DEFAULT = os.environ.get('SM2_VRM')                        # source VRM; --vrm overrides it here


def vrm_path():
    """SM2_VRM for the tools that read the source VRM without a --vrm option (sm2_batch, sm2_face, sm2_pose_check)."""
    if not VRM_DEFAULT:
        raise SystemExit('SM2_VRM is not set: point it at the source VRM')
    return VRM_DEFAULT


TARGETS = {
    'peter': 'characters/hero/hero_spiderman_advanced/hero_spiderman_advanced.model',
    'miles': 'characters/hero/hero_spiderman_miles_updated/hero_spiderman_miles_updated.model',
}
FINGERS = {'Index': 'A', 'Middle': 'B', 'Ring': 'C', 'Little': 'D'}


def sm_names(side):
    s = 'LF_' if side == 'left' else 'RT_'
    m = {f'{side}Shoulder': s + 'clavicle', f'{side}UpperArm': s + 'uparm', f'{side}LowerArm': s + 'loarm',
         f'{side}Hand': s + 'wrist', f'{side}UpperLeg': s + 'upleg', f'{side}LowerLeg': s + 'loleg',
         f'{side}Foot': s + 'foot', f'{side}Toes': s + 'ball',
         f'{side}ThumbMetacarpal': s + 'thumb_A', f'{side}ThumbProximal': s + 'thumb_B', f'{side}ThumbDistal': s + 'thumb_C'}
    for f, k in FINGERS.items():
        m[f'{side}{f}Proximal'] = f'{s}finger_{k}_B'
        m[f'{side}{f}Intermediate'] = f'{s}finger_{k}_C'
        m[f'{side}{f}Distal'] = f'{s}finger_{k}_D'
    return m


HUMAN2NAME = {'hips': 'pelvis', 'neck': 'neck', 'head': 'head', **sm_names('left'), **sm_names('right')}


def gltf_to_got(p):
    return F.gltf_to_got(p)


def got_to_gltf(p):
    p = np.asarray(p, np.float64)
    return np.stack([p[..., 1], p[..., 2], p[..., 0]], -1) / 100.0


class Hero:
    def __init__(self, path):
        self.m = M.Model(open(path, 'rb').read())
        self.names = [j['name'] for j in self.m.joints]
        self.idx = {n: i for i, n in enumerate(self.names)}
        self.W = self.m.joint_world()                     # row-vector matrices; translation = W[i][3,:3]
        self.J = np.array([w[3, :3] for w in self.W])     # glTF-like frame: x left, y up, z fwd, metres
        self.deform = {i for i, j in enumerate(self.m.joints) if j['u2'] & 0x80}

    def pos(self, name):
        return self.J[self.idx[name]]

    def got_world(self):
        """4x4 column-vector matrices in GoT cm (only translation is used by the fitter)."""
        out = np.tile(np.eye(4), (len(self.J), 1, 1))
        out[:, :3, 3] = gltf_to_got(self.J)
        return out

    def floor(self):
        lo = np.inf
        for me in self.m.meshes:
            if (me.skin_info >> 16) == 1:
                d = self.m.decode(me, skin=False)
                if len(d['idx']):
                    lo = min(lo, d['pos'][np.unique(d['idx']), 1].min())
        return lo


# ------------------------------------------------------------------ 1. repose
def subtree(parent, root):
    kids = {}
    for i, p in enumerate(parent):
        kids.setdefault(p, []).append(i)
    out, st = [], [root]
    while st:
        n = st.pop()
        out.append(n)
        st.extend(kids.get(n, []))
    return out


def rotate_subtree(G, nodes, R, pivot):
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = pivot - R @ pivot
    for n in nodes:
        G[n] = T @ G[n]


def axis_angle(axis, ang):
    a = axis / np.linalg.norm(axis)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(ang) * K + (1 - np.cos(ang)) * K @ K


def repose(v, hero, log):
    G = v.world.copy()
    H = v.human
    sub = {n: subtree(v.parent, n) for n in H.values()}
    P = lambda h: G[H[h]][:3, 3]
    T = lambda h: hero.pos(HUMAN2NAME[h])

    def align(bone, child, tgt_child=None, frac=1.0):
        if bone not in H or child not in H:
            return
        d_s = P(child) - P(bone)
        d_t = (hero.pos(tgt_child) if tgt_child else T(child)) - T(bone)
        R = F.rot_between(d_s, d_t)
        if frac != 1.0:
            ax = np.cross(d_s, d_t)
            if np.linalg.norm(ax) > 1e-9:
                ang = np.arccos(np.clip(d_s @ d_t / np.linalg.norm(d_s) / np.linalg.norm(d_t), -1, 1))
                R = axis_angle(ax, ang * frac)
        rotate_subtree(G, sub[H[bone]], R, P(bone).copy())

    def twist(bone, axis_from, axis_to, a_s_pair, a_t_pair, frac):
        """rotate bone subtree about the axis so the across-hand vector matches the hero's (by frac)"""
        ax = P(axis_to) - P(axis_from)
        ax /= np.linalg.norm(ax)
        vs = P(a_s_pair[0]) - P(a_s_pair[1])
        vt = hero.pos(a_t_pair[0]) - hero.pos(a_t_pair[1])
        vs -= ax * (vs @ ax)
        vt -= ax * (vt @ ax)
        ang = np.arctan2(np.cross(vs, vt) @ ax, vs @ vt)
        rotate_subtree(G, sub[H[bone]], axis_angle(ax, ang * frac), P(bone).copy())
        return np.degrees(ang)

    rep = {}
    for side in ('left', 'right'):
        s = 'LF_' if side == 'left' else 'RT_'
        align(f'{side}Shoulder', f'{side}UpperArm')
        align(f'{side}UpperArm', f'{side}LowerArm')
        align(f'{side}LowerArm', f'{side}Hand')
        align(f'{side}Hand', f'{side}MiddleProximal')
        pair_s = (f'{side}IndexProximal', f'{side}LittleProximal')
        pair_t = (f'{s}finger_A_B', f'{s}finger_D_B')
        rep[f'{side}_twist_deg'] = twist(f'{side}LowerArm', f'{side}LowerArm', f'{side}Hand', pair_s, pair_t, 0.5)
        twist(f'{side}Hand', f'{side}Hand', f'{side}MiddleProximal', pair_s, pair_t, 1.0)
        for f in FINGERS:
            align(f'{side}{f}Proximal', f'{side}{f}Intermediate')
            align(f'{side}{f}Intermediate', f'{side}{f}Distal')
        align(f'{side}ThumbMetacarpal', f'{side}ThumbProximal')
        align(f'{side}ThumbProximal', f'{side}ThumbDistal')
        align(f'{side}UpperLeg', f'{side}LowerLeg')
        align(f'{side}LowerLeg', f'{side}Foot')
        align(f'{side}Foot', f'{side}Toes')
    log(f'repose: forearm twist L {rep["left_twist_deg"]:.1f} R {rep["right_twist_deg"]:.1f} deg (half applied on forearm)')
    det = np.abs(np.linalg.det(v.world[:, :3, :3]))
    inv = np.tile(np.eye(4), (len(G), 1, 1))
    ok = det > 1e-12                                   # some helper nodes carry zero scale; they skin nothing
    inv[ok] = np.linalg.inv(v.world[ok])
    S = np.einsum('nij,njk->nik', G, inv)
    return G, S, rep


def skin(prim, S):
    J, W = prim['joints'], prim['weights']
    Mv = np.einsum('vk,vkij->vij', W, S[J])
    P = np.einsum('vij,vj->vi', Mv[:, :3, :3], prim['pos']) + Mv[:, :3, 3]
    N = np.einsum('vij,vj->vi', np.linalg.inv(Mv[:, :3, :3]).transpose(0, 2, 1), prim['normal'])
    return P, N / np.linalg.norm(N, axis=1, keepdims=True).clip(1e-12)


class Posed:
    """vrm-like view with posed world matrices for sm2_fit.build_warp"""
    def __init__(self, v, G):
        self.nodes, self.parent, self.human, self.node_human, self.names = v.nodes, v.parent, v.human, v.node_human, v.names
        self.world = G


# ------------------------------------------------------------------ 3. weights
def hat(t, keys):
    """piecewise-linear partition of unity over sorted keys (list of t) -> (n, len(keys))"""
    t = np.clip(t, keys[0], keys[-1])
    out = np.zeros((len(t), len(keys)))
    for c in range(len(keys)):
        y = np.zeros(len(keys))
        y[c] = 1
        out[:, c] = np.interp(t, keys, y)
    return out


def seg_t(P, a, b):
    d = b - a
    return ((P - a) @ d) / (d @ d)


def make_weight_mapper(v, hero, anc, dyn_map=None, skirt_src=None):
    """returns f(prim, P_fitted_gltf) -> (joints[n,8], weights[n,8]) in hero joint indices.
    dyn_map {vrm node: joint index >= len(hero.names)}: spring-chain nodes that become their own (dynamics) joints.
    skirt_src: use prim['skirt_rows'] (dense hero weights per vertex, skirt_rows()) for the skirt bones' share;
    None: old height blend spine -> thighs."""
    dyn_map = dyn_map or {}
    ix = hero.idx
    head = ix['head']
    spine_nodes = [n for n in ('pelvis', 'spine', 'spine_helper1', 'spine_B', 'spine_B_helper2', 'chest') if n in ix]
    spine_y = [hero.pos(n)[1] for n in spine_nodes]
    limbs = {}
    for side in ('left', 'right'):
        s = 'LF_' if side == 'left' else 'RT_'
        up = [n for n in (s + 'uparm_bind_1', s + 'uparm_bind_2', s + 'uparm_bind_3', s + 'uparm_bind_4') if n in ix]
        lo = [n for n in (s + 'loarm', s + 'loarm_bind_2', s + 'loarm_bind_3', s + 'loarm_bind_4', s + 'loarm_bind_5') if n in ix]
        if not up:
            up = [s + 'uparm']
        a, e, w = hero.pos(s + 'uparm'), hero.pos(s + 'loarm'), hero.pos(s + 'wrist')
        limbs[f'{side}UpperArm'] = (a, e, up + [s + 'loarm'], [seg_t(hero.pos(n)[None], a, e)[0] for n in up] + [1.0])
        limbs[f'{side}LowerArm'] = (e, w, lo, [seg_t(hero.pos(n)[None], e, w)[0] for n in lo])
    for k, (_, _, nodes, keys) in limbs.items():
        o = np.argsort(keys)
        limbs[k] = (limbs[k][0], limbs[k][1], [nodes[i] for i in o], [keys[i] for i in o])
    names = v.names

    def f(prim, P):
        V = len(P)
        acc = np.zeros((V, len(hero.names) + len(dyn_map)))
        y = P[:, 1]
        for k in range(prim['joints'].shape[1]):
            jk, wk = prim['joints'][:, k], prim['weights'][:, k]
            for j in np.unique(jk[wk > 0]):
                sel = np.where((jk == j) & (wk > 0))[0]
                w = wk[sel]
                name = names[j]
                h = anc[j]
                if j in dyn_map:
                    acc[sel, dyn_map[j]] += w
                elif name.startswith('Skirt') and skirt_src is not None:
                    rows = prim['skirt_rows'][sel]
                    acc[sel, :rows.shape[1]] += w[:, None] * rows
                elif name.startswith('Skirt'):
                    # waistband with the spine at its height, hem shared with the thigh on its side
                    top, bot = SKIRT_Y
                    t = np.clip((top - y[sel]) / max(top - bot, 1e-3), 0, 1)
                    a_ = SKIRT_MAX_LEG * t * t * (3 - 2 * t)
                    left = 1 / (1 + np.exp(-P[sel, 0] / 0.04))
                    hw = hat(y[sel], spine_y)
                    for c, n in enumerate(spine_nodes):
                        acc[sel, ix[n]] += w * (1 - a_) * hw[:, c]
                    acc[sel, ix['LF_upleg']] += w * a_ * left
                    acc[sel, ix['RT_upleg']] += w * a_ * (1 - left)
                elif name.startswith('Tail') or (h == 'hips' and j != v.human['hips']):
                    acc[sel, ix['pelvis']] += w
                elif h in ('hips', 'spine', 'chest', 'upperChest'):
                    hw = hat(y[sel], spine_y)
                    for c, n in enumerate(spine_nodes):
                        acc[sel, ix[n]] += w * hw[:, c]
                elif h == 'neck':
                    acc[sel, ix['neck']] += w
                elif h in ('head', 'leftEye', 'rightEye', 'jaw'):
                    acc[sel, head] += w
                elif h in limbs:
                    a, b, nodes, keys = limbs[h]
                    hw = hat(seg_t(P[sel], a, b), keys)
                    for c, n in enumerate(nodes):
                        acc[sel, ix[n]] += w * hw[:, c]
                elif h in HUMAN2NAME:
                    acc[sel, ix[HUMAN2NAME[h]]] += w
                else:
                    raise ValueError(f'no hero joint for {name} (humanoid {h})')
        # joints without the 0x80 'skinned' flag get it set by the model builder (sm2_build_model.flag_skinned)
        top = np.argsort(-acc, axis=1)[:, :6]
        tw = np.take_along_axis(acc, top, 1)
        tw[tw < 0.75 / 256] = 0
        s = tw.sum(1, keepdims=True)
        if (s <= 0).any():
            raise ValueError('vertex without weights')
        return top, tw / s
    return f


SKIRT_MAX_LEG = 0.5
SKIRT_Y = (1.0, 0.7)   # set from the fitted skirt in main()
SKIRT_SRC = ('hips', 'spine', 'leftUpperLeg', 'rightUpperLeg')   # surfaces the skirt copies its weights from
SKIRT_K, SKIRT_SIGMA, SKIRT_SPREAD = 32, 0.03, 0.025   # transfer kernel / smoothing around the skirt (m)


def skirt_transfer(prims, wm, nj, src_nodes):
    """-> f(P): Gaussian-weighted hip / thigh / waist surface weights (body and non-skirt costume) near P, so the skirt
    moves with what is under it: a raised thigh lifts the hem instead of cutting through it."""
    from scipy.spatial import cKDTree
    Ps, Ws = [], []
    for p in prims:
        S = (np.isin(p['joints'], p['skirt_nodes']) * p['weights']).sum(1)
        dom = p['joints'][np.arange(len(p['P'])), p['weights'].argmax(1)]
        m = (S == 0) & np.isin(dom, src_nodes)          # the humanoid bones themselves: no tail / ribbon helpers
        if not m.any():
            continue
        J, W = wm(p, p['P'])
        D = np.zeros((m.sum(), nj))
        np.put_along_axis(D, J[m], W[m], 1)   # top-k joints are distinct
        Ps.append(p['P'][m]); Ws.append(D)
    Ps, Ws = np.concatenate(Ps), np.concatenate(Ws)
    tree = cKDTree(Ps)

    def f(P):
        d, i = tree.query(P, SKIRT_K)
        w = np.exp(-(d ** 2 - d[:, :1] ** 2) / (2 * SKIRT_SIGMA ** 2))
        w /= w.sum(1, keepdims=True)
        return np.einsum('vk,vkj->vj', w, Ws[i])
    return f, len(Ps)


def skirt_rows(prims, src):
    """per skirt vertex: src() at the vertex, then averaged around the skirt in (angle, height) with the radius left
    out, so the inner and outer folds of a pleat share weights and the pleats move as one."""
    sel = [(p, np.where((np.isin(p['joints'], p['skirt_nodes']) * p['weights']).sum(1) > 0)[0]) for p in prims]
    sel = [(p, i) for p, i in sel if len(i)]
    P = np.concatenate([p['P'][i] for p, i in sel])
    T = src(P)
    c = P[:, [0, 2]].mean(0)
    th = np.arctan2(P[:, 0] - c[0], P[:, 2] - c[1])
    r = np.median(np.hypot(P[:, 0] - c[0], P[:, 2] - c[1]))
    U = np.stack([r * np.sin(th), P[:, 1], r * np.cos(th)], 1)      # radius flattened to the median
    from scipy.spatial import cKDTree
    tree = cKDTree(U)
    out = np.zeros_like(T)
    for a, nb in enumerate(tree.query_ball_point(U, 3 * SKIRT_SPREAD)):
        g = np.exp(-((U[nb] - U[a]) ** 2).sum(1) / (2 * SKIRT_SPREAD ** 2))
        out[a] = g @ T[nb] / g.sum()
    o = 0
    for p, i in sel:
        p['skirt_rows'] = np.zeros((len(p['P']), T.shape[1]))
        p['skirt_rows'][i] = out[o:o + len(i)]
        o += len(i)
    return len(P)


# ------------------------------------------------------------------ main
GROUPS = {   # Karin material -> part key written into the model
    'Karin_Body': 'body', 'Karin_Costume': 'costume', 'Karin_Hair': 'hair', 'Karin_Face': 'face',
    'Karin_Hair_Transparent': 'hair_alpha', 'Karin_Alpha': 'face_alpha',
}


# VRM spring chains (first joint name) simulated by SM2 AnimDynamics (i30_dynamics chain parameters). Skirt and
# cheeks stay on the static weights: SM2 dynamics have no colliders, a simulated skirt would cut through the legs.
# Karin's VRM springs all have gravityPower 0 and hold their shape by stiffness. SM2 has no restoring force, so the shape
# comes from type 1 (Cone, as Great Hunter's muscles): every link stays within `cone` of its rest direction in its parent
# link's frame, so the possible bend adds up along the chain. Type 0 (Simple, ropes / tentacles) ignores the cone: T15
# (2026-10-13) had all chains Simple and everything hung straight down, ears folded onto the head.
# sm2_dyn.load applies these to fitted npz files, so tuning needs no --refit.
DYN_SPRINGS = {
    # T17: T16 (damping 0.15-0.3, tighter cones, gravity -0.3..-2) bounced off the cone walls; ears (4-6 deg) barely moved
    'Hair_tail_L': dict(type=1, cone=10, cone_end=14, damping=0.4, gravity=(0, -2.5, 0)),
    'Hair_tail_R': dict(type=1, cone=10, cone_end=14, damping=0.4, gravity=(0, -2.5, 0)),
    'Hair_side_L': dict(type=1, cone=10, cone_end=14, damping=0.45, gravity=(0, -2.0, 0)),
    'Hair_side_R': dict(type=1, cone=10, cone_end=14, damping=0.45, gravity=(0, -2.0, 0)),
    'Hair_front': dict(type=1, cone=8, cone_end=10, damping=0.5, gravity=(0, -1.5, 0)),
    'Hair_front_L': dict(type=1, cone=8, cone_end=10, damping=0.5, gravity=(0, -1.5, 0)),
    'Hair_front_R': dict(type=1, cone=8, cone_end=10, damping=0.5, gravity=(0, -1.5, 0)),
    'Ear_L': dict(type=1, cone=10, cone_end=14, damping=0.35, gravity=(0, -0.5, 0)),
    'Ear_R': dict(type=1, cone=10, cone_end=14, damping=0.35, gravity=(0, -0.5, 0)),
    'Ribbon_L': dict(type=1, cone=14, cone_end=20, damping=0.4, gravity=(0, -2.5, 0)),
    'Ribbon_R': dict(type=1, cone=14, cone_end=20, damping=0.4, gravity=(0, -2.5, 0)),
    'Tail': dict(type=1, cone=6, cone_end=9, damping=0.45, gravity=(0, -1.0, 0)),
}


def aim_rows(p, q, up):
    """row-vector rotation rows: X toward q, Y close to up"""
    x = (q - p) / np.linalg.norm(q - p)
    y = up - x * (up @ x)
    if np.linalg.norm(y) < 1e-6:
        y = np.array([0.0, 1.0, 0.0]) - x * x[1]
    y /= np.linalg.norm(y)
    return np.stack([x, y, np.cross(x, y)])


def dyn_joints(v, G, anc, place, hero):
    """-> (joints [dict(name, node, parent_name, world 4x4 row-vector)], chains [dict(joints=[names], **params)])
    place(node, P0_got) -> fitted SM2 position (same map as the vertices: head-rigid or TPS)."""
    springs = v.js.get('extensions', {}).get('VRMC_springBone', {}).get('springs', [])
    joints, chains = [], []
    for s in springs:
        nodes = [j['node'] for j in s['joints']]
        key = v.names[nodes[0]]
        if key not in DYN_SPRINGS:
            continue
        P = [place(n, gltf_to_got(G[n][:3, 3][None])[0]) for n in nodes]
        h = anc[nodes[0]]
        attach = 'head' if h in ('head', 'leftEye', 'rightEye', 'jaw') else HUMAN2NAME[h]
        up = np.array([0.0, 0.0, 1.0])
        rows = None
        names = []
        for i, n in enumerate(nodes):
            if i + 1 < len(nodes):
                if abs(((P[i + 1] - P[i]) / np.linalg.norm(P[i + 1] - P[i])) @ up) > 0.95:
                    up = np.array([0.0, 1.0, 0.0])
                rows = aim_rows(P[i], P[i + 1], up)
                up = rows[1]
            W = np.eye(4)
            W[:3, :3], W[3, :3] = rows, P[i]
            nm = f'karin_{key}_{i:02d}'
            joints.append(dict(name=nm, node=n, parent_name=names[-1] if names else attach, world=W))
            names.append(nm)
        chains.append(dict(joints=names, key=key, **DYN_SPRINGS[key]))
    return joints, chains


def compact(p):
    used = np.unique(p['tris'])
    if len(used) == len(p['pos']):
        return p
    remap = -np.ones(len(p['pos']), np.int64)
    remap[used] = np.arange(len(used))
    q = dict(p)
    for k in ('pos', 'normal', 'uv', 'joints', 'weights'):
        if q.get(k) is not None:
            q[k] = p[k][used]
    q['tris'] = remap[p['tris']]
    return q


def main():
    global SKIRT_Y
    ap = argparse.ArgumentParser()
    ap.add_argument('--target', choices=TARGETS)
    ap.add_argument('--model', help='hero model asset path (overrides --target)')
    ap.add_argument('--vrm', default=VRM_DEFAULT, help='source VRM (default: SM2_VRM)')
    ap.add_argument('--scale', type=float, default=1.45)
    ap.add_argument('--head-scale', type=float, default=1.45, help='= --scale keeps Karin\'s own head / body ratio '
                    '(1.3 until T8: head looked small in game)')
    ap.add_argument('--neck-drop', type=float, default=3.0, help='cm below the hero neck joint')
    ap.add_argument('--shoulder-fit', type=float, default=0.3)
    ap.add_argument('--arm-drop', type=float, default=0.0)
    ap.add_argument('--out', default=None)
    ap.add_argument('--dyn', action='store_true', help='keep DYN_SPRINGS chains as their own joints (AnimDynamics)')
    ap.add_argument('--skirt-height', action='store_true', help='old skirt weights: height blend spine -> thighs')
    a = ap.parse_args()
    t0 = time.time()
    if not a.target and not a.model:
        ap.error('--target or --model required')
    if not a.vrm:
        ap.error('--vrm or SM2_VRM required (the source VRM)')
    mpath = a.model or TARGETS[a.target]
    out = a.out or os.path.join(WORK, f'build_{a.target}')
    os.makedirs(out, exist_ok=True)
    log = lambda s: print(f'[{time.time() - t0:5.1f}s] {s}', flush=True)
    hero = Hero(os.path.join(WORK, 'native', mpath))
    v = vrmmod.Vrm(a.vrm)
    prims = [compact(p) for p in v.primitives()]
    log(f'vrm prims {len(prims)}, verts {sum(len(p["pos"]) for p in prims)}; hero joints {len(hero.names)}')

    # 1. repose
    G, S, rep = repose(v, hero, log)
    for p in prims:
        p['P_pose'], p['N_pose'] = skin(p, S)

    # 2. fit
    F.set_mapping({h: hero.idx[n] for h, n in HUMAN2NAME.items()})
    pv = Posed(v, G)
    for p in prims:
        p['pos_bak'] = p['pos']
        p['pos'] = p['P_pose']                       # limb_radii / build_warp read 'pos' as the source pose
    tps, info = F.build_warp(pv, hero.got_world(), scale=a.scale, head_scale=a.head_scale, neck_drop=a.neck_drop,
                             shoulder_fit=a.shoulder_fit, arm_drop=a.arm_drop, prims=prims, ctrl_policy='skinned')
    hs, hn, A_head = info['maps']['head']
    anc = {}
    for n in range(len(v.nodes)):
        anc[n] = v.node_human.get(n) or F.humanoid_ancestor(v, n)
    head_like = {'head', 'leftEye', 'rightEye', 'jaw'}
    for p in prims:
        P0 = gltf_to_got(p['P_pose'])
        N0 = gltf_to_got(p['N_pose']) / 100.0
        P = tps(P0)
        Jac = tps.jacobian(P0)
        hanc = np.vectorize(anc.get, otypes=[object])(p['joints'])
        fh = sum(np.where(np.isin(hanc[:, k], list(head_like)), p['weights'][:, k], 0) for k in range(p['joints'].shape[1]))
        P = fh[:, None] * (hn + (P0 - hs) @ A_head.T) + (1 - fh[:, None]) * P
        Jac = fh[:, None, None] * A_head + (1 - fh[:, None, None]) * Jac
        N = np.einsum('vji,vj->vi', np.linalg.inv(Jac), N0)
        p['P'] = got_to_gltf(P)
        p['N'] = got_to_gltf(N) * 100.0
        p['N'] /= np.linalg.norm(p['N'], axis=1, keepdims=True).clip(1e-12)
        p['hanc'] = hanc
    log('fitted')

    # ground: sole -> hero floor, spread over hip -> ankle on each leg
    floor = hero.floor()
    lifts = {}
    for side in ('left', 'right'):
        legs = {f'{side}{b}' for b in ('UpperLeg', 'LowerLeg', 'Foot', 'Toes')}
        feet = {f'{side}Foot', f'{side}Toes'}
        fr = lambda p, names_: sum(np.where(np.isin(p['hanc'][:, k], list(names_)), p['weights'][:, k], 0)
                                   for k in range(p['joints'].shape[1]))
        sole = min(p['P'][fr(p, feet) > 0.5, 1].min() for p in prims if (fr(p, feet) > 0.5).any())
        lift = floor - sole
        s = 'LF_' if side == 'left' else 'RT_'
        yk, ya = hero.pos(s + 'upleg')[1], hero.pos(s + 'foot')[1]
        for p in prims:
            m = fr(p, legs)
            ramp = np.clip((yk - p['P'][:, 1]) / (yk - ya), 0, 1)
            p['P'][:, 1] += lift * ramp * m
        lifts[side] = float(lift)
    log(f'floor {floor:.4f} m, lifts {lifts}')

    # 3. weights
    dj, dch = [], []
    if a.dyn:
        def place(n, P0):
            if anc[n] in head_like:
                return got_to_gltf(hn + (P0 - hs) @ A_head.T)
            return got_to_gltf(tps(P0[None])[0])
        dj, dch = dyn_joints(v, G, anc, place, hero)
        log(f'dynamics: {len(dch)} chains, {len(dj)} joints')
    dyn_map = {d['node']: len(hero.names) + i for i, d in enumerate(dj)}
    all_names = hero.names + [d['name'] for d in dj]
    all_par = [j['parent'] for j in hero.m.joints] + [all_names.index(d['parent_name']) for d in dj]
    sk = [p['P'][:, 1][np.array([v.names[j].startswith('Skirt') for j in p['joints'][np.arange(len(p['P'])), p['weights'].argmax(1)]])]
          for p in prims]
    sk = np.concatenate([x for x in sk if len(x)])
    SKIRT_Y = (float(sk.max()), float(sk.min()))
    skirt_nodes = [j for j, n in enumerate(v.names) if n.startswith('Skirt')]
    wm = make_weight_mapper(v, hero, anc, dyn_map)
    if not a.skirt_height:
        for p in prims:
            p['skirt_nodes'] = skirt_nodes
        src, n_src = skirt_transfer(prims, wm, len(hero.names) + len(dyn_map), [v.human[h] for h in SKIRT_SRC])
        n_sk = skirt_rows(prims, lambda P: src(P)[:, :len(hero.names)])
        wm = make_weight_mapper(v, hero, anc, dyn_map, skirt_src=True)
        log(f'skirt: {n_sk} vertices weighted from {n_src} hip / thigh vertices')
    parts = {}
    for p in prims:
        key = GROUPS[p['mat_name']]
        J, W = wm(p, p['P'])
        S = (np.isin(p['joints'], skirt_nodes) * p['weights']).sum(1)
        parts.setdefault(key, []).append(dict(P=p['P'], N=p['N'], UV=p['uv'], T=p['tris'], J=J, W=W, S=S, mesh=p['mesh']))
    merged = {}
    for key, lst in parts.items():
        off = 0
        acc = {k: [] for k in ('P', 'N', 'UV', 'T', 'J', 'W', 'S')}
        for q in lst:
            for k in ('P', 'N', 'UV', 'J', 'W', 'S'):
                acc[k].append(q[k])
            acc['T'].append(q['T'] + off)
            off += len(q['P'])
        merged[key] = {k: np.concatenate(v_) for k, v_ in acc.items()}
    np.savez_compressed(os.path.join(out, 'karin_geo.npz'),
                        **{f'{k}__{f}': arr for k, d in merged.items() for f, arr in d.items()},
                        **{'_meta__joint_names': np.array(all_names), '_meta__parents': np.array(all_par)},
                        **({'_dyn__world': np.array([d['world'] for d in dj]),
                            '_dyn__chains': np.array(json.dumps(dch))} if dj else {}))
    allP = np.concatenate([d['P'] for d in merged.values()])
    report = dict(target=a.target, model=mpath, vrm=os.path.basename(a.vrm), scale=a.scale, head_scale=a.head_scale,
                  neck_drop_cm=a.neck_drop, shoulder_fit=a.shoulder_fit, repose=rep, floor=floor, lifts=lifts,
                  skirt_y=SKIRT_Y, parts={k: dict(verts=len(d['P']), tris=len(d['T']) // 3) for k, d in merged.items()},
                  bbox=[allP.min(0).round(4).tolist(), allP.max(0).round(4).tolist()],
                  ring_r=info.get('ring_r'), dyn_chains=[(c['key'], len(c['joints'])) for c in dch])
    json.dump(report, open(os.path.join(out, 'karin_geo.json'), 'w'), indent=1, default=float)
    log(f'parts { {k: len(d["P"]) for k, d in merged.items()} } bbox {report["bbox"]}')


if __name__ == '__main__':
    main()
