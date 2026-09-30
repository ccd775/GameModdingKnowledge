"""Ghost of Tsushima PC character formats: hero .xpps metadata, .xmesh (SMBS) and .sps (XTBS).

Layout knowledge partly derived from "Ghost of Tsushima Toolkit for Blender" by Dave349234
(MIT with attribution: https://www.nexusmods.com/profile/Dave349234) and verified against
the current PC build during this project.
"""
import struct

import numpy as np

MODEL_ASSET_HASHES = (8120115085854712779, 8121310221017043393)

FMT_POS_S16 = 3252492      # 3 x snorm16, scaled by per-mesh offset/scale (cm)
FMT_POS_F32 = 3254029
FMT_HALF = 2107138         # f16 bitangent sign, interleaved after the position
FMT_N10 = 3252233          # 10:10:10:2, (v + 1) / 2 biased; first = normal, second = tangent
FMT_UV_H2 = 2205445        # 2 x f16, top-left origin (same as glTF)
FMT_BONE_U16 = 11642124    # 4 x int16 global bone index, -1 = unused
FMT_U8X4 = 11640842        # weights of bones 1..3 (bone 0 = 255 - sum) or colour

ATTR_SIZE = {FMT_POS_S16: 6, FMT_HALF: 2, FMT_N10: 4, FMT_UV_H2: 4, FMT_BONE_U16: 8, FMT_U8X4: 4}
HIDE_SCALE = struct.unpack('<f', bytes.fromhex('00000835'))[0]   # value used by the v1.0 mod


def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def u64(d, o):
    return struct.unpack_from('<Q', d, o)[0]


class XppsMesh:
    asset: int
    index: int
    addr: int
    hash: int
    bbox_min: tuple
    bbox_max: tuple
    offset: tuple
    scale: float
    index_count: int
    vertex_count: int
    attrs: list
    material_addr: int
    textures: list


class Xpps:
    def __init__(self, data):
        self.data = bytearray(data)
        d = self.data
        pkg_h = u32(d, 24)
        self.data_start = ds = u32(d, 40)
        entry_cnt = u32(d, pkg_h + 8)
        self.assets = []
        curr = pkg_h + 48
        for _ in range(entry_cnt):
            kind, sz, off = struct.unpack_from('<III', d, curr)
            if kind == 2:
                p = ds + off
                end = p + sz
                while p < end:
                    magic = bytes(d[p:p + 4])
                    csz = u32(d, p + 4)
                    cstart = p + 8
                    if magic == b' DIC':
                        q = cstart + 8
                        for _ in range(u32(d, cstart)):
                            e_off, e_hash = struct.unpack_from('<QQ', d, q)
                            q += 16
                            if e_hash in MODEL_ASSET_HASHES:
                                self.assets.append(ds + e_off - 16)
                    p = cstart + csz
            curr += 40
        self.meshes = []
        self.by_hash = {}
        for ai, asset_pos in enumerate(self.assets):
            base = asset_pos + 64
            meshes_off, meshes_cnt = struct.unpack_from('<QQ', d, base + 128)
            model_group_off = u64(d, base + 296)
            mats = []
            if model_group_off:
                mat_ptr_off, mat_cnt = struct.unpack_from('<QQ', d, ds + model_group_off + 40)
                mats = [u64(d, ds + mat_ptr_off + 8 * i) for i in range(mat_cnt)]
            ptrs = struct.unpack_from('<%dQ' % meshes_cnt, d, ds + meshes_off) if meshes_cnt else ()
            for mi, ptr in enumerate(ptrs):
                m = XppsMesh()
                m.asset = ai
                m.index = mi
                m.addr = a = ds + ptr
                m.bbox_min = struct.unpack_from('<3f', d, a + 32)
                m.bbox_max = struct.unpack_from('<3f', d, a + 44)
                m.offset = struct.unpack_from('<3f', d, a + 56)
                m.scale = struct.unpack_from('<f', d, a + 68)[0]
                m.hash = u64(d, a + 80)
                attr_off = u64(d, a + 96)
                num_attrs = u64(d, a + 112)
                m.index_count = u32(d, a + 152)
                m.attrs = []
                for k in range(num_attrs):
                    q = ds + attr_off + 24 * k
                    fmt, stride, cnt = struct.unpack_from('<III', d, q + 8)
                    m.attrs.append((fmt, stride, cnt))
                m.vertex_count = m.attrs[0][2] if m.attrs else 0
                m.material_addr = (ds + mats[mi]) if mi < len(mats) and mats[mi] else 0
                m.textures = []
                if m.material_addr:
                    tex_off, tex_cnt = struct.unpack_from('<QQ', d, m.material_addr + 48)
                    m.textures = [u64(d, ds + tex_off + 32 * t) for t in range(tex_cnt)]
                self.meshes.append(m)
                self.by_hash.setdefault(m.hash, []).append(m)

    def mesh(self, h):
        ms = self.by_hash.get(h)
        if not ms:
            raise KeyError(f'mesh {h:016x} not in xpps')
        if len(ms) != 1:
            raise ValueError(f'mesh {h:016x} is ambiguous ({len(ms)} records)')
        return ms[0]

    def skeleton(self, asset_index=0):
        d = self.data
        ds = self.data_start
        info = u64(d, self.assets[asset_index] + 64 + 336)
        p = ds + info
        parent_off = u64(d, p + 32)
        unk3_off = u64(d, p + 40)
        s = ds + u64(d, p + 16)
        if bytes(d[s:s + 4]) != b'60SE':
            raise ValueError('skeleton signature mismatch')
        num = struct.unpack_from('<H', d, s + 16)[0]
        bone_off = s + 24 + struct.unpack_from('<i', d, s + 24)[0]
        parents = [-1] * num
        for k in range((unk3_off - parent_off) // 4):
            idx, flag = struct.unpack_from('<Hh', d, ds + parent_off + 4 * k)
            par = flag & 0x7FFF
            if idx < num:
                parents[idx] = -1 if par == 0x7FFF else par
        rot = np.zeros((num, 4))
        pos = np.zeros((num, 3))
        scl = np.zeros((num, 3))
        for i in range(num):
            v = struct.unpack_from('<12f', d, bone_off + 48 * i)
            rot[i], pos[i], scl[i] = v[0:4], v[4:7], v[8:11]
        return dict(parents=parents, rot=rot, pos=pos, scl=scl, num=num)

    def set_quant(self, m, offset, scale, bbox_min=None, bbox_max=None):
        struct.pack_into('<3ff', self.data, m.addr + 56, *[float(x) for x in offset], float(scale))
        if bbox_min is not None:
            struct.pack_into('<3f3f', self.data, m.addr + 32, *[float(x) for x in bbox_min],
                             *[float(x) for x in bbox_max])

    def hide(self, m):
        struct.pack_into('<3ff', self.data, m.addr + 56, 0.0, 0.0, 0.0, HIDE_SCALE)


def quat_to_mat(q):
    x, y, z, w = q
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def skeleton_world(sk):
    world = [None] * sk['num']

    def get(i):
        if world[i] is None:
            m = np.eye(4)
            m[:3, :3] = quat_to_mat(sk['rot'][i]) * sk['scl'][i][None, :]
            m[:3, 3] = sk['pos'][i]
            p = sk['parents'][i]
            world[i] = m if p == -1 else get(p) @ m
        return world[i]

    for i in range(sk['num']):
        get(i)
    return np.array(world)


class XmeshRecord:
    hash: int
    idx_off: int
    lod: int
    v_offs: list
    end: int


class Xmesh:
    def __init__(self, data):
        self.data = bytearray(data)
        d = self.data
        if bytes(d[:4]) != b'SMBS':
            raise ValueError('not an SMBS xmesh')
        self.buf = u32(d, 0x18)
        self.buf_size = u32(d, 0x20)
        o = 0x2c
        self.records = []
        for _ in range(u32(d, 0x28)):
            r = XmeshRecord()
            r.hash = u64(d, o)
            r.idx_off = u32(d, o + 8)
            r.lod = struct.unpack_from('<H', d, o + 12)[0]
            n = d[o + 14]
            r.v_offs = list(struct.unpack_from('<%dI' % n, d, o + 15))
            o += 15 + 4 * n
            self.records.append(r)
        for i, r in enumerate(self.records):
            r.end = self.records[i + 1].idx_off if i + 1 < len(self.records) else self.buf_size
        for i, r in enumerate(self.records):
            if i + 1 < len(self.records) and self.records[i + 1].idx_off < r.idx_off:
                raise ValueError(f'xmesh records not sorted by idx_off at {r.hash:016x}')
            if not r.v_offs:
                raise ValueError(f'xmesh record {r.hash:016x} has no vertex streams')
            # streams are not always listed in ascending order (vanilla hero_head), so bound min/max
            if not r.idx_off < min(r.v_offs) or not max(r.v_offs) < r.end:
                raise ValueError(f'xmesh record {r.hash:016x} streams outside its region')

    def region(self, r):
        return self.buf + r.idx_off, self.buf + r.end

    def clear(self, r):
        a, b = self.region(r)
        self.data[a:b] = bytes(b - a)

    def indices(self, r, count):
        a = self.buf + r.idx_off
        return np.frombuffer(bytes(self.data[a:a + 2 * count]), '<u2').copy()

    def attr(self, r, ai, stride, count):
        a = self.buf + r.v_offs[ai]
        return np.frombuffer(bytes(self.data[a:a + stride * count]), 'u1').reshape(count, stride)


def decode_record(xm, r, m):
    """Decode a record into numpy arrays (GoT space: x fwd, y left, z up; cm)."""
    V = m.vertex_count
    out = {'V': V}
    idx = xm.indices(r, m.index_count)
    out['tris'] = idx[:len(idx) // 3 * 3].reshape(-1, 3)
    n10 = 0
    u8 = []
    for ai, (fmt, stride, cnt) in enumerate(m.attrs):
        if cnt != V:
            continue
        raw = xm.attr(r, ai, stride, V)
        if ai == 0 and fmt == FMT_POS_S16:
            q = raw[:, :6].copy().view('<i2').reshape(V, 3).astype(np.float64) / 32767.0
            out['pos'] = q * m.scale + np.array(m.offset)
        elif fmt == FMT_HALF:
            out['tsign'] = raw[:, :2].copy().view('<f2').ravel().astype(np.float32)
        elif fmt == FMT_N10:
            v = raw[:, :4].copy().view('<u4').ravel()
            xyz = np.stack([v & 1023, (v >> 10) & 1023, (v >> 20) & 1023], 1) / 1023.0 * 2 - 1
            out['normal' if n10 == 0 else 'tangent'] = xyz
            n10 += 1
        elif fmt == FMT_UV_H2:
            out.setdefault('uvs', []).append(raw[:, :4].copy().view('<f2').reshape(V, 2).astype(np.float32))
        elif fmt == FMT_BONE_U16:
            out['bones'] = raw[:, :8].copy().view('<i2').reshape(V, 4)
        elif fmt == FMT_U8X4:
            u8.append(raw[:, :4].copy())
    if 'bones' in out and u8:
        w = u8[-1].astype(np.float64)
        b = out['bones']
        w123 = np.where(b[:, 1:] >= 0, w[:, :3], 0)
        w0 = np.maximum(0, 255 - w123.sum(1))
        out['weights'] = np.concatenate([w0[:, None], w123], 1) / 255.0
    return out


def pack_n10(v):
    q = np.clip(np.rint((np.clip(v, -1, 1) + 1) * 0.5 * 1023), 0, 1023).astype(np.uint32)
    return q[:, 0] | (q[:, 1] << 10) | (q[:, 2] << 20)


def quantize_weights(bones, weights):
    """bones (V,4) int, weights (V,4) float sorted desc -> (bones int16, u8 w1..w3 + 0)."""
    b = np.where(weights > 0, bones, -1).astype(np.int16)
    w = np.rint(weights[:, 1:] * 255).astype(np.int64)
    w = np.where(b[:, 1:] >= 0, w, 0)
    # keep bone 0 dominant and the implicit weight non-negative
    over = w.sum(1) - 255
    w[:, 0] -= np.maximum(over, 0)
    w = np.clip(w, 0, 255)
    packed = np.zeros((len(b), 4), np.uint8)
    packed[:, :3] = w
    return b, packed


def encode_record(xm, r, m, mesh):
    """Write mesh into record r keeping every vanilla count; returns (offset, scale, bmin, bmax)."""
    pos, tris = mesh['pos'], mesh['tris']
    V, T = len(pos), len(tris)
    if V > m.vertex_count:
        raise ValueError(f'{m.hash:016x}: {V} vertices > capacity {m.vertex_count}')
    if 3 * T > m.index_count:
        raise ValueError(f'{m.hash:016x}: {3 * T} indices > capacity {m.index_count}')
    if tris.max() >= V:
        raise ValueError('index out of range')
    xm.clear(r)
    lo, hi = pos.min(0), pos.max(0)
    offset = (lo + hi) / 2
    scale = float(max((hi - lo).max() / 2, 1e-3))
    idx = np.zeros(m.index_count, '<u2')
    idx[:3 * T] = tris.ravel()
    a = xm.buf + r.idx_off
    xm.data[a:a + idx.nbytes] = idx.tobytes()
    q = np.clip(np.rint((pos - offset) / scale * 32767), -32767, 32767).astype('<i2')
    bones, w8 = quantize_weights(mesh['bones'], mesh['weights'])
    n10 = 0
    for ai, (fmt, stride, cnt) in enumerate(m.attrs):
        if cnt != m.vertex_count:
            raise ValueError(f'attribute {ai} count {cnt} != vertex count')
        if fmt == FMT_POS_S16 and ai == 0:
            payload = q.tobytes()
        elif fmt == FMT_HALF:
            payload = np.where(mesh['tsign'] < 0, -1.0, 1.0).astype('<f2').tobytes()
        elif fmt == FMT_N10:
            payload = pack_n10(mesh['normal'] if n10 == 0 else mesh['tangent']).astype('<u4').tobytes()
            n10 += 1
        elif fmt == FMT_UV_H2:
            payload = mesh['uv'].astype('<f2').tobytes()
        elif fmt == FMT_BONE_U16:
            payload = bones.astype('<i2').tobytes()
        elif fmt == FMT_U8X4:
            payload = w8.tobytes()
        else:
            raise ValueError(f'unsupported attribute format {fmt}')
        size = ATTR_SIZE[fmt]
        arr = np.frombuffer(payload, 'u1').reshape(V, size)
        base = xm.buf + r.v_offs[ai]
        block = np.frombuffer(bytes(xm.data[base:base + stride * V]), 'u1').reshape(V, stride).copy()
        block[:, :size] = arr
        xm.data[base:base + stride * V] = block.tobytes()
    bmin = (lo - offset) / scale
    bmax = (hi - offset) / scale
    return offset, scale, bmin, bmax


# ---------------------------------------------------------------- sps (XTBS textures)
SPS_KIND = {251725312: 'BC1', 251725824: 'BC3', 251660544: 'BC4', 251791616: 'BC4', 251726080: 'BC4',
            251660800: 'BC5', 251923200: 'BC5', 251661824: 'BC7', 251727360: 'BC7', 251723776: 'BGRA8'}
BLOCK_BYTES = {'BC1': 8, 'BC4': 8, 'BC3': 16, 'BC5': 16, 'BC7': 16}


def sps_header(data):
    if data[:4] != b'XTBS':
        raise ValueError('not an XTBS texture')
    doff = u32(data, 24)
    nlen = u32(data, 32)
    p = 36 + nlen + 20
    fmt, w, h, depth, mips = struct.unpack_from('<IHHHH', data, p)
    return dict(data_offset=doff, fmt=fmt, kind=SPS_KIND.get(fmt, '?'), w=w, h=h, depth=depth, mips=mips)


def mip_sizes(kind, w, h, mips):
    out = []
    for i in range(mips):
        mw, mh = max(1, w >> i), max(1, h >> i)
        out.append(((mw + 3) // 4) * ((mh + 3) // 4) * BLOCK_BYTES[kind] if kind in BLOCK_BYTES else mw * mh * 4)
    return out
