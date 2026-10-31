"""Fit mirrored hips-bone ellipsoids over Karin's buttocks: cover the back skin the 'legs' set misses by MARGIN cm,
keep every non-root skirt chain point outside by CLEAR cm. usage: fit_butt3.py MARGIN CLEAR Y_MAX
(build24: fit_butt3.py 2 0.3 102 -- skin and underwear between y 86 and Y_MAX, behind z -2, |x| < 14)"""
import argparse
import itertools
import json
import struct
import sys
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('margin', type=float, help='cm the ellipsoids must cover the skin by')
ap.add_argument('clear', type=float, help='cm every non-root skirt chain point stays outside')
ap.add_argument('y_max', type=float, help='top of the skin band to cover (cm)')
args = ap.parse_args()

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'n3build'))
from n3_common import BODY, BUILD, load_model, skeleton  # noqa: E402
import n3_g1m_physics as ph  # noqa: E402

MARGIN, CLEAR = args.margin, args.clear
_, m = load_model(BODY)
sk = skeleton(m)


def prims(name):
    b, n = ph.lloc_entry_bytes(*ph.COLLISION_SETS[name])
    out = []
    for i in range(n):
        f = struct.unpack_from('<28f', b, 8 + 112 * i); u = struct.unpack_from('<28I', b, 8 + 112 * i)
        W = sk[u[1]]['world']
        out.append((W[:3, :3] @ np.array(f[20:23]) + W[:3, 3], W[:3, :3] @ np.array([f[8:11], f[12:15], f[16:19]]).T,
                    np.array(f[4:7])))
    return out


def r_al(P, c, s):
    return np.sqrt((((P - c) / s) ** 2).sum(1))


legs = prims('legs')
z = np.load(BUILD / 'conformed.npz')
skin = np.concatenate([z['body_2__pos'], z['underwear__pos']])
S = skin[(skin[:, 1] > 86) & (skin[:, 1] < args.y_max) & (skin[:, 2] < -2) & (np.abs(skin[:, 0]) < 14)]
cov = np.zeros(len(S), bool)
for c, ax, s in legs:
    cov |= np.sqrt(((((S - c) @ ax) / np.maximum(s - MARGIN, 0.1)) ** 2).sum(1)) <= 1
need = S[~cov]
phys = json.loads((BUILD / 'physics.json').read_text())
pts = np.array([p for ch in phys['chains'] if ch['name'].startswith('Skirt') for p in ch['points'][1:]])
print(f'need {len(need)} skin points (y {need[:, 1].min():.1f}..{need[:, 1].max():.1f}); skirt chain points {len(pts)}')

best = None
for x0, y0, z0, sx, sy, sz in itertools.product(np.arange(2, 9.1, 1.0), np.arange(94, 106.1, 1.0), np.arange(-9, 0.1, 1.0),
                                                 np.arange(5, 14.1, 1.0), np.arange(6, 16.1, 1.0), np.arange(4, 14.1, 1.0)):
    s = np.array([sx, sy, sz])
    cs = (np.array([x0, y0, z0]), np.array([-x0, y0, z0]))
    if (np.minimum(r_al(need, cs[0], s - MARGIN), r_al(need, cs[1], s - MARGIN)) > 1).any():
        continue
    rp = min(r_al(pts, c, s + CLEAR).min() for c in cs)
    if rp <= 1:
        continue
    vol = sx * sy * sz
    if best is None or vol < best[0]:
        best = (vol, cs, s)
if best is None:
    raise SystemExit('no fit')
vol, cs, s = best
print(f'centres {cs[0].tolist()} / mirrored, semi-axes (x, y, z) {s.tolist()}')
# clearances
for P, label in ((pts, 'skirt chain points'), (z['skirt__pos'], 'skirt vertices'), (need, 'needed skin')):
    r = np.minimum(r_al(P, cs[0], s), r_al(P, cs[1], s))
    print(f'  {label:18s} r min {r.min():.3f} max {r.max():.3f}  inside {np.mean(r < 1):.2f}')
sk_r = np.minimum(r_al(pts, cs[0], s), r_al(pts, cs[1], s))
for k in np.argsort(sk_r)[:6]:
    print('    closest chain point', pts[k], round(float(sk_r[k]), 3))
# back profile at x = 6: ellipsoid back z vs skin vs skirt
for y in range(88, 113, 3):
    t = 1 - ((y - cs[0][1]) / s[1]) ** 2 - ((6 - cs[0][0]) / s[0]) ** 2
    ez = cs[0][2] - s[2] * np.sqrt(t) if t > 0 else float('nan')
    bs = (np.abs(skin[:, 1] - y) < 1.5) & (np.abs(skin[:, 0] - 6) < 2) & (skin[:, 2] < 0)
    ks = (np.abs(z['skirt__pos'][:, 1] - y) < 1.5) & (np.abs(z['skirt__pos'][:, 0] - 6) < 2) & (z['skirt__pos'][:, 2] < 0)
    print(f'  x 6, y {y}: ellipsoid back z {ez:6.1f}  skin {skin[bs, 2].min() if bs.any() else float("nan"):6.1f}  '
          f'skirt {z["skirt__pos"][ks, 2].max() if ks.any() else float("nan"):6.1f}')
hips = np.array(sk[2]['world'])
print('hips world rot\n', hips[:3, :3].round(3), '\npos', hips[:3, 3].round(2))
