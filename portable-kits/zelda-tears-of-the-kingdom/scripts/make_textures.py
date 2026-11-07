"""Encode Karin textures to TexToGo (.txtg), using vanilla Link skin textures as header templates.
usage: python make_textures.py <out_dir>
"""
import hashlib, os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import txtg

_WORK = os.environ.get('TOTK_WORK') or '<set TOTK_WORK>'   # portable kit: the work tree (see the kit README)
T = os.path.join(_WORK, 'src', 'tex')   # PNGs written by blender/extract_tex.py
ROMFS_TEX = os.path.join(_WORK, 'romfs', 'TexToGo')
ALB = {  # name -> (source png, size)
    'KarinOri_Face_Alb': (os.path.join(T, 'Karin_Face__9838578e__9838578e__fbx_rgb.png'), 2048),
    'KarinOri_Hair_Alb': (os.path.join(T, 'Karin_Hair__1e553117__1e553117__fbx_rgb.png'), 2048),
    'KarinOri_Body_Alb': (os.path.join(T, 'Karin_Body__068b4464__068b4464__fbx_rgb.png'), 1024),
    'KarinOri_Costume_Alb': (os.path.join(T, 'Karin_Costume__3b9b5651__3b9b5651__fbx_rgb.png'), 2048),
}
SPM_VALUE = 20          # vanilla Link_RaulSkin_Spm: mean 35, median 15
TEMPLATE_KEYS = ('unk1', 'unk2', 'format_flag', 'format_setting', 'unk3', 'ts1', 'ts2', 'ts3', 'ts4', 'r', 'g', 'b', 'a')

def template(name):
    h, _ = txtg.read(os.path.join(ROMFS_TEX, name + '.txtg'))
    return h

def emit(out_dir, name, tpl, img, fmt, srgb=None):
    h = dict(tpl); h['hash'] = hashlib.sha256(name.encode()).digest()
    n = txtg.write(os.path.join(out_dir, name + '.txtg'), h, img, fmt, srgb=srgb)
    print(f'{name:24s} {img.size} fmt {fmt:#x} -> {n} bytes')
    return n

def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    alb_t = template('Link_RaulSkin_Alb')      # ASTC 4x4 (0x101), flag 1 (albedo)
    nrm_t = template('Link_RaulSkin_Nrm')      # BC5 (0x707), flag 4, swizzle (R, G, 1, 1)
    spm_t = template('Link_RaulSkin_Spm')      # BC4 (0x606), flag 6, swizzle (R, R, R, R)
    for name, (src, size) in ALB.items():
        img = Image.open(src).convert('RGBA')
        if img.size != (size, size): img = img.resize((size, size), Image.LANCZOS)
        a = np.asarray(img).copy(); a[..., 3] = 255
        emit(out_dir, name, alb_t, Image.fromarray(a), alb_t['format'], srgb=True)
    flat = np.zeros((64, 64, 4), np.uint8); flat[..., 0] = 128; flat[..., 1] = 128; flat[..., 3] = 255
    emit(out_dir, 'KarinOri_Flat_Nrm', nrm_t, Image.fromarray(flat), nrm_t['format'])
    spm = np.zeros((64, 64, 4), np.uint8); spm[..., 0] = SPM_VALUE; spm[..., 3] = 255
    emit(out_dir, 'KarinOri_Skin_Spm', spm_t, Image.fromarray(spm), spm_t['format'])

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out_dir')
    main(ap.parse_args().out_dir)
