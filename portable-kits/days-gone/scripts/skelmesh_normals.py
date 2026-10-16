"""Write per-vertex normals into a cooked UE 4.11 skeletal mesh's GPU skin vertex buffer, in place (needs numpy).

Layout found in the cooked deacon_head_standard (4 influences, 1 UV channel, half-float UVs): the LOD's
FSkeletalMeshVertexBuffer ends with MeshExtension (1,1,1), MeshOrigin (0,0,0), then the bulk array header
(int32 element size = 32, int32 count) and count vertices of
    TangentX u8[4] | TangentZ u8[4] (W = binormal sign) | bones u8[4] | weights u8[4] | position f32[3] | uv f16[2]
The buffer is located by that header and checked against the reference corners' positions. Only the two packed
tangent fields change; TangentX is re-orthogonalised to the new normal and both W bytes are kept, so the file size and
every offset stay the same.

patch(data, corners) -> (new_data, report); corners = dict(pos (N,3), uv (N,2), normal (N,3)) in UE space
"""
import struct
import numpy as np

STRIDE = 32

def find_buffer(d, pos):
    """offset of the first vertex of the buffer whose positions match the reference corner positions"""
    ref = set(map(tuple, np.round(pos, 2)))
    best = None
    o = d.find(struct.pack('<i', STRIDE))
    while o >= 0:
        n = struct.unpack_from('<i', d, o + 4)[0] if o + 8 <= len(d) else 0
        if 1000 < n < 2_000_000 and o + 8 + STRIDE * n <= len(d) and d[o - 24:o] == struct.pack('<6f', 1, 1, 1, 0, 0, 0):
            v = np.frombuffer(d, dtype=np.uint8, count=STRIDE * n, offset=o + 8).reshape(n, STRIDE)
            p = v[:, 16:28].copy().view('<f4').astype(np.float64)
            hit = sum(tuple(x) in ref for x in np.round(p[::max(1, n // 500)], 2)) / len(p[::max(1, n // 500)])
            if hit > 0.95 and (best is None or hit > best[2]):
                best = (o + 8, n, hit)
        o = d.find(struct.pack('<i', STRIDE), o + 1)
    if best is None:
        raise ValueError('vertex buffer not found')
    return best

def unpack(b):
    return b[..., :3].astype(np.float64) / 127.5 - 1.0

def pack(v):
    return np.clip(np.round(v * 127.5 + 127.5), 0, 255).astype(np.uint8)

def patch(data, corners, max_uv_err=2e-3):
    d = bytearray(data)
    start, n, hit = find_buffer(bytes(d), corners['pos'])
    v = np.frombuffer(d, dtype=np.uint8, count=STRIDE * n, offset=start).reshape(n, STRIDE).copy()
    p = v[:, 16:28].copy().view('<f4').astype(np.float64)
    uv = v[:, 28:32].copy().view('<f2').astype(np.float64)
    # corners grouped by rounded position
    cpos, cuv, cn = corners['pos'], corners['uv'], corners['normal']
    keys = {}
    for i, k in enumerate(map(tuple, np.round(cpos, 2))):
        keys.setdefault(k, []).append(i)
    offs = [(a, b, c) for a in (-.01, 0, .01) for b in (-.01, 0, .01) for c in (-.01, 0, .01)]
    new_n = np.zeros((n, 3)); misses = 0; two_sided = 0; uv_err = np.zeros(n)
    for j in range(n):
        q = np.round(p[j], 2)
        cand = keys.get(tuple(q)) or [i for o in offs for i in keys.get(tuple(np.round(q + o, 2)), ())]
        cand = np.array(cand, dtype=np.int64)
        if len(cand):
            cand = cand[np.linalg.norm(cpos[cand] - p[j], axis=1) < 1e-2]
        if not len(cand):
            misses += 1; new_n[j] = unpack(v[j, 4:8]); continue
        e = np.abs(cuv[cand] - uv[j]).max(axis=1)
        sel = cand[e <= e.min() + 1e-6]
        uv_err[j] = e.min()
        if len(sel) > 1 and (cn[sel] @ cn[sel].T).min() < 0:
            # double-sided geometry: front and back corners share position and UV; keep the side this vertex's
            # computed normal (from its triangles' winding) is on
            side = cn[sel] @ unpack(v[j, 4:8])
            sel = sel[side > 0] if (side > 0).any() else sel
            two_sided += 1
        m = cn[sel].sum(axis=0)
        new_n[j] = m / max(np.linalg.norm(m), 1e-9)
    old_z = unpack(v[:, 4:8]); old_x = unpack(v[:, 0:4])
    tx = old_x - new_n * (old_x * new_n).sum(1)[:, None]
    bad = np.linalg.norm(tx, axis=1) < 1e-4
    if bad.any():   # tangent parallel to the new normal: any perpendicular will do
        alt = np.cross(new_n[bad], np.array([0.0, 0.0, 1.0]))
        alt[np.linalg.norm(alt, axis=1) < 1e-4] = np.cross(new_n[bad][np.linalg.norm(alt, axis=1) < 1e-4], [1.0, 0, 0])
        tx[bad] = alt
    tx /= np.linalg.norm(tx, axis=1)[:, None]
    v[:, 4:7] = pack(new_n); v[:, 0:3] = pack(tx)
    d[start:start + STRIDE * n] = v.tobytes()
    dots = (old_z / np.linalg.norm(old_z, axis=1)[:, None] * new_n).sum(1)
    return bytes(d), {'buffer_offset': start, 'vertices': n, 'sample_hit': round(hit, 4), 'unmatched': misses,
                      'two_sided_resolved': two_sided, 'facing_away_from_winding': int((dots < 0).sum()),
                      'uv_err_max': float(uv_err.max()), 'uv_err_over_limit': int((uv_err > max_uv_err).sum()),
                      'changed_over_10deg': int((dots < np.cos(np.radians(10))).sum()),
                      'mean_dot_old_new': float(dots.mean())}
