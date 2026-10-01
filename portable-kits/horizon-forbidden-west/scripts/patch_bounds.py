"""Widen the LocalBounds of Beta's mesh hierarchy (group b2c4 core) to contain the Karin parts.

The importer keeps the vanilla boxes; Karin's ears, twin tails and tail reach outside them.
usage: patch_bounds.py CORE WORK
"""
import argparse
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hfwascii as H  # noqa: E402

ap = argparse.ArgumentParser(description="Widen Beta's LocalBounds and switch the CsNbtGen face SkinInfo parts "
                                         'to VsNbt in the imported b2c4 core (edited in place).')
ap.add_argument('core', help='02_19A7C73A.core written by make_mod.py')
ap.add_argument('work', help='build_hfw.py --work folder (reads ascii/lod0_*.ascii)')
args = ap.parse_args()
core_path, work = args.core, args.work
d = bytearray(open(core_path, 'rb').read())
A = os.path.join(work, 'ascii')


def bounds(files_subs):
    P = []
    for f, si in files_subs:
        _, ms = H.read_meshes(os.path.join(A, f), has_skeleton=True)
        P.append(ms[si]['pos'])
    P = np.concatenate(P)
    return P.min(0) - 0.02, P.max(0) + 0.02


# vanilla box (min xyz) -> Karin content that the box must also hold
BOXES = {
    'multi23': ((-0.58010125, -0.13116057, -0.0010226276), [('lod0_215.ascii', 1), ('lod0_260.ascii', 0), ('lod0_625.ascii', 0)]),
    'upper446': ((-0.58010125, -0.119961806, 0.7060173), [('lod0_215.ascii', 1)]),
    'lower57': ((-0.21693961, -0.13116057, -0.0010226276), [('lod0_260.ascii', 0)]),
    'face87': ((-0.0912399, -0.06903442, 1.3883084), [('lod0_625.ascii', 0)]),
}
for name, (mn, content) in BOXES.items():
    pat = struct.pack('<3f', *mn)
    hits = []
    i = d.find(pat)
    while i >= 0:
        hits.append(i)
        i = d.find(pat, i + 1)
    if len(hits) != 1:
        raise SystemExit(f'{name}: {len(hits)} matches')
    o = hits[0]
    vmin = np.array(struct.unpack_from('<3f', d, o))
    vmax = np.array(struct.unpack_from('<3f', d, o + 12))
    kmin, kmax = bounds(content)
    nmin, nmax = np.minimum(vmin, kmin), np.maximum(vmax, kmax)
    struct.pack_into('<6f', d, o, *nmin, *nmax)
    print(name, 'vanilla', vmin.round(3), vmax.round(3), '->', nmin.round(3), nmax.round(3))
# Skin info parts that regenerate normals on the GPU (CsNbtGen, type 7) from the vanilla vertex count: with new
# geometry the compute pass runs over the old count. Same fix as the reference Karin mod: vertex-shader NBT
# (type 5) and no compute count. Located by their vanilla (VertexCount, VertexComputeNbtCount) pair.
CS_NBT = {'625': (22895, 22816), '109': (5871, 5775), '514sm0': (4626, 4459), '514sm1': (960, 866),
          '644sm0': (1776, 1710), '644sm1': (424, 370)}
for name, (vc, nbt) in CS_NBT.items():
    pat = struct.pack('<ii', vc, nbt)
    hits = []
    i = d.find(pat)
    while i >= 0:
        hits.append(i)
        i = d.find(pat, i + 1)
    if len(hits) != 1:
        raise SystemExit(f'skininfo {name}: {len(hits)} matches')
    o = hits[0]
    t = struct.unpack_from('<I', d, o - 24)[0]
    if t != 7:
        raise SystemExit(f'skininfo {name}: type {t} at {o - 24}, expected 7 (CsNbtGen)')
    struct.pack_into('<I', d, o - 24, 5)
    struct.pack_into('<i', d, o + 4, -1)
    print('skininfo', name, 'CsNbtGen -> VsNbt at', o - 24)
open(core_path, 'wb').write(bytes(d))
