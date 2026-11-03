"""Static coat / skirt overlap at bind pose (game cm): per azimuth (0 = front +z, +90 = character's left +x) and
height, the skirt's outermost radius vs the coat's innermost radius, from dense samples of the triangles.
usage: coat_skirt_gap.py   (N3_BUILD)"""
import argparse
import sys
from pathlib import Path

argparse.ArgumentParser(description=__doc__).parse_args()

import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'n3build'))
from n3_common import BUILD as B  # noqa: E402
c = np.load(B / 'conformed.npz')
rng = np.random.default_rng(1)


def samples(name, n_per=6):
    P = c[f'{name}__pos'].astype(float); LV = c[f'{name}__loop_vertex']; T = c[f'{name}__tris']
    tri = P[LV[T]]
    a = rng.random((len(tri), n_per, 2)); flip = a.sum(2) > 1; a[flip] = 1 - a[flip]
    pts = tri[:, None, 0] + a[..., :1] * (tri[:, None, 1] - tri[:, None, 0]) + a[..., 1:] * (tri[:, None, 2] - tri[:, None, 0])
    return np.concatenate([tri.reshape(-1, 3), pts.reshape(-1, 3)])


sk = samples('skirt')
co = samples('coat')
co = co[(np.abs(co[:, 0]) < 24) & (co[:, 1] < 118)]          # coat body below the belt line, no sleeves / hands
ring = sk[(sk[:, 1] > 108) & (sk[:, 1] < 112)]
zc = (ring[:, 2].min() + ring[:, 2].max()) / 2
print('axis z', round(zc, 2), 'coat y range', co[:, 1].min().round(1), co[:, 1].max().round(1))


def cyl(p):
    return np.degrees(np.arctan2(p[:, 0], p[:, 2] - zc)), np.hypot(p[:, 0], p[:, 2] - zc)


sa, sr = cyl(sk); ca, cr = cyl(co)
AB = 10; YB = 2.0
rows = []
for a0 in np.arange(-180, 180, AB):
    for y0 in np.arange(86, 118, YB):
        s = (sa >= a0) & (sa < a0 + AB) & (sk[:, 1] >= y0) & (sk[:, 1] < y0 + YB)
        k = (ca >= a0) & (ca < a0 + AB) & (co[:, 1] >= y0) & (co[:, 1] < y0 + YB)
        if s.sum() > 3 and k.sum() > 3:
            rows.append((a0, y0, sr[s].max(), cr[k].min(), cr[k].max()))
rows = np.array(rows)
gap = rows[:, 3] - rows[:, 2]
print(f'bins {len(rows)}; skirt outside coat inner surface (gap < 0): {(gap < 0).sum()}, gap < 0.5 cm: {(gap < 0.5).sum()}')
print(' az    y    skirt r  coat r in/out  gap')
for r, g in sorted(zip(rows, gap), key=lambda t: t[1])[:30]:
    print(f'{r[0]:5.0f} {r[1]:5.0f}   {r[2]:6.2f}   {r[3]:6.2f}/{r[4]:6.2f}  {g:+6.2f}')
# per azimuth: coat hem vs skirt hem
print('\n az   skirt hem  coat hem  coat-skirt')
for a0 in np.arange(-180, 180, 30):
    s = (sa >= a0) & (sa < a0 + 30); k = (ca >= a0) & (ca < a0 + 30)
    if s.any() and k.any():
        print(f'{a0:5.0f}  {sk[s, 1].min():7.1f}  {co[k, 1].min():7.1f}  {co[k, 1].min() - sk[s, 1].min():+6.1f}')
