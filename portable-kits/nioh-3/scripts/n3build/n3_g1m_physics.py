"""Add NUNO type-4 bone-chain physics to a Nioh 3 G1M: new SM1G joints, a type-4 ONUN subchunk, FM1G counts.

Format facts this relies on (v2.0.0.2, see tools/nuno4.py):
- SM1G: header (magic, version, size, joint offset, u16 1, u16 0, u16 joints, u16 id count, u32 groups), id table
  (u16 per bone id), group table (u16: last storage index of the base group, then points-1 of each type-4 entry,
  in entry order), padding to 4, joints (48 bytes: scale 3f, parent i32, quat x y z w, position 3f, 1.0).
- A type-4 chain's joints are contiguous, all parented to the anchor bone; joint world position = chain point,
  local x axis = direction to the next point (the last joint copies the previous one).
- The entry's short list after the points indexes LLOC collision entries of the same model.
- FM1G +12 = SM1G groups (1 + type-4 entries), +16 = joints, +136 = bone id space, +96 / +100 = LLOC entries /
  primitives, and type-4 totals (all three vanilla samples match): +276 entries, +280 / +292 points, +284 / +328
  chains, +288 LLOC-list words, +320 = 156 x entries, +332 anchor-block bytes. Leaving them 0 crashes the game.
- LLOC: (magic, version, size, 1), subchunk (0x20001, size, entries), entry = (u32 flags, u32 n, n x 112-byte
  primitive: u32 shape, u32 bone id, ... size, rotation, offset in bone space).
- Chains that share a vertex go into one multi-chain entry (vanilla hair: 1-8 chains per entry, same anchor); every
  entry k is drawn by its own mesh, named by a MESH_LOD type-2 group with NUN id 0x2710 + k (n3_build_g1m.py).
"""
import json
import struct
from pathlib import Path

import numpy as np

from n3_common import BUILD, ORIG, gt

TEMPLATES = {'hair': ('0xd5d385f9', 0), 'waist': ('0xfed6b90c', 0)}   # vanilla model, type-4 entry index
FIXED = (28, 196)
# Karin's buttocks sit higher and further back than the body the 'legs' set was made for (bind pose: her back skin
# reaches z -12.9 / -13.3 with underwear at y 100-104, vanilla -11.6; the legs set's hips and thigh ellipsoids leave
# a ~4 cm gap there), and the skirt sank into it in big forward-leaning moves (build23). Two ellipsoids on the hips,
# (bone, semi-axes, centre) in bone space (hips axes: x up, y forward, z the character's left), identity rotation:
# bind-pose world centres (+-6, 97, -9), semi-axes x 11 / y 13 / z 7. Fitted (scratchpad ana/fit_butt3.py) to cover
# her back skin and underwear at y 88-102 by 2 cm wherever the legs set does not, with every non-root skirt chain
# point at least 0.3 cm outside.
KARIN_HIPS = ((2, (13.0, 7.0, 11.0), (-3.0, -9.0, 6.0)), (2, (13.0, 7.0, 11.0), (-3.0, -9.0, -6.0)))
COLLISION_SETS = {  # name -> vanilla model, LLOC entry index[, extra ellipsoids] (bones of the shared player skeleton)
    'torso': ('0x5548953f', 0),   # hips, spine x2, chest, clavicles, upper arms (ninja chest's scarf set)
    'head': ('0xd5d385f9', 0),    # chest, neck, clavicles, head x2, upper arms (hair set)
    'legs': ('0x6a0d18db', 1),    # hips, thighs, knees
    'skirt': ('0x6a0d18db', 1, KARIN_HIPS),   # legs + Karin's buttocks
}
MAX_CHAINS = 8         # chains per type-4 entry (vanilla hair: up to 8)
MAX_ENTRY_ID = 50      # vanilla (430 models): type-4 ids 0-25, consecutive within a model; type-5 ids 0-50


def first_entry_id(on_body, n):
    """Lowest start of n consecutive type-4 ids clear of the model's type-5 ids (first entry id at +24 of each
    type-5 subchunk's entries, the rest assumed consecutive: samurai chest 2, 3)."""
    taken, p = set(), 0
    while p < len(on_body):
        t, sz, cnt = struct.unpack_from('<3I', on_body, p)
        if t == 0x30005:
            first = struct.unpack_from('<I', on_body, p + 12 + 24)[0] & 0x7FFFFFFF
            taken |= set(range(first, first + cnt))
        p += sz
    s = 0
    while taken & set(range(s, s + n)):
        s += 1
    assert s + n - 1 <= MAX_ENTRY_ID, f'type-4 ids {s}..{s + n - 1} beyond the vanilla range'
    return s


def mat2quat(M):
    """rotation matrix -> (w, x, y, z)"""
    t = np.trace(M)
    if t > 0:
        s = np.sqrt(t + 1) * 2
        q = [0.25 * s, (M[2, 1] - M[1, 2]) / s, (M[0, 2] - M[2, 0]) / s, (M[1, 0] - M[0, 1]) / s]
    else:
        i = int(np.argmax(np.diag(M)))
        j, k = (i + 1) % 3, (i + 2) % 3
        s = np.sqrt(1 + M[i, i] - M[j, j] - M[k, k]) * 2
        q = [0.0] * 4
        q[0] = (M[k, j] - M[j, k]) / s
        q[1 + i] = 0.25 * s
        q[1 + j] = (M[j, i] + M[i, j]) / s
        q[1 + k] = (M[k, i] + M[i, k]) / s
    q = np.array(q)
    return q / np.linalg.norm(q)


def frames(pts):
    """World rotation (columns = local axes) per chain point: x towards the next point."""
    out = []
    for i in range(len(pts)):
        x = pts[i + 1] - pts[i] if i + 1 < len(pts) else pts[i] - pts[i - 1]
        x = x / np.linalg.norm(x)
        ref = np.array([0.0, 0.0, 1.0]) if abs(x[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
        y = np.cross(ref, x); y /= np.linalg.norm(y)
        z = np.cross(x, y)
        out.append(np.stack([x, y, z], 1))
    return out


def template_entries():
    import nuno4
    out = {}
    for kind, (h, k) in TEMPLATES.items():
        d = (ORIG / f'{h}.g1m').read_bytes(); m = gt.embedded_models(d)[-1]
        on = nuno4.parse_onun(d, m)
        out[kind] = [s for s in on['subs'] if s['type'] == 0x30004][0]['entries'][k]
    return out


def lloc_entry_bytes(h, k, extra=()):
    """LLOC entry k of a vanilla model, plus `extra` ellipsoids (bone, semi-axes, centre; bone space, identity rotation)
    cloned from the entry's first primitive. Primitive words: 0 shape (5 = ellipsoid), 1 bone id, 4-6 semi-axes,
    8-10 / 12-14 / 16-18 rotation rows, 20-22 centre in bone space, 23 = 1.0."""
    d = (ORIG / f'{h}.g1m').read_bytes(); m = gt.embedded_models(d)[-1]
    c = m.chunks['LLOC']; q = c.offset + 28
    for i in range(k + 1):
        flags, n = struct.unpack_from('<2I', d, q)
        if i == k:
            b = bytearray(d[q:q + 8 + 112 * n])
            for bone, size, centre in extra:
                p = bytearray(b[8:120])
                assert struct.unpack_from('<I', p, 0)[0] == 5
                struct.pack_into('<I', p, 4, bone)
                struct.pack_into('<3f', p, 16, *size)
                struct.pack_into('<12f', p, 32, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0)
                struct.pack_into('<3f', p, 80, *centre)
                b += p
            struct.pack_into('<I', b, 4, n + len(extra))
            return bytes(b), n + len(extra)
        q += 8 + 112 * n


def new_lloc(data, m, chains):
    """Append the collision sets the chains name; set each chain's `lloc` index list. Returns (chunk, entries, prims)."""
    c = m.chunks['LLOC']
    magic, ver, size, one = struct.unpack_from('<4s4s2I', data, c.offset)
    t, sz, cnt = struct.unpack_from('<3I', data, c.offset + 16)
    assert one == 1 and t == 0x20001 and c.offset + 16 + sz == c.end
    body = bytearray(data[c.offset + 28:c.end])
    prims = 0; q = 0
    for _ in range(cnt):
        n = struct.unpack_from('<I', body, q + 4)[0]; prims += n; q += 8 + 112 * n
    index = {}
    for r in chains:
        r['lloc'] = []
        for name in r['collide']:
            if name not in index:
                b, n = lloc_entry_bytes(*COLLISION_SETS[name])
                index[name] = cnt + len(index); body += b; prims += n
            r['lloc'].append(index[name])
    entries = cnt + len(index)
    sub = struct.pack('<3I', 0x20001, 12 + len(body), entries) + bytes(body)
    return struct.pack('<4s4s2I', magic, ver, 16 + len(sub), 1) + sub, entries, prims


def load():
    return json.loads((BUILD / 'physics.json').read_text())


def group(phys):
    """Chain indices per type-4 entry: chains sharing a vertex share an entry (union-find over the weights); a group
    over MAX_CHAINS splits into consecutive runs by angle about its roots' centre (vanilla entries hold 1-8 chains;
    the 16-chain skirt entry crashed the game, build16). Entries ordered by their first chain."""
    cs_all = phys['chains']
    root = list(range(len(cs_all)))
    def find(i):
        while root[i] != i:
            i = root[i]
        return i
    for verts in phys['weights'].values():
        for lst in verts.values():
            cs = sorted({ci for ci, j, w in lst if ci >= 0 and j >= 0 and w > 0})
            for c in cs[1:]:
                root[find(c)] = find(cs[0])
    comps = {}
    for i in range(len(cs_all)):
        comps.setdefault(find(i), []).append(i)
    out = []
    for comp in sorted(comps.values(), key=min):
        if len(comp) <= MAX_CHAINS:
            out.append(comp)
            continue
        p0 = np.array([cs_all[i]['points'][0] for i in comp], float); c = p0.mean(0)
        ring = sorted(comp, key=lambda i: np.arctan2(cs_all[i]['points'][0][0] - c[0], cs_all[i]['points'][0][2] - c[2]))
        k = -(-len(ring) // MAX_CHAINS); size = -(-len(ring) // k)
        out += [ring[s:s + size] for s in range(0, len(ring), size)]
    for g in out:
        assert len({(cs_all[i]['anchor'], cs_all[i]['template']) for i in g}) == 1, f'entry {g}: anchors / templates differ'
    return sorted(out, key=min)


def plan(phys, data, m, sk, joints):
    """New joints for every chain point, allocated entry by entry (each entry's joints contiguous). Extends `sk`
    ({bone id: ...}) and `joints` (storage list) in place and returns the chain records, in physics.json order."""
    fm = m.chunks['FM1G']
    id_count = struct.unpack_from('<H', data, m.chunks['SM1G'].offset + 22)[0]
    next_id = max(id_count, gt.u32(data, fm.offset + 136))
    next_st = len(joints)
    recs = {}
    for e, g in enumerate(group(phys)):
        for ci in g:
            c = phys['chains'][ci]
            pts = np.array(c['points'], float)
            a = sk[c['anchor']]
            Wa = np.array(a['world'], float); Ra, pa = Wa[:3, :3], Wa[:3, 3]
            rec = {'name': c['name'], 'anchor': c['anchor'], 'anchor_storage': a['storage'], 'template': c['template'],
                   'points': pts, 'ids': [], 'storages': [], 'frames': frames(pts), 'local': [],
                   'collide': c.get('collide', []), 'part': c.get('part', 'rest'), 'entry': e}
            for p, R in zip(pts, rec['frames']):
                W = np.eye(4); W[:3, :3] = R; W[:3, 3] = p
                bid, st = next_id, next_st
                next_id += 1; next_st += 1
                sk[bid] = {'storage': st, 'world': W, 'pos': p, 'parent': c['anchor']}
                joints.append({'parent': a['storage'], 'world': W.tolist(), 'world_p': tuple(p)})
                rec['ids'].append(bid); rec['storages'].append(st)
                rec['local'].append((mat2quat(Ra.T @ R), Ra.T @ (p - pa)))
            recs[ci] = rec
    return [recs[i] for i in range(len(phys['chains']))], next_id


def storage_order(chains):
    return sorted(chains, key=lambda r: r['storages'][0])


def entries(chains):
    """[[chain records of entry 0, in joint order], ...]"""
    out = []
    for r in storage_order(chains):
        if r['entry'] == len(out):
            out.append([])
        assert r['entry'] == len(out) - 1, 'entry joints are not contiguous'
        out[r['entry']].append(r)
    return out


def entry_lloc(recs, default):
    return sorted({x for r in recs for x in r.get('lloc', default)})


def override_weights(conf, phys, chains):
    """Replace the conformed weights of chain vertices: [chain, point, w] -> new bone ids (point -1 = anchor,
    chain -1 = point is a plain game bone id)."""
    conf = dict(conf)
    for key, verts in phys['weights'].items():
        gw = [str(x) for x in conf[key + '__gw']]          # fixed-width numpy strings would truncate
        for v, lst in verts.items():
            d = {}
            for ci, j, w in lst:
                b = j if ci < 0 else chains[ci]['anchor'] if j < 0 else chains[ci]['ids'][j]
                d[b] = d.get(b, 0) + w
            gw[int(v)] = json.dumps({str(b): w for b, w in d.items()})
        conf[key + '__gw'] = gw
    return conf


def entry_bytes(tmpl, recs, entry_id, lloc):
    """One type-4 entry holding the chains `recs` (same anchor), points chain after chain."""
    lloc = entry_lloc(recs, lloc)
    n = sum(len(r['points']) for r in recs)
    starts = np.cumsum([0] + [len(r['points']) for r in recs])[:-1]
    b = bytearray(struct.pack('<7I', recs[0]['anchor'], n, len(recs), len(lloc), n, len(recs), entry_id))
    b += tmpl['fixed']
    assert len(b) == FIXED[1]
    b += struct.pack(f'<{len(recs)}I', *starts)
    for r in recs:
        b += struct.pack('<9f', *r['frames'][0].T.ravel())          # rows = local axes
    for ci, r in enumerate(recs):
        seg = np.r_[0.0, np.linalg.norm(r['points'][1:] - r['points'][:-1], axis=1)]
        t = np.cumsum(seg) / seg.sum()
        for i, p in enumerate(r['points']):
            b += struct.pack('<4fIff', *p, 1.0, ci | (0x80000000 if i == 0 else 0), float(t[i]), float(seg[i]))
    b += struct.pack(f'<{len(lloc)}I', *lloc)
    for i, st in enumerate(st for r in recs for st in r['storages']):
        b += struct.pack('<2I', i, st)
    for s, r in zip(starts, recs):
        b += struct.pack('<4I', s, 3 | ((16 + 8) << 16), 4, 1) + struct.pack('<If', r['anchor'], 1.0)
    return bytes(b)


def new_onun(data, m, chains, lloc):
    tm = template_entries()
    c = m.chunks['ONUN']
    magic, ver, size, n = struct.unpack_from('<4s4s2I', data, c.offset)
    body = data[c.offset + 16:c.end]
    first = struct.unpack_from('<I', body, 0)[0]
    assert first != 0x30004, 'model already has type-4 chains'
    ents = entries(chains)
    first = first_entry_id(body, len(ents))
    blob = b''.join(entry_bytes(tm[rs[0]['template']], rs, first + i, lloc) for i, rs in enumerate(ents))
    sub = struct.pack('<3I', 0x30004, 12 + len(blob), len(ents)) + blob
    out = struct.pack('<4s4s2I', magic, ver, 16 + len(sub) + len(body), n + 1) + sub + body
    return out


def new_sm1g(data, m, chains, id_space):
    sm = m.chunks['SM1G']; o = sm.offset
    magic, ver, size, joff, one, zero, cnt, idc, groups = struct.unpack_from('<4s4sIIHHHHI', data, o)
    ids = list(struct.unpack_from(f'<{idc}H', data, o + 28))
    gtab = list(struct.unpack_from(f'<{groups}H', data, o + 28 + 2 * idc))
    jbytes = data[o + joff:o + joff + 48 * cnt]
    assert joff + 48 * cnt == size
    new_j = bytearray()
    for r in storage_order(chains):                      # joints are written in storage order
        for bid, st, (q, p) in zip(r['ids'], r['storages'], r['local']):
            while len(ids) <= bid:
                ids.append(0xFFFF)
            ids[bid] = st
            w, x, y, z = q
            new_j += struct.pack('<3fi4f4f', 1.0, 1.0, 1.0, r['anchor_storage'], x, y, z, w, *p, 1.0)
    for rs in entries(chains):
        gtab.append(sum(len(r['ids']) for r in rs) - 1)
    assert len(ids) == id_space
    new_cnt = cnt + sum(len(r['ids']) for r in chains)
    head = bytearray(struct.pack('<4s4sIIHHHHI', magic, ver, 0, 0, one, zero, new_cnt, len(ids), len(gtab)))
    tab = struct.pack(f'<{len(ids)}H', *ids) + struct.pack(f'<{len(gtab)}H', *gtab)
    body = bytes(head) + tab
    body += b'\0' * ((-len(body)) % 4)
    new_joff = len(body)
    out = bytearray(body + jbytes + bytes(new_j))
    struct.pack_into('<2I', out, 8, len(out), new_joff)
    return bytes(out), new_cnt, len(gtab)


def patch_fm1g(fm_new, groups, joints, id_space, lloc=None, chains=None, default_lloc=()):
    if lloc:
        struct.pack_into('<2I', fm_new, 96, *lloc)
    if chains:
        assert struct.unpack_from('<I', fm_new, 276)[0] == 0, 'template already has type-4 chains'
        ents = entries(chains)
        pts = sum(len(r['ids']) for r in chains)
        nch = len(chains)
        aw = sum(len(entry_lloc(rs, default_lloc)) for rs in ents)
        anchor_bytes = nch * (16 + 8)                      # one anchor bone per chain
        struct.pack_into('<5I', fm_new, 276, len(ents), pts, nch, aw, pts)
        struct.pack_into('<I', fm_new, 320, 156 * len(ents))
        struct.pack_into('<2I', fm_new, 328, nch, anchor_bytes)
    struct.pack_into('<I', fm_new, 12, groups)
    struct.pack_into('<I', fm_new, 16, joints)
    struct.pack_into('<I', fm_new, 136, id_space)


def lloc_entries(data, m):
    if 'LLOC' not in m.chunks:
        return 0
    c = m.chunks['LLOC']
    return struct.unpack_from('<3I', data, c.offset + 16)[2]
