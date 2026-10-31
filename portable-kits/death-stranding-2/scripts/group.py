"""Reads all objects of a streaming group (port of Odradek's StreamingObjectReader.readSingleGroup).

Pointers resolve through the graph's link table; StreamingDataSource compounds take the next locator.
Each object gets `__span__` (span index), `__off__`/`__end__` (byte range inside the span data).
"""
from ds2rtti import EXTRA, Obj, Reader, TypeReader
from graph import Graph, game_root


class GroupReader(TypeReader):
    def __init__(self, g: Graph, gi: int):
        super().__init__(g.db, pointer_hook=self._pointer, extra=EXTRA)
        self.g = g
        self.gi = gi
        self.links = g.links(gi)
        self.locators = iter(g.group_locators(gi))
        self.subgroups = g.subgroups(gi)

    def _pointer(self, tname, t, r):
        grp, idx = next(self.links)
        ptype = t['type']
        if ptype == 'StreamingRef':
            return ('StreamingRef', grp, idx)  # grp is a group ID here (or None)
        if grp is None:
            return (ptype, self.g.groups[self.gi]['GroupID'], idx)
        return (ptype, self.g.groups[self.subgroups[grp]]['GroupID'], idx)

    def read_compound(self, tname, r):
        obj = super().read_compound(tname, r)
        if tname == 'StreamingDataSource' and obj['Channel'] != 0xFF and obj['Length'] > 0:
            fi, off = next(self.locators)
            obj['Locator'] = (fi, off)
        return obj


def read_group(g: Graph, gid: int):
    gi = g.group_by_id[gid]
    types = g.group_types(gi)
    reader = GroupReader(g, gi)
    objects = []
    index = 0
    for si, (fi, off, length) in enumerate(g.group_spans(gi)):
        data = g.read_file(fi, off, length)
        r = Reader(data)
        while r.remaining() > 0:
            tname = types[index]
            start = r.pos
            obj = reader.read_compound(tname, r)
            obj['__span__'] = si
            obj['__off__'] = start
            obj['__end__'] = r.pos
            objects.append(obj)
            index += 1
    assert index == len(types), (index, len(types))
    return objects


def ref_index(ptr, gid):
    """Object index of a pointer tuple if it points into group `gid`, else None."""
    if ptr is None or not isinstance(ptr, tuple) or len(ptr) != 3:
        return None
    return ptr[2] if ptr[1] == gid else None


if __name__ == '__main__':
    import collections
    import sys
    import argparse
    ap = argparse.ArgumentParser(description='Read every object of a streaming group: python group.py <gid>')
    ap.add_argument('gid', type=int)
    gid = ap.parse_args().gid
    g = Graph(game_root())
    objs = read_group(g, gid)
    print('read', len(objs), 'objects')
    print(collections.Counter(o['__type__'] for o in objs).most_common())
