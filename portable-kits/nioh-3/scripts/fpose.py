"""Nioh 3 facial pose library (g1fpose, magic 1FPO0011) and facial weight animation (g1frani, magic 1FRA0020).
usage: fpose.py <file.g1fpose|file.g1frani> [--pose N]

g1fpose: +16 u16 record size (48), u16 pose count, +20 u32 bone count, +24 u32 record count, +28 u32 1,
then per bone (u32 bone id, pose count x u32 record offset from +32, 0 = bone not moved by that pose),
then records: f32 scale xyz, pad, rotation vector xyz (radians, bone-local), pad, translation xyz (parent space, cm), 1.
Pose 0 is unused (no records). Face bones are world-aligned in the bind pose (bone 400 under the head bone 12).

g1frani: +12 u16 32, u16 4, +16 u16 4, u16 60 (fps), +20 u32 channel bound, +24 u32 frame count, +28 u32 pair count,
+32 (frames + 1) x u32 frame data offsets from +32; frame data = pairs (u16 pose index, f16 weight).
"""
import argparse
import struct
import sys
from pathlib import Path

import numpy as np


def parse_pose(d):
    assert d[:8] == b'1FPO0011', d[:8]
    rs, npose, nb, nrec, _ = struct.unpack_from('<HHIII', d, 16)
    assert rs == 48
    bones, o = {}, 32
    for _ in range(nb):
        bid = struct.unpack_from('<I', d, o)[0]
        offs = struct.unpack_from(f'<{npose}I', d, o + 4)
        o += 4 + 4 * npose
        bones[bid] = {p: np.frombuffer(d, '<f4', 12, 32 + x).astype(float) for p, x in enumerate(offs) if x}
    poses = [dict() for _ in range(npose)]
    for b, recs in bones.items():
        for p, r in recs.items():
            poses[p][b] = {'scale': r[0:3], 'rot': r[4:7], 'loc': r[8:11]}
    return {'npose': npose, 'bones': sorted(bones), 'poses': poses}


def parse_anim(d):
    assert d[:8] == b'1FRA0020', d[:8]
    fps = struct.unpack_from('<H', d, 18)[0]
    bound, nframes, npairs = struct.unpack_from('<3I', d, 20)
    offs = struct.unpack_from(f'<{nframes + 1}I', d, 32)
    frames = []
    for f in range(nframes):
        a, b = 32 + offs[f], 32 + offs[f + 1]
        n = (b - a) // 4
        idx = np.frombuffer(d, '<u2', 2 * n, a).reshape(n, 2)[:, 0]
        w = np.frombuffer(d, '<f2', 2 * n, a).reshape(n, 2)[:, 1].astype(float)
        frames.append(dict(zip(idx.tolist(), w.tolist())))
    return {'fps': fps, 'bound': bound, 'frames': frames}


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('file', help='.g1fpose or .g1frani')
    ap.add_argument('--pose', type=int, help='g1fpose: print this pose\'s bone deltas')
    args = ap.parse_args(argv)
    d = Path(args.file).read_bytes()
    if d[:4] == b'1FPO':
        a = parse_pose(d)
        print('poses', a['npose'], 'bones', len(a['bones']), a['bones'][0], '..', a['bones'][-1])
        if args.pose is not None:
            p = args.pose
            for b, r in sorted(a['poses'][p].items()):
                print(b, 'rot', np.round(r['rot'], 4).tolist(), 'loc', np.round(r['loc'], 4).tolist(),
                      'scale', np.round(r['scale'], 4).tolist())
    else:
        a = parse_anim(d)
        ch = sorted({c for f in a['frames'] for c in f})
        print('fps', a['fps'], 'frames', len(a['frames']), 'channels used', len(ch), 'bound', a['bound'])
        for c in ch:
            v = np.array([f.get(c, 0.0) for f in a['frames']])
            print(c, 'min', round(v.min(), 3), 'max', round(v.max(), 3), 'mean', round(v.mean(), 3))


if __name__ == '__main__':
    main(sys.argv[1:])
