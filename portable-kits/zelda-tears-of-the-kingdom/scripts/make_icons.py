"""Replace armor inventory icons (UI/Tex/Icon/*.bntx.zs) in place: same size/format (256x256 ASTC 4x4 sRGB, 1 mip).
usage: python make_icons.py <romfs_src> <out_romfs> <rank...>
"""
import ctypes, os, struct, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import txtg, totkfs

_PREVIEW = os.path.join(os.environ.get('TOTK_WORK') or '<set TOTK_WORK>', 'work', 'build', 'preview')   # portable kit
ICONS = {p: os.path.join(_PREVIEW, f'icon_{p}.png') for p in ('Head', 'Upper', 'Lower')}

def replace_icon(bntx: bytes, img: Image.Image) -> bytes:
    d = bytearray(bntx)
    cnt, info_ptr = struct.unpack_from('<IQ', d, 0x24)
    assert cnt == 1
    ip = struct.unpack_from('<Q', d, info_ptr)[0]
    assert d[ip:ip + 4] == b'BRTI'
    mips = struct.unpack_from('<H', d, ip + 0x16)[0]
    fmt, acc, w, h, dep, arr, bhl = struct.unpack_from('<IIIIIII', d, ip + 0x1C)
    img_size = struct.unpack_from('<I', d, ip + 0x50)[0]
    mip_ptrs = struct.unpack_from('<Q', d, ip + 0x70)[0]
    off = struct.unpack_from('<Q', d, mip_ptrs)[0]
    assert fmt == 0x2D06 and mips == 1 and (w, h) == (256, 256), (hex(fmt), mips, w, h)
    a = np.asarray(img.convert('RGBA').resize((w, h), Image.LANCZOS)).copy()
    a[a[..., 3] == 0, :3] = 0
    lin = txtg.encode_blocks(a, 'ASTC_4x4_SRGB', 4, 4, srgb=True)
    out = ctypes.create_string_buffer(img_size)
    txtg.dll().swizzle_block_linear(w // 4, h // 4, 1, lin, len(lin), out, img_size, 1 << bhl, 16, False)
    d[off:off + img_size] = out.raw
    return bytes(d)

def main(src, dst, ranks):
    for r in ranks:
        for part, png in ICONS.items():
            name = f'Armor_{r}_{part}.bntx.zs'
            p = os.path.join(src, 'UI', 'Tex', 'Icon', name)
            raw = totkfs.zs_decompress(open(p, 'rb').read(), name, src)
            new = replace_icon(raw, Image.open(png))
            o = os.path.join(dst, 'UI', 'Tex', 'Icon', name)
            os.makedirs(os.path.dirname(o), exist_ok=True)
            open(o, 'wb').write(totkfs.zs_compress(new, name, src))
            print(name, len(raw), '->', os.path.getsize(o))

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('romfs_src'); ap.add_argument('out_romfs')
    ap.add_argument('ranks', nargs='+', help='armor ids, e.g. 1061 1062 1063 1064')
    a = ap.parse_args()
    main(a.romfs_src, a.out_romfs, a.ranks)
