#!/usr/bin/env python3
"""Skin a replacement's legs the way the game skins its own (needs numpy and scipy).

The game never binds a leg straight to the knee bone: every vanilla leg spreads it over helper bones (Rise of the Ronin
female skeleton, bone ids: thigh 129/85 with 3, knee 87/89, calf 89/91, shin 91/93, ankle 93 + 7, foot 7 with toe 25;
right side = the paired ids). A mod that puts everything below the knee on one bone gets feet that ignore the ankle
and calves that cross when running.

  reference  vanilla models -> npz of per-vertex bind positions and leg-chain weights ('body' above the ankle, 'wear'
             below: the game's legwear and shoes carry the ankle/foot split)
  apply      redistribute the leg share of one submesh like the nearest vanilla leg; everything that is not on a leg
             bone (hips, tail, cloth) stays as it is; new palette bones get native binds (inv of the model's own G1MS)
  check      read-back: what changed besides blend bytes, palette and binds; weight sums; rest pose; offline poses

Edits are in place (no gust round trip): only BLENDWEIGHT/BLENDINDICES bytes of the edited vertices change, the
palette grows, MM1G gets the new matrices and FM1G its count. Bone numbers are palette ids (what gust calls bone_<id>).
The defaults (chains, ankle blend heights, poses) are the Ronin female skeleton's; measure again for another one.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import g1m_tool  # noqa: E402

LEG_L = (3, 85, 129, 5, 87, 89, 91, 93, 111, 133, 7, 25)
LEG_R = (4, 86, 130, 6, 88, 90, 92, 94, 112, 134, 8, 26)
FOOT_BLEND = (-86.0, -91.0)        # bind-space y where the reference fades from base body to legwear (cm)
NEIGHBOURS = 6
SLOTS, QUANT = 8, 2048             # 8 influences, weights in steps of 2^-11 so the 8 stored weights sum to exactly 1
BANDS = (('thigh', -20, -40), ('knee', -40, -52), ('calf', -52, -70), ('shin', -70, -84), ('ankle', -84, -91),
         ('foot', -91, -110))
POSES = {'walk': {3: ('x', -40), 5: ('x', 80), 7: ('x', 30), 4: ('x', 30), 8: ('x', -30)},
         'squat': {3: ('x', -95), 4: ('x', -95), 5: ('x', 120), 6: ('x', 120), 7: ('x', -25), 8: ('x', -25)},
         'ankle': {7: ('x', 35), 8: ('x', -35)},
         'shin_twist': {7: ('y', 30), 8: ('y', -30)}}
NP_TYPES = {0x00: ('<f4', 1), 0x01: ('<f4', 2), 0x02: ('<f4', 3), 0x03: ('<f4', 4), 0x05: ('u1', 4), 0x07: ('<u2', 4),
            0x09: ('<u4', 4), 0x0A: ('<f2', 2), 0x0B: ('<f2', 4), 0x0D: ('u1', 4)}


# ---- vertex access -----------------------------------------------------------------------------------------------

def buffer_attrs(model, vb):
    for s in model.attributes:
        if vb in s['buffers']:
            return {f"{a['semantic']}{a['layer']}": a for a in s['attrs'] if s['buffers'][a['buffer']] == vb}
    raise g1m_tool.G1MError(f'no attribute set describes vertex buffer {vb}')


def read_attr(model, vb, attr):
    b = model.vertex_buffers[vb]
    dtype, n = NP_TYPES[attr['type']]
    raw = np.frombuffer(model.data, np.uint8, b['stride'] * b['count'], b['offset']).reshape(b['count'], b['stride'])
    width = np.dtype(dtype).itemsize * n
    out = raw[:, attr['offset']:attr['offset'] + width].copy().view(dtype).reshape(b['count'], n).astype(float)
    return out / 255 if attr['type'] == 0x0D else out


def blend(model, vb):
    """(palette slot indices (n, k), weight columns (n, m)) as stored."""
    at = buffer_attrs(model, vb)
    idx = np.concatenate([read_attr(model, vb, at[k]) for k in ('BLENDINDICES0', 'BLENDINDICES1') if k in at], 1).astype(int)
    w = [read_attr(model, vb, at[k]) for k in ('BLENDWEIGHT0', 'BLENDWEIGHT1') if k in at]
    return idx, (np.concatenate(w, 1) if w else np.zeros((len(idx), 0)))


def effective(idx, w, bone_of_slot, threshold=1e-6):
    """Per vertex {bone id: weight} as the vertex shader sees it: explicit weights, the last influence takes the rest."""
    k = idx.shape[1]
    full = np.zeros((len(idx), k))
    full[:, :min(k - 1, w.shape[1])] = w[:, :k - 1]
    full[:, k - 1] = 1 - full[:, :k - 1].sum(1)
    out = []
    for row_i, row_w in zip(idx, full):
        d = {}
        for b, x in zip(row_i, row_w):
            if x > threshold:
                bone = bone_of_slot[int(b)]
                d[bone] = d.get(bone, 0) + float(x)
        out.append(d)
    return out


def stored(idx, w, bone_of_slot, threshold=1e-4):
    """Per vertex {bone id: weight} from the stored weights (the reference reader; remainder only if a column is missing)."""
    if w.shape[1] < idx.shape[1]:
        w = np.concatenate([w, 1 - w.sum(1, keepdims=True), np.zeros((len(idx), idx.shape[1] - w.shape[1] - 1))], 1)
    out = []
    for row_i, row_w in zip(idx, w):
        d = {}
        for b, x in zip(row_i, row_w):
            if x > threshold:
                bone = bone_of_slot[int(b)]
                d[bone] = d.get(bone, 0) + float(x)
        out.append(d)
    return out


def slot_map(model, palette):
    """stored blend index -> bone id (palette index x 3, the KT convention)."""
    return {3 * i: e['joint'] for i, e in enumerate(model.palettes[palette])}


def worlds(model):
    joints, by_id = g1m_tool.skeleton(model)
    return {b: np.array(joints[j]['world']) for b, j in by_id.items()}, joints, by_id


# ---- reference ---------------------------------------------------------------------------------------------------

def model_vertices(model):
    """Bind positions and stored weights of every drawn vertex of every visible skinned submesh."""
    P, W = [], []
    for s in model.submeshes:
        if g1m_tool.is_hidden(model, s):
            continue
        at = buffer_attrs(model, s['vertex_buffer'])
        if 'BLENDINDICES0' not in at:
            continue
        _, _, ids = g1m_tool.submesh_indices(model, s)
        used = np.unique(ids)
        if len(used) < 4:
            continue
        pos = read_attr(model, s['vertex_buffer'], at['POSITION0'])[:, :3]
        idx, w = blend(model, s['vertex_buffer'])
        rows = stored(idx[used], w[used], slot_map(model, s['palette']))
        P.append(pos[used]); W += rows
    return (np.concatenate(P) if P else np.zeros((0, 3))), W


def leg_matrix(W, chains):
    M = np.zeros((len(W), 2, len(chains[0])))
    for i, d in enumerate(W):
        for s, cols in enumerate(chains):
            for k, b in enumerate(cols):
                M[i, s, k] = d.get(b, 0.0)
    return M


def band_table(P, M, chains, side_min=0.3):
    out = {}
    side = M.sum(2)
    for name, hi, lo in BANDS:
        sel = (P[:, 1] <= hi) & (P[:, 1] > lo) & (P[:, 0] > 0.5) & (side[:, 0] > side_min)
        if sel.any():
            mean = (M[sel, 0] / side[sel, 0:1]).mean(0)
            out[name] = {'n': int(sel.sum()), **{f'b{chains[0][k]}': round(float(mean[k]), 3) for k in np.argsort(-mean)[:5]}}
    return out


def cmd_reference(args):
    chains = (tuple(args.left), tuple(args.right))
    skel_model = g1m_tool.parse(Path(args.skeleton).read_bytes())
    ref_worlds, _, _ = worlds(skel_model)
    out, report = {}, {'inputs': {}, 'bands': {}, 'chains': chains}
    for kind, files in (('body', args.body), ('wear', args.wear)):
        P, W = [], []
        for f in files:
            data = Path(f).read_bytes()
            model = g1m_tool.parse(data)
            own, _, _ = worlds(model)
            err = max(float(np.abs(own[b][:3, 3] - ref_worlds[b][:3, 3]).max()) for b in chains[0] + chains[1])
            if err > args.tolerance:
                raise SystemExit(f'{Path(f).name}: leg bones differ from {Path(args.skeleton).name} by {err:.4f}')
            p, w = model_vertices(model)
            P.append(p); W += w
            report['inputs'][Path(f).name] = {'sha256': hashlib.sha256(data).hexdigest(), 'vertices': len(p),
                                              'leg_bone_offset_max': err}
        P = np.concatenate(P)
        M = leg_matrix(W, chains)
        out[kind + '_pos'] = P.astype(np.float32)
        out[kind + '_w'] = M.astype(np.float32)
        report['bands'][kind] = band_table(P, M, chains)
    dest = Path(args.output)
    if dest.exists():
        raise SystemExit(f'refusing to overwrite {dest}')
    np.savez_compressed(dest, chains=np.array(chains), **out)
    print(json.dumps(report, indent=1))


# ---- apply -------------------------------------------------------------------------------------------------------

def smoothstep(x):
    t = np.clip(x, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def leg_distributions(p, ref, foot_blend=FOOT_BLEND, k=NEIGHBOURS):
    """(n, 2, chain length): per vertex and side the game's split of a leg share over that side's chain (rows sum to 1),
    and the distance to the nearest reference vertex of that side."""
    from scipy.spatial import cKDTree
    n_chain = ref['body_w'].shape[2]
    out, dist = np.zeros((len(p), 2, n_chain)), np.zeros((len(p), 2))
    t = smoothstep((foot_blend[0] - p[:, 1]) / (foot_blend[0] - foot_blend[1]))
    for s, sign in ((0, 1.0), (1, -1.0)):
        for kind, wk in (('body', 1 - t), ('wear', t)):
            P = ref[kind + '_pos'].astype(float); M = ref[kind + '_w'][:, s].astype(float); tot = M.sum(1)
            keep = (tot > 0.3) & (sign * P[:, 0] > 0)
            P, M = P[keep], M[keep] / tot[keep, None]
            d, i = cKDTree(P).query(p, k=k)
            w = 1 / (d + 0.5); w /= w.sum(1, keepdims=True)
            out[:, s] += wk[:, None] * (w[:, :, None] * M[i]).sum(1)
            dist[:, s] += wk * d[:, 0]
    return out, dist


def quantise(d, slots=SLOTS, q=QUANT):
    items = sorted(((b, w) for b, w in d.items() if w > 1e-4), key=lambda x: -x[1])[:slots]
    s = sum(w for _, w in items)
    items = [(b, w / s) for b, w in items if w / s >= 1 / 512]
    s = sum(w for _, w in items)
    items = [(b, w / s) for b, w in items]
    n = [int(round(w * q)) for _, w in items]
    n[0] = q - sum(n[1:])
    return [(b, x / q) for (b, _), x in zip(items, n)]


def retarget(P, W, tgt_worlds, ref_worlds):
    """Carry bind positions from the target skeleton into the reference skeleton's space, bone by bone."""
    M = {b: ref_worlds[b] @ np.linalg.inv(tgt_worlds[b]) for b in tgt_worlds if b in ref_worlds}
    out = np.zeros_like(P)
    for i, (p, d) in enumerate(zip(P, W)):
        tot = sum(w for b, w in d.items() if b in M)
        out[i] = sum(w * (M[b] @ np.append(p, 1.0))[:3] for b, w in d.items() if b in M) / max(1e-9, tot)
    return out


def write_attr(buf, model, vb, attr, values, rows):
    b = model.vertex_buffers[vb]
    dtype, n = NP_TYPES[attr['type']]
    view = np.frombuffer(buf, np.uint8, b['stride'] * b['count'], b['offset']).reshape(b['count'], b['stride'])
    width = np.dtype(dtype).itemsize * n
    vals = np.asarray(values, float)
    if attr['type'] == 0x0D:
        vals = np.round(vals * 255)
    cast = vals.astype(dtype)
    if not np.allclose(cast.astype(float), vals, atol=0 if dtype in ('u1', '<u2', '<u4') else 1e-6):
        raise g1m_tool.G1MError(f"{attr['semantic']}{attr['layer']}: values are not exactly representable in {dtype}")
    view[rows, attr['offset']:attr['offset'] + width] = cast.reshape(len(rows), n).view(np.uint8).reshape(len(rows), width)


def reskin(data, sub_id, ref, ref_skeleton=None, chains=(LEG_L, LEG_R), foot_blend=FOOT_BLEND):
    """New G1M bytes with the submesh's legs redistributed, plus a report."""
    model = g1m_tool.parse(data)
    sub = model.submeshes[sub_id]
    vb, pal = sub['vertex_buffer'], sub['palette']
    _, _, ids = g1m_tool.submesh_indices(model, sub)
    rows = np.unique(ids)
    for other in model.submeshes:
        if other['id'] != sub_id and other['vertex_buffer'] == vb and not g1m_tool.is_hidden(model, other):
            _, _, oids = g1m_tool.submesh_indices(model, other)
            if np.intersect1d(rows, np.unique(oids)).size:
                raise SystemExit(f'submesh {other["id"]} draws vertices of the same buffer; refusing to reweight them')
    at = buffer_attrs(model, vb)
    idx, w = blend(model, vb)
    if idx.shape[1] != SLOTS or w.shape[1] < SLOTS - 1:
        raise SystemExit(f'expected {SLOTS} blend indices and at least {SLOTS - 1} stored weights, got {idx.shape[1]} / {w.shape[1]}')
    W = effective(idx[rows], w[rows], slot_map(model, pal))
    P = read_attr(model, vb, at['POSITION0'])[rows, :3]
    tgt_worlds, _, _ = worlds(model)
    Pref = P if ref_skeleton is None else retarget(P, W, tgt_worlds, worlds(g1m_tool.parse(ref_skeleton))[0])
    leg = set(chains[0]) | set(chains[1])
    share = np.array([[sum(d.get(b, 0) for b in cols) for cols in chains] for d in W])
    legv = share.sum(1) > 0
    D, dist = leg_distributions(Pref, ref, foot_blend)
    newW = []
    for v, d in enumerate(W):
        if not legv[v]:
            newW.append(d); continue
        nd = {b: x for b, x in d.items() if b not in leg}
        for s, cols in enumerate(chains):
            if share[v, s] > 0:
                for k, b in enumerate(cols):
                    if D[v, s, k] > 0:
                        nd[b] = nd.get(b, 0) + share[v, s] * D[v, s, k]
        newW.append(nd)
    qW = [quantise(d) for d in newW]

    old = model.palettes[pal]
    palette = [e['joint'] for e in old]
    used = sorted({b for t in qW for b, _ in t})
    new_bones = [b for b in used if b not in palette]
    missing = [b for b in new_bones if b not in tgt_worlds]
    if missing:
        raise SystemExit(f'bones {missing} are not in this model\'s skeleton')
    mm_count = len(g1m_tool.binds(model))
    joints = [dict(e) for e in old] + [{'g1mm': mm_count + i, 'physics': 0, 'joint': b, 'external': False}
                                       for i, b in enumerate(new_bones)]
    palette += new_bones
    if NP_TYPES[at['BLENDINDICES0']['type']][0] == 'u1' and 3 * (len(palette) - 1) > 255:
        raise SystemExit(f'palette of {len(palette)} bones does not fit 8-bit blend indices')
    lookup = {b: i for i, b in enumerate(palette)}
    BI = np.zeros((len(qW), SLOTS)); BW = np.zeros((len(qW), SLOTS))
    for v, t in enumerate(qW):
        BI[v, :] = lookup[t[0][0]] * 3
        for j, (b, x) in enumerate(t):
            BI[v, j] = lookup[b] * 3; BW[v, j] = x

    buf = bytearray(data)
    for name, values in (('BLENDINDICES0', BI[:, :4]), ('BLENDINDICES1', BI[:, 4:]),
                         ('BLENDWEIGHT0', BW[:, :4]), ('BLENDWEIGHT1', BW[:, 4:4 + NP_TYPES[at['BLENDWEIGHT1']['type']][1]])):
        write_attr(buf, model, vb, at[name], values, rows)
    model = g1m_tool.parse(bytes(buf))
    pals = [list(p) for p in model.palettes]
    pals[pal] = joints
    out = g1m_tool.replace_section(bytes(buf), model, 'JOINT_PALETTES', g1m_tool.palettes_body(pals))
    if new_bones:
        out, _ = g1m_tool.append_binds(out, [g1m_tool.native_bind(tgt_worlds[b].tolist()) for b in new_bones])
    report = {'submesh': sub_id, 'vertices': len(rows), 'leg_vertices': int(legv.sum()),
              'palette_before': [e['joint'] for e in old], 'palette_added': new_bones,
              'ref_dist_p50': round(float(np.median(dist[legv].min(1))), 2) if legv.any() else None,
              'ref_dist_p95': round(float(np.percentile(dist[legv].min(1), 95)), 2) if legv.any() else None,
              'bands_before': band_table(Pref[legv], leg_matrix([W[i] for i in np.nonzero(legv)[0]], chains), chains, 0),
              'bands_after': band_table(Pref[legv], leg_matrix([dict(qW[i]) for i in np.nonzero(legv)[0]], chains), chains, 0)}
    return out, report


def cmd_apply(args):
    data = Path(args.input).read_bytes()
    ref = dict(np.load(args.reference))
    chains = tuple(tuple(int(x) for x in row) for row in ref.pop('chains')) if 'chains' in ref else (LEG_L, LEG_R)
    rs = Path(args.reference_skeleton).read_bytes() if args.reference_skeleton else None
    out, report = reskin(data, args.submesh, ref, rs, chains, (args.foot_blend[0], args.foot_blend[1]))
    dest = Path(args.output)
    if dest.exists():
        raise SystemExit(f'refusing to overwrite {dest}')
    dest.write_bytes(out)
    report.update(input_sha256=hashlib.sha256(data).hexdigest(), output_sha256=hashlib.sha256(out).hexdigest())
    print(json.dumps(report, indent=1))


# ---- check -------------------------------------------------------------------------------------------------------

AXES = {'x': (1, 0, 0), 'y': (0, 1, 0), 'z': (0, 0, 1)}


def rotation(axis, deg):
    x, y, z = AXES[axis]
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    R = np.eye(4)
    R[:3, :3] = c * np.eye(3) + s * np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]]) + (1 - c) * np.outer((x, y, z), (x, y, z))
    return R


def posed_worlds(joints, by_id, pose):
    """Rotate the given bones (by id) about their own local axes; children follow."""
    rest = [np.array(j['world']) for j in joints]
    store_to_id = {j: b for b, j in by_id.items()}
    out = []
    for i, j in enumerate(joints):
        local = rest[i] if j['parent'] < 0 else np.linalg.inv(rest[j['parent']]) @ rest[i]
        if store_to_id.get(i) in pose:
            local = local @ rotation(*pose[store_to_id[i]])
        out.append(local if j['parent'] < 0 else out[j['parent']] @ local)
    return {b: out[j] for b, j in by_id.items()}


def skin(model, sub, world_by_id):
    vb, pal = sub['vertex_buffer'], sub['palette']
    at = buffer_attrs(model, vb)
    P = read_attr(model, vb, at['POSITION0'])[:, :3]
    idx, w = blend(model, vb)
    k = idx.shape[1]
    full = np.zeros((len(idx), k))
    full[:, :min(k - 1, w.shape[1])] = w[:, :k - 1]
    full[:, k - 1] = 1 - full[:, :k - 1].sum(1)
    mats = np.array(g1m_tool.binds(model))
    Ph = np.concatenate([P, np.ones((len(P), 1))], 1)
    out = np.zeros((len(P), 3))
    for slot, e in enumerate(model.palettes[pal]):
        sel = ((idx == 3 * slot) * full).sum(1)
        if sel.any():
            T = world_by_id[e['joint']] @ mats[e['g1mm']].T
            out += sel[:, None] * (Ph @ T.T)[:, :3]
    return P, out


def stretch(P0, P1, tris):
    e = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    l0 = np.linalg.norm(P0[e[:, 0]] - P0[e[:, 1]], axis=1); l1 = np.linalg.norm(P1[e[:, 0]] - P1[e[:, 1]], axis=1)
    r = l1[l0 > 1e-4] / l0[l0 > 1e-4]
    return {'max': round(float(r.max()), 3), 'p999': round(float(np.percentile(r, 99.9)), 3)}


def cmd_check(args):
    a, b = Path(args.before).read_bytes(), Path(args.after).read_bytes()
    m0, m1 = g1m_tool.parse(a), g1m_tool.parse(b)
    s0, s1 = m0.submeshes[args.submesh], m1.submeshes[args.submesh]
    errors = []
    changed = sorted(k for k in m0.chunks if a[m0.chunks[k].offset:m0.chunks[k].end] != b[m1.chunks[k].offset:m1.chunks[k].end])
    if set(changed) - {'GM1G', 'MM1G', 'FM1G'}:
        errors.append(f'chunks changed besides GM1G/MM1G/FM1G: {changed}')
    for x, y in zip(m0.sections, m1.sections):
        if x['name'] in ('JOINT_PALETTES', 'VERTEX_BUFFERS'):
            continue
        if a[x['offset']:x['offset'] + x['size']] != b[y['offset']:y['offset'] + y['size']]:
            errors.append(f"G1MG section {x['name']} changed")
    blend_cols = set()
    for v, (x, y) in enumerate(zip(m0.vertex_buffers, m1.vertex_buffers)):
        r0 = np.frombuffer(a, np.uint8, x['stride'] * x['count'], x['offset']).reshape(x['count'], x['stride'])
        r1 = np.frombuffer(b, np.uint8, y['stride'] * y['count'], y['offset']).reshape(y['count'], y['stride'])
        mask = np.ones(x['stride'], bool)
        if v == s0['vertex_buffer']:
            for name, at in buffer_attrs(m0, v).items():
                if name.startswith('BLEND'):
                    width = np.dtype(NP_TYPES[at['type']][0]).itemsize * NP_TYPES[at['type']][1]
                    mask[at['offset']:at['offset'] + width] = False
                    blend_cols.add(name)
        if not np.array_equal(r0[:, mask], r1[:, mask]):
            errors.append(f'vertex buffer {v}: bytes other than blend weights/indices changed')
    p0, p1 = m0.palettes[s0['palette']], m1.palettes[s1['palette']]
    if p1[:len(p0)] != p0:
        errors.append('existing palette entries changed')
    for i, (x, y) in enumerate(zip(m0.palettes, m1.palettes)):
        if i != s0['palette'] and x != y:
            errors.append(f'palette {i} changed')
    B0, B1 = g1m_tool.binds(m0), g1m_tool.binds(m1)
    if B1[:len(B0)] != B0:
        errors.append('existing binds changed')
    W1, joints, by_id = worlds(m1)
    new_err = max((float(np.abs(np.array(B1[e['g1mm']]) - np.array(g1m_tool.native_bind(W1[e['joint']].tolist()))).max())
                   for e in p1[len(p0):]), default=0.0)
    if new_err > 1e-4:
        errors.append(f'new binds are not native (max error {new_err})')
    idx, w = blend(m1, s1['vertex_buffer'])
    _, _, ids = g1m_tool.submesh_indices(m1, s1)
    rows = np.unique(ids)
    sums = w[rows].sum(1)
    tris = np.array(ids).reshape(-1, 3)
    W0, j0, b0 = worlds(m0)
    P, rest0 = skin(m0, s0, W0)
    _, rest1 = skin(m1, s1, W1)
    poses = {}
    for name, pose in POSES.items():
        _, q0 = skin(m0, s0, posed_worlds(j0, b0, pose))
        _, q1 = skin(m1, s1, posed_worlds(joints, by_id, pose))
        foot = P[:, 1] < args.foot_y
        poses[name] = {'stretch_before': stretch(rest0, q0, tris), 'stretch_after': stretch(rest1, q1, tris),
                       'foot_moved_before': round(float(np.linalg.norm(q0[foot] - rest0[foot], axis=1).mean()), 2) if foot.any() else None,
                       'foot_moved_after': round(float(np.linalg.norm(q1[foot] - rest1[foot], axis=1).mean()), 2) if foot.any() else None}
    rest_diff = float(np.abs(rest0[rows] - rest1[rows]).max())
    if rest_diff > args.rest_tolerance:
        errors.append(f'rest pose moved by {rest_diff:.4f}')
    report = {'chunks_changed': changed, 'blend_attributes': sorted(blend_cols), 'palette_added': [e['joint'] for e in p1[len(p0):]],
              'new_bind_max_error': new_err, 'stored_weight_sum': [round(float(sums.min()), 6), round(float(sums.max()), 6)],
              'rest_pose_max_diff': round(rest_diff, 5), 'poses': poses, 'errors': errors,
              'note': 'offline FK treats helper bones as rigid children of their parents; the game animates them, so pose '
                      'numbers are hints, not a runtime result'}
    print(json.dumps(report, indent=1))
    return 1 if errors else 0


def main(argv=None):
    ids = lambda s: [int(x) for x in s.split(',')]  # noqa: E731
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('reference', help='vanilla legs -> npz')
    p.add_argument('--body', nargs='+', required=True, help='base body G1M(s), e.g. 0x4ba258df.g1m')
    p.add_argument('--wear', nargs='+', required=True, help='legwear / shoes G1M(s), e.g. 0x32460701.g1m 0x6277d7a9.g1m')
    p.add_argument('--skeleton', required=True, help='the G1M whose bind space the reference must share (the target outfit)')
    p.add_argument('--left', type=ids, default=list(LEG_L)); p.add_argument('--right', type=ids, default=list(LEG_R))
    p.add_argument('--tolerance', type=float, default=1e-3); p.add_argument('--output', required=True)
    p = sub.add_parser('apply', help='redistribute one submesh\'s leg weights')
    p.add_argument('input'); p.add_argument('--submesh', type=int, required=True)
    p.add_argument('--reference', required=True, help='npz from `reference`')
    p.add_argument('--reference-skeleton', help='G1M of the reference bind space when the target skeleton differs')
    p.add_argument('--foot-blend', type=float, nargs=2, default=list(FOOT_BLEND))
    p.add_argument('--output', required=True)
    p = sub.add_parser('check', help='read-back of an `apply` result')
    p.add_argument('before'); p.add_argument('after'); p.add_argument('--submesh', type=int, required=True)
    p.add_argument('--foot-y', type=float, default=-91.0, help='vertices below this bind-space y count as foot')
    p.add_argument('--rest-tolerance', type=float, default=0.05)
    args = ap.parse_args(argv)
    return {'reference': cmd_reference, 'apply': cmd_apply, 'check': cmd_check}[args.cmd](args) or 0


if __name__ == '__main__':
    sys.exit(main())
