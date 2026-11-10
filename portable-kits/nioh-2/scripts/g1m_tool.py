#!/usr/bin/env python3
"""G1M / G1H reader and in-place editor for Rise of the Ronin (KT engine). Standard library only.

Field layouts follow gust_stuff v1.3.13 (eArmada8) g1m_export_meshes.parseG1MS / parseG1MG; nothing here needs gust.

  info                   chunks, G1MG sections, submeshes, palettes, skeleton summary (G1M or G1H)
  hide                   collapse every triangle of the chosen submeshes to one repeated index (zero area, same length)
  collapse-placeholders  the same for the 3-vertex / 3-index placeholder submeshes a replacement leaves behind
  check-binds            compare every palette entry's MM1G matrix with inv(own G1MS world).T

Edits never change the file length, so a G1H (the player's face, a header plus embedded G1Ms) stays valid.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

SECTION_NAMES = {0x00010001: 'GEOMETRY_SOCKETS', 0x00010002: 'MATERIALS', 0x00010003: 'SHADER_PARAMS',
                 0x00010004: 'VERTEX_BUFFERS', 0x00010005: 'VERTEX_ATTRIBUTES', 0x00010006: 'JOINT_PALETTES',
                 0x00010007: 'INDEX_BUFFER', 0x00010008: 'SUBMESH', 0x00010009: 'MESH_LOD'}
SEMANTICS = ('POSITION', 'BLENDWEIGHT', 'BLENDINDICES', 'NORMAL', 'PSIZE', 'TEXCOORD', 'TANGENT', 'BINORMAL',
             'TESSFACTOR', 'POSITIONT', 'COLOR', 'FOG', 'DEPTH', 'SAMPLE')
# data type code -> (name, struct format of one element, element count)
DATA_TYPES = {0x00: ('R32_FLOAT', 'f', 1), 0x01: ('R32G32_FLOAT', 'f', 2), 0x02: ('R32G32B32_FLOAT', 'f', 3),
              0x03: ('R32G32B32A32_FLOAT', 'f', 4), 0x05: ('R8G8B8A8_UINT', 'B', 4), 0x07: ('R16G16B16A16_UINT', 'H', 4),
              0x09: ('R32G32B32A32_UINT', 'I', 4), 0x0A: ('R16G16_FLOAT', 'e', 2), 0x0B: ('R16G16B16A16_FLOAT', 'e', 4),
              0x0D: ('R8G8B8A8_UNORM', 'B', 4)}


class G1MError(ValueError):
    pass


@dataclass
class Chunk:
    magic: str          # as stored on disk, e.g. 'GM1G' for G1MG in a little-endian file
    offset: int         # absolute
    size: int

    @property
    def end(self):
        return self.offset + self.size


@dataclass
class Model:
    """One G1M inside `data` (a G1M file, or a G1H holding it at `base`)."""
    data: bytes
    base: int
    size: int
    chunks: dict = field(default_factory=dict)
    g1mg_version: int = 0
    sections: list = field(default_factory=list)       # dicts: name, magic, offset, size, count
    vertex_buffers: list = field(default_factory=list)  # dicts: stride, count, offset
    attributes: list = field(default_factory=list)      # per set: dict(buffers, attrs[dict(buffer, offset, type, semantic, layer)])
    palettes: list = field(default_factory=list)        # per palette: list of dict(g1mm, physics, joint, external)
    index_buffers: list = field(default_factory=list)   # dicts: count, stride, offset
    submeshes: list = field(default_factory=list)       # dicts named like gust's SUBMESH fields
    materials: list = field(default_factory=list)       # per texture set: list of slot dicts

    def section(self, name):
        return next((s for s in self.sections if s['name'] == name), None)


def u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def parse_chunks(data, base=0):
    if data[base:base + 4] != b'_M1G':
        raise G1MError('not a little-endian G1M')
    size, first, count = u32(data, base + 8), u32(data, base + 12), u32(data, base + 20)
    if base + size > len(data):
        raise G1MError(f'G1M at {base:#x} declares {size} bytes, past the end of the data')
    out, offset = {}, base + first
    for _ in range(count):
        magic = data[offset:offset + 4].decode('ascii', 'replace')
        csize = u32(data, offset + 8)
        if csize < 12 or offset + csize > base + size:
            raise G1MError(f'chunk {magic} at {offset:#x} has invalid size {csize}')
        out[magic] = Chunk(magic, offset, csize)
        offset += csize
    if offset != base + size:
        raise G1MError(f'chunks end at {offset - base}, the header says {size}')
    return out, size


def parse(data, base=0):
    chunks, size = parse_chunks(data, base)
    model = Model(data=data, base=base, size=size, chunks=chunks)
    gm = chunks.get('GM1G')
    if gm is not None:
        _parse_g1mg(model, gm)
    return model


def _parse_g1mg(model, gm):
    d = model.data
    version = model.g1mg_version = u32(d, gm.offset + 4)
    cursor = gm.offset + 48
    for _ in range(u32(d, gm.offset + 44)):
        magic, size, count = struct.unpack_from('<3I', d, cursor)
        if size < 12 or cursor + size > gm.end:
            raise G1MError(f'G1MG section {magic:#x} at {cursor:#x} has invalid size {size}')
        sec = {'name': SECTION_NAMES.get(magic, f'UNKNOWN_{magic:#x}'), 'magic': magic, 'offset': cursor,
               'size': size, 'count': count}
        model.sections.append(sec)
        body = cursor + 12
        if magic == 0x00010002:
            for _ in range(count):
                n = u32(d, body + 4); body += 16
                slots = []
                for _ in range(n):
                    idx, layer, typ, sub, tx, ty = struct.unpack_from('<6H', d, body); body += 12
                    slots.append({'index': idx, 'layer': layer, 'type': typ, 'subtype': sub, 'tile': [tx, ty]})
                model.materials.append(slots)
        elif magic == 0x00010004:
            repository = None
            j = 0
            while j < count:
                _u, stride, n = struct.unpack_from('<3I', d, body)
                body += 16 if version > 0x30303430 else 12
                model.vertex_buffers.append({'stride': stride, 'count': n, 'offset': body})
                if stride == 1:
                    repository = body
                body += stride * n
                j += 1
                # segmented layout: headers flagged 0x80000000 point into the preceding repository buffer
                while j < count and u32(d, body) == 0x80000000:
                    if repository is None:
                        raise G1MError('segmented vertex buffer without a repository')
                    _u, stride, n = struct.unpack_from('<3I', d, body)
                    body += 16 if version > 0x30303430 else 12
                    model.vertex_buffers.append({'stride': stride, 'count': n, 'offset': repository})
                    repository += stride * n
                    j += 1
        elif magic == 0x00010005:
            for _ in range(count):
                k = u32(d, body); buffers = list(struct.unpack_from(f'<{k}I', d, body + 4)); body += 4 + 4 * k
                attrs = []
                n = u32(d, body); body += 4
                for _ in range(n):
                    buf, off = struct.unpack_from('<2H', d, body)
                    typ, _dummy, sem, layer = struct.unpack_from('<4B', d, body + 4); body += 8
                    attrs.append({'buffer': buf, 'offset': off, 'type': typ,
                                  'semantic': SEMANTICS[sem] if sem < len(SEMANTICS) else f'UNKNOWN_{sem}', 'layer': layer})
                model.attributes.append({'buffers': buffers, 'attrs': attrs})
        elif magic == 0x00010006:
            for _ in range(count):
                n = u32(d, body); body += 4
                joints = []
                for _ in range(n):
                    g1mm, phys, joint = struct.unpack_from('<3I', d, body); body += 12
                    ext = joint >= 0x80000000
                    joints.append({'g1mm': g1mm, 'physics': phys ^ 0x80000000 if ext else phys,
                                   'joint': joint ^ 0x80000000 if ext else joint, 'external': ext})
                model.palettes.append(joints)
        elif magic == 0x00010007:
            for _ in range(count):
                n, bits = struct.unpack_from('<2I', d, body)
                body += 12 if version > 0x30303430 else 8
                model.index_buffers.append({'count': n, 'stride': bits // 8, 'offset': body})
                body += n * (bits // 8)
                body += (-(body - gm.offset)) % 4
        elif magic == 0x00010008:
            keys = ('flags', 'vertex_buffer', 'palette', 'bone_index', 'unknown', 'shader', 'material', 'index_buffer',
                    'unknown2', 'primitive', 'vertex_offset', 'vertex_count', 'index_offset', 'index_count')
            for i in range(count):
                model.submeshes.append({'id': i, **dict(zip(keys, struct.unpack_from('<14I', d, body)))})
                body += 56
        cursor += size


def embedded_models(data):
    """Every G1M inside a G1H container (or the file itself when it is a G1M)."""
    if data[:4] == b'_M1G':
        return [parse(data, 0)]
    out, i = [], 0
    while (i := data.find(b'_M1G', i)) >= 0:
        if data[i + 4:i + 8].isdigit() and i + u32(data, i + 8) <= len(data):
            try:
                out.append(parse(data, i))
                i += out[-1].size
                continue
            except (G1MError, struct.error):
                pass
        i += 4
    return out


def submesh_indices(model, sub):
    ib = model.index_buffers[sub['index_buffer']]
    fmt = {2: 'H', 4: 'I'}[ib['stride']]
    start = ib['offset'] + ib['stride'] * sub['index_offset']
    return start, fmt, list(struct.unpack_from(f'<{sub["index_count"]}{fmt}', model.data, start))


def is_hidden(model, sub):
    """True when every triangle of the submesh has zero area by construction (repeated indices)."""
    if sub['index_count'] == 0:
        return True
    _, _, idx = submesh_indices(model, sub)
    return all(len(set(idx[t:t + 3])) == 1 for t in range(0, len(idx) - 2, 3))


def collapse(data, model, subs):
    """Set every index of each submesh to its first index; returns (new bytes, list of edits)."""
    out, edits = bytearray(data), []
    for sub in subs:
        if sub['index_count'] == 0:
            continue
        if sub['primitive'] != 3:
            raise G1MError(f'submesh {sub["id"]}: primitive {sub["primitive"]} is not a triangle list')
        start, fmt, idx = submesh_indices(model, sub)
        struct.pack_into(f'<{len(idx)}{fmt}', out, start, *([idx[0]] * len(idx)))
        edits.append({'submesh': sub['id'], 'offset': start, 'indices': len(idx), 'first_index': idx[0]})
    return bytes(out), edits


# ---- skeleton and binds ------------------------------------------------------------------------------------------

def _qmul(a, b):
    aw, ax, ay, az = a; bw, bx, by, bz = b
    return (aw * bw - ax * bx - ay * by - az * bz, aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw)


def _qrot(q, v):
    w, x, y, z = q
    p = _qmul(_qmul(q, (0.0, *v)), (w, -x, -y, -z))
    return p[1:]


def _qmat(q):
    w, x, y, z = q
    n = math.sqrt(w * w + x * x + y * y + z * z) or 1.0
    w, x, y, z = w / n, x / n, y / n, z / n
    return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]


def skeleton(model):
    """G1MS joints in storage order: dict(parent (storage index), local q (w,x,y,z), local p, world q, world p,
    world 4x4 [R|p] column form), and `by_id`: bone id -> storage index.

    The bone id is what palettes store as jointIndex, what gust names bones by (bone_<id>) and what animation uses;
    the G1MS id list maps it to the storage index (gust: boneIDList / boneToBoneID). They are not the same numbers."""
    sm = model.chunks.get('SM1G')
    if sm is None:
        raise G1MError('no SM1G (skeleton) chunk')
    d, o = model.data, sm.offset
    joint_offset = u32(d, o + 12)
    count, id_count = struct.unpack_from('<2H', d, o + 20)
    ids = struct.unpack_from(f'<{id_count}H', d, o + 28)
    by_id = {k: j for k, j in enumerate(ids) if j != 0xFFFF}
    joints = []
    for i in range(count):
        p = o + joint_offset + 48 * i
        parent = struct.unpack_from('<i', d, p + 12)[0]
        x, y, z, w = struct.unpack_from('<4f', d, p + 16)
        pos = struct.unpack_from('<3f', d, p + 32)
        q = (w, x, y, z)
        if parent >= 0:
            pq, pp = joints[parent]['world_q'], joints[parent]['world_p']
            wq = _qmul(pq, q)
            n = math.sqrt(sum(c * c for c in wq)); wq = tuple(c / n for c in wq)
            wp = tuple(a + b for a, b in zip(_qrot(pq, pos), pp))
        else:
            wq, wp = q, pos
        r = _qmat(wq)
        joints.append({'parent': parent, 'local_q': q, 'local_p': pos, 'world_q': wq, 'world_p': wp,
                       'world': [r[0] + [wp[0]], r[1] + [wp[1]], r[2] + [wp[2]], [0.0, 0.0, 0.0, 1.0]]})
    return joints, by_id


def native_bind(world):
    """inv(world).T in the row-major order MM1G stores (world is a rigid [R|p])."""
    r = [row[:3] for row in world[:3]]
    p = [world[i][3] for i in range(3)]
    t = [-sum(r[k][i] * p[k] for k in range(3)) for i in range(3)]   # -R^T p
    # inv(world) = [R^T | t]; its transpose has R in the upper left and t in the bottom row
    return [r[0] + [0.0], r[1] + [0.0], r[2] + [0.0], t + [1.0]]


def binds(model):
    mm = model.chunks.get('MM1G')
    if mm is None:
        raise G1MError('no MM1G (inverse bind) chunk')
    n = u32(model.data, mm.offset + 12)
    return [[list(struct.unpack_from('<4f', model.data, mm.offset + 16 + 64 * i + 16 * r)) for r in range(4)]
            for i in range(n)]


def bind_errors(model):
    joints, by_id = skeleton(model)
    mats = binds(model)
    out = []
    for p, palette in enumerate(model.palettes):
        for k, e in enumerate(palette):
            if e['external'] or e['joint'] not in by_id or e['g1mm'] >= len(mats):
                out.append({'palette': p, 'entry': k, 'joint': e['joint'], 'error': None})
                continue
            want = native_bind(joints[by_id[e['joint']]]['world'])
            err = max(abs(a - b) for ra, rb in zip(mats[e['g1mm']], want) for a, b in zip(ra, rb))
            out.append({'palette': p, 'entry': k, 'joint': e['joint'], 'g1mm': e['g1mm'], 'error': err})
    return out


# ---- writers used by other kit scripts ---------------------------------------------------------------------------

def replace_section(data, model, name, body):
    """Replace one G1MG section's payload (after its 12-byte header); fixes the section, GM1G and file sizes.
    Only valid for a stand-alone G1M (base 0) with GM1G as the chunk that grows."""
    if model.base != 0:
        raise G1MError('section growth is only supported for a stand-alone G1M')
    sec = model.section(name)
    gm = model.chunks['GM1G']
    new = struct.pack('<3I', sec['magic'], 12 + len(body), sec['count']) + body
    out = bytearray(data[:sec['offset']] + new + data[sec['offset'] + sec['size']:])
    delta = len(new) - sec['size']
    struct.pack_into('<I', out, gm.offset + 8, gm.size + delta)
    struct.pack_into('<I', out, 8, len(out))
    return bytes(out)


def palettes_body(palettes):
    body = bytearray()
    for joints in palettes:
        body += struct.pack('<I', len(joints))
        for e in joints:
            flag = 0x80000000 if e['external'] else 0
            body += struct.pack('<3I', e['g1mm'], e['physics'] ^ flag, e['joint'] ^ flag)
    return bytes(body)


def append_binds(data, matrices):
    """Append 4x4 row-major matrices to MM1G and raise FM1G's matrix count (u32 at +24) to match."""
    model = parse(data)
    mm, fm = model.chunks['MM1G'], model.chunks['FM1G']
    count = u32(data, mm.offset + 12)
    if u32(data, fm.offset + 24) != count:
        raise G1MError('FM1G +24 does not hold the MM1G matrix count; refusing to guess')
    extra = b''.join(struct.pack('<16f', *[v for row in m for v in row]) for m in matrices)
    out = bytearray(data[:mm.end] + extra + data[mm.end:])
    struct.pack_into('<2I', out, mm.offset + 8, mm.size + len(extra), count + len(matrices))
    fm_offset = fm.offset + (len(extra) if fm.offset > mm.offset else 0)
    struct.pack_into('<I', out, fm_offset + 24, count + len(matrices))
    struct.pack_into('<I', out, 8, len(out))
    return bytes(out), count


# ---- CLI ---------------------------------------------------------------------------------------------------------

def describe(model):
    subs = []
    for s in model.submeshes:
        subs.append({k: s[k] for k in ('id', 'vertex_buffer', 'palette', 'material', 'shader', 'index_buffer',
                                       'vertex_count', 'index_count')} | {'hidden': is_hidden(model, s)})
    info = {'offset': model.base, 'bytes': model.size,
            'chunks': [{'magic': c.magic, 'size': c.size} for c in model.chunks.values()],
            'sections': [{k: s[k] for k in ('name', 'size', 'count')} for s in model.sections],
            'vertex_buffers': model.vertex_buffers and [{k: b[k] for k in ('stride', 'count')} for b in model.vertex_buffers],
            'attribute_sets': [{'buffers': a['buffers'], 'attrs': [
                f"{x['semantic']}{x['layer']}:{DATA_TYPES.get(x['type'], (hex(x['type']),))[0]}@{x['buffer']}+{x['offset']}"
                for x in a['attrs']]} for a in model.attributes],
            'palettes': [[e['joint'] for e in p] for p in model.palettes],
            'submeshes': subs}
    if 'SM1G' in model.chunks:
        joints, by_id = skeleton(model)
        info['skeleton'] = {'joints': len(joints), 'bone_ids': len(by_id),
                            'bone_id_equals_storage_index': all(by_id.get(j) == j for j in range(len(joints)))}
    if 'MM1G' in model.chunks:
        info['mm1g_matrices'] = u32(model.data, model.chunks['MM1G'].offset + 12)
    return info


def write_new(path, data):
    path = Path(path)
    if path.exists():
        raise SystemExit(f'refusing to overwrite {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def cmd_info(args):
    data = Path(args.input).read_bytes()
    models = embedded_models(data)
    report = {'file': Path(args.input).name, 'container': data[:4].decode('ascii', 'replace'), 'bytes': len(data),
              'sha256': hashlib.sha256(data).hexdigest(), 'models': [describe(m) for m in models]}
    text = json.dumps(report, indent=1)
    if args.json:
        write_new(args.json, text.encode())
    print(text if not args.json else f'{len(models)} model(s) -> {args.json}')


def cmd_hide(args):
    data = Path(args.input).read_bytes()
    out, report = data, []
    for model in embedded_models(data):
        if not model.submeshes:
            continue
        chosen = model.submeshes if args.all else [s for s in model.submeshes if s['id'] in args.submeshes]
        model = parse(out, model.base)
        out, edits = collapse(out, model, chosen)
        report.append({'offset': model.base, 'edits': edits})
    if not any(r['edits'] for r in report):
        raise SystemExit('nothing to hide')
    assert len(out) == len(data)
    for model in embedded_models(out):
        for s in model.submeshes:
            if args.all or s['id'] in args.submeshes:
                assert is_hidden(model, s), s['id']
    write_new(args.output, out)
    print(json.dumps({'output': str(args.output), 'sha256': hashlib.sha256(out).hexdigest(),
                      'triangles_collapsed': sum(e['indices'] // 3 for r in report for e in r['edits']),
                      'bytes_changed': sum(a != b for a, b in zip(data, out)), 'models': report}, indent=1))


def cmd_placeholders(args):
    data = Path(args.input).read_bytes()
    model = parse(data)
    chosen = [s for s in model.submeshes if s['vertex_count'] == 3 and s['index_count'] == 3 and not is_hidden(model, s)]
    out, edits = collapse(data, model, chosen)
    if not edits:
        raise SystemExit('no visible 3-vertex/3-index placeholder submesh')
    write_new(args.output, out)
    print(json.dumps({'output': str(args.output), 'placeholders': edits, 'sha256': hashlib.sha256(out).hexdigest()}, indent=1))


def cmd_binds(args):
    model = parse(Path(args.input).read_bytes())
    rows = bind_errors(model)
    if args.palette is not None:
        rows = [r for r in rows if r['palette'] == args.palette]
    bad = [r for r in rows if r['error'] is None or r['error'] > args.tolerance]
    print(json.dumps({'entries': len(rows), 'native': len(rows) - len(bad), 'non_native': bad}, indent=1))
    return 1 if bad and args.strict else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('info'); p.add_argument('input'); p.add_argument('--json', help='write the report here (new file)')
    p = sub.add_parser('hide'); p.add_argument('input'); p.add_argument('--output', required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--all', action='store_true', help='every submesh of every embedded model')
    g.add_argument('--submeshes', type=lambda s: {int(x) for x in s.split(',')}, help='e.g. 0,3,5')
    p = sub.add_parser('collapse-placeholders'); p.add_argument('input'); p.add_argument('--output', required=True)
    p = sub.add_parser('check-binds'); p.add_argument('input'); p.add_argument('--palette', type=int)
    p.add_argument('--tolerance', type=float, default=1e-3); p.add_argument('--strict', action='store_true')
    args = ap.parse_args(argv)
    return {'info': cmd_info, 'hide': cmd_hide, 'collapse-placeholders': cmd_placeholders,
            'check-binds': cmd_binds}[args.cmd](args) or 0


if __name__ == '__main__':
    sys.exit(main())
