"""How well the skirt's collision ellipsoids ('legs' set) cover Karin's hips / buttocks vs the vanilla body (bind pose).
usage: coll_cover.py   (orig/ and conformed.npz from N3_BUILD)"""
import argparse
import struct
import sys
from pathlib import Path

argparse.ArgumentParser(description=__doc__).parse_args()

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'n3build'))
from n3_common import BODY, BUILD, load_model, skeleton  # noqa: E402
import n3_conform  # noqa: E402
import n3_g1m_physics as ph  # noqa: E402


def prims(name):
    b, n = ph.lloc_entry_bytes(*ph.COLLISION_SETS[name])
    out = []
    for i in range(n):
        f = struct.unpack_from('<28f', b, 8 + 112 * i); u = struct.unpack_from('<28I', b, 8 + 112 * i)
        R = np.array([f[8:11], f[12:15], f[16:19]])
        out.append({'shape': u[0], 'bone': u[1], 'size': np.array(f[4:7]), 'R': R, 'off': np.array(f[20:23])})
    return out


_, m = load_model(BODY)
sk = skeleton(m)


def world(p, rows=True):
    W = sk[p['bone']]['world']
    c = W[:3, :3] @ p['off'] + W[:3, 3]
    ax = (W[:3, :3] @ (p['R'] if not rows else p['R'].T))   # columns = local axes in world
    return c, ax


def rnorm(P, cols, rows=True):
    best = np.full(len(P), np.inf); which = np.full(len(P), -1)
    for k, p in enumerate(cols):
        c, ax = world(p, rows)
        loc = (P - c) @ ax
        r = np.sqrt(((loc / p['size']) ** 2).sum(1))
        better = r < best; best[better] = r[better]; which[better] = k
    return best, which


legs = prims('legs')
for p in legs:
    c, ax = world(p)
    print(f"bone {p['bone']:3d} size {p['size'].round(1)} centre {c.round(1)}  long axis {ax[:, np.argmax(p['size'])].round(2)}")

z = np.load(BUILD / 'conformed.npz')
karin = {n: z[n + '__pos'] for n in ('body_2', 'underwear', 'skirt')}
vb, _ = n3_conform.body_reference()
print('\nbone 2 (hips) pos', sk[2]['pos'].round(1), ' thighs', sk[3]['pos'].round(1), sk[4]['pos'].round(1),
      ' knees', sk[5]['pos'].round(1))

for rows in (True, False):
    print(f'\n=== rotation as {"rows" if rows else "columns"} ===')
    for label, P in (('vanilla body', vb), ('karin body_2', karin['body_2']), ('karin underwear', karin['underwear'])):
        sel = (P[:, 1] > 80) & (P[:, 1] < 112) & (P[:, 2] < -3)      # back, waist to below the buttocks
        r, w = rnorm(P[sel], legs, rows)
        print(f'{label:16s} back verts {sel.sum():5d}: inside {np.mean(r < 1):.2f}  r p50 {np.median(r):.2f} p90 '
              f'{np.percentile(r, 90):.2f} max {r.max():.2f}')
        for y0 in range(80, 112, 4):
            s = (P[sel][:, 1] >= y0) & (P[sel][:, 1] < y0 + 4)
            if s.any():
                zz = P[sel][s][:, 2]
                print(f'    y {y0:3d}-{y0 + 4:3d}: n {s.sum():4d} back-most z {zz.min():6.1f}  r max {r[s].max():.2f}'
                      f'  outside {np.mean(r[s] > 1):.2f}')
    sk_r, _ = rnorm(karin['skirt'], legs, rows)
    print(f'karin skirt verts inside a collider: {np.mean(sk_r < 1):.2f}')
