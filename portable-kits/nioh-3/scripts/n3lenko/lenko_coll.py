"""Fit Lenko's collision sets to her body (bind pose); prints the constants for lenko_build.py.

lenko1 (in game) borrowed vanilla sets made for other clothes, far bigger than her:
- 'legs' (LLOC entry 1 of the helmet 0x6a0d18db, for its tassels): the hips ellipsoid reaches 8 cm in front of her belly,
  the thigh ellipsoids (semi-axes ~16 cm, centres x +-2.6) ~7 cm in front of her thighs. Her front pleats hang 1.5-4.5 cm
  in front of the skin, so at rest the front skirt chains started inside (r 0.64-0.66) and were pushed out: a bulge
  under the belt.
- 'torso' (entry 0 of the ninja chest 0x5548953f, for its scarf): a spine-bone sphere of radius ~25 cm centred at the
  navel reaches 14-28 cm in front of her belly below the bust; the necktie rested on it, sticking out in front.
- 'head' (entry 0 of the vanilla hair 0xd5d385f9): its chest-bone ellipsoid is a slab 118 cm deep front to back
  (semi-axes 15 / 11 / 59); her four long strands started inside it (r 0.59). 'lenko_hair' = 'head' with that one
  refitted to her upper back (coat included); the long strands also keep the vanilla 'torso' set lower down.
Here the vanilla ellipsoids that matter keep their bones and rotations (all axis-aligned at bind) and get new centres /
semi-axes: per ellipsoid, random search (fixed seed) for the one that covers most of its skin band within MARGIN cm
(then the most strictly, then the smallest) while every non-root point of the set's chains stays CLEAR cm outside.
For the skirt, two mirrored hips-bone ellipsoids then cover the back skin the rest leaves uncovered (her buttocks).
usage: lenko_coll.py   (conformed.npz / physics.json from N3_BUILD)
"""
import argparse
import json
import struct
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'n3build'))
from n3_common import BODY, BUILD, load_model, skeleton  # noqa: E402
import n3_g1m_physics as ph  # noqa: E402

if __name__ == '__main__':          # before the module-level body skeleton read below
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()

MARGIN = 1.0        # cm: skin up to this far outside an ellipsoid counts as covered
BUTT_MARGIN = 1.0   # cm: the buttocks ellipsoids reach this far beyond the back skin they cover
BUTT_CLEAR = 0.3    # cm
SAMPLES = 150000
# set -> vanilla base (model, LLOC entry), chain name prefix, CLEAR cm, skin meshes (|x| limit),
#        {primitive: (label, skin y range, 1 = left side only (mirrored to MIRROR) / 0 = centred,
#                     centre lo / hi, semi-axes lo / hi (world x y z))}
SETS = {
    'lenko_skirt': (('0x6a0d18db', 1), 'Skirt', 0.5, ('legwear', 'skin'), 20, {
        0: ('hips', (94, 110), 0, ((0, 96, -6), (0, 110, 4)), ((10, 5, 7), (20, 16, 16))),
        1: ('left thigh', (60, 95), 1, ((4, 70, -5), (12, 92, 2)), ((5, 10, 5), (12, 28, 12))),
        3: ('left knee', (36, 62), 1, ((5, 40, -5), (13, 60, 2)), ((4, 6, 4), (10, 18, 10))),
    }),
    'lenko_tie': (('0x5548953f', 0), 'Tie', 0.3, ('clothes', 'skin'), 12, {
        1: ('waist', (112, 128), 0, ((0, 110, -6), (0, 126, 3)), ((8, 6, 8), (18, 18, 14))),
        2: ('belly', (100, 116), 0, ((0, 98, -6), (0, 116, 3)), ((8, 6, 8), (18, 18, 14))),
        3: ('bust', (126, 150), 0, ((0, 124, -6), (0, 146, 4)), ((8, 6, 8), (20, 20, 16))),
    }),
    'lenko_hair': (('0xd5d385f9', 0), 'LongHair', 0.5, ('clothes', 'skin', 'coat'), 20, {
        0: ('upper back', (126, 156), 0, ((0, 126, -10), (0, 150, 2)), ((8, 6, 8), (22, 18, 20))),
    }),
}
MIRROR = {1: 2, 3: 4}

sk = skeleton(load_model(BODY)[1])


def primitives(base, extra=(), resize=None):
    b, n = ph.lloc_entry_bytes(*base, extra, resize)
    out = []
    for i in range(n):
        f = struct.unpack_from('<28f', b, 8 + 112 * i); u = struct.unpack_from('<28I', b, 8 + 112 * i)
        W = np.array(sk[u[1]]['world'])
        ax = W[:3, :3] @ np.array([f[8:11], f[12:15], f[16:19]]).T          # columns: primitive axes in world
        out.append({'bone': u[1], 'W': W, 'ax': ax, 'size': np.array(f[4:7]),
                    'c': W[:3, :3] @ np.array(f[20:23]) + W[:3, 3]})
    return out


def perm_of(p):
    """world axis of each primitive axis; the fit is axis-aligned, the written ellipsoid keeps the vanilla rotation
    (legs set tilted <= 3 deg, torso spine / chest spheres 8.5 deg about x), so the final check uses the written bytes"""
    perm = [int(np.argmax(np.abs(p['ax'][:, i]))) for i in range(3)]
    assert sorted(perm) == [0, 1, 2] and all(abs(p['ax'][perm[i], i]) > 0.98 for i in range(3)), p['ax']
    return perm


def r_al(P, c, s):
    """normalized radius of points P (n, 3) in axis-aligned ellipsoids c / s (m, 3) -> (m, n)"""
    return np.sqrt((((P[None] - c[:, None]) / s[:, None]) ** 2).sum(-1))


def r_prims(P, prims):
    return np.min([np.sqrt(((((P - p['c']) @ p['ax']) / p['size']) ** 2).sum(1)) for p in prims], 0)


def fit(skin, chain, clear, lo_c, hi_c, lo_s, hi_s, rng):
    best = None
    for _ in range(SAMPLES // 10000):
        c = rng.uniform(lo_c, hi_c, (10000, 3)); s = rng.uniform(lo_s, hi_s, (10000, 3))
        ok = r_al(chain, c, s + clear).min(1) >= 1
        c, s = c[ok], s[ok]
        if not len(c):
            continue
        cov1 = (r_al(skin, c, s + MARGIN) <= 1).mean(1)
        cov0 = (r_al(skin, c, s) <= 1).mean(1)
        key = np.round(cov1, 2) * 1e6 + np.round(cov0, 2) * 1e3 - s.prod(1) / 1e4
        i = int(np.argmax(key))
        if best is None or key[i] > best[0]:
            best = (key[i], c[i], s[i], cov1[i], cov0[i])
    assert best is not None, 'no ellipsoid clears the chain points'
    return best[1:]


def butt(z, world, chain):
    """mirrored hips-bone ellipsoids over the back skin (y 84-102) that `world` leaves uncovered by BUTT_MARGIN"""
    back = np.concatenate([z['legwear__pos'], z['belt__pos']]).astype(float)
    S = back[(back[:, 1] > 84) & (back[:, 1] < 102) & (back[:, 2] < -4) & (np.abs(back[:, 0]) < 14)]
    cov = np.zeros(len(S), bool)
    for c, s in world.values():
        cov |= r_al(S, c[None], np.maximum(s - BUTT_MARGIN, 0.1)[None])[0] <= 1
    need = S[~cov]
    print(f'  back skin y 84-102: {len(S)} points, {len(need)} not covered by {BUTT_MARGIN} cm')
    best = None
    sz = np.arange(4, 14.1, 1.0)
    for x0 in np.arange(2, 9.1, 1.0):
        for y0 in np.arange(88, 104.1, 1.0):
            for z0 in np.arange(-12, 0.1, 1.0):
                cs = np.array([[x0, y0, z0], [-x0, y0, z0]])
                for sx in np.arange(5, 14.1, 1.0):
                    for sy in np.arange(6, 16.1, 1.0):
                        s = np.stack([np.full_like(sz, sx), np.full_like(sz, sy), sz], 1)
                        okn = np.ones(len(sz), bool)
                        if len(need):
                            okn = (np.minimum(r_al(need, cs[[0] * len(sz)], s - BUTT_MARGIN),
                                              r_al(need, cs[[1] * len(sz)], s - BUTT_MARGIN)) <= 1).all(1)
                        okc = (np.minimum(r_al(chain, cs[[0] * len(sz)], s + BUTT_CLEAR),
                                          r_al(chain, cs[[1] * len(sz)], s + BUTT_CLEAR)) > 1).all(1)
                        for i in np.nonzero(okn & okc)[0]:
                            if best is None or s[i].prod() < best[0]:
                                best = (s[i].prod(), cs.copy(), s[i].copy())
    assert best is not None, 'no buttocks fit'
    _, cs, s = best
    R, t = sk[2]['world'][:3, :3], sk[2]['world'][:3, 3]
    print(f'  buttocks: world centres {cs[0].round(1)} / mirrored, semi-axes {s.round(1)}')
    return tuple((2, tuple(round(float(x), 2) for x in np.abs(R.T) @ s), tuple(round(float(x), 2) for x in R.T @ (c - t)))
                 for c in cs)


def main():
    z = np.load(BUILD / 'conformed.npz')
    phys = json.loads((BUILD / 'physics.json').read_text())
    rng = np.random.default_rng(7)
    for name, (base, prefix, clear, meshes, xlim, fits) in SETS.items():
        print(f'== {name} (from {base[0]} entry {base[1]}, chains {prefix}*, clear {clear} cm)')
        skin = np.concatenate([z[m + '__pos'].astype(float) for m in meshes])
        skin = skin[np.abs(skin[:, 0]) < xlim]
        chain = np.array([p for c in phys['chains'] if c['name'].startswith(prefix) for p in c['points'][1:]])
        prims = primitives(base)
        print(f'  vanilla: chain points r min {r_prims(chain, prims).min():.3f}')
        world = {}
        for k, (label, (y0, y1), side, (lo_c, hi_c), (lo_s, hi_s)) in fits.items():
            band = skin[(skin[:, 1] >= y0) & (skin[:, 1] <= y1) & ((skin[:, 0] > 0.5) if side else True)]
            c, s, cov1, cov0 = fit(band, chain, clear, lo_c, hi_c, lo_s, hi_s, rng)
            world[k] = (c, s)
            print(f'  {label:10s} skin {len(band):5d}: centre {c.round(1)} semi {s.round(1)} covered within {MARGIN} cm '
                  f'{cov1:.2f}, inside {cov0:.2f}   (vanilla centre {prims[k]["c"].round(1)} semi {prims[k]["size"].round(1)})')
            if side:
                world[MIRROR[k]] = (c * [-1, 1, 1], s)
        resize = {}
        for k, (c, s) in sorted(world.items()):
            p = prims[k]; perm = perm_of(p)
            resize[k] = (tuple(round(float(s[perm[i]]), 2) for i in range(3)),
                         tuple(round(float(x), 2) for x in p['W'][:3, :3].T @ (c - p['W'][:3, 3])))
        extra = butt(z, world, chain) if name == 'lenko_skirt' else ()
        final = primitives(base, extra, resize)
        print(f'  written set: {len(final)} ellipsoids, chain points r min {r_prims(chain, final).min():.3f}')
        print(f'  {name}: resize {resize}\n  {name}: extra {extra}')


if __name__ == '__main__':
    main()
