"""Physics chains for Karin_Original (Nioh 3 NUNO type-4 bone chains): chain points and vertex weights.

Default: Karin's own rig. Her VRM carries the author's spring chains (VRMC_springBone, converted from PhysBones);
each spring becomes one chain whose points are its bone heads plus the tip, mapped into game space by a similarity
fit of each bone's weighted vertices (source -> conformed, so every conform deformation is followed). Chain joint i
takes the source weight of spring bone i; the rest of a vertex's weight keeps its conformed game bones in proportion.
The anchor is the game bone the spring root's parent rides (RIG_ANCHOR). Cheek springs are skipped (face jiggle on the
expression mesh, n3_face.py owns it).

--geometry: the earlier geometry-derived chains (conformed game-space geometry, cm):
  twin_L / twin_R  the 13 hair strand islands per side hanging below y=140, anchored to the head (12)
  tail             the tail mesh, anchored to the hips (2)
  skirt_0..7       (--skirt) 8 chains of 3 points (waistband, middle, hem) every 45 deg around the skirt, hips (2)
Each chain's points are slice centroids along its main direction, root first. A vertex in the chain region is
weighted to the two chain joints around its projection on the centre line (linear blend); vertices above the
root keep the anchor weight, and the first segment blends from the anchor into the chain.
Skirt vertices blend between the two neighbouring chains by angle and between their points by height.
`collide` names the LLOC collision sets a chain uses (n3_g1m_physics.COLLISION_SETS), `part` the submesh group.
Output: BUILD/physics.json  {chains: [{name, anchor, template, points, collide, part}],
                             weights: {mesh key: {vertex: [[chain, point, w], ...]}}}   point -1 = the anchor;
                             chain -1 = a plain game bone: [-1, bone id, w]
usage: n3_physics.py [--vrm <Karin.vrm>] [--geometry [--skirt]]   (default mode: --vrm or N3_VRM)
"""
import argparse
import os
import json
import re
import struct
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import scipy.sparse.csgraph as cg

from n3_common import BUILD, load_source, to_game_axes

VRM = os.environ.get('N3_VRM')     # the source VRM with the VRMC_springBone chains (--vrm overrides)
RIG = (   # spring root prefix -> (template entry kind, collision sets); first match wins, None = skipped
    ('Cheek', None),
    ('Hair_tail', ('hair', ['head', 'torso'])), ('Hair_side', ('hair', ['head', 'torso'])),
    ('Hair_front', ('hair', ['head'])), ('Ribbon_L', ('hair', ['head'])), ('Ribbon_R', ('hair', ['head'])),
    ('Ear', ('hair', [])),
    # tail and skirt: the hair entry's parameters hold the modelled shape (build20: with the waist tassels' the tail
    # hung straight down between the legs and the skirt fell onto the thighs); the skirt's set adds Karin's buttocks
    # to the legs set (build24: in forward-leaning attacks it sank into her buttocks)
    ('Tail', ('hair', ['torso', 'legs'])), ('Skirt', ('hair', ['skirt'])),
    ('Ribbon_camisole', ('waist', ['torso'])), ('Ribbon_tops', ('waist', ['torso'])),
    ('Ribbon_hand', ('waist', [])), ('Shoes_tag', ('waist', [])),
)
# game bone each spring root's parent rides: the camisole ribbon (under Neck) sits on the chest, and the cuff ribbons
# (under the hands) on the sleeves, which follow the forearm (n3_conform.py)
RIG_ANCHOR = {'Head': 12, 'Hips': 2, 'Chest': 10, 'Neck': 10, 'LeftFoot': 7, 'RightFoot': 8,
              'LeftHand': 17, 'RightHand': 18}
FIT_MIN_WEIGHT = 0.3        # vertices at least this much on a bone define its source -> game fit
AFFINE_MIN_SPREAD = 0.1     # smallest / largest principal spread for an affine fit (else similarity)
SIDE_TOL = 0.5              # cm: an _L chain may weight vertices down to x = -SIDE_TOL (and mirrored)

CHAINS = {   # --geometry: name -> (anchor bone id, template entry kind, points, collision sets)
    'twin_L': (12, 'hair', 6, ['head', 'torso']),
    'twin_R': (12, 'hair', 6, ['head', 'torso']),
    'tail': (2, 'waist', 5, ['torso', 'legs']),
    'skirt': (2, 'waist', 3, ['legs']),
}
SKIRT_CHAINS = 8
TWIN_MIN_Y = 140.0          # a strand island belongs to a twin tail when its lowest point is below this


def islands(pos, vt):
    n = len(pos)
    a, b = np.r_[vt[:, 0], vt[:, 1], vt[:, 2]], np.r_[vt[:, 1], vt[:, 2], vt[:, 0]]
    nc, lab = cg.connected_components(sp.coo_matrix((np.ones(len(a)), (a, b)), shape=(n, n)), directed=False)
    used = np.unique(vt)
    return [used[lab[used] == c] for c in np.unique(lab[used])]


def centre_line(p, root, n):
    """n points from the root end to the far end along the main axis (slice centroids, root pinned)."""
    axis = p.mean(0) - root
    axis /= np.linalg.norm(axis)
    s = (p - root) @ axis
    lo, hi = 0.0, np.percentile(s, 99)
    out = [root]
    for t in np.linspace(lo, hi, n)[1:]:
        band = np.abs(s - t) < (hi - lo) / (n - 1) * 0.5
        out.append(p[band].mean(0) if band.sum() >= 3 else root + axis * t)
    return np.array(out)


def chain_weights(p, pts, fade):
    """[(point index, w)] per vertex: projection onto the poly line, linear between neighbours.
    `fade`: length of the first segment over which the weight blends in from the anchor (point -1)."""
    seg = pts[1:] - pts[:-1]
    L = np.linalg.norm(seg, axis=1)
    out = []
    for v in p:
        best = None
        for i in range(len(seg)):
            u = np.clip((v - pts[i]) @ seg[i] / L[i] ** 2, 0, 1)
            d = np.linalg.norm(v - (pts[i] + u * seg[i]))
            if best is None or d < best[0]:
                best = (d, i, u)
        _, i, u = best
        if i == 0 and (v - pts[0]) @ seg[0] < 0:
            out.append([(-1, 1.0)])          # above the root: anchor only
            continue
        w = [(i, 1 - u), (i + 1, u)]
        if i == 0 and fade:
            k = min(1.0, u * L[0] / fade)      # anchor share fades out along the first segment
            w = [(-1, (1 - u) * (1 - k)), (0, (1 - u) * k), (1, u)]
        out.append([(j, x) for j, x in w if x > 1e-4])
    return out


def skirt(sm, conf, chains, weights):
    """SKIRT_CHAINS chains around the skirt; weights: angular blend of two chains x height blend of their points."""
    key = sm['key']; p = conf[key + '__pos'].astype(float)
    anchor, tmpl, n, coll = CHAINS['skirt']
    y_top, y_hem = np.percentile(p[:, 1], 98), np.percentile(p[:, 1], 2)
    levels = np.linspace(y_top, y_hem, n)
    ang = np.arctan2(p[:, 0], p[:, 2])                     # 0 = front (+z), +90 deg = character's left (+x)
    step = 2 * np.pi / SKIRT_CHAINS
    base = len(chains)
    for k in range(SKIRT_CHAINS):
        th = k * step
        d = np.angle(np.exp(1j * (ang - th)))
        sector = np.abs(d) < step / 2
        pts = []
        for y in levels:
            band = sector & (np.abs(p[:, 1] - y) < (y_top - y_hem) / (n - 1) * 0.35)
            pts.append(p[band].mean(0))
        chains.append({'name': f'skirt_{k}', 'anchor': anchor, 'template': tmpl,
                       'points': np.array(pts).round(4).tolist(), 'vertices': int(sector.sum()), 'collide': coll,
                       'part': 'skirt'})
    wd = weights.setdefault(key, {})
    for v in range(len(p)):
        a = (ang[v] % (2 * np.pi)) / step
        k0 = int(np.floor(a)) % SKIRT_CHAINS; f = a - np.floor(a); k1 = (k0 + 1) % SKIRT_CHAINS
        s_ = np.clip((y_top - p[v, 1]) / (y_top - y_hem), 0, 1) * (n - 1)
        j0 = min(int(np.floor(s_)), n - 2); g = s_ - j0
        out = {}
        for kc, wa in ((k0, 1 - f), (k1, f)):
            for j, wv in ((j0, 1 - g), (j0 + 1, g)):
                if j == 0:          # waistband point: shared with the anchor so the band stays on the hips
                    out[(-1, -1)] = out.get((-1, -1), 0) + wa * wv * 0.5
                    out[(base + kc, 0)] = out.get((base + kc, 0), 0) + wa * wv * 0.5
                else:
                    out[(base + kc, j)] = out.get((base + kc, j), 0) + wa * wv
        wd[str(v)] = [[base if c < 0 else c, -1 if c < 0 else j, round(float(w), 6)] for (c, j), w in out.items() if w > 1e-4]


def springs():
    """[(root name, [joint names])] from the VRM's VRMC_springBone (names as in source.json: '.' and ' ' -> '_')."""
    if not VRM:
        raise SystemExit('N3_VRM is not set: give the source VRM (VRMC_springBone) with --vrm or N3_VRM')
    d = Path(VRM).read_bytes()
    n = struct.unpack_from('<I', d, 12)[0]
    j = json.loads(d[20:20 + n])
    nodes = j['nodes']
    out = []
    for s in j['extensions']['VRMC_springBone']['springs']:
        names = [nodes[x['node']]['name'].replace('.', '_').replace(' ', '_') for x in s['joints']]
        out.append((names[0], names))
    return out


def point_fit(X, Y):
    """(M, t) with M x + t ~ y, residual rms: affine where the points span 3D well (conform moves limbs and the hips
    by affines), else a similarity (Umeyama)."""
    mx, my = X.mean(0), Y.mean(0)
    A, B = X - mx, Y - my
    sv = np.linalg.svd(A, compute_uv=False)
    if len(X) >= 12 and sv[2] > AFFINE_MIN_SPREAD * sv[0]:
        M = np.linalg.lstsq(A, B, rcond=None)[0].T
    else:
        U, S, Vt = np.linalg.svd(B.T @ A / len(X))
        D = np.eye(3); D[2, 2] = np.sign(np.linalg.det(U @ Vt))
        var = (A ** 2).sum() / len(X)
        M = ((S * np.diag(D)).sum() / var if var > 1e-12 else 1.0) * (U @ D @ Vt)
    t = my - M @ mx
    res = np.sqrt((((X @ M.T + t) - Y) ** 2).sum(1).mean())
    return (M, t), float(res)


def rig():
    meta, arr = load_source()
    conf = dict(np.load(BUILD / 'conformed.npz'))
    cj = json.loads((BUILD / 'conform.json').read_text(encoding='utf-8'))
    hs, t0 = cj['head_scale'], np.array(cj['t0'])
    base = lambda p: hs * to_game_axes(p) + t0  # noqa: E731
    bones = {b['name']: b for b in meta['bones']}
    # per mesh: normalised source weights (vertex x group) and conformed positions / game weights
    W, src, dst, gws = {}, {}, {}, {}
    for m in meta['meshes']:
        k = m['key']
        w = np.zeros((len(arr[k + '__co']), len(m['groups'])))
        w[arr[k + '__w_vertex'], arr[k + '__w_group']] = arr[k + '__w_weight']
        W[k] = w / w.sum(1, keepdims=True)
        src[k] = base(arr[k + '__co']); dst[k] = conf[k + '__pos'].astype(float)
        gws[k] = [{int(b): x for b, x in json.loads(s).items()} for s in conf[k + '__gw']]
    by_group = {}       # bone name -> [(mesh key, group index)]
    for m in meta['meshes']:
        for gi, g in enumerate(m['groups']):
            by_group.setdefault(g, []).append((m['key'], gi))

    def fit(name):
        """source -> game fit of a bone from its weighted vertices; walks up to the parent if it has none."""
        b = name
        while b is not None:
            X, Y = [], []
            for k, gi in by_group.get(b, []):
                sel = W[k][:, gi] >= FIT_MIN_WEIGHT
                X.append(src[k][sel]); Y.append(dst[k][sel])
            if X and sum(len(x) for x in X) >= 4:
                return (b, *point_fit(np.concatenate(X), np.concatenate(Y)))
            b = bones[b]['parent']
        raise SystemExit(f'no weighted vertices on {name} or its parents')

    chains, weights, report = [], {}, []
    owner = {}          # source bone -> (chain, joint)
    for root, names in springs():
        kind = next((v for p, v in RIG if root.startswith(p)), 'missing')
        assert kind != 'missing', f'spring {root} has no RIG entry'
        if kind is None:
            continue
        tmpl, coll = kind
        missing = [x for x in names if x not in bones]
        assert not missing, f'{root}: bones {missing} not in source.json'
        a = bones[root]['parent']
        while a not in RIG_ANCHOR:
            a = bones[a]['parent']
            assert a is not None, f'{root}: no anchored ancestor'
        pts, res = [], []
        for x in names:
            _, (M, t), r = fit(x)
            pts.append(M @ base(np.array(bones[x]['head'])) + t); res.append(r)
        ci = len(chains)
        for j, x in enumerate(names):
            owner[x] = (ci, j)
        part = 'skirt' if root.startswith('Skirt') else 'rest'
        chains.append({'name': root, 'anchor': RIG_ANCHOR[a], 'template': tmpl,
                       'points': np.array(pts).round(4).tolist(), 'collide': coll, 'part': part})
        report.append((root, RIG_ANCHOR[a], len(names), max(res)))
    for m in meta['meshes']:
        k = m['key']
        if m['name'] == 'Body':
            continue                      # the face (and its cheek springs) belongs to n3_face.py
        cols = [(gi, owner[g]) for gi, g in enumerate(m['groups']) if g in owner]
        if not cols:
            continue
        wd = weights.setdefault(k, {})
        for v in range(len(W[k])):
            lst = [[c, j, float(W[k][v, gi])] for gi, (c, j) in cols if W[k][v, gi] > 1e-4]
            if not lst:
                continue
            rest = 1.0 - sum(x for _, _, x in lst)
            lst += [[-1, b, rest * x] for b, x in gws[k][v].items() if rest * x > 1e-4]
            wd[str(v)] = [[c, j, round(x, 6)] for c, j, x in lst]
    # every chain's vertices stay on its own side
    for ci, c in enumerate(chains):
        side = 1 if re.search(r'_L(_|$)', c['name']) else -1 if re.search(r'_R(_|$)', c['name']) else 0
        xs = [dst[k][int(v), 0] for k, wd in weights.items() for v, lst in wd.items() if any(e[0] == ci for e in lst)]
        c['vertices'] = len(xs)
        assert xs, f"{c['name']}: no vertices"
        if side:
            wrong = sum(1 for x in xs if side * x < -SIDE_TOL)
            assert wrong == 0, f"{c['name']}: {wrong} vertices on the other side"
    return chains, weights, report


def main():
    global VRM
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--vrm', help='source VRM with VRMC_springBone (default: N3_VRM)')
    ap.add_argument('--geometry', action='store_true', help='geometry-derived chains instead of Karin\'s own rig')
    ap.add_argument('--skirt', action='store_true', help='with --geometry: 8 skirt chains')
    args = ap.parse_args()
    VRM = args.vrm or VRM
    if args.geometry:
        return geometry(args.skirt)
    chains, weights, report = rig()
    (BUILD / 'physics.json').write_text(json.dumps({'chains': chains, 'weights': weights}))
    for (root, anchor, n, res), c in zip(report, chains):
        P = np.array(c['points'])
        print(f"{root:18s} anchor {anchor:3d} points {n} vertices {c['vertices']:5d} length "
              f"{np.linalg.norm(P[1:] - P[:-1], axis=1).sum():6.1f} fit rms {res:.3f}  {c['template']} {c['collide']}")
    print('chains', len(chains), 'joints', sum(len(c['points']) for c in chains),
          'weighted vertices', sum(len(w) for w in weights.values()))


def geometry(with_skirt=False):
    meta, arr = load_source()
    conf = dict(np.load(BUILD / 'conformed.npz'))
    by_name = {m['name']: m for m in meta['meshes']}
    chains, weights = [], {}

    # twin tails
    hm = by_name['hair']; hk = hm['key']
    pos = conf[hk + '__pos'].astype(float)
    vt = arr[hk + '__loop_vertex'][arr[hk + '__tris']]
    strands = [c for c in islands(pos, vt) if pos[c, 1].min() < TWIN_MIN_Y]
    for name, sign in (('twin_L', 1), ('twin_R', -1)):
        idx = np.concatenate([c for c in strands if np.sign(pos[c, 0].mean()) == sign])
        p = pos[idx]
        top = p[p[:, 1] > p[:, 1].max() - 3.0]
        root = top.mean(0)
        anchor, tmpl, n, coll = CHAINS[name]
        pts = centre_line(p, root, n)
        cw = chain_weights(p, pts, fade=float(np.linalg.norm(pts[1] - pts[0])) * 0.6)
        ci = len(chains)
        chains.append({'name': name, 'anchor': anchor, 'template': tmpl, 'points': pts.round(4).tolist(),
                       'vertices': int(len(idx)), 'collide': coll, 'part': 'rest'})
        wd = weights.setdefault(hk, {})
        for v, w in zip(idx, cw):
            wd[str(int(v))] = [[ci, j, round(float(x), 6)] for j, x in w]

    # tail
    tm = by_name['tail']; tk = tm['key']
    pos = conf[tk + '__pos'].astype(float)
    p = pos
    root_band = p[:, 2] > p[:, 2].max() - 4.0          # the end nearest the body (largest z)
    root = p[root_band].mean(0)
    anchor, tmpl, n, coll = CHAINS['tail']
    pts = centre_line(p, root, n)
    cw = chain_weights(p, pts, fade=float(np.linalg.norm(pts[1] - pts[0])) * 0.5)
    ci = len(chains)
    chains.append({'name': 'tail', 'anchor': anchor, 'template': tmpl, 'points': pts.round(4).tolist(),
                   'vertices': int(len(p)), 'collide': coll, 'part': 'rest'})
    wd = weights.setdefault(tk, {})
    for v, w in enumerate(cw):
        wd[str(v)] = [[ci, j, round(float(x), 6)] for j, x in w]

    if with_skirt:
        skirt(by_name['skirt'], conf, chains, weights)

    (BUILD / 'physics.json').write_text(json.dumps({'chains': chains, 'weights': weights}))
    for c in chains:
        P = np.array(c['points'])
        print(c['name'], 'anchor', c['anchor'], 'vertices', c['vertices'], 'length', round(float(np.linalg.norm(P[1:] - P[:-1], axis=1).sum()), 1))
        print('   ', P.round(1).tolist())


if __name__ == '__main__':
    main()
