#!/usr/bin/env python3
"""Nioh 3 G1T (version 0066) textures stored as type 3: zlib-compressed DX12 64 KB tiles plus a linear mip tail.

  info      header, format, size, mips, layers, storage type, zlib block header, meta tables, chunk table summary
  dds       decode one texture to a linear DX10 DDS (every mip and layer, or one with --mip / --layer)
  encode    template .g1t + DDS with identical format/size/mips/layers -> new .g1t (re-tiled, re-compressed)
  constant  template .g1t + one colour -> new .g1t, every mip and layer filled with that colour

Layout notes and the evidence behind them: N3_G1T_FORMAT.md next to this script. Writes never overwrite a file.
Run with `python -I`; numpy is then looked up in the user site-packages, appended after the standard library.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path

try:
    import numpy as np
except ImportError:  # python -I drops the user site; append it (never the cwd or script dir) and retry
    import site
    sys.path.append(site.getusersitepackages())
    import numpy as np

TILE = 65536
ZLIB_STORAGE = 3
BAAD = 0xBAADBAAD

# G1T format code -> (name, bytes per element, block edge in pixels, DXGI written to DDS, DXGI accepted from DDS)
FORMATS = {
    0x00: ('R8G8B8A8_UNORM', 4, 1, 28, {27, 28, 29}),
    0x01: ('B8G8R8A8_UNORM', 4, 1, 87, {87, 90, 91}),
    0x02: ('R32_FLOAT', 4, 1, 41, {39, 41}),
    0x03: ('R16G16B16A16_FLOAT', 8, 1, 10, {9, 10}),
    0x04: ('R32G32B32A32_FLOAT', 16, 1, 2, {1, 2}),
    0x0D: ('R32G32B32A32_FLOAT', 16, 1, 2, {1, 2}),
    0x06: ('BC1', 8, 4, 71, {70, 71, 72}),
    0x59: ('BC1', 8, 4, 71, {70, 71, 72}),
    0x5A: ('BC2', 16, 4, 74, {73, 74, 75}),
    0x5B: ('BC3', 16, 4, 77, {76, 77, 78}),
    0x5C: ('BC4', 8, 4, 80, {79, 80}),
    0x5D: ('BC5', 16, 4, 83, {82, 83}),
    0x5E: ('BC6H', 16, 4, 95, {94, 95}),
    0x5F: ('BC7', 16, 4, 98, {97, 98, 99}),
}
LEGACY_FOURCC = {b'DXT1': 71, b'DXT3': 74, b'DXT5': 77, b'ATI1': 80, b'BC4U': 80, b'ATI2': 83, b'BC5U': 83,
                 struct.pack('<I', 113): 10, struct.pack('<I', 116): 2}
# D3D12 standard 64 KB tile shape in elements, by bytes per element
TILE_SHAPE = {1: (256, 256), 2: (256, 128), 4: (128, 128), 8: (128, 64), 16: (64, 64)}
LOAD_TYPES = {0: 'PLANAR', 1: 'CUBE', 2: 'VOLUME', 3: 'PLANE_ARRAY', 4: 'CUBE_ARRAY'}


class G1TError(ValueError):
    pass


def u32(data, off):
    return struct.unpack_from('<I', data, off)[0]


# ---- parsing ---------------------------------------------------------------------------------------------------

def parse(data):
    """Container header and every texture's header, extra header and (for storage 3) zlib block tables."""
    if data[:4] != b'GT1G':
        raise G1TError('not a G1T (magic)')
    version = data[4:8].decode('ascii', 'replace')
    size, table, count, platform, meta_size = struct.unpack_from('<5I', data, 8)
    if size != len(data):
        raise G1TError(f'declared file size {size} differs from actual {len(data)}')
    flags = list(struct.unpack_from(f'<{count}I', data, 28))
    offsets = list(struct.unpack_from(f'<{count}I', data, table))
    head = {'version': version, 'file_size': size, 'table_offset': table, 'count': count, 'platform': platform,
            'metadata_size': meta_size, 'normal_flags': flags, 'offsets': offsets}
    texs = []
    for i, rel in enumerate(offsets):
        start = table + rel
        end = table + offsets[i + 1] if i + 1 < count else len(data)
        texs.append(parse_texture(data, start, end, i))
    return head, texs


def parse_texture(data, start, end, index):
    b0, fmt, dims, b3 = data[start:start + 4]
    t = {'index': index, 'start': start, 'end': end, 'format': fmt, 'mips': max(1, b0 >> 4), 'load_type': b0 & 15,
         'width': 1 << (dims & 15), 'height': 1 << (dims >> 4), 'depth': 1 << (b3 & 15),
         'header_bytes_4_6': data[start + 4:start + 7].hex(), 'extra_version': data[start + 7],
         'extra_size': 0, 'faces': 0, 'array': 0, 'storage': 0, 'extra_raw': ''}
    pos = start + 8
    if t['extra_version']:
        es = u32(data, pos)
        raw = data[pos:pos + es]
        t['extra_size'], t['extra_raw'] = es, raw.hex(' ')
        if es >= 12:
            t['z_scale'] = struct.unpack_from('<f', raw, 4)[0]
            ex = struct.unpack_from('<H', raw, 8)[0]
            t['faces'], t['array'] = ex & 15, ex >> 4
            t['storage'], t['extra_byte_11'] = raw[10], raw[11]
        if es >= 16:
            t['width'] = u32(raw, 12)
        if es >= 20:
            t['height'] = u32(raw, 16)
        pos += es
    t['payload'] = pos
    lt = t['load_type']
    t['layers'] = max(1, t['array']) if lt in (3, 4) else 1
    if lt in (1, 4):
        t['layers'] *= 6
    t['slices'] = t['depth'] * t['layers'] * max(1, t['faces'])   # reference parser's meta stride
    if t['storage'] == ZLIB_STORAGE:
        t['z'] = parse_zblock(data, pos, t['slices'], end)
    return t


def parse_zblock(data, pos, stride, end):
    magic = data[pos:pos + 4]
    table_size, unk, window, m1, nchunks, m2, has_tail, tail_size = struct.unpack_from('<8i', data, pos + 4)
    if magic != b'0000':
        raise G1TError(f'zlib block magic {magic!r}, expected b"0000"')
    q = pos + 36
    meta1 = [struct.unpack_from('<4I', data, q + 16 * i) for i in range(m1 * stride)]
    q += 16 * m1 * stride
    meta2 = [struct.unpack_from('<4I', data, q + 16 * i) for i in range(m2 * stride)]
    q += 16 * m2 * stride
    chunks = [struct.unpack_from('<2I', data, q + 8 * i) for i in range(nchunks)]
    q += 8 * nchunks
    tail = struct.unpack_from('<2I', data, q) if has_tail else None
    q += 8 if has_tail else 0
    if q - pos != table_size:
        raise G1TError(f'zlib block table is {q - pos} bytes, header says {table_size}')
    return {'pos': pos, 'magic': magic.decode('ascii', 'replace'), 'table_size': table_size, 'unk_0c': unk,
            'window': window, 'meta1_count': m1, 'chunk_count': nchunks, 'meta2_count': m2, 'has_tail': has_tail,
            'tail_size': tail_size, 'meta1': meta1, 'meta2': meta2, 'chunks': chunks, 'tail': tail,
            'data_start': q, 'end': end}


def fmt_info(t):
    if t['format'] not in FORMATS:
        raise G1TError(f"format 0x{t['format']:02x} is not supported")
    return FORMATS[t['format']]


def mip_dims(t, mip):
    """(width, height, elements across, elements down) of one mip."""
    _, _, blk, _, _ = fmt_info(t)
    w, h = max(1, t['width'] >> mip), max(1, t['height'] >> mip)
    return w, h, (w + blk - 1) // blk, (h + blk - 1) // blk


def layout(t):
    """Where every (mip, slice) lives. Tiled mips: meta1 order is mip-major, slice-minor; each entry is
    (tiles across, tiles down, 0, first tile). Tail mips: meta2 order is the same; images are packed linearly."""
    z = t.get('z')
    if t['storage'] != ZLIB_STORAGE or z is None:
        raise G1TError(f"storage type {t['storage']} is not the zlib type 3 this tool handles")
    if t['load_type'] not in (0, 3) or t['depth'] != 1 or t['faces'] > 1:
        raise G1TError(f"load type {LOAD_TYPES.get(t['load_type'], t['load_type'])}, depth {t['depth']}, "
                       f"faces {t['faces']}: only planar textures and plane arrays are verified")
    _, bpe, blk, _, _ = fmt_info(t)
    tw, th = TILE_SHAPE[bpe]
    S = t['slices']
    if z['meta1_count'] + z['meta2_count'] != t['mips']:
        raise G1TError(f"meta1 {z['meta1_count']} + meta2 {z['meta2_count']} != mip count {t['mips']}")
    out, tiles_used, tail_off = [], 0, 0
    for mip in range(t['mips']):
        w, h, ew, eh = mip_dims(t, mip)
        for s in range(S):
            rec = {'mip': mip, 'slice': s, 'width': w, 'height': h, 'ew': ew, 'eh': eh, 'linear': ew * eh * bpe}
            if mip < z['meta1_count']:
                nx, ny, unk, first = z['meta1'][mip * S + s]
                if (nx, ny) != (-(-ew // tw), -(-eh // th)) or unk != 0:
                    raise G1TError(f'meta1 entry {mip * S + s} = {(nx, ny, unk, first)} does not match '
                                   f'{ew}x{eh} elements in {tw}x{th} tiles')
                rec.update(kind='tiled', tiles_x=nx, tiles_y=ny, first_tile=first, tile_w=tw, tile_h=th)
                tiles_used += nx * ny
            else:
                a, size, c, d = z['meta2'][(mip - z['meta1_count']) * S + s]
                # a = bytes of one pixel row (width * bits per pixel / 8); for BC that is block-row pitch / 4
                if size != rec['linear'] or a * blk != ew * bpe or (c, d) != (BAAD, BAAD):
                    raise G1TError(f'meta2 entry {(mip - z["meta1_count"]) * S + s} = {(a, size, hex(c), hex(d))}'
                                   f' does not match a linear {ew}x{eh} x {bpe} B image')
                rec.update(kind='tail', tail_offset=tail_off)
                tail_off += size
            out.append(rec)
    stream = z['chunk_count'] * z['window']
    if tiles_used * TILE > stream:
        raise G1TError(f'meta1 needs {tiles_used} tiles, the chunks hold {stream} bytes')
    if tail_off != (z['tail_size'] if z['has_tail'] else 0):
        raise G1TError(f"tail images total {tail_off} bytes, header says {z['tail_size']}")
    return out


def read_stream(data, t):
    """Inflate every chunk (absolute file offset; u32 deflated size + zlib stream) and read the raw tail."""
    z = t['z']
    parts = []
    for i, (off, size) in enumerate(z['chunks']):
        csz = u32(data, off)
        if csz + 4 != size:
            raise G1TError(f'chunk {i}: table size {size}, prefix says {csz} + 4')
        raw = zlib.decompress(data[off + 4:off + 4 + csz])
        if len(raw) != z['window'] and i + 1 < len(z['chunks']):
            raise G1TError(f'chunk {i} inflates to {len(raw)} bytes, window is {z["window"]}')
        parts.append(raw)
    tail = b''
    if z['tail']:
        off, size = z['tail']
        if size != z['tail_size'] or off + size > len(data):
            raise G1TError('tail entry does not match the header')
        tail = data[off:off + size]
    return b''.join(parts), tail, [len(p) for p in parts]


# ---- tiling ------------------------------------------------------------------------------------------------------

def tile_view(stream, rec, bpe):
    """Tiles of one image as a (rows, row bytes) padded linear array view. Tile interior: tile_h rows of
    tile_w*bpe (= 1024 for BC) bytes; tiles row-major from first_tile."""
    nx, ny, tw, th = rec['tiles_x'], rec['tiles_y'], rec['tile_w'], rec['tile_h']
    a = stream[rec['first_tile'] * TILE:(rec['first_tile'] + nx * ny) * TILE].reshape(ny, nx, th, tw * bpe)
    return a


def untile(stream, rec, bpe):
    a = tile_view(stream, rec, bpe)
    lin = a.transpose(0, 2, 1, 3).reshape(rec['tiles_y'] * rec['tile_h'], rec['tiles_x'] * rec['tile_w'] * bpe)
    return lin[:rec['eh'], :rec['ew'] * bpe].tobytes()


def retile(stream, rec, bpe, img):
    """Write one linear image into its tiles in `stream` (a writable uint8 array); padding stays untouched."""
    a = tile_view(stream, rec, bpe)
    lin = a.transpose(0, 2, 1, 3)  # view (ny, th, nx, tw*bpe)
    padded = np.empty((rec['tiles_y'] * rec['tile_h'], rec['tiles_x'] * rec['tile_w'] * bpe), np.uint8)
    padded[:] = lin.reshape(padded.shape)
    padded[:rec['eh'], :rec['ew'] * bpe] = np.frombuffer(img, np.uint8).reshape(rec['eh'], rec['ew'] * bpe)
    lin[...] = padded.reshape(lin.shape)


def decode_images(data, t):
    """{(mip, slice): linear bytes} of one texture."""
    stream, tail, _ = read_stream(data, t)
    arr = np.frombuffer(stream, np.uint8)
    bpe = fmt_info(t)[1]
    out = {}
    for rec in layout(t):
        if rec['kind'] == 'tiled':
            out[rec['mip'], rec['slice']] = untile(arr, rec, bpe)
        else:
            out[rec['mip'], rec['slice']] = tail[rec['tail_offset']:rec['tail_offset'] + rec['linear']]
    return out


def encode_payload(data, t, images, base=None):
    """New (stream, tail) for a texture from {(mip, slice): linear bytes}. Starts from the template's own
    stream and tail (or `base`), so only bytes that belong to an image change."""
    stream, tail, sizes = read_stream(data, t)
    if base is not None:
        stream, tail = base
    arr = np.frombuffer(stream, np.uint8).copy()
    tail = bytearray(tail)
    bpe = fmt_info(t)[1]
    for rec in layout(t):
        img = images[rec['mip'], rec['slice']]
        if len(img) != rec['linear']:
            raise G1TError(f"mip {rec['mip']} slice {rec['slice']}: {len(img)} bytes, expected {rec['linear']}")
        if rec['kind'] == 'tiled':
            retile(arr, rec, bpe, img)
        else:
            tail[rec['tail_offset']:rec['tail_offset'] + rec['linear']] = img
    return arr.tobytes(), bytes(tail), sizes


def rebuild(data, t, stream, tail, sizes, level=6):
    """The template file with this texture's chunks re-deflated and its chunk / tail table and file size updated.
    Everything else (headers, extra header, zlib block header, meta tables) is copied from the template."""
    head, _ = parse(data)
    if head['count'] != 1:
        raise G1TError('writing is only implemented for single-texture files (chunk offset base unverified otherwise)')
    if t['end'] != len(data):
        raise G1TError('bytes follow the texture payload; not handled')
    z = t['z']
    first = z['chunks'][0][0] if z['chunks'] else (z['tail'][0] if z['tail'] else z['data_start'])
    if first != z['data_start']:
        raise G1TError('chunk data does not start right after the zlib block table')
    old_end = (z['tail'][0] + z['tail'][1]) if z['tail'] else (z['chunks'][-1][0] + z['chunks'][-1][1] if z['chunks']
                                                                else z['data_start'])
    if old_end != len(data):
        raise G1TError('template has bytes after the chunk data and tail; not handled')
    out = bytearray(data[:z['data_start']])
    pos, table, cur = z['data_start'], [], 0
    blobs = []
    for n in sizes:
        comp = zlib.compress(stream[cur:cur + n], level)
        cur += n
        blobs.append(struct.pack('<I', len(comp)) + comp)
        table.append((pos, len(comp) + 4))
        pos += len(comp) + 4
    if cur != len(stream):
        raise G1TError('stream length changed')
    q = z['data_start'] - 8 * len(sizes) - (8 if z['has_tail'] else 0)
    for i, (off, size) in enumerate(table):
        struct.pack_into('<2I', out, q + 8 * i, off, size)
    if z['has_tail']:
        struct.pack_into('<2I', out, q + 8 * len(sizes), pos, len(tail))
    for b in blobs:
        out += b
    out += tail
    struct.pack_into('<I', out, 8, len(out))
    return bytes(out)


# ---- DDS ---------------------------------------------------------------------------------------------------------

def write_dds(t, images, mips=None, slices=None):
    name, bpe, blk, dxgi, _ = fmt_info(t)
    mips = list(range(t['mips'])) if mips is None else mips
    slices = list(range(t['slices'])) if slices is None else slices
    w, h, ew, eh = mip_dims(t, mips[0])
    compressed = blk > 1
    flags = 0x1 | 0x2 | 0x4 | 0x1000 | (0x80000 if compressed else 0x8) | (0x20000 if len(mips) > 1 else 0)
    pitch = ew * eh * bpe if compressed else ew * bpe
    caps = 0x1000 | (0x400008 if len(mips) > 1 else 0) | (0x8 if len(slices) > 1 else 0)
    header = [124, flags, h, w, pitch, 0, len(mips)] + [0] * 11 + [32, 4, 0x30315844, 0, 0, 0, 0, 0] + \
             [caps, 0, 0, 0, 0]
    out = bytearray(b'DDS ' + struct.pack('<31I', *header) + struct.pack('<5I', dxgi, 3, 0, len(slices), 0))
    for s in slices:            # DDS order: slice-major, mips inside
        for m in mips:
            out += images[m, s]
    return bytes(out)


def read_dds(blob):
    if blob[:4] != b'DDS ' or u32(blob, 4) != 124:
        raise G1TError('not a DDS file')
    h, w = u32(blob, 12), u32(blob, 16)
    mips = max(1, u32(blob, 28))
    fourcc = blob[84:88]
    pos, layers = 128, 1
    if fourcc == b'DX10':
        dxgi, dim, misc, layers = struct.unpack_from('<4I', blob, 128)
        if dim != 3 or misc & 4:
            raise G1TError('DDS is not a plain 2D texture / array')
        pos = 148
    elif u32(blob, 80) & 4 and fourcc in LEGACY_FOURCC:
        dxgi = LEGACY_FOURCC[fourcc]
    else:
        raise G1TError(f'DDS pixel format {fourcc!r} not understood; write it with texconv -dx10')
    if u32(blob, 112) & 0x200 or u32(blob, 24) > 1:
        raise G1TError('cube or volume DDS is not supported')
    return {'width': w, 'height': h, 'mips': mips, 'layers': max(1, layers), 'dxgi': dxgi, 'data': blob[pos:]}


def dds_images(t, dds):
    name, bpe, blk, _, accept = fmt_info(t)
    want = {'width': t['width'], 'height': t['height'], 'mips': t['mips'], 'layers': t['slices']}
    got = {k: dds[k] for k in want}
    if got != want or dds['dxgi'] not in accept:
        raise G1TError(f"DDS is {got} DXGI {dds['dxgi']}; template needs {want} {name} (DXGI {sorted(accept)})")
    images, pos = {}, 0
    for s in range(t['slices']):
        for m in range(t['mips']):
            _, _, ew, eh = mip_dims(t, m)
            n = ew * eh * bpe
            images[m, s] = dds['data'][pos:pos + n]
            pos += n
    if pos != len(dds['data']):
        raise G1TError(f"DDS holds {len(dds['data'])} pixel bytes, expected {pos}")
    return images


# ---- constant colour ---------------------------------------------------------------------------------------------

def _expand(v, bits):
    return (v << (8 - bits)) | (v >> (2 * bits - 8))


def bc1_block(rgb):
    """Every texel uses palette index 2 (2/3 c0 + 1/3 c1); endpoints searched per channel for the closest value."""
    ends = []
    for x, bits in zip(rgb, (5, 6, 5)):
        vals = np.array([_expand(v, bits) for v in range(1 << bits)], np.float64)
        err = np.abs((2 * vals[:, None] + vals[None, :]) / 3 - x)
        a, b = np.unravel_index(int(np.argmin(err)), err.shape)
        ends.append((int(a), int(b)))
    c0 = ends[0][0] << 11 | ends[1][0] << 5 | ends[2][0]
    c1 = ends[0][1] << 11 | ends[1][1] << 5 | ends[2][1]
    if c0 == c1:
        return struct.pack('<HHI', c0, c1, 0)               # index 0 = c0
    if c0 > c1:
        return struct.pack('<HHI', c0, c1, 0xAAAAAAAA)      # 4-colour mode, index 2
    return struct.pack('<HHI', c1, c0, 0xFFFFFFFF)          # swapped endpoints, index 3 is the same mix


def bc1_decode(block):
    c0, c1, idx = struct.unpack('<HHI', block)
    e = [(_expand(c >> 11, 5), _expand((c >> 5) & 63, 6), _expand(c & 31, 5)) for c in (c0, c1)]
    i = idx & 3
    if i < 2:
        return list(e[i])
    w = (2, 1) if i == 2 else (1, 2)
    if c0 <= c1:
        return [(a + b) / 2 for a, b in zip(*e)] if i == 2 else [0, 0, 0]
    return [(w[0] * a + w[1] * b) / 3 for a, b in zip(*e)]


def bc4_block(v):
    return bytes([v, v]) + bytes(6)


BC7_W4 = (0, 4, 9, 13, 17, 21, 26, 30, 34, 38, 43, 47, 51, 55, 60, 64)


def bc7_block(rgba):
    """Mode 6 (RGBA 7.7.7.7 + p-bit per endpoint, 4-bit indices). Every texel gets one index < 8 (the anchor
    texel's top index bit is implicit); endpoints, p-bits and that index are searched for the closest value."""
    e = np.arange(128)
    best = None
    for p0 in (0, 1):
        for p1 in (0, 1):
            A, B = (e << 1 | p0)[:, None], (e << 1 | p1)[None, :]
            for idx in range(8):
                w = BC7_W4[idx]
                val = ((64 - w) * A + w * B + 32) >> 6
                pick = []
                err = 0
                for x in rgba:
                    d = np.abs(val - x)
                    k = int(np.argmin(d))
                    pick.append(divmod(k, 128))
                    err += int(d.flat[k])
                if best is None or err < best[0]:
                    best = (err, p0, p1, idx, pick)
    _, p0, p1, idx, pick = best
    bits, pos = 1 << 6, 7
    for a, b in pick:
        bits |= a << pos | b << (pos + 7)
        pos += 14
    bits |= p0 << pos | p1 << (pos + 1)
    pos += 2
    bits |= idx << pos                # anchor: 3 bits
    pos += 3
    for _ in range(15):
        bits |= idx << pos
        pos += 4
    return bits.to_bytes(16, 'little')


def bc7_mode6_decode(block):
    """Colour of texel 0 of a mode-6 block (None for other modes)."""
    bits = int.from_bytes(block, 'little')
    if bits & 0x7F != 0x40:
        return None
    pos, e = 7, []
    for _ in range(8):
        e.append((bits >> pos) & 127)
        pos += 7
    p0, p1 = (bits >> pos) & 1, (bits >> (pos + 1)) & 1
    w = BC7_W4[(bits >> (pos + 2)) & 7]
    return [((64 - w) * (e[2 * c] << 1 | p0) + w * (e[2 * c + 1] << 1 | p1) + 32) >> 6 for c in range(4)]


def unit_value(fmt, unit):
    """Decoded value of one constant block / pixel (what `constant` wrote)."""
    if fmt in (0x06, 0x59):
        return [round(v, 2) for v in bc1_decode(unit)]
    if fmt == 0x5C:
        return [unit[0]]
    if fmt == 0x5D:
        return [unit[0], unit[8]]
    if fmt == 0x5F:
        return bc7_mode6_decode(unit)
    if fmt == 0x00:
        return list(unit)
    if fmt == 0x01:
        return [unit[2], unit[1], unit[0], unit[3]]
    if fmt == 0x02:
        return list(struct.unpack('<f', unit))
    if fmt == 0x03:
        return np.frombuffer(unit, '<f2').astype(float).tolist()
    if fmt in (0x04, 0x0D):
        return list(struct.unpack('<4f', unit))
    return None


def constant_unit(fmt, rgba, floats):
    """One block / pixel. rgba: 4 ints 0..255; floats: 4 floats (used by float formats)."""
    if fmt in (0x06, 0x59):
        return bc1_block(rgba[:3])
    if fmt == 0x5C:
        return bc4_block(rgba[0])
    if fmt == 0x5D:
        return bc4_block(rgba[0]) + bc4_block(rgba[1])
    if fmt == 0x5F:
        return bc7_block(rgba)
    if fmt == 0x00:
        return bytes(rgba)
    if fmt == 0x01:
        return bytes([rgba[2], rgba[1], rgba[0], rgba[3]])
    if fmt == 0x02:
        return struct.pack('<f', floats[0])
    if fmt == 0x03:
        return np.array(floats, '<f2').tobytes()
    if fmt in (0x04, 0x0D):
        return struct.pack('<4f', *floats)
    raise G1TError(f"constant fill is not implemented for {FORMATS.get(fmt, ('0x%02x' % fmt,))[0]}")


def constant_images(t, rgba, floats):
    unit = constant_unit(t['format'], rgba, floats)
    bpe = fmt_info(t)[1]
    assert len(unit) == bpe
    out = {}
    for m in range(t['mips']):
        _, _, ew, eh = mip_dims(t, m)
        for s in range(t['slices']):
            out[m, s] = unit * (ew * eh)
    return out


# ---- reports -----------------------------------------------------------------------------------------------------

def texture_summary(data, t):
    row = {k: t[k] for k in ('index', 'start', 'payload', 'end', 'width', 'height', 'mips', 'depth', 'faces',
                             'array', 'layers', 'slices', 'storage', 'extra_version', 'extra_size', 'extra_raw',
                             'header_bytes_4_6')}
    row['format'] = f"0x{t['format']:02x} {FORMATS.get(t['format'], ('unknown',))[0]}"
    row['load_type'] = f"{t['load_type']} {LOAD_TYPES.get(t['load_type'], '?')}"
    for k in ('z_scale', 'extra_byte_11'):
        if k in t:
            row[k] = t[k]
    z = t.get('z')
    if z:
        row['zlib_block'] = {k: z[k] for k in ('pos', 'magic', 'table_size', 'unk_0c', 'window', 'meta1_count',
                                                'chunk_count', 'meta2_count', 'has_tail', 'tail_size', 'tail',
                                                'data_start')}
        row['meta1'] = ['tiles %d x %d, unk %d, first tile %d' % e for e in z['meta1']]
        row['meta2'] = ['row bytes %d, size %d, %08x %08x' % e for e in z['meta2']]
        comp = [s for _, s in z['chunks']]
        contiguous = all(z['chunks'][i][0] + z['chunks'][i][1] == z['chunks'][i + 1][0] for i in range(len(comp) - 1))
        row['chunks'] = {'count': len(comp), 'first_offset': z['chunks'][0][0] if comp else None,
                         'total_bytes': sum(comp), 'min': min(comp, default=0), 'max': max(comp, default=0),
                         'contiguous': contiguous}
        try:
            stream, tail, sizes = read_stream(data, t)
            row['chunks']['inflated_total'] = len(stream)
            row['chunks']['all_inflate_to_window'] = all(s == z['window'] for s in sizes)
            row['decompressed_sha256'] = hashlib.sha256(stream + tail).hexdigest()
            row['layout_slice0'] = [
                f"mip {r['mip']} {r['width']}x{r['height']} {r['linear']} B " +
                (f"tiled {r['tiles_x']}x{r['tiles_y']} from tile {r['first_tile']}" if r['kind'] == 'tiled'
                 else f"tail +{r['tail_offset']}") for r in layout(t) if r['slice'] == 0]
        except (G1TError, zlib.error) as e:
            row['error'] = str(e)
    return row


def write_new(path, blob):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, 'xb') as f:
            f.write(blob)
    except FileExistsError:
        raise SystemExit(f'refusing to overwrite {path}')


def check_written(blob, t_index, images):
    """Re-parse a written file and decode it back; must give exactly `images`."""
    head, texs = parse(blob)
    got = decode_images(blob, texs[t_index])
    if got != images:
        raise G1TError('read-back of the written file differs from the input images')
    return texs[t_index]


def parse_rgba(text):
    vals = [int(v) for v in text.split(',')]
    if not 1 <= len(vals) <= 4 or not all(0 <= v <= 255 for v in vals):
        raise argparse.ArgumentTypeError('give 1-4 comma-separated values 0..255')
    vals += [0] * (3 - len(vals))
    return vals if len(vals) == 4 else vals + [255]


def parse_floats(text):
    vals = [float(v) for v in text.split(',')]
    if not 1 <= len(vals) <= 4:
        raise argparse.ArgumentTypeError('give 1-4 comma-separated floats')
    vals += [0.0] * (3 - len(vals))
    return vals if len(vals) == 4 else vals + [1.0]


def pick(texs, n):
    if not 0 <= n < len(texs):
        raise SystemExit(f'texture {n} out of range (file has {len(texs)})')
    return texs[n]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('info')
    p.add_argument('input')
    p.add_argument('--full', action='store_true', help='also list meta tables and the per-mip layout')
    p = sub.add_parser('dds')
    p.add_argument('input')
    p.add_argument('--output', required=True)
    p.add_argument('--texture', type=int, default=0)
    p.add_argument('--mip', type=int, help='only this mip')
    p.add_argument('--layer', type=int, help='only this array layer')
    p = sub.add_parser('encode')
    p.add_argument('template')
    p.add_argument('dds')
    p.add_argument('--output', required=True)
    p.add_argument('--texture', type=int, default=0)
    p.add_argument('--level', type=int, default=6, help='zlib level (vanilla streams carry the level-6 header 78 9C)')
    p = sub.add_parser('constant')
    p.add_argument('template')
    p.add_argument('--output', required=True)
    p.add_argument('--texture', type=int, default=0)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--rgba', type=parse_rgba, help='0..255, e.g. 128,128,255,255 (BC5 uses R,G; BC4 uses R; '
                                                   'missing G/B = 0, A = 255)')
    g.add_argument('--float', type=parse_floats, dest='floats', help='e.g. 1 or 0.5,0.5,1,1 (missing G/B = 0, A = 1);'
                                                                      ' 8-bit / BC formats get round(f*255)')
    args = ap.parse_args(argv)

    try:
        if args.cmd == 'info':
            data = Path(args.input).read_bytes()
            head, texs = parse(data)
            rows = [texture_summary(data, t) for t in texs]
            if not args.full:
                for r in rows:
                    for k in ('meta1', 'meta2'):
                        if k in r and len(r[k]) > 12:
                            r[k] = r[k][:6] + [f'... {len(r[k]) - 12} more ...'] + r[k][-6:]
            print(json.dumps({'header': head, 'sha256': hashlib.sha256(data).hexdigest(), 'textures': rows}, indent=1))
        elif args.cmd == 'dds':
            data = Path(args.input).read_bytes()
            t = pick(parse(data)[1], args.texture)
            images = decode_images(data, t)
            mips = None if args.mip is None else [args.mip]
            slices = None if args.layer is None else [args.layer]
            write_new(args.output, write_dds(t, images, mips, slices))
            print(json.dumps({'output': args.output, 'format': fmt_info(t)[0], 'width': t['width'],
                              'height': t['height'], 'mips': t['mips'] if mips is None else 1,
                              'layers': t['slices'] if slices is None else 1}))
        elif args.cmd in ('encode', 'constant'):
            data = Path(args.template).read_bytes()
            t = pick(parse(data)[1], args.texture)
            layout(t)
            if args.cmd == 'encode':
                images = dds_images(t, read_dds(Path(args.dds).read_bytes()))
            else:
                if args.rgba is not None:
                    rgba, floats = args.rgba, [v / 255 for v in args.rgba]
                else:
                    floats = args.floats
                    rgba = [min(255, max(0, round(v * 255))) for v in floats]
                images = constant_images(t, rgba, floats)
            stream, tail, sizes = encode_payload(data, t, images)
            out = rebuild(data, t, stream, tail, sizes, getattr(args, 'level', 6))
            t2 = check_written(out, args.texture, images)
            s2, tail2, _ = read_stream(out, t2)
            q = t['z']['data_start'] - 8 * len(sizes) - (8 if t['z']['has_tail'] else 0)
            if out[12:q] != data[12:q] or out[:8] != data[:8]:
                raise G1TError('headers / meta tables changed; internal error')
            write_new(args.output, out)
            extra = {}
            if args.cmd == 'constant':
                extra['decoded_value'] = unit_value(t['format'], images[0, 0][:fmt_info(t)[1]])
            print(json.dumps({'output': args.output, **extra, 'bytes': len(out), 'template_bytes': len(data),
                              'decompressed_sha256': hashlib.sha256(s2 + tail2).hexdigest(),
                              'template_decompressed_sha256': hashlib.sha256(b''.join(read_stream(data, t)[:2])).hexdigest(),
                              'sha256': hashlib.sha256(out).hexdigest()}))
    except (G1TError, zlib.error) as e:
        raise SystemExit(f'error: {e}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
