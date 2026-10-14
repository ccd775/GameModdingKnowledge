"""Rebuild i30 .model assets: drop/replace sections, keep absolute string offsets valid, refresh toc header.

Absolute DAT1 string offsets live only in ModelMaterial (path/name per material) and ModelLookBuilt (look name
at +76 of every 80-byte look) - verified by scanning both protagonist suits for words that hit a string start.
"""
import struct
from sm2_dat1 import DAT1, MODEL_ALIGN

T_MAT, T_LOOKBUILT, T_GEOM = 0x3250BB80, 0x811902D7, 0xF4EA9E18
ZIVA_TAGS = (0x6694064E, 0x06E24ED4, 0x55187F02)   # ModelAnimZiva2Info, ModelAnimVertInfo2, ModelAnimVertSmoothInfo


def split_asset(raw):
    pairs = raw[5]
    extra = struct.unpack_from('<H', raw, 6)[0]
    hl = 8 + 8 * pairs + extra
    return bytes(raw[:hl]), DAT1(raw, hl)


def rebase_strings(d, delta):
    if not delta:
        return
    m = bytearray(d.get(T_MAT))
    n = len(m) // 32
    for i in range(n):
        for k in (0, 8):
            v = struct.unpack_from('<I', m, 16 * i + k)[0]
            struct.pack_into('<I', m, 16 * i + k, v + delta)
    d.sections[T_MAT] = bytes(m)
    lb = bytearray(d.get(T_LOOKBUILT))
    nl = struct.unpack_from('<I', lb, 0)[0] // 80
    for i in range(nl):
        v = struct.unpack_from('<I', lb, 80 * i + 76)[0]
        struct.pack_into('<I', lb, 80 * i + 76, v + delta)
    d.sections[T_LOOKBUILT] = bytes(lb)


def save_model(header, d, base_before):
    """Serialise with original alignment rules, fix string offsets, and refresh the two header pairs:
    pair0.A = offset of ModelSubsetGeomData, pair1.A = its size (top 2 bits and B kept from the original)."""
    rebase_strings(d, d.string_base() - base_before)
    body = d.save(MODEL_ALIGN)
    # locate geom offset in the saved table
    n = struct.unpack_from('<H', body, 12)[0]
    geo = None
    for i in range(n):
        t, o, s = struct.unpack_from('<III', body, 16 + 12 * i)
        if t == T_GEOM:
            geo = (o, s)
    h = bytearray(header)
    a0, b0, a1, b1 = struct.unpack_from('<IIII', h, 8)
    assert geo[0] < 1 << 30 and geo[1] < 1 << 30
    struct.pack_into('<I', h, 8, (a0 & 0xC0000000) | geo[0])
    struct.pack_into('<I', h, 16, (a1 & 0xC0000000) | geo[1])
    return bytes(h), body


T_BUILT = 0x283D0383
BUILT_HAS_ANIMVERT = 0x10000000   # set exactly when ModelAnimVertInfo2 exists (174 hero models surveyed)


def strip(raw, tags=ZIVA_TAGS, clear_flags=0):
    header, d = split_asset(raw)
    base = d.string_base()
    for t in tags:
        d.remove(t)
    if clear_flags:
        b = bytearray(d.get(T_BUILT))
        struct.pack_into('<I', b, 0, struct.unpack_from('<I', b, 0)[0] & ~clear_flags)
        d.sections[T_BUILT] = bytes(b)
    return save_model(header, d, base)
