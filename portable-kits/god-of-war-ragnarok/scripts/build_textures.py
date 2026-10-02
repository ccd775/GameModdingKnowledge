"""Pick a texture for every Kratos skin/body texture slot and write the patch texpack.
usage: build_textures.py --game G --wad W --tex-src DIR --out FILE.texpack   (Kratos rules; Freya: build_valk_textures.py)"""
import re, struct, json
import numpy as np
from PIL import Image
from wad import Wad
from agctex import AgcTexture, parse_tsharp
from gnf import FMT, decode_blocks
from packs import read_texpack_toc
from textures import gnf_entry, write_texpack
from gamedir import set_game, wad_dir

BODY_RE = re.compile(r'^TX_(kratos00_int9_(head|torso|arm|arms)_|youngkratos_(head|torso|arms|legs|legswraps)_|'
                     r'kratos_(head01?|arms|torso|ashes|tattoo)_|kratos00_wrinklemap_)')
DIFFUSE_HI = ('youngkratos_head_gen_0d', 'kratos00_int9_head_sand_m_gen_0d', 'kratos00_int9_head_m_paint_cine__35FD')
DIFFUSE = DIFFUSE_HI + ('youngkratos_torso_gen_0d', 'youngkratos_arms_gen_0d', 'youngkratos_legs_gen_0d',
                        'youngkratos_legswraps_gen_0d', 'kratos00_int9_torso_m_gen_0d', 'kratos00_int9_torso_sand_m_gen_0_0797',
                        'kratos00_int9_arms_sand_m_gen_0d', 'kratos00_int9_arms_m_paint_cine__EB89',
                        'kratos_arms_m_skintemp_white_gen_3680')
EFFECT_RE = re.compile(r'ashes|_m\d?_?ashes|nails|tattoo|chain|emi_|handemi|paint_cine_m1|m_paint_cine__(235D|3B97|5A09)|'
                       r'facetilere|cinetears|bloodflow|regionidmap')
NORMAL_RE = re.compile(r'_0n_|_n_rage_|wrinklemap_normal|_n1_')
OPAQUE_RE = re.compile(r'_0ao_|_gen_0a_|_sand_o_|_head_o_|_torso_o_')


def wad_textures(wad_path):
    w = Wad(open(wad_path, 'rb').read())
    defs, gpus = {}, {}
    for e in w.entries:
        m = re.search(r'_([0-9A-F]{16})$', e.name)
        if not m:
            continue
        h = int(m.group(1), 16)
        if e.type == 34:
            defs[h] = (e.name, w.get(e))
        elif e.type == 32930 and e.group == 29:
            gpus[h] = w.get(e)
    return defs, gpus


class StreamedTextures:
    """Full-resolution originals from the game's texpacks (root first), raw entries with a 0x20 header."""
    def __init__(self):
        import glob
        self.packs = []
        for toc in [wad_dir() + '/root.texpack.toc'] + sorted(glob.glob(wad_dir() + '/*.texpack.toc')):
            if toc.endswith('root.texpack.toc') and self.packs:
                continue
            ents, _ = read_texpack_toc(toc)
            self.packs.append((toc[:-4], ents))

    def image(self, h, ts):
        from agctex import set_tsharp_dims
        p = parse_tsharp(ts)
        kind, bpe = FMT[p['fmt']]
        for path, ents in self.packs:
            if h not in ents:
                continue
            r = ents[h]
            with open(path, 'rb') as f:
                f.seek(r['off']); e = f.read(r['size'])
            doff = struct.unpack_from('<I', e, 4)[0]
            t = AgcTexture(set_tsharp_dims(ts, r['w'], r['h'], r['mips'])).attach(e[doff:])
            if t.data_size != r['datasize']:
                continue
            _, raw = t.detile(0, r['w'], r['h'], bpe)
            return decode_blocks(kind, raw, r['w'], r['h'])
        return None


STREAMED = None


def low_res_stats(h, tsdef, gpu):
    global STREAMED
    if STREAMED is None:
        STREAMED = StreamedTextures()
    ts = tsdef[0x78:0x98]
    p = parse_tsharp(ts)
    img = STREAMED.image(h, ts)
    if img is None:
        kind, bpe = FMT[p['fmt']]
        t = AgcTexture(ts).attach(gpu)
        _, raw = t.detile(0, p['width'], p['height'], bpe)
        img = decode_blocks(kind, raw, p['width'], p['height'])
    return p, np.median(img.reshape(-1, 4), 0).astype(int)


def ident(name):
    base = re.sub(r'_[0-9A-F]{16}$', '', name)[3:]
    return base, base + '_' + name[-16:-12]


def in_set(name, names):
    base, short = ident(name)
    return base in names or short in names


def plan(name, p, median):
    if in_set(name, DIFFUSE):
        return 'atlas'
    if NORMAL_RE.search(name):
        return (128, 128, 255, 255)
    if EFFECT_RE.search(name):
        return (0, 0, 0, 255)
    if OPAQUE_RE.search(name):
        return (255, 255, 255, 255)
    return tuple(int(x) for x in median)


def build(wad_path, atlas_img, out_path, const_size=128, diffuse_hi=4096, diffuse_lo=2048, select=None, planner=None, hi_set=None):
    select = select or BODY_RE
    planner = planner or plan
    hi_set = DIFFUSE_HI if hi_set is None else hi_set
    defs, gpus = wad_textures(wad_path)
    rt, _ = read_texpack_toc(wad_dir() + '/root.texpack.toc')
    h2 = {h: v['h2'] for h, v in rt.items()}
    entries, report = {}, {}
    atlas_cache = {}
    for h, (name, tsdef) in sorted(defs.items(), key=lambda t: t[1][0]):
        if not select.search(name) or h not in gpus:
            continue
        if parse_tsharp(tsdef[0x78:0x98])['fmt'] not in FMT:
            report[name] = dict(choice='skipped (non-BC format)')
            continue
        p, med = low_res_stats(h, tsdef, gpus[h])
        choice = planner(name, p, med)
        if choice == 'atlas':
            size = diffuse_hi if in_set(name, hi_set) else diffuse_lo
            img = atlas_cache.setdefault(size, atlas_img.resize((size, size), Image.LANCZOS) if size != atlas_img.width else atlas_img)
        else:
            img = Image.new('RGBA', (const_size, const_size), choice)
        e, info = gnf_entry(tsdef[0x78:0x98], img)
        entries[h] = (e, info)
        report[name] = dict(choice=choice if choice == 'atlas' else list(choice), size=img.width, fmt=info['fmt'], orig_median=[int(x) for x in med])
    write_texpack(out_path, entries, h2)
    return report


def make_atlas(tex_dir):
    atlas = Image.new('RGBA', (4096, 4096), (128, 128, 128, 255))
    for name, (x, y) in {'Karin_Face': (0, 0), 'Karin_Body': (2048, 0), 'Karin_Hair': (0, 2048), 'Karin_Costume': (2048, 2048)}.items():
        im = Image.open(f'{tex_dir}/{name}.png').convert('RGBA')
        if im.size != (2048, 2048):
            im = im.resize((2048, 2048), Image.LANCZOS)
        rgb = Image.new('RGBA', im.size, (0, 0, 0, 255))
        rgb.paste(im.convert('RGB'))
        atlas.paste(rgb, (x, y))
    return atlas


# ---- Freya (r_freya00): only her own textures; shared material tiles keep their global hashes untouched ----
FREYA_SELECT = re.compile(r'^TX_freya00_')
FREYA_DIFFUSE = re.compile(r'(_gen_\dd_|_head_d_|_head_crying_d_|_acc_d_)')
FREYA_NORMAL = re.compile(r'(_gen_\dn_|_n_|_nm_)')
FREYA_ZERO = re.compile(r'(_m\d+_|_m0\d|tile|tattoo|skintile|decay|emissive|chainmail|warrior_hide)')
FREYA_OPAQUE = re.compile(r'(_ao_|_gen_0ao_|_o_)')
FREYA_HI = ('freya00_body_gen_0d', 'freya00_head_m_gen_0d', 'freya00_head_d')


def plan_freya(name, p, median):
    if FREYA_DIFFUSE.search(name):
        return 'atlas'
    if FREYA_NORMAL.search(name):
        return (128, 128, 255, 255)
    if FREYA_ZERO.search(name):
        return (0, 0, 0, 255)
    if FREYA_OPAQUE.search(name):
        return (255, 255, 255, 255)
    return tuple(int(x) for x in median)


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game', help='game folder with exec/ and libSceAgcTextureTool.dll (default: GOWR_GAME)')
    ap.add_argument('--wad', required=True, help='r_heroa00.wad whose texture descriptors are replaced')
    ap.add_argument('--tex-src', required=True, help='folder with Karin_Face/Body/Hair/Costume.png')
    ap.add_argument('--out', required=True, help='output .texpack (the .toc and a .plan.json are written beside it)')
    args = ap.parse_args()
    set_game(args.game)
    rep = build(args.wad, make_atlas(args.tex_src), args.out)
    json.dump(rep, open(args.out + '.plan.json', 'w'), indent=1)
    print(len(rep), 'textures;', sum(1 for v in rep.values() if v['choice'] == 'atlas'), 'atlas')


if __name__ == '__main__':
    main()
