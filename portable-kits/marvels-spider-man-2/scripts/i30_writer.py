"""Encode plain skinned (fmt 1) i30 mesh blocks and rebuild ModelSubset + ModelSubsetGeomData.

Block (fmt 1): 16 B vertices | u16 indices | pad to 4 | skin batches | batch table (u16 off/4, u16 info).
Vertex: i16 x,y,z (1/4096 m), i16 w (tangent: |w| = 0x5800 + 11 bits, sign = -handedness; written neutral),
        u32 normal (10/10 bits sphere-map + bit31 = z >= 0; bits 20-30 tangent, written 0), i16 u,v (x16384).
Skin batch: 32 slots; table info = (g-1)<<5 (bits 5-8) | offset bits 16-19 (bits 0-3); bit 4 (u16 joints) and
        bit 9 (+256 joint base) are never written; 0x2000 only on anim-vert models (see i30_model.decode_skin);
        g = max influences in the batch; g = 1 -> absolute joint byte; else per slot g pairs
        (joint delta from the previous joint, ascending; weight byte), weights sum to 256, padding (0, 0).
"""
import struct
import numpy as np

SQ2 = np.sqrt(2.0)
NK = 0.00276483595


def encode_normal(N):
    N = N / np.linalg.norm(N, axis=1, keepdims=True).clip(1e-12)
    q = 2.0 * (1.0 - np.abs(N[:, 2]))                    # x^2 + y^2 of the stored (sphere-map) pair
    w = np.sqrt(np.clip(1.0 - q / 4.0, 1e-12, None))
    x = N[:, 0] / w
    y = N[:, 1] / w
    a = np.clip(np.rint((x + SQ2) / NK), 0, 1023).astype(np.int64)
    b = np.clip(np.rint((y + SQ2) / NK), 0, 1023).astype(np.int64)
    sign = (N[:, 2] >= 0).astype(np.int64)
    return (a | (b << 10) | (sign << 31)).astype(np.uint32)


def quantize_weights(J, W):
    """-> list per vertex of [(joint, byte)] ascending joint, bytes sum to 256 (each <= 255)."""
    out = []
    for jr, wr in zip(J, W):
        d = {}
        for j, w in zip(jr, wr):
            if w > 0:
                d[int(j)] = d.get(int(j), 0.0) + float(w)
        s = sum(d.values())
        items = sorted(d.items())
        raw = [w / s * 256.0 for _, w in items]
        q = [int(np.floor(r)) for r in raw]
        rem = 256 - sum(q)
        for i in np.argsort([-(r - np.floor(r)) for r in raw])[:rem]:
            q[i] += 1
        pairs = [(j, b) for (j, _), b in zip(items, q) if b > 0]
        fixed = []
        for j, b in pairs:                                  # a 256 share does not fit a byte: 255 + 1 on the same joint
            if b > 255:
                fixed += [(j, 255), (j, b - 255)]
            else:
                fixed.append((j, b))
        out.append(fixed)
    return out


def encode_skin(J, W):
    vw = quantize_weights(J, W)
    rows = []
    for v in vw:                                   # (delta, weight) pairs; (255, 0) stepping stones reach joints > 255
        prev, row = 0, []
        for j, b in v:
            while j - prev > 255:
                row.append((255, 0))
                prev += 255
            row.append((j - prev, b))
            prev = j
        rows.append(row)
    n = len(vw)
    data = bytearray()
    table = []
    for b0 in range(0, n, 32):
        chunk = vw[b0:b0 + 32]
        crow = rows[b0:b0 + 32]
        g = max(len(r) for r in crow)
        single = g == 1 and all(len(v) == 1 and v[0][1] == 256 and v[0][0] <= 255 for v in chunk)
        if g == 1 and not single:
            g = 2
        if g > 16:
            raise ValueError('more than 16 influences (incl. stepping stones)')
        off = len(data)
        assert off % 4 == 0
        for s in range(32):
            if single:
                data.append(chunk[s][0][0] if s < len(chunk) else 0)
                continue
            row = [x for pr in (crow[s] if s < len(crow) else []) for x in pr]
            row += [0, 0] * (g - len(row) // 2)
            if any(x < 0 or x > 255 for x in row):
                raise ValueError(f'skin byte out of range {row}')
            data += bytes(row)
        o4 = off // 4
        if o4 >> 20:                               # bit 4 of info is the u16-joint flag
            raise ValueError('skin data too large')
        table.append((o4 & 0xFFFF, ((g - 1) << 5) | (o4 >> 16)))
    return bytes(data), table


def encode_block(P, N, UV, T, J, W, pos_scale=1.0 / 4096):
    v = len(P)
    if v > 65535:
        raise ValueError('mesh over 65535 vertices')
    q = np.rint(P / pos_scale)
    if np.abs(q).max() > 32767:
        raise ValueError('position out of int16 range')
    uv = np.clip(np.rint(UV * 16384.0), -32768, 32767)
    vert = np.zeros(v, dtype=[('x', '<i2'), ('y', '<i2'), ('z', '<i2'), ('w', '<i2'), ('n', '<u4'), ('u', '<i2'), ('v', '<i2')])
    vert['x'], vert['y'], vert['z'] = q[:, 0], q[:, 1], q[:, 2]
    vert['w'] = -(0x5800 + 1024)                          # neutral tangent word (flat normal maps planned)
    vert['n'] = encode_normal(N)
    vert['u'], vert['v'] = uv[:, 0], uv[:, 1]
    blk = bytearray(vert.tobytes())
    index_off = len(blk)
    idx = np.asarray(T, np.int64).reshape(-1)
    assert idx.max() < v
    blk += idx.astype('<u2').tobytes()
    blk += bytes(-len(blk) % 4)
    skin_off = len(blk)
    sk, table = encode_skin(J, W)
    blk += sk
    tab_off = len(blk)
    for o, info in table:
        blk += struct.pack('<HH', o, info)
    # stats used by the record
    tri = idx.reshape(-1, 3)
    e = np.concatenate([np.linalg.norm(P[tri[:, a]] - P[tri[:, b]], axis=1) for a, b in ((1, 0), (2, 1), (0, 2))])
    area = 0.5 * np.linalg.norm(np.cross(P[tri[:, 1]] - P[tri[:, 0]], P[tri[:, 2]] - P[tri[:, 0]]), axis=1).sum()
    u1, u2 = UV[tri[:, 1]] - UV[tri[:, 0]], UV[tri[:, 2]] - UV[tri[:, 0]]
    uv_area = 0.5 * np.abs(u1[:, 0] * u2[:, 1] - u1[:, 1] * u2[:, 0]).sum()
    return bytes(blk), dict(vertex_count=v, index_count=len(idx), index_off=index_off, skin_off=skin_off,
                            skinbatch_off=tab_off, area=float(area), uv_area=float(uv_area),
                            max_edge=int(np.rint(e.max() / pos_scale)) if len(e) else 0)


def make_record(template, st, material, vertex_start, block_off, block_size, lod_mask):
    r = bytearray(template)
    struct.pack_into('<IIII', r, 0, st['index_count'], st['vertex_count'], 0, st['index_off'])
    struct.pack_into('<I', r, 16, 0xFFFF)
    struct.pack_into('<I', r, 20, 1)                       # fmt 1: plain skinned, no second stream
    struct.pack_into('<f', r, 24, 1.0 / 4096)
    struct.pack_into('<I', r, 28, material)
    struct.pack_into('<ff', r, 32, st['area'], st['uv_area'])
    r[40:52] = bytes(12)
    struct.pack_into('<10I', r, 64, 0, 0, 0, st['skin_off'], st['skinbatch_off'], vertex_start, block_off, block_size,
                     st['vertex_count'], lod_mask << 16)
    r[104:116] = bytes(12)
    struct.pack_into('<HH', r, 116, 0, min(st['max_edge'], 0xFFFF))
    struct.pack_into('<I', r, 124, 0)
    return bytes(r)


def build_subset(slots):
    """slots: list of dict(template=128B record, block=(bytes, stats), material=int, lod_mask=int)
    -> (subset bytes, geom bytes, total vertices)"""
    geom = bytearray()
    recs = bytearray()
    vs = 0
    for s in slots:
        blk, st = s['block']
        geom += bytes(-len(geom) % 16)
        bo = len(geom)
        geom += blk
        recs += make_record(s['template'], st, s['material'], vs, bo, len(blk), s['lod_mask'])
        vs += st['vertex_count']
        vs += vs % 2
    return bytes(recs), bytes(geom), sum(s['block'][1]['vertex_count'] for s in slots)
