"""Field-level 3-way check of a port: for each replaced core, every object's leaf fields in old vanilla (v0), new vanilla
(v1), the original mod build (m) and the ported install (p).

python port_fields.py <old root> <old modded out dir> <old report zip> <new root> <variant dir> <new version> [gid...]

Per field: v0 == v1 -> p must equal m; m == v0 -> p must equal v1; else both changed it (conflict). Pointers compare as
(kind, mapped group, index). Also lists objects where the mod changed some fields and the new build changed others
(the byte merge keeps both, which is only right if they are independent, e.g. not a shader swap next to recompiled
texture-binding words).
"""
import collections
import json
import os
import sys

import numpy as np

from graph import Graph
from group import read_group
from mapgroups import build_map, load
from port_verify import PTR, install


def leaves(o, path, out):
    if isinstance(o, tuple) and len(o) == 3 and o[0] in PTR:
        out[path] = ('ptr', o)
    elif isinstance(o, dict):
        for k, v in o.items():
            if k not in ('__pos__', '__span__', '__off__', '__end__', 'Locator'):
                leaves(v, path + '.' + str(k), out)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            leaves(v, '%s[%d]' % (path, i), out)
    elif isinstance(o, np.ndarray):
        out[path] = ('arr', o.tobytes())
    else:
        out[path] = ('val', o)


def norm(x, idmap, own_old, own_new, side):
    """Comparable form; old-build pointers are mapped to new group IDs."""
    if x is None or x[0] != 'ptr':
        return x
    k, g, i = x[1]
    if side == 'old':
        g = own_new if g == own_old else idmap.get(g, ('unmapped', g))
    return ('ptr', (k, g, i))


def main():
    old_root, old_out, old_report, new_root, vdir, version = sys.argv[1:7]
    only = {int(x) for x in sys.argv[7:]}
    man_old = json.load(open(os.path.join(vdir, 'manifest.json'), encoding='utf-8'))
    man_new = json.load(open(os.path.join(vdir, 'manifest_%s.json' % version), encoding='utf-8'))
    ga, gb, known = load(old_root, os.path.join(old_root, 'LocalCacheWinGame', 'package', 'streaming_graph.core.org'),
                         os.path.join(old_root, 'LocalCacheWinGame', 'package', 'streaming_links.stream'), old_report, new_root)
    go = Graph(old_root, graph_path=os.path.join(old_out, 'streaming_graph.core'),
               overrides={0x80: os.path.join(old_out, 'package.18.00.core.stream')})
    go._links = open(os.path.join(old_out, 'streaming_links.stream'), 'rb').read()
    graph_b, links_b, data_b, fi = install(gb, man_new, os.path.join(vdir, man_new['archive']['file']))
    tg, ta = os.path.join(vdir, '_fields_graph.core'), os.path.join(vdir, '_fields_archive.stream')
    open(tg, 'wb').write(graph_b)
    open(ta, 'wb').write(data_b)
    gn = None
    try:
        gn = Graph(new_root, graph_path=tg, overrides={fi: ta})
        gn._links = links_b
        for go_grp, gn_grp in zip(man_old['groups'], man_new['groups']):
            old_gid, new_gid = go_grp['gid'], gn_grp['gid']
            if only and old_gid not in only:
                continue
            if not go_grp['spans'] and not only:
                continue                 # core not replaced: p is new vanilla plus link edits (port_verify covers it)
            try:
                o0 = read_group(ga, old_gid)
            except OSError:
                print('%6d: old vanilla unreadable' % old_gid)
                continue
            o1, om, op = read_group(gb, new_gid), read_group(go, old_gid), read_group(gn, new_gid)
            ptr_groups = set()
            for objs in (o0, om):
                for o in objs:
                    d = {}
                    leaves(o, '', d)
                    ptr_groups |= {v[1][1] for v in d.values() if v[0] == 'ptr' and v[1][1] is not None}
            gmap, _, _ = build_map(ga, gb, sorted(ga.group_by_id[t] for t in ptr_groups if t in ga.group_by_id), known)
            idmap = {ga.groups[a]['GroupID']: gb.groups[b]['GroupID'] for a, b in gmap.items()}
            wrong, conflicts, mixed = collections.Counter(), [], collections.Counter()
            examples = []
            for n, (a0, a1, am, ap) in enumerate(zip(o0, o1, om, op)):
                L0, L1, Lm, Lp = {}, {}, {}, {}
                for o, L in ((a0, L0), (a1, L1), (am, Lm), (ap, Lp)):
                    leaves(o, '', L)
                keys = set(L0) | set(L1) | set(Lm) | set(Lp)
                mod_changed, van_changed = [], []
                for k in keys:
                    v0 = norm(L0.get(k), idmap, old_gid, new_gid, 'old')
                    v1 = norm(L1.get(k), idmap, old_gid, new_gid, 'new')
                    m = norm(Lm.get(k), idmap, old_gid, new_gid, 'old')
                    p = norm(Lp.get(k), idmap, old_gid, new_gid, 'new')
                    if m != v0:
                        mod_changed.append(k)
                    if v1 != v0:
                        van_changed.append(k)
                    if v0 == v1:
                        want = m
                    elif m == v0:
                        want = v1
                    else:
                        conflicts.append((n, a0['__type__'], k, v0, v1, m, p))
                        continue
                    if p != want:
                        wrong[(a0['__type__'], k.split('[')[0])] += 1
                        if len(examples) < 8:
                            examples.append((n, a0['__type__'], k, v0, v1, m, p))
                if mod_changed and van_changed:
                    mixed[a0['__type__']] += 1
                    if len(examples) < 16:
                        examples.append(('MIXED', n, a0['__type__'], sorted(mod_changed)[:6], sorted(van_changed)[:6]))
            print('%6d -> %6d: %d objects; %d fields not as expected, %d conflicts, objects changed by both: %s' % (
                old_gid, new_gid, len(op), sum(wrong.values()), len(conflicts), dict(mixed)))
            for k, c in wrong.most_common(10):
                print('     wrong %4d  %s' % (c, k))
            for c in conflicts[:10]:
                print('     conflict', c)
            for e in examples:
                print('     ', e)
    finally:
        if gn is not None:
            for a in gn._archives.values():
                a.close()
        os.remove(tg)
        os.remove(ta)


if __name__ == '__main__':
    if sys.argv[1:2] in (['-h'], ['--help']) or len(sys.argv) < 7:
        print(__doc__)
        raise SystemExit(0 if sys.argv[1:2] in (['-h'], ['--help']) else 2)
    main()
