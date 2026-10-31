"""Offline gate for a packed mod: read groups through the patched graph + packed file and decode mesh positions.

python verify_pack.py <out dir> <gid> <mesh idx> [<mesh idx> ...]
"""
import argparse
import os
import struct
import sys

import numpy as np

from graph import Graph, game_root
from group import read_group

PACK_INDEX = 0x80


def positions(g, objs, gid, mi):
    """Decode float positions of every primitive of a mesh from its streaming data (Pos is Float @0 of stream 0)."""
    m = objs[mi]
    sds = m['StreamingDataSource']
    fi, off = sds['Locator']
    blob = g.read_file(fi, off + sds['Offset'], sds['Length'])
    out = []
    pos = 0
    for pref in m['Primitives']:
        prim = objs[pref[2]]
        va = objs[prim['VertexArray'][2]]
        ia = objs[prim['IndexArray'][2]]
        n = va['Count']
        s0 = va['Streams'][0]
        p = np.frombuffer(blob, np.float32, count=n * s0['Stride'] // 4, offset=pos).reshape(n, -1)[:, :3]
        out.append((n, p))
        # advance: vertex streams then indices (layout checked against the tool log offsets)
        for s in va['Streams']:
            pos += s['Stride'] * n
        pos += ia['Count'] * (2 if ia['Format'] == 0 else 4)
        pos = (pos + 15) & ~15
    return out, fi, off, sds['Length'], len(blob)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out_dir'); ap.add_argument('gid', type=int); ap.add_argument('meshes', nargs='*', type=int)
    a = ap.parse_args()
    out_dir, gid = a.out_dir, a.gid
    g = Graph(game_root(), graph_path=os.path.join(out_dir, 'streaming_graph.core'),
              overrides={PACK_INDEX: os.path.join(out_dir, 'package.18.00.core.stream')})
    gi = g.group_by_id[gid]
    print('group %d spans %s' % (gid, g.group_spans(gi)))
    objs = read_group(g, gid)
    print('parsed %d objects through the packed graph' % len(objs))
    for mi in a.meshes:
        prims, fi, off, length, got = positions(g, objs, gid, mi)
        print('mesh %d: data file 0x%x @%d length %d (read %d)' % (mi, fi, off, length, got))
        for n, p in prims:
            print('   %d verts, min %s max %s' % (n, np.round(p.min(0), 3).tolist(), np.round(p.max(0), 3).tolist()))


if __name__ == '__main__':
    main()
