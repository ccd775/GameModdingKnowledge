"""Fingerprint every G1M vertex buffer in the Nioh 2 archives (MDLTEXPK / G1M_PACK / bare G1M).
usage: g1m_index.py <archive dir> <index.jsonl> <out.jsonl> [--from N]
out line: {a, e, model (pack item index), g1m_off, vb (index), stride, count, fp (sha1 of first 96 bytes), fpm (sha1 of middle 96 bytes)}"""
import hashlib
import json
import os
import struct
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import g1m_tool as gt  # noqa: E402
import ktpack  # noqa: E402
import n2lnk  # noqa: E402

KEEP = (b'MDLTEXPK', b'G1M_PACK')


def main(adir, idx, out, start=0):
    recs = [json.loads(l) for l in open(idx, encoding='utf-8')]
    recs = [r for r in recs if bytes.fromhex(r['magic'])[:8] in KEEP or bytes.fromhex(r['magic'])[:4] == b'_M1G']
    if "--zip-only" in sys.argv:
        recs = [r for r in recs if r["zip"]]
    handles = {}
    errs = 0
    with open(out, 'a', encoding='utf-8') as o:
        for n, r in enumerate(recs):
            if n < start:
                continue
            a = r['a']
            if a not in handles:
                handles[a] = open(n2lnk.arch_path(adir, a), 'rb')
            try:
                data = n2lnk.unpack(handles[a], r['off'], r['size'], r['zsize'], r['zip'])
                for mi, (mo, ms) in enumerate(ktpack.models(data)):
                    if data[mo:mo + 4] != b'_M1G':
                        continue
                    m = gt.parse(data, mo)
                    for vi, vb in enumerate(m.vertex_buffers):
                        off, st, cnt = vb['offset'], vb['stride'], vb['count']
                        blob = data[off:off + st * cnt]
                        mid = (cnt // 2) * st
                        o.write(json.dumps({'a': a, 'e': r['e'], 'model': mi, 'g1m_off': mo, 'vb': vi, 'stride': st, 'count': cnt,
                                            'fp': hashlib.sha1(blob[:96]).hexdigest()[:16],
                                            'fpm': hashlib.sha1(blob[mid:mid + 96]).hexdigest()[:16]}) + '\n')
            except Exception as ex:  # keep going, report
                errs += 1
                o.write(json.dumps({'a': a, 'e': r['e'], 'error': repr(ex)[:200]}) + '\n')
            if n % 200 == 0:
                print(n, len(recs), 'errors', errs, flush=True)
    print('done', len(recs), 'errors', errs)


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('adir', metavar='archive_dir'); ap.add_argument('idx', metavar='index.jsonl')
    ap.add_argument('out', metavar='out.jsonl', help='appended to')
    ap.add_argument('--from', dest='start', type=int, default=0, metavar='N', help='skip the first N model records (resume)')
    ap.add_argument('--zip-only', action='store_true', help='only compressed entries (main() reads it from sys.argv)')
    a = ap.parse_args()
    main(a.adir, a.idx, a.out, a.start)
