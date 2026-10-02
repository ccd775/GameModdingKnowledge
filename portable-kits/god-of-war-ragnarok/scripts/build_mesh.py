"""Build the replacement r_heroa00.wad + lodpack buffers for a fitted character.

Slots: the Kratos head mesh of group 230 at LOD0..LOD3 carries the whole new body; every other MESH def
of MESH_heroa00_0 (rest of Kratos, trousers group 267, all armour variants, LOD4) is emptied.
"""
import struct, collections, copy
import numpy as np
from wad import Wad
from mesh import parse_mesh
from decode import decode
from encode import build_buffer, patch_def, zero_def
from packs import read_lodpack_toc
from gamedir import wad_dir

MESH_ENTRY = 'MESH_heroa00_0'
HEADER_ENTRY_IDX = 1
SLOTS = {1138: 0x167745b9b547165a, 1144: 0x6d78060030afb059, 1150: 0x87c392a4fd4d1cd8, 1154: 0xe4d4dd54884159f5}
# hashes the reference mod bumped by one and that must point back at the shipped data
RESTORE = {0x2a5ef0f242a705b6: 0x2a5ef0f242a705b5}
PAD_JOINT = 1447


def root_buffer(h):
    g, mem, _ = read_lodpack_toc(wad_dir() + '/root.lodpack.toc')
    gi, mo, size = mem[h]
    with open(wad_dir() + '/root.lodpack', 'rb') as f:
        f.seek(g[gi][0] + mo)
        return f.read(size)


def head_attr15(ms):
    """Most common value of the packed attribute 15 on Kratos's original head (LOD0)."""
    orig = root_buffer(SLOTS[1138])
    m = copy.copy(ms[1138]); m.vcount = 21769; m.icount = 0
    out, _ = decode(m, orig)
    vals = [v[0] for k, vv in out.items() if k[0] == 15 for v in vv]
    return collections.Counter(vals).most_common(1)[0][0]


def replace_hash_and_size(hdr, old_h, new_h, new_size):
    pat = struct.pack('<Q', old_h)
    n = 0; i = hdr.find(pat)
    while i >= 0:
        hdr[i:i + 8] = struct.pack('<Q', new_h)
        if new_size is not None:
            struct.pack_into('<I', hdr, i + 8, new_size)
        n += 1
        i = hdr.find(pat, i + 8)
    return n


def build(base_wad_path, geo, out_wad_path, slots=None, zero_scope='all'):
    slots = slots or SLOTS
    w = Wad(open(base_wad_path, 'rb').read())
    data = bytearray(w.data)
    me = [e for e in w.entries if e.name == MESH_ENTRY and e.type == 1][0]
    he = w.entries[HEADER_ENTRY_IDX]
    mb = bytearray(w.get(me)); hdr = bytearray(w.get(he))
    ms = parse_mesh(bytes(mb))
    a15 = head_attr15(ms)

    lo, hi = geo['P'].min(0), geo['P'].max(0)
    V, F = len(geo['P']), len(geo['IDX'])
    buffers = {}
    report = {'attr15': hex(a15), 'verts': V, 'tris': F, 'slots': {}}
    current = {i: ms[i].hash for i in slots}
    for i, orig_h in slots.items():
        m = ms[i]
        new_h = orig_h + 1
        buf, offs, ind_off = build_buffer(m, geo, a15, PAD_JOINT)
        buffers[new_h] = buf
        patch_def(mb, m, V, F * 3, F, offs, ind_off, new_h, (lo, hi))
        # the stream manifest in the WAD header lists the hash (as shipped or as bumped by the reference mod)
        n = replace_hash_and_size(hdr, current[i], new_h, len(buf))
        report['slots'][i] = dict(hash=hex(new_h), size=len(buf), header_refs=n)
    for m in ms:
        if m.i in slots:
            continue
        if zero_scope == 'all' or (isinstance(zero_scope, (set, list, tuple)) and m.i in zero_scope):
            zero_def(mb, m)
    for old, new in RESTORE.items():
        for m in ms:
            if m.hash == old:
                struct.pack_into('<Q', mb, m.off + 0x68, new)
        replace_hash_and_size(hdr, old, new, None)
    # other defs sharing the slot buffers must not reference the old/bumped hash with stale offsets
    for m in ms:
        if m.i not in slots and (m.hash in current.values() or m.hash in slots.values()):
            struct.pack_into('<Q', mb, m.off + 0x68, next(h + 1 for s, h in slots.items() if m.hash in (h, current[s])))
            for j in range(m.buf_count):
                struct.pack_into('<I', mb, m.off + m.buf_off_off + 4 * j, 0)
            struct.pack_into('<I', mb, m.off + 0x30, 0)
            struct.pack_into('<I', mb, m.off + 0x3C, 0)
    data[me.abs:me.abs + me.size] = mb
    data[he.abs:he.abs + he.size] = hdr
    open(out_wad_path, 'wb').write(data)
    return buffers, report


def write_lodpack(path, buffers):
    """One group per buffer, matching the base game's root.lodpack layout."""
    items = sorted(buffers.items())
    n = len(items)
    head = 16 + 24 * n * 2
    off = (head + 15) & ~15
    groups, members, blob = [], [], bytearray()
    for gi, (h, b) in enumerate(items):
        groups.append(struct.pack('<QQII', off + len(blob), h, len(b), 0))
        members.append(struct.pack('<IIQII', gi, 0, h, len(b), 0))
        blob += b
        blob += b'\0' * (((len(blob) + 15) & ~15) - len(blob))
    toc = struct.pack('<IIQ', n, n, 1 << 32) + b''.join(groups) + b''.join(members)
    toc += b'\0' * (off - len(toc))
    open(path, 'wb').write(toc + blob)
    open(path + '.toc', 'wb').write(toc[:head])


def write_lodpack_single_group(path, buffers):
    """All members in one raw group placed right after the TOC (the layout the working reference mod uses)."""
    items = sorted(buffers.items())
    n = len(items)
    head = 16 + 24 + 24 * n
    members, blob = [], bytearray()
    for h, b in items:
        members.append(struct.pack('<IIQII', 0, len(blob), h, len(b), 0))
        blob += b
    group = struct.pack('<QQII', head, items[-1][0], len(blob), 0)
    toc = struct.pack('<IIQ', 1, n, 1 << 32) + group + b''.join(members)
    open(path, 'wb').write(toc + blob)
    open(path + '.toc', 'wb').write(toc)
