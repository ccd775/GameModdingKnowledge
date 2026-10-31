"""Make the DDS files for the Porter material slots (sizes and formats fixed by the vanilla textures).

python make_dds.py <work dir> <texconv.exe>
Writes <work>/dds/<group>_<tex>.dds and <work>/textures.json ([group, tex, dds] import jobs).
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image

N = 2048
# (group, tex hex, size, texconv format, source)  source: page name, ('rough', page[, alpha]), ('file', png in the work
# dir, already at size) or a constant RGBA. Mask_Alpha stays 255 (body / boot colour A, coat 13 G): v24 set it to 0 and
# her shoes rendered black while the grey long-save layer stayed
SLOTS = [
    # body material (set 50108:2)
    ('7e9d', '10', N, 'BC7_UNORM', 'B'),                    # colour RGB + mask alpha (A = 255)
    ('7e9d', 'F', N, 'BC7_UNORM', ('rough', 'B')),          # normal RG, roughness B, AO A
    ('7e9d', '1F4', N, 'BC1_UNORM', (48, 48, 48, 255)),     # reflectance
    ('7e9d', '88', N, 'BC1_UNORM', (0, 0, 0, 255)),         # detail-layer mask
    ('7e9d', '17F', N, 'BC1_UNORM', (0, 0, 0, 255)),        # misc (seams / wear lines)
    ('7e9d', 'CA', 1024, 'BC4_UNORM', (115, 115, 115, 255)),   # curvature
    ('7e9d', '9E', 512, 'BC4_UNORM', (159, 159, 159, 255)),    # luminance
    # gloves material (set 50108:3) -> head page
    ('7e9d', '180', N, 'BC1_UNORM', 'A'),
    ('7e9d', 'E', N, 'BC7_UNORM', ('rough', 'A')),
    ('7e9d', '15D', N, 'BC1_UNORM', (48, 48, 48, 255)),
    ('7e9d', '19E', N, 'BC1_UNORM', (0, 0, 0, 255)),
    ('7e9d', '1A0', 1024, 'BC4_UNORM', (115, 115, 115, 255)),
    ('7e9d', '50', 512, 'BC4_UNORM', (159, 159, 159, 255)),
    # boot material (set 50108:1) -> body page (shoes are on page B)
    ('7e9d', '8', N, 'BC7_UNORM', 'B'),
    ('7e9d', '7', N, 'BC7_UNORM', ('rough', 'B')),
    ('7e9d', '24C', N, 'BC1_UNORM', (48, 48, 48, 255)),
    ('7e9d', '19A', N, 'BC1_UNORM', (0, 0, 0, 255)),
    ('7e9d', 'BD', 1024, 'BC4_UNORM', (115, 115, 115, 255)),
    ('7e9d', '18B', 512, 'BC4_UNORM', (159, 159, 159, 255)),
    # Porter decal opacity (set 50110:4, Mask_Alpha): no PORTER logos on Karin
    ('47cd', 'DC', 1024, 'BC4_UNORM', (0, 0, 0, 255)),
    # coat material (set 50110:9) -> cloth page (skirt, tail); constants from the vanilla coat medians
    ('47cd', 'E8', N, 'BC1_UNORM', 'C'),                    # colour
    ('47cd', 'D', N, 'BC7_UNORM', ('rough', 'C', 50)),      # normal RG, roughness B, reflectance A (vanilla ~50)
    ('47cd', 'E', 1024, 'BC7_UNORM', (0, 0, 0, 125)),       # detail-layer masks RGB, curvature A
    ('47cd', '13', N, 'BC1_UNORM', (255, 255, 0, 255)),     # AO R, mask alpha G
    ('47cd', '54', N, 'BC1_UNORM', (0, 0, 0, 255)),         # misc (seams / wear lines)
    ('47cd', '5C', 512, 'BC4_UNORM', (255, 255, 255, 255)),  # alpha test: opaque
    # coat decals (set 50110:11): opacity in the normal texture's B
    ('47cd', '12', 1024, 'BC1_UNORM', (128, 128, 0, 255)),
    # coat paint mask (set 50110:27, sam_coat_porter_v00_paint_alpha): where the game paints mud / dirt at runtime;
    # vanilla ~255 everywhere, which put dark blotches on the white tail
    ('47cd', '8F', N, 'BC4_UNORM', (0, 0, 0, 255)),
    # Sam's hair atlas (set 67704:0, tool key A60): vanilla textures with Karin's ears / bangs / side locks pasted into
    # free space by build_ds2 (hair_<tex>.png); alpha 0 outside her pieces
    ('a60', '2', N, 'BC7_UNORM', ('file', 'hair_2.png')),          # colour RGB, AO A
    ('a60', '8', 4096, 'BC4_UNORM', ('file', 'hair_8.png')),       # alpha
    ('a60', '10', 1024, 'BC1_UNORM', ('file', 'hair_10.png')),     # normal RG
    ('a60', '7', N, 'BC1_UNORM', ('file', 'hair_7.png')),          # masks
    ('a60', 'F', N, 'BC1_UNORM', ('file', 'hair_F.png')),          # misc
    ('a60', '1', 256, 'BC7_UNORM', ('file', 'hair_1.png')),        # reflectance / translucency / roughness
    ('a60', '3', 512, 'BC1_UNORM', ('file', 'hair_3.png')),        # height / mask alpha
    # Sam's hair paint mask (set 67706:0 sam_hair_def_v00_paint_alpha, tool key AA4): where stains may land on the hair
    # material. Karin's ears / bangs / side locks sit in atlas cells Sam's hair cards leave empty and stayed white
    # while a long save greyed the rest of her (v15-v25); 255 everywhere lets them grey too (v27; Sam's cards are
    # transparent anyway)
    ('aa4', '2', 1024, 'BC4_UNORM', (255, 255, 255, 255)),
    # equipped boots (player group 31123): their uppers carry Karin's shoes and their materials bind the "pizza" variant
    # set 31225:22 (tool key A15, make_links.sh v10) -> body page at the set's sizes; packing codes as the Porter boot set
    ('a15', '1B', 1024, 'BC7_UNORM', ('rough', 'B')),       # normal RG, roughness B, AO A
    ('a15', '96', 1024, 'BC1_UNORM', 'B'),                  # colour
    ('a15', '77', 1024, 'BC1_UNORM', (48, 48, 48, 255)),    # reflectance
    ('a15', '7F', 1024, 'BC1_UNORM', (0, 0, 0, 255)),       # detail-layer mask
    ('a15', '6B', 512, 'BC4_UNORM', (115, 115, 115, 255)),  # curvature
    ('a15', '38', 128, 'BC4_UNORM', (159, 159, 159, 255)),  # luminance
]
# face build only (build_ds2 --face writes face_<tex>.png): Sam's face textures (group 67673, tool key F9A)
FACE_SLOTS = [('f9a', t, size, fmt, ('file', f'face_{t}.png')) for t, size, fmt in (
    ('1E', N, 'BC1_UNORM'), ('17', N, 'BC1_UNORM'), ('1F', N, 'BC1_UNORM'), ('1C', N, 'BC1_UNORM'),   # colours
    ('4', 4096, 'BC1_UNORM'), ('1A', 1024, 'BC1_UNORM'), ('14', 1024, 'BC1_UNORM'), ('13', 1024, 'BC1_UNORM'),
    ('1B', 512, 'BC4_UNORM'), ('5', 512, 'BC7_UNORM'), ('1D', 1024, 'BC1_UNORM'), ('6', 512, 'BC1_UNORM'))]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('work'); ap.add_argument('texconv')
    a = ap.parse_args()
    work, texconv = a.work, a.texconv
    src = os.path.join(work, 'dds_src')
    out = os.path.join(work, 'dds')
    os.makedirs(src, exist_ok=True)
    os.makedirs(out, exist_ok=True)
    jobs = []
    face = os.path.exists(os.path.join(work, 'face_1E.png'))
    for group, tex, size, fmt, source in SLOTS + (FACE_SLOTS if face else []):
        name = f'{group}_{tex}'
        if isinstance(source, str):
            im = Image.open(os.path.join(work, f'page_{source}.png')).convert('RGB').resize((size, size), Image.LANCZOS)
            im = Image.merge('RGBA', (*im.split(), Image.new('L', (size, size), 255)))
        elif source[0] == 'file':
            im = Image.open(os.path.join(work, source[1]))
            im = im.convert('L' if im.mode == 'L' else 'RGBA')
            if im.size != (size, size):
                raise SystemExit(f'{source[1]} is {im.size}, expected {size}')
        elif source[0] == 'rough':
            r = Image.open(os.path.join(work, f'rough_{source[1]}.png')).convert('L').resize((size, size), Image.LANCZOS)
            flat = Image.new('L', (size, size), 128)
            alpha = source[2] if len(source) > 2 else 255
            im = Image.merge('RGBA', (flat, flat, r, Image.new('L', (size, size), alpha)))
        else:
            im = Image.fromarray(np.full((size, size, 4), source, np.uint8), 'RGBA')
        png = os.path.join(src, name + '.png')
        im.save(png)
        r = subprocess.run([texconv, '-nologo', '-y', '-f', fmt, '-m', '0', '-o', out, png], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f'texconv failed for {name}: {r.stdout} {r.stderr}')
        jobs.append([group, tex, os.path.join(out, name + '.dds')])
        print(name, fmt, size, flush=True)
    json.dump(jobs, open(os.path.join(work, 'textures.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
