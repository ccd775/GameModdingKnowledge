"""Offline preview of the fitted Karin geometry next to the hero LOD0 mesh (same scale, front + side).
  python sm2_preview.py --target peter [--npz ...] [--out ...png]"""
import argparse, os, sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render                               # noqa: E402
from sm2_karin_geo import Hero, TARGETS, WORK, gltf_to_got   # noqa: E402

COL = {'body': (240, 200, 180), 'face': (250, 220, 200), 'face_alpha': (255, 120, 120), 'hair': (240, 230, 170),
       'hair_alpha': (250, 240, 190), 'costume': (110, 140, 220)}


def load_parts(npz):
    z = np.load(npz)
    parts = {}
    for k in z.files:
        part, f = k.split('__')
        if part.startswith('_'):
            continue
        parts.setdefault(part, {})[f] = z[k]
    return parts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--target', choices=TARGETS, required=True)
    ap.add_argument('--npz')
    ap.add_argument('--out')
    a = ap.parse_args()
    bdir = os.path.join(WORK, f'build_{a.target}')
    parts = load_parts(a.npz or os.path.join(bdir, 'karin_geo.npz'))
    hero = Hero(os.path.join(WORK, 'native', TARGETS[a.target]))
    km = [(gltf_to_got(d['P']), d['T'].reshape(-1, 3), COL.get(k, (200, 200, 200))) for k, d in parts.items()]
    hm = []
    for me in hero.m.meshes:
        if (me.skin_info >> 16) == 1 and me.index_count >= 3:
            d = hero.m.decode(me)
            hm.append((gltf_to_got(d['pos']), d['idx'].reshape(-1, 3), (170, 170, 170)))
    allv = np.concatenate([m[0] for m in km + hm])
    bounds = (allv.min(0), allv.max(0))
    joints = gltf_to_got(hero.J[[i for i in sorted(hero.deform)]])
    ims = [render.render_mesh(km, os.devnull + '.png' if False else os.path.join(bdir, '_k.png'), joints=joints, W=420,
                              H=900, bounds=bounds, views=((1, 2, 1), (0, 2, 1))),
           render.render_mesh(hm, os.path.join(bdir, '_h.png'), joints=None, W=420, H=900, bounds=bounds,
                              views=((1, 2, 1), (0, 2, 1)))]
    out = Image.new('RGB', (sum(i.width for i in ims), 900), 'white')
    x = 0
    for im in ims:
        out.paste(im, (x, 0))
        x += im.width
    dst = a.out or os.path.join(bdir, 'preview_fit.png')
    out.save(dst)
    for f in ('_k.png', '_h.png'):
        os.remove(os.path.join(bdir, f))
    print(dst)


if __name__ == '__main__':
    main()
