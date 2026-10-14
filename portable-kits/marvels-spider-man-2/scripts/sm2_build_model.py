"""Write Karin into a hero suit .model (keeps every look / LOD / culling table; replaces mesh contents).

  python sm2_build_model.py --target peter [--materials keep|karin] [--out-stage ...]

Slot plan
  - meshes of the 'body' look at every LOD get Karin parts in PART_ORDER (full resolution at every LOD);
  - meshes only in other looks of the suit (mask, dmg_decal, web shooters when no part is left) become a
    degenerate 3-vertex triangle skinned to the head;
  - meshes of looks named knife* stay as shipped (story props).
  - ModelAnimZiva2Info / AnimVertInfo2 / VertSmoothInfo removed, ModelBuilt flag 0x10000000 cleared (T2),
    ModelBuilt vertex total and bounds refreshed, toc header pairs refreshed by i30_build.save_model.
"""
import argparse, json, os, struct, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import i30_model as M          # noqa: E402
import i30_build as B          # noqa: E402
import i30_writer as Wr        # noqa: E402
from sm2_karin_geo import TARGETS, WORK   # noqa: E402
from sm2_preview import load_parts        # noqa: E402

# hair strands and facial morphs index the original vertices; a blanked model drops them
STRAND_TAGS = (0x3C9DABDF, 0x27CA5246, 0xB25B3163, 0xBB7303D5, 0x14D8B13C, 0x5D5CF541)
MORPH_TAGS = (0x948C38CD, 0x5E03CEFE, 0xDE8D9DCF, 0x573C714B)
PART_ORDER = ['body', 'costume', 'hair', 'face', 'hair_alpha', 'face_alpha']
T_LOOK, T_LOOKBUILT, T_SUBSET, T_GEOM, T_BUILT = 0x06EB7EFC, 0x811902D7, 0x78D9CBDE, 0xF4EA9E18, 0x283D0383
T_LOOKGROUP = 0x4CCEA4AD


def looks(model):
    """-> {look name: [[mesh idx per LOD] x 8]} from ModelLook + ModelLookBuilt"""
    L = model.sec(T_LOOK)
    lb = model.sec(T_LOOKBUILT)
    n = struct.unpack_from('<I', lb, 0)[0] // 80
    out = {}
    for i in range(n):
        h = struct.unpack_from('<16I', lb, i * 80)
        name = model.cstr(struct.unpack_from('<I', lb, i * 80 + 76)[0])
        cnt = h[14] & 0xFFFF            # high half: flags (Miles Default look)
        lst = struct.unpack_from(f'<{cnt}H', lb, h[0]) if cnt else ()
        lods = []
        for k in range(8):
            st, c = struct.unpack_from('<HH', L, (2 * i) * 32 + 4 * k)
            lods.append(list(lst[st:st + c]))
        out[name] = lods
    return out


def look_groups(model):
    """-> {group name: [look names]} from ModelLookGroup: u8 count, then per group (u64 list offset from byte 1,
    u64 count, u32 crc32(name), u32 name offset), then the u16 look index lists. A group is a look preset
    (civilian outfits: 'tuxedo', 'teacher'...; suits: 'Default' = Default + body + mask, some 'noMask')."""
    G = model.sec(T_LOOKGROUP)
    lb = model.sec(T_LOOKBUILT)
    names = [model.cstr(struct.unpack_from('<I', lb, i * 80 + 76)[0]) for i in range(struct.unpack_from('<I', lb, 0)[0] // 80)]
    out = {}
    for k in range(G[0] if G else 0):
        off, cnt, _, no = struct.unpack_from('<QQII', G, 1 + 24 * k)
        out[model.cstr(no)] = [names[i] for i in struct.unpack_from(f'<{cnt}H', G, 1 + off)]
    return out


ADDITIVE_LOOKS = ('mask',)      # groups made only of these (or empty) toggle a part, they are not outfit presets


def cover_looks(model, lk, first):
    """-> looks whose slot 0 shows Karin: `first` plus a greedy cover of every look group that would otherwise
    show no Karin mesh (T5 put Karin only in the body / Default look: Peter's 'tuxedo' / 'teacher' presets,
    the teacher 'spider_suit' and Miles Mysterio's 'dj_suit_group' do not include it)."""
    chosen = [first]
    meshes = lambda look: {m for lst in lk[look] for m in lst[:1]}
    shown = lambda grp: {m for look in grp for lst in lk[look] for m in lst}
    todo = [g for g in look_groups(model).values()
            if any(look not in ADDITIVE_LOOKS and any(lk[look]) for look in g)]
    done = [g for g in todo if meshes(first) & shown(g)]
    todo = [g for g in todo if not (meshes(first) & shown(g))]
    while todo:                    # score: groups newly covered minus groups that would draw Karin twice
        cand = {look for g in todo for look in g if look not in ADDITIVE_LOOKS and any(lk[look])
                and not look.lower().startswith('knife')}
        best = max(sorted(cand), key=lambda look: sum(bool(meshes(look) & shown(g)) for g in todo)
                   - sum(bool(meshes(look) & shown(g)) for g in done))
        chosen.append(best)
        done += [g for g in todo if meshes(best) & shown(g)]
        todo = [g for g in todo if not (meshes(best) & shown(g))]
    return chosen


def degenerate(at, joint):
    P = np.repeat(np.asarray(at, np.float64)[None], 3, 0) + np.array([[0, 0, 0], [1e-4, 0, 0], [0, 1e-4, 0]])
    N = np.tile([0, 0, 1.0], (3, 1))
    UV = np.zeros((3, 2))
    J = np.full((3, 1), joint)
    W = np.ones((3, 1))
    return Wr.encode_block(P, N, UV, np.array([0, 1, 2]), J, W)


def plan_slots(model, lk, extra=None):
    """-> {mesh idx: part name | 'degenerate' | 'keep'}
    extra {look name: part}: slot 0 of that look at every LOD carries the part (e.g. {'mask': 'face'})."""
    plan = {}
    for name, lods in lk.items():
        if name.lower().startswith('knife'):
            for lst in lods:
                for mi in lst:
                    plan.setdefault(mi, 'keep')
    first = 'body' if 'body' in lk else 'Default'
    for lst in lk[first]:
        for slot, mi in enumerate(lst):
            plan[mi] = PART_ORDER[slot] if slot < len(PART_ORDER) else 'degenerate'
    for look in cover_looks(model, lk, first)[1:]:
        for lst in lk[look]:
            if lst and plan.get(lst[0]) != 'keep':
                plan[lst[0]] = PART_ORDER[0]
    for look, part in (extra or {}).items():
        for lst in lk.get(look, []):
            if lst:
                plan[lst[0]] = part
    for mi in range(len(model.meshes)):
        plan.setdefault(mi, 'degenerate')
    return plan


def set_materials(d, base, override):
    """override {material index: (asset path, name)}: append the strings to the DAT1 string block and point the
    ModelMaterial entry (path/name offsets + crc64(path) / crc32(name)) at them. Offsets are written against the
    pre-edit string base; save_model's rebase adds the header-size delta to every entry."""
    from sm2_common import ALERT
    sys.path.insert(0, ALERT)
    import dat1lib.crc32 as c32
    import dat1lib.crc64 as c64
    mt = bytearray(d.get(0x3250BB80))
    n = len(mt) // 32
    strings = bytearray(d.strings)
    for mi, (path, name) in override.items():
        assert 0 <= mi < n
        path = path.replace('/', chr(92))
        po = base + len(strings)
        strings += path.encode() + bytes(1)
        no = base + len(strings)
        strings += name.encode() + bytes(1)
        struct.pack_into('<IIII', mt, 16 * mi, po, 0, no, 0)
        struct.pack_into('<QII', mt, 16 * (n + mi), c64.hash(path), c32.hash(name), 0)
    strings += bytes(-len(strings) % 4)
    d.strings = bytes(strings)
    d.sections[0x3250BB80] = bytes(mt)


def flag_skinned(d, used):
    """set u2 bit 0x80 on every joint the new skin uses (originals flag exactly their weighted joints)"""
    js = bytearray(d.get(0x15DF9D3B))
    n = len(d.get(0xDCC88A19)) // 48
    for j in used:
        assert 0 <= j < n
        u2 = struct.unpack_from('<H', js, 16 * j + 6)[0]
        struct.pack_into('<H', js, 16 * j + 6, u2 | 0x80)
    d.sections[0x15DF9D3B] = bytes(js)


def raw_block(model, me):
    return model.geom[me.block_off:me.block_off + me.block_size]


def build(model_raw, parts, head_pos, head_joint, keep_materials=True, mat_for_part=None, blank=False, mat_override=None,
          drop_parts=(), share_blocks=False, strip_extra=(), extra_slots=None):
    m = M.Model(model_raw)
    lk = looks(m)
    plan = {mi: 'degenerate' for mi in range(len(m.meshes))} if blank else plan_slots(m, lk, extra_slots)
    plan = {k: ('degenerate' if v in drop_parts else v) for k, v in plan.items()}
    blocks = {}
    for key, d in parts.items():
        blocks[key] = Wr.encode_block(d['P'], d['N'], d['UV'], d['T'], d['J'], d['W'])
    degen = degenerate(head_pos, head_joint)
    recs, geom = bytearray(), bytearray()
    placed = {}
    vs = 0
    lo = np.array([np.inf] * 3)
    hi = -lo
    for me in m.meshes:
        what = plan[me.i]
        lod_mask = me.skin_info >> 16
        if what == 'keep':
            blk = raw_block(m, me)
            geom += bytes(-len(geom) % 16)
            bo = len(geom)
            geom += blk
            r = bytearray(me.rec)
            struct.pack_into('<III', r, 84, vs, bo, len(blk))
            recs += r
            vs += me.vertex_count
            vs += vs % 2
            continue
        blk, st = blocks[what] if what in parts else degen
        key = what if what in parts else 'degenerate'
        mat = me.material
        if what in parts and not keep_materials and what in mat_for_part:
            mat = (me.material & 0xFFFF0000) | mat_for_part[what]
        if share_blocks and key in placed:          # every LOD record of a part points at one block
            bo = placed[key]
        else:
            geom += bytes(-len(geom) % 16)
            bo = len(geom)
            geom += blk
            placed[key] = bo
        recs += Wr.make_record(me.rec, st, mat, vs, bo, len(blk), lod_mask)
        vs += st['vertex_count']
        vs += vs % 2
        if what in parts:
            lo = np.minimum(lo, parts[what]['P'].min(0))
            hi = np.maximum(hi, parts[what]['P'].max(0))
    header, d = B.split_asset(model_raw)
    base = d.string_base()
    if mat_override:
        set_materials(d, base, mat_override)
    for t in B.ZIVA_TAGS + (STRAND_TAGS + MORPH_TAGS if blank else tuple(strip_extra)):
        d.remove(t)
    if parts:
        used = set()
        for pd in parts.values():
            used |= set(np.unique(pd['J'][pd['W'] > 0]).tolist())
        flag_skinned(d, used)
    d.sections[T_SUBSET] = bytes(recs)
    d.sections[T_GEOM] = bytes(geom)
    bt = bytearray(d.get(T_BUILT))
    struct.pack_into('<I', bt, 0, struct.unpack_from('<I', bt, 0)[0] & ~B.BUILT_HAS_ANIMVERT)
    total = sum(struct.unpack_from('<I', recs, 128 * i + 4)[0] for i in range(len(recs) // 128))
    struct.pack_into('<I', bt, 0x44, total)
    if np.isfinite(lo).all():
        c = (lo + hi) / 2
        ext = (hi - lo) / 2
        struct.pack_into('<7f', bt, 0x20, c[0], c[1], c[2], float(np.linalg.norm(ext)), ext[0], ext[1], ext[2])
    d.sections[T_BUILT] = bytes(bt)
    h, body = B.save_model(header, d, base)
    return h + body, dict(plan={str(k): v for k, v in sorted(plan.items())}, looks={k: v[0] for k, v in lk.items()},
                          total_vertices=total, geom_bytes=len(geom), bbox=[lo.tolist(), hi.tolist()])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--target', choices=TARGETS, required=True)
    ap.add_argument('--npz')
    ap.add_argument('--out')
    a = ap.parse_args()
    bdir = os.path.join(WORK, f'build_{a.target}')
    parts = load_parts(a.npz or os.path.join(bdir, 'karin_geo.npz'))
    path = os.path.join(WORK, 'native', TARGETS[a.target])
    raw = open(path, 'rb').read()
    m = M.Model(raw)
    hj = [j['name'] for j in m.joints].index('head')
    head_pos = m.joint_world()[hj][3, :3]
    out, rep = build(raw, parts, head_pos, hj)
    dst = a.out or os.path.join(bdir, os.path.basename(path))
    open(dst, 'wb').write(out)
    json.dump(rep, open(dst + '.json', 'w'), indent=1)
    print(dst, len(out), 'vertices', rep['total_vertices'], 'looks LOD0', rep['looks'])


if __name__ == '__main__':
    main()
