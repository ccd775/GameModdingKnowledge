"""Convert Karin's facial shape keys into a W3 mimic rig (bone translations per mimic pose).

All arrays are in W3 model space (metres) after the body fit.
  P             (N,3) fitted face vertex positions
  pose_targets  list of (pose name, (N,3) displacement field) for the mimic poses (zeros where unmapped)
Result:
  bones    (M,3) rest positions of the face bones
  weights  (N,M) bone weights; each row sums to the vertex's activity share a_v (the rest of the row stays on
           the vertex's original head/neck weights)
  trans    (K,M,3) per-pose bone translations (model space)

Method (translation-only skinning decomposition, SSDR-like):
  1. bones = weighted k-means over [position, scaled displacement signature] of the active vertices, so the
     upper and lower lip (adjacent, opposite motion) get different bones;
  2. alternate: per-vertex non-negative weights over nearby bones (sum = a_v, smoothness pull towards a
     distance kernel) <-> per-pose least-squares bone translations.
"""
import numpy as np


def side_mask(P, side, width):
    """smooth 0..1 mask for one half of the face; character's left is -x in W3 space."""
    if side is None:
        return np.ones(len(P))
    x = P[:, 0] if side == 'R' else -P[:, 0]
    return np.clip(0.5 + x / (2 * width), 0.0, 1.0)


def kmeans(X, w, k, iters=40, seed=0):
    rng = np.random.default_rng(seed)
    n = len(X)
    centers = [X[rng.choice(n, p=w / w.sum())]]
    d2 = np.sum((X - centers[0]) ** 2, axis=1)
    for _ in range(1, k):
        p = d2 * w
        p = p / p.sum() if p.sum() > 0 else np.full(n, 1 / n)
        centers.append(X[rng.choice(n, p=p)])
        d2 = np.minimum(d2, np.sum((X - centers[-1]) ** 2, axis=1))
    C = np.array(centers)
    lab = None
    for _ in range(iters):
        lab = np.argmin(((X[:, None, :] - C[None]) ** 2).sum(-1), axis=1)
        for j in range(k):
            m = lab == j
            if m.any():
                C[j] = np.average(X[m], axis=0, weights=w[m])
    return C, lab


def nnls(A, b, iters=60):
    """Lawson-Hanson non-negative least squares for small problems."""
    n = A.shape[1]
    x = np.zeros(n)
    passive = np.zeros(n, bool)
    w = A.T @ (b - A @ x)
    for _ in range(iters):
        if passive.all() or (w[~passive] <= 1e-12).all():
            break
        j = np.argmax(np.where(~passive, w, -np.inf))
        passive[j] = True
        while True:
            s = np.zeros(n)
            s[passive] = np.linalg.lstsq(A[:, passive], b, rcond=None)[0]
            if (s[passive] > 0).all():
                x = s
                break
            neg = passive & (s <= 0)
            alpha = np.min(x[neg] / (x[neg] - s[neg] + 1e-30))
            x = x + alpha * (s - x)
            passive &= x > 1e-12
            if not passive.any():
                break
        w = A.T @ (b - A @ x)
    return x


def solve(P, pose_targets, n_bones=80, act_thr=0.0008, sigma_scale=1.2, region_scale=1.5, k_near=3,
          lam=1e-4, sig_gain=2.0, cand=8, smooth=0.05, rounds=6):
    names = [n for n, _t in pose_targets]
    T = np.stack([t for _n, t in pose_targets])           # (K,N,3)
    K, N, _ = T.shape
    act = np.sqrt((T ** 2).sum(-1)).max(0)                 # (N,)
    active = act > act_thr
    ia = np.where(active)[0]
    # --- clustering features: position + displacement signature (PCA of the stacked pose displacements)
    sig = T[:, ia, :].transpose(1, 0, 2).reshape(len(ia), K * 3)
    sig = sig - sig.mean(0)
    U, S, Vt = np.linalg.svd(sig, full_matrices=False)
    ncomp = min(12, len(S))
    feat_sig = U[:, :ncomp] * S[:ncomp]
    pos_scale = np.sqrt(((P[ia] - P[ia].mean(0)) ** 2).sum(1).mean())
    sig_scale = np.sqrt((feat_sig ** 2).sum(1).mean()) + 1e-12
    F = np.hstack([P[ia] / pos_scale, sig_gain * feat_sig / sig_scale])
    _Cf, lab = kmeans(F, act[ia] + 1e-6, n_bones)
    C = np.array([np.average(P[ia][lab == j], axis=0, weights=act[ia][lab == j] + 1e-6) if (lab == j).any()
                  else P[ia][0] for j in range(n_bones)])
    M = len(C)
    dd = np.sqrt(((C[:, None] - C[None]) ** 2).sum(-1))
    np.fill_diagonal(dd, np.inf)
    spacing = float(np.median(dd.min(1)))
    sigma = spacing * sigma_scale
    # --- region and activity share
    da = np.sqrt(((P[:, None] - P[ia][None]) ** 2).sum(-1)).min(1)
    region = active | (da < spacing * region_scale)
    a = np.where(active, 1.0, np.clip(1.0 - da / (spacing * region_scale), 0.0, 1.0))
    a[~region] = 0.0
    R = np.where(region)[0]
    D = np.sqrt(((P[:, None] - C[None]) ** 2).sum(-1))     # (N,M)
    near = np.argsort(D, axis=1)[:, :cand]
    # kernel weights (smoothness prior / initial weights)
    Wk = np.zeros((N, M))
    kidx = near[:, :k_near]
    rows = np.arange(N)[:, None]
    ker = np.exp(-(D[rows, kidx] / sigma) ** 2)
    ker /= ker.sum(1, keepdims=True)
    Wk[rows, kidx] = ker * a[:, None]
    # initial weights: hard cluster membership for active vertices, kernel elsewhere
    W = Wk.copy()
    W[ia] = 0.0
    W[ia, lab] = 1.0
    Tr = T.transpose(1, 0, 2).reshape(N, K * 3)            # per-vertex stacked targets

    def solve_t(W):
        A = W[R]
        AtA = A.T @ A + lam * np.eye(M)
        return np.linalg.solve(AtA, A.T @ Tr[R])            # (M, K*3)

    hist = []
    for r in range(rounds):
        tb = solve_t(W)                                     # (M, K*3)
        # per-vertex weights over candidate bones, sum = a_v, pulled towards the kernel prior
        Wn = np.zeros_like(W)
        for v in R:
            c = near[v]
            A = tb[c].T                                     # (K*3, cand)
            y = Tr[v]
            pen = 10.0 * max(np.linalg.norm(A), 1e-6)
            A2 = np.vstack([A, pen * np.ones((1, len(c))), smooth * pen * np.eye(len(c))])
            y2 = np.concatenate([y, [pen * a[v]], smooth * pen * Wk[v, c]])
            x = nnls(A2, y2)
            keep = np.argsort(x)[::-1][:k_near]
            xs = np.zeros_like(x)
            xs[keep] = x[keep]
            if xs.sum() > 1e-9:
                xs *= a[v] / xs.sum()
            Wn[v, c] = xs
        W = Wn
        tb = solve_t(W)
        err = np.linalg.norm(W[R] @ tb - Tr[R]) / (np.linalg.norm(Tr[R]) + 1e-12)
        hist.append(float(err))
    trans = tb.reshape(M, K, 3).transpose(1, 0, 2)          # (K,M,3)
    errs = []
    for k, name in enumerate(names):
        t = T[k][R]
        tn = np.linalg.norm(t)
        rec = W[R] @ trans[k]
        errs.append((name, float(np.linalg.norm(rec - t) / tn) if tn > 1e-9 else 0.0, float(tn)))
    return {'bones': C, 'weights': W, 'activity': a, 'trans': trans, 'errors': errs, 'history': hist,
            'spacing': spacing, 'n_active': int(active.sum()), 'n_region': int(region.sum())}
