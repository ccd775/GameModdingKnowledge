"""Physics chains for Ichel (Nioh 3 NUNO type-4 bone chains): chain points and vertex weights -> BUILD/physics.json
(the format n3_build_g1m.py / n3_g1m_physics.py read, see tools/n3build/n3_physics.py).

The chains are the model's own physics bones: every FBX bone family below whose PMX rigid bodies are dynamic
(mode 1 / 2) and that weights vertices. A chain is a family root (its parent is outside the family) followed down its
single child; its points are the bone heads plus a tip (the last segment repeated), mapped into game space by the
affine / similarity fit of each bone's weighted vertices (source -> conformed, n3_physics.point_fit). Chain joint i
takes the source weight of bone i (the tip none); the rest of a vertex's weight keeps its conformed game bones in
proportion. The face mesh is left to ichel_face (n3_face.py).

Families (template: 'hair' keeps the modelled shape, 'waist' is a pure pendulum; collision sets n3_g1m_physics):
  HairBack      Hf_<level>_<k>   11 back-hair strands            head 12   hair   head, torso
  HairSideBack  Yhb / Zhb        side-back locks                 head      hair   head, torso
  HairFront     Yqb / Zqb        front side locks                head      hair   head
  HairLock      Yb / Zb          locks in front of the shoulders head      hair   head, torso
  Ahoge         E                forehead lock                   head      hair   head
  Braid         Xbz              small braid                     head      hair   head
  Ear           Yed / Zed        animal ears                     head      hair   -
  Sleeve        Yxz / Zxz        10 strips round each puff sleeve upper arm 15/16 hair -
  SkirtRibbon   Qda/Qdb/M_qd*    ribbons at the skirt's sides    hips 2    waist  legs
  BackRibbon    Bs / M_bs        bow on the back                 chest 10  waist  torso
Not used: Wb (tail, its mesh is not in the FBX), the breast bones (single bodies).
usage: ichel_physics.py <pmx>
"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'n3build'))
import pmx_read  # noqa: E402
from n3_common import BUILD, load_source, to_game_axes  # noqa: E402
from n3_physics import FIT_MIN_WEIGHT, SIDE_TOL, point_fit  # noqa: E402

FAMILIES = (   # FBX bone name pattern, chain name, template, collision sets
    (r'^Hf_\d+_\d+$', 'HairBack', 'hair', ['head', 'torso']),
    (r'^[YZ]hb_\d+_1$', 'HairSideBack', 'hair', ['head', 'torso']),
    (r'^[YZ]qb_\d+_1$', 'HairFront', 'hair', ['head']),
    (r'^[YZ]b_\d+_1$', 'HairLock', 'hair', ['head', 'torso']),
    (r'^E_\d+_1$', 'Ahoge', 'hair', ['head']),
    (r'^Xbz_\d+_1$', 'Braid', 'hair', ['head']),
    (r'^(Yed_\d+|Zed_\d+_1)$', 'Ear', 'hair', []),
    (r'^[YZ]xz_\d+(_\d+)?$', 'Sleeve', 'hair', []),
    (r'^(M_)?[Qq]d[ab]\d$', 'SkirtRibbon', 'waist', ['legs']),
    (r'^(M_)?[Bb]s\d$', 'BackRibbon', 'waist', ['torso']),
    (r'^Wb_\d+_1$', 'Tail', 'hair', ['torso', 'legs']),
)
ANCHOR = {'Head': 12, 'Chest': 10, 'Spine': 2, 'Hips': 2, 'LeftUpperArm': 15, 'RightUpperArm': 16}


def norm(n):
    return re.sub(r'[^a-z0-9]', '', n.lower())


def dynamic_bones(pmx_path):
    pj = pmx_read.parse(pmx_path)
    return {norm(pj['bones'][r['bone']]['name']) for r in pj['rigid_bodies'] if r['mode'] in (1, 2) and r['bone'] >= 0}


def family_of(fbx_name):
    for i, (pat, *_rest) in enumerate(FAMILIES):
        if fbx_name and re.match(pat, fbx_name):
            return i
    return None


def find_chains(bones, dyn):
    """[(family index, [bone names root -> tip])]"""
    fam = {b['name']: family_of(b['fbx_name']) for b in bones}
    kids = {}
    for b in bones:
        kids.setdefault(b['parent'], []).append(b['name'])
    out = []
    for b in bones:
        f = fam[b['name']]
        if f is None or fam.get(b['parent']) == f:
            continue
        names = [b['name']]
        while True:
            nxt = [c for c in kids.get(names[-1], []) if fam[c] == f]
            if not nxt:
                break
            assert len(nxt) == 1, f'{names[-1]} branches: {nxt}'
            names.append(nxt[0])
        out.append((f, names))
    by = {b['name']: b for b in bones}
    for f, names in out:
        not_dyn = [n for n in names if norm(by[n]['fbx_name']) not in dyn]
        assert not not_dyn or len(not_dyn) == len(names), f'{names[0]}: partly static {not_dyn}'
    return [(f, n) for f, n in out if norm(by[n[0]]['fbx_name']) in dyn]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('pmx', help='the original PMX (its rigid bodies say which bones are dynamic)')
    args = ap.parse_args()
    dyn = dynamic_bones(args.pmx)
    meta, arr = load_source()
    conf = dict(np.load(BUILD / 'conformed.npz'))
    cj = json.loads((BUILD / 'conform.json').read_text(encoding='utf-8'))
    hs, t0 = cj['head_scale'], np.array(cj['t0'])
    base = lambda p: hs * to_game_axes(p) + t0  # noqa: E731
    bones = {b['name']: b for b in meta['bones']}
    W, src, dst, gws = {}, {}, {}, {}
    for m in meta['meshes']:
        k = m['key']
        w = np.zeros((len(arr[k + '__co']), len(m['groups'])))
        w[arr[k + '__w_vertex'], arr[k + '__w_group']] = arr[k + '__w_weight']
        W[k] = w / w.sum(1, keepdims=True)
        src[k] = base(arr[k + '__co']); dst[k] = conf[k + '__pos'].astype(float)
        gws[k] = [{int(b): x for b, x in json.loads(s).items()} for s in conf[k + '__gw']]
    by_group = {}
    for m in meta['meshes']:
        if m['name'] == 'Body':
            continue
        for gi, g in enumerate(m['groups']):
            if (W[m['key']][:, gi] > 1e-4).any():
                by_group.setdefault(g, []).append((m['key'], gi))

    def fit(name):
        b = name
        while b is not None:
            X, Y = [], []
            for k, gi in by_group.get(b, []):
                sel = W[k][:, gi] >= FIT_MIN_WEIGHT
                X.append(src[k][sel]); Y.append(dst[k][sel])
            if X and sum(len(x) for x in X) >= 4:
                return point_fit(np.concatenate(X), np.concatenate(Y))
            b = bones[b]['parent']
        raise SystemExit(f'no weighted vertices on {name} or its parents')

    chains, weights, report, skipped = [], {}, [], []
    owner = {}
    count = {}
    for f, names in find_chains(meta['bones'], dyn):
        _, label, tmpl, coll = FAMILIES[f]
        if not any(n in by_group for n in names):
            skipped.append((label, names[0], 'no weighted vertices'))
            continue
        a = bones[names[0]]['parent']
        while a not in ANCHOR:
            a = bones[a]['parent']
        pts, res = [], []
        for x in names:
            (M, t), r = fit(x)
            pts.append(M @ base(np.array(bones[x]['head'])) + t); res.append(r)
        tip_src = 2 * np.array(bones[names[-1]]['head']) - np.array(bones[names[-2]]['head'])
        (M, t), _ = fit(names[-1])
        pts.append(M @ base(tip_src) + t)
        P = np.array(pts)
        x = P[:, 0].mean()
        side = 'L' if x > 1.0 else 'R' if x < -1.0 else 'C'
        count[(label, side)] = count.get((label, side), 0) + 1
        name = f'{label}_{side}_{count[(label, side)] - 1}' if side != 'C' else f'{label}_{count[(label, side)] - 1}'
        ci = len(chains)
        for j, b in enumerate(names):
            owner[b] = (ci, j)
        chains.append({'name': name, 'bones': names, 'anchor': ANCHOR[a], 'template': tmpl,
                       'points': P.round(4).tolist(), 'collide': coll, 'part': 'rest'})
        report.append((name, ANCHOR[a], len(P), max(res)))
    for m in meta['meshes']:
        k = m['key']
        if m['name'] == 'Body':
            continue
        cols = [(gi, owner[g]) for gi, g in enumerate(m['groups']) if g in owner]
        wd = {}
        for v in range(len(W[k])):
            lst = [[c, j, float(W[k][v, gi])] for gi, (c, j) in cols if W[k][v, gi] > 1e-4]
            if not lst:
                continue
            rest = 1.0 - sum(x for _, _, x in lst)
            lst += [[-1, b, rest * x] for b, x in gws[k][v].items() if rest * x > 1e-4]
            wd[str(v)] = [[c, j, round(x, 6)] for c, j, x in lst]
        if wd:
            weights[k] = wd
    for ci, c in enumerate(chains):
        side = 1 if '_L_' in c['name'] else -1 if '_R_' in c['name'] else 0
        xs = [dst[k][int(v), 0] for k, wd in weights.items() for v, lst in wd.items() if any(e[0] == ci for e in lst)]
        c['vertices'] = len(xs)
        assert xs, f"{c['name']}: no vertices"
        if side:
            wrong = sum(1 for x in xs if side * x < -SIDE_TOL)
            assert wrong == 0, f"{c['name']}: {wrong} vertices on the other side"
    (BUILD / 'physics.json').write_text(json.dumps({'chains': chains, 'weights': weights}))
    for (name, anchor, n, res), c in zip(report, chains):
        P = np.array(c['points'])
        print(f"{name:16s} anchor {anchor:3d} points {n:2d} vertices {c['vertices']:5d} length "
              f"{np.linalg.norm(P[1:] - P[:-1], axis=1).sum():6.1f} fit rms {res:.3f}  {c['template']} {c['collide']}")
    print('skipped', skipped)
    print('chains', len(chains), 'joints', sum(len(c['points']) for c in chains),
          'weighted vertices', sum(len(w) for w in weights.values()))


if __name__ == '__main__':
    main()
