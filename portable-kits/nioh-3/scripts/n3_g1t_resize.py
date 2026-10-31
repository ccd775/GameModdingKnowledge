#!/usr/bin/env python3
"""Write a Nioh 3 G1T (v0066, storage 3) at a NEW size from a DDS, using a vanilla single-texture planar G1T as the
header template (format, header bytes 4-6, extra header). Layout rules from N3_G1T_FORMAT.md:
mips down to 4x4 for BC; a mip is tiled (64 KB tiles, meta1 = tiles x, tiles y, 0, first tile) when its linear size
is >= one tile, else it goes to the linear tail (meta2 = row bytes, size, 0xBAADBAAD x2), mip-major.
The output is read back with n3_g1t's parser and compared image by image with the DDS before it is written.

usage: n3_g1t_resize.py <template.g1t> <new.dds> --output <new.g1t>
"""
import argparse
import struct
import sys
import zlib
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import n3_g1t as g  # noqa: E402


def build(template, dds_blob):
    head, texs = g.parse(template)
    if head['count'] != 1:
        raise SystemExit('template must hold one texture')
    t = texs[0]
    if t['load_type'] != 0 or t['layers'] != 1 or t['storage'] != g.ZLIB_STORAGE:
        raise SystemExit('template must be a planar, single-layer, storage-3 texture')
    dds = g.read_dds(dds_blob)
    W, H, M = dds['width'], dds['height'], dds['mips']
    if dds['dxgi'] not in g.fmt_info(t)[4] or dds['layers'] != 1:
        raise SystemExit(f"DDS DXGI {dds['dxgi']} / {dds['layers']} layers does not fit the template's {g.fmt_info(t)[0]}")
    if W & (W - 1) or H & (H - 1):
        raise SystemExit('power-of-two sizes only')
    _, bpe, blk, _, _ = g.fmt_info(t)
    want_mips = int(np.log2(min(W, H))) + 1 - (2 if blk == 4 else 0)
    if M != want_mips:
        raise SystemExit(f'DDS has {M} mips; vanilla BC textures stop at 4x4 ({want_mips} mips for {W}x{H})')
    nt = dict(t, width=W, height=H, mips=M)
    tw, th = g.TILE_SHAPE[bpe]
    imgs, p = {}, 0
    for mip in range(M):
        _, _, ew, eh = g.mip_dims(nt, mip)
        imgs[mip, 0] = dds['data'][p:p + ew * eh * bpe]; p += ew * eh * bpe
    if p != len(dds['data']):
        raise SystemExit(f"DDS holds {len(dds['data'])} pixel bytes, expected {p}")
    meta1, meta2, tiles, tail = [], [], [], bytearray()
    for mip in range(M):
        _, _, ew, eh = g.mip_dims(nt, mip)
        img = imgs[mip, 0]
        if len(img) != ew * eh * bpe:
            raise SystemExit(f'mip {mip}: {len(img)} bytes, expected {ew * eh * bpe}')
        if ew * eh * bpe >= g.TILE:
            if meta2:
                raise SystemExit('a tiled mip after a tail mip')
            nx, ny = -(-ew // tw), -(-eh // th)
            meta1.append((nx, ny, 0, len(tiles)))
            padded = np.zeros((ny * th, nx * tw * bpe), np.uint8)
            padded[:eh, :ew * bpe] = np.frombuffer(img, np.uint8).reshape(eh, ew * bpe)
            a = padded.reshape(ny, th, nx, tw * bpe).transpose(0, 2, 1, 3)
            tiles += [a[y, x].tobytes() for y in range(ny) for x in range(nx)]
        else:
            meta2.append((ew * bpe // blk, len(img), g.BAAD, g.BAAD))
            tail += img
    z = t['z']
    n1, n2, nc = len(meta1), len(meta2), len(tiles)
    table_size = 36 + 16 * (n1 + n2) + 8 * nc + 8
    out = bytearray(template[:t['payload']])
    b0 = (M << 4) | t['load_type']
    out[t['start']] = b0
    out[t['start'] + 2] = int(np.log2(W)) | (int(np.log2(H)) << 4)
    zb = bytearray(b'0000' + struct.pack('<8i', table_size, z['unk_0c'], z['window'], n1, nc, n2, 1, len(tail)))
    for e in meta1 + meta2:
        zb += struct.pack('<4I', *e)
    data_start = len(out) + len(zb) + 8 * nc + 8
    blobs, pos = [], data_start
    for tile in tiles:
        c = zlib.compress(tile, 6)
        blobs.append(struct.pack('<I', len(c)) + c)
    for b in blobs:
        zb += struct.pack('<2I', pos, len(b)); pos += len(b)
    zb += struct.pack('<2I', pos, len(tail))
    out += zb
    for b in blobs:
        out += b
    out += tail
    struct.pack_into('<I', out, 8, len(out))
    # read back with the reference tool and compare every mip
    _, rt = g.parse(bytes(out))
    back = g.decode_images(bytes(out), rt[0])
    for mip in range(M):
        if back[mip, 0] != imgs[mip, 0]:
            raise SystemExit(f'read-back mismatch at mip {mip}')
    return bytes(out), {'width': W, 'height': H, 'mips': M, 'tiled_mips': n1, 'tail_mips': n2, 'tiles': nc,
                        'tail_bytes': len(tail), 'bytes': len(out)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('template'); ap.add_argument('dds'); ap.add_argument('--output', required=True)
    a = ap.parse_args(argv)
    blob, info = build(Path(a.template).read_bytes(), Path(a.dds).read_bytes())
    g.write_new(a.output, blob)
    print(info)


if __name__ == '__main__':
    main()
