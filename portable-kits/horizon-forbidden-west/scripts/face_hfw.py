"""Skin Karin's face to Beta's joint-driven facial rig (skeleton 719), after the Days Gone kit's face_rig.py.

HFW animates faces with ~620 FACIAL_* deformer joints that sit on Beta's skin; there are no morph targets, and the
importer cannot move joints, so Karin's face only takes their weights and every animated delta is applied to her face
as is. Beta's face skin (mesh 625) is warped onto Karin's face with a thin-plate RBF through landmarks (eyes, nose tip,
mouth corners and centre, chin) and sampled at the closest surface point of every Karin skin vertex, with two guards:
  - mouth: skin above Karin's mouth line samples only Beta's upper-lip side and skin below only the lower-lip / jaw
    side (otherwise both lips take the same weights and the mouth cannot open);
  - eyes: Beta's lids travel about 1 cm, Karin's anime eye is 4.6 cm tall, so a blink would only twitch her lids;
    eyelid / eye-corner / eye-sack joints are left out around her eyes (the eyes stay open).
The face skin shares no vertices with the body (the neck overlaps it under the chin, so the chin stays free); along the
hairline, where the hair covers it, it fades back to its old head weights. Mouth interior
parts take Beta's teeth weights, the other small parts (lashes, brows, lines, eye surfaces) follow the nearest skin
vertex, and expression props hidden behind the skin are dropped (facial joints would push the skin over them).
"""
import re

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

EYE_JOINT = re.compile(r'Eyelid|Eyelash|EyeCorner|Eyesack')
UPPER = re.compile(r'LipUpper|UpperLip|MouthUpper|MouthInteriorUpper|TeethUpper')
LOWER = re.compile(r'LipLower|LowerLip|MouthLower|MouthInteriorLower|TeethLower|Chin|Jaw|Tongue')
SEAM_FADE = 2.0      # cm: skin weights blend back to the old (head) weights toward the hairline border
EYE_FADE = 1.0       # cm around the eye zone over which the eye joints come back
MOUTH_SIDE = 0.15    # donor triangle lip score threshold for the upper / lower guard
SMOOTH_ITERS = 3     # neighbour-averaging passes over the sampled skin weights


def components(T, n):
    A = coo_matrix((np.ones(T.size), (T[:, [0, 1, 2]].ravel(), T[:, [1, 2, 0]].ravel())), shape=(n, n))
    return connected_components(A, directed=False)[1]


def rbf_fit(a, b):
    n = len(a)
    K = np.linalg.norm(a[:, None] - a[None], axis=2)
    P = np.c_[a, np.ones(n)]
    M = np.zeros((n + 4, n + 4))
    M[:n, :n] = K
    M[:n, n:] = P
    M[n:, :n] = P.T
    rhs = np.zeros((n + 4, 3))
    rhs[:n] = b
    return a, np.linalg.solve(M, rhs)


def rbf_apply(f, x):
    a, W = f
    K = np.linalg.norm(x[:, None] - a[None], axis=2)
    return K @ W[:len(a)] + np.c_[x, np.ones(len(x))] @ W[len(a):]


def closest_on_triangles(p, A, B, C):
    """closest points of p (n,3) on triangles A, B, C (n,3) each; returns barycentrics (n,3) (Ericson 5.1.5)"""
    ab, ac, ap = B - A, C - A, p - A
    d1, d2 = (ab * ap).sum(1), (ac * ap).sum(1)
    bp = p - B
    d3, d4 = (ab * bp).sum(1), (ac * bp).sum(1)
    cp = p - C
    d5, d6 = (ab * cp).sum(1), (ac * cp).sum(1)
    va, vb, vc = d3 * d6 - d5 * d4, d5 * d2 - d1 * d6, d1 * d4 - d3 * d2
    den = np.where(np.abs(va + vb + vc) < 1e-12, 1e-12, va + vb + vc)
    bary = np.stack([va / den, vb / den, vc / den], 1)          # interior
    eps = 1e-12

    def seg(mask, t, i, j):                                     # on edge i-j at parameter t
        b = np.zeros((mask.sum(), 3))
        b[:, i] = 1 - t
        b[:, j] = t
        bary[mask] = b
    m = (va <= 0) & (d4 - d3 >= 0) & (d5 - d6 >= 0)
    seg(m, ((d4 - d3) / np.maximum((d4 - d3) + (d5 - d6), eps))[m], 1, 2)
    m = (vb <= 0) & (d2 >= 0) & (d6 <= 0)
    seg(m, (d2 / np.maximum(d2 - d6, eps))[m], 0, 2)
    m = (vc <= 0) & (d1 >= 0) & (d3 <= 0)
    seg(m, (d1 / np.maximum(d1 - d3, eps))[m], 0, 1)
    for mask, i in (((d6 >= 0) & (d5 <= d6), 2), ((d3 >= 0) & (d4 <= d3), 1), ((d1 <= 0) & (d2 <= 0), 0)):
        b = np.zeros((mask.sum(), 3))
        b[:, i] = 1
        bary[mask] = b
    return bary


class Surface:
    """donor triangles (warped positions) with sparse vertex weights; nearest-point weight sampling"""

    def __init__(self, X, T, bi, bw, nb):
        self.X, self.T, self.bi, self.bw, self.nb = X, T, bi, bw, nb
        self.C = X[T].mean(1)

    def locate(self, P, allowed=None, k=24):
        """closest triangle (rows of T) and barycentrics for every point, and the distance"""
        T = self.T if allowed is None else self.T[allowed]
        C = self.C if allowed is None else self.C[allowed]
        _, cand = cKDTree(C).query(P, k=min(k, len(T)))
        n = len(P)
        best = np.full(n, np.inf)
        bt = np.zeros(n, int)
        bb = np.zeros((n, 3))
        for j in range(cand.shape[1]):
            t = T[cand[:, j]]
            bary = closest_on_triangles(P, self.X[t[:, 0]], self.X[t[:, 1]], self.X[t[:, 2]])
            q = np.einsum('nk,nkd->nd', bary, self.X[t])
            d = np.linalg.norm(P - q, axis=1)
            better = d < best
            best[better], bt[better], bb[better] = d[better], cand[better, j], bary[better]
        return T[bt], bb, best

    def sample(self, P, allowed=None):
        tri, bb, best = self.locate(P, allowed)
        W = np.zeros((len(P), self.nb))
        rows = np.arange(len(P))
        for c in range(3):
            v = tri[:, c]
            if self.bi is None:      # dense vertex weights
                W += bb[:, c, None] * self.bw[v]
                continue
            for s in range(self.bi.shape[1]):
                np.add.at(W, (rows, self.bi[v, s]), bb[:, c] * self.bw[v, s])
        return W, best


def donor(mesh, z_min=100.0):
    """positions (cm), triangles above z_min, slot arrays of an h2 ascii submesh"""
    X = np.asarray(mesh['pos'], float) * 100.0
    T = np.asarray(mesh['faces'])
    T = T[(X[T][:, :, 2] > z_min).all(1)]
    bi = np.asarray(mesh['bi'])
    bw = np.nan_to_num(np.asarray(mesh['bw'], float))
    return X, T, bi, bw


def ray_hits(origins, d, X, T, max_t):
    """distance along d to the first triangle hit for each origin (inf when none)"""
    v0, e1, e2 = X[T[:, 0]], X[T[:, 1]] - X[T[:, 0]], X[T[:, 2]] - X[T[:, 0]]
    pv = np.cross(d, e2)
    det = (e1 * pv).sum(1)
    ok = np.abs(det) > 1e-12
    inv = np.where(ok, 1 / np.where(ok, det, 1), 0)
    out = np.full(len(origins), np.inf)
    for i, o in enumerate(origins):
        tv = o - v0
        u = (tv * pv).sum(1) * inv
        qv = np.cross(tv, e1)
        v = (qv * d).sum(1) * inv
        t = (e2 * qv).sum(1) * inv
        hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-4) & (t < max_t)
        if hit.any():
            out[i] = t[hit].min()
    return out


def rig_face(face, names719, skin_mesh, teeth_mesh, report):
    """face: merged Karin face part (P cm, N, UV, A = weights over the 719 skeleton, T, joints719 = 719 bind positions
    in cm). skin_mesh / teeth_mesh: Beta's h2 ascii submeshes 625 sm0 and 514 sm0. Returns the rigged part."""
    P, T, A_old = face['P'], face['T'], face['A']
    nb = len(names719)
    idx = {n: i for i, n in enumerate(names719)}
    head = idx['C_Head_sjnt_0']
    lab = components(T, len(P))
    sizes = np.bincount(lab)
    skin_c = int(np.argmax(sizes))
    skin = np.where(lab == skin_c)[0]

    # ---- Karin parts
    parts = {}
    for c in range(len(sizes)):
        if c == skin_c:
            continue
        v = np.where(lab == c)[0]
        parts[c] = dict(v=v, ctr=P[v].mean(0), size=np.ptp(P[v], 0))
    # the mouth line: the widest thin centred strip below the eyes
    eye_like = {c: q for c, q in parts.items() if 2.0 < abs(q['ctr'][0]) < 9.0 and q['size'][0] > 2.5 and q['size'][2] > 3.0}
    eyes = {}
    for side, sgn in (('L', -1), ('R', 1)):    # HFW: model left is -x
        cs = [c for c, q in eye_like.items() if np.sign(q['ctr'][0]) == sgn]
        eyes[side] = max(cs, key=lambda c: parts[c]['ctr'][1])          # the front-most one is the visible eye
    eye_z = np.mean([parts[c]['ctr'][2] for c in eyes.values()])
    strips = {c: q for c, q in parts.items() if abs(q['ctr'][0]) < 0.3 and q['size'][0] > 1.5 and q['size'][2] < 0.6
              and q['ctr'][2] < eye_z - 2}
    mouth_c = max(strips, key=lambda c: strips[c]['size'][0])
    mq = parts[mouth_c]
    mouth = mq['ctr']
    half_w = mq['size'][0] / 2
    mouth_parts = [c for c, q in parts.items() if c != mouth_c and abs(q['ctr'][0]) < 2.5
                   and abs(q['ctr'][2] - mouth[2]) < 2.5 and mouth[1] - 4.5 < q['ctr'][1] <= mouth[1]]

    # ---- hidden expression props: more than 0.5 cm behind the skin, straight ahead
    skin_T = T[np.isin(T, skin).all(1)]
    keep_c = set(eyes.values()) | {mouth_c} | set(mouth_parts)
    others = [c for c in parts if c not in keep_c]
    depth = ray_hits(np.array([parts[c]['ctr'] for c in others]), np.array([0, 1.0, 0]), P, skin_T, 15.0)
    hidden = [c for c, t in zip(others, depth) if np.isfinite(t) and t > 0.5]

    # ---- landmarks
    def centreline_front(pts, zlo, zhi, half=0.4):
        s = pts[(np.abs(pts[:, 0]) < half) & (pts[:, 2] > zlo) & (pts[:, 2] < zhi)]
        return s[np.argmax(s[:, 1])]

    def chin_point(pts, mouth_z):
        s = pts[(np.abs(pts[:, 0]) < 1.0) & (pts[:, 2] < mouth_z - 1.0)]
        s = s[s[:, 1] > s[:, 1].max() - 1.5]
        return s[np.argmin(s[:, 2])]

    Xd, Td, bid, bwd = donor(skin_mesh)
    jpos = face['joints719']
    k_eye = {s: parts[c]['ctr'] for s, c in eyes.items()}
    k_corner = {'L': mouth + np.array([-half_w, 0, 0]), 'R': mouth + np.array([half_w, 0, 0])}
    k_nose = centreline_front(P[skin], mouth[2], eye_z)
    k_chin = chin_point(P[skin], mouth[2])
    # Beta: pupils sit on the front of her eyeballs; mouth corners and centre from the skin around the lip joints
    d_eye = {'L': jpos[idx['FACIAL_L_Pupil']], 'R': jpos[idx['FACIAL_R_Pupil']]}
    dv = np.unique(Td)
    tree_d = cKDTree(Xd[dv])
    d_corner = {s: Xd[dv[tree_d.query(jpos[idx[f'FACIAL_{s}_LipCorner']])[1]]] for s in ('L', 'R')}
    lip_up = np.isin(bid, [i for n, i in idx.items() if UPPER.search(n)])
    lip_lo = np.isin(bid, [i for n, i in idx.items() if LOWER.search(n)])
    score = (bwd * lip_up).sum(1) - (bwd * lip_lo).sum(1)           # per donor vertex: + upper side, - lower side
    mz = (d_corner['L'][2] + d_corner['R'][2]) / 2
    cl = dv[(np.abs(Xd[dv, 0]) < 0.4) & (np.abs(Xd[dv, 2] - mz) < 2.0)]
    cl = cl[Xd[cl, 1] > Xd[cl, 1].max() - 2.5]
    up_low = cl[score[cl] > 0.3]
    lo_high = cl[score[cl] < -0.3]
    d_mouth = (Xd[up_low[np.argmin(Xd[up_low, 2])]] + Xd[lo_high[np.argmax(Xd[lo_high, 2])]]) / 2
    d_nose = centreline_front(Xd[dv], d_mouth[2], d_eye['L'][2])
    d_chin = chin_point(Xd[dv], d_mouth[2])
    src = [d_eye['L'], d_eye['R'], d_corner['L'], d_corner['R'], d_mouth, d_nose, d_chin]
    dst = [k_eye['L'], k_eye['R'], k_corner['L'], k_corner['R'], mouth, k_nose, k_chin]
    hp = jpos[head]
    for off in ((0, -12, 6), (0, 0, 17), (12, -2, 5), (-12, -2, 5), (0, -7, -14), (9, -4, -10), (-9, -4, -10)):
        src.append(hp + np.array(off, float))
        dst.append(hp + np.array(off, float))
    src, dst = np.array(src), np.array(dst)
    warp = rbf_fit(src, dst)
    Xw = Xd.copy()
    Xw[dv] = rbf_apply(warp, Xd[dv])
    surf = Surface(Xw, Td, bid, bwd, nb)
    tri_score = score[Td].mean(1)

    # ---- the mouth slit: a hole in the skin whose upper and lower rims lie only 0.04 cm apart (and whose loop touches
    # another border at the centre line), so a rim vertex's side comes from where its skin triangles extend
    E = np.sort(np.concatenate([skin_T[:, [0, 1]], skin_T[:, [1, 2]], skin_T[:, [2, 0]]]), 1)
    ue, cnt = np.unique(E, axis=0, return_counts=True)
    be = ue[cnt == 1]
    bl = components(np.c_[be, be[:, 0]], len(P))[be[:, 0]]
    bverts = np.unique(be)
    slit = bverts[(np.abs(P[bverts, 0]) <= half_w + 0.05) & (np.abs(P[bverts, 2] - mouth[2]) < 0.3)
                  & (P[bverts, 1] > mouth[1] - 1.0)]
    tri_dz = P[skin_T, 2].mean(1)
    rim_side = np.array([np.sign((tri_dz[(skin_T == v).any(1)] - P[v, 2]).mean()) for v in slit])
    up_rim, lo_rim = slit[rim_side > 0], slit[rim_side < 0]
    W = np.zeros((len(P), nb))
    S = P[skin]
    in_mouth = (np.abs(S[:, 0]) < half_w + 1.0) & (np.abs(S[:, 2] - mouth[2]) < 1.5) & (S[:, 1] > mouth[1] - 2.5)
    side = np.zeros(len(P))                     # +1 upper lip, -1 lower lip
    side[skin] = np.where(S[:, 2] > P[slit, 2].mean(), 1, -1)
    side[up_rim], side[lo_rim] = 1, -1
    above = side[skin] > 0
    groups = [(~in_mouth, None), (in_mouth & above, tri_score >= -MOUTH_SIDE), (in_mouth & ~above, tri_score <= MOUTH_SIDE)]
    dist = np.zeros(len(S))
    for sel, allowed in groups:
        if sel.any():
            W[skin[sel]], dist[sel] = surf.sample(S[sel], allowed)
    # eyes: no lid joints around Karin's eyes
    eyej = np.array([bool(EYE_JOINT.search(n)) for n in names719])
    for s, c in eyes.items():
        q = parts[c]
        r = np.sqrt(((P[skin, 0] - q['ctr'][0]) / (q['size'][0] / 2 + 0.6)) ** 2 +
                    ((P[skin, 2] - q['ctr'][2]) / (q['size'][2] / 2 + 0.8)) ** 2)
        reach = (q['size'][0] / 2 + 0.6)
        f = np.clip(1 - (r - 1) * reach / EYE_FADE, 0, 1)
        f = f * f * (3 - 2 * f)
        moved = W[skin][:, eyej].sum(1) * f
        Wd = W[skin]
        Wd[:, eyej] *= (1 - f)[:, None]
        Wd[:, head] += moved
        W[skin] = Wd
    # hair seam: the face skin shares no vertices with the body; its outer border runs under the chin (the neck
    # overlaps it there, and the chin must stay free to move) and along the hairline, where the bangs and the hair
    # (head joint only) cover it: fade back to the old weights there so the forehead does not push through the hair
    outer = np.unique(be[bl == np.bincount(bl).argmax()])
    seam = outer[(P[outer, 2] > eye_z + 3.0) | (P[outer, 1] < -2.0)]
    if len(seam):
        dseam = cKDTree(P[seam]).query(P[skin])[0]
        t = np.clip(1 - dseam / SEAM_FADE, 0, 1)
        t = t * t * (3 - 2 * t)
        W[skin] = (1 - t)[:, None] * W[skin] + t[:, None] * A_old[skin]
    # smooth the skin field a little: neighbouring samples can come from different Beta triangles, and the lines on
    # the skin (brows, lashes) then kink where the weights jump
    nbr = coo_matrix((np.ones(skin_T.size), (skin_T[:, [0, 1, 2]].ravel(), skin_T[:, [1, 2, 0]].ravel())),
                     shape=(len(P), len(P))).tocsr()
    nbr = ((nbr + nbr.T) > 0).astype(float)[skin][:, skin]
    deg = np.asarray(nbr.sum(1)).ravel()
    Ws = W[skin]
    free = ~in_mouth            # the guarded lips keep their samples (smoothing would mix upper and lower lip)
    for _ in range(SMOOTH_ITERS):
        Ws[free] = (0.5 * Ws + 0.5 * (nbr @ Ws) / np.maximum(deg, 1)[:, None])[free]
    W[skin] = Ws
    # mouth interior: Beta's teeth / tongue
    if mouth_parts:
        Xt, Tt, bit, bwt = donor(teeth_mesh)
        tv = np.unique(Tt)
        Xtw = Xt.copy()
        Xtw[tv] = rbf_apply(warp, Xt[tv])
        tsurf = Surface(Xtw, Tt, bit, bwt, nb)
        mv = np.concatenate([parts[c]['v'] for c in mouth_parts])
        W[mv] = tsurf.sample(P[mv])[0]
    # the rest follows the closest point of the skin surface; the mouth line rides on the upper lip rim
    rest = np.concatenate([parts[c]['v'] for c in parts if c not in mouth_parts and c not in hidden and c != mouth_c])
    W[rest] = Surface(P, skin_T, None, W, nb).sample(P[rest])[0]
    up = np.array(up_rim)
    W[mq['v']] = W[up[cKDTree(P[up]).query(P[mq['v']])[1]]]

    # ---- coincident vertices (the mirrored halves' centre line, UV seams) share one set of weights, or the seam
    # opens when the face moves (seen in game as a dark crack down the chin)
    _, grp = np.unique(np.round(P * 1000).astype(np.int64), axis=0, return_inverse=True)
    grp = grp.ravel()
    sums = np.zeros((grp.max() + 1, nb))
    np.add.at(sums, grp, W)
    W = sums[grp] / np.bincount(grp)[grp, None]

    # ---- drop the hidden props
    drop = np.zeros(len(P), bool)
    for c in hidden:
        drop[parts[c]['v']] = True
    keep_t = ~drop[T].all(1)
    used, inv = np.unique(T[keep_t], return_inverse=True)
    out = dict(P=P[used], N=face['N'][used], UV=face['UV'][used], A=W[used], T=inv.reshape(-1, 3))
    facial = np.array([n.startswith('FACIAL') for n in names719])
    report['face_rig'] = dict(
        skin=int(len(skin)), parts=len(parts), hidden_parts=len(hidden), hidden_verts=int(drop.sum()),
        mouth_parts=len(mouth_parts), eyes={s: int(len(parts[c]['v'])) for s, c in eyes.items()},
        mouth=[round(float(x), 2) for x in mouth], mouth_width=round(float(2 * half_w), 2),
        landmarks_beta=np.round(src[:7], 2).tolist(), landmarks_karin=np.round(dst[:7], 2).tolist(),
        sample_dist_max=round(float(dist.max()), 2), sample_dist_p95=round(float(np.percentile(dist, 95)), 2),
        skin_verts_on_facial_joints=int((W[skin][:, facial].sum(1) > 0.05).sum()),
        facial_joints_used=int((W[:, facial].max(0) > 0.01).sum()), seam_verts=int(len(seam)),
        lip_rims=[len(up_rim), len(lo_rim)])
    return out
