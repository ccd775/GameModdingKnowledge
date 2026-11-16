"""Field-level diff of one group's objects between two builds.

python corediff.py <new root> <new gid> <old core file> [max lines]

<old core file>: the old build's decompressed group data, read from that build's own files (a ds2_pc_mi export's
*.core.pristine re-writes a few bytes, so it shows small differences that are not the build's); the new build's
is read from <new root>. Both are parsed with the new group's type list (the builds share its type hashes), and every
object whose bytes differ is compared field by field. Prints a summary per (type, field path) and the first changes.
"""
import collections
import hashlib
import sys

import numpy as np

from ds2rtti import Reader
from graph import Graph
from group import GroupReader


def parse(g, gi, data):
    types = g.group_types(gi)
    rd = GroupReader(g, gi)
    r = Reader(data)
    out = []
    for t in types:
        start = r.pos
        obj = rd.read_compound(t, r)
        out.append((t, start, r.pos, obj))
    assert r.remaining() == 0, r.remaining()
    return out


def walk(a, b, path, out):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in a:
            if k in ('__pos__',):
                continue
            walk(a[k], b.get(k), path + (k,), out)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            walk(x, y, path + ('[]',), out)
    elif isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        if not (isinstance(a, np.ndarray) and isinstance(b, np.ndarray) and a.shape == b.shape and np.array_equal(a, b)):
            out.append((path, 'array', 'array'))
    elif isinstance(a, (bytes, bytearray)) or isinstance(b, (bytes, bytearray)):
        if a != b:
            out.append((path, 'bytes(%d)' % len(a or b''), 'bytes(%d)' % len(b or b'')))
    elif a != b:
        out.append((path, a, b))


def main():
    root, gid, old_file = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    lines = int(sys.argv[4]) if len(sys.argv) > 4 else 40
    g = Graph(root)
    gi = g.group_by_id[gid]
    new = b''.join(g.read_file(fi, off, ln) for fi, off, ln in g.group_spans(gi))
    old = open(old_file, 'rb').read()
    print('old %d bytes sha1 %s / new %d bytes sha1 %s' % (len(old), hashlib.sha1(old).hexdigest()[:12], len(new),
                                                          hashlib.sha1(new).hexdigest()[:12]))
    if len(old) == len(new):
        d = np.nonzero(np.frombuffer(old, np.uint8) != np.frombuffer(new, np.uint8))[0]
        print('differing bytes: %d' % len(d))
    po, pn = parse(g, gi, old), parse(g, gi, new)
    summary = collections.Counter()
    first = []
    nobj = 0
    for i, ((t, s0, e0, a), (_, s1, e1, b)) in enumerate(zip(po, pn)):
        if old[s0:e0] == new[s1:e1]:
            continue
        nobj += 1
        diffs = []
        walk(a, b, (), diffs)
        if not diffs:
            diffs = [(('<bytes only>',), e0 - s0, e1 - s1)]
        for path, x, y in diffs:
            summary[(t, '.'.join(path))] += 1
            if len(first) < lines:
                first.append('  #%d %s.%s: %r -> %r' % (i, t, '.'.join(path), str(x)[:60], str(y)[:60]))
    print('objects differing: %d of %d' % (nobj, len(po)))
    for (t, p), n in summary.most_common(30):
        print('  %5d  %s.%s' % (n, t, p))
    print('\n'.join(first))


if __name__ == '__main__':
    if sys.argv[1:2] in (['-h'], ['--help']) or len(sys.argv) < 4:
        print(__doc__)
        raise SystemExit(0 if sys.argv[1:2] in (['-h'], ['--help']) else 2)
    main()
