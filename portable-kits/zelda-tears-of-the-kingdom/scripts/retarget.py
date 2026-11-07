"""Retarget Karin (VRM humanoid rig, game space) onto TotK Link armor skeletons.

Geometry: every humanoid source bone gets a similarity map T_i (uniform scale s, then rotate the source
segment direction onto the target segment direction, optional stretch along the segment, then translate the
source joint onto the target joint). Vertices are moved with linear blend of the T_i using the source skin
weights (non-humanoid bones -> their nearest mapped ancestor). This keeps hands/fingers rigid per segment.

Weights: source bones -> target bone names via BONE_MAP plus physics chain maps; then limited/normalized.
"""
import json
import numpy as np

def quat_to_mat(q):
    x, y, z, w = q
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])

def target_world(model):
    """World bind matrices of a TotkMdl-exported model's skeleton (column-vector convention)."""
    bones = model['bones']
    W = [None] * len(bones)
    def get(i):
        if W[i] is not None: return W[i]
        b = bones[i]
        L = np.eye(4)
        L[:3, :3] = quat_to_mat(b['quat']) * np.array(b['scale'])[None, :]
        L[:3, 3] = b['pos']
        W[i] = L if b['parent'] < 0 else get(b['parent']) @ L
        return W[i]
    for i in range(len(bones)): get(i)
    return {bones[i]['name']: W[i] for i in range(len(bones))}

def rot_between(a, b):
    a = a / np.linalg.norm(a); b = b / np.linalg.norm(b)
    v = np.cross(a, b); c = float(np.dot(a, b))
    if c < -0.999999:
        axis = np.cross(a, [1, 0, 0])
        if np.linalg.norm(axis) < 1e-6: axis = np.cross(a, [0, 1, 0])
        axis /= np.linalg.norm(axis)
        return 2 * np.outer(axis, axis) - np.eye(3)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx / (1 + c)

def frame_rot(d_src, r_src, d_dst, r_dst):
    """Rotation taking (direction d_src, reference r_src) onto (d_dst, r_dst)."""
    def basis(d, r):
        d = d / np.linalg.norm(d)
        r = r - d * np.dot(r, d)
        if np.linalg.norm(r) < 1e-6: return None
        r /= np.linalg.norm(r)
        return np.stack([d, r, np.cross(d, r)], 1)
    A = basis(d_src, r_src); B = basis(d_dst, r_dst)
    if A is None or B is None: return rot_between(d_src, d_dst)
    return B @ A.T

def similarity(src_joint, dst_joint, R, s, stretch_dir=None, stretch=1.0, radial=1.0):
    """4x4: x -> dst + R @ (S_axial @ (s * (x - src))). radial: extra scale perpendicular to stretch_dir."""
    M = np.eye(3) * s
    if stretch_dir is not None and (abs(stretch - 1) > 1e-4 or abs(radial - 1) > 1e-4):
        d = stretch_dir / np.linalg.norm(stretch_dir); dd = np.outer(d, d)
        M = (radial * (np.eye(3) - dd) + stretch * dd) @ M
    T = np.eye(4)
    T[:3, :3] = R @ M
    T[:3, 3] = dst_joint - T[:3, :3] @ src_joint
    return T

def blend_transform(pos, nrm, w_idx, w_val, T):
    """Linear blend of per-source-bone 4x4 maps. T: (nbones,4,4)."""
    P = np.c_[pos, np.ones(len(pos))]
    out = np.zeros_like(pos); outn = np.zeros_like(nrm)
    wsum = np.zeros(len(pos))
    for j in range(w_idx.shape[1]):
        idx = w_idx[:, j]; w = w_val[:, j]
        ok = idx >= 0
        if not ok.any(): continue
        M = T[idx[ok]]
        out[ok] += w[ok, None] * np.einsum('nij,nj->ni', M, P[ok])[:, :3]
        outn[ok] += w[ok, None] * np.einsum('nij,nj->ni', M[:, :3, :3], nrm[ok])
        wsum[ok] += w[ok]
    zero = wsum < 1e-6
    out[~zero] /= wsum[~zero, None]
    out[zero] = pos[zero]
    outn /= np.maximum(np.linalg.norm(outn, axis=1, keepdims=True), 1e-9)
    outn[zero] = nrm[zero]
    return out, outn

def limit_weights(names, weights, k):
    """names/weights: lists per vertex -> top-k normalized."""
    out_n, out_w = [], []
    for n, w in zip(names, weights):
        acc = {}
        for a, b in zip(n, w): acc[a] = acc.get(a, 0) + b
        items = sorted(acc.items(), key=lambda kv: -kv[1])[:k]
        tot = sum(b for _, b in items) or 1.0
        out_n.append([a for a, _ in items]); out_w.append([b / tot for _, b in items])
    return out_n, out_w
