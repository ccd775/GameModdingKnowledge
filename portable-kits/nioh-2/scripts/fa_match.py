"""Match frame-analysis vertex buffers to archive G1M vertex buffers by fingerprint.
usage: fa_match.py <FrameAnalysis dir> <fa.json> <g1m_vb.jsonl> [draw ids...]"""
import hashlib
import json
import os
import sys
from collections import defaultdict


def main(fadir, fajson, vbidx, only=None):
    idx = defaultdict(list)
    for line in open(vbidx, encoding='utf-8'):
        r = json.loads(line)
        if 'fp' in r:
            idx[(r['stride'], r['fp'])].append(r)
    draws = json.load(open(fajson))
    seen = set()
    for d in draws:
        if only and d['draw'] not in only:
            continue
        for k in ('vb0', 'vb1', 'vb2'):
            if k not in d or 'buf' not in d[k] or 'hdr' not in d[k]:
                continue
            h = d[k]['hash']
            if h in seen:
                continue
            seen.add(h)
            st = int(d[k]['hdr']['stride'])
            blob = open(os.path.join(fadir, d[k]['buf']), 'rb').read()
            fp = hashlib.sha1(blob[:96]).hexdigest()[:16]
            hits = idx.get((st, fp), [])
            n = len(blob) // st
            if hits:
                print(d['draw'], k, h, 'stride', st, 'n', n, '->', [(x['a'], x['e'], x['model'], x['vb'], x['count']) for x in hits[:4]])
            elif only:
                print(d['draw'], k, h, 'stride', st, 'n', n, 'NO MATCH')


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('fadir', metavar='FrameAnalysis_dir'); ap.add_argument('fajson', metavar='fa.json')
    ap.add_argument('vbidx', metavar='g1m_vb.jsonl'); ap.add_argument('draws', nargs='*', type=int, metavar='draw')
    a = ap.parse_args()
    only = set(a.draws) or None
    main(a.fadir, a.fajson, a.vbidx, only)
