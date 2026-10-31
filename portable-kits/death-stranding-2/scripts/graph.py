"""Death Stranding 2 streaming graph reader (port of Odradek's StreamingGraphImpl)."""
import os
import struct
import sys

from ds2rtti import DSAR, Reader, TypeDB, TypeReader

HERE = os.path.dirname(os.path.abspath(__file__))
# Machine paths come from the environment: DS2_GAME_DIR is the game folder (DS2.exe), DS2_MODDING the modding
# workspace (clean\, work\, out\, backup\, tools\), DS2_TYPES_DIR the folder with Odradek's types_1048.json /
# extensions_1048.json (default: next to this script).
GAME_ROOT = os.environ.get('DS2_GAME_DIR', '')
# The game folder holds the installed (modded) graph after install.ps1; the clean root keeps the vanilla graph and
# hard links to the vanilla package files, so every analysis/patch reads vanilla data from there.
VANILLA_ROOT = os.path.join(os.environ['DS2_MODDING'], 'clean') if os.environ.get('DS2_MODDING') else ''
TYPES_DIR = os.environ.get('DS2_TYPES_DIR', HERE)


def _need(var, value, what):
    if not value:
        raise SystemExit('set %s (%s)' % (var, what))
    return value


def game_root():
    """The game folder; Graph() on it reads the clean root's vanilla graph when DS2_MODDING has one."""
    return _need('DS2_GAME_DIR', GAME_ROOT, 'the game folder with DS2.exe')


def clean_root():
    return _need('DS2_MODDING', VANILLA_ROOT, 'the modding workspace holding clean\\')


def modding_dir(*parts):
    return os.path.join(_need('DS2_MODDING', os.environ.get('DS2_MODDING', ''), 'the modding workspace'), *parts)


class Graph:
    def __init__(self, game_root, db=None, graph_path=None, overrides=None):
        if GAME_ROOT and os.path.normcase(game_root) == os.path.normcase(GAME_ROOT) and os.path.isdir(VANILLA_ROOT):
            game_root = VANILLA_ROOT
        self.root = game_root
        self.overrides = overrides or {}  # graph file index -> local path (e.g. a packed mod file)
        self.db = db or TypeDB(os.path.join(TYPES_DIR, 'types_1048.json'), os.path.join(TYPES_DIR, 'extensions_1048.json'))
        path = graph_path or os.path.join(game_root, 'LocalCacheWinGame', 'package', 'streaming_graph.core')
        with open(path, 'rb') as f:
            self.raw = f.read()
        self.res = TypeReader(self.db).read_object(Reader(self.raw))
        g = self.res
        self.files = g['Files']
        self.groups = g['Groups']
        self.group_by_id = {grp['GroupID']: i for i, grp in enumerate(self.groups)}
        self.type_table = self._type_table()
        self.spans = [(s['FileIndexAndIsPatch'] & 0x7FFFFFFF, s['Offset'], s['Length']) for s in g['SpanTable']]
        self.locators = [(l['Data'] & 0xFFFFFF, l['Data'] >> 24) for l in g['LocatorTable']]
        self._archives = {}
        self._links = None

    def _type_table(self):
        r = Reader(self.res['TypeTableData'])
        comp, stride, count, count2, unk = r.i32(), r.i32(), r.i32(), r.i32(), r.i32()
        assert comp == 0 and stride == 2 and count == count2 and unk == 1, (comp, stride, count, count2, unk)
        hashes = self.res['TypeHashes']
        out = []
        for _ in range(count):
            out.append(self.db.by_hash[hashes[r.u16()]])
        return out

    def archive(self, name):
        a = self._archives.get(name)
        if a is None:
            p = os.path.join(self.root, 'LocalCacheWinGame', name.split(':', 1)[1] if ':' in name else name)
            a = DSAR(p)
            self._archives[name] = a
        return a

    def read_file(self, file_index, offset, length):
        if file_index in self.overrides:
            a = self._archives.get(('override', file_index))
            if a is None:
                a = self._archives[('override', file_index)] = DSAR(self.overrides[file_index])
            return a.read(offset, length)
        return self.archive(self.files[file_index]).read(offset, length)

    @property
    def link_table(self):
        if self._links is None:
            self._links = self.read_file(self.res['LinkTableID'], 0, self.res['LinkTableSize'])
        return self._links

    def group_types(self, gi):
        grp = self.groups[gi]
        return self.type_table[grp['TypeStart']:grp['TypeStart'] + grp['TypeCount']]

    def group_roots(self, gi):
        grp = self.groups[gi]
        return self.res['RootIndices'][grp['RootStart']:grp['RootStart'] + grp['RootCount']]

    def group_spans(self, gi):
        grp = self.groups[gi]
        return self.spans[grp['SpanStart']:grp['SpanStart'] + grp['SpanCount']]

    def group_locators(self, gi):
        grp = self.groups[gi]
        return self.locators[grp['LocatorStart']:grp['LocatorStart'] + grp['LocatorCount']]

    def subgroups(self, gi):
        grp = self.groups[gi]
        ids = self.res['SubGroups'][grp['SubGroupStart']:grp['SubGroupStart'] + grp['SubGroupCount']]
        return [self.group_by_id[i] for i in ids]

    def links(self, gi, with_pos=False):
        """Yields (group_or_None, index) link records for a group (Odradek readLink);
        with_pos=True yields (group_or_None, index, start, end) byte positions in the link table."""
        buf = self.link_table
        pos = self.groups[gi]['LinkStart']

        def varint(initial):
            nonlocal pos
            temp = initial
            value = initial & 0x7F
            while temp & 0x80:
                temp = buf[pos]; pos += 1
                value = (value << 7) | (temp & 0x7F)
            return value

        while pos < len(buf):
            start = pos
            first = buf[pos]; pos += 1
            if first & 0x40:
                grp = varint(first & 0xBF)
                b = buf[pos]; pos += 1
                idx = varint(b)
            else:
                grp, idx = None, varint(first & 0xBF)
            yield (grp, idx, start, pos) if with_pos else (grp, idx)


def encode_link(grp, idx, length=None):
    """Inverse of Graph.links: grp is the subgroup index (None for the current group).
    length pads a shorter record with zero-valued leading varint groups (the decoder accepts them)."""
    if length is not None:
        enc = encode_link(grp, idx)
        pad = length - len(enc)
        if pad < 0:
            raise ValueError('record needs %d bytes, only %d available' % (len(enc), length))
        if pad == 0:
            return enc
        if grp is None:   # local form: leading 0x80 = continuation with zero value; the old first byte then reads
            return bytes([0x80] * pad) + enc   # as a 7-bit group, which is the same value because bit 6 is 0
        head_len = len(encode_link(grp, 0)) - 1   # bytes used by the group varint
        return enc[:head_len] + bytes([0x80] * pad) + enc[head_len:]
    def varint(v, first_bits):
        groups = []
        while True:
            groups.append(v & 0x7F)
            v >>= 7
            if not v:
                break
        groups.reverse()
        if groups[0] >= (1 << first_bits):   # first byte holds only first_bits value bits
            groups.insert(0, 0)
        return [g | 0x80 for g in groups[:-1]] + [groups[-1]]
    if grp is None:
        return bytes(varint(idx, 6))
    head = varint(grp, 6)
    head[0] |= 0x40
    return bytes(head + varint(idx, 7))


def main():
    import argparse
    ap = argparse.ArgumentParser(description='Summary of a streaming graph: files, groups, root types.')
    ap.add_argument('root', nargs='?', help='game folder (default DS2_GAME_DIR)')
    root = ap.parse_args().root or game_root()
    g = Graph(root)
    print('files', len(g.files), 'groups', len(g.groups), 'types', len(g.type_table),
          'spans', len(g.spans), 'locators', len(g.locators))
    for i, f in enumerate(g.files[:8]):
        print(' file', i, f)
    print(' ...', g.files[-3:])
    print('link table', g.res['LinkTableID'], g.files[g.res['LinkTableID']], g.res['LinkTableSize'])
    interesting = ('DSPlayerBodyVariant', 'BodyVariant', 'SkinnedModelResource', 'DSPlayerEntityResource')
    import collections
    hist = collections.Counter()
    for gi, grp in enumerate(g.groups):
        types = g.group_types(gi)
        roots = [types[r] for r in g.group_roots(gi)]
        for t in roots:
            hist[t] += 1
        if any(t in interesting for t in roots):
            print('group idx=%d (0x%x) id=%d objs=%d roots=%s' % (gi, gi, grp['GroupID'], grp['NumObjects'], roots[:6]))
    print('top root types:')
    for t, n in hist.most_common(40):
        print('  %6d %s' % (n, t))


if __name__ == '__main__':
    main()
