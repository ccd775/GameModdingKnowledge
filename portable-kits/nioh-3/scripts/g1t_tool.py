#!/usr/bin/env python3
"""G1T inspection and container-preserving writes for Rise of the Ronin. Standard library only.

  info      header, format, size, mips, array layers, storage flag (0 linear / 1 DX12 64 KB tiles), uniform-block check
  dds       one mip / layer as a DX10 DDS (tiles undone when the header says tiled) for texconv or an image viewer
  storage   rewrite the payload between linear and tiled order, every mip and layer, with a round-trip check
  constant  fill every mip and layer with one colour in the file's own format and container (same length)
  compare   two G1Ts: header fields, identical bytes, uniform colour of each
  mips      actual mip count against a full chain to 4x4 and, optionally, against the game's own file

Storage layout follows MrIkso/RDBExplorer G1TParser (commit 22e72d8). Reading a tiled payload as linear produces a
convincing but false "left and right halves are copies" picture; always go through `describe` and `dds` here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

# format code -> (bytes per 4x4 block, DXGI format)
BLOCKS = {0x06: (8, 71), 0x59: (8, 71), 0x5B: (16, 77), 0x5C: (8, 80), 0x5D: (16, 83), 0x5E: (16, 95), 0x5F: (16, 98)}
# uncompressed format code -> (bytes per pixel, DXGI format)
PIXELS = {0x00: (4, 28), 0x01: (4, 87), 0x02: (4, 41), 0x03: (8, 10), 0x04: (16, 2)}
NAMES = {0x00: 'RGBA8', 0x01: 'BGRA8', 0x02: 'R32_FLOAT', 0x03: 'R16G16B16A16_FLOAT', 0x04: 'R32G32B32A32_FLOAT',
         0x06: 'BC1', 0x59: 'BC1', 0x5B: 'BC3', 0x5C: 'BC4', 0x5D: 'BC5', 0x5E: 'BC6H', 0x5F: 'BC7'}
TILE = 65536


def describe(data):
    """Per texture in the container: payload range, format, size, mips, layers, storage flag and its offset."""
    if data[:4] != b'GT1G':
        raise ValueError('not a G1T')
    if struct.unpack_from('<I', data, 8)[0] != len(data):
        raise ValueError('declared size differs from the file size')
    table, count = struct.unpack_from('<2I', data, 12)
    out = []
    for i in range(count):
        start = table + struct.unpack_from('<I', data, table + 4 * i)[0]
        end = table + struct.unpack_from('<I', data, table + 4 * (i + 1))[0] if i + 1 < count else len(data)
        mipload, fmt, dims = data[start:start + 3]
        width, height = 1 << (dims & 15), 1 << (dims >> 4)
        extra_size = struct.unpack_from('<I', data, start + 8)[0] if data[start + 7] else 0
        extra = start + 8
        if extra_size >= 16:
            width = struct.unpack_from('<I', data, extra + 12)[0]
        if extra_size >= 20:
            height = struct.unpack_from('<I', data, extra + 16)[0]
        layers = max(1, struct.unpack_from('<H', data, extra + 8)[0] >> 4) if extra_size >= 12 and (mipload & 15) == 3 else 1
        out.append({'start': start, 'payload': start + 8 + extra_size, 'end': end, 'format': fmt,
                    'name': NAMES.get(fmt, f'0x{fmt:02x}'), 'width': width, 'height': height, 'mips': max(1, mipload >> 4),
                    'layers': layers, 'storage': data[extra + 10] if extra_size >= 12 else 0,
                    'storage_offset': extra + 10 if extra_size >= 12 else None})
    return out


def level_size(info, w, h):
    if info['format'] in BLOCKS:
        return max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * BLOCKS[info['format']][0]
    if info['format'] in PIXELS:
        return w * h * PIXELS[info['format']][0]
    raise ValueError(f"format {info['name']} is not supported")


def levels(info):
    """(offset, size, width, height, mip, layer) for every stored image, in payload order (mip-major)."""
    out, offset, w, h = [], info['payload'], info['width'], info['height']
    for mip in range(info['mips']):
        size = level_size(info, w, h)
        for layer in range(info['layers']):
            out.append((offset, size, w, h, mip, layer))
            offset += size
        w, h = max(1, w // 2), max(1, h // 2)
    if offset != info['end']:
        raise ValueError(f'payload holds {info["end"] - info["payload"]} bytes, the header implies {offset - info["payload"]}')
    return out


def reorder_tiles(src, width, height, bpb, to_tiled=False):
    """DX12 64 KB tiles of 1024 bytes x 64 rows of blocks <-> linear block rows. Images up to one tile are linear."""
    if len(src) <= TILE:
        return bytes(src)
    bw, bh = (width + 3) // 4, (height + 3) // 4
    tw, th = 1024 // bpb, 64
    nx = (bw + tw - 1) // tw
    dst = bytearray(len(src))
    touched = 0
    for ty in range((bh + th - 1) // th):
        for tx in range(nx):
            for row in range(min(th, bh - ty * th)):
                s = (ty * nx + tx) * TILE + row * 1024
                d = ((ty * th + row) * bw + tx * tw) * bpb
                size = min(tw, bw - tx * tw) * bpb
                if s + size > len(src) or d + size > len(src):
                    raise ValueError('partial hardware tile is not supported')
                if to_tiled:
                    dst[s:s + size] = src[d:d + size]
                else:
                    dst[d:d + size] = src[s:s + size]
                touched += size
    if touched != len(src):
        raise ValueError('tile walk did not cover the image')
    return bytes(dst)


def rewrite_storage(data, tiled):
    out = bytearray(data)
    for info in describe(data):
        if info['storage_offset'] is None or info['storage'] not in (0, 1):
            raise ValueError('unsupported storage header')
        if info['format'] not in BLOCKS:
            raise ValueError('storage rewrite is only implemented for block-compressed formats')
        bpb = BLOCKS[info['format']][0]
        for offset, size, w, h, _m, _l in levels(info):
            src = data[offset:offset + size]
            if bool(info['storage']) != tiled:
                res = reorder_tiles(src, w, h, bpb, to_tiled=tiled)
                if reorder_tiles(res, w, h, bpb, to_tiled=not tiled) != src:
                    raise ValueError('tile round trip failed')
                out[offset:offset + size] = res
        out[info['storage_offset']] = int(tiled)
    return bytes(out)


def to_dds(data, info, mip=0, layer=0, mode='header'):
    """DX10 DDS of one stored image. mode: header (follow the storage flag), linear or tiled (force a reading)."""
    rec = next((r for r in levels(info) if r[4] == mip and r[5] == layer), None)
    if rec is None:
        raise ValueError(f'no mip {mip} / layer {layer}')
    offset, size, w, h = rec[:4]
    src = data[offset:offset + size]
    if info['format'] in BLOCKS:
        bpb, dxgi = BLOCKS[info['format']]
        if mode == 'tiled' or (mode == 'header' and info['storage'] == 1):
            src = reorder_tiles(src, w, h, bpb)
        flags, pitch = 0x81007, size
    else:
        dxgi = PIXELS[info['format']][1]
        flags, pitch = 0x100F, w * PIXELS[info['format']][0]
    header = [124, flags, h, w, pitch, 0, 1] + [0] * 11 + [32, 4, 0x30315844, 0, 0, 0, 0, 0] + [0x1000, 0, 0, 0, 0]
    return b'DDS ' + struct.pack('<31I', *header) + struct.pack('<5I', dxgi, 3, 0, 1, 0) + src


# ---- constant blocks ---------------------------------------------------------------------------------------------

def bc1_block(rgb):
    r, g, b = (int(round(x * m / 255)) for x, m in zip(rgb, (31, 63, 31)))
    v = (r << 11) | (g << 5) | b
    return struct.pack('<HHI', v, v, 0)


def bc4_block(v):
    return bytes([v, v]) + bytes(6)


def bc7_block(rgba):
    """Mode 6 with both endpoints equal and every index 0; one p-bit shared by the four channels."""
    best = None
    for p in (0, 1):
        e = [min(127, max(0, (x - p + 1) // 2)) for x in rgba]
        err = sum(abs((ei << 1 | p) - x) for ei, x in zip(e, rgba))
        if best is None or err < best[0]:
            best = (err, p, e)
    _, p, e = best
    bits, pos = 1 << 6, 7
    for ch in range(4):
        for _ in range(2):
            bits |= e[ch] << pos
            pos += 7
    bits |= p << pos | p << (pos + 1)
    return bits.to_bytes(16, 'little')


def constant_block(fmt, rgba, value=None):
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
        return struct.pack('<f', rgba[0] / 255 if value is None else value)
    raise ValueError(f'constant fill is not implemented for {NAMES.get(fmt, hex(fmt))}')


def constant(data, rgba, value=None):
    """Same container, every block (or pixel) of every mip and layer set to one value. Tiling is irrelevant."""
    out = bytearray(data)
    for info in describe(data):
        unit = constant_block(info['format'], rgba, value)
        for offset, size, *_ in levels(info):
            out[offset:offset + size] = unit * (size // len(unit))
    return bytes(out)


# ---- decoding of uniform content ---------------------------------------------------------------------------------

def _rgb565(c):
    r, g, b = c >> 11, (c >> 5) & 63, c & 31
    return (r << 3 | r >> 2, g << 2 | g >> 4, b << 3 | b >> 2)


def _bc1_colours(block):
    c0, c1 = struct.unpack_from('<2H', block)
    e0, e1 = _rgb565(c0), _rgb565(c1)
    if c0 > c1:
        pal = [e0, e1, tuple((2 * a + b) // 3 for a, b in zip(e0, e1)), tuple((a + 2 * b) // 3 for a, b in zip(e0, e1))]
    else:
        pal = [e0, e1, tuple((a + b) // 2 for a, b in zip(e0, e1)), (0, 0, 0)]
    idx = struct.unpack_from('<I', block, 4)[0]
    return [pal[(idx >> 2 * i) & 3] for i in range(16)]


def _bc4_values(block):
    a0, a1 = block[0], block[1]
    if a0 > a1:
        pal = [a0, a1] + [((7 - i) * a0 + i * a1) // 7 for i in range(1, 7)]
    else:
        pal = [a0, a1] + [((5 - i) * a0 + i * a1) // 5 for i in range(1, 5)] + [0, 255]
    bits = int.from_bytes(block[2:8], 'little')
    return [pal[(bits >> 3 * i) & 7] for i in range(16)]


def _bc7_mode6(block):
    bits = int.from_bytes(block, 'little')
    if bits & 0x7F != 0x40:
        return None
    pos, e = 7, []
    for _ in range(8):
        e.append((bits >> pos) & 127)
        pos += 7
    p0 = (bits >> pos) & 1
    if bits >> (pos + 2):
        return None   # indices not all zero: only the endpoint-0 case (what `constant` writes) is decoded here
    return tuple(e[2 * ch] << 1 | p0 for ch in range(4))


def uniform_value(data, info):
    """The single colour of a texture whose stored units are all identical, else None."""
    recs = levels(info)
    offset, size = recs[0][:2]
    unit = BLOCKS[info['format']][0] if info['format'] in BLOCKS else PIXELS.get(info['format'], (None,))[0]
    if unit is None:
        return None
    first = data[offset:offset + unit]
    for off, sz, *_ in recs:
        if data[off:off + sz] != first * (sz // unit):
            return None
    fmt = info['format']
    if fmt in (0x06, 0x59):
        texels = _bc1_colours(first)
        return list(texels[0]) if len(set(texels)) == 1 else None
    if fmt == 0x5C:
        v = _bc4_values(first)
        return [v[0]] if len(set(v)) == 1 else None
    if fmt == 0x5D:
        r, g = _bc4_values(first[:8]), _bc4_values(first[8:])
        return [r[0], g[0]] if len(set(r)) == 1 and len(set(g)) == 1 else None
    if fmt == 0x5F:
        v = _bc7_mode6(first)
        return list(v) if v else None
    if fmt == 0x00:
        return list(first)
    if fmt == 0x01:
        return [first[2], first[1], first[0], first[3]]
    if fmt == 0x02:
        return [struct.unpack('<f', first)[0]]
    return None


def full_chain(w, h):
    """Mip count of a chain that stops at 4x4 (what the game's own BC textures carry)."""
    n = 1
    while min(w, h) > 4:
        w, h, n = w // 2, h // 2, n + 1
    return n


def summary(data):
    rows = []
    for info in describe(data):
        row = {k: info[k] for k in ('name', 'width', 'height', 'mips', 'layers', 'storage')}
        row['full_chain_to_4x4'] = full_chain(info['width'], info['height'])
        try:
            row['uniform'] = uniform_value(data, info)
        except ValueError as error:
            row['uniform'] = None
            row['error'] = str(error)
        rows.append(row)
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'textures': rows}


# ---- CLI ---------------------------------------------------------------------------------------------------------

def write_new(path, data):
    path = Path(path)
    if path.exists():
        raise SystemExit(f'refusing to overwrite {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def parse_rgba(text):
    vals = [int(v) for v in text.split(',')]
    if not 1 <= len(vals) <= 4 or not all(0 <= v <= 255 for v in vals):
        raise argparse.ArgumentTypeError('give 1-4 comma-separated values 0..255')
    vals += [0] * (3 - len(vals))      # missing G / B are 0
    return vals if len(vals) == 4 else vals + [255]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('info'); p.add_argument('input')
    p = sub.add_parser('dds'); p.add_argument('input'); p.add_argument('--output', required=True)
    p.add_argument('--mip', type=int, default=0); p.add_argument('--layer', type=int, default=0)
    p.add_argument('--mode', choices=('header', 'linear', 'tiled'), default='header')
    p = sub.add_parser('storage'); p.add_argument('input'); p.add_argument('--output', required=True)
    p.add_argument('--to', choices=('linear', 'tiled'), required=True)
    p = sub.add_parser('constant'); p.add_argument('input'); p.add_argument('--output', required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--rgba', type=parse_rgba, help='e.g. 8,150,232,255 (BC5 uses R,G; BC4 uses R)')
    g.add_argument('--float', type=float, dest='value', help='R32_FLOAT textures, e.g. 1.0')
    p = sub.add_parser('compare'); p.add_argument('a'); p.add_argument('b')
    p = sub.add_parser('mips'); p.add_argument('input'); p.add_argument('--reference', help="the game's own file")
    args = ap.parse_args(argv)

    data = Path(args.input if hasattr(args, 'input') else args.a).read_bytes()
    if args.cmd == 'info':
        print(json.dumps(summary(data), indent=1))
    elif args.cmd == 'dds':
        info = describe(data)[0]
        write_new(args.output, to_dds(data, info, args.mip, args.layer, args.mode))
        print(json.dumps({k: info[k] for k in ('name', 'width', 'height', 'mips', 'layers', 'storage')}))
    elif args.cmd == 'storage':
        out = rewrite_storage(data, args.to == 'tiled')
        write_new(args.output, out)
        print(json.dumps({'output': args.output, 'storage': args.to, 'sha256': hashlib.sha256(out).hexdigest()}))
    elif args.cmd == 'constant':
        out = constant(data, args.rgba or [0, 0, 0, 0], args.value)
        assert len(out) == len(data) and out[:describe(data)[0]['payload']] == data[:describe(data)[0]['payload']]
        got = summary(out)['textures'][0]['uniform']
        if got is None:
            raise SystemExit('read-back did not decode as one uniform value')
        write_new(args.output, out)
        print(json.dumps({'output': args.output, 'decoded': got, 'sha256': hashlib.sha256(out).hexdigest()}))
    elif args.cmd == 'compare':
        other = Path(args.b).read_bytes()
        a, b = summary(data), summary(other)
        fields = ('name', 'width', 'height', 'mips', 'layers', 'storage')
        same_layout = [{k: x[k] for k in fields} for x in a['textures']] == [{k: x[k] for k in fields} for x in b['textures']]
        print(json.dumps({'identical': data == other, 'same_layout': same_layout, 'same_length': len(data) == len(other),
                          'a': a, 'b': b}, indent=1))
    elif args.cmd == 'mips':
        rows = summary(data)['textures']
        out = {'textures': [{**{k: r[k] for k in ('name', 'width', 'height', 'mips')},
                             'complete': r['mips'] >= r['full_chain_to_4x4']} for r in rows]}
        if args.reference:
            ref = summary(Path(args.reference).read_bytes())['textures']
            out['reference_mips'] = [r['mips'] for r in ref]
            out['matches_reference'] = [r['mips'] for r in rows] == out['reference_mips']
        print(json.dumps(out, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
