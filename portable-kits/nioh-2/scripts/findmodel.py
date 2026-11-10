"""Find the archive G1M behind dumped draws: candidates by vertex count, confirmed by decoded positions.
usage: findmodel.py <FrameAnalysis dir> <fa.json> <g1m_vb.jsonl> <out.json> draw [draw ...]"""
import json
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import g1m_tool as gt  # noqa: E402
import ktpack  # noqa: E402
import n2lnk  # noqa: E402
from fa_mesh import load_draw  # noqa: E402

ADIR = None    # <game dir>/archive: --game-dir or N2_GAME_DIR, needed when an entry is not in the cache
CACHE = None   # --cache: folder of decompressed entries kept between runs (no cache by default)


def entry(a, e, tabs={}):
    p = os.path.join(CACHE, f'{a:02d}_{e:05d}.bin') if CACHE else None
    if p and os.path.exists(p):
        return open(p, 'rb').read()
    if ADIR is None:
        raise SystemExit('N2_GAME_DIR is not set: point it at the Nioh 2 folder (archive/ inside) or pass --game-dir')
    if a not in tabs:
        tabs[a] = n2lnk.table(n2lnk.arch_path(ADIR, a))[0]
    off, size, zs, z = tabs[a][e]
    data = n2lnk.unpack(open(n2lnk.arch_path(ADIR, a), 'rb'), off, size, zs, z)
    if p:
        os.makedirs(CACHE, exist_ok=True)
        open(p, 'wb').write(data)
    return data


def g1m_positions(m, vbi):
    for att in m.attributes:
        for x in att['attrs']:
            if x['semantic'] == 'POSITION' and x['layer'] == 0 and att['buffers'][x['buffer']] == vbi:
                vb = m.vertex_buffers[vbi]
                raw = np.frombuffer(m.data, np.uint8, vb['count'] * vb['stride'], vb['offset']).reshape(vb['count'], vb['stride'])
                return raw[:, x['offset']:x['offset'] + 12].copy().view('<f4').reshape(-1, 3)
    return None


def main(fadir, fajson, vbidx, out, draws):
    bycount = defaultdict(list)
    for line in open(vbidx, encoding='utf-8'):
        r = json.loads(line)
        if 'count' in r:
            bycount[r['count']].append(r)
    fa = {d['draw']: d for d in json.load(open(fajson))}
    res = {}
    for di in draws:
        d = fa[di]
        m = load_draw(fadir, d)
        P = m['POSITION0'][:, :3].astype(np.float32)
        n = len(P)
        hits = []
        for c in bycount.get(n, []):
            try:
                data = entry(c['a'], c['e'])
                mo = ktpack.models(data)[c['model']][0]
                g = gt.parse(data, mo)
                Q = g1m_positions(g, c['vb'])
            except Exception as ex:  # noqa: BLE001
                continue
            if Q is None or len(Q) != n:
                continue
            err = float(np.abs(Q - P).max())
            if err < 1e-3:
                hits.append({'a': c['a'], 'e': c['e'], 'model': c['model'], 'g1m_off': mo, 'vb': c['vb'], 'stride': c['stride'], 'err': err})
        res[di] = hits
        print(di, 'n', n, 'hits', [(h['a'], h['e'], h['model'], h['vb'], h['stride']) for h in hits][:5], flush=True)
    json.dump(res, open(out, 'w'), indent=1)


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('fadir', metavar='FrameAnalysis_dir'); ap.add_argument('fajson', metavar='fa.json')
    ap.add_argument('vbidx', metavar='g1m_vb.jsonl'); ap.add_argument('out', metavar='out.json')
    ap.add_argument('draws', nargs='+', type=int, metavar='draw')
    ap.add_argument('--game-dir', default=os.environ.get('N2_GAME_DIR'), help='Nioh 2 folder with archive/ (default: N2_GAME_DIR)')
    ap.add_argument('--cache', help='folder for decompressed archive entries, reused between runs (default: none)')
    a = ap.parse_args()
    ADIR = os.path.join(a.game_dir, 'archive') if a.game_dir else None
    CACHE = a.cache
    main(a.fadir, a.fajson, a.vbidx, a.out, a.draws)
