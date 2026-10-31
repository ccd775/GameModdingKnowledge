"""Fit a VRM humanoid onto the Death Stranding 2 Sam bind skeleton (Porter body skeleton 50118:0; space in cm).

Copied from the HFW kit fit_hfw.py (itself adapted from the Ghost of Tsushima kit fit.py); only the bone names differ.
DS2 uses the same axes as HFW: x = model right, y = forward, z = up.

Geometry: smooth 3D thin-plate-spline warp driven by joint correspondences, bone-axis
samples and rings (so each bone keeps a similarity frame), rigid clusters for head/hands/feet
and for non-humanoid chains (hair, tail, skirt) through their humanoid ancestor.
"""
import numpy as np

# VRM humanoid -> DS2 Sam (skeleton 50118:0) joint name; set_skeleton() resolves them to indices
HUMAN2NAME = {
    'neck': 'JNT_C_B_006_Neck', 'head': 'JNT_C_B_008_Head',
    'leftShoulder': 'JNT_L_B_000_Shoulder', 'leftUpperArm': 'JNT_L_B_001_Arm', 'leftLowerArm': 'JNT_L_B_002_Arm',
    'leftHand': 'JNT_L_B_003_Hand',
    'rightShoulder': 'JNT_R_B_000_Shoulder', 'rightUpperArm': 'JNT_R_B_001_Arm', 'rightLowerArm': 'JNT_R_B_002_Arm',
    'rightHand': 'JNT_R_B_003_Hand',
    'leftUpperLeg': 'JNT_L_B_100_Leg', 'leftLowerLeg': 'JNT_L_B_101_Leg', 'leftFoot': 'JNT_L_B_102_Foot',
    'leftToes': 'JNT_L_B_103_Toe',
    'rightUpperLeg': 'JNT_R_B_100_Leg', 'rightLowerLeg': 'JNT_R_B_101_Leg', 'rightFoot': 'JNT_R_B_102_Foot',
    'rightToes': 'JNT_R_B_103_Toe',
}
for _s, _S in (('left', 'L'), ('right', 'R')):
    for _f, (_F, _n) in (('Thumb', ('Thumb', 5)), ('Index', ('Index', 4)), ('Middle', ('Middle', 3)),
                         ('Ring', ('Ring', 2)), ('Little', ('Pinky', 1))):
        _segs = ('Metacarpal', 'Proximal', 'Distal') if _f == 'Thumb' else ('Proximal', 'Intermediate', 'Distal')
        for _k, _seg in enumerate(_segs):
            HUMAN2NAME[f'{_s}{_f}{_seg}'] = f'JNT_{_S}_H_0{_n}{_k}_{_F}'
HUMAN2GOT = {}
FINGERS = ('Thumb', 'Index', 'Middle', 'Ring', 'Little')


def is_finger(h):
    return any(f in h for f in FINGERS)


def is_hand(h):
    """humanoid bone in a hand subtree (hand or finger)"""
    return h.endswith('Hand') or is_finger(h)


def set_skeleton(names):
    """Resolve HUMAN2NAME against the target skeleton bone names (fills HUMAN2GOT with indices)."""
    HUMAN2GOT.clear()
    idx = {n: i for i, n in enumerate(names)}
    for k, n in HUMAN2NAME.items():
        HUMAN2GOT[k] = idx[n]
    return HUMAN2GOT


# segments (bone -> child joint used as tail) for axis sampling
CHAINS = [
    ['hips', 'spine', 'chest', 'neck', 'head'],
    ['leftShoulder', 'leftUpperArm', 'leftLowerArm', 'leftHand'],
    ['rightShoulder', 'rightUpperArm', 'rightLowerArm', 'rightHand'],
    ['leftUpperLeg', 'leftLowerLeg', 'leftFoot', 'leftToes'],
    ['rightUpperLeg', 'rightLowerLeg', 'rightFoot', 'rightToes'],
]
for side in ('left', 'right'):
    for f in ('Thumb', 'Index', 'Middle', 'Ring', 'Little'):
        first = 'Metacarpal' if f == 'Thumb' else 'Proximal'
        mid = 'Proximal' if f == 'Thumb' else 'Intermediate'
        CHAINS.append([f'{side}Hand', f'{side}{f}{first}', f'{side}{f}{mid}', f'{side}{f}Distal'])


def gltf_to_got(p):
    """glTF (x = model left, y up, z fwd; metres) -> DS2 (x = model right, y fwd, z up) in cm."""
    p = np.asarray(p, dtype=np.float64)
    return np.stack([-p[..., 0], p[..., 2], p[..., 1]], -1) * 100.0


def rot_between(a, b):
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    v = np.cross(a, b)
    c = float(a @ b)
    if c < -0.999999:
        axis = np.cross(a, [1, 0, 0])
        if np.linalg.norm(axis) < 1e-6:
            axis = np.cross(a, [0, 1, 0])
        axis /= np.linalg.norm(axis)
        return 2 * np.outer(axis, axis) - np.eye(3)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx / (1 + c)


class TPS:
    def __init__(self, src, dst, reg=1e-3):
        self.src = src
        n = len(src)
        K = np.linalg.norm(src[:, None] - src[None], axis=2)
        K[np.diag_indices(n)] += reg
        P = np.concatenate([np.ones((n, 1)), src], 1)
        A = np.zeros((n + 4, n + 4))
        A[:n, :n] = K
        A[:n, n:] = P
        A[n:, :n] = P.T
        b = np.zeros((n + 4, 3))
        b[:n] = dst
        sol = np.linalg.solve(A, b)
        self.w = sol[:n]
        self.a = sol[n:]

    def __call__(self, x, chunk=4096):
        out = np.empty_like(x)
        for i in range(0, len(x), chunk):
            xx = x[i:i + chunk]
            K = np.linalg.norm(xx[:, None] - self.src[None], axis=2)
            out[i:i + chunk] = K @ self.w + np.concatenate([np.ones((len(xx), 1)), xx], 1) @ self.a
        return out

    def jacobian(self, x, eps=0.05):
        J = np.empty((len(x), 3, 3))
        for k in range(3):
            d = np.zeros(3)
            d[k] = eps
            J[:, :, k] = (self(x + d) - self(x - d)) / (2 * eps)
        return J


def palm_frame(wrist, knuckles):
    """Hand frame from the wrist and the index, middle, ring, little knuckles: x wrist -> middle knuckle,
    y index -> little knuckle (orthogonalised), z = x cross y. Also returns the palm length and knuckle span."""
    x = knuckles[1] - wrist
    length = np.linalg.norm(x)
    x = x / length
    y = knuckles[3] - knuckles[0]
    y = y - (y @ x) * x
    span = np.linalg.norm(y)
    y = y / span
    return np.stack([x, y, np.cross(x, y)], 1), length, span


def build_fit(vrm, got_world, scale=1.45, head_scale=None, ring_r=None, chest_share=0.0,
              neck_drop=5.0, shoulder_fit=0.0, arm_drop=5.0, own_feet=False, foot_scale=None, hands='tps'):
    """Return (src, dst, info): control points mapping Karin rest (GoT space, cm) -> fitted GoT bind space.

    Hip, knee, ankle, elbow, wrist and finger joints land on the hero joints. The pelvis keeps
    Karin's shape relative to her hip joints, the neck keeps her length with its base neck_drop cm
    below the hero neck joint (the hero head pivot then lies inside her larger head), the shoulders
    sit shoulder_fit of the way from her own width to the hero's, and the torso takes the rest.
    own_feet: the toes keep Karin's own (scaled) offset from the ankle instead of landing on the hero's
    toe joint, so the foot keeps its shape (the toe joint only bends the front of the sole); foot_scale
    (default scale) then sizes the whole foot uniformly about the ankle.
    hands='rigid': the hand map aligns the whole palm frame (roll included) and stretches the palm onto the
    hero's knuckles; each finger segment keeps that roll and turns onto its hero bone axis. The fingers get no
    TPS control points: the caller places hand vertices with these maps blended by skin weight.
    """
    head_scale = head_scale or scale
    J = got_world[:, :3, 3]
    kj = {k: gltf_to_got(vrm.world[n][:3, 3]) for k, n in vrm.human.items()}
    tgt = {}
    for k, gi in HUMAN2GOT.items():
        if k in kj:
            tgt[k] = J[gi].copy()

    def own(bone, ref):
        """bone placed at Karin's own (scaled) offset from an already fitted joint"""
        return tgt[ref] + scale * (kj[bone] - kj[ref])

    hip_k = (kj['leftUpperLeg'] + kj['rightUpperLeg']) / 2
    hip_t = (tgt['leftUpperLeg'] + tgt['rightUpperLeg']) / 2
    tgt['hips'] = hip_t + scale * (kj['hips'] - hip_k)
    tgt['neck'] = J[HUMAN2GOT['neck']] - np.array([0, 0, neck_drop])
    tgt['head'] = own('head', 'neck')
    foot_scale = scale if foot_scale is None else foot_scale
    if own_feet:
        for side in ('left', 'right'):
            f, t = f'{side}Foot', f'{side}Toes'
            tgt[t] = tgt[f] + foot_scale * (kj[t] - kj[f])
    for side in ('left', 'right'):
        for b in (f'{side}Shoulder', f'{side}UpperArm'):
            if b not in kj:   # shoulders are optional VRM bones
                continue
            o = own(b, 'neck')
            # only the arm root moves toward the hero (HFW clavicles sat across the midline; kept for DS2)
            tgt[b] = o if b.endswith('Shoulder') else o + shoulder_fit * (J[HUMAN2GOT[b]] - o)
            if b.endswith('UpperArm'):
                # arm root below the hero pivot: when the arm hangs it swings in toward the body
                tgt[b] = tgt[b] - np.array([0, 0, arm_drop])
    # spine / chest: Karin's torso frame stretched along hips -> neck
    a_s = kj['neck'] - kj['hips']
    a_n = tgt['neck'] - tgt['hips']
    R_t = rot_between(a_s, a_n)

    def torso(bone, f):
        local = kj[bone] - kj['hips']
        perp = local - (local @ a_s) / (a_s @ a_s) * a_s
        return tgt['hips'] + f * a_n + scale * (R_t @ perp)

    f_sp = (kj['spine'] - kj['hips']) @ a_s / (a_s @ a_s)
    f_ch_uniform = (kj['chest'] - kj['hips']) @ a_s / (a_s @ a_s)
    # chest_share: 0 -> uniform stretch, 1 -> chest segment keeps source length*scale
    # (axial part only: the chest's sideways offset is carried unstretched by torso())
    f_ch_keep = 1 - scale * ((kj['neck'] - kj['chest']) @ a_s) / (np.linalg.norm(a_s) * np.linalg.norm(a_n))
    f_ch = (1 - chest_share) * f_ch_uniform + chest_share * max(f_ch_keep, f_ch_uniform)
    tgt['spine'] = torso('spine', f_sp)
    tgt['chest'] = torso('chest', f_ch)

    src_pts, dst_pts = [], []

    def frame_map(bone, tail_bone, s_perp, pre=None):
        """similarity-ish map of a bone: rotation aligning axis, along-axis stretch.
        pre: rotation applied first (the hand roll for fingers), the axis is then aligned from there."""
        hs, ts = kj[bone], kj[tail_bone]
        hn, tn = tgt[bone], tgt[tail_bone]
        a_s = ts - hs
        a_n = tn - hn
        R = rot_between(a_s, a_n) if pre is None else rot_between(pre @ a_s, a_n) @ pre
        k = np.linalg.norm(a_n) / (np.linalg.norm(a_s) * s_perp)
        an = a_n / np.linalg.norm(a_n)
        A = (np.eye(3) + (k - 1) * np.outer(an, an)) @ R * s_perp
        return hs, hn, A

    def rigid_map(bone, s, R=None):
        hs = kj[bone]
        hn = tgt[bone]
        R = np.eye(3) if R is None else R
        return hs, hn, R * s

    maps = {}
    for chain in CHAINS:
        for b, c in zip(chain, chain[1:]):
            if b not in kj or c not in kj or b not in tgt or c not in tgt:
                continue
            if b in maps and b.endswith('Hand'):
                continue
            maps[b] = frame_map(b, c, foot_scale if own_feet and b.endswith('Foot') else scale)
    # terminal / rigid bones
    maps['head'] = rigid_map('head', head_scale)
    for side in ('left', 'right'):
        maps[f'{side}Toes'] = (kj[f'{side}Toes'], tgt[f'{side}Toes'], maps[f'{side}Foot'][2])
        hand = f'{side}Hand'
        if hands == 'rigid':
            # palm frame to palm frame; length and knuckle span land on the hero's knuckles, thickness at scale
            knuckles = [f'{side}{f}Proximal' for f in ('Index', 'Middle', 'Ring', 'Little')]
            FK, lk, wk = palm_frame(kj[hand], [kj[b] for b in knuckles])
            FB, lb, wb = palm_frame(tgt[hand], [tgt[b] for b in knuckles])
            R_h = FB @ FK.T
            maps[hand] = (kj[hand], tgt[hand], FB @ np.diag([lb / lk, wb / wk, scale]) @ FK.T)
            for f in ('Thumb', 'Index', 'Middle', 'Ring', 'Little'):
                segs = ('Metacarpal', 'Proximal', 'Distal') if f == 'Thumb' else ('Proximal', 'Intermediate', 'Distal')
                for b, c in zip(segs, segs[1:]):
                    if f'{side}{f}{b}' in kj and f'{side}{f}{c}' in kj:
                        maps[f'{side}{f}{b}'] = frame_map(f'{side}{f}{b}', f'{side}{f}{c}', scale, pre=R_h)
        else:
            # hand: orient by middle finger direction, no stretch
            hs, hn, _ = frame_map(hand, f'{side}MiddleProximal', scale)
            a_s = kj[f'{side}MiddleProximal'] - hs
            a_n = tgt[f'{side}MiddleProximal'] - hn
            maps[hand] = (hs, hn, rot_between(a_s, a_n) * scale)
        for f in ('Thumb', 'Index', 'Middle', 'Ring', 'Little'):
            dist = f'{side}{f}Distal'
            prev = f'{side}{f}Intermediate' if f != 'Thumb' else f'{side}ThumbProximal'
            if dist in kj and prev in maps:
                maps[dist] = (kj[dist], tgt[dist], maps[prev][2])
    maps['hips'] = (kj['hips'], tgt['hips'], np.eye(3) * scale)

    def apply(m, p):
        hs, hn, A = m
        return hn + (p - hs) @ A.T

    ring_r = ring_r or {}
    # axis samples + rings
    for b, m in maps.items():
        if hands == 'rigid' and is_finger(b):
            continue
        hs, hn, A = m
        tail = None
        for chain in CHAINS:
            if b in chain and chain.index(b) + 1 < len(chain):
                tail = chain[chain.index(b) + 1]
                break
        if b in ('head',) or tail is None or b.endswith('Hand') or b.endswith('Toes') or b.endswith('Distal'):
            # rigid cluster: small cube around head joint
            r = ring_r.get(b, 2.0)
            pts = [hs] + [hs + r * np.array(d) for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
            for p in pts:
                src_pts.append(p)
                dst_pts.append(apply(m, p))
            continue
        ts = kj[tail]
        L = np.linalg.norm(ts - hs)
        a = (ts - hs) / L
        u = np.cross(a, [0, 0, 1.0])
        if np.linalg.norm(u) < 1e-3:
            u = np.cross(a, [1.0, 0, 0])
        u /= np.linalg.norm(u)
        v = np.cross(a, u)
        r = ring_r.get(b, 0.35 * L if L > 3 else 1.0)
        nt = 4 if L > 6 else 2
        for t in np.linspace(0, 1, nt + 1)[:-1]:
            c = hs + t * L * a
            src_pts.append(c)
            dst_pts.append(apply(m, c))
            for ang in np.linspace(0, 2 * np.pi, 7)[:-1]:
                p = c + r * (np.cos(ang) * u + np.sin(ang) * v)
                src_pts.append(p)
                dst_pts.append(apply(m, p))
    info = dict(kj=kj, tgt=tgt, maps=maps, apply=apply)
    return np.array(src_pts), np.array(dst_pts), info


def humanoid_ancestor(vrm, node):
    while node >= 0 and node not in vrm.node_human:
        node = vrm.parent[node]
    return vrm.node_human.get(node)


def limb_radii(vrm, prims, pct=30):
    """Ring radius per limb bone (source cm): a low percentile of the radial distance of the vertices the
    bone dominates. Rings at 0.35 * bone length reach into the other leg or the chest, where the two
    limbs' different maps fight and stretch both limbs sideways."""
    kj = {k: gltf_to_got(vrm.world[n][:3, 3]) for k, n in vrm.human.items()}
    P = np.concatenate([gltf_to_got(p['pos']) for p in prims])
    dom = np.concatenate([p['joints'][np.arange(len(p['pos'])), p['weights'].argmax(1)] for p in prims])
    out = {}
    for chain in CHAINS[:5]:   # torso, arms, legs; short finger segments keep their 1 cm rings
        for b, c in zip(chain, chain[1:]):
            if b not in kj or c not in kj or b in out or b == 'head' or b.endswith(('Hand', 'Toes', 'Distal')):
                continue
            a = kj[c] - kj[b]
            L = np.linalg.norm(a)
            if L <= 3:
                continue
            a = a / L
            rel = P[dom == vrm.human[b]] - kj[b]
            t = rel @ a
            r = np.linalg.norm(rel - np.outer(t, a), axis=1)[(t >= 0) & (t <= L)]
            if len(r) >= 12:
                out[b] = float(min(np.percentile(r, pct), 0.35 * L))
    return out


def build_warp(vrm, got_world, scale=1.45, head_scale=None, chest_share=0.0, reg=1e-2, *, neck_drop=5.0,
               shoulder_fit=0.0, arm_drop=5.0, prims=None, radius_prims=None, ctrl_policy='all', own_feet=False,
               foot_scale=None, hands='tps'):
    """TPS warp (Karin GoT-space cm -> fitted hero bind space) plus fit info.
    prims (VRM primitives) set the limb ring radii at the skin (radius_prims, when given, instead); without
    them rings use 0.35 * bone length.
    ctrl_policy picks the non-humanoid nodes that become control points (mapped by their humanoid ancestor):
      'all'     every node (models with a clean armature);
      'skinned' only nodes that skin a vertex of prims (merged outfit armatures carry unused copies of the
                arm bones under the chest), no head-subtree node below the neck (hair and cables hanging by
                the legs follow the head rigidly and would drag the body), and torso-subtree nodes below the
                hip joint (jacket hem) follow the hips map rather than the spine extrapolated downwards.
    hands: see build_fit; 'rigid' also leaves the nodes below the fingers out of the control points."""
    ring_prims = radius_prims if radius_prims is not None else prims
    ring_r = limb_radii(vrm, ring_prims) if ring_prims else None
    src, dst, info = build_fit(vrm, got_world, scale=scale, head_scale=head_scale, ring_r=ring_r,
                               chest_share=chest_share, neck_drop=neck_drop, shoulder_fit=shoulder_fit,
                               arm_drop=arm_drop, own_feet=own_feet, foot_scale=foot_scale, hands=hands)
    info['ring_r'] = ring_r
    if ctrl_policy not in ('all', 'skinned'):
        raise ValueError(f'unknown ctrl_policy {ctrl_policy}')
    skinned = None
    if ctrl_policy == 'skinned':
        skinned = set()
        for p in prims:
            skinned.update(np.unique(p['joints'][p['weights'] > 0]).tolist())
    kj = info['kj']
    extra_s, extra_d = [], []
    for n in range(len(vrm.nodes)):
        if n in vrm.node_human:
            continue
        if skinned is not None and n not in skinned:
            continue
        h = humanoid_ancestor(vrm, n)
        if h is None:
            continue
        p = gltf_to_got(vrm.world[n][:3, 3])
        if skinned is not None:
            if h == 'head' and p[2] < kj['neck'][2]:
                continue
            if h in ('spine', 'chest', 'upperChest') and p[2] < kj['leftUpperLeg'][2]:
                h = 'hips'
        if h not in info['maps'] or (hands == 'rigid' and is_finger(h)):
            continue
        extra_s.append(p)
        extra_d.append(info['apply'](info['maps'][h], p))
    if extra_s:
        src = np.concatenate([src, extra_s])
        dst = np.concatenate([dst, extra_d])
    keep = []
    for i, p in enumerate(src):
        if all(np.linalg.norm(p - src[k]) > 0.8 for k in keep[-400:]):
            keep.append(i)
    info['ctrl_src'] = src[keep]
    info['ctrl_dst'] = dst[keep]
    return TPS(src[keep], dst[keep], reg=reg), info
