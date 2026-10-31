"""Dump LLOC collision primitives (112 bytes each) of vanilla models as u32 / f32 words.
usage: lloc_dump.py <hash> [...]   (models read from N3_BUILD/orig/<hash>.g1m)"""
import argparse
import struct
import sys
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('hashes', nargs='+', metavar='hash')
args = ap.parse_args()

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'n3build'))
from n3_common import ORIG, gt  # noqa: E402


def dump(h):
    d = (ORIG / f'{h}.g1m').read_bytes(); m = gt.embedded_models(d)[-1]
    if 'LLOC' not in m.chunks:
        print(h, 'no LLOC'); return
    c = m.chunks['LLOC']
    t, sz, cnt = struct.unpack_from('<3I', d, c.offset + 16)
    q = c.offset + 28
    print(f'== {h}: {cnt} entries')
    for e in range(cnt):
        flags, n = struct.unpack_from('<2I', d, q)
        print(f' entry {e}: flags {flags:#x} n {n}')
        for i in range(n):
            p = q + 8 + 112 * i
            u = struct.unpack_from('<28I', d, p); f = struct.unpack_from('<28f', d, p)
            row = []
            for a, b in zip(u, f):
                row.append(f'{a}' if a < 0x10000 or a == 0xFFFFFFFF else f'{b:.3f}')
            print('   ', ' '.join(row))
        q += 8 + 112 * n


for h in args.hashes:
    dump(h)
