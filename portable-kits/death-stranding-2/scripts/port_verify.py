"""Checks a ported manifest offline: installs it in memory into the new build's graph and links (as install.ps1 would),
reads every group it touches, and compares them object by object with the same groups of the original mod build.

python port_verify.py <old root> <old modded out dir> <old report zip> <new root> <variant dir> <new version>
  <old modded out dir>: the build the release was made from (streaming_graph.core, streaming_links.stream,
  package.18.00.core.stream at graph file index 0x80), e.g. <workspace>\\out\\karin_v34.

Pointers must resolve to the mapped targets; other values may differ only where the two vanilla builds differ
(reported by type / field so that can be judged). Temp files go next to the variant's manifest and are removed.
"""
import collections
import json
import os
import struct
import sys

import numpy as np

from graph import Graph
from group import read_group
from mapgroups import build_map, load

PTR = ('Ref', 'UUIDRef', 'StreamingRef', 'WeakPtr', 'cptr')


def install(gb, man, archive_path):
    """New-build graph bytes (spans / locators -> file index len(Files)) and link bytes with the manifest applied."""
    g = bytearray(gb.raw)
    links = bytearray(gb.link_table)
    pos = gb.res['__pos__']
    span_at = pos['SpanTable'] + 4       # array count, then 12-byte entries
    loc_at = pos['LocatorTable'] + 4
    fi = len(gb.files)
    for grp in man['groups']:
        gi = gb.group_by_id[grp['gid']]
        G = gb.groups[gi]
        for s in grp['spans']:
            q = span_at + 12 * (G['SpanStart'] + s['k'])
            e = gb.res['SpanTable'][G['SpanStart'] + s['k']]
            assert struct.unpack_from('<III', g, q) == (e['FileIndexAndIsPatch'], e['Length'], e['Offset']), q
            struct.pack_into('<III', g, q, fi, s['length'], s['offset'])
        for lc in grp['locators']:
            q = loc_at + 8 * (G['LocatorStart'] + lc['k'])
            assert struct.unpack_from('<Q', g, q)[0] == gb.res['LocatorTable'][G['LocatorStart'] + lc['k']]['Data'], q
            struct.pack_into('<Q', g, q, (lc['offset'] << 24) | fi)
        for e in grp['link_edits']:
            a = G['LinkStart'] + e['rel']
            assert links[a:a + len(e['old']) // 2].hex() == e['old'], (grp['gid'], e)
            links[a:a + len(e['new']) // 2] = bytes.fromhex(e['new'])
    data = bytearray(open(archive_path, 'rb').read())
    for p in man.get('archive_patch', []):
        b = bytes.fromhex(p['hex'])
        data[p['offset']:p['offset'] + len(b)] = b
    return bytes(g), bytes(links), bytes(data), fi


def pointers_and_values(o, path, ptrs, vals):
    if isinstance(o, tuple) and len(o) == 3 and o[0] in PTR:
        ptrs.append((path, o))
    elif isinstance(o, dict):
        for k, v in o.items():
            if k not in ('__pos__', '__span__', '__off__', '__end__', 'Locator'):
                pointers_and_values(v, path + '.' + str(k), ptrs, vals)
    elif isinstance(o, list):
        for v in o:
            pointers_and_values(v, path + '[]', ptrs, vals)
    else:
        vals.append((path, o))


def same(a, b):
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        return isinstance(a, np.ndarray) and isinstance(b, np.ndarray) and a.shape == b.shape and np.array_equal(a, b)
    return a == b


def main():
    old_root, old_out, old_report, new_root, vdir, version = sys.argv[1:7]
    man_old = json.load(open(os.path.join(vdir, 'manifest.json'), encoding='utf-8'))
    man_new = json.load(open(os.path.join(vdir, 'manifest_%s.json' % version), encoding='utf-8'))
    archive = os.path.join(vdir, man_new['archive']['file'])
    ga, gb, known = load(old_root, os.path.join(old_root, 'LocalCacheWinGame', 'package', 'streaming_graph.core.org'),
                         os.path.join(old_root, 'LocalCacheWinGame', 'package', 'streaming_links.stream'), old_report, new_root)
    go = Graph(old_root, graph_path=os.path.join(old_out, 'streaming_graph.core'),
               overrides={0x80: os.path.join(old_out, 'package.18.00.core.stream')})
    go._links = open(os.path.join(old_out, 'streaming_links.stream'), 'rb').read()

    graph_b, links_b, data_b, fi = install(gb, man_new, archive)
    tg, ta = os.path.join(vdir, '_verify_graph.core'), os.path.join(vdir, '_verify_archive.stream')
    open(tg, 'wb').write(graph_b)
    open(ta, 'wb').write(data_b)
    try:
        gn = Graph(new_root, graph_path=tg, overrides={fi: ta})
        gn._links = links_b
        for go_grp, gn_grp in zip(man_old['groups'], man_new['groups']):
            old_gid, new_gid = go_grp['gid'], gn_grp['gid']
            try:
                oo = read_group(go, old_gid)
            except OSError:
                oo = None
            on = read_group(gn, new_gid)       # must parse: core and links consistent
            if oo is None:
                print('%6d -> %6d: new reads (%d objects); old build unreadable here, not compared' % (
                    old_gid, new_gid, len(on)))
                continue
            assert [o['__type__'] for o in oo] == [o['__type__'] for o in on], old_gid
            po, vo, pn, vn = [], [], [], []
            for o in oo:
                pointers_and_values(o, o['__type__'], po, vo)
            for o in on:
                pointers_and_values(o, o['__type__'], pn, vn)
            targets = {t[1] for _, t in po if t[1] is not None}
            gmap, _, _ = build_map(ga, gb, sorted(ga.group_by_id[t] for t in targets if t in ga.group_by_id), known)
            idmap = {ga.groups[a]['GroupID']: gb.groups[b]['GroupID'] for a, b in gmap.items()}
            bad_ptr = [(p, x, y) for (p, x), (_, y) in zip(po, pn)
                       if not (x[0] == y[0] and x[2] == y[2] and (x[1] is None and y[1] is None or idmap.get(x[1]) == y[1]))]
            diff_vals = collections.Counter(p for (p, x), (_, y) in zip(vo, vn) if not same(x, y))
            print('%6d -> %6d: %d objects, %d pointers (%d not matching), %d values differ%s' % (
                old_gid, new_gid, len(on), len(po), len(bad_ptr), sum(diff_vals.values()),
                '' if len(po) == len(pn) and len(vo) == len(vn) else ' (COUNTS DIFFER %d/%d %d/%d)' % (
                    len(po), len(pn), len(vo), len(vn))))
            # a mismatch whose old target has no counterpart at all is a group the new build changed (e.g. recompiled
            # shaders): the vanilla record already points at the new one; anything else is listed as SUSPECT
            agg = collections.Counter((p, x[1], y[1], x[1] in idmap) for p, x, y in bad_ptr)
            for (p, a_, b_, mapped), n in sorted(agg.items(), key=lambda t: -t[1]):
                print('     %s %4d x %s: group %s -> %s' % ('SUSPECT' if mapped else 'changed', n, p, a_, b_))
            for p, n in diff_vals.most_common(8):
                print('     %5d  %s' % (n, p))
    finally:
        for g in (locals().get('gn'),):
            if g is not None:
                for a in g._archives.values():
                    a.close()
        os.remove(tg)
        os.remove(ta)


if __name__ == '__main__':
    if sys.argv[1:2] in (['-h'], ['--help']) or len(sys.argv) < 7:
        print(__doc__)
        raise SystemExit(0 if sys.argv[1:2] in (['-h'], ['--help']) else 2)
    main()
