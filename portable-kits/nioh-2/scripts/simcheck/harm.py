"""Skirt weight experiment: body transfer at the waist, the nearest thigh skin at the hem, harmonic (Jacobi)
interpolation in between; prints stretch and penetration on the test2 poses per setting.
usage: harm.py   (build dir: N2_BUILD)"""
import argparse
if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
from xfer import *
from collections import Counter
from scipy.spatial import cKDTree

def mesh_nb(n, tris):
    nb_ = [set() for _ in range(n)]
    for t in tris:
        for i in range(3):
            nb_[t[i]].update((t[(i + 1) % 3], t[(i + 2) % 3]))
    return [np.array(sorted(s)) for s in nb_]

def hem_loop(SP, Stris):
    e = np.sort(np.concatenate([Stris[:, [0, 1]], Stris[:, [1, 2]], Stris[:, [2, 0]]]), 1)
    c = Counter(map(tuple, e))
    return np.unique(np.array([k for k, v in c.items() if v == 1]))

def leg_xfer(P, side):
    """weights of the nearest thigh skin (leg tokens only) on one side."""
    B, _, bgw, _ = BODY['body_2']
    legs = LEG[side]
    sel = [i for i in range(len(B)) if 60 < B[i, 1] < 100 and (B[i, 0] > 2 if side == 'L' else B[i, 0] < -2)
           and set(bgw[i]) <= {f'g{g}' for g in legs} | {'g0'} and any(t != 'g0' for t in bgw[i])]
    tree = cKDTree(B[sel])
    out = []
    for p in P:
        d, j = tree.query([p[0], p[1], p[2]], 6)
        acc = {}
        for jj in j:
            d0 = bgw[sel[jj]]; s = sum(w for t, w in d0.items() if t != 'g0')
            for t, w in d0.items():
                if t != 'g0': acc[t] = acc.get(t, 0) + w / s / len(j)
        out.append(acc)
    return out

def design(SP, Stris, y_top=108.0, f_hem=0.8, a=8.0, iters=400, hem_y=None):
    top_w, dmin = body_xfer(SP, Stris, 12, 2.0, 0)
    toks = sorted({t for d in top_w for t in d} | {f'g{g}' for s in LEG.values() for g in s}, key=lambda t: int(t[1:]))
    ti = {t: j for j, t in enumerate(toks)}
    nv = len(SP)
    W = np.zeros((nv, len(toks))); pin = np.zeros(nv, bool)
    for v in range(nv):
        if SP[v, 1] > y_top:
            for t, w in top_w[v].items(): W[v, ti[t]] = w
            W[v] /= W[v].sum(); pin[v] = True
    hem = hem_loop(SP, Stris) if hem_y is None else np.nonzero(SP[:, 1] < hem_y)[0]
    wl = leg_xfer(SP[hem], 'L'); wr = leg_xfer(SP[hem], 'R')
    for k, v in enumerate(hem):
        x = SP[v, 0]; sL = np.clip(0.5 + 0.5 * x / a, 0, 1); sL = sL * sL * (3 - 2 * sL)
        W[v] = 0; W[v, ti['g0']] = 1 - f_hem
        for t, w in wl[k].items(): W[v, ti[t]] += f_hem * sL * w
        for t, w in wr[k].items(): W[v, ti[t]] += f_hem * (1 - sL) * w
        pin[v] = True
    nb_ = mesh_nb(nv, Stris)
    free = np.nonzero(~pin)[0]
    # init free with top-transfer, then Jacobi harmonic iterations
    for v in free:
        for t, w in top_w[v].items(): W[v, ti[t]] = w
    for _ in range(iters):
        Wn = np.array([W[nb_[v]].mean(0) for v in free])
        W[free] = Wn
    out = []
    for v in range(nv):
        order = np.argsort(-W[v])[:4]
        out.append({toks[j]: float(W[v, j]) for j in order if W[v, j] > 1e-3})
    return out

def abs_stretch(Sgw, label):
    e = np.unique(np.sort(np.concatenate([Stris[:, [0, 1]], Stris[:, [1, 2]], Stris[:, [2, 0]]]), 1), axis=0)
    l0 = np.linalg.norm(SP[e[:, 0]] - SP[e[:, 1]], axis=1)
    s = []
    for pn in [p for p in ('run', 'sprint', 'kneeup', 'crouch') if p in POSES]:
        Sp = skin(SP, Sgw, pose2(**POSES[pn]))
        l1 = np.linalg.norm(Sp[e[:, 0]] - Sp[e[:, 1]], axis=1)
        r = l1 / np.maximum(l0, 1e-6); big = l0 > 0.8
        s.append(f'{pn} {np.percentile(r[big], 99):.2f}/{r[big].max():.2f}')
    print(f'{label:18s} stretch (p99/max, edges>0.8cm): ' + '  '.join(s))

if __name__ == '__main__':
    abs_stretch(chains['skirt'], 'current')
    gw, _ = body_xfer(SP, Stris, 12, 2.0, 5); abs_stretch(gw, 'xfer')
    for yt, fh, a in ((108, 0.8, 8), (108, 0.6, 8), (108, 0.8, 12), (104, 0.7, 10), (112, 0.7, 10)):
        gw = design(SP, Stris, yt, fh, a)
        lab = f'h{yt}/{fh}/{a}'
        abs_stretch(gw, lab)
        evaluate(gw, lab)
