"""Run the shared Nioh 3 build steps (tools/n3build) for Lenko: her texture atlas layout, her skirt collision set.
usage: lenko_build.py g1m <ninja|samurai> [n3_build_g1m flags]   (default flags: --physics --collide --face)
       lenko_build.py registry <ninja|samurai>
       lenko_build.py textures
Everything else (chests, physics, registry, counts, validation) is the Karin pipeline unchanged; $N3_BUILD points at
Lenko's build directory.

Atlas (4096, top-left origin, one texture set as Karin's; each source PNG is 2048 except the pig's 1024):
  coat   (0, 0, 2048, 2048)      front hair (2048, 0, 1024 x 2048)   back hair (3072, 0, 1024 x 2048)
  skirt  (0, 2048, 2048 x 1024)  face (2048, 2048, 1024)             eyes (3072, 2048, 1024)
  cloth  (0, 3072, 1024)         body skin (1024, 3072, 1024)        legs (2048, 3072, 1024)   pig (3072, 3072, 1024)
Materials sharing a texture share its region; the texels none of them covers are filled from the covered ones
(n3_textures.push_pull over the union of their UV coverage).

Collision sets fitted to her body by lenko_coll.py (bind pose; the vanilla sets lenko1 borrowed were far bigger than
her and pushed the front skirt out / held the necktie off her belly / pushed the long strands off her back, in game):
  lenko_skirt  the 'legs' set (0x6a0d18db entry 1) with its hips / thigh / knee ellipsoids refitted (every non-root
               skirt chain point >= 0.5 cm outside) + two hips-bone ellipsoids over her buttocks
  lenko_tie    the 'torso' set (0x5548953f entry 0) with the waist / navel / chest ellipsoids refitted (necktie >= 0.3 cm)
  lenko_hair   the 'head' set (0xd5d385f9 entry 0) with its chest slab refitted to her upper back (long strands >= 0.5)
Template 'longhair' (the four long strands): the parameter block of the vanilla 50 cm long hair (type-4 entry 0 of
0x6da3fe6e, 13 chains of ~11 points under the head; not in orig/, so the block itself, rebuilt from the vanilla
parameter dump that rebuilds the 'hair' and 'waist' blocks byte for byte). It differs from 'hair' in words 6 (0x200),
14 (0.5), 22 / 25 / 26 (1, 0.2, 0 vs 0.4, 1, 0.1), 29-32 (1) and 37 (100 vs 500).
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
import n3_g1m_physics  # noqa: E402
import n3_textures  # noqa: E402
from n3_common import BUILD, load_source  # noqa: E402

REGIONS = {   # texture file -> region; every material using the texture maps onto it
    'tex/Lenko_Coat_Base_color.png': (0, 0, 2048, 2048),
    'tex/Lenko_Fhair_Base_color.png': (2048, 0, 1024, 2048),
    'tex/Lenko_Bhair_Base_color.png': (3072, 0, 1024, 2048),
    'tex/Lenko_Skirt_Base_color.png': (0, 2048, 2048, 1024),
    'tex/Lenko_Face_Base_color.png': (2048, 2048, 1024, 1024),
    'tex/Lenko_eyes_Base_color.png': (3072, 2048, 1024, 1024),
    'tex/Lenko_Cloth_Base_color.png': (0, 3072, 1024, 1024),
    'tex/Lenko_Body_Base_color.png': (1024, 3072, 1024, 1024),
    'tex/Lenko_Leg_Base_color.png': (2048, 3072, 1024, 1024),
    'tex/Lenko_Pig_Base_color.png': (3072, 3072, 1024, 1024),
}
# lenko_coll.py output. resize: {vanilla primitive: (semi-axes, centre)} in the primitive's own words (rotation kept);
# extra: (bone, semi-axes, centre) in hips bone space (x up, y forward, z the character's left), identity rotation
LENKO_SKIRT_RESIZE = {0: ((11.45, 15.24, 16.28), (-0.78, -2.31, 0.0)),        # hips: world centre (0, 99.2, -2.3)
                      1: ((11.47, 27.1, 9.34), (14.94, 1.37, -2.85)),         # thighs: (+-6.5, 82.5, -2.4)
                      2: ((11.47, 27.1, 9.34), (14.94, 1.37, 2.85)),
                      3: ((9.65, 17.71, 9.48), (3.28, 3.15, -0.2)),           # knees: (+-9.2, 50.3, -4.2)
                      4: ((9.65, 17.71, 9.48), (3.28, 3.15, 0.2))}
LENKO_BUTT = ((2, (13.0, 5.0, 10.0), (-7.0, -10.0, 7.0)), (2, (13.0, 5.0, 10.0), (-7.0, -10.0, -7.0)))  # (+-7, 93, -10)
LENKO_TIE_RESIZE = {1: ((11.58, 12.65, 16.56), (5.7, 1.39, 0.0)),            # waist: (0, 120.8, 1.4)
                    2: ((9.9, 6.13, 12.4), (-1.61, -0.04, 0.0)),              # navel: (0, 113.5, 0)
                    3: ((19.85, 19.73, 15.57), (1.93, -4.69, 0.0))}           # chest: (0, 132.1, -4.7)
LENKO_HAIR_RESIZE = {0: ((17.05, 21.37, 18.74), (10.38, -0.61, 0.0))}       # upper back: (0, 140.5, -0.6)
n3_g1m_physics.COLLISION_SETS.update({
    'lenko_skirt': ('0x6a0d18db', 1, LENKO_BUTT, LENKO_SKIRT_RESIZE),
    'lenko_tie': ('0x5548953f', 0, (), LENKO_TIE_RESIZE),
    'lenko_hair': ('0xd5d385f9', 0, (), LENKO_HAIR_RESIZE),
})
n3_g1m_physics.TEMPLATE_BLOCKS['longhair'] = bytes.fromhex(
    '0000000000000000000000009c000000050000000000803f000200003333733fcdcc4c3fcdcc4c3ecdcc4c3ecdcc4c3e0a000000cdcc4c3e'
    '0000003f000000000000000000000000000000000000000000000000010100000000803fcdcc4c3e0000803fcdcc4c3e0000000003000000'
    '000000000000803f0000803f0000803f0000803fffffffff0000000000000000000000000000c842010000000000003f0000803f01000000')


def atlas():
    meta, _ = load_source()
    files = {x['name']: x['texture_file'] for m in meta['meshes'] for x in m['materials']}
    missing = sorted({f for f in files.values() if f not in REGIONS})
    assert not missing, f'textures without a region: {missing}'
    return {'A': (4096, {name: REGIONS[f] for name, f in files.items()})}


def atlas_png(out):
    meta, arr = load_source()
    img = Image.new('RGB', (4096, 4096), (128, 128, 128))
    by_tex = {}
    for m in meta['meshes']:
        for x in m['materials']:
            by_tex.setdefault(x['texture_file'], set()).add(x['name'])
    stats = {}
    for f, mats in sorted(by_tex.items()):
        x, y, w, h = REGIONS[f]
        im = Image.open(Path(meta['textures'][f]['file'])).convert('RGB')
        cov = np.zeros((im.size[1], im.size[0]), bool)
        for name in sorted(mats):
            cov |= n3_textures.coverage(meta, arr, name, im.size[0])
        filled = n3_textures.push_pull(im, cov)
        img.paste(filled.resize((w, h), Image.LANCZOS), (x, y))
        stats[f] = {'materials': sorted(mats), 'size': im.size, 'region': [x, y, w, h],
                    'uv_coverage': round(float(cov.mean()), 3)}
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
        n3_build_g1m.ATLAS = atlas()
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
        (BUILD / 'atlas_uv.json').write_text(json.dumps(atlas(), indent=1))
        sys.argv = [n3_textures.__file__]          # the kit's n3_textures.py parses its own (empty) command line
        n3_textures.main()


if __name__ == '__main__':
    main()
