"""List the skinned draws of a frame analysis, one row per (vb0, ib) pair: draw, VS / PS, vb0 / vb1 / ib hashes,
used vertices, triangles, bbox of the used vertices, max BLENDINDICES, then every draw with the same pair.
usage: fa_list.py <FrameAnalysis dir> <fa.json>   (fa.json from fa_parse.py --json)"""
import argparse,json,os,sys
ap=argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('fadir', metavar='FrameAnalysis_dir'); ap.add_argument('fajson', metavar='fa.json'); args=ap.parse_args()
import numpy as np
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from fa_mesh import load_draw
FA=args.fadir; d=json.load(open(args.fajson))
seen={}; rows=[]
for r in d:
    if 'ib' not in r or 'vb0' not in r: continue
    lays=[x for k in ('vb0','vb1') if k in r for x in r[k].get('layout',[])]
    if not any('BLENDINDICES' in x for x in lays): continue
    if not any(x.startswith('NORMAL') for x in lays): continue
    key=(r['vb0']['hash'], r['ib']['hash'])
    if key in seen: seen[key].append(r['draw']); continue
    seen[key]=[r['draw']]
    m=load_draw(FA,r)
    P=m.get('POSITION0')
    if P is None or 'tris' not in m: continue
    used=np.unique(m['tris']); used=used[used<len(P)]
    Q=P[used,:3].astype(float)
    bi=int(m['BLENDINDICES0'][used].max()) if 'BLENDINDICES0' in m else -1
    rows.append([r['draw'],r['vs'][:8],r['ps'][:8],r['vb0']['hash'],r.get('vb1',{}).get('hash','-'),r['ib']['hash'],len(used),len(m['tris']),np.round(Q.min(0),1).tolist(),np.round(Q.max(0),1).tolist(),bi])
for x in rows: print(*x, seen[(x[3],x[5])])
print(len(rows))
