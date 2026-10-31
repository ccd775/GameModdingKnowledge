"""Koei Tecmo G1A animation reader (port of Joschuka's Project-G1M G1A.h; Nioh 3 version 0042).
usage: g1a.py <file.g1a|hash> [--package <dir>] [--bones lo-hi] [--frames]

Layout: resource header (magic _A1G, version, size), u16 type (+2 pad), f32 duration, u32 data offset / 16, ...,
at +48 u16 bone-info count, u16 max bone id, bone infos (u32 bone id, u32 spline-info offset / 16 from +48).
Spline info: u32 opcode (1: 2 comps, 2: quat, 4: quat + loc, 6: scale + quat + loc, 8: scale + quat), then per
component (u32 key count, u32 data offset / 16); data: keys x 4 f32 cubic coefficients, then keys x f32 end time.
Value in a key's span [t0, t1]: a r^3 + b r^2 + c r + d with r = (t - t0) / (t1 - t0).
"""
import argparse
import struct
import sys
from pathlib import Path

import numpy as np

LAYOUT = {1: {'n': 2}, 2: {'n': 4, 'rot': 0}, 4: {'n': 7, 'rot': 0, 'loc': 4}, 6: {'n': 10, 'scl': 0, 'rot': 3, 'loc': 7},
          8: {'n': 7, 'scl': 0, 'rot': 3}}


def parse(d):
    magic, ver, size = struct.unpack_from('<4s4sI', d, 0)
    assert magic == b'_A1G', magic
    duration = struct.unpack_from('<f', d, 16)[0]
    n, max_id = struct.unpack_from('<2H', d, 48)
    bones = {}
    for i in range(n):
        bid, so = struct.unpack_from('<2I', d, 52 + 8 * i)
        base = 48 + so * 16
        op = struct.unpack_from('<I', d, base)[0]
        lay = LAYOUT.get(op)
        if lay is None:
            bones[bid] = {'op': op}
            continue
        comps = []
        for j in range(lay['n']):
            kc, do = struct.unpack_from('<2I', d, base + 4 + 8 * j)
            q = base + do * 16
            if ver > b'0040':
                coef = np.frombuffer(d, '<f4', 4 * kc, q).reshape(kc, 4); times = np.frombuffer(d, '<f4', kc, q + 16 * kc)
            else:
                times = np.frombuffer(d, '<f4', kc, q); coef = np.frombuffer(d, '<f4', 4 * kc, q + 4 * kc).reshape(kc, 4)
            comps.append((coef.copy(), times.copy()))
        bones[bid] = {'op': op, 'layout': lay, 'comps': comps}
    return {'version': ver, 'duration': duration, 'max_id': max_id, 'bones': bones}


def eval_comp(coef, times, t):
    k = int(np.searchsorted(times, t, side='right'))
    k = min(k, len(times) - 1)
    t0 = 0.0 if k == 0 else times[k - 1]
    r = (t - t0) / (times[k] - t0) if times[k] > t0 else 0.0
    a, b, c, dd = coef[k]
    return a * r ** 3 + b * r ** 2 + c * r + dd


def channel(bone, name, t):
    lay = bone['layout']
    if name not in lay:
        return None
    s = lay[name]; n = 4 if name == 'rot' else 3
    return np.array([eval_comp(*bone['comps'][s + i], t) for i in range(n)])


def key_times(bone):
    return sorted({0.0, *[float(x) for c in bone['comps'] for x in c[1]]})


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src', help='.g1a file, or a resource hash read through --package')
    ap.add_argument('--package', help='package dir with root.rdb.original / root.rdx.original')
    ap.add_argument('--bones', help='lo-hi bone id range')
    ap.add_argument('--frames', action='store_true', help='also print the key times')
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
    print('version', a['version'], 'duration', round(a['duration'], 3), 'bones', len(a['bones']), 'max id', a['max_id'])
    for b, bone in sorted(a['bones'].items()):
        if not lo <= b <= hi:
            continue
        if 'layout' not in bone:
            print(b, 'opcode', bone['op']); continue
        ts = key_times(bone)
        out = [f"op {bone['op']} keys {len(ts)}"]
        for name in ('rot', 'loc', 'scl'):
            vals = [channel(bone, name, t) for t in ts]
            if vals[0] is None:
                continue
            v = np.array(vals)
            out.append(f"{name} min {np.round(v.min(0), 3).tolist()} max {np.round(v.max(0), 3).tolist()}")
        print(b, ' | '.join(out))
        if args.frames:
            print('   times', [round(t, 3) for t in ts][:40])


if __name__ == '__main__':
    main(sys.argv[1:])
