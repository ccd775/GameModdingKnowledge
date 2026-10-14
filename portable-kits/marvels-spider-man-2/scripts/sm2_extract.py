"""Extract assets by path (as in the index) into Work/native/<path>. Usage: sm2_extract.py <path|regex> [--regex] [--span N]"""
import argparse, os, re
from sm2_common import load_toc, load_index, extract, NATIVE, find_entry

ap = argparse.ArgumentParser()
ap.add_argument('items', nargs='+')
ap.add_argument('--regex', action='store_true')
ap.add_argument('--span', type=int, default=None)
ap.add_argument('--out', default=NATIVE)
a = ap.parse_args()

idx = load_index()
paths = []
for it in a.items:
    if a.regex:
        rx = re.compile(it, re.I)
        paths += [n for n in idx if rx.search(n.replace(chr(92), '/'))]
    else:
        paths.append(it.replace('/', chr(92)).lower())
toc = load_toc()
for p in sorted(set(paths)):
    v = idx.get(p)
    if not v:
        print('MISSING', p)
        continue
    for r in v['recs']:
        if a.span is not None and r['span'] != a.span:
            continue
        data, e = extract(toc, int(v['id'], 16), r['span'])
        rel = p.replace(chr(92), '/')
        if r['span'] != 0:
            rel = f'span{r["span"]}/' + rel
        dst = os.path.join(a.out, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, 'wb') as f:
            f.write(data)
        hl = len(e.header) if e.header else 0
        print(f'{len(data):>10}  hdr={hl:<4} s{r["span"]:<3} {rel}')
