"""Checks a tool root rebuilt from a collect.ps1 zip (sparse_root.py) against a complete root of the same build.

python dry_verify.py <rebuilt root> <complete root>

For every collected group: its objects (all spans) read the same through ds2py from both roots, and for the groups
taken in full every stream (locator up to the next locator or span start in that file) does too. Reading data the
zip left out fails (empty chunk), so a pass means the zip holds all of it.
"""
import bisect
import collections
import json
import os
import sys

from graph import Graph


def main():
    rebuilt, complete = sys.argv[1:3]
    meta = json.load(open(os.path.join(rebuilt, 'collect.json'), encoding='utf-8'))
    gr = Graph(rebuilt)
    gc = Graph(complete, graph_path=os.path.join(complete, 'LocalCacheWinGame', 'package', 'streaming_graph.core.org'))
    assert gr.raw == gc.raw, 'graphs differ'
    bounds = collections.defaultdict(set)
    for fi, off in gr.locators:
        bounds[fi].add(off)
    for fi, off, _ in gr.spans:
        bounds[fi].add(off)
    bounds = {fi: sorted(v) for fi, v in bounds.items()}
    absent = set(meta['missing_files'])
    bad, nbytes, counts = [], 0, collections.Counter()
    for gid in meta['full'] + meta['core_only']:
        gi = gr.group_by_id[gid]
        reads = [(fi, off, ln) for fi, off, ln in gr.group_spans(gi)]
        if gid in meta['full']:
            for fi, off in gr.group_locators(gi):
                v = bounds[fi]
                k = bisect.bisect_right(v, off)
                end = v[k] if k < len(v) else gc.archive(gc.files[fi]).size
                reads.append((fi, off, end - off))
        for fi, off, ln in reads:
            if gc.files[fi].split(':', 1)[1] in absent:
                counts['skipped (file not on disk)'] += 1
                continue
            try:
                a = gr.read_file(fi, off, ln)
            except Exception as e:      # noqa: BLE001 - any read failure is a miss
                bad.append((gid, gr.files[fi], off, ln, repr(e)[:80]))
                continue
            if a != gc.read_file(fi, off, ln):
                bad.append((gid, gr.files[fi], off, ln, 'content differs'))
            nbytes += ln
            counts['reads'] += 1
    print('groups %d full + %d object-only, %s, %.1f MB compared, %d failures' % (
        len(meta['full']), len(meta['core_only']), dict(counts), nbytes / 1e6, len(bad)))
    for b in bad[:20]:
        print('  FAIL', b)


if __name__ == '__main__':
    if sys.argv[1:2] in (['-h'], ['--help']) or len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(0 if sys.argv[1:2] in (['-h'], ['--help']) else 2)
    main()
