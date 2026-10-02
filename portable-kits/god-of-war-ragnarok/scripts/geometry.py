"""Turn the Blender-fitted Karin meshes into one GoWR-space vertex/index set skinned to Kratos's rig."""
import json
import numpy as np
from scipy.spatial import cKDTree

def humanoid_map(spec):
    """VRM humanoid bone name -> target game bone index, from a rigspec (gowr/rigspec.py)."""
    c = spec['core']
    m = {'Hips': c['Hips'], 'Spine': c['Spine'], 'Chest': c['Chest'], 'Neck': c['Neck'], 'Head': c['Head']}
    for s in ('Left', 'Right'):
        d = spec[s]
        m.update({f'{s}Shoulder': d['clav'], f'{s}UpperArm': d['sh'], f'{s}LowerArm': d['el'], f'{s}Hand': d['wr'],
                  f'{s}UpperLeg': d['hip'], f'{s}LowerLeg': d['kn'], f'{s}Foot': d['an'], f'{s}ToeBase': d['toe']})
        for f in ('Index', 'Middle', 'Ring', 'Little', 'Thumb'):
            for seg, b in zip(('Proximal', 'Intermediate', 'Distal'), d[f][:3]):
                m[f'{s}{f}{seg}'] = b
    return m


MAIN = None
MAX_INF = 10

ATLAS = {  # material -> (u offset, v offset) of its 2048 quadrant in the 4096 atlas (v grows downward)
    'Karin_Face': (0.0, 0.0), 'Karin_Body': (0.5, 0.0),
    'Karin_Hair': (0.0, 0.5), 'Karin_Hair_Transparent': (0.0, 0.5),
    'Karin_Costume': (0.5, 0.5),
}
DROP_MATERIALS = {'Karin_Alpha'}   # blush/highlight overlays need alpha blending the skin shader lacks


def b2g(a):
    a = np.asarray(a, np.float64)
    return np.stack([-a[..., 0], a[..., 2], a[..., 1]], -1)


def bone_resolver(karin_bones, MAIN):
    cache = {}
    def resolve(name):
        if name in cache:
            return cache[name]
        n = name
        while n is not None and n not in MAIN:
            n = karin_bones.get(n, {}).get('parent')
        cache[name] = MAIN[n] if n is not None else MAIN['Hips']
        return cache[name]
    return resolve


def load_mesh(fit_dir, name):
    d = np.load(f'{fit_dir}/{name}.npz')
    return {k: d[k] for k in d.files}


def vertex_weights(m, groups, resolve):
    """Per original vertex: dict kratos_bone -> weight."""
    nv = len(m['V'])
    acc = [dict() for _ in range(nv)]
    for v, g, w in zip(m['w_vert'], m['w_group'], m['w_weight']):
        kb = resolve(groups[g])
        acc[v][kb] = acc[v].get(kb, 0.0) + float(w)
    return acc


def normalize_inf(d, hips):
    items = sorted(((b, w) for b, w in d.items() if w > 1e-4), key=lambda t: -t[1])[:MAX_INF]
    if not items:
        items = [(hips, 1.0)]
    s = sum(w for _, w in items)
    return [(b, w / s) for b, w in items]


def build(fit_dir, karin_bones_json, spec_json, skirt_leg_blend=0.6):
    summ = json.load(open(f'{fit_dir}/summary.json'))
    kb = json.load(open(karin_bones_json))['bones']
    spec = json.load(open(spec_json))
    MAIN = humanoid_map(spec)
    resolve = bone_resolver(kb, MAIN)
    meshes = {n: load_mesh(fit_dir, n) for n in summ['meshes']}
    weights = {n: vertex_weights(meshes[n], summ['meshes'][n]['groups'], resolve) for n in meshes}

    # skirt: blend rigid-hips weights with the nearest body weights so it follows the thighs
    body = meshes['body_2']
    tree = cKDTree(body['V'])
    hips_leg = {MAIN[k] for k in ('Hips', 'LeftUpperLeg', 'RightUpperLeg', 'LeftLowerLeg', 'RightLowerLeg')}
    if 'skirt' in meshes:
        sk = meshes['skirt']
        dist, idx = tree.query(sk['V'], k=4)
        for v in range(len(sk['V'])):
            mix = {}
            ws = 1.0 / np.maximum(dist[v], 1e-4)
            ws /= ws.sum()
            for j, wj in zip(idx[v], ws):
                for b, w in weights['body_2'][j].items():
                    if b in hips_leg:
                        mix[b] = mix.get(b, 0.0) + w * wj
            tot = sum(mix.values())
            if tot <= 0:
                continue
            new = {b: w / tot * skirt_leg_blend for b, w in mix.items()}
            for b, w in weights['skirt'][v].items():
                new[b] = new.get(b, 0.0) + w * (1.0 - skirt_leg_blend)
            weights['skirt'][v] = new

    P, N, UV, INF, IDX = [], [], [], [], []
    stats = {}
    for name, m in meshes.items():
        mats = summ['meshes'][name]['materials']
        keep = np.array([mats[t] not in DROP_MATERIALS for t in m['tri_mat']])
        tl = m['tri_loops'][keep]
        tmat = m['tri_mat'][keep]
        loops = tl.reshape(-1)
        lmat = np.repeat(tmat, 3)
        lv = m['loop_v'][loops]
        ln = m['loop_n'][loops]
        luv = m['loop_uv'][loops].astype(np.float64)
        off = np.array([ATLAS[mats[t]] for t in lmat])
        u = np.clip(luv[:, 0], 0, 1) * 0.5 + off[:, 0]
        v = (1.0 - np.clip(luv[:, 1], 0, 1)) * 0.5 + off[:, 1]
        auv = np.stack([u, v], 1)
        key = np.concatenate([lv[:, None].astype(np.float64), np.round(auv * 65535), np.round(ln * 512)], 1)
        uniq, inv = np.unique(key, axis=0, return_inverse=True)
        inv = inv.reshape(-1)
        first = np.zeros(len(uniq), np.int64)
        first[inv[::-1]] = np.arange(len(inv))[::-1]
        base = sum(len(p) for p in P)
        vid = lv[first]
        P.append(b2g(m['V'][vid]))
        nn = b2g(ln[first]); nn /= np.maximum(np.linalg.norm(nn, axis=1, keepdims=True), 1e-8)
        N.append(nn)
        UV.append(auv[first])
        INF.extend(normalize_inf(weights[name][int(i)], MAIN['Hips']) for i in vid)
        IDX.append(inv.reshape(-1, 3) + base)
        stats[name] = dict(verts=len(uniq), tris=len(tl), dropped=int((~keep).sum()), vbase=base)
    part_of_tri = np.concatenate([np.full(len(i), k) for k, i in enumerate(IDX)])
    P = np.concatenate(P); N = np.concatenate(N); UV = np.concatenate(UV); IDX = np.concatenate(IDX)
    T = tangents(P, N, UV, IDX)
    # GoWR treats clockwise triangles (relative to the outward normal) as front faces; Blender data is CCW
    IDX = IDX[:, [0, 2, 1]]
    return dict(P=P, N=N, T=T, UV=UV, INF=INF, IDX=IDX, stats=stats, part_of_tri=part_of_tri)


def subset(geo, part_names):
    """Geometry restricted to the named source meshes, re-indexed from zero."""
    names = list(geo['stats'])
    tri = np.zeros(len(geo['IDX']), bool)
    cx = geo['P'][geo['IDX']].mean(1)[:, 0]
    for n in part_names:
        side = None
        if n.endswith('_L') or n.endswith('_R'):     # virtual half part: game left = -X
            n, side = n[:-2], n[-1]
        sel = geo['part_of_tri'] == names.index(n)
        if side == 'L': sel &= cx < 0
        if side == 'R': sel &= cx >= 0
        tri |= sel
    idx = geo['IDX'][tri]
    used = np.unique(idx)
    remap = np.full(len(geo['P']), -1, np.int64); remap[used] = np.arange(len(used))
    return dict(P=geo['P'][used], N=geo['N'][used], T=geo['T'][used], UV=geo['UV'][used],
                INF=[geo['INF'][i] for i in used], IDX=remap[idx])


def tangents(P, N, UV, IDX):
    T = np.zeros_like(P)
    p0, p1, p2 = P[IDX[:, 0]], P[IDX[:, 1]], P[IDX[:, 2]]
    t0, t1, t2 = UV[IDX[:, 0]], UV[IDX[:, 1]], UV[IDX[:, 2]]
    e1, e2 = p1 - p0, p2 - p0
    d1, d2 = t1 - t0, t2 - t0
    r = d1[:, 0] * d2[:, 1] - d2[:, 0] * d1[:, 1]
    r = np.where(np.abs(r) < 1e-12, 1e-12, r)
    tan = (e1 * d2[:, 1:2] - e2 * d1[:, 1:2]) / r[:, None]
    for k in range(3):
        np.add.at(T, IDX[:, k], tan)
    T = T - N * (T * N).sum(1, keepdims=True)
    n = np.linalg.norm(T, axis=1, keepdims=True)
    fallback = np.cross(N, np.array([0.0, 1.0, 0.0]))
    T = np.where(n > 1e-8, T / np.maximum(n, 1e-12), fallback)
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-8)
    return T


def merge(geos):
    """Concatenate geometry dicts (vertex/index sets) into one."""
    out = dict(P=[], N=[], T=[], UV=[], INF=[], IDX=[])
    base = 0
    for g in geos:
        for k in ('P', 'N', 'T', 'UV'):
            out[k].append(g[k])
        out['INF'].extend(g['INF'])
        out['IDX'].append(g['IDX'] + base)
        base += len(g['P'])
    for k in ('P', 'N', 'T', 'UV', 'IDX'):
        out[k] = np.concatenate(out[k])
    return out
