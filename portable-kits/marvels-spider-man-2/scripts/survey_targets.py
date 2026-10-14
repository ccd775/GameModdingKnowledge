"""For every candidate hero model: looks (LOD0 / min slots), skeleton signature, required joints present.
Writes Work/reports/targets.json used by the batch builder."""
import argparse, hashlib, json, os, re
import numpy as np
from sm2_common import load_index, load_toc, extract, REPORTS
import i30_model as M
import sm2_build_model as SB
from sm2_karin_geo import HUMAN2NAME

argparse.ArgumentParser(description=__doc__).parse_args()
idx = load_index()
toc = load_toc()
suits = json.load(open(os.path.join(REPORTS, 'suit_models.json')))
cands = set()
for v in suits.values():
    for m in v['models']:
        if m.startswith(('characters/hero/hero_spiderman', 'characters/hero/hero_peterparker', 'characters/hero/hero_milesmorales')):
            cands.add(m)
for extra in ('characters/hero/hero_spiderman_advanced/hero_spiderman_advanced_removesymbiote.model',
              'characters/hero/hero_spiderman_symbiote/hero_spiderman_symbiote_split_cine.model'):
    cands.add(extra)
cands.discard('characters/hero/hero_spiderman_miles_venomxray/hero_spiderman_miles_venomxray.model')
need = set(HUMAN2NAME.values()) | {'spine', 'spine_helper1', 'spine_B', 'spine_B_helper2', 'chest'}
for s in ('LF_', 'RT_'):
    need |= {s + 'uparm_bind_1', s + 'uparm_bind_2', s + 'uparm_bind_3', s + 'uparm_bind_4', s + 'loarm_bind_2',
             s + 'loarm_bind_3', s + 'loarm_bind_4', s + 'loarm_bind_5'}
out = {}
for p in sorted(cands):
    v = idx.get(p.replace('/', chr(92)))
    if not v:
        print('MISSING', p)
        continue
    data, e = extract(toc, int(v['id'], 16), 0)
    m = M.Model(data)
    lk = SB.looks(m)
    names = [j['name'] for j in m.joints]
    missing = sorted(need - set(names))
    W = m.joint_world()
    key = [(n, tuple(np.round(W[i][3, :3], 3))) for i, n in enumerate(names) if n in need]
    sig = hashlib.sha1(json.dumps(sorted(key)).encode()).hexdigest()[:12]
    main = 'body' if 'body' in lk else 'Default'
    slots = [len(x) for x in lk[main]]
    out[p] = dict(bytes=len(data), joints=len(names), sig=sig, missing=missing, looks=list(lk), main=main,
                  slots=slots, lod0_meshes=lk[main][0])
    print(f'{p.split("/")[-1]:55s} {len(data):>9} j{len(names):4d} sig {sig} main {main:8s} slots {slots} miss {missing[:4]} looks {list(lk)[:6]}', flush=True)
json.dump(out, open(os.path.join(REPORTS, 'targets.json'), 'w'), indent=1)
print(len(out), 'targets;', len({v["sig"] for v in out.values()}), 'skeleton signatures')
