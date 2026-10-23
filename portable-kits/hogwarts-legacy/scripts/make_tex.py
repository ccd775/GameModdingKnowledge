# make_tex.py <ktex_dir> <out_dir> — build host-texture PNGs for the hijacked DarkArtsDeluxe01 material instances.
import argparse, sys, os, json
ap = argparse.ArgumentParser(description='host-texture PNGs (D, flat N, MRO) from the source model textures')
ap.add_argument('ktex_dir', help='PNGs written by blender/extract_tex.py'); ap.add_argument('out_dir')
args = ap.parse_args()
import numpy as np
from PIL import Image

src, out = args.ktex_dir, args.out_dir
os.makedirs(out, exist_ok=True)
def load(n): return np.array(Image.open(os.path.join(src, n)).convert('RGBA'))
def save(a, n): Image.fromarray(a).save(os.path.join(out, n)); print('wrote', n, a.shape)
def opaque(a): b = a.copy(); b[..., 3] = 255; return b

# colour maps (alpha forced opaque; MM_Prop opaque hosts)
save(opaque(load('UnityTexture_15_Karin_Costume__3b9b5651.png')), 'Costume_D.png')
save(opaque(load('UnityTexture_4_Karin_Body__068b4464.png')), 'Skin_D.png')
save(opaque(load('UnityTexture_0_Karin_Face__9838578e.png')), 'Face_D.png')
hair = load('UnityTexture_9_Karin_Hair__1e553117.png')
save(opaque(hair), 'Hair_D.png')

# masked host (Hat MI, BC7 with alpha): Karin_Alpha as-is (eye highlights, blush)
save(load('UnityTexture_3_Karin_Alpha__88100961.png'), 'Atlas_D.png')

# flat normal + MRO constants (R metal, G roughness, B ao)
n = np.zeros((64, 64, 4), np.uint8); n[...] = (128, 128, 255, 255); save(n, 'Flat_N.png')
for name, rough in (('Costume', 0.78), ('Skin', 0.55), ('Face', 0.6), ('Hair', 0.6), ('Atlas', 0.65)):
    m = np.zeros((64, 64, 4), np.uint8); m[...] = (0, int(rough * 255), 255, 255); save(m, f'{name}_MRO.png')
