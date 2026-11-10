"""Build the Karin 3DMigoto mod for Nioh 2 (Mod Enabler) from the conformed Karin and the frame-dump skeleton.

Host A  = right gauntlet draw (last body-armour draw of the main pass): body, costume, hair, ears, tail, drawn with a
          merged bone palette assembled each frame by a compute shader from the armour pieces' own bone palettes.
Host B  = vanilla face draw: Karin's face with the face draw's own palette (face bones -> game expressions).
Every original character draw is skipped (main pass and shadow passes).

usage: n2_build.py <work dir> <out mod dir> [--texconv <texconv.exe>]
work dir: build1/conformed.npz, data/bones3.json, data/joints.json, fa3 dump, source/, asm/
texconv: --texconv, else N2_TEXCONV, else <work dir>/texconv/texconv.exe
"""
import glob
import json
import os
import shutil
import struct
import subprocess
import sys

import numpy as np
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fa_mesh import load_draw  # noqa: E402
from bones import skin_arrays  # noqa: E402

TEXCONV = os.environ.get('N2_TEXCONV')   # main() falls back to <work dir>/texconv/texconv.exe
FA = 'fa3/FrameAnalysis-2026-11-07-205515'
MOD = 'KarinN2'
ALBEDO_SCALE = {'face': 0.65, 'body': 0.65, 'hair': 0.55, 'costume': 0.55}

# ---------------------------------------------------------------- game draws (fa3, equipment screen, Hayabusa set)
SOURCES = [  # (name, ib hash, fa3 draw) in main-pass draw order; the host must be last
    ('greaveL', 'f8e46d5e', 15), ('gauntL', 'b7ed5500', 16), ('hakama', '39df894a', 19), ('chest', '091c8de0', 21),
    ('scarfL', '3acd6cdf', 22), ('scarfR', '6f1d0023', 24), ('greaveR', 'ee8051c8', 29), ('gauntR', '0814c08f', 31)]
HOST_A = ('gauntR', '0814c08f', 31)
HOST_B = ('face', '834bff26', 39)
HIDE_IBS = {  # every vanilla character draw: armour, skin, face parts, eyes, mouth, hair
    'f8e46d5e', 'b7ed5500', 'a8ccaf54', '39df894a', '091c8de0', '3acd6cdf', '738d7a83', '6f1d0023', '9a736db9',
    'ee8051c8', '0814c08f', '8f7dccdc', '9524b452', 'f1e0f02c', 'ea019727', 'b366539d', 'caa99e18', 'c8ad97ea',
    'dcaa40bf', '834bff26', 'c90201e4', '1c0f2460', '3682084f', '4f25fad6', '85f441d8', '0ea0fd7c', 'ab2f3eb8',
    '5c283c8e', '60e07fc9', 'f4cdcdfc', '2592092d', '2b62f2e3', '1a241f17', '0ccbe728', 'c4f93dc9', 'c0ff01f2',
    '4ba966a5',
    '07e1d521', 'eeded2d0',                              # Hayabusa Plated Headband (helmet + face mask)
    '0d1604b3', 'c5bf613a', '87a00936', 'b1162e31',      # rigid armour pieces (VS d637f756): knee guards etc.
    'c03cb62d', 'dfeb63e0'}                              # the two cloth flaps hanging at the crotch (cloth VS 24f9a3d0)
PS_HASHES = [  # pixel shaders of the character's own mesh draws only. Full-screen passes (VS f8978790 etc.) inherit a
    # stale index buffer (seen: the ponytail ib), so hooking them would skip post-processing (build1: black screen)
    'd0e492840a2b7911', '2b4f1e31175e9cbc', '1c66ca69cf2a610c', 'b2f60a9e522cd98f', 'd2bf49c8ea14806d',
    'b28794540ed533bc', '350aaed214d440c4', '4687106fff835666', '65c8c4905227d570', 'eec27fd8b62a555b',
    '7ec4d7cd2e0f82ca']
VS_HASHES = ['24f9a3d0d0d9c367']   # cloth-flap VS (also hooked by the community 'Basewear No Flap' mod); its PS
# (7bfcb1a8) is not one of the character PS above
SHADOW_VS = ['cefcd0d8bb9cb78b', 'e91b4a26b8c1704e']   # their PS are hooked by the enabler (CommandListN2Shadows)
# shadow VS cb0 layouts: (bone row 0, flag rows, total rows). VS1: mW2P 0-3, mL2W from 4, bSkin 388-390;
# VS2: vLit 0, mW2P 1-4, mL2W from 5, bSkin 389-391
SHADOW_LAYOUT = {1: (4, (388, 391), 391), 2: (5, (389, 392), 392)}

# skirt: weights copied from the body surface underneath (body_2 skin + underwear), blended toward the hem with the
# thigh on that side, so the waist moves exactly like the skin it covers and the lower skirt is carried by the thighs
# (a lifted knee lifts the front panel instead of passing through it). Offline-checked on synthetic leg swings up to
# 75 deg forward / 45 deg back / 30 deg sideways, crouch, and captured in-game spine twists: no skin outside the skirt.
# Build 2 used the hakama flap bones for the front panels and pelvis-only tops: the flaps sag at idle and the waist
# skin follows the spine, so hips poked through in levels; a pure skin copy (build 3a) let a running thigh poke through.
SKIRT_SRC = ('body_2', 'underwear')
SKIRT_TOKENS = {'g0', 'g1', 'g2', 'g11', 'g13', 'g9', 'g10', 'g12', 'g19', 'g17', 'g18'}   # pelvis, spine, chest, legs
SKIRT_K, SKIRT_SIGMA, SKIRT_SMOOTH = 128, 1.0, 3   # skin copy: nearest body vertices, Gaussian width (cm), smoothing
SKIRT_THIGH = ('g11', 'g12')                       # upper thigh L / R
SKIRT_Y_TOP, SKIRT_Y_HEM, SKIRT_THIGH_MAX = 112.0, 80.0, 0.85   # thigh share: 0 above Y_TOP, rising to MAX at Y_HEM
SKIRT_LR_CM = 6.0                                  # front / back centre: L-R thigh split blended over +-6 cm

# own spring-chain physics (sim_a.hlsl, once per frame): twin tails, fox tail, ears. Each chain hangs from an anchor
# token; joints run root -> tip in Karin's conformed game space, the root rides the anchor, the rest are particles with
# fixed segment lengths (no stretching). (key, mesh, anchor, joints, vertex group -> segment, stiffness root/tip
# (pull toward the rigid pose per frame), velocity kept per frame, inertia (share of the anchor's own motion that the
# particles lag behind; 0 = carried along rigidly), gravity cm/s^2, colliders). Offline-tuned (simtest.py): twin tails
# swing ~16 deg running / 11 deg turning / 26 deg on a dodge. Fox tail (build 5, softer: build 4's 0.15/0.08/0.85/0.5
# looked rigid in game): tip ~15 deg running with hip sway / 12 on a stop / 44 on a 120 deg turn (b4: 3 / 2 / 14),
# idle droop 2 cm, no contact with the thigh capsules (simcheck/tailtune.py). Ears (two segments, soft and bouncy;
# eartest3.py with in-game-like eased stops / turns / lunges): ~20 deg running, 18 deg on a stop then 3 rebounds,
# 10 deg on a 120 deg turn, 27 deg on a lunge then 5 rebounds. (Build 3a's 0.22/0.15/0.92/0.35 barely moved in game.)
SIDE_HAIR_K, SIDE_HAIR_DAMP, SIDE_HAIR_INERTIA = (0.30, 0.20), 0.88, 0.4
SKIRT_SIM_K, SKIRT_SIM_DAMP, SKIRT_SIM_INERTIA = (0.25, 0.15), 0.85, 0.5
_TL = ['Hair_tail_L_001', 'Hair_tail_L_002', 'Hair_tail_L_003', 'Hair_tail_L_004', 'Hair_tail_L_005']
_TR = [n.replace('_L_', '_R_') for n in _TL]
SIM_CHAINS = [
    ('TL', 'hair', 'g8', _TL + ['Hair_tail_L_005_end'], {g: i for i, g in enumerate(_TL)},
     (0.12, 0.06), 0.88, 0.5, 300.0, ('head', 'chest', 'pelvis')),
    ('TR', 'hair', 'g8', _TR + ['Hair_tail_L_005_end_1'], {**{g: i for i, g in enumerate(_TR)}, 'Hair_tail_L_005_end_1': 4},
     (0.12, 0.06), 0.88, 0.5, 300.0, ('head', 'chest', 'pelvis')),
    ('TA', 'tail', 'g0', ['Tail', 'Tail_001', 'Tail_002', 'Tail_003', 'Tail_004', 'Tail_005', 'Tail_005_end'],
     {'Tail': 0, 'Tail_001': 1, 'Tail_002': 2, 'Tail_003': 3, 'Tail_004': 4, 'Tail_005': 5},
     (0.04, 0.02), 0.95, 0.8, 180.0, ('pelvis', 'butt', 'thighL', 'thighR')),
    ('EL', 'kemomimi', 'g8', ['Ear_L', 'Ear_L_001', 'Ear_L_001_end'], {'Ear_L': 0, 'Ear_L_001': 1},
     (0.16, 0.08), 0.95, 0.6, 0.0, ()),
    ('ER', 'kemomimi', 'g8', ['Ear_R', 'Ear_R_001', 'Ear_R_001_end'], {'Ear_R': 0, 'Ear_R_001': 1},
     (0.16, 0.08), 0.95, 0.6, 0.0, ()),
]
# side locks framing the face: three segments each, a little sway. Skirt and side locks offline-tested with a
# Python port of sim_a.hlsl (tools/simcheck/: eased run with 70 / 30 deg strides, stop, 120 deg turn, sideways dodge):
# skirt hem ~13 deg running / 5 on a stop / 13 on a turn or dodge, side locks ~6 / 5 / 3 / 11, no skin through the
# skirt (<= 0.1 cm on a few vertices during a dodge).
for _s in 'LR':
    _h = [f'Hair_side_{_s}', f'Hair_side_{_s}_001', f'Hair_side_{_s}_002']
    SIM_CHAINS.append((f'H{_s}', 'hair', 'g8', _h + [f'Hair_side_{_s}_002_end'], {g: i for i, g in enumerate(_h)},
                       SIDE_HAIR_K, SIDE_HAIR_DAMP, SIDE_HAIR_INERTIA, 300.0, ('head', 'jaw', 'chest')))
# skirt: Karin's 16 skirt chains, lower two segments simulated (_001 joint = pivot). Anchor 'field': every joint rides
# the blend of bones the skirt weight field gives at that joint (body at the waist, more thigh toward the hem), so the
# undisturbed skirt is exactly the no-poke skinning of build 3; the springs only add lag / swing on top. The top
# segment (waist to _001) keeps the field weights.
SKIRT_CHAINS = ['Skirt_0'] + [f'Skirt_{i}_{s}' for i in range(1, 8) for s in 'LR'] + ['Skirt_8']
for _n in SKIRT_CHAINS:
    SIM_CHAINS.append((f'K{_n[6:]}', 'skirt', 'field', [_n + '_001', _n + '_002', _n + '_002_end'],
                       {_n + '_001': 0, _n + '_002': 1}, SKIRT_SIM_K, SKIRT_SIM_DAMP, SKIRT_SIM_INERTIA, 300.0,
                       ('pelvis', 'hips', 'butt', 'thighL', 'thighR')))
SIM_DEFAULT = {'hair': 'g8', 'tail': 'g0', 'kemomimi': 'g8', 'skirt': 'field'}   # token of the other groups of those meshes
# colliders: (token, (joint, offset cm), (joint, offset cm) or None = sphere, radius cm). Joints: Karin's conformed joints,
# or game joints from data/joints.json. Radii are shrunk to 90 % of the nearest rest particle of a chain that uses them.
SIM_COLLIDERS = {'head': ('g8', ('Head', (0.0, 8.5, 0.5)), None, 12.0),
                 'jaw': ('g8', ('Head', (0.0, -0.5, 3.0)), None, 7.5),
                 'chest': ('g2', ('Chest', (0.0, 9.0, -1.0)), None, 14.0),
                 'pelvis': ('g0', ('Hips', (0.0, -5.0, -1.0)), None, 14.0),
                 'hips': ('g0', ('Hips', (-8.0, -19.0, 0.0)), ('Hips', (8.0, -19.0, 0.0)), 12.0),
                 'butt': ('g0', ('Hips', (0.0, -19.0, -5.0)), None, 12.0),
                 'thighL': ('g11', ('hip_L', (0.0, 0.0, 0.0)), ('knee_L', (0.0, 0.0, 0.0)), 11.0),
                 'thighR': ('g12', ('hip_R', (0.0, 0.0, 0.0)), ('knee_R', (0.0, 0.0, 0.0)), 11.0)}
SIM_FPS = 60.0
# per chain-key prefix: max lag per frame (cm; caps how far a dodge / roll can leave a chain behind, running at
# 450 cm/s lags ~3.7 cm/frame at inertia 0.5) and max deviation of a segment from its rest direction (deg)
SIM_LIMITS = {'T': (5.0, 70.0), 'TA': (8.0, 70.0), 'E': (4.0, 45.0), 'H': (3.0, 35.0), 'K': (1.8, 40.0)}  # full key wins
# host A draws the meshes with simulated bones with a second merged palette (u8 blend indices: <= 85 bones each)
PAL_B_MESHES = ('hair', 'kemomimi', 'tail', 'skirt')


def sim_tokens():
    """(mesh, Karin group) -> sim token, and the token list of each chain ('s<n>', numbered in chain order)."""
    n, group_tok, chain_toks = 0, {}, []
    for key, mesh, anchor, joints, groups, *_ in SIM_CHAINS:
        toks = [f's{n + i}' for i in range(len(joints) - 1)]
        n += len(toks)
        chain_toks.append(toks)
        for g, seg in groups.items():
            group_tok[(mesh, g)] = toks[seg]
    return group_tok, chain_toks

# cb0 layout of the main skinned VS (73278b6e): 5 header rows, mL2W from row 5 (current, then previous-frame), flags
CB_ROWS, CB_BONE0, CB_LEN_ROW = 781, 5, 780
# face draw palette: upper-lid entries (vertex-weighted centroids above the eye centre, L even / R odd)
UPPER_LID = {2, 3, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 30, 31, 32, 33, 34, 35, 36, 37}
LID_TRAVEL, LID_MAX = 1.3, 4.0          # LID_MODE 'bones' only: weight amplification (build 1d; lids only half close)
LID_MODE = 'shape'                      # 'shape': blink shape key driven by the lid bones in blink_b.hlsl
# blink bones per side (+1 = character's left, +X). Measured in-game (palette ring capture, 2026-11-09): entries 24/25 drop
# 1.6 cm at their vanilla centroid in a full blink (rest -0.03); 32/33 and 34/35 follow the same curve; 16/17 never move.
LID_REF = {24: 1, 25: -1}
LID_FULL_CM = 1.4                       # lid-bone drop (cm, head space, at the entry's vanilla centroid) = fully closed
LID_DEAD_CM = 0.08                      # drop ignored as rest-pose noise
FACE_VS = '7439d16e62ebca1f'            # face main-pass VS (cb0: 5 header rows + 128 x 3 palette rows)


def f16(a):
    return np.asarray(a, np.float32).astype(np.float16)


def tangents(P, N, UV, tris):
    """per-vertex tangent along -dP/dv, w = sign so that w*cross(N,T) is along -dP/du (Nioh convention)."""
    p0, p1, p2 = P[tris[:, 0]], P[tris[:, 1]], P[tris[:, 2]]
    u0, u1, u2 = UV[tris[:, 0]], UV[tris[:, 1]], UV[tris[:, 2]]
    e1, e2 = p1 - p0, p2 - p0
    d1, d2 = u1 - u0, u2 - u0
    det = d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]
    det = np.where(np.abs(det) < 1e-12, 1e-12, det)
    dpdu = (e1 * d2[:, 1:2] - e2 * d1[:, 1:2]) / det[:, None]
    dpdv = (e2 * d1[:, 0:1] - e1 * d2[:, 0:1]) / det[:, None]
    T = np.zeros_like(P); Bu = np.zeros_like(P)
    for c in range(3):
        np.add.at(T, tris[:, c], -dpdv)
        np.add.at(Bu, tris[:, c], -dpdu)
    T = T - N * np.sum(T * N, 1, keepdims=True)
    ln = np.linalg.norm(T, axis=1)
    bad = ln < 1e-9
    T[bad] = np.cross(N[bad], [0, 1, 0.001])
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-12)
    w = np.sign(np.sum(np.cross(N, T) * Bu, 1)); w[w == 0] = 1
    return T, w


def unweld(P, N, UV, lv, tris):
    """Karin data is per-loop for normals/uvs: make one vertex per distinct (vertex, normal, uv)."""
    key = np.concatenate([lv[:, None].astype(np.float64), np.round(N, 4), np.round(UV, 5)], 1)
    uniq, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.reshape(-1)
    first = np.zeros(len(uniq), np.int64)
    first[inv[::-1]] = np.arange(len(inv))[::-1]
    return lv[first], N[first], UV[first], inv[tris.reshape(-1)].reshape(-1, 3) if tris is not None else None


def pack_weights(d, k):
    items = sorted(((b, w) for b, w in d.items() if abs(w) > 1e-4), key=lambda x: -abs(x[1]))[:k]
    tot = sum(w for _, w in items)
    ws = [w / tot for _, w in items]
    # f16 quantisation keeping the implicit last weight exact
    q = [float(np.float16(w)) for w in ws]
    if len(q) > 1:
        q[-1] = 1.0 - sum(q[:-1])
    ids = [b for b, _ in items] + [items[0][0]] * (k - len(items))
    q += [0.0] * (k - len(q))
    return ids, q


class Game:
    def __init__(self, work):
        self.fa = {d['draw']: d for d in json.load(open(os.path.join(work, 'fa3', 'fa3.json')))}
        self.B = json.load(open(os.path.join(work, 'data', 'bones3.json')))
        self.M = {g: np.vstack([np.array(m), [0, 0, 0, 1]]) for g, m in enumerate(self.B['mats'])}
        self.work = work

    def entries(self, draw):
        return {int(e): v['gid'] for e, v in self.B['draws'][str(draw)]['entries'].items()}

    def mesh(self, draw):
        return load_draw(os.path.join(self.work, FA), self.fa[draw])


# ---------------------------------------------------------------- weights for the chains and the skirt
def mesh_neighbours(nv, tris):
    nb = [set() for _ in range(nv)]
    for t in tris:
        for i in range(3):
            nb[t[i]].update((t[(i + 1) % 3], t[(i + 2) % 3]))
    return [np.array(sorted(x), np.int64) for x in nb]


def skirt_from_body(meta, arr, conf, P, tris):
    """Skirt vertex weights: copy of the body surface underneath (SKIRT_SRC meshes, vertices weighted only to
    SKIRT_TOKENS; Gaussian over the nearest SKIRT_K body vertices), blended with the thigh on that side by a share
    rising from 0 at SKIRT_Y_TOP to SKIRT_THIGH_MAX at SKIRT_Y_HEM, then smoothed over the skirt mesh.
    Returns [dict token -> w] per skirt vertex (top 4)."""
    pts, ws = [], []
    for m in meta['meshes']:
        if m['name'] not in SKIRT_SRC:
            continue
        k = m['key']
        Pb = conf[k + '__pos'].astype(float)
        for i, x in enumerate(conf[k + '__gw']):
            d = json.loads(x)
            if 60 < Pb[i, 1] < 130 and set(d) <= SKIRT_TOKENS:
                pts.append(Pb[i]); ws.append(d)
    toks = sorted({t for d in ws for t in d} | set(SKIRT_THIGH), key=lambda t: int(t[1:]))
    ti = {t: j for j, t in enumerate(toks)}
    Wsrc = np.zeros((len(ws), len(toks)))
    for i, d in enumerate(ws):
        s = sum(d.values())
        for t, w in d.items():
            Wsrc[i, ti[t]] = w / s
    dist, idx = cKDTree(np.array(pts)).query(P, SKIRT_K)
    a = np.exp(-((dist - dist[:, :1]) / SKIRT_SIGMA) ** 2)
    W = np.einsum('vk,vkt->vt', a, Wsrc[idx]) / a.sum(1, keepdims=True)
    lam = SKIRT_THIGH_MAX * np.clip((SKIRT_Y_TOP - P[:, 1]) / (SKIRT_Y_TOP - SKIRT_Y_HEM), 0, 1)
    sl = np.clip(0.5 + 0.5 * P[:, 0] / SKIRT_LR_CM, 0, 1); sl = sl * sl * (3 - 2 * sl)   # +X = character's left
    Wt = np.zeros_like(W); Wt[:, ti[SKIRT_THIGH[0]]] = sl; Wt[:, ti[SKIRT_THIGH[1]]] = 1 - sl
    W = (1 - lam[:, None]) * W + lam[:, None] * Wt
    nb = mesh_neighbours(len(P), tris)
    for _ in range(SKIRT_SMOOTH):
        W = 0.5 * W + 0.5 * np.array([W[n].mean(0) if len(n) else W[v] for v, n in enumerate(nb)])
    out = []
    for v in range(len(P)):
        order = np.argsort(-W[v])[:4]
        out.append({toks[j]: float(W[v, j]) for j in order if W[v, j] > 1e-3})
    return out


def retarget_hair_and_skirt(meta, arr, conf):
    """Hair / tail / ears: groups of a SIM_CHAINS chain -> its simulated bones, everything else the mesh's SIM_DEFAULT
    (head or pelvis). Skirt: weights of the body underneath (skirt_from_body).
    Returns {mesh name: [dict token->w]}."""
    out = {}
    group_tok, _ = sim_tokens()
    for m in meta['meshes']:
        k = m['key']
        if m['name'] not in SIM_DEFAULT:
            continue
        field = None
        if m['name'] == 'skirt':
            Pk = conf[k + '__pos'].astype(float)
            field = skirt_from_body(meta, arr, conf, Pk, arr[k + '__loop_vertex'][arr[k + '__tris']])
            SKIRT_FIELD.update(pos=Pk, w=field)
        groups = m['groups']; nv = len(arr[k + '__co'])
        W = np.zeros((nv, len(groups)))
        W[arr[k + '__w_vertex'], arr[k + '__w_group']] = arr[k + '__w_weight']
        W /= W.sum(1, keepdims=True)
        gw = [dict() for _ in range(nv)]
        for gi, g in enumerate(groups):
            tok = group_tok.get((m['name'], g), SIM_DEFAULT[m['name']])
            for v in np.nonzero(W[:, gi])[0]:
                for t, f in (field[v].items() if tok == 'field' else ((tok, 1.0),)):
                    gw[v][t] = gw[v].get(t, 0) + W[v, gi] * f
        out[m['name']] = gw
    return out


SKIRT_FIELD = {}     # skirt vertex positions + field weights (skirt_from_body), for the skirt chains' joint frames


def joint_weights(anchor, p):
    """bone blend that carries a chain joint at conformed position p: the anchor token, or for 'field' the skirt weight
    field at the nearest skirt vertex (top 4)."""
    if anchor != 'field':
        return {anchor: 1.0}
    v = int(np.argmin(np.linalg.norm(SKIRT_FIELD['pos'] - p, axis=1)))
    items = sorted(SKIRT_FIELD['w'][v].items(), key=lambda x: -x[1])[:4]
    s = sum(w for _, w in items)
    return {t: w / s for t, w in items}


_CONF_JOINTS = {}


# ---------------------------------------------------------------- face transfer
def face_landmarks_karin(P):
    """eye surfaces, nose tip, mouth, chin of the conformed Karin face mesh (game space)."""
    eyes = []
    for sx in (1, -1):
        m = (np.abs(P[:, 0] - 5.4 * sx) < 2.5) & (np.abs(P[:, 1] - 172) < 3) & (P[:, 2] > 4)
        eyes.append(P[m].mean(0))
    m = (np.abs(P[:, 0]) < 1) & (P[:, 1] > 167) & (P[:, 1] < 172)
    nose = P[np.argmax(np.where(m, P[:, 2], -99))]
    m = (np.abs(P[:, 0]) < 1) & (P[:, 1] < 165) & (P[:, 1] > 158) & (P[:, 2] > 4)
    chin = P[m][np.argmin(P[m][:, 1])]
    return eyes, nose, chin


def face_weights(game, Pk, UVk, mouth_k, Dblink=None):
    """Karin face vertices -> face-draw palette weights, transferred from the vanilla face after a per-axis
    scale + translation least-squares fit on landmarks (eye surfaces, nose tip, mouth, chin). Irises stay on the head.
    Returns list of {entry: w} and diagnostic info."""
    fm = game.mesh(HOST_B[2])
    P = fm['POSITION0'][:, :3].astype(float)
    idx, w = skin_arrays(fm)
    used = np.unique(fm['tris'])
    e2g = game.entries(HOST_B[2])
    head_entry = min(e for e, g in e2g.items() if g == 8)
    neck_entry = min(e for e, g in e2g.items() if g == 3)
    eye_l = game.mesh(35)['POSITION0'][:, :3].mean(0); eye_r = game.mesh(36)['POSITION0'][:, :3].mean(0)
    eye_l[2] = eye_r[2] = 11.3
    g_nose = P[np.argmax(P[:, 2])]
    g_mouth = np.array([0.0, 162.9, 12.4])
    mc = np.abs(P[:, 0]) < 0.5
    g_chin = P[mc][np.argmin(P[mc][:, 1])]
    (k_el, k_er), k_nose, k_chin = face_landmarks_karin(Pk)
    K = np.array([k_el, k_er, k_nose, mouth_k, k_chin]); G = np.array([eye_l, eye_r, g_nose, g_mouth, g_chin])
    S = np.zeros(3); Tt = np.zeros(3)
    for a in range(3):
        A = np.c_[K[:, a], np.ones(len(K))]
        sol = np.linalg.lstsq(A, G[:, a], rcond=None)[0]
        S[a], Tt[a] = sol
    if abs(S[2]) < 0.3:   # depth from the face profile is ill-conditioned when z barely varies
        S[2] = (S[0] + S[1]) / 2; Tt[2] = np.mean(G[:, 2] - S[2] * K[:, 2])
    Q = Pk * S + Tt
    ec_k = (k_el + k_er) / 2
    tree = cKDTree(P[used])
    d, nn = tree.query(Q, k=4)
    nn = used[nn]
    out = []
    for v in range(len(Pk)):
        acc = {}
        iris = UVk[v][1] < 0.26 and (UVk[v][0] < 0.32 or UVk[v][0] > 0.68)
        if iris:
            acc = {head_entry: 1.0}
        elif Pk[v][1] < k_chin[1] + 1.0 and Pk[v][2] < ec_k[2] - 4:
            acc = {neck_entry: 0.3, head_entry: 0.7}
        else:
            iw = 1 / (d[v] + 0.05); iw /= iw.sum()
            f = float(np.clip(1 - (d[v, 0] - 0.6) / 1.4, 0, 1))
            for j in range(4):
                for k in range(idx.shape[1]):
                    if w[nn[v, j], k] > 0:
                        e = int(idx[nn[v, j], k])
                        acc[e] = acc.get(e, 0) + f * iw[j] * w[nn[v, j], k]
            acc[head_entry] = acc.get(head_entry, 0) + (1 - f)
        out.append(acc)
    # eyelids: the game's blink moves the upper-lid bones ~LID_TRAVEL cm (vanilla eye opening 1.19 cm); Karin's
    # own blink moves her (larger) lids up to 4.5 cm. Scale the upper-lid weights so her lid travels its blink
    # distance; the head entry takes the negative remainder so the rest pose is unchanged (Nioh 3 FACE.md method).
    amp = 0
    cent = {}
    for e in UPPER_LID:
        ww = (w * (idx == e)).sum(1)
        if ww.sum() > 0:
            cent[e] = (P * ww[:, None]).sum(0) / ww.sum()
    shape_v = []
    if Dblink is not None and LID_MODE == 'shape':
        # blink = Karin's own shape key, applied by blink_b.hlsl from the game's lid-bone travel: lid vertices ride
        # the head rigidly (no lid-bone weights), so the bones cannot push her larger lids forward instead of down.
        for v in range(len(Pk)):
            iris = UVk[v][1] < 0.26 and (UVk[v][0] < 0.32 or UVk[v][0] > 0.68)
            if iris or float(np.linalg.norm(Dblink[v])) < 0.05:
                continue
            out[v] = {head_entry: 1.0}
            shape_v.append(v)
    elif Dblink is not None:
        main_l = [e for e in (16, 18, 20) if e in cent]; main_r = [e for e in (17, 19, 21) if e in cent]
        for v in range(len(Pk)):
            dv = Dblink[v]
            mag = float(np.linalg.norm(dv))
            iris = UVk[v][1] < 0.26 and (UVk[v][0] < 0.32 or UVk[v][0] > 0.68)
            if mag < 0.05 or dv[1] >= 0 or iris:
                continue
            target = min(mag / LID_TRAVEL, LID_MAX)
            dd = out[v]
            wup = sum(x for e, x in dd.items() if e in UPPER_LID)
            if wup > 0.05:
                k = target / wup
                if k > 1:
                    for e in list(dd):
                        if e in UPPER_LID:
                            dd[e] *= k
            else:
                cand = main_l if Pk[v][0] > 0 else main_r
                e = min(cand, key=lambda e: np.linalg.norm(cent[e][:2] - Q[v][:2]))
                dd[e] = dd.get(e, 0) + target
            rest = sum(x for e, x in dd.items() if e != head_entry)
            dd[head_entry] = 1.0 - rest
            amp += 1
    front = Pk[:, 2] > ec_k[2] - 1
    info = {'amplified_lid_vertices': amp, 'shape_lid_vertices': len(shape_v), 'scale': S.tolist(), 'offset': Tt.tolist(),
            'landmark_residual': np.round(K * S + Tt - G, 2).tolist(),
            'transfer_d_front_p50_p95': np.round(np.percentile(d[front, 0], [50, 95]), 2).tolist(),
            'head_entry': head_entry, 'neck_entry': neck_entry,
            'lid_ref': {e: np.round(cent[e], 3).tolist() for e in LID_REF if e in cent}, 'shape_v': shape_v}
    return out, info


# ---------------------------------------------------------------- textures
def dds_const(path, rgba, srgb=False, size=4):
    """tiny uncompressed DDS (DX10 header) filled with one colour."""
    fmt = 29 if srgb else 28  # R8G8B8A8_UNORM(_SRGB)
    hdr = bytearray(148)
    struct.pack_into('<4sI', hdr, 0, b'DDS ', 124)
    struct.pack_into('<IIIIIII', hdr, 8, 0x1 | 0x2 | 0x4 | 0x1000 | 0x8, size, size, size * 4, 0, 1, 0)
    struct.pack_into('<II4s', hdr, 76, 32, 0x4, b'DX10')
    struct.pack_into('<I', hdr, 108, 0x1000)
    struct.pack_into('<IIIII', hdr, 128, fmt, 3, 0, 1, 0)
    open(path, 'wb').write(bytes(hdr) + bytes(rgba) * (size * size))


def darken_png(src, dst, k):
    """scale albedo in linear space (anime albedo is ~0.95 white; the game's PBR lighting expects <= ~0.75)."""
    from PIL import Image
    im = np.asarray(Image.open(src).convert('RGBA'), np.float32) / 255.0
    rgb = im[..., :3]
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4) * k
    srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(np.maximum(lin, 0), 1 / 2.4) - 0.055)
    im[..., :3] = srgb
    Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(dst)


def texconv(src, outdir, fmt, size=None):
    args = [TEXCONV, '-nologo', '-y', '-ft', 'dds', '-f', fmt, '-m', '0', '-o', outdir]
    if size:
        args += ['-w', str(size), '-h', str(size)]
    if fmt.endswith('SRGB'):
        args += ['-srgb']
    subprocess.run(args + [src], check=True, capture_output=True)
    return os.path.join(outdir, os.path.splitext(os.path.basename(src))[0] + '.dds')


def host_mean(game, draw, slot):
    f = glob.glob(os.path.join(game.work, FA, f'{draw:06d}-ps-t{slot}=*.dds'))
    if not f:
        return None
    tmp = os.path.join(game.work, 'texview'); os.makedirs(tmp, exist_ok=True)
    subprocess.run([TEXCONV, '-nologo', '-y', '-ft', 'png', '-f', 'R8G8B8A8_UNORM', '-o', tmp, f[0]], check=True, capture_output=True)
    from PIL import Image
    im = np.asarray(Image.open(os.path.join(tmp, os.path.splitext(os.path.basename(f[0]))[0] + '.png')).convert('RGBA'), float)
    return [int(round(x)) for x in im.reshape(-1, 4).mean(0)]


# ---------------------------------------------------------------- spring-chain physics shader
def sim_layout(used, chain_toks, game_joints):
    """Chains, joint frames and colliders in palette indices (shared by write_sim_shader and the offline test)."""
    pal = {t: i for i, t in enumerate(used)}
    J = {k: np.array(v, float) for k, v in _CONF_JOINTS.items()}
    J.update({k: np.array(v, float) for k, v in game_joints.items()})
    joints, jw, ch = [], [], []
    p_base = b_base = 0
    for (key, mesh, anchor, names, groups, (k0, k1), damp, inertia, grav, cols), toks in zip(SIM_CHAINS, chain_toks):
        pts = [J[n] for n in names]
        lag, ang = SIM_LIMITS.get(key, SIM_LIMITS[key[0]])
        ch.append(dict(key=key, j0=len(joints), n=len(names) - 1, p0=p_base, b0=b_base, tok=pal[toks[0]], k0=k0, k1=k1,
                       damp=damp, inertia=inertia, grav=grav / SIM_FPS ** 2, cols=cols, pts=pts, lag=lag,
                       cosmax=float(np.cos(np.radians(ang)))))
        assert [pal[t] for t in toks] == list(range(pal[toks[0]], pal[toks[0]] + len(toks)))
        for p in pts:
            joints.append(p)
            jw.append([(pal[t], w) for t, w in joint_weights(anchor, p).items()])
        p_base += len(names) - 1; b_base += len(toks)
    names_c = list(SIM_COLLIDERS)
    col = []
    for cn in names_c:
        tok, (ja, oa), jb, r = SIM_COLLIDERS[cn]
        a = J[ja] + np.array(oa)
        b = J[jb[0]] + np.array(jb[1]) if jb else a.copy()

        def dist(p, a=a, b=b):
            ab = b - a
            t = np.clip(np.dot(p - a, ab) / max(np.dot(ab, ab), 1e-9), 0, 1)
            return np.linalg.norm(p - (a + t * ab))
        # the rest pose must start outside: shrink to 90 % of the nearest simulated rest particle
        near = min((dist(p) for x in ch if cn in x['cols'] for p in x['pts'][1:]), default=r / 0.9)
        col.append(dict(name=cn, tok=pal[tok], a=a, b=b, r=min(r, 0.9 * near)))
    return ch, joints, jw, col


def write_sim_shader(outdir, used, chain_toks, report, game_joints):
    """sim_a.hlsl: one thread per SIM_CHAINS chain. Every joint rides its own blend of palette bones (the anchor token,
    or the skirt weight field); rest joints = those frames x Karin joints. Particles: verlet with damping and gravity,
    pulled toward the rest pose, pushed out of sphere / capsule colliders, then put back at their rest segment lengths
    from the root out. Each segment's bone = its joint frame, rotated (and stretched along the segment) about the joint
    so the segment ends on the next particle, moved with the particle. Writes current + previous-frame rows into merged palette B.
    Returns the number of float4 state rows (particles x2, then 3 rows of last frame's matrix per simulated bone)."""
    ch, joints, jw, col = sim_layout(used, chain_toks, game_joints)
    report['sim'] = {'chains': len(ch), 'bones': sum(x['n'] for x in ch),
                     'colliders': {c['name']: round(c['r'], 1) for c in col}}
    P = sum(x['n'] for x in ch); B = P
    NCH, NC = len(ch), len(col)
    assert NCH <= 32
    maxj = max(x['n'] for x in ch) + 1
    names_c = [c['name'] for c in col]
    f3 = lambda v: 'float3(%.3f, %.3f, %.3f)' % tuple(v)  # noqa: E731
    arr = lambda typ, name, vals: f'static const {typ} {name}[{len(vals)}] = {{{", ".join(vals)}}};'  # noqa: E731
    jt = ['uint4(%s)' % ', '.join(str(w[i][0]) if i < len(w) else '0' for i in range(4)) for w in jw]
    jwv = ['float4(%s)' % ', '.join('%.5f' % w[i][1] if i < len(w) else '0' for i in range(4)) for w in jw]
    L = ['// generated by n2_build.py: spring-chain physics for Karin (once per frame, after merge_a), merged palette B.',
         '// Chains (array order): ' + ', '.join(x['key'] for x in ch) + '.',
         '// TL/TR twin tails, TA fox tail, EL/ER ears, HL/HR side locks, K0..K8 skirt (front -> back, L/R sides).',
         '// Tuning: CH_K0/CH_K1 = pull toward the rest pose per frame at root/tip (higher = stiffer),',
         '// CH_DAMP = velocity kept per frame, CH_INERTIA = share of the body motion the chain lags behind (0 = rigid),',
         '// CH_GRAV = gravity (cm per frame^2), COL_R = collider radii (cm): ' + ', '.join(names_c) + '.',
         'RWBuffer<float4> o : register(u0);    // merged palette B: row 5 + 3 i = bone i, 5 + 3 (K + i) its previous frame',
         'RWStructuredBuffer<float4> mo : register(u1);   // merge_a mirror of palette B (typed UAVs are write-only here)',
         'RWStructuredBuffer<float4> sv : register(u2);   // state: [0, P) particles, [P, 2P) previous particles, then 3 rows / bone',
         f'static const uint K = {len(used)}, P = {P}, NCH = {NCH}, NC = {NC}, MAXJ = {maxj};',
         arr('float3', 'JNT', [f3(j) for j in joints]),
         '// bone blend carrying each joint (palette B indices, weights)',
         arr('uint4', 'JW_T', jt), arr('float4', 'JW_W', jwv),
         arr('uint', 'CH_J0', [str(x['j0']) for x in ch]), arr('uint', 'CH_N', [str(x['n']) for x in ch]),
         arr('uint', 'CH_P0', [str(x['p0']) for x in ch]), arr('uint', 'CH_B0', [str(x['b0']) for x in ch]),
         arr('uint', 'CH_TOK', [str(x['tok']) for x in ch]),
         arr('float', 'CH_K0', ['%.3f' % x['k0'] for x in ch]), arr('float', 'CH_K1', ['%.3f' % x['k1'] for x in ch]),
         arr('float', 'CH_DAMP', ['%.3f' % x['damp'] for x in ch]),
         arr('float', 'CH_INERTIA', ['%.3f' % x['inertia'] for x in ch]),
         arr('float', 'CH_GRAV', ['%.4f' % x['grav'] for x in ch]),
         '// CH_LAG = max lag per frame (cm), CH_COSMAX = cos(max deviation of a segment from its rest direction)',
         arr('float', 'CH_LAG', ['%.2f' % x['lag'] for x in ch]), arr('float', 'CH_COSMAX', ['%.4f' % x['cosmax'] for x in ch]),
         arr('uint', 'CH_COL', [str(sum(1 << names_c.index(c) for c in x['cols'])) for x in ch]),
         '// colliders: capsule a-b (sphere when a == b) in the bind space of bone COL_TOK',
         arr('uint', 'COL_TOK', [str(c['tok']) for c in col]), arr('float3', 'COL_A', [f3(c['a']) for c in col]),
         arr('float3', 'COL_B', [f3(c['b']) for c in col]), arr('float', 'COL_R', ['%.2f' % c['r'] for c in col]),
         'float3x4 bone(uint i) { return float3x4(mo[5 + 3 * i], mo[6 + 3 * i], mo[7 + 3 * i]); }',
         'float3 xf(float3x4 m, float3 p) { return mul(m, float4(p, 1)); }',
         'float3x4 jframe(uint j, uint off) {   // off = 0: this frame, K: last frame',
         '  float3x4 m = (float3x4)0;',
         '  [unroll] for (uint i = 0; i < 4; i++) if (JW_W[j][i] > 0) m += JW_W[j][i] * bone(JW_T[j][i] + off);',
         '  return m;',
         '}',
         'float3x3 rot_between(float3 a, float3 b) {   // minimal rotation taking unit a onto unit b',
         '  float3 v = cross(a, b); float c = dot(a, b);',
         '  float3x3 I = float3x3(1, 0, 0, 0, 1, 0, 0, 0, 1);',
         '  if (c < -0.9999) {',
         '    float3 x = normalize(abs(a.x) < 0.9 ? cross(a, float3(1, 0, 0)) : cross(a, float3(0, 1, 0)));',
         '    return 2 * float3x3(x.x * x, x.y * x, x.z * x) - I;',
         '  }',
         '  float3x3 vx = float3x3(0, -v.z, v.y, v.z, 0, -v.x, -v.y, v.x, 0);',
         '  return I + vx + mul(vx, vx) / (1 + c);',
         '}',
         '[numthreads(32, 1, 1)]',
         'void main(uint3 t : SV_GroupThreadID) {',
         '  uint c = t.x;',
         '  if (c >= NCH) return;',
         '  uint n = CH_N[c], j0 = CH_J0[c], p0 = CH_P0[c], k, i;',
         '  float3 r[MAXJ], rp[MAXJ], p[MAXJ], q[MAXJ], ca[NC], cb[NC];',
         '  float seg[MAXJ];',
         '  float3x4 F[MAXJ];',
         '  for (k = 0; k <= n; k++) {',
         '    F[k] = jframe(j0 + k, 0);',
         '    r[k] = xf(F[k], JNT[j0 + k]);',
         '    rp[k] = xf(jframe(j0 + k, K), JNT[j0 + k]);',
         '  }',
         '  seg[0] = 0;',
         '  for (k = 1; k <= n; k++) seg[k] = length(r[k] - r[k - 1]);   // rest lengths (the skirt field may stretch them)',
         '  for (i = 0; i < NC; i++) { float3x4 b = bone(COL_TOK[i]); ca[i] = xf(b, COL_A[i]); cb[i] = xf(b, COL_B[i]); }',
         '  bool reset = false;',
         '  for (k = 1; k <= n; k++) {',
         '    float4 s = sv[p0 + k - 1];',
         '    if (s.w != 1 || any(isnan(s.xyz)) || distance(s.xyz, r[k]) > 80) reset = true;',
         '  }',
         '  p[0] = r[0]; q[0] = r[0];',
         '  for (k = 1; k <= n; k++) {',
         '    if (reset) { p[k] = r[k]; q[k] = r[k]; continue; }',
         '    float3 dr = r[k] - rp[k], lag = dr * CH_INERTIA[c];   // follow part of the body motion, lag the rest',
         '    float ll = length(lag);',
         '    if (ll > CH_LAG[c]) lag *= CH_LAG[c] / ll;',
         '    float3 carry = dr - lag;',
         '    float3 cur = sv[p0 + k - 1].xyz + carry, old = sv[P + p0 + k - 1].xyz + carry;',
         '    float stiff = lerp(CH_K0[c], CH_K1[c], n > 1 ? (k - 1) / float(n - 1) : 0);',
         '    float3 np = cur + (cur - old) * CH_DAMP[c] - float3(0, CH_GRAV[c], 0);',
         '    p[k] = lerp(np, r[k], stiff); q[k] = cur;',
         '  }',
         '  for (uint it = 0; it < 3; it++) {',
         '    for (k = 1; k <= n; k++) {',
         '      float3 rd = normalize(r[k] - r[k - 1]), dd = p[k] - p[k - 1];',
         '      float cd = dot(rd, normalize(dd));',
         '      if (cd < CH_COSMAX[c]) {   // swing limit',
         '        float3 perp = dd - rd * dot(dd, rd);',
         '        float pl = length(perp);',
         '        if (pl > 1e-5) p[k] = p[k - 1] + (rd * CH_COSMAX[c] + perp / pl * sqrt(1 - CH_COSMAX[c] * CH_COSMAX[c])) * length(dd);',
         '      }',
         '      for (i = 0; i < NC; i++) {',
         '        if (!((CH_COL[c] >> i) & 1)) continue;',
         '        float3 ab = cb[i] - ca[i];',
         '        float3 cp = ca[i] + ab * saturate(dot(p[k] - ca[i], ab) / max(dot(ab, ab), 1e-6));',
         '        float3 d = p[k] - cp; float l = length(d);',
         '        if (l < COL_R[i] && l > 1e-4) p[k] = cp + d * (COL_R[i] / l);',
         '      }',
         '      float3 d = p[k] - p[k - 1]; float l = length(d);',
         '      p[k] = p[k - 1] + (l > 1e-5 ? d / l : rd) * seg[k];',
         '    }',
         '  }',
         '  for (k = 1; k <= n; k++) { sv[p0 + k - 1] = float4(p[k], 1); sv[P + p0 + k - 1] = float4(q[k], 1); }',
         '  for (k = 0; k < n; k++) {',
         '    float3x3 Fr = (float3x3)F[k]; float3 Ft = float3(F[k][0].w, F[k][1].w, F[k][2].w);',
         '    float3 a = xf(F[k], JNT[j0 + k + 1]) - r[k], ah = normalize(a), d = p[k + 1] - p[k];',
         '    float s = length(d) / length(a) - 1;   // stretch along the segment so its end lands on the next particle',
         '    float3x3 Sa = float3x3(1, 0, 0, 0, 1, 0, 0, 0, 1) + s * float3x3(ah.x * ah, ah.y * ah, ah.z * ah);',
         '    float3x3 R = mul(rot_between(ah, normalize(d)), Sa);',
         '    float3x3 Mr = mul(R, Fr); float3 Mt = mul(R, Ft - r[k]) + p[k];',
         '    float4 m[3] = {float4(Mr[0], Mt.x), float4(Mr[1], Mt.y), float4(Mr[2], Mt.z)};',
         '    uint tok = CH_TOK[c] + k, sb = 2 * P + 3 * (CH_B0[c] + k);',
         '    bool fresh = reset || sv[sb].w == 0;',
         '    for (i = 0; i < 3; i++) {',
         '      o[5 + 3 * tok + i] = m[i];',
         '      o[5 + 3 * (K + tok) + i] = fresh ? m[i] : sv[sb + i];',
         '      sv[sb + i] = m[i];',
         '    }',
         '  }',
         '}']
    open(os.path.join(outdir, 'sim_a.hlsl'), 'w').write('\n'.join(L) + '\n')
    return 2 * P + 3 * B


# ---------------------------------------------------------------- main
def main(work, outdir, texconv_exe=None):
    global TEXCONV
    TEXCONV = texconv_exe or TEXCONV or os.path.abspath(os.path.join(work, 'texconv', 'texconv.exe'))
    game = Game(work)
    meta = json.load(open(os.path.join(work, 'source', 'source.json'), encoding='utf-8'))
    arr = dict(np.load(os.path.join(work, 'source', 'source.npz')))
    conf = dict(np.load(os.path.join(work, 'build1', 'conformed.npz'), allow_pickle=True))
    cj = json.load(open(os.path.join(work, 'build1', 'conform.json')))
    _CONF_JOINTS.update(cj['karin_joints_game'])
    os.makedirs(outdir, exist_ok=True)
    mdir = os.path.join(outdir, 'meshes'); tdir = os.path.join(outdir, 'textures')
    os.makedirs(mdir, exist_ok=True); os.makedirs(tdir, exist_ok=True)
    report = {'parts': {}}
    chains = retarget_hair_and_skirt(meta, arr, conf)

    # ---- host A geometry: every mesh but the face, grouped by texture
    A_parts = []   # (texture key, P, N, T, w, UV, tris, gws)
    tex_of = {'Karin_Body': 'body', 'Karin_Costume': 'costume', 'Karin_Hair': 'hair', 'Karin_Hair_Transparent': 'hair',
              'Karin_Face': 'face', 'Karin_Alpha': None}
    for m in meta['meshes']:
        if m['name'] == 'Body':
            continue
        k = m['key']
        lv = arr[k + '__loop_vertex']; tris_l = arr[k + '__tris']; tm = arr[k + '__tri_material']
        Pv = conf[k + '__pos'].astype(float)
        Nl = conf[k + '__loop_normal'].astype(float)
        UVl = arr[k + '__loop_uv'].astype(float).copy(); UVl[:, 1] = 1.0 - UVl[:, 1]
        gw_v = chains.get(m['name']) or [json.loads(x) for x in conf[k + '__gw']]
        vid, N, UV, tris = unweld(Pv, Nl, UVl, lv, tris_l)
        P = Pv[vid]
        gws = [gw_v[i] for i in vid]
        T, tw = tangents(P, N, UV, tris)
        mats = [x['name'] for x in m['materials']]
        for mi, mname in enumerate(mats):
            key = tex_of.get(mname)
            sel = tris[tm == mi]
            if key is None or not len(sel):
                continue
            A_parts.append((key, P, N, T, tw, UV, sel, gws, m['name']))
        report['parts'][m['name']] = {'verts': int(len(P)), 'tris': int(len(tris))}

    # two merged palettes (tokens g<gid> -> (source, entry)): A for the body / costume meshes, B for the meshes with
    # simulated bones plus every bone that carries a chain joint or a collider. Game tokens first, then the simulated
    # bones (contiguous, in chain order: sim_a.hlsl relies on it).
    order = lambda ts: sorted(ts, key=lambda t: (t[0] != 'g', int(t[1:])))  # noqa: E731
    used_A = order({t for part in A_parts if part[8] not in PAL_B_MESHES for d in part[7] for t in d})
    extra_B = {t for c in SIM_CHAINS for t in ([c[2]] if c[2] != 'field' else [])} | {c[0] for c in SIM_COLLIDERS.values()}
    for c in SIM_CHAINS:
        if c[2] == 'field':
            for n in c[3]:
                extra_B |= set(joint_weights('field', np.array(_CONF_JOINTS[n], float)))
    used_B = order({t for part in A_parts if part[8] in PAL_B_MESHES for d in part[7] for t in d} | extra_B)
    assert not any(t.startswith('s') for t in used_A)
    src_of = {}
    for name, ib, draw in SOURCES:
        for e, g in game.entries(draw).items():
            src_of.setdefault(f'g{g}', (name, e))
    _, chain_toks = sim_tokens()
    for toks in chain_toks:
        for t in toks:
            src_of[t] = ('sim', int(t[1:]))
    sim_used = [t for t in used_B if t.startswith('s')]
    assert sim_used == [t for toks in chain_toks for t in toks], f'simulated bones without vertices: {sim_used}'
    for nm, used in (('A', used_A), ('B', used_B)):
        missing = [t for t in used if t not in src_of]
        assert not missing, f'palette {nm}: no source draw for {missing}'
        assert len(used) <= 85, f'palette {nm}: {len(used)} bones > 85 (u8 indices)'
        report[f'palette_{nm}'] = {t: src_of[t] for t in used}
    pals = {'A': {t: i for i, t in enumerate(used_A)}, 'B': {t: i for i, t in enumerate(used_B)}}

    # write host A vertex buffer (one VB, one IB per texture)
    stride = 48
    vbs, ibs = [], {}
    base = 0
    for key, P, N, T, tw, UV, sel, gws, mname in A_parts:
        uv_used = np.unique(sel)
        remap = -np.ones(len(P), np.int64); remap[uv_used] = np.arange(len(uv_used))
        n = len(uv_used)
        buf = np.zeros((n, stride), np.uint8)
        buf[:, 0:12] = P[uv_used].astype('<f4').view(np.uint8).reshape(n, 12)
        W = np.zeros((n, 4), np.float32); I = np.zeros((n, 4), np.uint8)
        pid = 'B' if mname in PAL_B_MESHES else 'A'
        for j, v in enumerate(uv_used):
            ids, ws = pack_weights(gws[v], 4)
            I[j] = [pals[pid][t] * 3 for t in ids]; W[j] = ws
        buf[:, 12:20] = f16(W).view(np.uint8).reshape(n, 8)
        buf[:, 20:24] = I
        buf[:, 24:32] = f16(np.c_[N[uv_used], np.zeros(n)]).view(np.uint8).reshape(n, 8)
        buf[:, 36:40] = f16(UV[uv_used]).view(np.uint8).reshape(n, 4)
        buf[:, 40:48] = f16(np.c_[T[uv_used], tw[uv_used]]).view(np.uint8).reshape(n, 8)
        vbs.append(buf)
        ibs.setdefault(key + ('_b' if pid == 'B' else ''), []).append(remap[sel] + base)
        base += n
    assert base < 65536, base
    vb = np.concatenate(vbs)
    vb.tofile(os.path.join(mdir, 'karinA.vb'))
    for key, lst in ibs.items():
        np.concatenate(lst).astype('<u2').tofile(os.path.join(mdir, f'karinA_{key}.ib'))
    ibs = dict(sorted(ibs.items(), key=lambda kv: kv[0].endswith('_b')))     # palette A draws first
    report['host_A'] = {'verts': int(base), 'ibs': {k: int(sum(len(x) for x in v)) for k, v in ibs.items()},
                        'bones_A': len(used_A), 'bones_B': len(used_B)}

    # ---- host B: Karin face in the vanilla face draw
    fmesh = next(m for m in meta['meshes'] if m['name'] == 'Body')
    k = fmesh['key']
    lv = arr[k + '__loop_vertex']; tris_l = arr[k + '__tris']; tm = arr[k + '__tri_material']
    Pv = conf[k + '__pos'].astype(float); Nl = conf[k + '__loop_normal'].astype(float)
    UVl = arr[k + '__loop_uv'].astype(float).copy(); UVl[:, 1] = 1.0 - UVl[:, 1]
    vid, N, UV, tris = unweld(Pv, Nl, UVl, lv, tris_l)
    P = Pv[vid]
    T, tw = tangents(P, N, UV, tris)
    # Karin's mouth: the face texture's mouth line sits at uv (0.5, 0.835) in DX orientation
    mi = np.argmin(np.linalg.norm(UV - [0.5, 0.835], axis=1))
    mouth_k = P[mi]
    sk_info = json.load(open(os.path.join(work, 'source', 'shapekeys.json'), encoding='utf-8'))
    sk = np.load(os.path.join(work, 'source', 'shapekeys.npz'))
    bi = next(x['index'] for x in sk_info['Body'] if x['name'] == 'blink')
    Dsrc = sk[f'Body__{bi}'].astype(float) * float(cj['head_scale'])
    Dsrc = np.stack([Dsrc[:, 0], Dsrc[:, 2], -Dsrc[:, 1]], -1)       # Blender -> game axes (head is rigid)
    fw, finfo = face_weights(game, P, UV, mouth_k, Dsrc[vid])
    sel = tris[tm == 0]           # Karin_Face only (Karin_Alpha overlays need blending: not in build 1)
    used_v = np.unique(sel)
    remap = -np.ones(len(P), np.int64); remap[used_v] = np.arange(len(used_v))
    n = len(used_v)
    vb0 = np.zeros((n, 24), np.uint8)
    vb0[:, 0:12] = P[used_v].astype('<f4').view(np.uint8).reshape(n, 12)
    vb0[:, 12:24] = N[used_v].astype('<f4').view(np.uint8).reshape(n, 12)
    vb1 = np.zeros((n, 144), np.uint8)
    W = np.zeros((n, 8), np.float32); I = np.zeros((n, 8), np.int16)
    for j, v in enumerate(used_v):
        ids, ws = pack_weights(fw[v], 8)
        I[j] = [e * 3 for e in ids]; W[j] = ws
    vb1[:, 0:16] = f16(W).view(np.uint8).reshape(n, 16)
    vb1[:, 16:32] = I.astype('<i2').view(np.uint8).reshape(n, 16)
    vb1[:, 32:40] = f16(np.c_[T[used_v], tw[used_v]]).view(np.uint8).reshape(n, 8)
    vb1[:, 76:80] = f16(UV[used_v]).view(np.uint8).reshape(n, 4)
    vb0.tofile(os.path.join(mdir, 'karinB.vb0')); vb1.tofile(os.path.join(mdir, 'karinB.vb1'))
    (remap[sel]).astype('<u2').tofile(os.path.join(mdir, 'karinB_face.ib'))
    # blink shape key per face vertex (game bind space, cm) + side (+1 left / -1 right) for blink_b.hlsl
    shape_v = set(finfo.pop('shape_v'))
    blk = np.zeros((n, 4), np.float32)
    Db = Dsrc[vid]
    for j, v in enumerate(used_v):
        blk[j, 3] = 1.0 if P[v][0] > 0 else -1.0
        if v in shape_v:
            blk[j, :3] = Db[v]
    blk.astype('<f4').tofile(os.path.join(mdir, 'karinB_blink.buf'))
    report['host_B'] = {'verts': int(n), 'tris': int(len(sel)), **finfo, 'mouth_karin': mouth_k.tolist(),
                        'blink_verts': int((np.abs(blk[:, :3]).sum(1) > 0).sum()),
                        'blink_max_cm': round(float(np.linalg.norm(blk[:, :3], axis=1).max()), 2)}
    ref = finfo['lid_ref']
    side_e = {s: e for e, s in LID_REF.items()}
    hl = ['// generated by n2_build.py: Karin face (host B) blink = her own shape key, amount from the game lid bones.',
          '// cb0 = copy of the face draw vs-cb0 (VS %s): 5 header rows, then 3 rows (3x4 bind->world) per palette entry.' % FACE_VS,
          'cbuffer C : register(b0) { float4 c[389]; }',
          'ByteAddressBuffer src : register(t0);   // karinB.vb0: float3 pos, float3 normal (24 B / vertex)',
          'ByteAddressBuffer blk : register(t1);   // karinB_blink.buf: float3 shape-key delta, float side',
          'Buffer<float> prm : register(t2);       // [0] = lid drop (cm) that means fully closed, [1] = dead zone (cm)',
          'RWByteAddressBuffer dst : register(u0); // dynamic vb0',
          f'static const uint N = {n};',
          f'static const uint HEAD = {finfo["head_entry"]};',
          f'static const uint LID_L = {side_e[1]}, LID_R = {side_e[-1]};',
          'static const float3 QL = float3(%s), QR = float3(%s);' % (', '.join('%.3f' % x for x in ref[side_e[1]]),
                                                                     ', '.join('%.3f' % x for x in ref[side_e[-1]])),
          'float3 xf(uint e, float3 p) { uint r = 5 + 3 * e; float4 q = float4(p, 1); return float3(dot(c[r], q), dot(c[r + 1], q), dot(c[r + 2], q)); }',
          'float lid(uint e, float3 q, float D, float Z) {',
          '  uint r = 5 + 3 * HEAD;',
          '  float3 a0 = c[r].xyz, a1 = c[r + 1].xyz, a2 = c[r + 2].xyz;',
          '  float3 b = xf(e, q) - xf(HEAD, q);              // world-space offset of the lid point from rigid-head motion',
          '  float det = dot(a0, cross(a1, a2));',
          '  if (abs(det) < 1e-6) return 0;',
          '  float3 x = (cross(a1, a2) * b.x + cross(a2, a0) * b.y + cross(a0, a1) * b.z) / det;   // back to head space',
          '  return saturate((-x.y - Z) / (D - Z));',
          '}',
          '[numthreads(64, 1, 1)]',
          'void main(uint3 tid : SV_DispatchThreadID) {',
          '  uint v = tid.x;',
          '  if (v >= N) return;',
          '  float Z = max(prm[1], 0);',
          '  float D = max(prm[0], Z + 0.05);',
          '  float4 d = asfloat(blk.Load4(v * 16));',
          '  float a = d.w > 0 ? lid(LID_L, QL, D, Z) : lid(LID_R, QR, D, Z);',
          '  float3 p = asfloat(src.Load3(v * 24)) + a * d.xyz;',
          '  dst.Store3(v * 24, asuint(p));',
          '  dst.Store3(v * 24 + 12, src.Load3(v * 24 + 12));',
          '}']
    open(os.path.join(outdir, 'blink_b.hlsl'), 'w').write('\n'.join(hl) + '\n')

    # ---- textures
    srcdir = os.path.join(work, 'source', 'textures')
    tex = {'face': 'Standard_1_Karin_Face__9838578e__9838578e__fbx_rgb.png',
           'body': 'Standard_5_Karin_Body__068b4464__068b4464__fbx_rgb.png',
           'hair': 'Standard_10_Karin_Hair__1e553117__1e553117__fbx_rgb.png',
           'costume': 'Standard_16_Karin_Costume__3b9b5651__3b9b5651__fbx_rgb.png'}
    for key, fn in tex.items():
        tmp = os.path.join(tdir, f'karin_{key}.png')
        darken_png(os.path.join(srcdir, fn), tmp, ALBEDO_SCALE.get(key, 0.75))
        texconv(tmp, tdir, 'BC7_UNORM_SRGB', 2048)
        os.remove(tmp)
    spec_a = [10, 10, 10, 180]   # matte dielectric: reflectance 0.04, roughness 0.7 (o2.w = t1.a)
    spec_b = host_mean(game, HOST_B[2], 1) or [128, 128, 128, 128]
    art_b = host_mean(game, HOST_B[2], 7) or [128, 128, 128, 255]
    dds_const(os.path.join(tdir, 'flat_normal.dds'), [128, 128, 255, 255])
    dds_const(os.path.join(tdir, 'white.dds'), [255, 255, 255, 255])
    dds_const(os.path.join(tdir, 'spec_a.dds'), spec_a)
    dds_const(os.path.join(tdir, 'refrough_b.dds'), spec_b)
    dds_const(os.path.join(tdir, 'artior_b.dds'), art_b)
    report['textures'] = {'spec_a': spec_a, 'refrough_b': spec_b, 'artior_b': art_b}

    # ---- merge compute shader
    slot = {name: i for i, (name, ib, draw) in enumerate(SOURCES)}
    host_slot = len(SOURCES)
    lines = ['// generated by n2_build.py: merged bone palette for Karin host A (main-pass VS 73278b6e layout).',
             '// In levels the host (right gauntlet) is drawn before the other armour pieces, so their copies still hold',
             "// last frame's bones (stamp != frame counter): extrapolate those one frame at constant velocity",
             '// (M = C P^-1 C). Palette A -> o (body / costume draws), palette B -> o2 (hair, ears, tail, skirt) and its',
             '// readable mirror mo. Simulated bones (MAP.x == 255) are written afterwards by sim_a.hlsl.']
    for name, i in slot.items():
        lines.append(f'cbuffer S{i} : register(b{i}) {{ float4 s{i}[{CB_ROWS}]; }}')
    lines.append(f'cbuffer H : register(b{host_slot}) {{ float4 h[{CB_ROWS}]; }}')
    lines.append('RWBuffer<float4> o : register(u0);')
    lines.append('RWByteAddressBuffer st : register(u1);   // [0] frame counter (tick.hlsl), [4 + 4 s] frame of source s copy')
    lines.append('RWStructuredBuffer<float4> mo : register(u2);   // readable mirror of palette B for sim_a.hlsl')
    lines.append('RWBuffer<float4> o2 : register(u3);')
    lines.append(f'static const uint KA = {len(used_A)}, KB = {len(used_B)};')
    for nm, used in (('A', used_A), ('B', used_B)):
        lines.append(f'static const uint2 MAP{nm}[K{nm}] = {{' + ', '.join(
            f'uint2({255 if src_of[t][0] == "sim" else slot[src_of[t][0]]}, {src_of[t][1]})' for t in used) + '};')
    lines.append('float4 src(uint s, uint r) {')
    lines.append('  switch (s) {')
    for i in range(len(SOURCES)):
        lines.append(f'    case {i}: return s{i}[r];')
    lines.append('  } return float4(0, 0, 0, 0); }')
    lines.append('int srclen(uint s) { return asint(src(s, %d).x); }' % CB_LEN_ROW)
    lines += [
        'float3x4 bone(uint s, uint r) { return float3x4(src(s, r), src(s, r + 1), src(s, r + 2)); }',
        'float3x4 mul_affine(float3x4 a, float3x4 b) {',
        '  float3x4 r;',
        '  [unroll] for (uint i = 0; i < 3; i++)',
        '    r[i] = a[i].x * b[0] + a[i].y * b[1] + a[i].z * b[2] + float4(0, 0, 0, a[i].w);',
        '  return r; }',
        'bool inv_affine(float3x4 m, out float3x4 r) {',
        '  float3 a0 = m[0].xyz, a1 = m[1].xyz, a2 = m[2].xyz;',
        '  float det = dot(a0, cross(a1, a2));',
        '  r = m;',
        '  if (abs(det) < 1e-8) return false;',
        '  float3x3 ri = transpose(float3x3(cross(a1, a2), cross(a2, a0), cross(a0, a1)) / det);',
        '  float3 t = -mul(ri, float3(m[0].w, m[1].w, m[2].w));',
        '  r = float3x4(float4(ri[0], t.x), float4(ri[1], t.y), float4(ri[2], t.z));',
        '  return true; }',
        'void get(uint2 m, out float3x4 cur, out float3x4 prv) {',
        '  uint s = m.x, e = m.y; int L = srclen(s);',
        f'  float3x4 c = bone(s, {CB_BONE0} + 3 * e), p = bone(s, {CB_BONE0} + 3 * (e + L)), pi;',
        '  cur = c; prv = p;',
        '  if (st.Load(4 + 4 * s) != st.Load(0) && inv_affine(p, pi)) { prv = c; cur = mul_affine(mul_affine(c, pi), c); }',
        '}',
        '[numthreads(64, 1, 1)]',
        'void main(uint3 tid : SV_DispatchThreadID) {',
        '  uint j = tid.x, r;',
        '  float3x4 cur, prv;',
        f'  if (j < {CB_BONE0} || (j >= 773 && j < {CB_ROWS})) {{ o[j] = h[j]; o2[j] = h[j]; }}',
        f'  if (j == {CB_LEN_ROW}) {{ o[j] = float4(asfloat(int(KA)), h[j].yzw); o2[j] = float4(asfloat(int(KB)), h[j].yzw); }}',
        '  if (j < KA && MAPA[j].x != 255) {',
        '    get(MAPA[j], cur, prv);',
        '    [unroll] for (r = 0; r < 3; r++) {',
        f'      o[{CB_BONE0} + 3 * j + r] = cur[r]; o[{CB_BONE0} + 3 * (KA + j) + r] = prv[r];',
        '    }',
        '  }',
        '  if (j < KB && MAPB[j].x != 255) {',
        '    get(MAPB[j], cur, prv);',
        '    [unroll] for (r = 0; r < 3; r++) {',
        f'      o2[{CB_BONE0} + 3 * j + r] = cur[r]; mo[{CB_BONE0} + 3 * j + r] = cur[r];',
        f'      o2[{CB_BONE0} + 3 * (KB + j) + r] = prv[r]; mo[{CB_BONE0} + 3 * (KB + j) + r] = prv[r];',
        '    }',
        '  }',
        '}']
    open(os.path.join(outdir, 'merge_a.hlsl'), 'w').write('\n'.join(lines) + '\n')
    open(os.path.join(outdir, 'tick.hlsl'), 'w').write(
        '// frame counter for the bone-copy stamps (run with max_executions_per_frame = 1)\n'
        'RWByteAddressBuffer st : register(u1);\n'
        '[numthreads(1, 1, 1)] void main() { st.Store(0, st.Load(0) + 1); }\n')
    open(os.path.join(outdir, 'stamp.hlsl'), 'w').write(
        '// mark which frame the bones of source slot idx[0] were copied in\n'
        'Buffer<float> idx : register(t0);\n'
        'RWByteAddressBuffer st : register(u1);\n'
        '[numthreads(1, 1, 1)] void main() { st.Store(4 + 4 * uint(idx[0]), st.Load(0)); }\n')
    game_joints = json.load(open(os.path.join(work, 'data', 'joints.json')))['joints']
    sim_state_rows = write_sim_shader(outdir, used_B, chain_toks, report, game_joints)


    # ---- shadow-pass merges: re-layout the main-pass merged palette (bones are world matrices, pass-independent)
    for sid, (b0, (f0, f1), rows) in SHADOW_LAYOUT.items():
        L = [f'// generated: Karin host A palette (A or B, K from its length row) for shadow VS {SHADOW_VS[sid - 1]}',
             f'cbuffer M : register(b0) {{ float4 m[{CB_ROWS}]; }}',
             f'cbuffer H : register(b1) {{ float4 h[{rows}]; }}',
             'RWBuffer<float4> o : register(u0);',
             '[numthreads(64, 1, 1)]',
             'void main(uint3 tid : SV_DispatchThreadID) {',
             f'  uint j = tid.x, K = asint(m[{CB_LEN_ROW}].x);',
             f'  if (j < {b0} || (j >= {f0} && j < {f1})) o[j] = h[j];',
             '  if (j < 3 * K) o[' + str(b0) + ' + j] = m[' + str(CB_BONE0) + ' + j];',
             '}']
        open(os.path.join(outdir, f'merge_s{sid}.hlsl'), 'w').write(chr(10).join(L) + chr(10))

    # ---- ini
    ini = [f'; Karin_Original -> Nioh 2 female player (Hayabusa set + long ponytail). Generated by n2_build.py',
           '; Requires the Nioh 2 Mod Enabler (3DMigoto). F10 reloads, F2 toggles mods.', '',
           '[Constants]', 'global $kn2_shadow = 0', 'global $kn2_facevs = 0', '']
    ini += [f'[ShaderOverrideKN2_VS_{FACE_VS}]', f'hash = {FACE_VS}', 'allow_duplicate_hash = true', '$kn2_facevs = 1',
            'post $kn2_facevs = 0', '']
    for h in PS_HASHES:
        ini += [f'[ShaderOverrideKN2_PS_{h}]', f'hash = {h}', 'allow_duplicate_hash = true', 'run = CommandListN2General', '']
    for h in VS_HASHES:
        ini += [f'[ShaderOverrideKN2_VS_{h}]', f'hash = {h}', 'allow_duplicate_hash = true', 'run = CommandListN2General', '']
    for i, h in enumerate(SHADOW_VS):
        ini += [f'[ShaderOverrideKN2_VS_{h}]', f'hash = {h}', 'allow_duplicate_hash = true', f'$kn2_shadow = {i + 1}',
                'post $kn2_shadow = 0', '']
    for name, ib, draw in SOURCES:
        ini += [f'[ResourceKN2_cb_{name}]']
    ini += ['[ResourceKN2_hostcb]', '[ResourceKN2_bakcb]', '[ResourceKN2_hostcb_s]', '']
    for sfx in ('', '2'):
        ini += [f'[ResourceKN2_merged{sfx}_s]', 'type = RWBuffer', 'format = R32G32B32A32_FLOAT', 'array = 392', '']
        for sid, (b0, fl, rows) in SHADOW_LAYOUT.items():
            ini += [f'[CustomShaderKN2_MergeS{sid}{"B" if sfx else ""}]', f'cs = merge_s{sid}.hlsl',
                    f'cs-cb0 = copy ResourceKN2_merged{sfx}', 'cs-cb1 = ResourceKN2_hostcb_s',
                    f'cs-u0 = ResourceKN2_merged{sfx}_s', f'dispatch = {(rows + 63) // 64}, 1, 1', 'cs-u0 = null', '']
    ini += ['; merged bone palettes of host A: A = body / costume, B = hair, ears, tail, skirt and the simulated bones']
    for sfx in ('', '2'):
        ini += [f'[ResourceKN2_merged{sfx}]', 'type = RWBuffer', 'format = R32G32B32A32_FLOAT', f'array = {CB_ROWS}', '']
    ini += ['[CustomShaderKN2_MergeA]', f'cs = merge_a.hlsl']
    for name, i in slot.items():
        ini.append(f'cs-cb{i} = ResourceKN2_cb_{name}')
    ini += [f'cs-cb{host_slot} = ResourceKN2_hostcb', 'cs-u0 = ResourceKN2_merged', 'cs-u1 = ResourceKN2_stamp',
            'cs-u2 = ResourceKN2_mirror', 'cs-u3 = ResourceKN2_merged2', f'dispatch = {(CB_ROWS + 63) // 64}, 1, 1',
            'cs-u0 = null', 'cs-u1 = null', 'cs-u2 = null', 'cs-u3 = null', '',
            '[ResourceKN2_mirror]', 'type = RWStructuredBuffer', 'stride = 16', f'array = {CB_ROWS}', '']
    # frame stamps of the bone copies (merge_a extrapolates the ones copied last frame) and the chain physics state
    ini += ['[ResourceKN2_stamp]', 'type = RWByteAddressBuffer', 'byte_width = 64', 'data = R32_UINT' + ' 0' * 16, '',
            '[CustomShaderKN2_Tick]', 'cs = tick.hlsl', 'max_executions_per_frame = 1', 'cs-u1 = ResourceKN2_stamp',
            'dispatch = 1, 1, 1', 'cs-u1 = null', '']
    for name, i in slot.items():
        ini += [f'[ResourceKN2_slot{i}]', 'type = Buffer', 'format = R32_FLOAT', f'data = {i}', '',
                f'[CustomShaderKN2_Stamp{i}]', 'cs = stamp.hlsl', f'cs-t0 = ResourceKN2_slot{i}', 'cs-u1 = ResourceKN2_stamp',
                'dispatch = 1, 1, 1', 'cs-u1 = null', 'cs-t0 = null', '']
    ini += ['; spring-chain physics of the twin tails, fox tail, ears, side locks and skirt (tuning: top of sim_a.hlsl)',
            '[ResourceKN2_simstate]', 'type = RWStructuredBuffer', 'stride = 16', f'array = {sim_state_rows}',
            'data = R32_FLOAT' + ' 0' * (4 * sim_state_rows), '',
            '[CustomShaderKN2_Sim]', 'cs = sim_a.hlsl', 'max_executions_per_frame = 1', 'cs-u0 = ResourceKN2_merged2',
            'cs-u1 = ResourceKN2_mirror', 'cs-u2 = ResourceKN2_simstate', 'dispatch = 1, 1, 1', 'cs-u0 = null',
            'cs-u1 = null', 'cs-u2 = null', '']
    src_ibs = {ib for _, ib, _ in SOURCES}
    for name, ib, draw in SOURCES:
        if ib == HOST_A[1]:
            continue
        ini += [f'[TextureOverrideKN2_src_{name}]', f'hash = {ib}', 'handling = skip', 'run = CustomShaderKN2_Tick',
                'if $kn2_shadow == 0', f'  ResourceKN2_cb_{name} = copy vs-cb0', f'  run = CustomShaderKN2_Stamp{slot[name]}',
                'endif', '']
    ini += [f'[TextureOverrideKN2_hostA]', f'hash = {HOST_A[1]}', 'handling = skip', 'run = CustomShaderKN2_Tick',
            'if $kn2_shadow == 0',
            f'  ResourceKN2_cb_{HOST_A[0]} = copy vs-cb0', '  ResourceKN2_hostcb = copy vs-cb0',
            f'  run = CustomShaderKN2_Stamp{slot[HOST_A[0]]}', '  run = CustomShaderKN2_MergeA', '  run = CustomShaderKN2_Sim',
            '  ResourceKN2_bakcb = ref vs-cb0',
            '  vb0 = ResourceKN2_A_vb', '  ps-t1 = ResourceKN2_spec_a', '  ps-t2 = ResourceKN2_white',
            '  ps-t4 = ResourceKN2_flat_normal']

    def draws(shadow):
        out, cur = [], None
        for key in ibs:
            sfx = '2' if key.endswith('_b') else ''
            if sfx != cur:
                out.append(f'  vs-cb0 = copy ResourceKN2_merged{sfx}{"_s" if shadow else ""}')
                cur = sfx
            out += [f'  ib = ResourceKN2_A_ib_{key}', f'  ps-t0 = ResourceKN2_tex_{key.replace("_b", "")}',
                    '  drawindexed = auto']
        return out
    ini += draws(False)
    ini += ['  vs-cb0 = ref ResourceKN2_bakcb', 'else', '  ResourceKN2_hostcb_s = copy vs-cb0',
            '  if $kn2_shadow == 1', '    run = CustomShaderKN2_MergeS1', '    run = CustomShaderKN2_MergeS1B', '  else',
            '    run = CustomShaderKN2_MergeS2', '    run = CustomShaderKN2_MergeS2B',
            '  endif', '  ResourceKN2_bakcb = ref vs-cb0', '  vb0 = ResourceKN2_A_vb']
    ini += draws(True)
    ini += ['  vs-cb0 = ref ResourceKN2_bakcb', 'endif', '']
    nB = int(report['host_B']['verts'])
    ini += ['[ResourceKN2_cb_face]', '',
            '[ResourceKN2_B_src]', 'type = ByteAddressBuffer', 'filename = meshes/karinB.vb0', '',
            '[ResourceKN2_B_blk]', 'type = ByteAddressBuffer', 'filename = meshes/karinB_blink.buf', '',
            '; blink tuning: [1] lid-bone drop (cm) that counts as fully closed (vanilla full blink = 1.6; lower = eyes',
            '; close more easily), [2] drop ignored as rest-pose noise',
            '[ResourceKN2_B_prm]', 'type = Buffer', 'format = R32_FLOAT', f'data = {LID_FULL_CM} {LID_DEAD_CM} 0 0', '',
            '[ResourceKN2_B_dyn]', 'type = RWByteAddressBuffer', 'stride = 24', f'byte_width = {nB * 24}',
            'bind_flags = vertex_buffer unordered_access', '',
            '[CustomShaderKN2_Blink]', 'cs = blink_b.hlsl', 'cs-cb0 = ResourceKN2_cb_face', 'cs-t0 = ResourceKN2_B_src',
            'cs-t1 = ResourceKN2_B_blk', 'cs-t2 = ResourceKN2_B_prm', 'cs-u0 = ResourceKN2_B_dyn',
            f'dispatch = {(nB + 63) // 64}, 1, 1', 'cs-u0 = null', 'cs-t0 = null', 'cs-t1 = null', 'cs-t2 = null', '']
    ini += [f'[TextureOverrideKN2_hostB]', f'hash = {HOST_B[1]}', 'handling = skip',
            'if $kn2_facevs == 1', '  ResourceKN2_cb_face = copy vs-cb0', '  run = CustomShaderKN2_Blink',
            '  vb0 = ResourceKN2_B_dyn', 'else', '  vb0 = ResourceKN2_B_vb0', 'endif',
            'vb1 = ResourceKN2_B_vb1', 'ib = ResourceKN2_B_ib_face', 'ps-t0 = ResourceKN2_tex_face',
            'if $kn2_shadow == 0', '  ps-t1 = ResourceKN2_refrough_b', '  ps-t3 = ResourceKN2_flat_normal',
            '  ps-t4 = ResourceKN2_flat_normal', '  ps-t7 = ResourceKN2_artior_b', 'endif', 'drawindexed = auto', '']
    for ib in sorted(HIDE_IBS - src_ibs - {HOST_B[1]}):
        ini += [f'[TextureOverrideKN2_hide_{ib}]', f'hash = {ib}', 'handling = skip', '']
    ini += ['[ResourceKN2_A_vb]', 'type = Buffer', f'stride = {stride}', 'filename = meshes/karinA.vb', '']
    for key in ibs:
        ini += [f'[ResourceKN2_A_ib_{key}]', 'type = Buffer', 'format = DXGI_FORMAT_R16_UINT', f'filename = meshes/karinA_{key}.ib', '']
    ini += ['[ResourceKN2_B_vb0]', 'type = Buffer', 'stride = 24', 'filename = meshes/karinB.vb0', '',
            '[ResourceKN2_B_vb1]', 'type = Buffer', 'stride = 144', 'filename = meshes/karinB.vb1', '',
            '[ResourceKN2_B_ib_face]', 'type = Buffer', 'format = DXGI_FORMAT_R16_UINT', 'filename = meshes/karinB_face.ib', '']
    for key in tex:
        ini += [f'[ResourceKN2_tex_{key}]', f'filename = textures/karin_{key}.dds', '']
    for key in ('flat_normal', 'white', 'spec_a', 'refrough_b', 'artior_b'):
        ini += [f'[ResourceKN2_{key}]', f'filename = textures/{key}.dds', '']
    open(os.path.join(outdir, 'karin.ini'), 'w').write('\n'.join(ini) + '\n')
    json.dump(report, open(os.path.join(work, 'build1', 'build_report.json'), 'w'), indent=1, default=str)
    print(json.dumps({k: v for k, v in report.items() if not k.startswith('palette_')}, indent=1, default=str))


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('work', metavar='work_dir'); ap.add_argument('outdir', metavar='out_mod_dir')
    ap.add_argument('--texconv', help='texconv.exe (default: N2_TEXCONV, else <work dir>/texconv/texconv.exe)')
    a = ap.parse_args()
    main(a.work, a.outdir, a.texconv)
