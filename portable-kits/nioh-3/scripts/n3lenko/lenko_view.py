"""Textured flat render of the Lenko source ($N3_BUILD/source) or of conformed.npz: per-triangle colour from the
material's texture at the UV centroid.
usage: lenko_view.py <out.png> [--conformed] [--ylim lo hi] [--hide mesh,mesh]   (source space: PMX units, Blender axes)"""
import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
from PIL import Image  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'n3build'))
from n3_common import BUILD, to_game_axes  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('out', help='output PNG')
    ap.add_argument('--conformed', action='store_true', help='render BUILD/conformed.npz (game space) instead of the source')
    ap.add_argument('--ylim', nargs=2, type=float, metavar=('LO', 'HI'), help='height range, with 16 grid lines')
    ap.add_argument('--hide', help='meshes to leave out, comma-separated')
    args = ap.parse_args()
    out = args.out
    conformed = args.conformed
    ylim = None
    if args.ylim:
        ylim = tuple(args.ylim)
    hide = set(args.hide.split(',')) if args.hide is not None else set()
    meta = json.loads((BUILD / 'source' / 'source.json').read_text(encoding='utf-8'))
    arr = np.load(BUILD / 'source' / 'source.npz')
    conf = np.load(BUILD / 'conformed.npz') if conformed else None
    texs, T, C = {}, [], []
    for m in meta['meshes']:
        if m['name'] in hide:
            continue
        k = m['key']
        pos = conf[k + '__pos'].astype(float) if conformed else to_game_axes(arr[k + '__co'].astype(float))
        lv = arr[k + '__loop_vertex']; tris = arr[k + '__tris']; uv = arr[k + '__loop_uv']; tm = arr[k + '__tri_material']
        T.append(pos[lv[tris]])
        c = uv[tris].mean(1)
        col = np.zeros((len(tris), 3))
        for mi, mat in enumerate(m['materials']):
            f = meta['textures'][mat['texture_file']]['file']
            if f not in texs:
                texs[f] = np.asarray(Image.open(f).convert('RGB'), float) / 255
            A = texs[f]; S = A.shape[0]; sel = tm == mi
            col[sel] = A[np.clip(((1 - c[sel, 1]) * S).astype(int), 0, S - 1), np.clip((c[sel, 0] * S).astype(int), 0, S - 1)]
        C.append(col)
    T = np.concatenate(T); C = np.concatenate(C)
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    L = np.array([0.3, 0.4, 0.85]); L /= np.linalg.norm(L)
    lit = np.clip(0.45 + 0.55 * np.abs(n @ L), 0, 1)
    fig, axs = plt.subplots(1, 3, figsize=(27, 12))
    # game axes: +z forward (towards a front viewer), +x the character's left (viewer's right from the front)
    for ax, (title, a0, dep, sgn) in zip(axs, [('front', 0, 2, 1), ('side (from her left, front to the right)', 2, 0, 1),
                                               ('back', 0, 2, -1)]):
        order = np.argsort(sgn * T[:, :, dep].mean(1))       # far first
        x = T[order][:, :, a0] * (-1 if (dep == 2 and sgn < 0) else 1)
        if dep == 2 and sgn > 0:
            x = x                                            # front: +x on the viewer's right
        y = T[order][:, :, 1]
        keep = np.ones(len(order), bool) if ylim is None else (y.max(1) > ylim[0]) & (y.min(1) < ylim[1])
        ax.add_collection(PolyCollection(np.stack([x, y], -1)[keep], facecolors=(C[order] * lit[order][:, None])[keep],
                                         edgecolors='none'))
        ax.set_aspect('equal'); ax.autoscale(); ax.set_title(title)
        if ylim:
            ax.set_ylim(*ylim)
            step = (ylim[1] - ylim[0]) / 16
            for g in np.arange(ylim[0], ylim[1] + 1e-9, step):
                ax.axhline(g, color='r', lw=0.3)
            ax.set_yticks(np.round(np.arange(ylim[0], ylim[1] + 1e-9, step), 2))
    plt.tight_layout(); plt.savefig(out, dpi=50); plt.close()
    print('triangles', len(T))


if __name__ == '__main__':
    main()
