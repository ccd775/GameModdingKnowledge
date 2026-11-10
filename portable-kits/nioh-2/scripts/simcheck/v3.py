"""Skirt weight experiment (the build-3 field): body transfer blended toward the thigh on each side by height
(blend()); prints total / worst penetration and stretch per pose for a few settings.
usage: v3.py   (build dir: N2_BUILD)"""
import argparse
if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
from v2 import *
import itertools, sys
LT, RT = 'g11', 'g12'
def blend(y_top=112.0, y_hem=80.0, lmax=0.85, p=1.0, a=6.0, sig0=1.0, it=3, c=0.0):
    Wn, _ = kern(sig0 + c * GAP)
    t = np.clip((y_top - SP[:, 1]) / (y_top - y_hem), 0, 1) ** p
    lam = lmax * t
    sL = np.clip(0.5 + 0.5 * SP[:, 0] / a, 0, 1); sL = sL * sL * (3 - 2 * sL)
    Wt = np.zeros_like(Wn); Wt[:, TOKS.index(LT)] = sL; Wt[:, TOKS.index(RT)] = 1 - sL
    W = (1 - lam[:, None]) * Wn + lam[:, None] * Wt
    return finish(W, it)
def score(gw, label, quiet=False):
    g0 = outer_grid(SP, Stris); tot = 0; worst = 0; st = []
    e = np.unique(np.sort(np.concatenate([Stris[:, [0, 1]], Stris[:, [1, 2]], Stris[:, [2, 0]]]), 1), axis=0)
    l0 = np.linalg.norm(SP[e[:, 0]] - SP[e[:, 1]], axis=1); big = l0 > 0.8
    rows = []
    for pn, kw in POSES.items():
        T = pose2(**kw); Sp = skin(SP, gw, T); g = outer_grid(Sp, Stris); n = 0; w = 0
        for bn, (P, tris, bgw, m) in BODY.items():
            r0s, r0 = lookup(g0, P)
            cov = np.isfinite(r0s) & (r0 < r0s - 0.2) & (P[:, 1] > 78) & (P[:, 1] < 121)
            Pp = skin(P[cov], [bgw[j] for j in np.nonzero(cov)[0]], T)
            rs, r = lookup(g, Pp); o = np.isfinite(rs) & (r > rs)
            n += o.sum(); w = max(w, np.where(o, r - rs, 0).max(initial=0))
        l1 = np.linalg.norm(Sp[e[:, 0]] - Sp[e[:, 1]], axis=1); rr = (l1 / np.maximum(l0, 1e-6))[big]
        rows.append(f'{pn}:{n}/{w:.1f}/{np.percentile(rr, 99):.1f}'); tot += n; worst = max(worst, w)
    if not quiet: print(f'{label:28s} total {tot:3d} worst {worst:3.1f} | ' + ' '.join(rows), flush=True)
    return tot, worst
if __name__ == '__main__':
    for yt, lm, p, a in [(112, .85, 1, 6), (112, .7, 1, 6), (115, .85, 1.5, 6), (110, .9, 1, 8), (115, .7, 1, 8), (118, .8, 1.5, 6)]:
        score(blend(yt, 80, lm, p, a), f'yt{yt} l{lm} p{p} a{a}')
