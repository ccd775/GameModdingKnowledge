"""Minimal i30 (Marvel's Spider-Man 2) .model container reader/writer.

Asset layout as extracted (toc header + archive bytes):
  [toc header: u32 magic, u8 ?, u8 pairs, u16 extra, pairs*8, extra]  (24 bytes for models)
  DAT1: u32 'DAT1', u32 type magic, u32 total size, u16 section count, u16 ?, then (tag, offset, size)*n,
        then section data; offsets are relative to DAT1 start.
Section names come from InsomniacTools IGEngine/Model/ModelHashes.cs.
"""
import struct

NAMES = {
    0x283D0383: 'ModelBuilt', 0x78D9CBDE: 'ModelSubset', 0xF4EA9E18: 'ModelSubsetGeomData',
    0xF508D8C3: 'ModelSubsetSkinData', 0x06EB7EFC: 'ModelLook', 0x4CCEA4AD: 'ModelLookGroup',
    0x811902D7: 'ModelLookBuilt', 0xB9E51D26: 'ModelLookBVHData', 0xDF9FDF12: 'ModelLookBVHInfo',
    0xAF739EBF: 'ModelLookBVHAdditionalLodInfo', 0x3250BB80: 'ModelMaterial', 0x90CDB60C: 'ModelJointHierarchy',
    0x15DF9D3B: 'ModelJoint', 0xC5354B60: 'ModelMirrorIds', 0xB7380E8C: 'ModelLeafIds', 0x7496D749: 'ModelSplineRadii',
    0x0AD3A708: 'ModelJointBspheres', 0xEE31971C: 'ModelJointLookup', 0xDCC88A19: 'ModelBindPose',
    0x2C2CA205: 'ModelInvBindPose', 0x9F614FAB: 'ModelLocator', 0x731CBC2E: 'ModelLocatorLookup',
    0x5796FEF6: 'ModelCollisionIndexData', 0xF4CB2F37: 'ModelCollisionVertexData', 0xD2B0CB7D: 'ModelCollisionComplexity',
    0xEFD92E68: 'ModelHavokData', 0x707F1B58: 'ModelRagDollMetaData', 0x1112DF22: 'ModelDestructibleMetaData',
    0x5A39FAB7: 'ModelClothMetaData', 0x9A434B29: 'ModelIKSetupData', 0x06E24ED4: 'ModelAnimVertInfo2',
    0x948C38CD: 'ModelAnimMorph2Info', 0x5E03CEFE: 'ModelAnimMorph2Batches', 0xDE8D9DCF: 'ModelAnimMorph2ValidMasks',
    0x573C714B: 'ModelAnimMorph2Deltas', 0xCD903318: 'ModelAnimGeomInfo', 0x3F70F60D: 'ModelAnimGeomParticles',
    0x92123A05: 'ModelAnimGeomMeshInfo', 0x6694064E: 'ModelAnimZiva2Info', 0x855275D7: 'ModelAnimVertNormalInfo',
    0x8A84E4D6: 'ModelAnimVertNormalStitches', 0x55187F02: 'ModelAnimVertSmoothInfo', 0x53EA4273: 'ModelBVol',
    0xFB7F6A48: 'ModelVGroup', 0xB32D7671: 'ModelMeshNames', 0x14A9959C: 'ModelContentAnimVertInfos',
    0x00823787: 'ModelTextureOverrides', 0xBCE86B01: 'ModelRenderOverrides', 0x7CA37DA0: 'ModelAmbientShadowPrims',
    0xADD1CBD3: 'ModelAnimDynamicsDef', 0x3C9DABDF: 'ModelStrandSubsets', 0x27CA5246: 'ModelStrands',
    0xB25B3163: 'ModelStrandCVs', 0xBB7303D5: 'ModelStrandSBs', 0x14D8B13C: 'ModelStrandJBs',
    0x5D5CF541: 'ModelStrandCVWeights', 0x0BA45069: 'ModelRayTracingParameters',
    0x4F26E619: 'ModelRayTracingAdditionalParameters', 0xE2B463E7: 'ModelDefaultLook', 0x2D095A7B: 'ModelDefaultLookLower',
    0x36AC9E04: 'ModelLodInfoBuilt', 0xD4CB21D3: 'ModelLodPoolBuilt', 0x4A71612B: 'ModelLodGeometry',
    0x1F235224: 'ModelLodMaterialNames', 0xFC869EB4: 'ModelLodBoneNames', 0x789C01DB: 'ModelLodJointNames',
    0x55F83681: 'ModelLodAnimVertKey',
}


class Asset:
    def __init__(self, raw):
        self.raw = raw
        pairs = raw[5]
        extra = struct.unpack_from('<H', raw, 6)[0]
        self.hlen = 8 + pairs * 8 + extra
        self.header = raw[:self.hlen]
        d = raw[self.hlen:]
        self.dat = d
        magic, self.type, self.size, n = struct.unpack_from('<IIII', d, 0)
        assert magic == 0x44415431, hex(magic)
        self.n = n & 0xFFFF
        self.unk_n = n >> 16
        self.sections = []
        for i in range(self.n):
            tag, off, sz = struct.unpack_from('<III', d, 16 + 12 * i)
            self.sections.append([tag, off, sz])
        self.table_end = 16 + 12 * self.n
        first = min(s[1] for s in self.sections) if self.sections else self.table_end
        self.prefix = d[self.table_end:first]       # string table etc. lives between table and first section

    def sec(self, tag):
        for t, o, s in self.sections:
            if t == tag:
                return self.dat[o:o + s]
        return None

    def sec_off(self, tag):
        for t, o, s in self.sections:
            if t == tag:
                return o, s
        return None

    def cstr(self, off):
        e = self.dat.index(b'\0', off)
        return self.dat[off:e].decode('utf-8', 'replace')

    def describe(self):
        out = [f'header {self.hlen}B {self.header[:8].hex()}  type {self.type:08X}  size {self.size}  sections {self.n} unk {self.unk_n}  prefix {len(self.prefix)}B']
        for t, o, s in sorted(self.sections, key=lambda x: x[1]):
            out.append(f'  {t:08X} {NAMES.get(t, "?"):<34} off {o:>10} size {s:>10}')
        return '\n'.join(out)


import numpy as np

T_SUBSET, T_GEOM = 0x78D9CBDE, 0xF4EA9E18
T_JOINT, T_BIND, T_INVBIND, T_MAT = 0x15DF9D3B, 0xDCC88A19, 0x2C2CA205, 0x3250BB80


def decode_normal(n):
    """RCRA-style packed normal (10/10 bits + sign in bit 31). n: uint32 array -> (N,3)."""
    n = n.astype(np.uint64)
    nx = (n & 0x3FF).astype(np.float64) * 0.00276483595 - np.sqrt(2)
    ny = ((n >> 10) & 0x3FF).astype(np.float64) * 0.00276483595 - np.sqrt(2)
    q = nx * nx + ny * ny
    w = np.sqrt(np.clip(1 - 0.25 * q, 0, None))
    nz = 1 - 0.5 * q
    nz = np.where((n >> 31) == 0, -nz, nz)
    return np.stack([nx * w, ny * w, nz], 1)


class Mesh:
    FIELDS = ('index_count', 'vertex_count', 'z8', 'index_off', 'u16', 'fmt', 'pos_scale', 'material',
              'f32', 'f36')

    def __init__(self, rec, i):
        self.i = i
        self.rec = bytearray(rec)
        (self.index_count, self.vertex_count, self.z8, self.index_off, self.u16, self.fmt, self.pos_scale,
         self.material, self.f32, self.f36) = struct.unpack_from('<IIIIIIfIff', rec, 0)
        self.b52, self.b56 = struct.unpack_from('<Ii', rec, 52)
        self.lodbytes = bytes(rec[60:64])
        (self.pos_off, self.uv1_off, self.z72, self.skin_off, self.skinbatch_off, self.vertex_start,
         self.block_off, self.block_size, self.vertex_count2, self.skin_info) = struct.unpack_from('<10I', rec, 64)
        self.t116, self.f120 = struct.unpack_from('<If', rec, 116)

    @property
    def skin_batches(self):
        return self.skin_info & 0xFFFF


class Model(Asset):
    def __init__(self, raw):
        super().__init__(raw)
        sub = self.sec(T_SUBSET)
        self.meshes = [Mesh(sub[i * 128:(i + 1) * 128], i) for i in range(len(sub) // 128)]
        self.geom = self.sec(T_GEOM)
        js = self.sec(T_JOINT)
        bp = self.sec(T_BIND)
        self.njoints = len(bp) // 48
        self.joints = []
        for i in range(self.njoints):
            p, ix, u1, u2, h, so = struct.unpack_from('<hHHHII', js, i * 16)
            e = js.index(b'\0', i * 16 + so)
            self.joints.append(dict(parent=p, index=ix, u1=u1, u2=u2, hash=h, name=js[i * 16 + so:e].decode()))
        self.bind_local = []
        for i in range(self.njoints):
            v = struct.unpack_from('<12f', bp, i * 48)
            self.bind_local.append(dict(scale=v[0:3], rot=v[4:8], pos=v[8:11]))
        ib = self.sec(T_INVBIND)
        self.inv_bind = np.frombuffer(ib, np.float32, count=self.njoints * 16).reshape(-1, 4, 4).astype(np.float64)
        mt = self.sec(T_MAT)
        nm = len(mt) // 32
        self.materials = [(self.cstr(struct.unpack_from('<I', mt, i * 16)[0]),
                           self.cstr(struct.unpack_from('<I', mt, i * 16 + 8)[0])) for i in range(nm)]

    def joint_world(self):
        """World bind matrices (row-vector convention, translation in last row) = inverse of inv_bind."""
        return np.linalg.inv(self.inv_bind)

    def decode(self, m, skin=True):
        g, b = self.geom, m.block_off
        V = np.frombuffer(g, np.int16, count=m.vertex_count * 8, offset=b + m.pos_off).reshape(-1, 8)
        N32 = np.frombuffer(g, np.uint32, count=m.vertex_count * 4, offset=b + m.pos_off).reshape(-1, 4)[:, 2]
        pos = V[:, 0:3].astype(np.float64) * m.pos_scale
        if m.fmt & 0x4000:                  # head meshes (1/65536 m): origin (0, b52, b56) in 1/256 m
            pos += np.array([0.0, m.b52, m.b56]) / 256.0
        nrm = decode_normal(N32)
        uv0 = V[:, 6:8].astype(np.float64)
        uv1 = None
        if m.fmt & 2:                       # second 4-byte stream (UV1-like) only when fmt bit 2 is set
            uv1 = np.frombuffer(g, np.int16, count=m.vertex_count * 2, offset=b + m.uv1_off).reshape(-1, 2).astype(np.float64)
        idx = np.frombuffer(g, np.uint16, count=m.index_count, offset=b + m.index_off).astype(np.int64)
        joints = weights = None
        if skin:
            try:
                joints, weights = self.decode_skin(m)
            except IndexError:                      # rigid / unusual meshes: no readable skin batches
                joints, weights = None, None
        return dict(pos=pos, w=V[:, 3].copy(), nrm=nrm, uv0=uv0, uv1=uv1, idx=idx, joints=joints, weights=weights)

    def decode_skin(self, m):
        g, b = self.geom, m.block_off
        nb = (m.vertex_count + 31) // 32
        tab = np.frombuffer(g, np.uint16, count=nb * 2, offset=b + m.skinbatch_off).reshape(-1, 2)
        J = np.zeros((m.vertex_count, 16), np.int64)
        W = np.zeros((m.vertex_count, 16), np.float64)
        v = 0
        gmax = 1
        for bi in range(nb):
            info = int(tab[bi, 1])
            off = int(tab[bi, 0]) | ((info & 0xF) << 16)    # 4-byte units; info bits 0-3 extend the offset
            wide = info & 0x10                              # u16 absolute joint indices (>255-joint head models)
            groups = ((info >> 5) & 0xF) + 1               # bits 5-8; 0x2000 flag on anim-vert models
            base = 256 if info & 0x200 else 0               # byte joints start at 256
            gmax = max(gmax, groups)
            p = b + m.skin_off + off * 4
            for k in range(32):                             # every batch has 32 slots (last one padded)
                if v >= m.vertex_count:
                    break
                if groups == 1:                     # one influence: joint only, weight 1
                    J[v, 0] = (g[p] | g[p + 1] << 8) if wide else base + g[p]
                    W[v, 0] = 1.0
                    p += 2 if wide else 1
                elif wide:                          # (u16 joint, weight/256) triples
                    for gi in range(groups):
                        J[v, gi] = g[p] | g[p + 1] << 8
                        W[v, gi] = g[p + 2] / 256.0
                        p += 3
                else:
                    jn = base
                    for gi in range(groups):        # (joint delta, weight/256) pairs; joints ascend
                        jn += g[p]
                        J[v, gi] = jn
                        W[v, gi] = g[p + 1] / 256.0
                        p += 2
                v += 1
        k = max(8, gmax)
        return J[:, :k], W[:, :k]
