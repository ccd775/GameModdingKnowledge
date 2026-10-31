"""Flat-shaded orthographic previews (front / side / back) of ascii meshes, painter's algorithm, PIL only.

python preview.py <out.jpg> <ascii>[#sub,sub] ... [--ref=<ascii>,<ascii>...] [--size=900] [--tex=<page.png>]
Karin submeshes are drawn shaded (textured with --tex when given, sampling UV0); --ref meshes are drawn grey behind.
"""
import argparse
import sys

import numpy as np
from PIL import Image, ImageDraw

from ds2ascii import read_meshes

LIGHT = np.array([0.3, 0.6, 0.75])
LIGHT = LIGHT / np.linalg.norm(LIGHT)


def load(spec, has_skeleton):
    path, _, sel = spec.partition('#')
    _, meshes = read_meshes(path, has_skeleton=has_skeleton)
    if sel:
        meshes = [meshes[int(i)] for i in sel.split(',')]
    return meshes


def project(P, view):
    if view == 'front':      # looking at the face (-y), x to the viewer's left
        return np.c_[-P[:, 0], P[:, 2]], P[:, 1]
    if view == 'back':
        return np.c_[P[:, 0], P[:, 2]], -P[:, 1]
    return np.c_[P[:, 1], P[:, 2]], P[:, 0]     # side: looking from +x


def draw(img, meshes, view, scale, ox, oy, tex=None, grey=False):
    dr = ImageDraw.Draw(img)
    tris = []
    for m in meshes:
        P = m['pos']
        F = m['faces']
        if len(np.unique(P.round(5), axis=0)) <= 1:
            continue  # collapsed
        xy, depth = project(P, view)
        a, b, c = P[F[:, 0]], P[F[:, 1]], P[F[:, 2]]
        n = np.cross(b - a, c - a)
        n /= np.linalg.norm(n, axis=1, keepdims=True).clip(1e-12)
        shade = 0.35 + 0.65 * np.abs(n @ LIGHT)
        d = depth[F].mean(1)
        if tex is not None and not grey:
            uv = m['uv'][0][F].mean(1)
            px = (np.clip(uv[:, 0], 0, 1) * (tex.shape[1] - 1)).astype(int)
            py = (np.clip(1 - uv[:, 1], 0, 1) * (tex.shape[0] - 1)).astype(int)
            col = tex[py, px, :3].astype(float)
        else:
            col = np.full((len(F), 3), 150.0 if grey else 200.0)
        for k in range(len(F)):
            tris.append((d[k], xy[F[k]], col[k] * shade[k] * (0.6 if grey else 1.0)))
    tris.sort(key=lambda t: -t[0])
    for _, q, c in tris:
        dr.polygon([(ox + float(x) * scale, oy - float(y) * scale) for x, y in q], fill=tuple(int(v) for v in c))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out'); ap.add_argument('specs', nargs='*', metavar='<ascii>[#sub,sub]')
    ap.add_argument('--ref', default='', metavar='<ascii>,<ascii>...')
    ap.add_argument('--size', type=int, default=900)
    ap.add_argument('--tex', metavar='<page.png>')
    a = ap.parse_intermixed_args()
    out, size, specs = a.out, a.size, a.specs
    refs = a.ref.split(',') if a.ref else []
    tex = np.asarray(Image.open(a.tex).convert('RGB')) if a.tex else None
    kar = [m for s in specs for m in load(s, True)]
    ref = [m for s in refs for m in load(s, False)]
    views = ('front', 'side', 'back')
    img = Image.new('RGB', (size * len(views), size), (40, 40, 48))
    scale = size / 2.1
    for i, v in enumerate(views):
        draw(img, ref, v, scale, size * i + size / 2, size - 20, grey=True)
        draw(img, kar, v, scale, size * i + size / 2, size - 20, tex=tex)
    img.save(out, quality=85)


if __name__ == '__main__':
    main()
