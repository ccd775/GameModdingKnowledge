"""Run the shared Nioh 3 build steps (tools/n3build) for Ichel: her texture atlas layout and her source.
usage: ichel_build.py g1m <ninja|samurai> [n3_build_g1m flags]   (default flags: --physics --collide --face)
       ichel_build.py registry <ninja|samurai>
       ichel_build.py textures
Everything else (chests, physics, registry, counts, validation) is the Karin pipeline unchanged; $N3_BUILD points at
Ichel's build directory.

Atlas (4096, top-left origin, one texture set as Karin's; source PNG -> region, upscaled where smaller):
  clothes 衣服a.png 2048 -> (0, 0, 2048)       hair 头发.png 1024 -> (2048, 0, 2048)
  skin    皮肤.png  1024 -> (0, 2048, 2048)    face 脸.png 1024 -> (2048, 2048, 1024)   eyes 眼睛.png 512 -> (3072, 2048, 1024)
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'n3build'))
import n3_build_g1m  # noqa: E402
import n3_textures  # noqa: E402
from n3_common import BUILD, load_source  # noqa: E402

ATLAS = {'A': (4096, {'胸口.001': (0, 0, 2048, 2048), '头发1.001': (2048, 0, 2048, 2048), '皮肤.001': (0, 2048, 2048, 2048),
                      '口腔.001': (2048, 2048, 1024, 1024), '眼睛.001': (3072, 2048, 1024, 1024)})}


def atlas_png(out):
    meta, arr = load_source()
    size, regs = ATLAS['A']
    img = Image.new('RGB', (size, size), (128, 128, 128))
    files = {x['name']: x['texture_file'] for m in meta['meshes'] for x in m['materials']}
    stats = {}
    for name, (x, y, w, h) in regs.items():
        im = Image.open(Path(meta['textures'][files[name]]['file'])).convert('RGB')
        cov = n3_textures.coverage(meta, arr, name, im.size[0])
        filled = n3_textures.push_pull(im, cov)
        img.paste(filled.resize((w, h), Image.LANCZOS), (x, y))
        stats[name] = {'source': files[name], 'size': im.size, 'uv_coverage': round(float(cov.mean()), 3)}
    img.save(out)
    return stats


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('step', choices=('g1m', 'registry', 'textures'))
    ap.add_argument('target', nargs='?', help='ninja or samurai (g1m, registry)')
    ap.add_argument('flags', nargs=argparse.REMAINDER, help='g1m: n3_build_g1m.py flags (default --physics --collide --face)')
    args = ap.parse_args()
    step = args.step
    if step in ('g1m', 'registry') and not args.target:
        ap.error(f'{step} needs <ninja|samurai>')
    if step == 'g1m':
        n3_build_g1m.ATLAS = ATLAS
        n3_build_g1m.DROP = set()
        flags = args.flags or ['--physics', '--collide', '--face']
        sys.argv = [n3_build_g1m.__file__, args.target, *flags]
        n3_build_g1m.main()
    elif step == 'registry':
        import n3_registry
        sys.argv = [n3_registry.__file__, args.target]
        n3_registry.main()
    elif step == 'textures':
        n3_textures.atlas_png = lambda out: atlas_png(out)
        (BUILD / 'atlas_uv.json').write_text(json.dumps(ATLAS, indent=1))
        sys.argv = [n3_textures.__file__]          # the kit's n3_textures.py parses its own (empty) command line
        n3_textures.main()


if __name__ == '__main__':
    main()
