"""Write Karin_Original into a Nioh 3 chest piece G1M and empty the parts she replaces.
usage: n3_build_g1m.py [ninja|samurai] [--physics [--collide] [--face]]
  default ninja; --physics adds BUILD/physics.json's chains (skirt chains also move the skirt mesh into its own
  submesh), --collide appends their LLOC collision sets (otherwise every chain uses the model's LLOC entry 0),
  --face skins the face (Body mesh) to the face bones with BUILD/face.json (n3_face.py) and moves it into the
  skirt's submesh (the rest palette is full); those weights are signed and already exact, written as they are

ninja chest 0x5548953f (vanilla v2.0.0.2):  sub0 VB0 8-weight stride 56, material 0 (2048 BC7 colour)   -> rest
                                           sub1 VB1 4-weight stride 48, material 1 (bare hands, 512 BC1 colour)
                                           sub2 VB2 cloth (stride 132, NUNO scarf, MESH_LOD type 1), material 2
                                           sub3 VB3 8-weight stride 56, material 2
samurai chest 0xed9b4309:                  sub0/sub1 VB0/1 cloth (stride 132, MESH_LOD type 1), material 0
                                           sub2 VB2 8-weight stride 56, material 0                      -> rest
                                           sub3 VB3 4-weight stride 40, material 1 (belt)
Karin's main part replaces the rest submesh. Every other vanilla submesh keeps its buffers, material and MESH_LOD
group, triangles collapsed to zero area: each material keeps its vanilla submeshes, each type-5 cloth entry its type-1
mesh. Every other part (arms, skirt / face, one mesh per type-4 entry) is inserted after the template's last material-0
submesh (and after the last vertex buffer / attribute set / palette / index buffer a material-0 submesh uses; later
vanilla indices shift): own vertex buffer, attribute set (the rest submesh's layout), palette, index buffer and
submesh (the rest record: material group 0, shader 0, material 0), and a MESH_LOD group (the rest group's name; type 0, or type 2 with NUN id 0x2710 + k for
type-4 entry k, as vanilla hair, helmets and chest 0xa2fd65db: a triangle with chain weight on a corner goes to the
entry with the largest summed weight; the entry's palette holds all of its joints, tips included).
The chest's per-material counts (n3_registry.py) then equal the submeshes / vertex buffers each material really has,
and each material's submeshes stay contiguous: the count records cover consecutive submesh indices in record order
(build20 appended after ninja sub1-3: its counts (26, 1, 2) put appended sub26 in material 1's range and that skirt
half was not drawn; the samurai, whose only other-material submesh came last, drew everything).
build12-18 moved vanilla submeshes onto material 0: type-2 meshes were not drawn while material 0's count was short
(build12-15) and the game crashed once it covered them (build16-18), with materials 1 / 2 still counted but empty
(no vanilla count record is empty; assumed cause, build20 tests it). Unregistered entries without type-2 groups only
simulate on the title screen (build11); registered ones on type-0 meshes do not simulate at all (build19).
The rest palette is rebuilt from the bones it uses, appended parts get their own (storage indices, each entry bound to
a native inverse bind, reused if the template already has one, else appended to MM1G). A palette over 85 entries
(u8 indices hold index x 3) uses u16 BLENDINDICES (type 7, as the vanilla female head's 124-128-entry palettes): the
offsets after them shift and the stride grows by 4 per set. Beyond 128 the least-weighted bones merge into their
nearest kept ancestor; chain joints and face bones never merge. FM1G's MM1G count and palette-entry total follow, and
+52 / +60 (vertex buffers), +56 (attribute sets), +64 (palettes), +72 (index buffers), +76 / +80 / +92 (submeshes),
+88 (MESH_LOD groups). The GM1G bounding box grows to Karin's bounds.
Output: BUILD/g1m/<model>.g1m, BUILD/g1m/build_report[_<target>].json, BUILD/atlas_uv.json (atlas regions used).
"""
import argparse
import hashlib
import json
import struct

import numpy as np

import n3_g1m_physics as physics
from n3_common import BUILD, gt, load_model, load_source, pack_weights, skeleton

# One 4096 atlas in texture set 0 only: its COLOR / NORMAL / SHADING / slot-49 textures are drawn by no other model.
# Set 1 holds global defaults (100-500 models) and set 2's colour is shared with a sibling ninja top, so neither is
# touched; all of Karin's submeshes use material 0 / shader 0.
ATLAS = {   # atlas -> (size, {source material: (x0, y0, w, h)} in atlas pixels, top-left origin)
    'A': (4096, {'Karin_Costume': (0, 0, 2048, 2048), 'Karin_Hair': (2048, 0, 2048, 2048),
                 'Karin_Hair_Transparent': (2048, 0, 2048, 2048),
                 'Karin_Face': (0, 2048, 2048, 2048), 'Karin_Body': (2048, 2048, 2048, 2048)}),
}
PARTS = {   # part -> (atlas, weights per vertex); split at the upper arms keeps both palettes <= 85
    'rest': ('A', 8),
    'arms': ('A', 8),
}
TARGETS = {  # model, the submesh holding Karin's main part (material group 0 / shader 0 / material 0)
    'ninja': {'model': '0x5548953f', 'rest': 0},
    'samurai': {'model': '0xed9b4309', 'rest': 2},
}
SKIRT_PART = False        # set when physics chains include the skirt: the skirt mesh gets its own submesh / palette
FACE_PART = False         # --face: the Body mesh (face) joins the skirt's submesh
ARM_ROOTS = (15, 16)
DROP = {('Body', 'Karin_Alpha')}         # transparent blush / highlight overlays: no alpha-blended slot here
U8_PALETTE = 85                # u8 blend indices store index x 3
MAX_PALETTE = 128              # u16 blend indices (vanilla female head: up to 128 entries)
CHAIN_NUN = 0x2710             # MESH_LOD type-2 group NUN id = 0x2710 + type-4 entry index


def part_of(mesh, mat, arm_share):
    if (mesh, mat) in DROP:
        return None
    if SKIRT_PART and mesh == 'skirt' or FACE_PART and mesh == 'Body':
        return 'skirt'
    return 'arms' if arm_share >= 0.5 else 'rest'


def arm_bones(sk):
    out = set()
    for b in sk:
        a = b
        while a is not None and a not in ARM_ROOTS:
            a = sk[a]['parent']
        if a is not None:
            out.add(b)
    return out


def gather(meta, arr, conf, arm, owner=None):
    """Per part: unique vertices (pos, normal, uv in atlas space, weights dict) and triangles. With `owner` (chain
    joint id -> type-4 entry), a triangle with chain weight on a corner goes to part e<entry> (largest summed weight)."""
    parts = {p: {'pos': [], 'nrm': [], 'uv': [], 'gw': [], 'tris': [], 'src': []} for p in PARTS}
    for m in meta['meshes']:
        k = m['key']
        pos = conf[k + '__pos'].astype(float); ln = conf[k + '__loop_normal'].astype(float)
        gws = [{int(b): w for b, w in json.loads(x).items()} for x in conf[k + '__gw']]
        lv = arr[k + '__loop_vertex']; luv = arr[k + '__loop_uv']; tris = arr[k + '__tris']; tm = arr[k + '__tri_material']
        share = np.array([sum(w for b, w in d.items() if b in arm) for d in gws])
        mats = [x['name'] for x in m['materials']]
        keymap = {p: {} for p in PARTS}
        co = arr[k + '__co'][lv[tris]]
        area = np.linalg.norm(np.cross(co[:, 1] - co[:, 0], co[:, 2] - co[:, 0]), axis=1) / 2
        for t, mi, a in zip(tris, tm, area):
            if a < 1e-10:             # kisekae keys collapse the skin under clothing to zero area (source space)
                continue
            mat = mats[mi]
            part = part_of(m['name'], mat, share[lv[t]].mean())
            if part is None:
                continue
            if owner:
                ew = {}
                for loop in t:
                    for b, w in gws[lv[loop]].items():
                        if b in owner and w > 0:
                            ew[owner[b]] = ew.get(owner[b], 0) + w
                if ew:
                    part = f'e{max(ew, key=lambda e: ew[e])}'
            size, regions = ATLAS[PARTS[part][0]]
            x0, y0, w, h = regions[mat]
            P = parts[part]; tri = []
            for loop in t:
                u, v = luv[loop]
                uv = ((x0 + u * w) / size, (y0 + (1 - v) * h) / size)
                key = (int(lv[loop]), mat, round(uv[0], 5), round(uv[1], 5), *np.round(ln[loop], 3))
                idx = keymap[part].get(key)
                if idx is None:
                    idx = keymap[part][key] = len(P['pos'])
                    P['pos'].append(pos[lv[loop]]); P['nrm'].append(ln[loop]); P['uv'].append(uv)
                    P['gw'].append(gws[lv[loop]]); P['src'].append(m['name'])
                tri.append(idx)
            P['tris'].append(tri)
    for P in parts.values():
        for key in ('pos', 'nrm', 'uv', 'tris'):
            P[key] = np.array(P[key], float if key != 'tris' else np.int64)
    return parts


def tangents(P):
    """Nioh 3 convention (measured on vanilla): stored T ~ -dP/dv, w*cross(N, T) ~ -dP/du."""
    pos, uv, nrm, I = P['pos'], P['uv'], P['nrm'], P['tris']
    e1, e2 = pos[I[:, 1]] - pos[I[:, 0]], pos[I[:, 2]] - pos[I[:, 0]]
    d1, d2 = uv[I[:, 1]] - uv[I[:, 0]], uv[I[:, 2]] - uv[I[:, 0]]
    r = d1[:, 0] * d2[:, 1] - d2[:, 0] * d1[:, 1]
    r = np.where(np.abs(r) > 1e-12, r, 1e-12)
    fu = (e1 * d2[:, 1:2] - e2 * d1[:, 1:2]) / r[:, None]
    fv = (e2 * d1[:, 0:1] - e1 * d2[:, 0:1]) / r[:, None]
    du, dv = np.zeros_like(pos), np.zeros_like(pos)
    for c in range(3):
        np.add.at(du, I[:, c], fu); np.add.at(dv, I[:, c], fv)
    t = -dv - nrm * (nrm * -dv).sum(1, keepdims=True)
    bad = np.linalg.norm(t, axis=1) < 1e-9
    alt = np.cross(nrm, np.where(np.abs(nrm[:, :1]) < 0.9, [[1.0, 0, 0]], [[0, 1.0, 0]]))
    t[bad] = alt[bad]
    t /= np.linalg.norm(t, axis=1, keepdims=True)
    w = np.sign((np.cross(nrm, t) * -du).sum(1)); w[w == 0] = 1
    return np.concatenate([t, w[:, None]], 1)


def pack(d, k):
    """pack_weights, except signed face weights (n3_face.py): already exact, kept as they are, largest |w| first."""
    if all(0 <= w <= 1.001 for w in d.values()):
        return pack_weights(d, k)
    items = sorted(d.items(), key=lambda bw: -abs(bw[1]))
    assert len(items) <= k and sum(w for _, w in items) == 1.0, items
    return [b for b, _ in items] + [items[0][0]] * (k - len(items)), [w for _, w in items] + [0.0] * (k - len(items))


def palette_for(gws, k, sk, fixed=frozenset(), extra=()):
    """Bones (ids) for a part, <= MAX_PALETTE, and the per-vertex weights remapped onto them. `fixed` bones (chain
    joints) must never merge; `extra` bones join the palette even without weight (all joints of a type-4 entry)."""
    packed = [pack(d, k) for d in gws]
    total = {}
    for ids, ws in packed:
        for b, w in zip(ids, ws):
            if w > 0:
                total[b] = total.get(b, 0) + w
    keep = set(total)
    merged = {}
    signed = {b for d in gws if not all(0 <= w <= 1.001 for w in d.values()) for b in d}
    while len(keep) > MAX_PALETTE:
        b = min((x for x in keep if x not in (0, 1, 2)), key=lambda x: total[x])
        assert b not in signed, f'palette overflow would merge face bone {b}'
        assert b not in fixed, f'palette overflow would merge chain joint {b}'
        keep.discard(b)
        a = sk[b]['parent']
        while a is not None and a not in keep:
            a = sk[a]['parent']
        merged[b] = a if a is not None else 2
    def target(b):
        while b in merged:
            b = merged[b]
        return b
    out = []
    for d in gws:
        nd = {}
        for b, w in d.items():
            nd[target(b)] = nd.get(target(b), 0) + w
        out.append(pack(nd, k))
    palette = sorted({b for ids, ws in out for b, w in zip(ids, ws) if w > 0} | {ids[0] for ids, _ in out} | set(extra))
    assert len(palette) <= MAX_PALETTE, f'palette {len(palette)} > {MAX_PALETTE}'
    return palette, out, merged


def vertex_bytes(layout, stride, P, pal_index, weights, k):
    n = len(P['pos'])
    buf = np.zeros((n, stride), np.uint8)
    put = lambda off, arr: buf.__setitem__((slice(None), slice(off, off + arr.shape[1])), arr)  # noqa: E731
    tan = tangents(P)
    for a in layout:
        sem, layer, off = a['semantic'], a['layer'], a['offset']
        if sem == 'POSITION':
            put(off, P['pos'].astype('<f4').view(np.uint8).reshape(n, 12))
        elif sem == 'NORMAL':
            put(off, np.concatenate([P['nrm'], np.zeros((n, 1))], 1).astype('<f2').view(np.uint8).reshape(n, 8))
        elif sem == 'TANGENT':
            put(off, tan.astype('<f2').view(np.uint8).reshape(n, 8))
        elif sem == 'TEXCOORD' and layer == 0:
            put(off, P['uv'].astype('<f2').view(np.uint8).reshape(n, 4))
        elif sem == 'BLENDWEIGHT':
            cnt = {0x0B: 4, 0x0A: 2}[a['type']]
            W = np.array([ws[4 * layer:4 * layer + cnt] for _, ws in weights], float)
            put(off, W.astype('<f2').view(np.uint8).reshape(n, 2 * cnt))
        elif sem == 'BLENDINDICES':
            I = np.array([[pal_index[b] * 3 for b in ids[4 * layer:4 * layer + 4]] if 4 * layer < k else
                          [pal_index[ids[0]] * 3] * 4 for ids, _ in weights])
            if a['type'] == 0x07:
                put(off, I.astype('<u2').view(np.uint8).reshape(n, 8))
            else:
                assert a['type'] == 0x05 and I.max() < 256
                put(off, I.astype(np.uint8))
        else:
            raise SystemExit(f'unhandled vertex attribute {sem}{layer}')
    return buf.tobytes()


def widen(attrs, stride):
    """The layout with u8 x 4 blend indices as u16 x 4: later attributes shift by 4 per index set."""
    narrow = [a['offset'] for a in attrs if a['semantic'] == 'BLENDINDICES' and a['type'] == 0x05]
    out = []
    for a in attrs:                   # parse order kept: the section rewrite patches the records in place
        b = dict(a, offset=a['offset'] + 4 * sum(1 for o in narrow if o < a['offset']))
        if a['semantic'] == 'BLENDINDICES' and a['type'] == 0x05:
            b['type'] = 0x07
        out.append(b)
    return out, stride + 4 * len(narrow)


def main():
    global SKIRT_PART, FACE_PART
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('target', nargs='?', default='ninja', choices=sorted(TARGETS))
    ap.add_argument('--physics', action='store_true', help="BUILD/physics.json's chains")
    ap.add_argument('--collide', action='store_true', help='append the chains\' LLOC collision sets')
    ap.add_argument('--face', action='store_true', help='skin the face with BUILD/face.json (needs --physics)')
    opts = ap.parse_args()
    tname = opts.target
    with_physics = opts.physics
    target = TARGETS[tname]
    model, subs = target['model'], {'rest': target['rest']}
    meta, arr = load_source()
    conf = dict(np.load(BUILD / 'conformed.npz'))
    data, m = load_model(model)
    empty_subs = [i for i in range(len(m.submeshes)) if i != subs['rest']]
    sk = skeleton(m)
    joints, _ = gt.skeleton(m)
    chains = None
    chain_joints = frozenset()
    owner = {}                        # chain joint id -> type-4 entry index
    ents = []
    if with_physics:                  # new chain joints extend sk / joints; chain vertices move onto them
        phys = physics.load()
        chains, id_space = physics.plan(phys, data, m, sk, joints)
        conf = physics.override_weights(conf, phys, chains)
        chain_joints = frozenset(b for r in chains for b in r['ids'])
        ents = physics.entries(chains)
        owner = {b: e for e, rs in enumerate(ents) for r in rs for b in r['ids']}
        for e in range(len(ents)):
            PARTS[f'e{e}'] = ('A', 8)
        if any(r['part'] == 'skirt' for r in chains) or opts.face:     # the face needs the room too
            SKIRT_PART = True
            PARTS['skirt'] = ('A', 8)
    if opts.face:
        assert SKIRT_PART, '--face needs the skirt submesh (--physics with skirt chains)'
        FACE_PART = True
        face = json.loads((BUILD / 'face.json').read_text(encoding='utf-8'))['weights']
        gw = conf['Body__gw'].astype(object)
        for v, ws in face.items():
            gw[int(v)] = json.dumps({str(b): w for b, w in ws})
        conf['Body__gw'] = gw
    parts = gather(meta, arr, conf, arm_bones(sk), owner)
    tparts = [n for n in PARTS if n in subs]          # parts written into template submeshes; the others are appended
    d = bytearray(data)
    gm = m.chunks['GM1G']
    version = m.g1mg_version
    vb_hdr = 16 if version > 0x30303430 else 12
    ib_hdr = 12 if version > 0x30303430 else 8
    # native binds: reuse template entries that already are native, append the rest
    mats = gt.binds(m)
    st_bind = {}                      # storage index -> MM1G index holding its native inverse bind
    for p in m.palettes:
        for e in p:
            want = np.array(gt.native_bind(joints[e['joint']]['world']))
            if e['g1mm'] < len(mats) and np.abs(np.array(mats[e['g1mm']]) - want).max() < 1e-3:
                st_bind.setdefault(e['joint'], e['g1mm'])
    appended = []
    new_vb, new_ib, new_pal, report = {}, {}, {}, {'template_sha256': hashlib.sha256(data).hexdigest(), 'parts': {}}
    wide = {}                         # attribute set -> its layout with u16 blend indices
    rest_s = m.submeshes[subs['rest']]
    mats_v = [x['material'] for x in m.submeshes]
    assert mats_v == sorted(mats_v) and mats_v[0] == 0, 'vanilla submeshes not ordered by material'
    m0 = [x for x in m.submeshes if x['material'] == 0]; other = [x for x in m.submeshes if x['material'] != 0]
    def insert_at(kind):             # first index after every material-0 submesh's item of this kind
        lo = max(max(kind(x)) for x in m0) + 1
        assert all(min(kind(x)) >= lo for x in other), 'vanilla buffers not ordered by material'
        return lo
    s_at = len(m0)
    v_at = insert_at(lambda x: m.attributes[x['vertex_buffer']]['buffers'])
    a_at = insert_at(lambda x: [x['vertex_buffer']])
    p_at = insert_at(lambda x: [x['palette']])
    i_at = insert_at(lambda x: [x['index_buffer']])
    added = []                        # appended meshes: own VB / attribute set / palette / IB / submesh, in order
    n_entry = 0
    for name, (atlas, k) in PARTS.items():
        P = parts[name]
        assert len(P['tris']), f'{name}: no triangles'
        s = m.submeshes[subs[name]] if name in subs else rest_s       # appended meshes take the rest submesh's layout
        attrs = m.attributes[s['vertex_buffer']]
        stride = m.vertex_buffers[attrs['buffers'][0]]['stride']
        assert len(P['pos']) < 65536 and m.index_buffers[s['index_buffer']]['stride'] == 2, name
        entry = int(name[1:]) if name[0] == 'e' and name[1:].isdigit() else None
        own = [b for r in ents[entry] for b in r['ids']] if entry is not None else []
        palette, weights, merged = palette_for(P['gw'], k, sk, chain_joints, own)
        assert set(own) <= set(palette), f'{name}: entry joints missing from the palette'
        assert entry is not None or not set(palette) & chain_joints, f'{name}: chain joints outside the entry meshes'
        pal_index = {b: i for i, b in enumerate(palette)}
        layout = attrs['attrs']
        if len(palette) > U8_PALETTE:
            assert len(attrs['buffers']) == 1, f'{name}: u16 indices need a single-buffer layout'
            layout, stride = widen(layout, stride)
            if name in subs:
                wide[s['vertex_buffer']] = layout
        entries = []
        for b in palette:
            st = sk[b]['storage']
            if st not in st_bind:
                st_bind[st] = len(mats) + len(appended)
                appended.append(gt.native_bind(joints[st]['world']))
            entries.append({'g1mm': st_bind[st], 'physics': 0, 'joint': st, 'external': False})
        vb = vertex_bytes(layout, stride, P, pal_index, weights, k)
        ib = np.asarray(P['tris'], '<u2').ravel().tobytes()
        if name in subs:
            new_pal[s['palette']] = entries
            new_vb[m.attributes[s['vertex_buffer']]['buffers'][0]] = (stride, len(P['pos']), vb)
            new_ib[s['index_buffer']] = ib
            sub = subs[name]
        else:
            if entry is not None:
                assert entry == n_entry, 'entry meshes out of order'
                n_entry += 1
            added.append({'layout': layout, 'stride': stride, 'n': len(P['pos']), 'vb': vb, 'ib': ib, 'palette': entries,
                          'tris': len(P['tris']), 'lod': (2, CHAIN_NUN + entry) if entry is not None else (0, 0xFFFFFFFF)})
            sub = s_at + len(added) - 1
        report['parts'][name] = {'submesh': sub, 'atlas': atlas, 'vertices': len(P['pos']), 'triangles': len(P['tris']),
                                 'palette': palette, 'merged_bones': {str(a): b for a, b in merged.items()},
                                 'blend_indices': 'u16' if len(palette) > U8_PALETTE else 'u8', 'stride': stride,
                                 'sources': sorted(set(P['src']))}
        if entry is not None:
            report['parts'][name]['chains'] = [r['name'] for r in ents[entry]]
    rest_vbi = m.attributes[rest_s['vertex_buffer']]['buffers'][0]
    nv, na, npal, nib, ns = (len(m.vertex_buffers), len(m.attributes), len(m.palettes), len(m.index_buffers),
                             len(m.submeshes))
    sh = lambda i, at: i + len(added) if i >= at else i  # noqa: E731  (vanilla index -> index after the insertion)
    # emptied vanilla submeshes: every index -> its first index (zero area, same length)
    empty = {}
    for e in empty_subs:
        se = m.submeshes[e]; ibe = m.index_buffers[se['index_buffer']]
        assert se['index_offset'] == 0 and se['index_count'] == ibe['count'], 'submesh does not own its index buffer'
        empty[se['index_buffer']] = struct.unpack_from('<H', data, ibe['offset'])[0]
    # ---- rebuild GM1G sections in order ----
    sec_out = []
    for sec in m.sections:
        body0 = sec['offset'] + 12
        raw = bytes(data[body0:sec['offset'] + sec['size']])
        count = sec['count']
        if sec['name'] == 'VERTEX_BUFFERS':
            chunks = []; cur = body0
            for i, vb in enumerate(m.vertex_buffers):
                hdr = bytearray(data[cur:cur + vb_hdr])
                if i == rest_vbi:
                    rest_hdr = bytes(hdr)
                if i in new_vb:
                    stride, n, payload = new_vb[i]
                    struct.pack_into('<2I', hdr, 4, stride, n)
                else:
                    payload = bytes(data[vb['offset']:vb['offset'] + vb['stride'] * vb['count']])
                chunks.append(bytes(hdr) + payload)
                cur = vb['offset'] + vb['stride'] * vb['count']
            assert not added or gt.u32(rest_hdr, 0) != 0x80000000, 'rest buffer is a segment'
            new = []
            for a in added:
                hdr = bytearray(rest_hdr)
                struct.pack_into('<2I', hdr, 4, a['stride'], a['n'])
                new.append(bytes(hdr) + a['vb'])
            count += len(added)
            raw = b''.join(chunks[:v_at] + new + chunks[v_at:])
        elif sec['name'] == 'INDEX_BUFFER':
            chunks = []; cur = body0
            for i, ib in enumerate(m.index_buffers):
                hdr = bytearray(data[cur:cur + ib_hdr])
                if i == rest_s['index_buffer']:
                    rest_ihdr = bytes(hdr)
                if i in new_ib:
                    payload = new_ib[i]
                    struct.pack_into('<I', hdr, 0, len(payload) // 2)
                elif i in empty:
                    payload = struct.pack('<H', empty[i]) * ib['count']
                else:
                    payload = bytes(data[ib['offset']:ib['offset'] + ib['count'] * ib['stride']])
                chunks.append(bytes(hdr) + payload)
                end = ib['offset'] + ib['count'] * ib['stride']
                cur = end + ((-(end - gm.offset)) % 4)
            new = []
            for a in added:
                hdr = bytearray(rest_ihdr)
                struct.pack_into('<I', hdr, 0, len(a['ib']) // 2)
                new.append(bytes(hdr) + a['ib'])
            body = bytearray()
            for c in chunks[:i_at] + new + chunks[i_at:]:
                body += c + b'\0' * ((-(len(body) + len(c))) % 4)
            count += len(added)
            raw = bytes(body)
        elif sec['name'] == 'VERTEX_ATTRIBUTES' and (wide or added):
            sets, cur = [], body0
            for _ in range(sec['count']):
                k = gt.u32(data, cur); head = data[cur:cur + 4 + 4 * k]; cur += 4 + 4 * k
                n = gt.u32(data, cur); sets.append((head, data[cur:cur + 4 + 8 * n])); cur += 4 + 8 * n
            assert cur == sec['offset'] + sec['size'], 'VERTEX_ATTRIBUTES parse'
            rest_set = sets[rest_s['vertex_buffer']][1]
            for dst, layout in wide.items():          # records in parse order: u16 buffer, u16 offset, u8 type, ...
                rec = bytearray(sets[dst][1])
                assert gt.u32(rec, 0) == len(layout)
                for i, a in enumerate(layout):
                    struct.pack_into('<H', rec, 4 + 8 * i + 2, a['offset']); rec[4 + 8 * i + 4] = a['type']
                sets[dst] = (sets[dst][0], bytes(rec))
            new = []
            for j, a in enumerate(added):             # one buffer (local index 0) = the entry's own buffer
                rec = bytearray(rest_set)
                assert gt.u32(rec, 0) == len(a['layout'])
                for i, x in enumerate(a['layout']):
                    assert struct.unpack_from('<H', rec, 4 + 8 * i)[0] == 0
                    struct.pack_into('<H', rec, 4 + 8 * i + 2, x['offset']); rec[4 + 8 * i + 4] = x['type']
                new.append((struct.pack('<2I', 1, v_at + j), bytes(rec)))
            for i, (head, rec) in enumerate(sets):    # head: u32 n, n x u32 vertex buffer
                k = gt.u32(head, 0)
                sets[i] = (struct.pack(f'<{k + 1}I', k, *(sh(v, v_at) for v in struct.unpack_from(f'<{k}I', head, 4))), rec)
            count += len(added)
            raw = b''.join(h + a for h, a in sets[:a_at] + new + sets[a_at:])
        elif sec['name'] == 'MESH_LOD':
            # one block, c1 groups of one submesh each (both chests); groups are rewritten in submesh order with
            # vanilla indices shifted, one group per inserted mesh: name[16], type, unk, NUN id, 1, submesh
            c1, c2 = struct.unpack_from('<2I', raw, 12)
            assert sec['count'] == 1 and c2 == 0, 'MESH_LOD: one block, no c2'
            groups, q = {}, 36
            for _ in range(c1):
                ic, i = struct.unpack_from('<2I', raw, q + 24)
                assert ic == 1 and i not in groups, 'MESH_LOD group not naming exactly one submesh'
                groups[i] = raw[q:q + 24]; q += 32
            assert q == len(raw) and sorted(groups) == list(range(ns)), 'MESH_LOD parse'
            src = groups[subs['rest']]
            assert struct.unpack_from('<H', src, 16)[0] == 0, 'rest MESH_LOD group is not type 0'
            out = {sh(i, s_at): g for i, g in groups.items()}
            for j, a in enumerate(added):
                out[s_at + j] = src[:16] + struct.pack('<HHI', a['lod'][0], struct.unpack_from('<H', src, 18)[0], a['lod'][1])
            head = bytearray(raw[:36]); struct.pack_into('<I', head, 12, len(out))
            raw = bytes(head) + b''.join(out[i] + struct.pack('<2I', 1, i) for i in sorted(out))
        elif sec['name'] == 'JOINT_PALETTES':
            pals = [new_pal.get(i, p) for i, p in enumerate(m.palettes)]
            pals = pals[:p_at] + [a['palette'] for a in added] + pals[p_at:]
            count += len(added)
            raw = gt.palettes_body(pals)
        elif sec['name'] == 'SUBMESH':
            body = bytearray(raw)
            mat_fields = bytes(raw[56 * subs['rest'] + 12:56 * subs['rest'] + 28])
            group, _, shader, material = struct.unpack('<4I', mat_fields)
            assert (group, shader, material) == (0, 0, 0), 'rest submesh is not material group 0 / shader 0 / set 0'
            for name in tparts:
                sub, P = subs[name], parts[name]
                struct.pack_into('<I', body, 56 * sub + 40, 0)                     # vertex offset
                struct.pack_into('<I', body, 56 * sub + 44, len(P['pos']))         # vertex count
                struct.pack_into('<I', body, 56 * sub + 48, 0)                     # index offset
                struct.pack_into('<I', body, 56 * sub + 52, 3 * len(P['tris']))    # index count
                body[56 * sub + 12:56 * sub + 28] = mat_fields                     # material group, +16, shader, material
            new = []
            for j, a in enumerate(added):                                          # inserted meshes: the rest record
                rec = bytearray(body[56 * subs['rest']:56 * subs['rest'] + 56])
                struct.pack_into('<2I', rec, 4, a_at + j, p_at + j)                # attribute set, palette
                struct.pack_into('<I', rec, 28, i_at + j)                          # index buffer
                struct.pack_into('<4I', rec, 40, 0, a['n'], 0, 3 * a['tris'])
                new.append(bytes(rec))
            recs = []
            for i in range(ns):                                                    # vanilla: shifted references
                rec = bytearray(body[56 * i:56 * i + 56])
                at_, pal_ = struct.unpack_from('<2I', rec, 4)
                struct.pack_into('<2I', rec, 4, sh(at_, a_at), sh(pal_, p_at))
                struct.pack_into('<I', rec, 28, sh(struct.unpack_from('<I', rec, 28)[0], i_at))
                recs.append(bytes(rec))
            assert len(body) == 56 * ns
            count += len(added)
            raw = b''.join(recs[:s_at] + new + recs[s_at:])
        sec_out.append(struct.pack('<3I', sec['magic'], 12 + len(raw), count) + raw)
    gm_body = b''.join(sec_out)
    gm_head = bytearray(data[gm.offset:gm.offset + 48])
    allp = np.concatenate([parts[p]['pos'] for p in PARTS])
    lo = np.minimum(np.array(struct.unpack_from('<3f', gm_head, 20)), allp.min(0) - 1)
    hi = np.maximum(np.array(struct.unpack_from('<3f', gm_head, 32)), allp.max(0) + 1)
    struct.pack_into('<6f', gm_head, 20, *lo, *hi)
    struct.pack_into('<I', gm_head, 8, 48 + len(gm_body))
    new_gm = bytes(gm_head) + gm_body
    # ---- MM1G / FM1G ----
    mm = m.chunks['MM1G']; fm = m.chunks['FM1G']
    mm_count = gt.u32(data, mm.offset + 12)
    mm_new = bytearray(data[mm.offset:mm.end]) + b''.join(struct.pack('<16f', *[v for r in a for v in r]) for a in appended)
    struct.pack_into('<2I', mm_new, 8, len(mm_new), mm_count + len(appended))
    fm_new = bytearray(data[fm.offset:fm.end])
    assert struct.unpack_from('<I', fm_new, 24)[0] == mm_count
    old_entries = sum(len(p) for p in m.palettes)
    assert struct.unpack_from('<I', fm_new, 68)[0] == old_entries, 'FM1G +68 is not the palette-entry total'
    struct.pack_into('<I', fm_new, 24, mm_count + len(appended))
    struct.pack_into('<I', fm_new, 68, sum(len(new_pal.get(i, p)) for i, p in enumerate(m.palettes))
                     + sum(len(a['palette']) for a in added))
    if added:                         # counts of vertex buffers, attribute sets, palettes, index buffers, submeshes, groups
        for off, n in ((52, nv), (56, na), (60, nv), (64, npal), (72, nib), (76, ns), (80, ns), (92, ns), (88, ns)):
            assert gt.u32(fm_new, off) == n, f'FM1G +{off} is not {n}'
            struct.pack_into('<I', fm_new, off, n + len(added))
    new_chunks = {'GM1G': new_gm, 'MM1G': bytes(mm_new)}
    if chains:
        lloc = list(range(min(1, physics.lloc_entries(data, m))))    # collide with the model's first LLOC set
        lloc_counts = None
        if opts.collide:                                              # per chain: its own appended sets
            new_chunks['LLOC'], *lloc_counts = physics.new_lloc(data, m, chains)
        new_chunks['SM1G'], n_joints, groups = physics.new_sm1g(data, m, chains, id_space)
        new_chunks['ONUN'] = physics.new_onun(data, m, chains, lloc)
        physics.patch_fm1g(fm_new, groups, n_joints, id_space, lloc_counts, chains, lloc)
        report['physics'] = [{'name': r['name'], 'anchor': r['anchor'], 'ids': r['ids'], 'storages': r['storages'],
                              'lloc': r.get('lloc', lloc), 'part': r['part'], 'entry': r['entry']} for r in chains]
    new_chunks['FM1G'] = bytes(fm_new)
    # ---- reassemble the file ----
    first_chunk = struct.unpack_from('<I', data, 12)[0]
    out = bytearray(data[:first_chunk])
    for c in m.chunks.values():
        out += new_chunks.get(c.magic, data[c.offset:c.end])
    struct.pack_into('<I', out, 8, len(out))
    (BUILD / 'g1m').mkdir(exist_ok=True)
    dst = BUILD / 'g1m' / f'{model}.g1m'
    dst.write_bytes(out)
    report.update({'output_sha256': hashlib.sha256(out).hexdigest(), 'bytes': len(out), 'appended_binds': len(appended),
                   'bbox': [lo.round(2).tolist(), hi.round(2).tolist()]})
    report_name = 'build_report.json' if tname == 'ninja' else f'build_report_{tname}.json'
    (BUILD / 'g1m' / report_name).write_text(json.dumps(report, indent=1))
    (BUILD / 'atlas_uv.json').write_text(json.dumps(ATLAS, indent=1))
    for n, r in report['parts'].items():
        print(n, {k: v for k, v in r.items() if k not in ('palette',)}, 'palette', len(r['palette']))
    print('out', dst, len(out), 'appended binds', len(appended))


if __name__ == '__main__':
    main()
