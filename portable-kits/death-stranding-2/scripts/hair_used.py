"""Mask of the hair atlas (67704) cells that vanilla hair cards use: union of UV0 of every mesh on the hair skeleton
(1A0C) in the 50121 / 67700 / 50120 exports, all LODs, at 512 cells, grown by 2 cells. Primitives covering nearly the
whole square (depth / shadow proxies on other textures) are left out."""
import argparse
import glob, os, re, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_dilation
import ds2ascii as H
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--work', help='export root holding g50121 / g67700 / g50120 (default DS2_MODDING/work)')
ap.add_argument('--out', help='mask PNG (default <work>/g50121/hair_used.png)')
args = ap.parse_args()
if not args.work and not os.environ.get('DS2_MODDING'):
    raise SystemExit('set DS2_MODDING (the modding workspace) or pass --work')
WORK = args.work or os.path.join(os.environ['DS2_MODDING'], 'work')
R = 512
union = np.zeros((R, R), bool)
for d in (os.path.join(WORK, 'g50121'), os.path.join(WORK, 'g67700'), os.path.join(WORK, 'g50120')):
    for ld in sorted(glob.glob(os.path.join(d, 'lod*'))):
        log = open(os.path.join(ld, 'export.log'), encoding='utf-8-sig', errors='replace').read()
        skel = {int(m): s for m, s in re.findall(r'Mesh (\d+) with skeleton (\w+) ', log)}
        for f in sorted(glob.glob(os.path.join(ld, '*.ascii'))):
            if '_skel_' in f:
                continue
            try:
                ms = H.read_meshes(f)[1]
            except Exception as e:
                print('skip', f, e); continue
            for m in ms:
                mm = re.match(r'mesh_(\d+)_sm_', m['name'])
                if not mm or skel.get(int(mm.group(1))) != '1A0C':
                    continue
                uv = np.asarray(m['uv'][0])
                im = Image.new('L', (R, R), 0); dr = ImageDraw.Draw(im)
                for t in np.asarray(m['faces']):
                    dr.polygon([tuple(uv[k] * R) for k in t], fill=255, outline=255)
                a = np.asarray(im) > 0
                print(os.path.relpath(f, WORK), m['name'], 'cover %.3f' % a.mean(), 'skip' if a.mean() > 0.95 else '')
                if a.mean() <= 0.95:
                    union |= a
used = binary_dilation(union, iterations=2)
print('union %.3f dilated %.3f' % (union.mean(), used.mean()))
Image.fromarray((used * 255).astype(np.uint8)).save(args.out or os.path.join(WORK, 'g50121', 'hair_used.png'))
