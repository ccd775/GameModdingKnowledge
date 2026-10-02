"""Patch texpack for the companion Freya (r_freyavalkyrie00): her own freyavalkyrie00_/freya00_ textures only.
usage: build_valk_textures.py --game G --wad W --tex-src DIR --out FILE.texpack"""
import json, re, sys
import build_textures as bt
from gamedir import set_game

VALK_SELECT = re.compile(r'^TX_(freyavalkyrie00|freyavalkyriehelm00|freya00)_')
VALK_DIFFUSE_EXTRA = ('freyavalkyrie00_head_notearmakeu_06FB',)      # truncated name; skin-coloured head diffuse
VALK_HI = bt.FREYA_HI + ('freyavalkyrie00_head_gen_0d', 'freyavalkyrie00_head_cine_gen_0d',
                         'freyavalkyrie00_arms_gen_0d') + VALK_DIFFUSE_EXTRA
TEARS = re.compile(r'tearsflow')


def plan_valk(name, p, median):
    if bt.in_set(name, VALK_DIFFUSE_EXTRA):
        return 'atlas'
    if TEARS.search(name):          # '_o_' would make the tear overlay fully opaque
        return (0, 0, 0, 255)
    return bt.plan_freya(name, p, median)


def main(wad_path, tex_dir, out_path):
    atlas = bt.make_atlas(tex_dir)
    rep = bt.build(wad_path, atlas, out_path, select=VALK_SELECT, planner=plan_valk, hi_set=VALK_HI)
    json.dump(rep, open(out_path + '.plan.json', 'w'), indent=1)
    return rep


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game', help='game folder with exec/ and libSceAgcTextureTool.dll (default: GOWR_GAME)')
    ap.add_argument('--wad', required=True, help='original r_freyavalkyrie00.wad (its texture descriptors are replaced)')
    ap.add_argument('--tex-src', required=True, help='folder with Karin_Face/Body/Hair/Costume.png')
    ap.add_argument('--out', required=True, help='output .texpack (the .toc and a .plan.json are written beside it)')
    args = ap.parse_args()
    set_game(args.game)
    rep = main(args.wad, args.tex_src, args.out)
    print(len(rep), 'textures;', sum(1 for v in rep.values() if v['choice'] == 'atlas'), 'atlas')
