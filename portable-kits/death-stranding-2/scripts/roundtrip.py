"""Offline round-trip check of ds2_pc_mi imports.

prep:    python roundtrip.py prep <skel.ascii> <mesh.ascii> <out.ascii>        (prepend skeleton header)
compare: python roundtrip.py compare <gid> <pristine core> <new core>       (diff objects of a group span)
"""
import argparse
import sys

from ds2rtti import Reader
from graph import Graph, game_root
from group import GroupReader


def prep(skel, mesh, out):
    s = open(skel, encoding='utf-8').read().rstrip('\n')
    m = open(mesh, encoding='utf-8').read()
    open(out, 'w', encoding='utf-8', newline='\n').write(s + '\n' + m)


def read_span(g, gid, data):
    gi = g.group_by_id[gid]
    types = g.group_types(gi)
    reader = GroupReader(g, gi)
    r = Reader(data)
    objs = []
    while r.remaining() > 0:
        start = r.pos
        o = reader.read_compound(types[len(objs)], r)
        o['__off__'], o['__end__'] = start, r.pos
        objs.append(o)
    return objs


def strip(v):
    if isinstance(v, dict):
        return {k: strip(x) for k, x in v.items() if k not in ('__off__', '__end__', '__pos__', 'DataOffset', 'EmbeddedDataOffset')}
    if isinstance(v, list):
        return [strip(x) for x in v]
    return v


def diff(a, b, path, out):
    if type(a) != type(b):
        out.append('%s: type %s -> %s' % (path, type(a).__name__, type(b).__name__))
    elif isinstance(a, dict):
        for k in set(a) | set(b):
            diff(a.get(k), b.get(k), path + '.' + str(k), out)
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append('%s: len %d -> %d' % (path, len(a), len(b)))
        for i, (x, y) in enumerate(zip(a, b)):
            diff(x, y, '%s[%d]' % (path, i), out)
    elif a != b:
        out.append('%s: %r -> %r' % (path, a if not isinstance(a, bytes) else 'bytes%d' % len(a),
                                       b if not isinstance(b, bytes) else 'bytes%d' % len(b)))


def compare(gid, pristine, new):
    g = Graph(game_root())
    A = read_span(g, gid, open(pristine, 'rb').read())
    B = read_span(g, gid, open(new, 'rb').read())
    print('objects', len(A), len(B))
    for i, (a, b) in enumerate(zip(A, B)):
        out = []
        diff(strip(a), strip(b), '', out)
        if out or (a['__end__'] - a['__off__']) != (b['__end__'] - b['__off__']):
            print('%d %s size %d -> %d' % (i, a['__type__'], a['__end__'] - a['__off__'], b['__end__'] - b['__off__']))
            for line in out[:25]:
                print('    ' + line)
            if len(out) > 25:
                print('    ... %d more' % (len(out) - 25))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('prep'); p.add_argument('skel'); p.add_argument('mesh'); p.add_argument('out')
    c = sub.add_parser('compare'); c.add_argument('gid', type=int); c.add_argument('pristine'); c.add_argument('new')
    a = ap.parse_args()
    if a.cmd == 'prep':
        prep(a.skel, a.mesh, a.out)
    else:
        compare(a.gid, a.pristine, a.new)
