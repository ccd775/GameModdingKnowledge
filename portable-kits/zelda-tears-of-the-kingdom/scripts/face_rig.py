"""Fit Karin's face shape keys onto Link's face bones (skin weights), so TotK's face animations drive her expressions.

For each correspondence k = (Link face anim, frame, Karin target = sum coef * shape-key delta) and each candidate bone b,
the displacement of vertex v when fully skinned to b is m_bk(v) = (S_b^k - I) v, S_b^k = W_pose @ inv(W_rest) (Head space).
Per vertex: min_w sum_k lam_k |sum_b w_b m_bk - D_k|^2 + mu |w|^2, w >= 0 (NNLS), then top-N bones, sum <= 1; the rest stays
on the vertex's original bones (Head).
"""
import os, sys
import numpy as np
from scipy.optimize import nnls
sys.path.insert(0, os.path.dirname(__file__))
import face_anim as fa

# (anim, frame or 'peak', {shape key: coef}, lambda)
# Eyes are NOT rigged: Link's eyelids travel ~7 mm about pivots 3 cm above / in front of Karin's anime eyes, whose blink
# needs up to 3.9 cm of lid travel -> bones can't close them and only distort them. Eye-area verts stay on Head.
CORR = [
    ('Voice_Default_A', 3, {'kuchi_A': 1.0}, 2.0),
    ('Voice_Default_O', 'peak', {'お': 1.0}, 1.0),
    ('Voice_Serious_I', 'peak', {'い': 1.0}, 0.7),
    ('Voice_Battle_U', 'peak', {'う': 1.0}, 0.7),
    ('Face_Battle_Blink', 0, {'怒り': 1.0}, 1.0),
    ('Face_Smile_Blink', 0, {'にこり': 1.0, '口角上げ': 1.0, 'にっこり': 1.0}, 1.0),
    ('Face_Serious_Blink', 0, {'真面目': 1.0}, 0.5),
    ('Face_Talk_Surprise', 'peak', {'上': 1.0, 'あ': 0.6}, 0.7),
]
EYE_KEYS = ['まばたき', '笑い', 'じと目', 'びっくり', 'LookUp', 'LookDown', 'LookLeft', 'LookRight', 'eyelids_forward',
            'hitomi_small_all', 'hitomi_big_all', 'highlight_big_all', 'LowerEyelid_up', 'LowerEyelid_down', 'tsurime', 'tareme']
FACE_BONES = ['Eyebrow_In_L', 'Eyebrow_In_R', 'Eyebrow_Mid_L', 'Eyebrow_Mid_R', 'Eyebrow_Out_L', 'Eyebrow_Out_R',
              'Chin', 'Chin_Point', 'Lip_U', 'Lip_D', 'Lip_U_L_1', 'Lip_U_L_2', 'Lip_U_R_1', 'Lip_U_R_2', 'Lip_D_L_1',
              'Lip_D_R_1', 'Cheek_U_L', 'Cheek_U_R', 'Cheek_D_L', 'Cheek_D_R', 'Nose', 'Teeth_U', 'Teeth_D']
SMOOTH_ITERS = 2   # Laplacian smoothing of the fitted weights over the face mesh (kills kinks in the brow line)
MU = 2e-6          # ridge on weights (m^2 scale): keeps far / irrelevant bones at 0
TOP_N = 3          # face bones kept per vertex (4th slot = Head)
MIN_TARGET = 2e-4  # vertices whose targets never exceed this stay rigid


def peak_frame(skel, anim):
    def score(t):
        S = fa.pose(skel, anim, t)
        return sum(np.linalg.norm(S[n][:3, :3] - np.eye(3)) + 10 * np.linalg.norm(S[n][:3, 3]) for n in S)
    return max(range(anim['frames'] + 1), key=score)


def poses(skel=None):
    skel = skel or fa.Skeleton()
    A = {a['name']: a for a in fa.load_face_anims()}
    out = []
    for an, fr, tgt, lam in CORR:
        a = A[an]
        t = peak_frame(skel, a) if fr == 'peak' else fr
        out.append((an, t, tgt, lam, fa.pose(skel, a, t)))
    return out


def smooth(weights, adj, frozen, iters=SMOOTH_ITERS):
    """Laplacian-smooth per-vertex weight dicts over adjacency adj (list of neighbour index arrays); frozen verts keep 0."""
    W = [dict(d) for d in weights]
    for _ in range(iters):
        new = []
        for v, d in enumerate(W):
            if frozen[v] or len(adj[v]) == 0: new.append(d); continue
            acc = {k: 0.5 * x for k, x in d.items()}
            f = 0.5 / len(adj[v])
            for u in adj[v]:
                for k, x in W[u].items(): acc[k] = acc.get(k, 0) + f * x
            new.append(acc)
        W = new
    out = []
    for d in W:
        top = dict(sorted(((k, x) for k, x in d.items() if x > 0.02), key=lambda kv: -kv[1])[:TOP_N])
        tot = sum(top.values())
        out.append({k: x / tot for k, x in top.items()} if tot > 1 else top)
    return out


def fit(P, targets, pose_list, rest_world, cand_radius=0.07, frozen=None):
    """P: (n,3) game-space rest positions of face verts; targets: list over correspondences of (n,3) displacements.
    rest_world: {bone: 4x4} rest world matrices of the model's face bones (must match the anim skeleton).
    frozen: bool mask of verts that must stay rigid (eye area). Returns list of {bone: w} per vertex."""
    n = len(P)
    frozen = np.zeros(n, bool) if frozen is None else frozen
    bones = [b for b in FACE_BONES if b in rest_world]
    Ph = np.c_[P, np.ones(n)]
    # m[k][b] : (n,3)
    M = [{b: (Ph @ (pl[4][b] - np.eye(4)).T)[:, :3] for b in bones} for pl in pose_list]
    lam = np.array([pl[3] for pl in pose_list])
    bpos = np.array([rest_world[b][:3, 3] for b in bones])
    out = []
    tmax = np.max([np.linalg.norm(T, axis=1) for T in targets], axis=0)
    for v in range(n):
        if frozen[v] or tmax[v] < MIN_TARGET: out.append({}); continue
        cand = [i for i, b in enumerate(bones) if np.linalg.norm(bpos[i] - P[v]) < cand_radius]
        if not cand: out.append({}); continue
        rows, rhs = [], []
        for k in range(len(pose_list)):
            s = np.sqrt(lam[k])
            rows.append(s * np.stack([M[k][bones[i]][v] for i in cand], axis=1)); rhs.append(s * targets[k][v])
        A = np.vstack(rows + [np.sqrt(MU) * np.eye(len(cand))]); y = np.concatenate(rhs + [np.zeros(len(cand))])
        w, _ = nnls(A, y)
        order = np.argsort(-w)[:TOP_N]
        d = {bones[cand[i]]: float(w[i]) for i in order if w[i] > 0.02}
        tot = sum(d.values())
        if tot > 1: d = {k: x / tot for k, x in d.items()}
        out.append(d)
    return out


# ---- v5 blink: signed / amplified eyelid weights (Nioh 3 approach; needs float skin weights in the bfres)
# Link's Eyelid_U pivot sits ~3 cm above / in front of Karin's anime eye and the lid only travels ~7 mm, so with weights in
# [0, 1] the lid can't close (and moves up/back). A weight w on a bone moves the vertex by w * (S - I) v, linear in w:
# w > 1 amplifies the travel, w < 0 reverses it; Head takes 1 - sum (can be very negative), so the rest pose is unchanged.
# Amplifying also magnifies the lids' off-axis rotation (tilts up to ~17 deg in Voice_Battle_*, Face_Eat_*), so the fit is
# constrained by EVERY distinct eyelid pose in Link's face anims: target = c * blink, c = Link's upper-lid rotation along
# the blink axis. Candidates per eye: its own Eyelid_U / Eyelid_D + the other eye's Eyelid_U (different pivot -> an
# independent direction that cancels much of the tilt); Head = 4th influence.
BLINK_ANIM = 'Face_Default_Blink'
BLINK_KEY = 'まばたき'
BLINK_LAM = 4.0              # per Face_Default_Blink frame
BLINK_LAM_OTHER = 8.0        # total over all other eyelid poses (spread evenly)
BLINK_C_CLIP = (-0.5, 1.2)
BLINK_ZW = 1.0               # weight of the depth (z) error vs. vertical/lateral
BLINK_SMOOTH = 3e-5          # Laplacian coupling between neighbouring position groups (and to 0 outside the eye area)
BLINK_RIDGE = 1e-7
LIDS = ('Eyelid_U_L', 'Eyelid_D_L', 'Eyelid_U_R', 'Eyelid_D_R')


def _rotvec(M):
    from scipy.spatial.transform import Rotation
    return Rotation.from_matrix(M[:3, :3]).as_rotvec()


def blink_bones(side):
    o = 'R' if side == 'L' else 'L'
    return [f'Eyelid_U_{side}', f'Eyelid_D_{side}', f'Eyelid_U_{o}']


def eyelid_poses(skel=None):
    """Distinct eyelid poses over all face anims (Face_Default_Blink first, never dropped as a duplicate):
    list of (anim, frame, {lid: S}, {'L': c, 'R': c})."""
    skel = skel or fa.Skeleton()
    AN = sorted(fa.load_face_anims(), key=lambda a: a['name'] != BLINK_ANIM)
    out, seen = [], set()
    u = a0 = None
    for a in AN:
        for t in range(a['frames'] + 1):
            S = fa.pose(skel, a, t)
            if 'Eyelid_U_L' not in S: continue
            S = {b: S[b] for b in LIDS}
            key = tuple(np.round(np.concatenate([M[:3, :].ravel() for M in S.values()]), 4))
            if key in seen and a['name'] != BLINK_ANIM: continue
            seen.add(key)
            if u is None:  # frame 0 of the blink = fully closed
                u = {s: _rotvec(S['Eyelid_U_' + s]) for s in 'LR'}; a0 = {s: float(u[s] @ u[s]) for s in 'LR'}
            c = {s: float(np.clip(_rotvec(S['Eyelid_U_' + s]) @ u[s] / a0[s], *BLINK_C_CLIP)) for s in 'LR'}
            out.append((a['name'], t, S, c))
    return out


def fit_blink(P, T, groups, adj, skel=None, poses=None, zw=BLINK_ZW, smooth=BLINK_SMOOTH, ridge=BLINK_RIDGE,
              lam_blink=BLINK_LAM, lam_other=BLINK_LAM_OTHER):
    """P, T: (n,3) rest positions / blink target (game space) per position group; groups: indices of the eye-area groups
    to solve; adj: neighbour index arrays for every group. Returns {group: {bone: w}} (signed; Head gets the remainder)."""
    import scipy.sparse as sp
    from scipy.sparse.linalg import spsolve
    poses = poses or eyelid_poses(skel)
    nb = sum(1 for p in poses if p[0] == BLINK_ANIM); no = len(poses) - nb
    groups = list(groups); col = {g: i for i, g in enumerate(groups)}; n = len(groups)
    side = np.array(['L' if P[g, 0] > 0 else 'R' for g in groups])
    bones = [blink_bones(s) for s in side]
    Ph = np.c_[P[groups], np.ones(n)]; Tg = T[groups]
    Z = np.array([1.0, 1.0, zw])
    K = len(bones[0])
    M = np.zeros((n, K, K)); v = np.zeros((n, K))
    for name, t, S, c in poses:
        lam = lam_blink if name == BLINK_ANIM else lam_other / max(no, 1)
        D = {b: (Ph @ (S[b] - np.eye(4)).T)[:, :3] for b in LIDS}
        X = np.stack([np.stack([D[bones[i][k]][i] for k in range(K)], 1) for i in range(n)]) * Z[None, :, None]  # n,3,K
        y = np.array([c[s] for s in side])[:, None] * Tg * Z
        M += lam * np.einsum('nck,ncj->nkj', X, X); v += lam * np.einsum('nck,nc->nk', X, y)
    rows, cols, vals = [], [], []
    for i in range(n):
        for a in range(K):
            for b in range(K): rows.append(K * i + a); cols.append(K * i + b); vals.append(M[i, a, b])
    for i, g in enumerate(groups):  # Laplacian: neighbours share bone k (same side), boundary pulled to 0
        for h in adj[g]:
            j = col.get(int(h))
            if j is not None and side[j] != side[i]: j = None
            for k in range(K):
                rows.append(K * i + k); cols.append(K * i + k); vals.append(smooth)
                if j is not None: rows.append(K * i + k); cols.append(K * j + k); vals.append(-smooth)
    A = sp.csr_matrix((vals, (rows, cols)), shape=(K * n, K * n)) + ridge * sp.eye(K * n)
    x = spsolve(A.tocsc(), v.ravel()).reshape(n, K)
    out = {}
    for i, g in enumerate(groups):
        d = {bones[i][k]: float(x[i, k]) for k in range(K) if abs(x[i, k]) > 0.01}
        if d: out[g] = d
    return out


def other_pose_report(P, T, weights, poses):
    """Worst-vertex deviation from c * blink over the non-blink eyelid poses (cm): p50 / p90 / max + worst anims."""
    gs = list(weights); Ph = np.c_[P[gs], np.ones(len(gs))]
    side = ['L' if P[g, 0] > 0 else 'R' for g in gs]
    worst = []
    for name, t, S, c in poses:
        if name == BLINK_ANIM: continue
        disp = np.zeros((len(gs), 3))
        for i, g in enumerate(gs):
            for b, w in weights[g].items(): disp[i] += w * ((S[b] - np.eye(4)) @ Ph[i])[:3]
        tgt = np.array([c[s] for s in side])[:, None] * T[gs]
        worst.append((float(np.linalg.norm(disp - tgt, axis=1).max()), name, t))
    e = np.array([w[0] for w in worst])
    return {'p50_cm': float(np.median(e) * 100), 'p90_cm': float(np.percentile(e, 90) * 100), 'max_cm': float(e.max() * 100),
            'worst': [(n, t, round(x * 100, 2)) for x, n, t in sorted(worst, reverse=True)[:5]]}


def blink_report(P, T, weights, skel=None):
    """Closing achieved at Face_Default_Blink frame 0 for the verts with big targets."""
    skel = skel or fa.Skeleton()
    S = fa.pose(skel, {a['name']: a for a in fa.load_face_anims()}[BLINK_ANIM], 0)
    tn = np.linalg.norm(T, axis=1); big = tn > 0.5 * tn.max()
    disp = np.zeros_like(P)
    for g, d in weights.items():
        ph = np.append(P[g], 1.0)
        for b, w in d.items(): disp[g] += w * ((S[b] - np.eye(4)) @ ph)[:3]
    err = np.linalg.norm(disp - T, axis=1); m = tn > 1e-3
    along = (disp[big] * T[big]).sum(1) / tn[big] ** 2
    ws = np.array([w for d in weights.values() for w in d.values()])
    return {'verts_big': int(big.sum()), 'along_mean': float(along.mean()), 'along_min': float(along.min()),
            'vertical_mean': float(np.mean(disp[big, 1] / T[big, 1])), 'err_mean_cm': float(err[m].mean() * 100),
            'err_max_cm': float(err[m].max() * 100), 'depth_bias_cm': float((disp[big, 2] - T[big, 2]).mean() * 100),
            'w_min': float(ws.min()), 'w_max': float(ws.max())}


def residual_report(P, targets, pose_list, weights):
    """Per correspondence: mean / max target size and remaining error after the fit (cm)."""
    n = len(P); Ph = np.c_[P, np.ones(n)]
    rep = []
    for k, pl in enumerate(pose_list):
        disp = np.zeros((n, 3))
        for v, d in enumerate(weights):
            for b, w in d.items(): disp[v] += w * ((pl[4][b] - np.eye(4)) @ Ph[v])[:3]
        T = targets[k]; mask = np.linalg.norm(T, axis=1) > 1e-3
        err = np.linalg.norm(disp - T, axis=1)
        rep.append((pl[0], pl[1], float(np.linalg.norm(T, axis=1)[mask].mean() * 100) if mask.any() else 0,
                    float(err[mask].mean() * 100) if mask.any() else 0, float(np.linalg.norm(T, axis=1).max() * 100)))
    return rep
