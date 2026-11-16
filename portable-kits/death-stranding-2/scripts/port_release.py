"""Ports a release variant (manifest.json + karin.core.stream, made by make_release.py from build 1.0.48) to another
game build whose groups hold the same data under other IDs (Steam 1.10.89 renumbered most groups and changed only
shader IDs, material texture-binding words and LOD distances inside them).

python port_release.py <old root> <old graph> <old links> <old report zip> <new root> <variant dir> <new version>

Writes <variant dir>/manifest_<new version>.json: the same archive plus `archive_patch` (byte runs the installer
writes into its copy of the archive), with
- groups renamed through mapgroups.build_map and their fingerprints taken from the new build;
- spans and locators at the same ordinals (the mapped groups have the same counts and span lengths);
- each replaced core 3-way merged (merge_span): bytes that changed between the two vanilla builds take the new value;
  such a byte that the mod also changed is a conflict and stops the port. The old vanilla core is read from the old
  build's files and must have the SHA-1 the old report holds (ds2_pc_mi's .core.pristine exports re-write a few
  bytes, so they are no substitute); a core whose new data has the old SHA-1 needs nothing;
- every link edit re-made on the record with the same ordinal in the new group's links: its vanilla target, mapped,
  must equal the new vanilla target; the mod's target is mapped (own group: same index; subgroup: its position in the
  new subgroup list; StreamingRef: the new group ID) and encoded into the new record's length.
"""
import bisect
import hashlib
import json
import os
import struct
import sys

from graph import encode_link
from mapgroups import build_map, group_records, load


def merge_span(v0, v1, m, base=0):
    """3-way byte merge of one core span: old vanilla v0, new vanilla v1, the mod's bytes m (built on v0).

    Returns (runs, changed, conflicts): runs = [[archive offset, bytearray]] of new-vanilla bytes to write over the
    mod's copy where the vanilla builds differ and the mod kept the old byte (base = the span's archive offset);
    changed = bytes that differ between v0 and v1; conflicts = those the mod changed too (left as the mod has them)."""
    if not (len(v0) == len(v1) == len(m)):
        raise ValueError('lengths old %d new %d mod %d' % (len(v0), len(v1), len(m)))
    runs, run, changed, conflicts = [], None, 0, 0
    for i in range(len(v1)):
        if v0[i] == v1[i]:
            run = None
            continue
        changed += 1
        if m[i] != v0[i]:
            conflicts += 1
            continue
        if run is not None and run[0] + len(run[1]) == base + i:
            run[1].append(v1[i])
        else:
            run = [base + i, bytearray([v1[i]])]
            runs.append(run)
    return runs, changed, conflicts


def decode(buf, pos):
    """One link record at `pos` (Graph.links): (grp or None, idx, end)."""
    def varint(initial):
        nonlocal pos
        temp, value = initial, initial & 0x7F
        while temp & 0x80:
            temp = buf[pos]
            pos += 1
            value = (value << 7) | (temp & 0x7F)
        return value
    first = buf[pos]
    pos += 1
    if first & 0x40:
        grp = varint(first & 0xBF)
        b = buf[pos]
        pos += 1
        return grp, varint(b), pos
    return None, varint(first & 0xBF), pos


def sref_flags(g, gi, upto):
    """Per link record of the group (in order, at least up to record `upto`): is its field a StreamingRef."""
    from ds2rtti import Reader
    from relink import TracingReader
    tr = TracingReader(g, gi)
    types = g.group_types(gi)
    index = 0
    for fi, off, ln in g.group_spans(gi):
        r = Reader(g.read_file(fi, off, ln))
        while r.remaining() > 0 and len(tr.trace) <= upto:
            tr.obj_index = index
            tr.read_compound(types[index], r)
            index += 1
        if len(tr.trace) > upto:
            break
    return [t[6] for t in tr.trace]


def type_sha1(g, gi):
    grp = g.groups[gi]
    idx = struct.unpack_from('<%dH' % grp['TypeCount'], g.res['TypeTableData'], 20 + 2 * grp['TypeStart'])
    return hashlib.sha1(b''.join(struct.pack('<Q', g.res['TypeHashes'][i]) for i in idx)).hexdigest()


def main():
    old_root, old_graph, old_links, old_report, new_root, vdir, version = sys.argv[1:8]
    man = json.load(open(os.path.join(vdir, 'manifest.json'), encoding='utf-8'))
    archive = open(os.path.join(vdir, man['archive']['file']), 'rb')
    ga, gb, known = load(old_root, old_graph, old_links, old_report, new_root)
    la, lb = ga.link_table, gb.link_table

    # groups to map: the manifest's, their subgroups, and every group ID a record touched by an edit could name
    want = set()
    for grp in man['groups']:
        gi = ga.group_by_id[grp['gid']]
        want |= {gi, *ga.subgroups(gi)}
        start = ga.groups[gi]['LinkStart']
        mod = bytearray(la[start:start + ga.groups[gi]['LinkSize']])
        for e in grp['link_edits']:
            mod[e['rel']:e['rel'] + len(e['new']) // 2] = bytes.fromhex(e['new'])
        for buf in (la[start:start + len(mod)], mod):
            pos = 0
            while pos < len(buf):
                g_, _, pos = decode(buf, pos)
                if g_ is not None and g_ in ga.group_by_id:
                    want.add(ga.group_by_id[g_])
    gmap, how, pending = build_map(ga, gb, sorted(want), known)
    gid_a = lambda gi: ga.groups[gi]['GroupID']       # noqa: E731
    gid_b = lambda gi: gb.groups[gi]['GroupID']       # noqa: E731
    idmap = {gid_a(a): gid_b(b) for a, b in gmap.items()}

    out_groups, patches, problems = [], [], []
    for grp in man['groups']:
        a = ga.group_by_id[grp['gid']]
        if a not in gmap:
            problems.append('group %d: no counterpart' % grp['gid'])
            continue
        b = gmap[a]
        ga_, gb_ = ga.groups[a], gb.groups[b]
        new = {'gid': gb_['GroupID']}
        check = {f: gb_[f] for f in ('NumObjects', 'GroupSize', 'SubGroupCount', 'SpanCount', 'TypeCount', 'LinkSize',
                                     'LocatorCount')}
        check['types_sha1'] = type_sha1(gb, b)
        if check['types_sha1'] != grp['check']['types_sha1']:
            problems.append('group %d: type list differs' % grp['gid'])
        check['subgroups'] = [gid_b(s) for s in gb.subgroups(b)]
        check['links_sha1'] = hashlib.sha1(lb[gb_['LinkStart']:gb_['LinkStart'] + gb_['LinkSize']]).hexdigest()
        new['check'] = check

        # spans: same ordinals; replaced cores merged with the vanilla change
        new['spans'] = []
        for s in grp['spans']:
            fi, off, ln = gb.group_spans(b)[s['k']]
            if ln != s['vanilla_length']:
                problems.append('group %d span %d: length %d -> %d' % (grp['gid'], s['k'], s['vanilla_length'], ln))
                continue
            v1 = gb.read_file(fi, off, ln)
            want_sha = known.get(grp['gid'], [None] * (s['k'] + 1))[s['k']]
            v0 = None
            if want_sha == hashlib.sha1(v1).hexdigest():
                v0 = v1                                 # unchanged between the vanilla builds
            if v0 is None:                              # the old build's own files (verified against the report)
                try:
                    fa, oa, lna = ga.group_spans(a)[s['k']]
                    x = ga.read_file(fa, oa, lna)
                    if want_sha in (None, hashlib.sha1(x).hexdigest()):
                        v0 = x
                except OSError:
                    pass
            if v0 is None:
                problems.append('group %d span %d: no old vanilla data to merge against' % (grp['gid'], s['k']))
                continue
            archive.seek(s['offset'])
            m = archive.read(s['length'])
            try:
                runs, n_changed, conflicts = merge_span(v0, v1, m, s['offset'])
            except ValueError as ex:
                problems.append('group %d span %d: %s' % (grp['gid'], s['k'], ex))
                continue
            patches += runs
            if conflicts:
                problems.append('group %d span %d: %d of %d vanilla-changed bytes were changed by the mod too' % (
                    grp['gid'], s['k'], conflicts, n_changed))
            print('group %d -> %d span %d: %d bytes changed between the vanilla builds' % (
                grp['gid'], gb_['GroupID'], s['k'], n_changed))
            new['spans'].append(dict(s, vanilla_length=ln))
        if ga_['LocatorCount'] != gb_['LocatorCount']:
            problems.append('group %d: locator count %d -> %d' % (grp['gid'], ga_['LocatorCount'], gb_['LocatorCount']))
        new['locators'] = grp['locators']

        # link edits, record by record
        ra, rb = group_records(ga, a), group_records(gb, b)
        if len(ra) != len(rb):
            problems.append('group %d: %d vs %d link records' % (grp['gid'], len(ra), len(rb)))
            continue
        subs_a = [gid_a(s) for s in ga.subgroups(a)]
        subs_b = check['subgroups']
        mod = bytearray(la)
        for e in grp['link_edits']:
            p = ga_['LinkStart'] + e['rel']
            mod[p:p + len(e['new']) // 2] = bytes.fromhex(e['new'])
        starts = [r[2] for r in ra]
        touched = sorted({bisect.bisect_right(starts, ga_['LinkStart'] + e['rel'] + j) - 1
                          for e in grp['link_edits'] for j in range(len(e['new']) // 2)})

        def meaning(grp_v, idx, subs, ids):
            """(kind, target group ID, index) candidates for a record."""
            if grp_v is None:
                return [('own', None, idx)]
            out = []
            if grp_v < len(subs):
                out.append(('sub', subs[grp_v], idx))
            if grp_v in ids:
                out.append(('sref', grp_v, idx))
            return out
        new['link_edits'] = []
        kinds_of = {}
        for n in touched:
            g0, i0, _, _ = ra[n]
            g1, i1, _, _ = rb[n]
            van_a = meaning(g0, i0, subs_a, ga.group_by_id)
            van_b = meaning(g1, i1, subs_b, gb.group_by_id)
            kinds_of[n] = [k for k in ('own', 'sub', 'sref')
                           if any(x[0] == k for x in van_a) and any(y[0] == k for y in van_b)
                           and any(y == (k, None if k == 'own' else idmap.get(x[1]), x[2])
                                   for x in van_a if x[0] == k for y in van_b if y[0] == k)]
            if not kinds_of[n]:
                problems.append('group %d record %d: vanilla targets %s / %s do not line up' % (grp['gid'], n, van_a,
                                                                                               van_b))
        # a small group value reads as a subgroup position and as a StreamingRef group ID alike: the field's type
        # (the new group's objects parsed up to that record) settles it
        unsure = [n for n in touched if len(kinds_of[n]) > 1]
        if unsure:
            flags = sref_flags(gb, b, max(unsure))
            for n in unsure:
                kinds_of[n] = ['sref' if flags[n] else 'sub'] if ('sref' if flags[n] else 'sub') in kinds_of[n] else []
                if not kinds_of[n]:
                    problems.append('group %d record %d: field type does not fit its vanilla target' % (grp['gid'], n))
        for n in touched:
            if len(kinds_of[n]) != 1:
                continue
            g0, i0, s0, e0 = ra[n]
            g1, i1, s1, e1 = rb[n]
            kind = kinds_of[n][0]
            gm, im, end = decode(mod, s0)
            assert end == e0, (grp['gid'], n, end, e0)
            # the mod's target: a Ref field (vanilla 'own' or 'sub') may now point into the own group or a subgroup
            if kind != 'sref' and gm is None:
                enc_grp, tgt = None, (gb_['GroupID'], im)
            elif kind != 'sref':
                old_t = subs_a[gm] if gm < len(subs_a) else None
                new_t = idmap.get(old_t)
                if new_t not in subs_b:
                    problems.append('group %d record %d: subgroup target %s -> %s not a subgroup' % (grp['gid'], n, old_t,
                                                                                                  new_t))
                    continue
                enc_grp, tgt = subs_b.index(new_t), (new_t, im)
            else:
                new_t = idmap.get(gm)
                if new_t is None:
                    problems.append('group %d record %d: StreamingRef target %s unmapped' % (grp['gid'], n, gm))
                    continue
                enc_grp, tgt = new_t, (new_t, im)
            try:
                nb = encode_link(enc_grp, im, length=e1 - s1)
            except ValueError as ex:
                problems.append('group %d record %d: %s' % (grp['gid'], n, ex))
                continue
            new['link_edits'].append(dict(rel=s1 - gb_['LinkStart'], old=lb[s1:e1].hex(), new=nb.hex()))
            print('  %d #%d %s %s:%d -> %s' % (grp['gid'], n, kind, gm if kind != 'own' else 'own', im, tgt))
        out_groups.append(new)

    if pending:
        print('unmapped groups (ok unless named above):', [gid_a(x) for x in pending][:20])
    if problems:
        print('PROBLEMS:')
        for p in problems:
            print('  ' + p)
        raise SystemExit(1)
    h = hashlib.sha256()                    # SHA-256 of the archive after the patch (the installer checks its copy)
    archive.seek(0)
    pos = 0
    pending_p = sorted((o, bytes(b)) for o, b in patches)
    while True:
        block = bytearray(archive.read(1 << 24))
        if not block:
            break
        for o, b in pending_p:
            lo, hi = max(o, pos), min(o + len(b), pos + len(block))
            if lo < hi:
                block[lo - pos:hi - pos] = b[lo - o:hi - o]
        h.update(block)
        pos += len(block)
    man2 = dict(man, built_from_exe=version, ported_from=man['built_from_exe'], groups=out_groups,
                archive_patch=[dict(offset=o, hex=bytes(b).hex()) for o, b in patches],
                patched_sha256=h.hexdigest().upper())
    man2['graph_type_hash'] = '%016X' % struct.unpack_from('<Q', gb.raw, 0)[0]
    path = os.path.join(vdir, 'manifest_%s.json' % version)
    json.dump(man2, open(path, 'w'), indent=1)
    print('%s: %d groups, %d spans, %d locators, %d link edits, %d archive patch runs (%d bytes) -> %s' % (
        man['title'], len(out_groups), sum(len(g['spans']) for g in out_groups),
        sum(len(g['locators']) for g in out_groups), sum(len(g['link_edits']) for g in out_groups), len(patches),
        sum(len(b) for _, b in patches), path))


if __name__ == '__main__':
    if sys.argv[1:2] in (['-h'], ['--help']) or len(sys.argv) < 8:
        print(__doc__)
        raise SystemExit(0 if sys.argv[1:2] in (['-h'], ['--help']) else 2)
    main()
