"""Compares two collect.ps1 (or the older diagnose.ps1) reports (the build the mod was made from vs a player's build) to scope a port.

python diagcompare.py <reference zip> <other zip> [<manifest.json> ...]

Prints: type table changes; per-group fingerprint changes over the whole graph; for every detailed group whether its
data (decompressed span SHA-1), locators, subgroups and link records are the same, and how the link records differ
(only the subgroup numbering, or the targets themselves); for each manifest link edit, what the record at the same
place points to in the other build; and fingerprint matches for groups that are missing or changed.
Standard library only.
"""
import base64
import bisect
import collections
import json
import sys
import zipfile

FIELDS = ('NumObjects', 'GroupSize', 'SubGroupCount', 'RootCount', 'SpanCount', 'TypeCount', 'LinkSize',
          'LocatorCount', 'UUIDs', 'types_sha1', 'links_sha1', 'subgroups_sha1')


def load(path):
    z = zipfile.ZipFile(path)
    rep = json.loads(z.read('report.json'))
    rows = z.read('groups.tsv').decode().splitlines()
    head = rows[0].split('\t')
    table = {}
    for r in rows[1:]:
        v = r.split('\t')
        table[int(v[0])] = dict(zip(head[1:], v[1:]))
    rep['table'] = table
    rep['types'] = z.read('types.txt').decode().split()
    rep['detail'] = {d['gid']: d for d in rep['groups']}
    return rep


def records(d):
    """Decoded link records of a detailed group: (start, end, grp or None, idx) (Graph.links)."""
    buf = base64.b64decode(d['links_b64'])
    pos, out = 0, []

    def varint(initial):
        nonlocal pos
        temp, value = initial, initial & 0x7F
        while temp & 0x80:
            temp = buf[pos]
            pos += 1
            value = (value << 7) | (temp & 0x7F)
        return value
    while pos < len(buf):
        start = pos
        first = buf[pos]
        pos += 1
        if first & 0x40:
            grp = varint(first & 0xBF)
            b = buf[pos]
            pos += 1
            out.append((start, None, grp, varint(b)))
        else:
            out.append((start, None, None, varint(first & 0xBF)))
        out[-1] = (start, pos) + out[-1][2:]
    return out


def target(d, rec):
    """(group ID, object index) a record points to. A group field below the subgroup count is read as a subgroup
    index, anything else as a StreamingRef group ID (the record does not say which; this guess is right for large
    group IDs)."""
    grp, idx = rec[2], rec[3]
    if grp is None:
        return (d['gid'], idx)
    if grp < len(d['subgroups']):
        return (d['subgroups'][grp], idx)
    return ('sref', grp, idx)


def main():
    a, b = load(sys.argv[1]), load(sys.argv[2])
    edits = collections.defaultdict(list)
    for mp in sys.argv[3:]:
        for g in json.load(open(mp, encoding='utf-8'))['groups']:
            for e in g['link_edits']:
                if (e['rel'], e['old']) not in [(x['rel'], x['old']) for x in edits[g['gid']]]:
                    edits[g['gid']].append(e)
    print('reference: exe %s, %d groups, %d types, %d files, links %d' % (
        a['exe_version'], len(a['table']), len(a['types']), len(a['files']), a['link_table_size']))
    print('other:     exe %s (steam build %s), %d groups, %d types, %d files, links %d, graph type %s' % (
        b['exe_version'], b.get('steam_buildid'), len(b['table']), len(b['types']), len(b['files']),
        b['link_table_size'], 'same' if a['graph_type_hash'] == b['graph_type_hash'] else 'DIFFERENT'))
    ta, tb = set(a['types']), set(b['types'])
    print('types: %d removed, %d added; type table order %s' % (
        len(ta - tb), len(tb - ta), 'same' if a['types'][:len(b['types'])] == b['types'][:len(a['types'])] else 'changed'))
    fa, fb = set(a['files']), set(b['files'])
    print('files: %d removed, %d added: %s' % (len(fa - fb), len(fb - fa), sorted(fb - fa)[:20]))

    # ---- whole graph
    same = changed = 0
    why = collections.Counter()
    for gid, ra in a['table'].items():
        rb = b['table'].get(gid)
        if rb is None:
            continue
        diff = [f for f in FIELDS if ra[f] != rb[f]]
        if diff:
            changed += 1
            why[tuple(diff)] += 1
        else:
            same += 1
    gone = sorted(set(a['table']) - set(b['table']))
    new = sorted(set(b['table']) - set(a['table']))
    print('\ngroups: %d identical fingerprints, %d changed, %d only in reference, %d only in other' % (
        same, changed, len(gone), len(new)))
    for k, n in why.most_common(12):
        print('  %6d  %s' % (n, ', '.join(k)))

    def fp(r):
        return (r['NumObjects'], r['GroupSize'], r['TypeCount'], r['types_sha1'])
    by_fp = collections.defaultdict(list)
    for gid, r in b['table'].items():
        by_fp[fp(r)].append(gid)

    # ---- detailed groups
    print('\ndetailed groups (data = decompressed span SHA-1):')
    for gid in sorted(a['detail']):
        da, db = a['detail'][gid], b['detail'].get(gid)
        ra = a['table'][gid]
        if db is None:
            print('  %6d  MISSING in other; same-fingerprint groups there: %s' % (gid, by_fp.get(fp(ra), [])[:8]))
            continue
        out = []
        fd = [f for f in ('NumObjects', 'GroupSize', 'SubGroupCount', 'SpanCount', 'TypeCount', 'LinkSize',
                          'LocatorCount') if da[f] != db[f]]
        if fd:
            out.append('fields ' + ','.join('%s %s->%s' % (f, da[f], db[f]) for f in fd))
        if da['types_sha1'] != db['types_sha1']:
            ka, kb = collections.Counter(da['types']), collections.Counter(db['types'])
            out.append('types (%d kinds gone, %d new)' % (len(set(ka) - set(kb)), len(set(kb) - set(ka))))
        data_same = [x['sha1'] == y['sha1'] for x, y in zip(da['spans'], db['spans'])] if len(da['spans']) == len(db['spans']) else [False]
        out.append('data ' + ('SAME' if all(data_same) else 'differs'))
        if da['subgroups'] != db['subgroups']:
            sa, sb = set(da['subgroups']), set(db['subgroups'])
            out.append('subgroups (-%d +%d%s)' % (len(sa - sb), len(sb - sa), ', reordered' if sa == sb else ''))
        if da['locators'] != db['locators']:
            files_a = [a['files'][x[0]] for x in da['locators']]
            files_b = [b['files'][x[0]] for x in db['locators']]
            out.append('locators differ (files %s)' % ('same' if files_a == files_b else 'differ'))
        if da['links_sha1'] != db['links_sha1']:
            xa, xb = records(da), records(db)
            if len(xa) != len(xb):
                out.append('links: %d -> %d records' % (len(xa), len(xb)))
            else:
                raw = sum(1 for p, q in zip(xa, xb) if p[2:] != q[2:])
                sem = sum(1 for p, q in zip(xa, xb) if target(da, p) != target(db, q))
                out.append('links: %d/%d records differ raw, %d by target' % (raw, len(xa), sem))
        print('  %6d  %s' % (gid, '; '.join(out)))
        if fd and gid not in b['detail']:
            continue
        if gid in edits:
            xa, xb = records(da), records(db)

            def holding(xs, rel):        # an edit can start inside a record (only its later bytes changed)
                k = bisect.bisect_right([r[0] for r in xs], rel) - 1
                return xs[k] if k >= 0 and xs[k][0] <= rel < xs[k][1] else None
            for e in edits[gid]:
                ra_, rb_ = holding(xa, e['rel']), holding(xb, e['rel'])
                ta_ = target(da, ra_) if ra_ else None
                tb_ = target(db, rb_) if rb_ else None
                if ta_ != tb_ or (ra_ and rb_ and ra_[:2] != rb_[:2]):
                    print('          edit @%d: ref -> %s @%s, other -> %s @%s' % (
                        e['rel'], ta_, ra_ and ra_[0], tb_, rb_ and rb_[0]))
        if fd or da['types_sha1'] != db['types_sha1']:
            m = [g for g in by_fp.get(fp(ra), []) if g != gid]
            if m:
                print('          same fingerprint as the reference in other: %s' % m[:8])


if __name__ == '__main__':
    if sys.argv[1:2] in (['-h'], ['--help']) or len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(0 if sys.argv[1:2] in (['-h'], ['--help']) else 2)
    main()
