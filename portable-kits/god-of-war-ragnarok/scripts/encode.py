"""Encode vertex/index data into a GoWR MESH definition's vertex format."""
import struct
import numpy as np
from mesh import DT_SIZE

def snorm10(v, w):
    q = np.clip(np.round(np.asarray(v) * 512.0 + 511.0), 0, 1023).astype(np.uint32)
    return q[:, 0] | (q[:, 1] << 10) | (q[:, 2] << 20) | (np.uint32(w) << 30)

def pack_joints(js):
    """10 joints, 11 bits each, MSB-first across 4 u32."""
    bits = 0
    for j in js:
        bits = (bits << 11) | (int(j) & 2047)
    bits <<= 128 - 11 * len(js)
    return [(bits >> (96 - 32 * k)) & 0xffffffff for k in range(4)]

def pack_weights(ws, words=3):
    """3*words explicit 10-bit unorm weights (3 per u32); the last influence is implicit.
    Quantise so the explicit ones sum exactly to 1023 when the implicit slot is empty."""
    ne = 3 * words
    q = [int(round(w * 1023)) for w in ws[:ne]]
    if len(ws) <= ne and q:
        q[0] += 1023 - sum(q)
    q += [0] * (ne - len(q))
    return [q[3*k] | (q[3*k+1] << 10) | (q[3*k+2] << 20) for k in range(words)]

def max_influences(m):
    """Influences per vertex the def's weight component can carry (packed u32s hold 3 + 1 implicit)."""
    for (pt, dt, n, co, bi) in m.comps:
        if pt == 10:
            return 3 * n + 1 if dt == 2 else 4
    return None

def limit_influences(INF, k):
    out = []
    for inf in INF:
        inf = inf[:k]; s = sum(w for _, w in inf)
        out.append([(j, w / s) for j, w in inf])
    return out

def encode_streams(m, geo, attr15, pad_joint, uv_offset=None, inherit=None):
    """Return a list of per-buffer bytes for MESH def `m` (layout taken from its components)."""
    V = len(geo['P'])
    bufs = [np.zeros((V, s), np.uint8) for s in m.strides]
    P, N, T, UV, INF = geo['P'], geo['N'], geo['T'], geo['UV'], geo['INF']
    k = max_influences(m)
    if k is not None and any(len(inf) > k for inf in INF):
        INF = limit_influences(INF, k)
    uv_offset = uv_offset or {}
    pad_of = (lambda inf: pad_joint) if pad_joint is not None else (lambda inf: inf[0][0])
    for (pt, dt, n, co, bi) in m.comps:
        b = bufs[bi]
        if pt == 0 and dt == 0 and n == 3:
            col = P.astype('<f4').view(np.uint8).reshape(V, 12)
        elif pt in (1, 16) and dt == 3 and n == 1:
            col = snorm10(N, 0).astype('<u4').view(np.uint8).reshape(V, 4)
        elif pt == 2 and dt == 3 and n == 1:
            col = snorm10(T, 3).astype('<u4').view(np.uint8).reshape(V, 4)
        elif pt in (3, 4, 5) and dt == 6 and n == 2:
            col = np.clip(np.round(UV * 65535), 0, 65535).astype('<u2').view(np.uint8).reshape(V, 4)
        elif pt in (3, 4, 5) and dt == 7 and n == 2:
            uv = UV + np.array(uv_offset.get(pt, (0, 0)))
            col = np.clip(np.round(uv * 32767), -32767, 32767).astype('<i2').view(np.uint8).reshape(V, 4)
        elif pt in (3, 4, 5, 6) and dt == 0 and n == 2:
            uv = UV + np.array(uv_offset.get(pt, (0, 0)))
            col = uv.astype('<f4').view(np.uint8).reshape(V, 8)
        elif pt == 9 and dt == 2 and n == 4 and k == 7:
            # 7-influence layout (weights (10, 2, 2)): eight u16 joint slots, 7 used, the 8th zero
            arr = np.array([[j for j, _ in inf] + [pad_of(inf)] * (7 - len(inf)) + [0] for inf in INF], '<u2')
            col = arr.view(np.uint8).reshape(V, 16)
        elif pt == 9 and dt == 2 and n == 4:
            arr = np.array([pack_joints([j for j, _ in inf] + [pad_of(inf)] * (10 - len(inf))) for inf in INF], '<u4')
            col = arr.view(np.uint8).reshape(V, 16)
        elif pt == 10 and dt == 2 and n in (2, 3):
            arr = np.array([pack_weights([w for _, w in inf], n) for inf in INF], '<u4')
            col = arr.view(np.uint8).reshape(V, 4 * n)
        elif pt == 9 and dt == 8 and n == 4:
            js = [[j for j, _ in inf[:4]] + [pad_of(inf)] * (4 - len(inf[:4])) for inf in INF]
            assert max(max(j) for j in js) < 256, 'u8 joint slot cannot address bones >= 256'
            col = np.array(js, np.uint8).reshape(V, 4)
        elif pt == 9 and dt == 4 and n == 4:
            arr = np.array([[j for j, _ in inf[:4]] + [pad_of(inf)] * (4 - len(inf[:4])) for inf in INF], '<u2')
            col = arr.view(np.uint8).reshape(V, 8)
        elif pt == 10 and dt == 3 and n == 1:
            w4 = []
            for inf in INF:
                ws = [w for _, w in inf[:4]]; s = sum(ws); ws = [w / s for w in ws] + [0] * (4 - len(ws))
                q = [int(round(w * 1023)) for w in ws[:3]]
                w4.append(q[0] | (q[1] << 10) | (q[2] << 20))
            col = np.array(w4, '<u4').view(np.uint8).reshape(V, 4)
        elif pt == 15 and dt == 2 and n == 1:
            col = np.full(V, attr15, '<u4').view(np.uint8).reshape(V, 4)
        elif inherit and pt in inherit:
            raw = np.frombuffer(inherit[pt], np.uint8)
            col = np.tile(raw, (V, 1))
        else:
            raise ValueError(f'unsupported component {(pt, dt, n)}')
        b[:, co:co + col.shape[1]] = col
    return [b.tobytes() for b in bufs]

def align(n, a=16):
    return (n + a - 1) // a * a

def build_buffer(m, geo, attr15, pad_joint):
    """Lay out all vertex streams then the index buffer (u16), 16-byte aligned. Returns (bytes, offsets)."""
    streams = encode_streams(m, geo, attr15, pad_joint)
    out = bytearray(); offs = []
    for s in streams:
        out += b'\0' * (align(len(out)) - len(out))
        offs.append(len(out)); out += s
    out += b'\0' * (align(len(out)) - len(out))
    ind_off = len(out)
    idx = geo['IDX'].reshape(-1)
    assert idx.max() < 65536
    out += idx.astype('<u2').tobytes()
    out += b'\0' * (align(len(out)) - len(out))
    return bytes(out), offs, ind_off

def patch_def(mb, m, vcount, icount, fcount, buf_offs, ind_off, hash_, bbox=None):
    """Write counts/offsets/hash/bbox into MESH def `m` inside bytearray `mb`."""
    o = m.off
    if bbox is not None:
        lo, hi = bbox
        c = (lo + hi) / 2; e = (hi - lo) / 2
        struct.pack_into('<3f', mb, o + 0x10, *e)
        struct.pack_into('<3f', mb, o + 0x1C, *c)
    struct.pack_into('<I', mb, o + 0x30, ind_off)
    struct.pack_into('<I', mb, o + 0x3C, buf_offs[0] if buf_offs else 0)
    struct.pack_into('<II', mb, o + 0x44, vcount, fcount)
    struct.pack_into('<I', mb, o + 0x5C, icount)
    struct.pack_into('<Q', mb, o + 0x68, hash_)
    for j, bo in enumerate(buf_offs):
        struct.pack_into('<I', mb, o + m.buf_off_off + 4 * j, bo)

def zero_def(mb, m):
    o = m.off
    struct.pack_into('<II', mb, o + 0x44, 0, 0)
    struct.pack_into('<I', mb, o + 0x5C, 0)


def capacity(m, next_vtx_off):
    """Vertex/index room a def had in its stream buffer, measured from its in-place layout."""
    vbytes = m.ind_off - m.buf_offs[0]
    if m.buf_count == 1:
        vcap = vbytes // m.strides[0]
    else:
        vcap = min((m.buf_offs[j + 1] - m.buf_offs[j]) // m.strides[j] for j in range(m.buf_count - 1))
        vcap = min(vcap, (m.ind_off - m.buf_offs[-1]) // m.strides[-1])
    icap = (next_vtx_off - m.ind_off) // m.ind_stride
    return vcap, icap


def write_in_place(buf, m, geo, attr15, pad_joint, uv_offset=None, inherit=None):
    """Encode `geo` with def m's format and overwrite its existing vertex streams and index range in `buf`."""
    streams = encode_streams(m, geo, attr15, pad_joint, uv_offset, inherit)
    for off, s in zip(m.buf_offs, streams):
        buf[off:off + len(s)] = s
    idx = geo['IDX'].reshape(-1).astype('<u2').tobytes()
    buf[m.ind_off:m.ind_off + len(idx)] = idx
