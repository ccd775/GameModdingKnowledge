"""Physics chains for Lenko (Nioh 3 NUNO type-4 bone chains): chain points and vertex weights -> BUILD/physics.json
(the format n3_build_g1m.py / n3_g1m_physics.py read, see tools/n3build/n3_physics.py).

The chains are the model's own physics bones: every PMX bone with a dynamic rigid body (mode 1 / 2) whose parent has
none starts a chain, which follows its single dynamic child down (the PMX has no branching chains). Points are the
bone heads plus a tip (the last segment repeated), mapped into game space by the affine / similarity fit of each
bone's weighted vertices (source -> conformed, n3_physics.point_fit). Chain joint i takes the source weight of bone i;
the rest of a vertex's weight keeps its conformed game bones in proportion. The face (Body) is n3_face.py's.

Kinds (root name -> label, template, anchor from the root's parent, collision sets):
  hair.*          Hair     hair     head 12   head (+ torso when the chain reaches below the neck)
                  LongHair longhair head 12   lenko_hair, torso  (the 4 strands over 40 cm: subdivided, see LONG_HAIR)
  Accessories*    Ornament hair     head 12   -        (the ribbons on top of her head)
  sk*             Skirt    hair     hips 2    lenko_skirt (11 chains; one continues into the long ribbon, one into
                                                           the bow on her left hip)
  streamer ribbon Tie      hair     chest 10  lenko_tie (the necktie; lenko1's waist template + the vanilla torso set
                                                         left it hanging off a 25 cm sphere in front of her belly)
  Bust*           Bust     hair     chest 10  -        (the breasts, one 3-bone chain each, user 2026-11-03 "胸部也要添加
                                                         一些物理，不需要太大的强度": the chains get BUST_SHARE of the
                                                         author's breast weights, the chest keeps the rest; no collision,
                                                         the points sit inside the chest)
Not used: the coat bones (Coat*). lenko1/2 swung the coat below the belt on its own 8 chains and the skirt, ~2 cm
inside it at rest, crossed it in game (the game does not collide cloth with cloth; user 2026-11-03 chose "外套跟着短裙摆").
Coat vertices below the belt now take the skirt's weights at the nearest point of the skirt surface (coat_follows_skirt),
blended with their own by the author's coat-bone share, so the two layers move together and keep their gap.
'hair' keeps the modelled shape (the skirt with the waist parameters fell onto the thighs, Karin build20).
The lenko_* collision sets are fitted to her body by lenko_coll.py (registered in lenko_build.py).
usage: lenko_physics.py <pmx>
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'n3build'))
sys.path.insert(0, str(HERE.parent / 'n3ichel'))
import pmx_read  # noqa: E402
from n3_common import BUILD, CHEST, load_model, load_source, skeleton, to_game_axes  # noqa: E402
from n3_physics import FIT_MIN_WEIGHT, SIDE_TOL, point_fit  # noqa: E402

KINDS = (   # root prefix, label, template, collision sets (None = decided per chain), part
    ('hair', 'Hair', 'hair', None, 'rest'),
    ('Accessories', 'Ornament', 'hair', [], 'rest'),
    ('sk', 'Skirt', 'hair', ['lenko_skirt'], 'skirt'),
    ('Coat', None, None, None, None),
    ('streamer ribbon', 'Tie', 'hair', ['lenko_tie'], 'rest'),
    ('Bust', 'Bust', 'hair', [], 'rest'),
)
# hair chains longer than LONG_HAIR (the four strands to her waist): template 'longhair' (the vanilla 50 cm hair's
# parameters, lenko_build.py), cut into segments of at most SEG_MAX (vanilla long hair ~4.5 cm; her bones are 9-12 cm
# apart and the strands swung as one block in lenko1), weights re-spread along the finer chain by position
LONG_HAIR = 40.0      # cm
SEG_MAX = 4.5         # cm
LONG_SETS = ['lenko_hair', 'torso']
ANCHOR = {'Head': 12, 'Chest': 10, 'Spine': 2, 'Hips': 2}
SIDE_X = 1.0          # cm: a chain whose points' mean |x| is below this is centred (no side)
CROSS_MAX = 10.0      # cm: furthest a side chain's vertex may sit on the other side of the midline
BUST_SHARE = 0.5      # share of the author's breast-bone weight the breast chains drive (the chest keeps the rest)
COAT_RAMP = 0.5       # coat vertices follow the skirt in full once the author's coat-bone share reaches this
COAT_KEEP = 6         # weights kept per transferred coat vertex (largest, renormalised)
ARM = ('Arm', 'Hand', 'Shoulder', 'Thumb', 'Index', 'Middle', 'Ring', 'Little', '腕', '手', '肩')


def subdivide(P):
    """points of P with every segment cut into equal parts of at most SEG_MAX"""
    out = []
    for a, b in zip(P[:-1], P[1:]):
        n = int(np.ceil(np.linalg.norm(b - a) / SEG_MAX))
        out += [a + (b - a) * m / n for m in range(n)]
    return np.array(out + [P[-1]])


def spread(Q, p, s):
    """weight s of a vertex at p over the joints of the chain Q by its position along it: nearest segment, blended
    between neighbouring segments' joints across each joint (segment i is driven by joint i; the tip joint by none)"""
    d = Q[1:] - Q[:-1]
    a = np.clip(((p - Q[:-1]) * d).sum(1) / (d * d).sum(1), 0, 1)
    i = int(np.argmin(np.linalg.norm(Q[:-1] + a[:, None] * d - p, axis=1)))
    u = min(max(i + a[i] - 0.5, 0.0), len(d) - 1.0)
    j = int(np.floor(u)); f = u - j
    return [(j, s)] if f < 1e-6 else [(j, s * (1 - f)), (j + 1, s * f)]


def coat_follows_skirt(W, groups, dst, weights, gws):
    """Coat weights below the belt from the skirt surface: each coat vertex (not a sleeve: arm share < 0.5) takes the
    barycentric mix of the skirt weight lists at its nearest skirt point, blended with its own by the author's
    coat-bone share / COAT_RAMP. Edits weights['coat'] in place; returns a report."""
    from scipy.spatial import cKDTree
    conf = np.load(BUILD / 'conformed.npz')
    T = conf['skirt__loop_vertex'][conf['skirt__tris']]                 # skirt triangles, conformed vertex ids
    sk_w = weights.get('skirt', {})
    full = lambda v: sk_w.get(str(v)) or [[-1, b, x] for b, x in gws['skirt'][v].items()]  # noqa: E731
    bary = np.array([(a, b, 1 - a - b) for a in np.linspace(0, 1, 7) for b in np.linspace(0, 1, 7) if a + b <= 1 + 1e-9])
    pts = np.einsum('kc,tcx->tkx', bary, dst['skirt'][T]).reshape(-1, 3)
    tree = cKDTree(pts)
    cg = [i for i, g in enumerate(groups) if g.startswith('Coat')]
    ag = [i for i, g in enumerate(groups) if any(a in g for a in ARM)]
    s_coat = W[:, cg].sum(1); s_arm = W[:, ag].sum(1)
    own = weights.setdefault('coat', {})
    moved, dist, full_n = 0, [], 0
    for v in np.nonzero((s_coat > 1e-4) & (s_arm < 0.5))[0]:
        d, i = tree.query(dst['coat'][v])
        t, k = divmod(int(i), len(bary))
        mix = {}
        for c, sv in zip(bary[k], T[t]):
            if c <= 1e-9:
                continue
            for ci, j, x in full(int(sv)):
                mix[ci, j] = mix.get((ci, j), 0.0) + c * x
        f = min(1.0, float(s_coat[v]) / COAT_RAMP)
        mine = own.get(str(v)) or [[-1, b, x] for b, x in gws['coat'][v].items()]
        out = {key: f * x for key, x in mix.items()}
        for ci, j, x in mine:
            out[ci, j] = out.get((ci, j), 0.0) + (1 - f) * x
        top = sorted(out.items(), key=lambda kv: -kv[1])[:COAT_KEEP]
        tot = sum(x for _, x in top)
        own[str(v)] = [[ci, j, round(x / tot, 6)] for (ci, j), x in top if x / tot > 1e-5]
        moved += 1; dist.append(d); full_n += f >= 1
    return {'coat_vertices': moved, 'full': int(full_n), 'nearest_skirt_cm': [round(float(np.min(dist)), 2),
            round(float(np.median(dist)), 2), round(float(np.max(dist)), 2)]}


def kind_of(root):
    for k in KINDS:
        if root.startswith(k[0]):
            return k
    raise SystemExit(f'chain root {root}: no kind')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('pmx', help='the source PMX (its rigid bodies say which bones are dynamic)')
    args = ap.parse_args()
    pj = pmx_read.parse(args.pmx)
    dyn_pmx = {pj['bones'][r['bone']]['name'] for r in pj['rigid_bodies'] if r['mode'] in (1, 2) and r['bone'] >= 0}
    meta, arr = load_source()
    conf = dict(np.load(BUILD / 'conformed.npz'))
    cj = json.loads((BUILD / 'conform.json').read_text(encoding='utf-8'))
    hs, t0 = cj['head_scale'], np.array(cj['t0'])
    base = lambda p: hs * to_game_axes(p) + t0  # noqa: E731
    neck_y = skeleton(load_model(CHEST)[1])[11]['pos'][1]
    bones = {b['name']: b for b in meta['bones']}
    dyn = {b['name'] for b in meta['bones'] if b.get('pmx_name') in dyn_pmx}
    kids = {}
    for b in meta['bones']:
        kids.setdefault(b['parent'], []).append(b['name'])
    roots = [b['name'] for b in meta['bones'] if b['name'] in dyn and b['parent'] not in dyn]
    W, src, dst, gws = {}, {}, {}, {}
    for m in meta['meshes']:
        k = m['key']
        w = np.zeros((len(arr[k + '__co']), len(m['groups'])))
        w[arr[k + '__w_vertex'], arr[k + '__w_group']] = arr[k + '__w_weight']
        W[k] = w / w.sum(1, keepdims=True)
        src[k] = base(arr[k + '__co'].astype(float)); dst[k] = conf[k + '__pos'].astype(float)
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

    chains, weights, report, skipped, owner, count, long = [], {}, [], [], {}, {}, {}
    for root in roots:
        _, label, tmpl, coll, part = kind_of(root)
        names = [root]
        while True:
            nxt = [c for c in kids.get(names[-1], []) if c in dyn]
            if not nxt:
                break
            assert len(nxt) == 1, f'{names[-1]} branches: {nxt}'
            names.append(nxt[0])
        if label is None:
            skipped.append((root, 'not used')); continue
        if not any(n in by_group for n in names):
            skipped.append((root, 'no weighted vertices')); continue
        assert len(names) >= 2, f'{root}: single-bone chain'
        a = bones[root]['parent']
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
        if label == 'Hair' and np.linalg.norm(P[1:] - P[:-1], axis=1).sum() > LONG_HAIR:
            label, tmpl, coll = 'LongHair', 'longhair', LONG_SETS
            P = subdivide(P)
            long[len(chains)] = P
        if coll is None:
            coll = ['head', 'torso'] if P[:, 1].min() < neck_y else ['head']
        x = P[:, 0].mean()
        side = 'L' if x > SIDE_X else 'R' if x < -SIDE_X else 'C'
        count[(label, side)] = count.get((label, side), 0) + 1
        name = f'{label}_{side}_{count[(label, side)] - 1}' if side != 'C' else f'{label}_{count[(label, side)] - 1}'
        ci = len(chains)
        for j, b in enumerate(names):
            owner[b] = (ci, j)
        chains.append({'name': name, 'bones': names, 'anchor': ANCHOR[a], 'template': tmpl,
                       'points': P.round(4).tolist(), 'collide': coll, 'part': part})
        report.append((name, root, ANCHOR[a], len(P), max(res)))
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
            for ci, Q in long.items():
                s = sum(x for c, _, x in lst if c == ci)
                if s > 0:
                    lst = [e for e in lst if e[0] != ci] + [[ci, j, x] for j, x in spread(Q, dst[k][v], s)]
            bust = {ci for ci, c in enumerate(chains) if c['name'].startswith('Bust')}
            lst = [[c, j, x * BUST_SHARE if c in bust else x] for c, j, x in lst]
            rest = 1.0 - sum(x for _, _, x in lst)
            lst += [[-1, b, rest * x] for b, x in gws[k][v].items() if rest * x > 1e-4]
            wd[str(v)] = [[c, j, round(x, 6)] for c, j, x in lst]
        if wd:
            weights[k] = wd
    ck = [m for m in meta['meshes'] if m['name'] == 'coat'][0]
    coat_report = coat_follows_skirt(W[ck['key']], ck['groups'], dst, weights, gws)
    print('coat follows skirt:', coat_report)
    side_report = {}
    for ci, c in enumerate(chains):
        side = 1 if '_L_' in c['name'] else -1 if '_R_' in c['name'] else 0
        xs = [dst[k][int(v), 0] for k, wd in weights.items() for v, lst in wd.items() if any(e[0] == ci for e in lst)]
        c['vertices'] = len(xs)
        assert xs, f"{c['name']}: no vertices"
        if side:
            over = [(-side * dst[k][int(v), 0], sum(e[2] for e in lst if e[0] == ci)) for k, wd in weights.items()
                    for v, lst in wd.items() if any(e[0] == ci for e in lst) and side * dst[k][int(v), 0] < -SIDE_TOL]
            if over:
                side_report[c['name']] = (len(over), round(float(max(o[0] for o in over)), 2),
                                          round(float(max(o[1] for o in over if o[0] > CROSS_MAX) if any(o[0] > CROSS_MAX for o in over) else 0), 3),
                                          c['bones'][0])
    # chains next to the midline legitimately reach across it (the author's own weights: pleats, coat panels and hair
    # strands either side of the centre, and the waistband smoothed over every skirt root at <= 0.31); a real left /
    # right mix-up would put a large weight far across
    print('vertices across the midline (count, furthest cm, largest chain weight beyond CROSS_MAX, root):')
    for n, r in side_report.items():
        print('   ', n, r)
    assert all(r[2] <= 0.5 for r in side_report.values()), 'a chain carries a large weight far on the other side'
    (BUILD / 'physics.json').write_text(json.dumps({'chains': chains, 'weights': weights}))
    for (name, root, anchor, n, res), c in zip(report, chains):
        P = np.array(c['points'])
        print(f"{name:14s} {root:20s} anchor {anchor:3d} points {n:2d} vertices {c['vertices']:5d} length "
              f"{np.linalg.norm(P[1:] - P[:-1], axis=1).sum():6.1f} low y {P[:, 1].min():6.1f} fit rms {res:.3f}  "
              f"{c['template']} {c['collide']}")
    print('skipped', skipped)
    print('chains', len(chains), 'joints', sum(len(c['points']) for c in chains),
          'weighted vertices', sum(len(w) for w in weights.values()))


if __name__ == '__main__':
    main()
