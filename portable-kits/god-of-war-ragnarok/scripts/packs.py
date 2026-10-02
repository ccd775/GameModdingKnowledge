import struct, os
def maybe_lz4(b):
    if b[:4] == b'\x04\x22\x4d\x18':
        import lz4.frame
        return lz4.frame.decompress(b)
    return b
def read_lodpack_toc(path):
    b = maybe_lz4(open(path,'rb').read())
    gc, mc = struct.unpack_from('<II', b, 0)
    groups = [struct.unpack_from('<QQII', b, 16+24*i)[:3] for i in range(gc)]
    p = 16 + 24*gc
    members = {}
    for i in range(mc):
        gi, mo, h, size, _ = struct.unpack_from('<IIQII', b, p+24*i)
        members[h] = (gi, mo, size)
    return groups, members, b
def read_texpack_toc(path):
    b = maybe_lz4(open(path,'rb').read())
    tocsize, n2, recoff, n, unk = struct.unpack_from('<IIIII', b, 0x20)
    ents = {}
    for i in range(n):
        h1, h2, ro = struct.unpack_from('<QQQ', b, 0x38+24*i)
        rec = b[ro:ro+0x20]
        off16, s1, s2, z, mips, w, hgt = struct.unpack_from('<IIIIIHH', rec, 0)
        ents[h1] = dict(h2=h2, off=off16*16, datasize=s1, size=s2, mips=mips, w=w, h=hgt, rec=rec)
    return ents, b
