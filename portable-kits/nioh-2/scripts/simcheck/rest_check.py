"""Skirt at rest on synthetic poses (stance, walk, run, sprint, side, back kick, crouch): the build-4 skinning after
one simulation step (reset) vs the build-3 weight field; mean / p95 / max difference and skin vertices outside
the skirt for both.
usage: rest_check.py   (build dir: N2_BUILD)"""
import argparse
if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
from simpy import *
# rest-state check: sim at equilibrium (one reset step) for each static pose vs build-3 field skinning
gw3 = blend(112, 80, 0.85, 1, 6)
POSES.clear()
POSES.update({'stance': dict(abdL=12, abdR=12, flexL=10, flexR=10), 'walk': dict(flexL=30, flexR=-20, twist=8),
              'run': dict(flexL=50, flexR=-30, twist=15, bend=10), 'sprint': dict(flexL=75, flexR=-35, twist=12, bend=15),
              'sprintR': dict(flexR=75, flexL=-35, twist=-12, bend=15), 'side': dict(abdL=30), 'back-kick': dict(flexL=-45),
              'crouch': dict(flexL=70, flexR=70, bend=25)})
g0 = outer_grid(SP, Stris)
def pokes(Sp, T):
    g = outer_grid(Sp, Stris); n = 0; w = 0
    for bn, (P, tris, bgw, m) in BODY.items():
        r0s, r0 = lookup(g0, P)
        cov = np.isfinite(r0s) & (r0 < r0s - 0.2) & (P[:, 1] > 78) & (P[:, 1] < 121)
        Pp = skin(P[cov], [bgw[j] for j in np.nonzero(cov)[0]], T)
        rs, r = lookup(g, Pp); o = np.isfinite(rs) & (r > rs)
        n += o.sum(); w = max(w, np.where(o, r - rs, 0).max(initial=0))
    return n, w
for pn, kw in POSES.items():
    T = pose2(**kw)
    sim = Sim(); bones = sim.step(T, T)
    Sp4 = skin_all(SP, SKIRT_GW, T, bones); Sp3 = skin(SP, gw3, T)
    d = np.linalg.norm(Sp4 - Sp3, axis=1)
    n4, w4 = pokes(Sp4, T); n3, w3 = pokes(Sp3, T)
    print(f'{pn:9s} b4-rest vs b3: mean {d.mean():.2f} p95 {np.percentile(d, 95):.2f} max {d.max():.2f} cm | pokes b4 {n4}/{w4:.1f}  b3 {n3}/{w3:.1f}')
