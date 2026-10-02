import struct
def parse_mg_groups(b):
    cnt = struct.unpack_from('<H', b, 0x30)[0]
    offs = struct.unpack_from('<%dI' % cnt, b, 0x44)
    groups = []
    for gi, o in enumerate(offs):
        lod_offs = []
        p = o + 0x38
        while True:
            if lod_offs and p >= o + min(lod_offs): break
            v = struct.unpack_from('<I', b, p)[0]
            if v == 0: break
            lod_offs.append(v); p += 4
        lods = []
        for lo in lod_offs:
            c = struct.unpack_from('<I', b, o+lo)[0]
            dist = struct.unpack_from('<f', b, o+lo+4)[0]
            idx = list(struct.unpack_from('<%dH' % c, b, o+lo+10))
            lods.append(dict(dist=dist, meshes=idx, off=o+lo))
        groups.append(dict(i=gi, off=o, parent=struct.unpack_from('<H', b, o)[0], lods=lods))
    return groups
