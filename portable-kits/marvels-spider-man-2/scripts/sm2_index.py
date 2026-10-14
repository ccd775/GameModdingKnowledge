"""Build name index: every dagstr string that hashes to a toc asset -> span/archive/offset/size/header."""
import argparse, json, re, sys, collections
from sm2_common import *

argparse.ArgumentParser(description=__doc__).parse_args()
toc = load_toc()
ids = toc.get_assets_section().ids
spans = toc.get_spans_section().entries
arch = toc.get_archives_section().archives
span_of = [0] * len(ids)
for si, s in enumerate(spans):
    for k in range(s.asset_index, s.asset_index + s.count):
        span_of[k] = si
pos = collections.defaultdict(list)
for i, a in enumerate(ids):
    pos[a].append(i)
raw = open(os.path.join(game_dir(), 'dagstr'), 'rb').read()
names = set(m.decode('utf-8', 'replace') for m in re.findall(rb'[\x20-\x7e]{4,}', raw))
out = {}
for n in names:
    a = asset_id(n)
    if a in pos:
        recs = []
        for i in pos[a]:
            e = entry(toc, i)
            fn = arch[e.archive].filename.split(b'\0')[0].decode()
            recs.append({'span': span_of[i], 'archive': fn, 'offset': e.offset, 'size': e.size, 'has_header': e.header is not None})
        out[n] = {'id': f'{a:016X}', 'recs': recs}
print('names', len(names), 'resolved', len(out), 'toc assets', len(ids), 'archives', len(arch))
json.dump(out, open(INDEX, 'w', encoding='utf-8'), indent=0, sort_keys=True)
