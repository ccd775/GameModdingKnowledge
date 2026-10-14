"""Query the asset index: sm2_find.py <regex> [--ext .model] [--group N]  (paths use '/' in the regex)."""
import argparse, collections, re
from sm2_common import load_index

ap = argparse.ArgumentParser()
ap.add_argument('pattern')
ap.add_argument('--ext', default=None)
ap.add_argument('--group', type=int, default=0, help='group by path component N and count')
ap.add_argument('--limit', type=int, default=200)
a = ap.parse_args()

idx = load_index()
rx = re.compile(a.pattern, re.I)
hits = []
for n, v in idx.items():
    p = n.replace(chr(92), '/')
    if a.ext and not p.endswith(a.ext):
        continue
    if rx.search(p):
        r = v['recs'][0]
        hits.append((p, v['id'], r['span'], r['archive'], r['size']))
hits.sort()
if a.group:
    g = collections.defaultdict(list)
    for h in hits:
        parts = h[0].split('/')
        g['/'.join(parts[:a.group])].append(h)
    for k in sorted(g):
        print(f'{len(g[k]):5d}  {k}')
else:
    for h in hits[:a.limit]:
        print(f'{h[1]}  s{h[2]:<3} {h[4]:>10}  {h[3]:<22} {h[0]}')
    print('total', len(hits))
