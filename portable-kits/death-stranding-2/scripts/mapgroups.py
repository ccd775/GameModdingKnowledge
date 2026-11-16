"""Maps the groups the mod uses from one game build to another (1.0.48 -> Steam 1.10.89 renumbered most groups) and
checks that the mapped groups hold the same data.

python mapgroups.py <old root> <old graph> <old links> <old report zip> <new root> <out json> <manifest.json> [...]

The old build's package files may be gone (the 1.0.48 copy was deleted on 2026-11-15): its object data is compared
through the per-span SHA-1s in its collect.ps1 / diagnose.ps1 report (<old report zip>), and read from its files only
where they still exist.

Mapping (build_map): a group's key is (NumObjects, GroupSize, TypeCount, its type hashes, its root object UUIDs);
without a match the key without the root UUIDs is tried (6744's roots changed). Unique keys map directly; a key shared
by several groups (tiny variant groups) is settled by the decompressed object data, then by the subgroups already
mapped, then by the ID shift of nearby mapped groups. Checked for the manifests' groups: same objects (decompressed
span SHA-1s), locator counts, subgroups mapped in the same order, and the group's own link records (bounded by
LinkSize) equal or differing only in StreamingRef group IDs that map. Data that differs (recompiled shaders etc.) is
reported, not fixed: port_release.py merges it.
Writes {"map": {old: new}, "checks": {...}}.
"""
import collections
import hashlib
import json
import os
import struct
import sys
import zipfile

from graph import Graph


def keys(g):
    r = g.res
    ttd = r['TypeTableData']
    out = {}
    for gi, grp in enumerate(g.groups):
        idx = struct.unpack_from('<%dH' % grp['TypeCount'], ttd, 20 + 2 * grp['TypeStart'])
        th = hashlib.sha1(b''.join(struct.pack('<Q', r['TypeHashes'][i]) for i in idx)).hexdigest()[:16]
        roots = r['RootUUIDs'][grp['RootStart']:grp['RootStart'] + grp['RootCount']]
        rk = hashlib.sha1(repr(roots).encode()).hexdigest()[:16] if roots else ''
        out[gi] = (grp['NumObjects'], grp['GroupSize'], grp['TypeCount'], th, rk)
    return out


def core_hash(g, gi, known=None):
    """Per-span SHA-1s of a group's decompressed objects (a tuple), from `known` (a report) or read; None if the
    files are gone."""
    gid = g.groups[gi]['GroupID']
    if known and gid in known:
        return known[gid]
    try:
        return tuple(hashlib.sha1(g.read_file(fi, off, ln)).hexdigest() for fi, off, ln in g.group_spans(gi))
    except OSError:
        return None


def group_records(g, gi):
    """The group's own link records (Graph.links runs on to the end of the table): (grp or None, idx, start, end)."""
    end = g.groups[gi]['LinkStart'] + g.groups[gi]['LinkSize']
    out = []
    for rec in g.links(gi, with_pos=True):
        if rec[2] >= end:
            break
        out.append(rec)
    return out


def load(old_root, old_graph, old_links, old_report, new_root):
    known = {d['gid']: tuple(sp['sha1'] for sp in d['spans'])
             for d in json.loads(zipfile.ZipFile(old_report).read('report.json'))['groups']}
    ga = Graph(old_root, graph_path=old_graph)
    ga._links = open(old_links, 'rb').read()
    # a game with the mod installed: its vanilla graph and links are in the installer's backup
    bak = os.path.join(new_root, 'KarinMod_backup')
    if os.path.isfile(os.path.join(bak, 'streaming_graph.core')):
        gb = Graph(new_root, graph_path=os.path.join(bak, 'streaming_graph.core'))
        gb._links = open(os.path.join(bak, 'streaming_links.stream'), 'rb').read()
    else:
        gb = Graph(new_root)
    return ga, gb, known


def build_map(ga, gb, want, known):
    """{old group index: new group index} for the group indices in `want`, and how each was matched."""
    ka, kb = keys(ga), keys(gb)
    by_key, by_key2 = collections.defaultdict(list), collections.defaultdict(list)
    for gi, k in kb.items():
        by_key[k].append(gi)
        by_key2[k[:4]].append(gi)        # without the root UUIDs (a group's roots can change: 6744)

    def cands(gi):
        return by_key.get(ka[gi]) or by_key2.get(ka[gi][:4], [])
    gmap, how = {}, {}
    for gi in want:
        c = by_key.get(ka[gi], [])
        if len(c) == 1:
            gmap[gi], how[gi] = c[0], 'unique key'
    pending = [gi for gi in want if gi not in gmap]
    for _ in range(3):
        for gi in list(pending):
            c = list(cands(gi))
            if not c:
                continue
            ch = core_hash(ga, gi, known)
            if ch is not None:
                c = [x for x in c if core_hash(gb, x) == ch]
            subs = [gmap.get(s) for s in ga.subgroups(gi)]
            if None not in subs:
                c2 = [x for x in c if gb.subgroups(x) == subs]
                if c2:
                    c = c2
            if len(c) > 1:      # still several identical groups: the one whose ID moved least like its neighbours'
                shift = collections.Counter(gb.groups[gmap[x]]['GroupID'] - ga.groups[x]['GroupID'] for x in gmap
                                            if abs(ga.groups[x]['GroupID'] - ga.groups[gi]['GroupID']) < 200)
                d = shift.most_common(1)[0][0] if shift else 0
                c.sort(key=lambda x: abs(gb.groups[x]['GroupID'] - ga.groups[gi]['GroupID'] - d))
                how[gi] = 'nearest of %d identical' % len(c)
            if c:
                gmap[gi] = c[0]
                how.setdefault(gi, 'core data' if by_key.get(ka[gi]) else 'key without roots')
                pending.remove(gi)
    return gmap, how, pending


def main():
    old_root, old_graph, old_links, old_report, new_root, out = sys.argv[1:7]
    manifests = [json.load(open(p, encoding='utf-8')) for p in sys.argv[7:]]
    ga, gb, known = load(old_root, old_graph, old_links, old_report, new_root)
    # groups to map: the manifests' groups and their subgroups (StreamingRef records name groups by ID; port_release
    # maps the ones its edits use)
    want = []
    for m in manifests:
        for grp in m['groups']:
            gi = ga.group_by_id[grp['gid']]
            want += [gi] + ga.subgroups(gi)
    want = sorted(set(want))
    gmap, how, pending = build_map(ga, gb, want, known)
    idmap = {ga.groups[a]['GroupID']: gb.groups[b]['GroupID'] for a, b in gmap.items()}
    print('mapped %d of %d groups (%s); unmapped: %s' % (
        len(gmap), len(want), dict(collections.Counter(how.values())), [ga.groups[x]['GroupID'] for x in pending][:30]))

    # checks for the manifests' groups
    checks = {}
    for m in manifests:
        for grp in m['groups']:
            gid = grp['gid']
            if gid in checks:
                continue
            a = ga.group_by_id[gid]
            b = gmap.get(a)
            if b is None:
                checks[gid] = {'new': None}
                print('  %6d -> UNMAPPED' % gid)
                continue
            c = {'new': gb.groups[b]['GroupID'], 'how': how[a]}
            ca = core_hash(ga, a, known)
            c['core_same'] = None if ca is None else ca == core_hash(gb, b)
            c['locators'] = '%d vs %d' % (len(ga.group_locators(a)), len(gb.group_locators(b)))
            subs = [idmap.get(ga.groups[s]['GroupID']) for s in ga.subgroups(a)]
            c['subgroups_in_order'] = subs == [gb.groups[s]['GroupID'] for s in gb.subgroups(b)]
            la = [r[:2] for r in group_records(ga, a)]
            lb = [r[:2] for r in group_records(gb, b)]
            if len(la) != len(lb):
                c['links'] = '%d vs %d records' % (len(la), len(lb))
            else:
                raw = sum(1 for x, y in zip(la, lb) if x != y)
                sref_ok = sum(1 for x, y in zip(la, lb) if x != y and x[0] is not None and y[0] is not None
                              and idmap.get(x[0]) == y[0] and x[1] == y[1])
                c['links'] = '%d records, %d differ, %d of those = old StreamingRef ID mapped' % (len(la), raw, sref_ok)
                c['links_unexplained'] = raw - sref_ok
            checks[gid] = c
            print('  %6d -> %6d  %-22s core %-5s locators %-13s subgroups %-5s links %s' % (
                gid, c['new'], c['how'], c['core_same'], c['locators'], c['subgroups_in_order'], c['links']))
    json.dump({'map': {str(k): v for k, v in sorted(idmap.items())}, 'checks': {str(k): v for k, v in checks.items()}},
              open(out, 'w'), indent=1)
    print('written', out)


if __name__ == '__main__':
    if sys.argv[1:2] in (['-h'], ['--help']) or len(sys.argv) < 8:
        print(__doc__)
        raise SystemExit(0 if sys.argv[1:2] in (['-h'], ['--help']) else 2)
    main()
