"""Re-point pointers of vanilla objects by editing their link records in streaming_links.stream (in place,
same byte length; shorter records are padded with zero-valued varint groups).

python relink.py <out streaming_links.stream> <gid>:<idx> <field> <target gid>:<target idx> [<gid>:<idx> <field> <target> ...]
<field> is an attribute path (Field#n picks the n-th link of a list field) or @<gid>:<idx>: every link of the object
that points there (a material's texture bindings across all its techniques).
Ref targets must be in the same group or one of its subgroups; StreamingRef targets can be any group (the record
holds the group ID). Always starts from the vanilla link table.
"""
import argparse
import shutil
import sys

from ds2rtti import Reader
from graph import Graph, encode_link, game_root
from group import GroupReader


class TracingReader(GroupReader):
    def __init__(self, g, gi):
        super().__init__(g, gi)
        self.links = g.links(gi, with_pos=True)
        self.trace = []          # (object index, attribute path, grp, idx, start, end, is StreamingRef)
        self.obj_index = -1
        self.path = []

    def _pointer(self, tname, t, r):
        grp, idx, start, end = next(self.links)
        self.trace.append((self.obj_index, '.'.join(self.path), grp, idx, start, end, t['type'] == 'StreamingRef'))
        if t['type'] == 'StreamingRef':
            return ('StreamingRef', grp, idx)
        if grp is None:
            return (t['type'], self.g.groups[self.gi]['GroupID'], idx)
        return (t['type'], self.g.groups[self.subgroups[grp]]['GroupID'], idx)

    def read_compound(self, tname, r):
        obj = {'__type__': tname}
        for name, atype in self.db.plan(tname):
            self.path.append(name)
            obj[name] = self.read(atype, r)
            self.path.pop()
        cb = self._extra_for(tname)
        if cb is not None:
            cb(self, r, obj)
        if tname == 'StreamingDataSource' and obj['Channel'] != 0xFF and obj['Length'] > 0:
            next(self.locators)
        return obj


def trace_group(g, gid, last=None):
    """Traces objects up to index `last` (all when None), so groups whose later objects carry unparsed extra data
    still work."""
    gi = g.group_by_id[gid]
    types = g.group_types(gi)
    tr = TracingReader(g, gi)
    index = 0
    for fi, off, length in g.group_spans(gi):
        r = Reader(g.read_file(fi, off, length))
        while r.remaining() > 0 and (last is None or index <= last):
            tr.obj_index = index
            tr.read_compound(types[index], r)
            index += 1
    return tr


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out'); ap.add_argument('edits', nargs='*', metavar='<gid>:<idx> <field> <target>')
    a = ap.parse_args()
    out, args = a.out, a.edits
    if len(args) % 3:
        ap.error('edits come in triples: <gid>:<idx> <field> <target gid>:<target idx>')
    edits = [args[i:i + 3] for i in range(0, len(args), 3)]
    last = {}
    for src, _, _ in edits:
        gid, oi = map(int, src.split(':'))
        last[gid] = max(last.get(gid, 0), oi)
    g = Graph(game_root())
    links_path = g.archive(g.files[g.res['LinkTableID']]).f.name
    shutil.copyfile(links_path, out)
    traces = {}
    with open(out, 'r+b') as f:
        for src, field, dst in edits:
            gid, oi = map(int, src.split(':'))
            tgid, tidx = map(int, dst.split(':'))
            if gid not in traces:
                traces[gid] = trace_group(g, gid, last[gid])
            tr = traces[gid]
            sub_ids = [g.groups[s]['GroupID'] for s in tr.subgroups]

            def target(t):
                return (t[2] if t[6] else gid if t[2] is None else sub_ids[t[2]], t[3])
            if field.startswith('@'):
                want = tuple(map(int, field[1:].split(':')))
                recs = [t for t in tr.trace if t[0] == oi and target(t) == want]
                if not recs:
                    raise SystemExit('no link of %s points to %s' % (src, field[1:]))
            else:
                field, _, nth = field.partition('#')   # Field#n picks the n-th link of a list field
                recs = [t for t in tr.trace if t[0] == oi and t[1] == field]
                if nth:
                    recs = recs[int(nth):int(nth) + 1]
                if len(recs) != 1:
                    raise SystemExit('expected one link for %s.%s, found %s' % (src, field, recs))
            for rec in recs:
                _, path, grp, idx, start, end, sref = rec
                old_target = target(rec)
                if sref:
                    new = encode_link(tgid, tidx, length=end - start)
                elif tgid == gid:
                    new = encode_link(None, tidx, length=end - start)
                elif tgid in sub_ids:
                    new = encode_link(sub_ids.index(tgid), tidx, length=end - start)
                else:
                    raise SystemExit('target group %d is not %d or one of its subgroups' % (tgid, gid))
                old = g.link_table[start:end]
                f.seek(start)
                f.write(new)
                print('%s.%s @%d: %s (%d:%d) -> %s (%d:%d)' % (src, path, start, old.hex(), *old_target, new.hex(),
                                                              tgid, tidx))
    print('written', out)


if __name__ == '__main__':
    main()
