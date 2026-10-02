"""In-place character build for MESH_heroa00_0.

GoWR pre-sizes per-mesh resources from the shipped layout, so a def may never exceed the vertex/index room it
had (measured from the original stream buffer). New geometry is therefore written into the original buffers at
their original offsets, stream buffers keep their size, and replaced buffers get their hash bumped by one so the
patch lodpack wins over root.lodpack.
"""
import struct
import numpy as np
from wad import Wad
from mesh import parse_mesh
from encode import write_in_place, capacity
from geometry import subset, merge
from build_mesh import root_buffer, write_lodpack_single_group
from decode import decode
import collections, copy



def slot_traits(m, buf):
    """Values to inherit from the original mesh in this slot: packed attribute 15 and the integer UV tile per channel."""
    mm = copy.copy(m); mm.icount = 0
    out, _ = decode(mm, buf)
    a15 = None; tiles = {}; inherit = {}
    from mesh import DT_SIZE
    for (pt, dt, n, co, bi) in m.comps:
        if pt in (14,):     # unknown per-vertex data: reuse the most common raw value of the original mesh
            st = m.strides[bi]; size = DT_SIZE[dt] * n
            vals = [bytes(buf[m.buf_offs[bi] + co + st * v: m.buf_offs[bi] + co + st * v + size]) for v in range(m.vcount)]
            inherit[pt] = collections.Counter(vals).most_common(1)[0][0]
    for (pt, dt, n), vals in out.items():
        if pt == 15:
            a15 = collections.Counter(v[0] for v in vals).most_common(1)[0][0]
        if pt in (3, 4, 5, 6) and vals:
            a = np.array(vals, float)
            tiles[pt] = tuple(np.floor(a.min(0) + 1e-4).tolist())
    return a15, tiles, inherit


def build(base_wad_path, lod_geos, plan, keep_group_ids, out_wad, out_lodpack, passthrough=None, dummy=None,
          mesh_entry='MESH_heroa00_0', gpu_entry='MG_heroa00_0_gpu', pad_joint=1447):
    """lod_geos: {lod_key: geo}; plan: {def_index: (lod_key, [part names])};
    keep_group_ids: def indices that stay untouched; every other def is emptied.
    passthrough: {hash_in_wad: original_hash} buffers re-shipped unchanged under the bumped hash."""
    w = Wad(open(base_wad_path, 'rb').read())
    data = bytearray(w.data)
    me = [e for e in w.entries if e.name == mesh_entry and e.type == 1][0]
    ge = [e for e in w.entries if e.name == gpu_entry][0]
    he = w.entries[1]
    mb = bytearray(w.get(me)); gpu = bytearray(w.get(ge)); hdr = bytearray(w.get(he))
    ms = parse_mesh(bytes(mb))

    # group defs by the stream buffer they live in (hash 0 = in-WAD gpu entry)
    by_hash = {}
    for m in ms:
        by_hash.setdefault(m.hash, []).append(m)

    buffers, report = {}, {}
    touched_hashes = {}
    for di, (lod_key, parts) in plan.items():
        m = ms[di]
        touched_hashes.setdefault(m.hash, []).append(di)
    for h, defs in touched_hashes.items():
        if h == 0:
            buf = gpu
        else:
            orig_h = h if h not in (passthrough or {}) else passthrough[h]
            # the reference mod may already have bumped this hash; the shipped data sits under hash-1
            try:
                buf = bytearray(root_buffer(h))
                orig_h = h
            except KeyError:
                buf = bytearray(root_buffer(h - 1))
                orig_h = h - 1
        siblings = sorted(by_hash[h], key=lambda m: m.buf_offs[0] if m.buf_count else 0)
        ends = {}
        for k, s in enumerate(siblings):
            nxt = siblings[k + 1].buf_offs[0] if k + 1 < len(siblings) else len(buf)
            ends[s.i] = nxt
        for di in defs:
            m = ms[di]
            lod_key, parts = plan[di]
            if lod_key == 'mixed':          # [(part, level), ...]
                g = merge([subset(lod_geos[k], [p]) for p, k in parts])
            else:
                g = subset(lod_geos[lod_key], parts)
            V, F = len(g['P']), len(g['IDX'])
            vcap, icap = capacity(m, ends[di])
            if V > vcap or F * 3 > icap:
                raise ValueError(f'def {di}: {V} verts/{F*3} idx exceed room {vcap}/{icap}')
            a15, tiles, inherit = slot_traits(m, bytes(buf))
            write_in_place(buf, m, g, a15, pad_joint, tiles, inherit)
            lo, hi = g['P'].min(0), g['P'].max(0)
            struct.pack_into('<3f', mb, m.off + 0x10, *((hi - lo) / 2))
            struct.pack_into('<3f', mb, m.off + 0x1C, *((hi + lo) / 2))
            struct.pack_into('<II', mb, m.off + 0x44, V, F)
            struct.pack_into('<I', mb, m.off + 0x5C, F * 3)
            report[di] = dict(lod=lod_key, verts=V, idx=F * 3, room=(vcap, icap), hash=hex(h), attr15=a15, uv_tiles=tiles)
        if h != 0:
            new_h = orig_h + 1
            buffers[new_h] = bytes(buf)
            for s in by_hash[h]:
                struct.pack_into('<Q', mb, s.off + 0x68, new_h)
            if h != new_h:
                pat = struct.pack('<Q', h)
                i = hdr.find(pat)
                while i >= 0:
                    hdr[i:i + 8] = struct.pack('<Q', new_h)
                    i = hdr.find(pat, i + 8)
    for h_wad, h_orig in (passthrough or {}).items():
        if h_wad not in buffers:
            buffers[h_wad] = root_buffer(h_orig)
    # Hidden meshes: an MG group whose meshes are all empty stalls the loader, so instead of zero counts every
    # hidden def draws one degenerate triangle from an all-zero block inside the (resident) LOD0 body buffer.
    keep = set(plan) | set(keep_group_ids)
    dummy_hash = dummy_off = None
    # The block must live in a shipped (bumped) stream buffer: pointing hidden defs into the in-WAD gpu entry
    # (hash 0) drew stray triangles in game.
    if dummy is not None:
        dummy_hash, dummy_off = dummy
        b = bytearray(buffers[dummy_hash]); b[dummy_off:dummy_off + 0x100] = bytes(0x100); buffers[dummy_hash] = bytes(b)
    for m in ms:
        if m.i in keep:
            continue
        if dummy is None:
            struct.pack_into('<II', mb, m.off + 0x44, 0, 0)
            struct.pack_into('<I', mb, m.off + 0x5C, 0)
            continue
        struct.pack_into('<II', mb, m.off + 0x44, 1, 1)
        struct.pack_into('<I', mb, m.off + 0x5C, 3)
        struct.pack_into('<Q', mb, m.off + 0x68, dummy_hash)
        struct.pack_into('<I', mb, m.off + 0x30, dummy_off + 0x80)
        struct.pack_into('<I', mb, m.off + 0x3C, dummy_off)
        for j in range(m.buf_count):
            struct.pack_into('<I', mb, m.off + m.buf_off_off + 4 * j, dummy_off)
    data[me.abs:me.abs + me.size] = mb
    data[ge.abs:ge.abs + ge.size] = gpu
    data[he.abs:he.abs + he.size] = hdr
    open(out_wad, 'wb').write(data)
    write_lodpack_single_group(out_lodpack, buffers)
    return report
