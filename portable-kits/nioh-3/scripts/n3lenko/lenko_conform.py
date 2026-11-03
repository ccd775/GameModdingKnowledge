"""Conform Lenko (lenko_source.py output) onto the Nioh 3 player skeleton and give every vertex game skin weights.
The transforms, weight mapping and body-weight transfer are ichel_conform.py's (itself n3_conform.py's); what differs:

- meshes: head-riding: Body (face), headskin, hair, headwear; body-weight transfer: skin, clothes, legwear, belt;
  mapped (her own weights moved to game bones): skirt, ribbon, tie, coat. The hand rule (vertices with >= 0.3 of
  their mapped weight on the hand / finger bones keep it) covers the skin and the clothes (her fingerless gloves);
  the coat follows the sleeve rule (no hand or finger bones, they go to the forearm).
- the skirt's hips -> leg blend towards the hem uses the leg skin (legwear: her bare / stockinged thighs), not 'skin'
  (her torso and arms); the hem push is smaller (SKIRT_PUSH) because the coat now hangs just above it.
- scale: the neck height ratio (MMD units -> cm, ~8.2).
- the coat's back below the belt is draped onto the skirt (drape_coat_back): the PMX coat stands 4-7 cm off the skirt
  there and steps out again at the hips (gap 4.0 cm at y 97, 5.9 at y 91), which lenko3's longer coat showed as a
  bulge behind her (user 2026-11-03 "身后的臀部附近的外套下摆鼓起来了一块"). Each (azimuth, height) cell of the coat is
  moved radially in until its innermost layer is DRAPE_GAP outside the skirt / ribbon, never inside the coat's own
  radius at the belt (it does not tuck in under the belt), fading in over BACK_AZ and DRAPE_RAMP; sleeves and the
  pocket pigs are not moved.
Output: BUILD/conformed.npz + BUILD/conform.json
usage: lenko_conform.py   (BUILD = N3_BUILD; N3_HEAD_SCALE, default: the neck height ratio)
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'n3build'))
sys.path.insert(0, str(HERE.parent / 'n3ichel'))
from n3_common import BUILD, CHEST, load_model, load_source, skeleton, to_game_axes  # noqa: E402
import ichel_conform as ic  # noqa: E402

HEAD_MESHES = ('Body', 'headskin', 'hair', 'headwear')
TRANSFER_MESHES = ('skin', 'clothes', 'legwear', 'belt')
HAND_RULE = ('skin', 'clothes')
SLEEVES = ('coat',)
LEG_REF = 'legwear'
SKIRT_FMAX, SKIRT_PUSH = 0.75, 0.5
DRAPE_GAP = 1.5            # cm: every layer of the coat (the hem band's inner face too) this far outside the skirt /
                           # ribbon behind her (lenko3's smallest rest gap there was 1.0)
BACK_AZ = (100.0, 130.0)   # deg from the front: the drape fades in over this range (the pocket pigs end at 93)
DRAPE_RAMP = 4.0           # cm below the belt's lower edge to the full drape
CELL = (2.0, 0.5)          # deg, cm: drape grid
ARM = ('Arm', 'Hand', 'Shoulder', 'Thumb', 'Index', 'Middle', 'Ring', 'Little', '腕', '手', '肩')


def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def surface_samples(P, T, n=5):
    bary = np.array([(a, b, 1 - a - b) for a in np.linspace(0, 1, n) for b in np.linspace(0, 1, n) if a + b <= 1 + 1e-9])
    return np.einsum('kc,tcx->tkx', bary, P[T]).reshape(-1, 3)


def vertex_normals(P, T):
    fn = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])
    vn = np.zeros_like(P)
    for c in range(3):
        np.add.at(vn, T[:, c], fn)
    return vn / (np.linalg.norm(vn, axis=1, keepdims=True) + 1e-12)


def drape_coat_back(out, meta, arr):
    """Pull the coat's back below the belt in to DRAPE_GAP (inner surface) outside the skirt / ribbon (see the
    docstring). Edits the coat's positions and loop normals in `out`; returns a report."""
    from scipy.ndimage import gaussian_filter, maximum_filter, minimum_filter
    key = {m['name']: m['key'] for m in meta['meshes']}
    cm = next(m for m in meta['meshes'] if m['name'] == 'coat')
    k = cm['key']
    P = out[k + '__pos'].astype(float)
    lv = arr[k + '__loop_vertex']; T = lv[arr[k + '__tris']]
    zc = float(out[key['skirt'] + '__pos'][:, 2].mean())
    W = np.zeros((len(P), len(cm['groups'])))
    W[arr[k + '__w_vertex'], arr[k + '__w_group']] = arr[k + '__w_weight']
    W /= W.sum(1, keepdims=True)
    s_arm = W[:, [i for i, g in enumerate(cm['groups']) if any(a in g for a in ARM)]].sum(1)
    pig = [i for i, mt in enumerate(cm['materials']) if 'Pig' in mt['name']]
    fixed = s_arm >= 0.5
    fixed[np.unique(T[np.isin(arr[k + '__tri_material'], pig)])] = True
    az_of = lambda Q: np.degrees(np.arctan2(Q[:, 0], Q[:, 2] - zc))  # noqa: E731
    r_of = lambda Q: np.hypot(Q[:, 0], Q[:, 2] - zc)  # noqa: E731
    B = out[key['belt'] + '__pos'].astype(float)
    y_top = float(np.percentile(B[np.abs(az_of(B)) >= BACK_AZ[0], 1], 2))
    nb, y0 = int(360 / CELL[0]), float(P[:, 1].min()) - 1.0
    ny = int(np.ceil((y_top + 2.0 - y0) / CELL[1]))

    def grid(Q, outer=True):
        """outer (inner) radius per (azimuth, height) cell, max- (min-) filtered over +-1 cell (azimuth wraps);
        -inf (+inf) where empty"""
        ia = ((az_of(Q) + 180) // CELL[0]).astype(int) % nb; iy = ((Q[:, 1] - y0) // CELL[1]).astype(int)
        ok = (iy >= 0) & (iy < ny)
        G = np.full((nb, ny), -np.inf if outer else np.inf)
        (np.maximum if outer else np.minimum).at(G, (ia[ok], iy[ok]), r_of(Q)[ok])
        return (maximum_filter if outer else minimum_filter)(G, size=(3, 3), mode=('wrap', 'nearest'))

    inner = np.concatenate([surface_samples(out[key[n] + '__pos'].astype(float),
                                            arr[key[n] + '__loop_vertex'][arr[key[n] + '__tris']])
                            for n in ('skirt', 'ribbon')])
    Gs = grid(inner)
    for a in range(nb):                       # below the skirt hem: the hem's radius (the coat hangs on past it)
        col = Gs[a]; ok = np.isfinite(col)
        if ok.any():
            lo = np.argmax(ok); col[:lo] = col[lo]
    keep = ~fixed[T].any(1)
    Q = surface_samples(P, T[keep])
    Gc, Gi = grid(Q), grid(Q, outer=False)
    iy_top = int((y_top - y0) // CELL[1])
    r_top = np.max(Gc[:, iy_top:iy_top + 3], axis=1)
    # the move keeps the outer surface at or outside the coat's radius at the belt, the inner one DRAPE_GAP out
    with np.errstate(invalid='ignore'):
        need = np.maximum(r_top[:, None] - Gc, Gs + DRAPE_GAP - Gi)
    idx = np.arange(ny)
    for a in range(nb):     # cells without coat (below the hem) carry the column's nearest value, so the smoothing
        ok = np.isfinite(need[a])   # below does not fade the hem's move towards the empty cells
        if ok.any():
            need[a] = np.interp(idx, idx[ok], need[a, ok])
    bound = np.where(np.isfinite(need), np.minimum(0.0, need), 0.0)      # the furthest each cell may move in
    ac = (np.arange(nb) + 0.5) * CELL[0] - 180; yc = y0 + (np.arange(ny) + 0.5) * CELL[1]
    d = bound * smoothstep((np.abs(ac) - BACK_AZ[0]) / (BACK_AZ[1] - BACK_AZ[0]))[:, None]
    d *= smoothstep((y_top - yc) / DRAPE_RAMP)[None, :]
    for _ in range(4):      # smooth, but never past a cell's own bound (a neighbour's pull must not close a small gap)
        d = np.maximum(gaussian_filter(d, sigma=(2.0, 2.0), mode=('wrap', 'nearest')), bound)
    move = ~fixed & (P[:, 1] < y_top)
    fa = (az_of(P[move]) + 180) / CELL[0] - 0.5; fy = (P[move, 1] - y0) / CELL[1] - 0.5
    a0 = np.floor(fa).astype(int); ta = fa - a0; yy = np.clip(fy, 0, ny - 1.001); j0 = np.floor(yy).astype(int); ty = yy - j0
    dv = ((1 - ta) * (1 - ty) * d[a0 % nb, j0] + ta * (1 - ty) * d[(a0 + 1) % nb, j0]
          + (1 - ta) * ty * d[a0 % nb, j0 + 1] + ta * ty * d[(a0 + 1) % nb, j0 + 1])
    radial = P[move] - np.array([0.0, 0.0, zc]); radial[:, 1] = 0
    radial /= np.linalg.norm(radial, axis=1, keepdims=True) + 1e-9
    n_old = vertex_normals(P, T)
    Pn = P.copy(); Pn[move] += dv[:, None] * radial
    n_new = vertex_normals(Pn, T)
    # loop normals follow the turn of the geometric vertex normal (Rodrigues), keeping the authored smoothing
    a, b = n_old[lv], n_new[lv]
    ln = out[k + '__loop_normal'].astype(float)
    ax = np.cross(a, b); s = np.linalg.norm(ax, axis=1); c = (a * b).sum(1)
    ax /= np.maximum(s, 1e-12)[:, None]
    rot = (ln * c[:, None] + np.cross(ax, ln) * s[:, None] + ax * (ax * ln).sum(1, keepdims=True) * (1 - c)[:, None])
    ln = np.where((s > 1e-9)[:, None], rot, ln)
    out[k + '__pos'] = Pn.astype(np.float32)
    out[k + '__loop_normal'] = (ln / np.linalg.norm(ln, axis=1, keepdims=True)).astype(np.float32)
    # report: coat vertex radius minus the inner layer's at its cell, back sector, before / after
    sel = move & (np.abs(az_of(P)) >= BACK_AZ[1])
    ia = ((az_of(P[sel]) + 180) // CELL[0]).astype(int) % nb; iy = np.clip(((P[sel, 1] - y0) // CELL[1]).astype(int), 0, ny - 1)
    gap0 = r_of(P[sel]) - Gs[ia, iy]; gap1 = r_of(Pn[sel]) - Gs[ia, iy]
    ok = np.isfinite(gap0)
    return {'y_top': round(y_top, 2), 'moved': int((dv < -1e-3).sum()), 'pull_max_cm': round(float(-dv.min()), 2),
            'back_gap_cm_before_min_med_max': np.round(np.percentile(gap0[ok], [0, 50, 100]), 2).tolist(),
            'back_gap_cm_after_min_med_max': np.round(np.percentile(gap1[ok], [0, 50, 100]), 2).tolist()}


def main():
    meta, arr = load_source()
    bones = meta['bones']
    _, chest = load_model(CHEST)
    sk = skeleton(chest)
    Q = {b: v['pos'] for b, v in sk.items()}
    neck_src = to_game_axes(np.array(next(b for b in bones if b['name'] == 'Neck')['head']))
    scale = ic.HEAD_SCALE or float(Q[11][1] / neck_src[1])
    t0 = Q[11] - scale * neck_src
    base = lambda p: scale * to_game_axes(p) + t0  # noqa: E731
    J, T, report = ic.build_transforms(bones, Q, base)
    hmap = ic.humanoid_map()
    xf, gmap = ic.resolve(bones, T, hmap)
    spine_ys = [Q[i][1] for i in ic.SPINE]
    body_P, body_W = ic.body_reference()
    body_tree = cKDTree(body_P)
    hand_bones = {19, 20} | {g + o for ids in ic.FINGERS.values() for g in ids for o in (0, 1)}
    out = {}
    summary = {'head_scale': scale, 't0': t0.tolist(), 'transforms': report, 'meshes': {}}
    leg_ref = None
    for m in meta['meshes']:
        k = m['key']; groups = m['groups']; name = m['name']
        co = base(arr[k + '__co'].astype(float)); nv = len(co)
        W = np.zeros((nv, len(groups)))
        W[arr[k + '__w_vertex'], arr[k + '__w_group']] = arr[k + '__w_weight']
        s = W.sum(1); assert (s > 0).all(), name
        W /= s[:, None]
        newp = np.zeros_like(co); Ab = np.zeros((nv, 3, 3))
        for gi, g in enumerate(groups):
            w = W[:, gi]
            if w.any():
                A, t = xf[g]
                newp += w[:, None] * (co @ A.T + t); Ab += w[:, None, None] * A
        lv = arr[k + '__loop_vertex']
        newn = np.einsum('nji,nj->ni', np.linalg.inv(Ab)[lv], to_game_axes(arr[k + '__loop_normal'].astype(float)))
        ln = np.linalg.norm(newn, axis=1)
        bad = ln < 1e-8
        if bad.any():
            tri = lv[arr[k + '__tris']]
            fn = np.cross(newp[tri[:, 1]] - newp[tri[:, 0]], newp[tri[:, 2]] - newp[tri[:, 0]])
            vn = np.zeros_like(newp)
            for c in range(3):
                np.add.at(vn, tri[:, c], fn)
            newn[bad] = vn[lv[bad]]
            ln = np.linalg.norm(newn, axis=1)
            summary['meshes'].setdefault(name, {})['geometric_normals'] = int(bad.sum())
        newn /= np.maximum(ln, 1e-12)[:, None]
        gw = [dict() for _ in range(nv)]
        for gi, g in enumerate(groups):
            target = gmap[g]
            for v in np.nonzero(W[:, gi])[0]:
                parts = ic.tent(newp[v, 1], ic.SPINE, spine_ys) if target == 'torso' else {target: 1.0}
                for b, f in parts.items():
                    gw[v][b] = gw[v].get(b, 0) + W[v, gi] * f
        if name in HEAD_MESHES:
            gw = [{12: 1.0} for _ in range(nv)]
        elif name in TRANSFER_MESHES:
            d, idx = body_tree.query(newp, k=ic.TRANSFER_K)
            iw = 1 / (d + 0.3); iw /= iw.sum(1, keepdims=True)
            f = 1 - np.clip((d[:, 0] - ic.TRANSFER_DIST[0]) / (ic.TRANSFER_DIST[1] - ic.TRANSFER_DIST[0]), 0, 1)
            moved = kept_hand = 0
            for v in range(nv):
                hand = sum(w for b, w in gw[v].items() if b in hand_bones)
                if name in HAND_RULE and hand >= 0.3:
                    kept_hand += 1
                    continue
                if f[v] <= 0:
                    continue
                acc = {b: (1 - f[v]) * w for b, w in gw[v].items()}
                for j in range(ic.TRANSFER_K):
                    for b, w in body_W[idx[v, j]].items():
                        acc[b] = acc.get(b, 0) + f[v] * iw[v, j] * w
                gw[v] = acc; moved += 1
            summary['meshes'].setdefault(name, {}).update({'transferred': moved, 'hand_rule_kept': kept_hand})
            summary['meshes'][name]['body_dist_p50_p95'] = np.round(np.percentile(d[:, 0], [50, 95]), 2).tolist()
        if name in SLEEVES:
            for dct in gw:
                for b in [b for b in dct if b in hand_bones]:
                    fore = ic.ARM_SIDE[ic.side_of(sk, b)]['fore']
                    dct[fore] = dct.get(fore, 0) + dct.pop(b)
        if name == LEG_REF:
            leg_ref = (newp.copy(), gw)
        xs = ic.cross_side(sk, newp, gw)
        summary['meshes'].setdefault(name, {})['cross_side_vertices'] = xs
        assert xs == 0, f'{name}: {xs} vertices weighted to the opposite arm'
        out[k + '__pos'] = newp.astype(np.float32)
        out[k + '__loop_normal'] = newn.astype(np.float32)
        out[k + '__gw'] = np.array([json.dumps({str(b): round(float(w), 6) for b, w in dct.items()}) for dct in gw])
        summary['meshes'].setdefault(name, {}).update({'bbox_min': np.round(newp.min(0), 2).tolist(),
                                                       'bbox_max': np.round(newp.max(0), 2).tolist()})
    # skirt: hips weights blend toward the nearest leg skin as the hem is approached, hem pushed outward
    sm = next(m for m in meta['meshes'] if m['name'] == 'skirt')
    sp = out[sm['key'] + '__pos'].astype(float)
    sgw = [{int(b): w for b, w in json.loads(x).items()} for x in out[sm['key'] + '__gw']]
    _, near = cKDTree(leg_ref[0]).query(sp, k=8)
    ytop, yhem = sp[:, 1].max(), sp[:, 1].min()
    tt = np.clip((ytop - sp[:, 1]) / (ytop - yhem), 0, 1)
    blended = []
    for v in range(len(sp)):
        f = SKIRT_FMAX * tt[v]
        acc = {b: (1 - f) * w for b, w in sgw[v].items()}
        for n in near[v]:
            for b, w in leg_ref[1][n].items():
                acc[b] = acc.get(b, 0) + f * w / len(near[v])
        blended.append(json.dumps({str(b): round(float(w), 6) for b, w in acc.items()}))
    out[sm['key'] + '__gw'] = np.array(blended)
    radial = sp - np.array([0.0, 0.0, sp[:, 2].mean()]); radial[:, 1] = 0
    radial /= np.linalg.norm(radial, axis=1, keepdims=True) + 1e-9
    out[sm['key'] + '__pos'] = (sp + SKIRT_PUSH * tt[:, None] * radial).astype(np.float32)
    summary['skirt'] = {'y_top': round(float(ytop), 2), 'y_hem': round(float(yhem), 2), 'push': SKIRT_PUSH}
    summary['coat_drape'] = drape_coat_back(out, meta, arr)
    for key in arr:
        if key.endswith(('__loop_uv', '__loop_vertex', '__tris', '__tri_material')):
            out[key] = arr[key]
    used = set()
    for key in out:
        if key.endswith('__gw'):
            for x in out[key]:
                used |= {int(b) for b in json.loads(x)}
    missing = sorted(b for b in used if b not in sk)
    assert not missing, f'bones not in the chest skeleton: {missing}'
    summary['bones_used'] = sorted(used)
    summary['source_joints_game'] = {n: np.round(p, 2).tolist() for n, p in J.items() if n in hmap}
    np.savez_compressed(BUILD / 'conformed.npz', **out)
    (BUILD / 'conform.json').write_text(json.dumps(summary, indent=1), encoding='utf-8')
    print('head scale', round(scale, 4))
    for n, v in summary['meshes'].items():
        print(n, v)
    print('skirt', summary['skirt'], 'bones used', len(used))
    print('coat drape', summary['coat_drape'])


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    main()
