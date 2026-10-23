"""Patch a WolvenKit-7-written CR2W so every CSkeleton bone 'name' (String) uses the vanilla encoding.

WolvenKit 7 writes a String as <len+1> <ansi chars> 00, the game expects the CR2W string form
<0x80|len> <ansi chars> (VLQ length, sign bit = 1-byte chars, no terminator). Its reader also drops the
field entirely, so a skeleton round-tripped through WolvenKit loses it - both break dangle skeletons.

Only the CSkeleton chunks are rewritten; export sizes/offsets, table CRCs, file sizes and the header CRC
are recomputed (header CRC = crc32 of the 160-byte header with the crc field set to 0xDEADBEEF).

Usage: python fix_cr2w_skeleton_names.py <in> [<out>]
"""
import struct
import sys
import zlib

def fnv1a32(b):
    h = 0x811c9dc5
    for c in b:
        h ^= c
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def vlq_str(s):
    b = s.encode('latin-1')
    n = len(b)
    if n < 0x40:
        return bytes([0x80 | n]) + b
    out = bytearray([0x80 | 0x40 | (n & 0x3F)])
    n >>= 6
    while True:
        byte = n & 0x7F
        n >>= 7
        if n:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            break
    return bytes(out) + b


def main():
    import argparse
    ap = argparse.ArgumentParser(description='Rewrite CSkeleton bone / track names of a WolvenKit-7-written CR2W to the vanilla String form.')
    ap.add_argument('src')
    ap.add_argument('dst', nargs='?', help='default: overwrite src')
    a = ap.parse_args()
    src = a.src
    dst = a.dst or src
    d = bytearray(open(src, 'rb').read())
    tables = [list(struct.unpack_from('<III', d, 40 + i * 12)) for i in range(10)]
    so, sn = tables[0][0], tables[0][1]
    no, nc = tables[1][0], tables[1][1]

    def name(i):
        off = struct.unpack_from('<I', d, no + i * 8)[0]
        e = d.index(b'\0', so + off)
        return d[so + off:e].decode('latin-1')
    names = [name(i) for i in range(nc)]
    # WolvenKit types the field 'StringAnsi'; vanilla uses 'String'. Rename the name entry in place
    # (string table bytes overwritten, FNV-1a32 hash of the zero-terminated string updated).
    ansi = names.index('StringAnsi') if 'StringAnsi' in names else None
    string_idx = names.index('String') if 'String' in names else ansi
    if ansi is not None and 'String' not in names:
        soff = struct.unpack_from('<I', d, no + ansi * 8)[0]
        d[so + soff:so + soff + 7] = b'String\0'
        struct.pack_into('<I', d, no + ansi * 8 + 4, fnv1a32(b'String\0'))
        names[ansi] = 'String'
        tables[0][2] = zlib.crc32(bytes(d[so:so + sn])) & 0xFFFFFFFF
        tables[1][2] = zlib.crc32(bytes(d[no:no + nc * 8])) & 0xFFFFFFFF
    eo, ec = tables[4][0], tables[4][1]
    exports = [list(struct.unpack_from('<HHIIIII', d, eo + i * 24)) for i in range(ec)]

    def parse_props(buf, p):
        """returns list of (nameIdx, typeIdx, value bytes) and end position (after the 0 terminator)."""
        props = []
        while True:
            ni = struct.unpack_from('<H', buf, p)[0]
            if ni == 0:
                return props, p + 2
            ti, size = struct.unpack_from('<HI', buf, p + 2)
            props.append((ni, ti, bytes(buf[p + 8:p + 4 + size])))
            p += 4 + size

    def ser_props(props):
        out = bytearray()
        for ni, ti, val in props:
            out += struct.pack('<HHI', ni, ti, len(val) + 4) + val
        return bytes(out) + b'\0\0'

    changed = 0
    new_chunks = {}
    for i, ex in enumerate(exports):
        if names[ex[0]] != 'CSkeleton':
            continue
        off, size = ex[4], ex[3]
        chunk = bytes(d[off:off + size])
        head = chunk[:1]                      # leading 0 byte before the property list
        props, end = parse_props(chunk, 1)
        tail = chunk[end:]
        out_props = []
        for ni, ti, val in props:
            if names[ni] in ('bones', 'tracks'):   # SSkeletonBone / SSkeletonTrack share the name layout
                count = struct.unpack_from('<I', val, 0)[0]
                p = 4
                elems = bytearray(struct.pack('<I', count))
                for _ in range(count):
                    # struct element: 1 zero byte, property list, u16 0
                    if val[p] != 0:
                        raise SystemExit(f'unexpected struct lead byte {val[p]} at {p}')
                    elems += b'\0'
                    sprops, p = parse_props(val, p + 1)
                    fixed = []
                    for sni, sti, sval in sprops:
                        if names[sni] == 'name' and names[sti] in ('String', 'StringAnsi'):
                            raw = sval
                            if raw and (raw[0] & 0x80) == 0 and raw[-1:] == b'\0':   # WolvenKit form
                                s = raw[1:-1].decode('latin-1')
                                sval = vlq_str(s)
                                sti = string_idx
                                changed += 1
                        fixed.append((sni, sti, sval))
                    elems += ser_props(fixed)
                val = bytes(elems)
            out_props.append((ni, ti, val))
        new_chunks[i] = head + ser_props(out_props) + tail
    if not new_chunks:
        raise SystemExit('no CSkeleton chunk')
    # rebuild data area: chunks are stored in export order after the tables
    order = sorted(range(ec), key=lambda i: exports[i][4])
    data_start = exports[order[0]][4]
    tail_start = max(exports[i][4] + exports[i][3] for i in range(ec))
    out = bytearray(d[:data_start])
    for i in order:
        ex = exports[i]
        blob = new_chunks.get(i, bytes(d[ex[4]:ex[4] + ex[3]]))
        ex[4] = len(out)
        ex[3] = len(blob)
        ex[6] = zlib.crc32(blob) & 0xFFFFFFFF
        out += blob
    out += d[tail_start:]                     # buffers / trailing data (none expected for dyng)
    for i, ex in enumerate(exports):
        struct.pack_into('<HHIIIII', out, eo + i * 24, *ex)
    tables[4][2] = zlib.crc32(bytes(out[eo:eo + ec * 24])) & 0xFFFFFFFF
    for t, (o, n, c) in enumerate(tables):
        struct.pack_into('<III', out, 40 + t * 12, o, n, c)
    struct.pack_into('<I', out, 24, len(out))   # fileSize
    struct.pack_into('<I', out, 28, len(out))   # bufferSize
    h = bytearray(out[:160])
    struct.pack_into('<I', h, 32, 0xDEADBEEF)
    struct.pack_into('<I', out, 32, zlib.crc32(bytes(h)) & 0xFFFFFFFF)
    open(dst, 'wb').write(out)
    print(f'fixed {changed} bone names -> {dst} ({len(d)} -> {len(out)} bytes)')


if __name__ == '__main__':
    main()
