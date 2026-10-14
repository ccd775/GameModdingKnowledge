"""Build new i30 texture and material assets from shipped templates.

Texture asset = toc header (2 pairs: DAT1 size, SD size) | DAT1 'Texture Built File' with the 32-byte
TextureBuilt header 4EDE3593 | SD mips (<= 256, down to 8x8). Textures over 256 put the larger mips in span 1
(HD, headerless). toc texture meta (72 B): u32[0]=3, [4]/[6] full w/h, [7] array, [8] total mips, [9] DXGI, [10]=1, [13]=0x4000,
[14] SD+HD bytes, [15] HD bytes, [16] = hd mips | sd mips << 8.
Material = template DAT1 with its serialized section F5260180 rebuilt (texture paths are inline strings
referenced by (offset from the string block, slot hash)); the DAT1 'unknown' entry points at E1275683.
"""
import io, os, struct, sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sm2_dat1 import DAT1          # noqa: E402

BC = {72: ('bc1', 8), 71: ('bc1', 8), 83: ('bc5', 16), 99: ('bc7', 16), 98: ('bc7', 16), 80: ('bc4', 8)}
SD_MAX = 256
MIN_MIP = 8


def mip_chain(img, linear=False):
    """img: PIL RGBA (square power of two) -> list of RGBA arrays largest first, down to MIN_MIP"""
    out = []
    w = img.width
    cur = img
    while True:
        out.append(np.asarray(cur.convert('RGBA'), np.uint8))
        if w <= MIN_MIP:
            break
        w //= 2
        cur = img.resize((w, w), Image.Resampling.BOX if w < 64 else Image.Resampling.LANCZOS)
    return out


def compress(rgba, fmt):
    import etcpak
    kind, _ = BC[fmt]
    h, w = rgba.shape[:2]
    return getattr(etcpak, 'compress_' + kind)(np.ascontiguousarray(rgba).tobytes(), w, h)


class TextureTemplate:
    """header bytes / DAT1 / kind bytes / meta taken from a shipped texture of the same role"""
    def __init__(self, raw, meta):
        pairs = raw[5]
        hl = 8 + 8 * pairs + struct.unpack_from('<H', raw, 6)[0]
        self.header = bytes(raw[:hl])
        body = raw[hl:]
        self.d = DAT1(body)
        self.dat = bytes(body[:self.d.size])
        self.meta = bytes(meta)
        self.hdr = bytes(self.d.get(0x4EDE3593))


def build_texture(tpl, img, fmt):
    """-> dict(span0=bytes, header=bytes, meta=72 bytes, span1=bytes|None)"""
    mips = mip_chain(img)
    data = [compress(m, fmt) for m in mips]
    sizes = [m.shape[1] for m in mips]
    hd = [d for d, s in zip(data, sizes) if s > SD_MAX]
    sd = [d for d, s in zip(data, sizes) if s <= SD_MAX]
    sd_w = sizes[len(hd)]
    full = sizes[0]
    sd_bytes, hd_bytes = b''.join(sd), b''.join(hd)
    h = bytearray(tpl.hdr)
    struct.pack_into('<IIHHHHH', h, 0, len(sd_bytes), len(hd_bytes), full, full, sd_w, sd_w, 1)
    h[24] = fmt                                   # h[25] stays as the template's (0x00 / 0x80, meaning unknown)
    h[26] = len(sd)
    h[27] = len(hd)
    d = DAT1(tpl.dat)
    d.sections[0x4EDE3593] = bytes(h)
    dat = d.save()
    assert len(dat) == len(tpl.dat)
    hdr = bytearray(tpl.header)
    a0, b0, a1, b1 = struct.unpack_from('<IIII', hdr, 8)
    struct.pack_into('<I', hdr, 8, (a0 & 0xC0000000) | len(dat))
    struct.pack_into('<I', hdr, 16, (a1 & 0xC0000000) | len(sd_bytes))
    m = bytearray(tpl.meta)
    u = list(struct.unpack('<18I', m))
    u[4], u[6], u[7], u[8], u[9] = full, full, 1, len(mips), fmt
    u[14], u[15] = len(sd_bytes) + len(hd_bytes), len(hd_bytes)
    u[16] = len(hd) | (len(sd) << 8)
    m = struct.pack('<18I', *u)
    return dict(span0=dat + sd_bytes, header=bytes(hdr), meta=m, span1=hd_bytes if hd else None,
                info=dict(size=full, mips=len(mips), hd_mips=len(hd), sd_mips=len(sd), fmt=fmt))


# ---------------------------------------------------------------- materials
T_SER, T_E127 = 0xF5260180, 0xE1275683


def parse_ser(s):
    """serialized material section -> dict(head words, params, textures[(path, slot_hash)])"""
    u = struct.unpack_from('<8I', s, 0)
    total, n_par, off_val, n_b, off_b, n_tex, off_tex, off_str = u
    tex = []
    for i in range(n_tex):
        so, slot = struct.unpack_from('<II', s, off_tex + 8 * i)
        p = off_str + so
        e = s.index(b'\0', p)
        tex.append((s[p:e].decode(), slot))
    return dict(u=u, tex=tex)


def build_ser(s, new_paths):
    """replace the texture paths (same order/slots) and rebuild the string block"""
    info = parse_ser(s)
    total, n_par, off_val, n_b, off_b, n_tex, off_tex, off_str = info['u']
    assert len(new_paths) == n_tex
    head = bytearray(s[:off_str])
    strs = bytearray()
    for i, p in enumerate(new_paths):
        struct.pack_into('<I', head, off_tex + 8 * i, len(strs))
        strs += p.encode() + b'\0'
    out = head + strs
    out += bytes(-len(out) % 16)
    struct.pack_into('<I', out, 0, len(out))
    return bytes(out)


SLOT = {'g': 360110152, 'n': 2061717114, 'c': 2883245952, 'm': 3867750572, 'micro_n': 1168449632,
        'fuzz': 2895125923, 'v': 3976464191}


def build_material(raw, new_paths):
    """new_paths: list in template order, or {slot name|hash: path} (unlisted slots keep the template's)"""
    pairs = raw[5]
    hl = 8 + 8 * pairs + struct.unpack_from('<H', raw, 6)[0]
    header = bytearray(raw[:hl])
    d = DAT1(raw, hl)
    if isinstance(new_paths, dict):
        want = {SLOT.get(k, k): v for k, v in new_paths.items()}
        cur = parse_ser(d.get(T_SER))['tex']
        missing = set(want) - {h for _, h in cur}
        if missing:
            raise ValueError(f'template lacks slots {missing}')
        new_paths = [want.get(h, p) for p, h in cur]
    d.sections[T_SER] = build_ser(d.get(T_SER), new_paths)
    body = d.save()
    # the DAT1 'unknown' entry (offset, size) points at E1275683; keep it right
    n = struct.unpack_from('<H', body, 12)[0]
    for i in range(n):
        t, o, sz = struct.unpack_from('<III', body, 16 + 12 * i)
        if t == T_E127:
            body = bytearray(body)
            struct.pack_into('<II', body, 16 + 12 * n, o, sz)
            body = bytes(body)
    a0 = struct.unpack_from('<I', header, 8)[0]
    struct.pack_into('<I', header, 8, (a0 & 0xC0000000) | len(body))
    return bytes(header), body
