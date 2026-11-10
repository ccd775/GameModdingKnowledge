"""KT generic packs in Nioh 2 archives: MDLTEXPK (EXARG texture pack + G1M_PACK), G1M_PACK, EXARG000.
header: magic[8], u32 0x01010000, u32 header size, u32 total size, u32 n, u32 n2, u32 0,
        u32 ptr_offsets, u32 ptr_sizes, u32 ptr_extra, u32 0; offsets/sizes are relative to the pack start."""
import struct


def parse(data, base=0):
    magic = data[base:base + 8]
    hsz, total, n = struct.unpack_from('<III', data, base + 12)
    po, ps, px = struct.unpack_from('<III', data, base + 0x20)
    offs = struct.unpack_from(f'<{n}I', data, base + po) if n else ()
    sizes = struct.unpack_from(f'<{n}I', data, base + ps) if n else ()
    return {'magic': magic, 'total': total, 'n': n, 'items': [(base + o, s) for o, s in zip(offs, sizes)], 'extra': base + px}


def models(data):
    """[(offset, size)] of every G1M in an MDLTEXPK / G1M_PACK / bare G1M."""
    if data[:4] == b'_M1G':
        return [(0, len(data))]
    if data[:8] == b'MDLTEXPK':
        p = parse(data)
        out = []
        for o, s in p['items']:
            out += [(o2, s2) for o2, s2 in models_at(data, o)]
        return out
    if data[:8] == b'G1M_PACK':
        return models_at(data, 0)
    return []


def models_at(data, base):
    if data[base:base + 8] == b'G1M_PACK':
        return parse(data, base)['items']
    if data[base:base + 4] == b'_M1G':
        return [(base, struct.unpack_from('<I', data, base + 8)[0])]
    return []


def textures(data):
    """EXARG000 inside an MDLTEXPK: [(offset, size)] of each G1T."""
    if data[:8] != b'MDLTEXPK':
        return []
    p = parse(data)
    x = p['extra']
    if data[x:x + 8] == b'EXARG000':
        return parse(data, x)['items']
    return []
