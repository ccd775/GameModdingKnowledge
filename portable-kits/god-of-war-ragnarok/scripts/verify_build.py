"""Round-trip check of a built character (kratos | valk): every planned slot decoded back from the built WAD/lodpack
must reproduce the source geometry vertex for vertex (positions, joints, weights, triangles); hidden defs must hit a
zeroed block that no planned slot occupies.
usage: verify_build.py kratos|valk OUT --game G --base-wad W --fit DIR --fit-lods DIR --karin-bones J --rigspec J
(the same base WAD, fits, bone table and rigspec the build used)"""
import sys, os, json, glob, argparse, numpy as np
from wad import Wad
from mesh import parse_mesh
from mg import parse_mg_groups
from decode import decode, skin_of
from packs import read_lodpack_toc
from rigspec import world
from geometry import build as build_geo, subset, merge
from encode import max_influences, limit_influences
from build_mesh import root_buffer
from gamedir import set_game

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('kind', choices=('kratos', 'valk'))
ap.add_argument('out', help='build output folder (wad, lodpack, mesh_report.json)')
ap.add_argument('--game', help='game folder with exec/ (root.lodpack is read from it; default: GOWR_GAME)')
ap.add_argument('--base-wad', required=True, help='the base WAD the build started from')
ap.add_argument('--fit', required=True)
ap.add_argument('--fit-lods', required=True)
ap.add_argument('--karin-bones', required=True)
ap.add_argument('--rigspec', required=True)
args = ap.parse_args()
set_game(args.game)
KIND, O = args.kind, args.out.rstrip('/\\') + '/'
CFG = {
    'kratos': dict(name='heroa00', proto='goProtoheroa00', wad='r_heroa00.wad', pack='KarinOriginal'),
    'valk': dict(name='freyavalkyrie00', proto='goProtofreyaValkyrie00', wad='r_freyavalkyrie00.wad',
                 pack='KarinOriginalFreya'),
}[KIND]
CFG.update(fit=args.fit, lods=args.fit_lods, kb=args.karin_bones, spec=args.rigspec)
base_path = args.base_wad
w = Wad(open(O + CFG['wad'], 'rb').read())
w0 = Wad(open(base_path, 'rb').read())
nm = CFG['name']
get = lambda W, n, t=None: W.get([e for e in W.entries if e.name == n and (t is None or e.type == t)][0])
nb = world(get(w0, CFG['proto']))[0]
ms, ms0 = parse_mesh(get(w, f'MESH_{nm}_0', 1)), parse_mesh(get(w0, f'MESH_{nm}_0', 1))
gs0 = parse_mg_groups(get(w0, f'MG_{nm}_0', 153))
gpu, gpu0 = get(w, f'MG_{nm}_0_gpu'), get(w0, f'MG_{nm}_0_gpu')
hdr = w.get(w.entries[1])
g, mem, _ = read_lodpack_toc(O + CFG['pack'] + '.lodpack.toc')
lp = open(O + CFG['pack'] + '.lodpack', 'rb').read()


def buf(h):
    if h == 0:
        return gpu
    gi, mo, size = mem[h]
    return lp[g[gi][0] + mo: g[gi][0] + mo + size]


def rbuf(h):
    try:
        return root_buffer(h)
    except KeyError:
        return root_buffer(h - 1)


deform = set()
for grp in gs0:
    for mi in (grp['lods'][0]['meshes'] if grp['lods'] else []):
        m0 = ms0[mi]
        if not m0.vcount or not any(c[0] == 9 for c in m0.comps):
            continue
        try:
            o0, _ = decode(m0, gpu0 if m0.hash == 0 else rbuf(m0.hash))
            deform |= {j for s in skin_of(m0, o0) for j, wt in s if wt > 0.01}
        except Exception:
            pass
geos = {'full': build_geo(CFG['fit'], CFG['kb'], CFG['spec'])}
for d in glob.glob(os.path.join(CFG['lods'], 'r*')):
    geos[os.path.basename(d)[1:]] = build_geo(d, CFG['kb'], CFG['spec'])
rep = json.load(open(O + 'mesh_report.json'))
bad = 0
for k, ch in rep['chosen'].items():
    m, m0 = ms[int(k)], ms0[int(k)]
    exp = merge([subset(geos[lvl], [p]) for p, lvl in ch['levels'].items()])
    kk = max_influences(m)
    inf = limit_influences(exp['INF'], kk) if any(len(i) > kk for i in exp['INF']) else exp['INF']
    out, idx = decode(m, buf(m.hash))
    P = np.array([x[:3] for x in [v for key, v in out.items() if key[0] == 0][0]])
    sk = skin_of(m, out)
    pos_err = float(np.abs(P - exp['P']).max())
    j_ok, w_err = 0, 0.0
    for got, want in zip(sk, inf):
        gw = {}
        for j, wt in got:
            gw[j] = gw.get(j, 0.0) + wt
        ww = {}
        for j, wt in want[:kk]:
            ww[j] = ww.get(j, 0.0) + wt
        j_ok += {j for j, wt in ww.items() if wt > 0.02} <= {j for j, wt in gw.items() if wt > 0.0}
        w_err = max(w_err, max(abs(gw.get(j, 0.0) - wt) for j, wt in ww.items()))
    tri_ok = np.array_equal(np.array(idx).reshape(-1, 3), exp['IDX'])
    used = {j for s in sk for j, wt in s if wt > 0.001}
    nondeform = sorted(used - deform)
    ok = (m.vcount == len(exp['P']) and pos_err < 1e-5 and j_ok == m.vcount and w_err < 0.01 and tri_ok and max(used) < nb
          and (KIND != 'valk' or not nondeform) and (m.hash == 0 or m.hash in (m0.hash, m0.hash + 1)))
    bad += not ok
    print(f"{k:>5} g{ch['group']:<3} lod{ch['lod']} v={m.vcount:<6} pos_err={pos_err:.1e} joints_ok={j_ok}/{m.vcount} "
          f"w_err={w_err:.3f} tris_ok={tri_ok} nondeform={nondeform} {'OK' if ok else 'BAD'}")
planned = {int(k) for k in rep['chosen']}
hid = [m for m in ms if m.i not in planned]
dh = {(m.hash, m.buf_offs[0] if m.buf_count else None) for m in hid if m.vcount == 1}
print('hidden', len(hid), 'dummy targets', [(hex(h), o) for h, o in dh])
for h, o in dh:
    z = buf(h)[o:o + 0x100] == bytes(0x100)
    def occupied(m):                       # vertex streams and index range actually written for a planned slot
        rs = [(b, b + m.vcount * st) for b, st in zip(m.buf_offs, m.strides)]
        return rs + [(m.ind_off, m.ind_off + m.icount * m.ind_stride)]
    clash = [m.i for m in ms if m.i in planned and m.hash == h and any(a < o + 0x100 and o < b for a, b in occupied(m))]
    print('  block', hex(h), o, 'zero:', z, 'overlaps planned slots:', clash)
    bad += (not z) or bool(clash)
print('BAD', bad)
