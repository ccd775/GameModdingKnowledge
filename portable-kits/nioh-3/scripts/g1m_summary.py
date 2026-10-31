"""One line per G1M: chunks, joints, submesh count (visible), vertices, LOD0-ish position bounds, palette bone range.
usage: g1m_summary.py <file.g1m> [...]"""
import argparse
import glob
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import g1m_tool as gt  # noqa: E402


def bounds(m):
    lo, hi = [1e9] * 3, [-1e9] * 3
    for a in m.attributes:
        pos = next((x for x in a['attrs'] if x['semantic'] == 'POSITION' and x['layer'] == 0), None)
        if pos is None or pos['type'] not in (0x02, 0x03):
            continue
        vb = m.vertex_buffers[a['buffers'][pos['buffer']]]
        step = max(1, vb['count'] // 2000)
        for i in range(0, vb['count'], step):
            p = struct.unpack_from('<3f', m.data, vb['offset'] + i * vb['stride'] + pos['offset'])
            for k in range(3):
                lo[k] = min(lo[k], p[k]); hi[k] = max(hi[k], p[k])
    return [round(v, 1) for v in lo], [round(v, 1) for v in hi]


ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('files', nargs='+', metavar='file.g1m', help='files or glob patterns')
args = ap.parse_args()
for f in [g for a in args.files for g in (sorted(glob.glob(a)) or [a])]:
    data = Path(f).read_bytes()
    try:
        ms = gt.embedded_models(data)
    except Exception as e:  # noqa: BLE001
        print(Path(f).name, 'ERR', e)
        continue
    for m in ms:
        try:
            joints = len(gt.skeleton(m)[0]) if 'SM1G' in m.chunks else 0
        except Exception:  # noqa: BLE001
            joints = -1
        vis = sum(not gt.is_hidden(m, s) for s in m.submeshes)
        bones = sorted({e['joint'] for p in m.palettes for e in p})
        lo, hi = bounds(m) if m.attributes else ([], [])
        print(f"{Path(f).name} {len(data)} chunks={'/'.join(m.chunks)} joints={joints} subs={len(m.submeshes)}"
              f" vis={vis} mats={len(m.materials)} verts={sum(b['count'] for b in m.vertex_buffers if b['stride'] > 1)}"
              f" bones={len(bones)}[{bones[:1]}..{bones[-1:]}] lo={lo} hi={hi}")
