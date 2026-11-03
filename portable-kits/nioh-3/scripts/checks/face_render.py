"""Z-buffered textured front render of the conformed face (game space) at rest, under game poses (face.json weights)
and at the MMD shape-key target. usage: face_render.py <out.png> <model dir>   (N3_BUILD; model dir: the source model's
folder, which the texture_file names in source/source.json are relative to)"""
import argparse
import json
import sys
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('out_png'); ap.add_argument('model_dir', help='source model folder (e.g. the one with Lenko06.pmx and tex/)')
args = ap.parse_args()

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
import face_sim as fs  # noqa: E402  (loads data, prints its table)

MODEL = Path(args.model_dir)
src = json.loads((fs.BUILD / 'source' / 'source.json').read_text(encoding='utf-8'))
mesh = [m for m in src['meshes'] if m['name'] == 'Body'][0]
tex = [np.asarray(Image.open(MODEL / m['texture_file']).convert('RGB'), float) / 255 for m in mesh['materials']]
LV = fs.conf['Body__loop_vertex']; UV = fs.conf['Body__loop_uv']; T = fs.conf['Body__tris']; TM = fs.conf['Body__tri_material']


def render(Pv, box, res=600):
    x0, x1, y0, y1 = box
    img = np.ones((res, res, 3)); zb = np.full((res, res), -np.inf)
    for t, mi in zip(T, TM):
        A = tex[mi]; S = A.shape[0]
        vi = LV[t]; p = Pv[vi]; uv = UV[t]
        sx = (p[:, 0] - x0) / (x1 - x0) * res
        sy = (y1 - p[:, 1]) / (y1 - y0) * res
        lx, hx = int(max(np.floor(sx.min()), 0)), int(min(np.ceil(sx.max()), res - 1))
        ly, hy = int(max(np.floor(sy.min()), 0)), int(min(np.ceil(sy.max()), res - 1))
        if lx > hx or ly > hy:
            continue
        X, Y = np.meshgrid(np.arange(lx, hx + 1) + 0.5, np.arange(ly, hy + 1) + 0.5)
        dd = (sy[1] - sy[2]) * (sx[0] - sx[2]) + (sx[2] - sx[1]) * (sy[0] - sy[2])
        if abs(dd) < 1e-12:
            continue
        a = ((sy[1] - sy[2]) * (X - sx[2]) + (sx[2] - sx[1]) * (Y - sy[2])) / dd
        b = ((sy[2] - sy[0]) * (X - sx[2]) + (sx[0] - sx[2]) * (Y - sy[2])) / dd
        c = 1 - a - b
        ins = (a >= 0) & (b >= 0) & (c >= 0)
        if not ins.any():
            continue
        z = a * p[0, 2] + b * p[1, 2] + c * p[2, 2]          # game +z = forward = towards the viewer
        u = a * uv[0, 0] + b * uv[1, 0] + c * uv[2, 0]; v = a * uv[0, 1] + b * uv[1, 1] + c * uv[2, 1]
        ys, xs = np.nonzero(ins); gy, gx = ys + ly, xs + lx
        zz = z[ys, xs]; win = zz > zb[gy, gx]
        gy, gx = gy[win], gx[win]
        zb[gy, gx] = zz[win]
        vv = v[ys, xs][win]; uu = u[ys, xs][win]
        img[gy, gx] = A[np.clip(((1 - vv) * S).astype(int), 0, S - 1), np.clip((uu * S).astype(int), 0, S - 1)]
    return (img * 255).astype(np.uint8)


P = fs.P
eye = P[fs.lidL | fs.lidR]
cx, cy = 0.0, eye[:, 1].mean()
box = (cx - 13, cx + 13, cy - 9, cy + 17)
panels = [('rest', P), ('pose 41+42', P + fs.disp({41: 1, 42: 1})), ('MMD target', P + fs.blinkL + fs.blinkR),
          ('pose 27+28', P + fs.disp({27: 1, 28: 1})), ('pose 39+40', P + fs.disp({39: 1, 40: 1}))]
imgs = [render(p, box) for _, p in panels]
Image.fromarray(np.concatenate(imgs, 1)).save(args.out_png)
print('saved', [n for n, _ in panels])
