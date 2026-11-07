"""TotK TexToGo (.txtg) reader/writer.

Layout (from Switch Toolbox TXTG.cs):
  0x50-byte header, then per surface (mip-major, array-minor) u16 array, u8 mip, u8 1,
  then per surface u32 zstd_size, u32 6, then zstd frames (one per surface) of block-linear swizzled data.
Swizzling uses Switch Toolbox's tegra_swizzle_x64.dll (same calls as TegraX1Swizzle.cs).
"""
import ctypes, os, struct, sys
import numpy as np
import zstandard as zs

# portable kit: Switch Toolbox folder with tegra_swizzle_x64.dll ($TOTK_ST_DIR, default $TOTK_WORK/tools/st_headless)
ST_DIR = os.environ.get('TOTK_ST_DIR') or os.path.join(os.environ.get('TOTK_WORK') or '<set TOTK_WORK>', 'tools', 'st_headless')
_dll = None

def dll():
    global _dll
    if _dll is None:
        _dll = ctypes.CDLL(os.path.join(ST_DIR, 'tegra_swizzle_x64.dll'))
        u64 = ctypes.c_uint64
        _dll.block_height_mip0.restype = u64; _dll.block_height_mip0.argtypes = [u64]
        _dll.mip_block_height.restype = u64; _dll.mip_block_height.argtypes = [u64, u64]
        _dll.swizzled_mip_size.restype = u64
        _dll.deswizzle_block_linear.restype = None
        _dll.deswizzle_block_linear.argtypes = [u64, u64, u64, ctypes.c_char_p, u64, ctypes.c_char_p, u64, u64, u64, ctypes.c_bool]
        _dll.swizzle_block_linear.restype = None
        _dll.swizzle_block_linear.argtypes = [u64, u64, u64, ctypes.c_char_p, u64, ctypes.c_char_p, u64, u64, u64, ctypes.c_bool]
    return _dll

# format code -> (name, block_w, block_h, bytes_per_block)
FORMATS = {
    0x101: ('ASTC_4x4_UNORM', 4, 4, 16), 0x102: ('ASTC_8x8_UNORM', 8, 8, 16), 0x105: ('ASTC_8x8_SRGB', 8, 8, 16),
    0x109: ('ASTC_4x4_SRGB', 4, 4, 16), 0x202: ('BC1_UNORM', 4, 4, 8), 0x203: ('BC1_UNORM_SRGB', 4, 4, 8),
    0x302: ('BC1_UNORM', 4, 4, 8), 0x505: ('BC3_UNORM_SRGB', 4, 4, 16), 0x602: ('BC4_UNORM', 4, 4, 8),
    0x606: ('BC4_UNORM', 4, 4, 8), 0x607: ('BC4_UNORM', 4, 4, 8), 0x702: ('BC5_UNORM', 4, 4, 16),
    0x703: ('BC5_UNORM', 4, 4, 16), 0x707: ('BC5_UNORM', 4, 4, 16), 0x901: ('BC7_UNORM', 4, 4, 16),
}

HDR = struct.Struct('<HH4sHHHBBBHBIBBBB32sHHIIII')
assert HDR.size == 0x50, HDR.size
HDR_FIELDS = ['header_size', 'version', 'magic', 'width', 'height', 'depth', 'mips', 'unk1', 'unk2', 'pad',
              'format_flag', 'format_setting', 'r', 'g', 'b', 'a', 'hash', 'format', 'unk3', 'ts1', 'ts2', 'ts3', 'ts4']

def block_dims(h):
    name, bw, bh, bpb = FORMATS[h['format']]
    if name.startswith('ASTC') and h['format'] == 0x101:
        if h['ts2'] == 32628: bw, bh = 8, 5
        elif h['ts2'] == 32631: bw, bh = 8, 8
    return name, bw, bh, bpb

def div_up(a, b): return (a + b - 1) // b

def read(path):
    d = open(path, 'rb').read()
    h = dict(zip(HDR_FIELDS, HDR.unpack_from(d, 0)))
    assert h['magic'] == b'6PK0', h['magic']
    n = h['mips'] * h['depth']
    off = h['header_size']
    surf = []
    for i in range(n):
        arr, mip, one = struct.unpack_from('<HBB', d, off); off += 4
        surf.append([arr, mip])
    for i in range(n):
        size, six = struct.unpack_from('<II', d, off); off += 8
        surf[i].append(size)
    out = []
    dctx = zs.ZstdDecompressor()
    for arr, mip, size in surf:
        raw = dctx.decompress(d[off:off + size], max_output_size=64 << 20); off += size
        out.append((arr, mip, raw))
    return h, out

def deswizzle_mip(h, mip, data):
    name, bw, bh, bpb = block_dims(h)
    w = max(1, h['width'] >> mip); hh = max(1, h['height'] >> mip)
    wb, hb = div_up(w, bw), div_up(hh, bh)
    bh0 = dll().block_height_mip0(div_up(h['height'], bh))
    mbh = dll().mip_block_height(hb, bh0)
    outlen = wb * hb * bpb
    out = ctypes.create_string_buffer(outlen)
    dll().deswizzle_block_linear(wb, hb, 1, data, len(data), out, outlen, mbh, bpb, False)
    return out.raw, w, hh

def swizzle_mip(fmt, width, height, mip, linear, bw, bh, bpb):
    w = max(1, width >> mip); hh = max(1, height >> mip)
    wb, hb = div_up(w, bw), div_up(hh, bh)
    bh0 = dll().block_height_mip0(div_up(height, bh))
    mbh = dll().mip_block_height(hb, bh0)
    # swizzled size: rows padded to GOB (64B x 8 rows) * block height
    gob_w = div_up(wb * bpb, 64)
    rows = div_up(hb, 8 * mbh) * 8 * mbh
    size = gob_w * 64 * rows
    out = ctypes.create_string_buffer(size)
    dll().swizzle_block_linear(wb, hb, 1, linear, len(linear), out, size, mbh, bpb, False)
    # TotK stores each surface truncated after the last byte the block-linear layout actually uses.
    probe = ctypes.create_string_buffer(size)
    ones = b'\xff' * len(linear)
    dll().swizzle_block_linear(wb, hb, 1, ones, len(ones), probe, size, mbh, bpb, False)
    used = len(probe.raw.rstrip(b'\0'))
    return out.raw[:used]

def decode_rgba(h, mip_index=0, surfaces=None):
    """Decode a mip to an RGBA uint8 array (for previews)."""
    import texture2ddecoder as t2d
    raw = [s for s in surfaces if s[0] == 0 and s[1] == mip_index][0][2]
    lin, w, hh = deswizzle_mip(h, mip_index, raw)
    name, bw, bh, bpb = block_dims(h)
    pw, ph = div_up(w, bw) * bw, div_up(hh, bh) * bh
    if name.startswith('ASTC'): bgra = t2d.decode_astc(lin, pw, ph, bw, bh)
    elif name.startswith('BC1'): bgra = t2d.decode_bc1(lin, pw, ph)
    elif name.startswith('BC3'): bgra = t2d.decode_bc3(lin, pw, ph)
    elif name.startswith('BC4'): bgra = t2d.decode_bc4(lin, pw, ph)
    elif name.startswith('BC5'): bgra = t2d.decode_bc5(lin, pw, ph)
    elif name.startswith('BC7'): bgra = t2d.decode_bc7(lin, pw, ph)
    else: raise ValueError(name)
    a = np.frombuffer(bgra, np.uint8).reshape(ph, pw, 4)[:hh, :w]
    return a[..., [2, 1, 0, 3]].copy()

_astc_ctx = {}

def encode_blocks(rgba, fmt_name, bw=4, bh=4, srgb=None):
    """rgba: HxWx4 uint8 with H,W multiples of the block size."""
    hh, w = rgba.shape[:2]
    data = np.ascontiguousarray(rgba).tobytes()
    if fmt_name.startswith('ASTC'):
        import astc_encoder as ae
        prof = ae.ASTCProfile.LDR_SRGB if (srgb if srgb is not None else 'SRGB' in fmt_name) else ae.ASTCProfile.LDR
        key = (prof, bw, bh)
        if key not in _astc_ctx:
            _astc_ctx[key] = ae.ASTCContext(ae.ASTCConfig(prof, bw, bh, 1, ae.ASTCQualityPreset.THOROUGH))
        return _astc_ctx[key].compress(ae.ASTCImage(ae.ASTCType.U8, w, hh, 1, data), ae.ASTCSwizzle.from_str('RGBA'))
    import etcpak
    if fmt_name.startswith('BC7'): return etcpak.compress_bc7(data, w, hh, None)
    if fmt_name.startswith('BC1'): return etcpak.compress_bc1(data, w, hh)
    if fmt_name.startswith('BC3'): return etcpak.compress_bc3(data, w, hh)
    if fmt_name.startswith('BC4'): return etcpak.compress_bc4(data, w, hh)
    if fmt_name.startswith('BC5'): return etcpak.compress_bc5(data, w, hh)
    raise ValueError(fmt_name)

def build_mips(img, count):
    from PIL import Image
    mips = [img]
    for i in range(1, count):
        w = max(1, img.width >> i); hh = max(1, img.height >> i)
        mips.append(img.resize((w, hh), Image.LANCZOS))
    return mips

def write(path, template_header, img, fmt_code=0x901, mip_count=None, level=19, srgb=None):
    """Write img (PIL RGBA) as a txtg, reusing the template header's identity fields (hash, settings)."""
    h = dict(template_header)
    name, bw, bh, bpb = FORMATS[fmt_code]
    w, hh = img.size
    if mip_count is None:
        mip_count = 1
        while (w >> mip_count) >= 1 or (hh >> mip_count) >= 1: mip_count += 1
    h.update(width=w, height=hh, depth=1, mips=mip_count, format=fmt_code)
    if fmt_code != 0x101:
        pass
    surfaces = []
    for mi, m in enumerate(build_mips(img.convert('RGBA'), mip_count)):
        a = np.asarray(m, np.uint8)
        pw, ph = div_up(m.width, bw) * bw, div_up(m.height, bh) * bh
        if (pw, ph) != (m.width, m.height):
            pad = np.zeros((ph, pw, 4), np.uint8); pad[:m.height, :m.width] = a
            pad[m.height:, :m.width] = a[-1:, :]; pad[:, m.width:] = pad[:, m.width - 1:m.width]
            a = pad
        lin = encode_blocks(a, name, bw, bh, srgb)
        surfaces.append(swizzle_mip(fmt_code, w, hh, mi, lin, bw, bh, bpb))
    cctx = zs.ZstdCompressor(level=level)
    comp = [cctx.compress(s) for s in surfaces]
    out = bytearray(HDR.pack(*[h[k] for k in HDR_FIELDS]))
    for mi in range(mip_count): out += struct.pack('<HBB', 0, mi, 1)
    for c in comp: out += struct.pack('<II', len(c), 6)
    for c in comp: out += c
    open(path, 'wb').write(out)
    return len(out)

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='Print the header of each .txtg file.')
    ap.add_argument('txtg', nargs='+')
    for p in ap.parse_args().txtg:
        h, s = read(p)
        name, bw, bh, bpb = block_dims(h)
        print(os.path.basename(p), name, hex(h['format']), h['width'], h['height'], 'mips', h['mips'], 'depth', h['depth'],
              'flag', h['format_flag'], 'fset', h['format_setting'], 'comp', (h['r'], h['g'], h['b'], h['a']),
              'unk', h['unk1'], h['unk2'], hex(h['unk3']), 'ts', h['ts1'], h['ts2'], h['ts3'], h['ts4'],
              'sizes', [len(x[2]) for x in s][:4])
