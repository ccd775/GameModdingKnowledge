"""GoWR PC MESH_/MG_ parsing (layout from GOWTool gowr-pc src/Formats.cpp)."""
import struct

DT_SIZE = {0:4, 1:2, 2:4, 3:4, 4:2, 6:2, 7:2, 8:1, 10:1}

class MeshDef:
    pass

def parse_mesh(b):
    hdr_off, count = struct.unpack_from('<II', b, 0xC)
    filesize = struct.unpack_from('<I', b, 0x1C)[0]
    base = hdr_off + 0xC
    out = []
    for i in range(count):
        rel = struct.unpack_from('<I', b, base + i*4)[0]
        o = base + i*4 + rel
        m = MeshDef()
        m.i = i; m.off = o
        p = o + 0x10
        ext = struct.unpack_from('<3f', b, p); p += 12
        org = struct.unpack_from('<3f', b, p); p += 12
        m.extent, m.origin = ext, org
        p += 8
        m.ind_off = struct.unpack_from('<I', b, p)[0]; p += 4
        p += 8
        m.vtx_off = struct.unpack_from('<I', b, p)[0]; p += 4
        p += 4
        m.vcount, m.fcount = struct.unpack_from('<II', b, p); p += 8
        p += 0x10
        m.icount = struct.unpack_from('<I', b, p)[0]; p += 4
        comp_off, buf_off = struct.unpack_from('<II', b, p); p += 8
        m.hash = struct.unpack_from('<Q', b, p)[0]; p += 8
        p += 0x10
        m.buf_count, m.ind_stride = b[p], b[p+1]; p += 2
        m.bpv = struct.unpack_from('<H', b, p)[0]; p += 2
        m.comp_count, m.count2, m.flag, m.r32 = b[p], b[p+1], struct.unpack_from('<b', b, p+2)[0], b[p+3]
        m.comps = [struct.unpack_from('<BBBBB', b, o + comp_off + j*8) for j in range(m.comp_count)]
        m.buf_offs = [struct.unpack_from('<I', b, o + buf_off + j*4)[0] for j in range(m.buf_count)]
        strides = []
        for j in range(m.buf_count):
            s = 0
            for (pt, dt, n, co, bi) in m.comps:
                if bi == j: s += DT_SIZE[dt]*n
            strides.append(s)
        m.strides = strides
        m.comp_off, m.buf_off_off = comp_off, buf_off
        m.raw = b[o:o+0x100]
        out.append(m)
    return out

def parse_mg(b, meshes):
    cnt = struct.unpack_from('<H', b, 0x30)[0]
    groups = []
    for i in range(cnt):
        d = struct.unpack_from('<I', b, 0x44 + i*4)[0]
        parent = struct.unpack_from('<H', b, d)[0]
        lods = b[d+2]
        g = {'i': i, 'off': d, 'parent': parent, 'lods': []}
        for j in range(lods):
            lo = struct.unpack_from('<I', b, d + 0x38 + j*4)[0]
            c = struct.unpack_from('<I', b, d + lo)[0]
            idxs = [struct.unpack_from('<H', b, d + lo + 10 + k*2)[0] for k in range(c)]
            g['lods'].append(idxs)
            for k in idxs:
                if k < len(meshes):
                    meshes[k].parent = parent; meshes[k].lod = j; meshes[k].group = i
        groups.append(g)
    return groups
