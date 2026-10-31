"""Turns a packed build (out/<name>: package.18.00.core.stream, streaming_graph.core, streaming_links.stream) into a
release variant that the PowerShell installer (remote/release/install.ps1) applies to any game copy whose touched
groups match the vanilla ones this build was made from.

python make_release.py <out dir> <release variant dir> "<title>" [--vanilla-graph ...] [--vanilla-links ...]

Writes <variant dir>/karin.core.stream (the packed archive) and manifest.json. Packing redirects whole spans and
stream locators to file index 0x80 and leaves every other graph table alone; the links only change in place. The
manifest keeps, per touched group, what the installer checks first (object / type / subgroup / link fingerprints of
the vanilla group) and the redirects and link edits it then writes.
"""
import argparse
import bisect
import hashlib
import json
import os
import shutil
import struct
import sys

import numpy as np

from graph import Graph, clean_root, modding_dir
PACK_INDEX = 0x80
FIELDS = ('NumObjects', 'GroupSize', 'SubGroupCount', 'SpanCount', 'TypeCount', 'LinkSize', 'LocatorCount')


def type_hashes(g, gi):
    r = g.res['TypeTableData']
    grp = g.groups[gi]
    idx = struct.unpack_from('<%dH' % grp['TypeCount'], r, 20 + 2 * grp['TypeStart'])
    return b''.join(struct.pack('<Q', g.res['TypeHashes'][i]) for i in idx)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out'); ap.add_argument('dst'); ap.add_argument('title')
    ap.add_argument('--vanilla-graph', help='default: <clean root>/LocalCacheWinGame/package/streaming_graph.core.org')
    ap.add_argument('--vanilla-links', help='default: DS2_MODDING/backup/streaming_links.stream')
    a = ap.parse_args()
    out, dst, title = a.out, a.dst, a.title
    vanilla_graph = a.vanilla_graph or os.path.join(clean_root(), 'LocalCacheWinGame', 'package', 'streaming_graph.core.org')
    vanilla_links = a.vanilla_links or modding_dir('backup', 'streaming_links.stream')
    gv = Graph(clean_root(), graph_path=vanilla_graph)
    gm = Graph(clean_root(), graph_path=os.path.join(out, 'streaming_graph.core'))
    va, ma = gv.raw, gm.raw
    assert len(va) == len(ma)
    # every changed byte must sit in a span or locator entry
    pos = sorted(gv.res['__pos__'].items(), key=lambda t: t[1])
    changed = set()
    d = np.nonzero(np.frombuffer(va, np.uint8) != np.frombuffer(ma, np.uint8))[0]
    starts = [p for _, p in pos]
    for x in d:
        changed.add(pos[bisect.bisect_right(starts, int(x)) - 1][0])
    assert changed <= {'SpanTable', 'LocatorTable'}, changed

    span_owner, loc_owner, link_owner = {}, {}, []
    for gi, grp in enumerate(gv.groups):
        for s in range(grp['SpanStart'], grp['SpanStart'] + grp['SpanCount']):
            span_owner.setdefault(s, []).append(gi)
        for s in range(grp['LocatorStart'], grp['LocatorStart'] + grp['LocatorCount']):
            loc_owner.setdefault(s, []).append(gi)
        if grp['LinkSize']:
            link_owner.append((grp['LinkStart'], grp['LinkStart'] + grp['LinkSize'], gi))
    link_owner.sort()

    touched = {}

    def entry(gi):
        if gi not in touched:
            touched[gi] = dict(spans=[], locators=[], link_edits=[])
        return touched[gi]

    for s, (x, y) in enumerate(zip(gv.res['SpanTable'], gm.res['SpanTable'])):
        if (x['FileIndexAndIsPatch'], x['Offset'], x['Length']) == (y['FileIndexAndIsPatch'], y['Offset'], y['Length']):
            continue
        assert y['FileIndexAndIsPatch'] == PACK_INDEX and len(span_owner.get(s, [])) == 1, (s, y, span_owner.get(s))
        gi = span_owner[s][0]
        entry(gi)['spans'].append(dict(k=s - gv.groups[gi]['SpanStart'], vanilla_length=x['Length'],
                                       offset=y['Offset'], length=y['Length']))
    for s, (x, y) in enumerate(zip(gv.res['LocatorTable'], gm.res['LocatorTable'])):
        if x['Data'] == y['Data']:
            continue
        assert y['Data'] & 0xFFFFFF == PACK_INDEX and len(loc_owner.get(s, [])) == 1, (s, loc_owner.get(s))
        gi = loc_owner[s][0]
        entry(gi)['locators'].append(dict(k=s - gv.groups[gi]['LocatorStart'], offset=y['Data'] >> 24))

    lv = open(vanilla_links, 'rb').read()
    lm = open(os.path.join(out, 'streaming_links.stream'), 'rb').read() \
        if os.path.exists(os.path.join(out, 'streaming_links.stream')) else lv
    assert len(lv) == len(lm) == gv.res['LinkTableSize']
    ld = np.nonzero(np.frombuffer(lv, np.uint8) != np.frombuffer(lm, np.uint8))[0]
    runs = []                                   # contiguous changed byte runs
    for x in ld:
        x = int(x)
        if runs and x == runs[-1][1]:
            runs[-1][1] = x + 1
        else:
            runs.append([x, x + 1])
    lstarts = [a for a, _, _ in link_owner]
    for a, b in runs:
        k = bisect.bisect_right(lstarts, a) - 1
        s, e, gi = link_owner[k]
        assert s <= a and b <= e, (a, b, link_owner[k])
        entry(gi)['link_edits'].append(dict(rel=a - s, old=lv[a:b].hex(), new=lm[a:b].hex()))

    groups = []
    for gi in sorted(touched, key=lambda i: gv.groups[i]['GroupID']):
        grp = gv.groups[gi]
        t = touched[gi]
        assert not grp['ObjectUUIDs']
        check = {f: grp[f] for f in FIELDS}
        check['types_sha1'] = hashlib.sha1(type_hashes(gv, gi)).hexdigest()
        check['subgroups'] = [gv.groups[s]['GroupID'] for s in gv.subgroups(gi)]
        check['links_sha1'] = hashlib.sha1(lv[grp['LinkStart']:grp['LinkStart'] + grp['LinkSize']]).hexdigest()
        groups.append(dict(gid=grp['GroupID'], check=check, **t))

    os.makedirs(dst, exist_ok=True)
    arc = os.path.join(dst, 'karin.core.stream')
    shutil.copyfile(os.path.join(out, 'package.18.00.core.stream'), arc)
    h = hashlib.sha256()
    with open(arc, 'rb') as f:
        for block in iter(lambda: f.read(1 << 24), b''):
            h.update(block)
    man = dict(format=1, title=title, built_from_exe='1.0.48.0',
               graph_type_hash='%016X' % struct.unpack_from('<Q', va, 0)[0],   # hex: PowerShell 5.1's JSON reads big numbers as doubles
               archive=dict(file='karin.core.stream', size=os.path.getsize(arc), sha256=h.hexdigest().upper()),
               groups=groups)
    json.dump(man, open(os.path.join(dst, 'manifest.json'), 'w'), indent=1)
    print('%s: %d groups, %d spans, %d locators, %d link edits, archive %d bytes' % (
        title, len(groups), sum(len(x['spans']) for x in groups), sum(len(x['locators']) for x in groups),
        sum(len(x['link_edits']) for x in groups), man['archive']['size']))


if __name__ == '__main__':
    main()
