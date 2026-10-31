"""Koei Tecmo G2A animation reader (port of Joschuka's Project-G1M G2A.h / Utils.h; Nioh 3 uses version 0040).
usage: g2a.py <file.g2a|hash> [--package <dir>] [--bones lo-hi]   -> per animated bone: channels and value ranges

Layout: resource header (magic _A2G, version, size), f32 framerate, u32 packed (length = & 0x3FFF frames,
bone-info bytes = (>> 18) & 0x3FFC), u32 timing-section bytes, u32 entry count, [u32 pad for v4/v5],
bone infos (u32: spline count & 0xF, bone id (>> 4) & 0x3FF (+1024 per wrap), timing offset >> 14),
per spline: u16 opcode (0 rotation as axis-angle vector, 1 position, 2 scale), u16 key count, u32 first data index,
u16 key frames; data = 32-byte quantised cubic segments in the data section.
"""
import argparse
import struct
import sys
from pathlib import Path

import numpy as np


def _seg(q, t):
    """Evaluate one quantised cubic segment (4 x u64) at t in [0, 1] -> vec3 (Project-G1M function1)."""
    r = [int(x) for x in q]
    def scale(row):
        bits = ((row >> 0x25) & 0x7800000) + 0x32000000
        return struct.unpack('<f', struct.pack('<I', bits & 0xFFFFFFFF))[0]
    def comp(row, shift):
        if shift == 28:
            v = (row >> 28) & 0xFFFFF000
        elif shift == 8:
            v = (row >> 8) & 0xFFFFF000
        else:
            v = (row << 12) & 0xFFFFFFFF
        v &= 0xFFFFFFFF
        return v - (1 << 32) if v & 0x80000000 else v
    sx, sy, sz, sw = (scale(x) for x in r)
    out = []
    for sh in (28, 8, 0):
        out.append(comp(r[3], sh) * sw * t ** 3 + comp(r[0], sh) * sx + comp(r[1], sh) * sy * t + comp(r[2], sh) * sz * t * t)
    return np.array(out)


def axis_angle_quat(v):
    a = np.linalg.norm(v)
    if a > 1.1920929e-05:
        xyz = v * (np.sin(a / 2) / a)
    else:
        xyz = v * 0.5
    return np.array([np.cos(a / 2), *xyz])      # w, x, y, z


def parse(d):
    magic, ver, size = struct.unpack_from('<4s4sI', d, 0)
    assert magic == b'_A2G', magic
    v5, v4 = ver == b'0500', ver == b'0400'
    fps, packed, timing_size, entries = struct.unpack_from('<fIII', d, 12)
    length = packed & 0x3FFF
    info_size = (packed >> 18) & 0x3FFC
    o = 28 + (4 if (v4 or v5) else 0)
    bones, last, wrap = {}, 0, 0
    for i in range(info_size // 4):
        p = struct.unpack_from('<I', d, o + 4 * i)[0]
        n = p & 0xF
        bid = (p >> 4) & (0xFF if v5 else 0x3FF)
        toff = (p >> 12) if v5 else (p >> 14)
        if bid < last:
            wrap += 1
        last = bid
        bid += wrap * (256 if v5 else 1024)
        q = o + info_size + toff
        q -= q % 4
        chans = []
        for _ in range(n):
            op, kc, first = struct.unpack_from('<HHI', d, q); q += 8
            frames = list(struct.unpack_from(f'<{kc}H', d, q)); q += 2 * kc
            q += (-q) % 4
            base = o + info_size + timing_size + first * 32
            segs = [struct.unpack_from('<4Q', d, base + 32 * k) for k in range(kc)]
            chans.append({'op': op, 'frames': frames, 'segs': segs})
        bones[bid] = chans
    return {'version': ver, 'fps': fps, 'length': length, 'bones': bones}


def sample(chan, length):
    """Per-frame values (length+1 x 3) of one channel (Project-G1M: hold single keys, extend to the end)."""
    fr, segs = list(chan['frames']), chan['segs']
    out = np.zeros((length + 1, 3))
    if len(fr) == 1:
        out[:] = _seg(segs[0], 0.0)
        return out
    if fr[-1] != length:
        fr = fr + [length]
    for k in range(len(fr) - 1):
        a, b = fr[k], fr[k + 1]
        for f in range(a, b):
            out[f] = _seg(segs[k], (f - a) / (b - a))
    out[length] = _seg(segs[min(len(fr) - 2, len(segs) - 1)], 1.0)
    return out


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src', help='.g2a file, or a resource hash read through --package')
    ap.add_argument('--package', help='package dir with root.rdb.original / root.rdx.original')
    ap.add_argument('--bones', help='lo-hi bone id range')
    args = ap.parse_args(argv)
    src = args.src
    if Path(src).exists():
        d = Path(src).read_bytes()
    else:
        if args.package is None:
            ap.error(f'{src} is not a file; give --package to read it as a resource hash')
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import ktdata
        pk = Path(args.package)
        recs = ktdata.parse_rdb(pk / 'root.rdb.original', pk / 'root.rdx.original')
        d = ktdata.read_entry(recs[int(src, 16)], pk)
    lo, hi = 0, 1 << 20
    if args.bones:
        lo, hi = (int(x) for x in args.bones.split('-'))
    a = parse(d)
    print('version', a['version'], 'fps', a['fps'], 'frames', a['length'], 'bones', len(a['bones']))
    for b, chans in sorted(a['bones'].items()):
        if not lo <= b <= hi:
            continue
        desc = []
        for c in chans:
            v = sample(c, a['length'])
            name = {0: 'rot', 1: 'pos', 2: 'scl'}.get(c['op'], c['op'])
            desc.append(f"{name} keys {len(c['frames'])} min {np.round(v.min(0), 3).tolist()} max {np.round(v.max(0), 3).tolist()}")
        print(b, ' | '.join(desc))


if __name__ == '__main__':
    main(sys.argv[1:])
