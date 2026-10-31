"""build23 -> build24 check: which G1M chunks changed, the new LLOC entry in world space, and the type-4 entries'
collision lists. usage: diff24.py old.g1m new.g1m"""
import argparse
import struct
import sys
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('old', help='earlier build .g1m'); ap.add_argument('new', help='later build .g1m')
args = ap.parse_args()

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'n3build'))
import g1m_tool as gt  # noqa: E402
import nuno4  # noqa: E402
from n3_common import skeleton  # noqa: E402

old, new = (open(p, 'rb').read() for p in (args.old, args.new))
mo, mn = gt.embedded_models(old)[-1], gt.embedded_models(new)[-1]
for name in mn.chunks:
    a, b = mo.chunks[name], mn.chunks[name]
    same = old[a.offset:a.end] == new[b.offset:b.end]
    if not same:
        print(f'{name}: changed ({a.end - a.offset} -> {b.end - b.offset} bytes)')
fo, fn = mo.chunks['FM1G'], mn.chunks['FM1G']
wo = struct.unpack_from(f'<{(fo.end - fo.offset) // 4}I', old, fo.offset)
wn = struct.unpack_from(f'<{(fn.end - fn.offset) // 4}I', new, fn.offset)
print('FM1G words changed:', [(i * 4, x, y) for i, (x, y) in enumerate(zip(wo, wn)) if x != y])
c = mn.chunks['LLOC']
t, sz, cnt = struct.unpack_from('<3I', new, c.offset + 16)
q = c.offset + 28
sk = skeleton(mn)
for e in range(cnt):
    flags, n = struct.unpack_from('<2I', new, q)
    bones = [struct.unpack_from('<I', new, q + 8 + 112 * i + 4)[0] for i in range(n)]
    print(f'LLOC entry {e}: flags {flags:#x} n {n} bones {bones}')
    if e == cnt - 1:
        for i in range(n):
            f = struct.unpack_from('<28f', new, q + 8 + 112 * i); u = struct.unpack_from('<4I', new, q + 8 + 112 * i)
            W = sk[u[1]]['world']
            ctr = W[:3, :3] @ np.array(f[20:23]) + W[:3, 3]
            ax = W[:3, :3] @ np.array([f[8:11], f[12:15], f[16:19]]).T
            print(f'   shape {u[0]} bone {u[1]} semi {np.round(f[4:7], 2)} world centre {ctr.round(2)} '
                  f'world semi (x,y,z) {np.abs(ax * np.array(f[4:7])).max(1).round(2)} w23 {f[23]}')
    q += 8 + 112 * n
for label, d, m in (('old', old, mo), ('new', new, mn)):
    on = nuno4.parse_onun(d, m)
    t4 = [s for s in on['subs'] if s['type'] == 0x30004][0]['entries']
    print(label, 'type-4 collision lists:', [e.get('lloc', e.get('collision')) for e in t4][:30])
