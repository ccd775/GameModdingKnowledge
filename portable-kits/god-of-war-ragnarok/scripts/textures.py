"""Build a patch .texpack (+.toc) of self-contained GNF entries tiled with the game's AGC texture tool."""
import re, struct, math
import numpy as np
from PIL import Image
import etcpak
from agctex import AgcTexture, parse_tsharp
from gnf import FMT

def make_tsharp(orig_ts, size):
    """Take format/swizzle/dst-select from the game's own descriptor; set a square size with a full mip chain."""
    w = list(struct.unpack_from('<8I', orig_ts, 0))
    m = size - 1
    last = int(math.log2(size))
    w[1] = (w[1] & ~(3 << 30)) | ((m & 3) << 30)
    w[2] = (w[2] & ~0xfff) | (m >> 2)
    w[2] = (w[2] & ~(0x3fff << 14)) | (m << 14)
    w[3] = (w[3] & ~(0xf << 12)) & ~(0xf << 16) | (last << 16)
    w[5] = last << 4
    return w, last

def mip_chain(img, levels):
    out = [img]
    for k in range(1, levels):
        s = max(1, img.width >> k)
        out.append(img.resize((s, s), Image.LANCZOS))
    return out

def encode_level(kind, im):
    a = np.array(im.convert('RGBA'))
    h, w = a.shape[:2]
    bw, bh = max(4, (w + 3) // 4 * 4), max(4, (h + 3) // 4 * 4)
    if (bw, bh) != (w, h):
        p = np.zeros((bh, bw, 4), np.uint8); p[:h, :w] = a
        p[h:, :w] = a[h - 1:h, :]; p[:, w:] = p[:, w - 1:w]
        a = p
    b = a.tobytes()
    if kind == 'bc1': return etcpak.compress_bc1(b, bw, bh)
    if kind == 'bc4': return etcpak.compress_bc4(b, bw, bh)
    if kind == 'bc7': return etcpak.compress_bc7(b, bw, bh)
    raise ValueError(kind)

def gnf_entry(orig_ts, img):
    size = img.width
    words, last = make_tsharp(orig_ts, size)
    fmt = (words[1] >> 20) & 0x1ff
    kind, bpe = FMT[fmt]
    words[7] = 0
    t = AgcTexture(struct.pack('<8I', *[x & 0xffffffff for x in words]))
    datasize = t.data_size
    words[7] = datasize
    ts = struct.pack('<8I', *[x & 0xffffffff for x in words])
    t = AgcTexture(ts).attach(None)
    assert t.data_size == datasize
    for k, lvl in enumerate(mip_chain(img, last + 1)):
        blocks = encode_level(kind, lvl)
        r = t.tile(k, lvl.width, lvl.height, bpe, blocks)
        assert r == 0, (k, r)
    data = t.raw()
    total = 0x124 + datasize
    pad = (-total) % 16
    gnfsize = (datasize + 0x1000 + 0xfff) & ~0xfff
    hdr = bytearray(0x124)
    struct.pack_into('<IIII', hdr, 0, 1, 0x124, total + pad, 5)
    hdr[0x10:0x14] = b'GNF '
    struct.pack_into('<IBBHI', hdr, 0x14, 0xff8, 4, 1, 0x0c, gnfsize)
    hdr[0x20:0x40] = ts
    struct.pack_into('<IIHHII', hdr, 0x110, 3, 0, last + 1, last + 1, datasize, 2)
    return bytes(hdr) + data + b'\0' * pad, dict(datasize=datasize, size=total + pad, last=last, w=size, h=size, fmt=fmt)

def write_texpack(path, entries, h2_of):
    """entries: dict hash -> (entry_bytes, info). Layout mirrors the game's patch texpacks (sorted by hash)."""
    hs = sorted(entries)
    n = len(hs)
    recoff = 0x38 + 24 * n
    tocsize = (recoff + 0x20 * n + 15) & ~15
    toc = bytearray(tocsize)
    struct.pack_into('<IIIIII', toc, 0x20, tocsize, n, recoff, n, 6, 0)
    blob = bytearray(); off = tocsize
    for i, h in enumerate(hs):
        e, info = entries[h]
        struct.pack_into('<QQQ', toc, 0x38 + 24 * i, h, h2_of.get(h, 0), recoff + 0x20 * i)
        struct.pack_into('<IIIIIHHq', toc, recoff + 0x20 * i, off // 16, info['datasize'], info['size'], 0,
                         info['last'], info['w'], info['h'], -1)
        blob += e; off += len(e)
    open(path, 'wb').write(bytes(toc) + bytes(blob))
    open(path + '.toc', 'wb').write(bytes(toc))
