import sys
from common import *
from scipy.spatial import cKDTree
chains = nb.retarget_hair_and_skirt(meta, arr, conf)
SP, Stris, _, sm = mesh('skirt')
BODY = {n: mesh(n) for n in ('body_2', 'underwear', 'knee_socks')}
POSES = {'stance': dict(abdL=12, abdR=12, flexL=10, flexR=10),
         'walk': dict(flexL=30, flexR=-20, twist=8), 'run': dict(flexL=50, flexR=-30, twist=15, bend=10),
         'run2': dict(flexL=-30, flexR=50, twist=-15, bend=10),
         'side': dict(abdL=25), 'twist20': dict(twist=20), 'bend20': dict(bend=20), 'lean-back': dict(bend=-12),
         'crouch': dict(flexL=70, flexR=70, bend=25)}
LEGTOK = {f'g{g}' for s in LEG.values() for g in s}
def evaluate(Sgw, label):
    g0 = outer_grid(SP, Stris)
    tot_all = 0
    for pn, kw in POSES.items():
        T = pose2(**kw)
        Sp = skin(SP, Sgw, T)
        g = outer_grid(Sp, Stris)
        tot = 0; worst = 0; rows = []
        for bn, (P, tris, gw, m) in BODY.items():
            r0s, r0 = lookup(g0, P)
            cov = np.isfinite(r0s) & (r0 < r0s - 0.2) & (P[:, 1] > 78) & (P[:, 1] < 121)
            if not cov.any(): continue
            Pp = skin(P[cov], [gw[i] for i in np.nonzero(cov)[0]], T)
            rs, r = lookup(g, Pp)
            out = np.isfinite(rs) & (r > rs)
            pen = np.where(out, r - rs, 0)
            tot += out.sum(); worst = max(worst, pen.max(initial=0))
            if out.any():
                phi, _ = cyl(Pp[out])
                rows.append(f'{bn}:{out.sum()} (phi {np.percentile(phi,5):.0f}-{np.percentile(phi,95):.0f}, y {Pp[out,1].min():.0f}-{Pp[out,1].max():.0f})')
        # stretch of skirt edges
        e = np.concatenate([Stris[:, [0, 1]], Stris[:, [1, 2]], Stris[:, [2, 0]]])
        l0 = np.linalg.norm(SP[e[:, 0]] - SP[e[:, 1]], axis=1); l1 = np.linalg.norm(Sp[e[:, 0]] - Sp[e[:, 1]], axis=1)
        st = (l1 / np.maximum(l0, 1e-6))
        tot_all += tot
        print(f'{label:8s} {pn:9s} poke {tot:5d} v, max {worst:4.1f} cm | stretch p99 {np.percentile(st,99):.2f} max {st.max():.2f}  ' + '; '.join(rows))
    return tot_all
