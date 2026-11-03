"""Coat over skirt under skirt swings: every skirt chain swings rigidly about its root by a random angle (outward /
inward / sideways), skirt and coat are skinned with physics.json's weights (body bones still), and the skirt's
outermost radius is compared with the coat's innermost one per (azimuth, height) bin, as coat_skirt_gap.py does at rest.
usage: layer_swing.py [trials] [max deg]   (N3_BUILD)"""
import argparse
import json
import sys
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('trials', nargs='?', type=int, default=20, help='read but not used: the scenarios are fixed (default 20)')
ap.add_argument('max_deg', nargs='?', type=float, default=35, help='read but not used (default 35)')
args = ap.parse_args()

import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'n3build'))
from n3_common import BUILD as B  # noqa: E402
c = np.load(B / 'conformed.npz')
phys = json.loads((B / 'physics.json').read_text())
chains = phys['chains']
skirt_ci = [i for i, ch in enumerate(chains) if ch['name'].startswith('Skirt')]
trials = args.trials
amax = np.radians(args.max_deg)
rng = np.random.default_rng(3)


def tri_samples(name):
    P = c[f'{name}__pos'].astype(float); T = c[f'{name}__loop_vertex'][c[f'{name}__tris']]
    bary = np.array([(a, b, 1 - a - b) for a in np.linspace(0, 1, 4) for b in np.linspace(0, 1, 4) if a + b <= 1 + 1e-9])
    return P, T, bary


def rot(axis, ang):
    axis = axis / np.linalg.norm(axis); K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(ang) * K + (1 - np.cos(ang)) * K @ K


def deform(name, P, Rs):
    out = P.copy()
    wd = phys['weights'].get(name, {})
    for v, lst in wd.items():
        v = int(v); acc = np.zeros(3)
        for ci, j, w in lst:
            if ci >= 0 and ci in Rs:
                R, p0 = Rs[ci]; acc += w * (R @ (P[v] - p0) + p0)
            else:
                acc += w * P[v]
        out[v] = acc
    return out


Ps, Ts, bs = tri_samples('skirt'); Pc, Tc, bc = tri_samples('coat')
zc = -1.48
AB, YB = 10, 2.0


def bins(Pv, T, bary, coat):
    pts = np.einsum('kc,tcx->tkx', bary, Pv[T]).reshape(-1, 3)
    if coat:
        pts = pts[(np.abs(pts[:, 0]) < 24) & (pts[:, 1] < 118)]
    a = np.degrees(np.arctan2(pts[:, 0], pts[:, 2] - zc)); r = np.hypot(pts[:, 0], pts[:, 2] - zc)
    ia = ((a + 180) // AB).astype(int); iy = ((pts[:, 1] - 70) // YB).astype(int)
    key = ia * 1000 + iy
    out = {}
    order = np.argsort(key)
    k_sorted, r_sorted = key[order], r[order]
    cuts = np.r_[0, np.nonzero(np.diff(k_sorted))[0] + 1, len(k_sorted)]
    for s, e in zip(cuts[:-1], cuts[1:]):
        if e - s > 3:
            out[k_sorted[s]] = (r_sorted[s:e].min(), r_sorted[s:e].max())
    return out



from scipy.spatial import cKDTree


def surface(Pv, T, bary):
    tri = Pv[T]
    pts = np.einsum('kc,tcx->tkx', bary, tri)
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    return pts.reshape(-1, 3), np.repeat(n, len(bary), 0)


# outward orientation per skirt triangle from the rest pose (normal along the horizontal radial direction)
pts0, n0 = surface(Ps, Ts, bs)
rad = pts0.copy(); rad[:, 1] = 0; rad[:, 2] -= zc; rad /= np.linalg.norm(rad, axis=1, keepdims=True) + 1e-12
flip = np.where((n0 * rad).sum(1) < 0, -1.0, 1.0)
wd = phys['weights']['coat']
cv = np.array(sorted(int(v) for v in wd))                     # coat vertices on chain weights
cv = cv[(np.abs(Pc[cv, 0]) < 24)]
# rest correspondence: each coat vertex's nearest skirt sample and its signed offset there
d0, src = cKDTree(pts0).query(Pc[cv])
off0 = ((Pc[cv] - pts0[src]) * (n0 * flip[:, None])[src]).sum(1)
ok0 = (d0 < 4.0) & (off0 > 0.3)
print('coat verts over the skirt and outside it at rest:', ok0.sum(), 'of', len(cv))


def scenario(kind, A, az0=0.0, rng_=None):
    Rs = {}
    for ci in skirt_ci:
        P = np.array(chains[ci]['points']); p0 = P[0]
        radial = P[-1] - p0; radial[1] = 0; radial /= np.linalg.norm(radial) + 1e-9
        tang = np.cross([0, 1, 0], radial)
        az = np.arctan2(radial[0], radial[2])
        if kind == 'sway':          # inertia: every chain swings about one horizontal axis (direction az0)
            axis = np.cross([0, 1, 0], [np.sin(az0), 0, np.cos(az0)])
            R = rot(axis, A)
        elif kind == 'leg':         # a thigh pushing out at az0: outward swing falling off with azimuth
            R = rot(tang, A * max(0.0, np.cos(az - az0)) ** 2)
        else:                       # independent random swings
            R = rot(tang, rng_.uniform(-A, A)) @ rot(radial, rng_.uniform(-A / 2, A / 2))
        Rs[ci] = (R, p0)
    sd = deform('skirt', Ps, Rs); cd = deform('coat', Pc, Rs)[cv]
    sp, sn = surface(sd, Ts, bs); sn = sn * flip[:, None]
    off = ((cd - sp[src]) * sn[src]).sum(1)
    bad = ok0 & (off < 0)
    return bad.sum(), (off - off0)[ok0].min()


for kind, A, az0 in [('sway', 20, 0), ('sway', 20, 90), ('sway', 20, 180), ('sway', 35, 45), ('leg', 30, 25),
                     ('leg', 30, -25), ('leg', 45, 25), ('leg', 30, 180)]:
    n, dmin = scenario(kind, np.radians(A), np.radians(az0))
    print(f'{kind:5s} {A:3d} deg toward az {az0:4d}: crossed {n:4d}, largest gap loss {dmin:+.2f} cm')
r2 = np.random.default_rng(5)
res = [scenario('random', np.radians(A), rng_=r2) for A in (10, 20, 35) for _ in range(4)]
print('independent random swings 10/20/35 deg (4 each): crossed', [int(n) for n, _ in res],
      'largest gap loss', [round(float(d), 2) for _, d in res])

# debug the back push: which coat vertices cross, and how many weight entries their source skirt point mixes
Rs = {}
for ci in skirt_ci:
    P = np.array(chains[ci]['points']); p0 = P[0]
    radial = P[-1] - p0; radial[1] = 0; radial /= np.linalg.norm(radial) + 1e-9
    tang = np.cross([0, 1, 0], radial); az = np.arctan2(radial[0], radial[2])
    Rs[ci] = (rot(tang, np.radians(30) * max(0.0, np.cos(az - np.pi)) ** 2), p0)
sd = deform('skirt', Ps, Rs); cd = deform('coat', Pc, Rs)[cv]
sp, sn = surface(sd, Ts, bs); sn = sn * flip[:, None]
off = ((cd - sp[src]) * sn[src]).sum(1)
bad = np.nonzero(ok0 & (off < 0))[0]
sk_w = phys['weights']['skirt']
for b in bad[:8]:
    v = cv[b]; t, k = divmod(int(src[b]), len(bs))
    mix = {}
    for cc, sv in zip(bs[k], Ts[t]):
        for ci, j, x in sk_w.get(str(int(sv)), []):
            mix[ci, j] = mix.get((ci, j), 0) + cc * x
    top = sorted(mix.values(), reverse=True)
    print(f'coat v {v} at {Pc[v].round(1)} rest off {off0[b]:.2f} -> {off[b]:.2f}; source mixes {len(mix)} entries, '
          f'top6 share {sum(top[:6]) / max(sum(top), 1e-9):.3f}, chains {sorted({ci for ci, _ in mix if ci >= 0})}; '
          f'coat list {len(wd[str(v)])}')
