"""Quadric-error mesh reduction that keeps every surviving vertex's attributes (half-edge collapse).

Only interior vertices are removed: a vertex whose position is shared by another vertex (a UV / normal
seam of the split glTF buffers) or that lies on an open edge stays, so UV seams, garment rims and culled
borders keep their exact outline and texture. Collapses that flip a face in 3D or in UV, create a sliver,
break the edge link condition, or merge vertices with different skinning are refused or penalised.
"""
import heapq

import numpy as np


def _plane_quadrics(P, T):
    a, b, c = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    n = np.cross(b - a, c - a)
    area2 = np.linalg.norm(n, axis=1)
    n = n / np.maximum(area2, 1e-20)[:, None]
    d = -(n * a).sum(1)
    pl = np.concatenate([n, d[:, None]], 1)
    # unweighted: the cost is squared distance to the original planes, so large flat regions go first and
    # small curved detail (fingers, rims) keeps its shape; area weighting would make tiny triangles free
    return pl[:, :, None] * pl[:, None, :]


def locked_vertices(P, T):
    """Seam (position shared with another vertex) or open / non-manifold edge vertices."""
    key = np.round(P * 1e6).astype(np.int64)
    _, pid, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    used = np.zeros(len(P), bool)
    used[T.ravel()] = True
    lock = cnt[pid.ravel()] > 1
    e = np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), 1)
    ue, c = np.unique(e, axis=0, return_counts=True)
    lock[ue[c != 2].ravel()] = True
    return lock | ~used


def decimate(mesh, target_verts, *, weight_penalty=4.0, min_normal_dot=0.8, min_quality=0.08, extra_lock=None):
    """Reduce mesh (dict with pos, tris, uv, weights (V,K) dense or with 'bones') to about target_verts used
    vertices. Returns (new mesh dict with unused vertices dropped, stats)."""
    P = np.asarray(mesh['pos'], np.float64)
    T = np.asarray(mesh['tris'], np.int64).copy()
    UV = np.asarray(mesh['uv'], np.float64)
    W = _dense_weights(mesh)
    lock = locked_vertices(P, T)
    if extra_lock is not None:
        lock |= extra_lock
    Q = np.zeros((len(P), 4, 4))
    fq = _plane_quadrics(P, T)
    for k in range(3):
        np.add.at(Q, T[:, k], fq)
    alive = np.ones(len(T), bool)
    vfaces = [set() for _ in range(len(P))]
    for f, t in enumerate(T):
        for v in t:
            vfaces[v].add(f)
    n_used = len(np.unique(T))
    scale2 = np.mean(np.linalg.norm(P[T[:, 1]] - P[T[:, 0]], axis=1)) ** 2
    stamp = np.zeros(len(P), np.int64)
    heap = []
    Pl = P.tolist()
    UVl = UV.tolist()

    def neighbours(u):
        s = set()
        for f in vfaces[u]:
            s.update(T[f].tolist())
        s.discard(u)
        return s

    def face_ok(t, u, v):
        """face t (indices) with u replaced by v: orientation kept in 3D and UV, not a sliver"""
        a0, b0, c0 = (Pl[i] for i in t)
        tn = [v if i == u else i for i in t]
        a1, b1, c1 = (Pl[i] for i in tn)
        n0 = _cross(_sub(b0, a0), _sub(c0, a0))
        n1 = _cross(_sub(b1, a1), _sub(c1, a1))
        l0, l1 = _norm(n0), _norm(n1)
        if l1 < 1e-14 or l0 < 1e-14:
            return False
        if _dot(n0, n1) / (l0 * l1) < min_normal_dot:
            return False
        per = _norm(_sub(b1, a1)) ** 2 + _norm(_sub(c1, b1)) ** 2 + _norm(_sub(a1, c1)) ** 2
        if 4 * 3 ** 0.5 * (l1 / 2) / per < min_quality:
            return False
        ua, ub, uc = (UVl[i] for i in t)
        va, vb, vc = (UVl[i] for i in tn)
        s0 = (ub[0] - ua[0]) * (uc[1] - ua[1]) - (uc[0] - ua[0]) * (ub[1] - ua[1])
        s1 = (vb[0] - va[0]) * (vc[1] - va[1]) - (vc[0] - va[0]) * (vb[1] - va[1])
        return s0 * s1 > 0 and abs(s1) > 1e-12

    def valid(u, v):
        nu, nv = neighbours(u), neighbours(v)
        if len(nu & nv) != 2:   # link condition for an interior edge
            return False
        v_faces = {tuple(sorted(T[f].tolist())) for f in vfaces[v]}
        for f in vfaces[u]:
            t = T[f].tolist()
            if v in t:
                continue
            # a face that would coincide with one of v's (e.g. collapsing a tetrahedron) breaks the surface
            if tuple(sorted(v if i == u else i for i in t)) in v_faces:
                return False
            if not face_ok(t, u, v):
                return False
        return True

    def cost(u, v):
        x = np.append(P[v], 1.0)
        c = float(x @ (Q[u] + Q[v]) @ x)
        wd = float(np.abs(W[u] - W[v]).sum())
        return c + weight_penalty * wd * scale2

    def push_best(u):
        stamp[u] += 1
        if lock[u] or not vfaces[u]:
            return
        cands = sorted((cost(u, v), v) for v in neighbours(u))
        for c, v in cands:
            if valid(u, v):
                heapq.heappush(heap, (c, u, v, stamp[u]))
                return

    for u in range(len(P)):
        if not lock[u] and vfaces[u]:
            push_best(u)
    collapsed = 0
    while heap and n_used > target_verts:
        _, u, v, st = heapq.heappop(heap)
        if st != stamp[u] or not vfaces[u] or not vfaces[v]:
            continue
        if v not in neighbours(u) or not valid(u, v):
            push_best(u)
            continue
        for f in list(vfaces[u]):
            t = T[f]
            if v in t:
                alive[f] = False
                for i in t:
                    vfaces[i].discard(f)
            else:
                t[t == u] = v
                vfaces[v].add(f)
        vfaces[u] = set()
        Q[v] += Q[u]
        n_used -= 1
        collapsed += 1
        for w in [v] + list(neighbours(v)):
            push_best(w)
    T2 = T[alive]
    used, inv = np.unique(T2, return_inverse=True)
    out = {k: (val[used] if isinstance(val, np.ndarray) and len(val) == len(P) else val)
           for k, val in mesh.items() if k != 'tris'}
    out['tris'] = inv.reshape(-1, 3)
    return out, dict(verts=(len(np.unique(T)), len(used)), tris=(len(T), len(T2)), collapsed=collapsed,
                     locked=int(lock[np.unique(T)].sum()))


def _dense_weights(mesh):
    J = np.asarray(mesh['joints'])
    Wt = np.asarray(mesh['weights'], np.float64)
    ids, inv = np.unique(J, return_inverse=True)
    D = np.zeros((len(J), len(ids)))
    np.add.at(D, (np.repeat(np.arange(len(J)), J.shape[1]), inv.ravel()), Wt.ravel())
    return D


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(a):
    return (a[0] * a[0] + a[1] * a[1] + a[2] * a[2]) ** 0.5
