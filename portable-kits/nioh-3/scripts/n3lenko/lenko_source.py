"""Lenko (Lenko06.pmx, by Kinsama) -> the source format the Nioh 3 build reads ($N3_BUILD/source: source.json / .npz,
shapekeys.json / .npz), read straight from the PMX (no Blender, no FBX).

usage: lenko_source.py <model dir>        (the folder with Lenko06.pmx and tex/)

Space: PMX is Y up, facing -Z, +X = the character's left, MMD units. The source format is Blender's (Z up, facing -Y,
+X left): (x, y, z)_blender = (x, z, y)_pmx. That swap is a reflection, so every triangle is written reversed (PMX
winding has the geometric normal along the vertex normals in PMX axes; after the swap it must be reversed to stay so).
UV: v_blender = 1 - v_pmx. Units stay MMD units; the conform scales by neck height.

Outfit: the coat version (the PMX default). Lenko_coat_Pig_l (the pig on the skirt, alpha 0 unless Coat_Hide) is left
out. The coat below the skirt belt is shortened (user request 2026-11-02: "把腰带以下的外套均匀缩短使得外套下摆末端略微高于
短裙末端"): coat vertices below the belt's lower edge (Y_BELT) that are not sleeve vertices (arm-bone share < 0.5) are
compressed towards it, y' = Y_BELT - k (Y_BELT - y), and so are the coat physics bones below it. lenko1/2 took the
largest k that kept the coat hem 0.2 above the skirt hem in every 15 deg sector (k 0.59); in game that looked too
short and the skirt showed under it (user 2026-11-03: "外套缩得有点过短了", then chose one ratio that covers the skirt), so
k is now the smallest factor that puts the coat hem at least HEM_COVER below the skirt hem in every sector where both
exist (capped at 1, the original length). The two
pocket pigs (Lenko_Pig_l) are scaled by k about their own centres (proportions kept), centres mapped like the coat,
so they shrink with their pockets instead of being flattened.

Meshes (by material, then by the triangle's dominant bone family):
  Body      face, face edge (lashes / mouth), eyes + brows  (n3_face.py rigs it; MMD morphs -> shape keys)
  headskin  Lenko_Body triangles riding the head (scalp / ears under the hair)
  skin      Lenko_Body (torso, arms, hands)
  hair      Lenko_Fhair, Lenko_Bhair
  headwear  head-riding triangles of Lenko_Skirt / Lenko_Skirt_h (hair ornaments)
  clothes   Lenko_Cloth, Lenko_Cloth_h (top, collar bow, cuffs, shoes, right garter)
  legwear   Lenko_Leg (socks, hips / underwear)
  belt      skirt-texture triangles on the spine / hips bones (waistband, belt, chain)
  skirt     skirt-texture triangles on the skirt bones (sk*)
  ribbon    the long ribbon hanging from the skirt's front left (sk.045 / sk.044 / sk.046)
  tie       the necktie (streamer ribbon) and the small chest pieces on the breast bones
  coat      Lenko_Coat_l, Lenko_Skirt_l (elbow cuffs), Lenko_Pig_l (pocket pigs)
Bones: humanoid MMD bones renamed to the names the conform expects (HUMANOID; leg skin is weighted to the D bones, so
those carry the leg names and the FK leg bones' few weights move onto them); finger tips `<finger>Distal_end` added
(extrapolated, no weights). The breast bones 'Chest*' are renamed 'Bust*' (the humanoid 'Chest' is 上半身2).
Face shape keys: every vertex morph, restricted to the Body mesh, plus the side-split keys n3_face.py maps
(blink_L/R from まばたき with the closing line lowered (bone_blink), mayu_up_L/R from 上, mayu_down_L/R from 下,
kuchi_smile_1_L/R from 口角上げ, kuchi_A from あ).
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'n3build'))
import lenko_pmx  # noqa: E402
from n3_common import BUILD  # noqa: E402

PMX = 'Lenko06.pmx'
Y_BELT = 12.95          # lower edge of the skirt belt (PMX units; belt band 12.9-13.3 all round, buckles dip lower)
HEM_COVER = 0.1         # coat hem at least this far below the skirt hem (~0.9 cm in game)
HEM_OUTLIER = 0.3       # skirt-hem sectors further than this from the median are ignored
SIDE_RAMP = 0.06        # side-split face keys blend over |x| < this (~0.5 cm)
CLOSE_BIN = 0.02        # bone_blink: x bins of the lower eye edge's lift (~0.2 cm)
CLOSE_MOVE = 0.03       # bone_blink: blink movers of at least this much (~0.3 cm) drop by the full lift
CLOSE_EXTRA = 0.025     # bone_blink: the falling lid / lashes go this much (~0.2 cm) further, over the fit residual
CLOSE_FALL = 0.1        # bone_blink: ... in full once they fall this much (~0.9 cm)
DROP_MATERIALS = ('Lenko_coat_Pig_l',)
FIXED = {'Lenko_Face': 'Body', 'Lenko_Face_edge': 'Body', 'Lenko_eyes_edge': 'Body',
         'Lenko_Fhair': 'hair', 'Lenko_Bhair': 'hair', 'Lenko_Cloth': 'clothes', 'Lenko_Cloth_h': 'clothes',
         'Lenko_Leg': 'legwear', 'Lenko_Coat_l': 'coat', 'Lenko_Skirt_l': 'coat', 'Lenko_Pig_l': 'coat'}
MESH_ORDER = ('Body', 'headskin', 'skin', 'hair', 'headwear', 'clothes', 'legwear', 'belt', 'skirt', 'ribbon', 'tie',
              'coat')
FINGERS = {'Thumb': '親指', 'Index': '人指', 'Middle': '中指', 'Ring': '薬指', 'Little': '小指'}
SEGS = ('Proximal', 'Intermediate', 'Distal')
LONG_RIBBON = ('sk.045', 'sk.044', 'sk.046')


def humanoid():
    m = {'下半身': 'Hips', '上半身': 'Spine', '上半身2': 'Chest', '首': 'Neck', '頭': 'Head',
         '左目': 'LeftEye', '右目': 'RightEye'}
    for side, s in (('Left', '左'), ('Right', '右')):
        m.update({f'{s}肩': f'{side}Shoulder', f'{s}腕': f'{side}UpperArm', f'{s}ひじ': f'{side}LowerArm',
                  f'{s}手首': f'{side}Hand', f'{s}足D': f'{side}UpperLeg', f'{s}ひざD': f'{side}LowerLeg',
                  f'{s}足首D': f'{side}Foot', f'{s}足先EX': f'{side}ToeBase'})
        for f, jp in FINGERS.items():
            first = 0 if f == 'Thumb' else 1
            for i, seg in enumerate(SEGS):
                m[f'{s}{jp}{"０１２３"[first + i]}'] = f'{side}{f}{seg}'
    return m


FK_TO_D = {f'{s}{a}': f'{s}{a}D' for s in '左右' for a in ('足', 'ひざ', '足首')} | {'左つま先': '左足先EX', '右つま先': '右足先EX'}


def ancestors(meta):
    par = [b['parent'] for b in meta['bones']]
    names = [b['name'] for b in meta['bones']]
    out = []
    for i in range(len(names)):
        s, b = set(), i
        while b >= 0:
            s.add(names[b]); b = par[b]
        out.append(s)
    return out


def shorten_coat(d, mats, names):
    """Compress the coat below Y_BELT (see the docstring). Returns a report; edits d['pos'] / d['nrm'] and the bone
    heads in d['meta'] in place."""
    P, N, F, FM, BI, BW = d['pos'], d['nrm'], d['faces'], d['face_mat'], d['bi'], d['bw']

    def share(vs, pred):
        s = np.zeros(len(vs))
        for k in range(4):
            ok = np.array([b >= 0 and pred(names[b]) for b in BI[vs, k]])
            s += np.where(ok, BW[vs, k], 0)
        return s

    def verts(*ms):
        return np.unique(F[np.isin(FM, [mats.index(m) for m in ms])])

    ang = lambda v: np.degrees(np.arctan2(P[v, 0], -P[v, 2]))  # noqa: E731
    sk = verts('Lenko_Skirt', 'Lenko_Skirt_h')
    # skirt hem per 15 deg sector: the lowest vertex on the skirt bones (not the long ribbon); sectors whose hem is more
    # than HEM_OUTLIER from the median are decorations hanging lower (the bow on the left hip) or the open front-right
    # panel, and are not used
    skirt = sk[(share(sk, lambda n: n.startswith('sk')) > 0.5) & (share(sk, lambda n: n in LONG_RIBBON) < 0.1)]
    coat = verts('Lenko_Coat_l')
    arm = share(coat, lambda n: any(k in n for k in ('腕', 'ひじ', '手')))
    body = coat[arm < 0.5]
    sectors = []
    for a0 in range(-180, 180, 15):
        s = skirt[(ang(skirt) >= a0) & (ang(skirt) < a0 + 15)]
        c = body[(ang(body) >= a0) & (ang(body) < a0 + 15)]
        if len(s) and len(c):
            sy, cy = float(P[s, 1].min()), float(P[c, 1].min())
            kk = (Y_BELT - sy + HEM_COVER) / (Y_BELT - cy)
            sectors.append({'sector': a0, 'skirt_hem': round(sy, 3), 'coat_hem': round(cy, 3), 'k_min': round(kk, 4)})
    med = float(np.median([s['skirt_hem'] for s in sectors]))
    for s in sectors:
        s['used'] = abs(s['skirt_hem'] - med) <= HEM_OUTLIER
    k = min(1.0, max(s['k_min'] for s in sectors if s['used']))
    move = body[P[body, 1] < Y_BELT]
    # sleeve vertices below the belt must not share a triangle with moved ones (no tear)
    moved = np.zeros(len(P), bool); moved[move] = True
    ct = F[FM == mats.index('Lenko_Coat_l')]
    mixed = int((moved[ct].any(1) & ~moved[ct].all(1) & (P[ct][:, :, 1] < Y_BELT - 1e-6).all(1)).sum())
    P[move, 1] = Y_BELT - k * (Y_BELT - P[move, 1])
    N[move, 1] /= k
    N[move] /= np.linalg.norm(N[move], axis=1, keepdims=True)
    pigs = verts('Lenko_Pig_l')
    assert not np.intersect1d(pigs, move).size, 'pig vertices shared with the coat'
    pig_report = []
    for side in (1, -1):
        v = pigs[np.sign(P[pigs, 0]) == side]
        c = (P[v].min(0) + P[v].max(0)) / 2
        c2 = c.copy(); c2[1] = Y_BELT - k * (Y_BELT - c[1])
        P[v] = c2 + k * (P[v] - c)
        pig_report.append({'side': 'L' if side > 0 else 'R', 'centre': c.round(3).tolist(), 'to': c2.round(3).tolist()})
    bones_moved = []
    for b in d['meta']['bones']:
        if b['name'].startswith('Coat') and b['pos'][1] < Y_BELT:
            p = list(b['pos']); p[1] = Y_BELT - k * (Y_BELT - p[1]); b['pos'] = p
            bones_moved.append(b['name'])
    after = P[body, 1].min()
    return {'y_belt': Y_BELT, 'cover': HEM_COVER, 'skirt_hem_median': round(med, 3), 'k': round(float(k), 4),
            'vertices': int(len(move)),
            'sleeve_vertices_kept': int((arm >= 0.5).sum()), 'mixed_triangles_below_belt': mixed,
            'coat_hem_before': round(float(min(s['coat_hem'] for s in sectors)), 3), 'coat_hem_after': round(float(after), 3),
            'sectors': sectors, 'pigs': pig_report, 'bones': bones_moved}


def classify(d, mats, names, anc):
    """Mesh name per triangle (None = dropped)."""
    F, FM, BI, BW = d['faces'], d['face_mat'], d['bi'], d['bw']
    nv = len(d['pos'])
    fam = {}
    for v in range(nv):
        acc = {}
        for k in range(4):
            b = BI[v, k]
            if b < 0 or BW[v, k] <= 0:
                continue
            a = anc[b]; n = names[b]
            key = ('head' if '頭' in a else 'ribbon' if n in LONG_RIBBON else 'skirt' if n.startswith('sk') or
                   n == 'streamer ribbon.004' else 'tie' if 'streamer ribbon' in n or n.startswith('Chest') else 'trunk')
            acc[key] = acc.get(key, 0) + BW[v, k]
        fam[v] = acc
    out = []
    for t, mi in zip(F, FM):
        name = mats[mi]
        if name in DROP_MATERIALS:
            out.append(None); continue
        tot = {}
        for v in t:
            for key, w in fam[v].items():
                tot[key] = tot.get(key, 0) + w
        top = max(tot, key=tot.get)
        if name in FIXED:
            out.append(FIXED[name])
        elif name == 'Lenko_Body':
            out.append('headskin' if top == 'head' else 'skin')
        elif name in ('Lenko_Skirt', 'Lenko_Skirt_h'):
            out.append({'head': 'headwear', 'skirt': 'skirt', 'ribbon': 'ribbon', 'tie': 'tie', 'trunk': 'belt'}[top])
        else:
            raise SystemExit(f'unassigned material {name}')
    # the ribbon tied at the belt: one strip (both faces) runs down her front left to the knee (sk.045-046), another
    # loops to the bow on her left hip (streamer ribbon.004); weighted across three skirt chains. Whole connected
    # pieces that carry either go to 'ribbon' so the skirt mesh is the pleats only.
    import scipy.sparse as sp
    import scipy.sparse.csgraph as cg
    sel = np.nonzero(np.isin(FM, [mats.index('Lenko_Skirt'), mats.index('Lenko_Skirt_h')]))[0]
    t = F[sel]
    a = np.r_[t[:, 0], t[:, 1], t[:, 2]]; b = np.r_[t[:, 1], t[:, 2], t[:, 0]]
    _, lab = cg.connected_components(sp.coo_matrix((np.ones(len(a)), (a, b)), shape=(nv, nv)), directed=False)
    marked = set()
    for v in np.unique(t):
        if any(BI[v, k] >= 0 and BW[v, k] > 0 and (names[BI[v, k]] in LONG_RIBBON or names[BI[v, k]] == 'streamer ribbon.004')
               for k in range(4)):
            marked.add(lab[v])
    for i, tri in zip(sel, t):
        if lab[tri[0]] in marked and out[i] in ('skirt', 'ribbon', 'belt'):
            out[i] = 'ribbon'
    return out


def to_bl(p):
    p = np.asarray(p, float)
    return np.stack([p[..., 0], p[..., 2], p[..., 1]], -1)


def bone_blink(dd, pos):
    """まばたき as the game's blink poses can skin it (Blender axes, z up). The morph closes the eye by bringing the upper
    lashes / lid down ~3 cm and lifting the lower edge of the eye (iris bottom, lower lash line) up to 0.046 units
    (0.42 cm). The game poses 41 / 42 move the upper-lid bones ~1 cm down but the lower-lid bones only 0.02 cm up, so
    the lift cannot be fitted (non-negative weights) and the iris bottom stayed visible under the closed lashes (lenko1
    in game). Lower the closing line instead: per eye, every mover's closed height drops by the lower edge's lift u(x)
    at its x (max lift in CLOSE_BIN bins, interpolated), scaled in by its own travel up to CLOSE_MOVE; the lifted
    vertices then stay where they are and the lid / lashes come down over them, CLOSE_EXTRA further so the fit's
    residual leaves no sliver of iris (lenko2 offline render)."""
    out = dd.copy()
    mag = np.linalg.norm(dd, axis=1)
    for side in (1.0, -1.0):
        eye = np.sign(pos[:, 0]) == side
        up = eye & (dd[:, 2] > 1e-4)
        if not up.any():
            continue
        x = pos[up, 0]
        edges = np.arange(x.min(), x.max() + CLOSE_BIN, CLOSE_BIN)
        cen, lift = [], []
        for a in edges:
            s = (x >= a) & (x < a + CLOSE_BIN)
            if s.any():
                cen.append(a + CLOSE_BIN / 2); lift.append(dd[up, 2][s].max())
        u = np.interp(pos[eye, 0], cen, lift)
        out[eye, 2] -= np.clip(mag[eye] / CLOSE_MOVE, 0, 1) * u + np.clip(-dd[eye, 2] / CLOSE_FALL, 0, 1) * CLOSE_EXTRA
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('model_dir', help='the folder with Lenko06.pmx and tex/')
    model_dir = Path(ap.parse_args().model_dir)
    d = lenko_pmx.load(model_dir / PMX)
    meta = d['meta']
    mats = [m['name'] for m in meta['materials']]
    names = [b['name'] for b in meta['bones']]
    report = {'coat_shortening': shorten_coat(d, mats, names)}
    anc = ancestors(meta)
    tri_mesh = classify(d, mats, names, anc)
    # bones: renamed, Blender axes
    hum = humanoid()
    missing = [k for k in hum if k not in names]
    assert not missing, f'humanoid bones missing: {missing}'
    def rename(n):
        if n in hum:
            return hum[n]
        if n.startswith('Chest'):
            return 'Bust' + n[5:]
        return n
    new_names = [rename(n) for n in names]
    assert len(set(new_names)) == len(new_names), 'bone names collide after renaming'
    bones = []
    for i, b in enumerate(meta['bones']):
        head = to_bl(b['pos'])
        tail = to_bl(meta['bones'][b['tail']]['pos']) if isinstance(b['tail'], int) and b['tail'] >= 0 else \
            head + (to_bl(b['tail']) if not isinstance(b['tail'], int) else 0)
        M = np.eye(4); M[:3, 3] = head
        bones.append({'name': new_names[i], 'parent': new_names[b['parent']] if b['parent'] >= 0 else None,
                      'head': head.tolist(), 'tail': np.asarray(tail, float).tolist(), 'matrix': M.tolist(),
                      'pmx_name': b['name'], 'fbx_name': b['name']})
    by = {b['name']: b for b in bones}
    for side in ('Left', 'Right'):            # finger tips: the distal bone continued by 0.75 of the previous segment
        for f in FINGERS:
            dd, ii = by[f'{side}{f}Distal'], by[f'{side}{f}Intermediate']
            tip = np.array(dd['head']) + 0.75 * (np.array(dd['head']) - np.array(ii['head']))
            bones.append({'name': f'{side}{f}Distal_end', 'parent': dd['name'], 'head': tip.tolist(), 'tail': tip.tolist(),
                          'matrix': dd['matrix'], 'pmx_name': None, 'fbx_name': None})
    # weights: FK leg bones onto their D bones
    idx = {n: i for i, n in enumerate(names)}
    BI = d['bi'].copy()
    for fk, dn in FK_TO_D.items():
        BI[BI == idx[fk]] = idx[dn]
    report['fk_leg_weights_moved'] = int(sum((d['bi'] == idx[fk]).sum() for fk in FK_TO_D))
    P = to_bl(d['pos']); N = to_bl(d['nrm']); UV = d['uv'].copy(); UV[:, 1] = 1 - UV[:, 1]
    F = d['faces'][:, [0, 2, 1]]                                      # reflection: reverse the winding
    gn = np.cross(P[F[:, 1]] - P[F[:, 0]], P[F[:, 2]] - P[F[:, 0]])
    agree = (gn * N[F].sum(1)).sum(1)
    report['winding_along_normals'] = [int((agree > 0).sum()), int((agree < 0).sum())]
    clamped = int(((UV < 0) | (UV > 1)).any(1).sum())
    UV = np.clip(UV, 0, 1)
    report['uv_clamped_vertices'] = clamped
    tex_of = {m['name']: meta['textures'][m['tex']].replace('\\', '/') for m in meta['materials']}
    out_meta, out_arr, vert_maps = [], {}, {}
    tri_mesh = np.array([t if t else '' for t in tri_mesh])
    for mesh in MESH_ORDER:
        sel = np.nonzero(tri_mesh == mesh)[0]
        assert len(sel), f'{mesh}: no triangles'
        t = F[sel]; fm = d['face_mat'][sel]
        mesh_mats = sorted(set(fm.tolist()))
        verts = np.unique(t)
        vmap = np.full(len(P), -1); vmap[verts] = np.arange(len(verts))
        # one loop per triangle corner
        lv = vmap[t.ravel()].astype(np.int32)
        wv, wg, ww = [], [], []
        for j, v in enumerate(verts):
            acc = {}
            for k in range(4):
                if BI[v, k] >= 0 and d['bw'][v, k] > 0:
                    acc[BI[v, k]] = acc.get(BI[v, k], 0) + d['bw'][v, k]
            for b, w in acc.items():
                wv.append(j); wg.append(int(b)); ww.append(w)
        out_arr.update({f'{mesh}__co': P[verts].astype(np.float32), f'{mesh}__loop_vertex': lv,
                        f'{mesh}__loop_normal': N[t.ravel()].astype(np.float32),
                        f'{mesh}__loop_uv': UV[t.ravel()].astype(np.float32),
                        f'{mesh}__tris': np.arange(3 * len(t), dtype=np.int32).reshape(-1, 3),
                        f'{mesh}__tri_material': np.array([mesh_mats.index(x) for x in fm], np.int32),
                        f'{mesh}__w_vertex': np.array(wv, np.int32), f'{mesh}__w_group': np.array(wg, np.int32),
                        f'{mesh}__w_weight': np.array(ww, np.float32)})
        out_meta.append({'name': mesh, 'key': mesh, 'groups': new_names,
                         'materials': [{'name': mats[x], 'texture_file': tex_of[mats[x]]} for x in mesh_mats],
                         'shape_keys_applied': [], 'vertices': len(verts), 'loops': 3 * len(t), 'triangles': len(t),
                         'hidden': False, 'pmx_materials': [mats[x] for x in mesh_mats]})
        vert_maps[mesh] = verts
        report[mesh] = {'vertices': int(len(verts)), 'triangles': int(len(t)), 'materials': [mats[x] for x in mesh_mats]}
    # face shape keys
    fv = vert_maps['Body']
    rows, kz, by_name = [], {}, {}
    for i, (name, (ids, off)) in enumerate(d['morphs'].items()):
        full = np.zeros((len(P), 3)); full[ids] = to_bl(off)
        dd = full[fv]
        mag = np.linalg.norm(dd, axis=1)
        outside = int(np.isin(ids, fv, invert=True).sum())
        rows.append({'index': i, 'name': name, 'moved': int((mag > 1e-6).sum()), 'max': float(mag.max()),
                     'outside_body': outside})
        if rows[-1]['moved']:
            kz[f'Body__{i}'] = dd.astype(np.float32)
        by_name[name] = dd
    x = P[fv, 0]
    sl = np.clip(0.5 + x / (2 * SIDE_RAMP), 0, 1)[:, None]
    nxt = len(rows)
    made = []
    base_keys = dict(by_name, まばたき=bone_blink(by_name['まばたき'], P[fv]))
    for base, mmd in {'blink': 'まばたき', 'mayu_up': '上', 'mayu_down': '下', 'kuchi_smile_1': '口角上げ'}.items():
        for side, f in (('L', sl), ('R', 1 - sl)):
            made.append((f'{base}_{side}', base_keys[mmd] * f, mmd))
    made.append(('kuchi_A', by_name['あ'], 'あ'))
    for name, dd, mmd in made:
        mag = np.linalg.norm(dd, axis=1)
        rows.append({'index': nxt, 'name': name, 'moved': int((mag > 1e-6).sum()), 'max': float(mag.max()), 'from': mmd})
        kz[f'Body__{nxt}'] = dd.astype(np.float32)
        nxt += 1
    report['face_keys'] = {r['name']: [r['moved'], round(r['max'], 4)] for r in rows[-len(made):]}
    report['morphs_touching_other_meshes'] = {r['name']: r['outside_body'] for r in rows if r.get('outside_body')}
    textures = {}
    for f in sorted(set(tex_of.values())):
        p = model_dir / f
        textures[f] = {'file': str(p), 'bytes': p.stat().st_size}
    dst = BUILD / 'source'
    dst.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(dst / 'source.npz', **out_arr)
    (dst / 'source.json').write_text(json.dumps({'pmx': PMX, 'bones': bones, 'meshes': out_meta, 'textures': textures,
                                                 'coat_shortening': report['coat_shortening'],
                                                 'dropped_materials': list(DROP_MATERIALS)},
                                                ensure_ascii=False, indent=1), encoding='utf-8')
    np.savez_compressed(dst / 'shapekeys.npz', **kz)
    (dst / 'shapekeys.json').write_text(json.dumps({'Body': rows}, ensure_ascii=False, indent=1), encoding='utf-8')
    (dst / 'source_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
    cs = report.pop('coat_shortening')
    print('coat shortening', {k: v for k, v in cs.items() if k not in ('sectors', 'bones')})
    for s in cs['sectors']:
        print('   ', s)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    print('bones', len(bones))


if __name__ == '__main__':
    main()
