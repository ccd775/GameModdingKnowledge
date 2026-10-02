import struct, numpy as np
from agctex import AgcTexture, parse_tsharp
import etcpak
# AGC image formats seen in GoWR texture descriptors (BCn block formats, UNORM/SRGB pairs)
FMT = {169: ('bc1', 8), 170: ('bc1', 8), 173: ('bc3', 16), 174: ('bc3', 16), 175: ('bc4', 8), 176: ('bc4', 8),
       177: ('bc5', 16), 178: ('bc5', 16), 181: ('bc7', 16), 182: ('bc7', 16)}
def decode_blocks(kind, data, w, h):
    bw, bh = max(4, (w+3)//4*4), max(4, (h+3)//4*4)
    import texture2ddecoder as t2d
    fn = {'bc1': t2d.decode_bc1, 'bc4': t2d.decode_bc4, 'bc7': t2d.decode_bc7, 'bc5': t2d.decode_bc5, 'bc3': t2d.decode_bc3}[kind]
    img = fn(bytes(data), bw, bh)
    a = np.frombuffer(img, np.uint8).reshape(bh, bw, 4)[:h, :w]
    return a[..., [2, 1, 0, 3]].copy()  # BGRA -> RGBA
def gnf_entry_info(entry):
    ts = entry[0x20:0x40]
    return parse_tsharp(ts)
def decode_gnf_entry(entry, mip=0, hdr=0x130):
    p = gnf_entry_info(entry)
    kind, bpe = FMT[p['fmt']]
    t = AgcTexture(entry[0x20:0x40]).attach(entry[hdr:])
    w, h = max(1, p['width'] >> mip), max(1, p['height'] >> mip)
    r, raw = t.detile(mip, w, h, bpe)
    assert r == 0, r
    img = decode_blocks(kind, raw, w, h)
    return p, img

def rot_fix(raw, bpe):
    """img2gnf-made textures detile with each block's dwords rotated by one; undo it."""
    nd = bpe // 4
    a = np.frombuffer(raw, np.uint32).reshape(-1, nd)
    return np.roll(a, -1, axis=1).copy().tobytes()
