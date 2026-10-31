r"""Find which streaming groups contain a byte pattern (e.g. texture source names) by scanning every core archive.

python scan_strings.py <regex bytes>   e.g.  python scan_strings.py "sam_[a-z0-9_]+\.psd"
Prints each distinct match with the groups whose spans contain it.
"""
import argparse
import bisect
import collections
import re
import sys

from graph import Graph, game_root

BLOCK = 64 << 20


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('pattern', help='regular expression over the raw bytes')
    pat = re.compile(ap.parse_args().pattern.encode())
    g = Graph(game_root())
    spans_by_file = collections.defaultdict(list)   # file index -> sorted [(offset, end, group id)]
    for gi, grp in enumerate(g.groups):
        for fi, off, length in g.group_spans(gi):
            spans_by_file[fi].append((off, off + length, grp['GroupID']))
    hits = collections.defaultdict(set)
    for fi in sorted(spans_by_file):
        name = g.files[fi]
        if not name.endswith('.core'):
            continue
        spans = sorted(spans_by_file[fi])
        starts = [s[0] for s in spans]
        a = g.archive(name)
        pos = 0
        while pos < a.size:
            n = min(BLOCK + 256, a.size - pos)
            buf = a.read(pos, n)
            for m in pat.finditer(buf):
                if m.start() >= BLOCK:
                    continue
                at = pos + m.start()
                k = bisect.bisect_right(starts, at) - 1
                if k >= 0 and spans[k][0] <= at < spans[k][1]:
                    hits[m.group().decode('latin-1')].add(spans[k][2])
            pos += BLOCK
            a._cache.clear()
        print('scanned', name, len(hits), file=sys.stderr, flush=True)
    for s in sorted(hits):
        print(s, sorted(hits[s]))


if __name__ == '__main__':
    main()
