"""Decode a cooked UE 4.11 UAnimSequence that uses AKF_PerTrackCompression (Days Gone face anims; CUE4Parse returns
constant tracks for these).

Layout (UE 4.11 AnimSequence.cpp / AnimEncoding_PerTrackCompression.cpp / AnimationCompression.h):
export = tagged properties, None, int32 guid flag, FGuid SkeletonGuid, FStripDataFlags (2 bytes), int32 NumBytes,
CompressedByteStream. CompressedTrackOffsets holds [trans, rot] stream offsets per track (-1 = identity),
CompressedScaleOffsets (if present) one per track. A track = int32 header (NumKeys 0-23, flags 24-27 (bit 27 = frame
table), format 28-31), fixed bytes (IntervalFixed32: min/range float pairs for the flagged components), keys, then a
frame table aligned to 4 (uint8 per key if NumFrames < 256 else uint16).

decode(path) -> dict(frames, length, additive, tracks=[{bone_index, t: (F,3), q: (F,4) xyzw}])  sampled at every frame
"""
import argparse, struct, sys
import numpy as np
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import upkg

ACF_None, ACF_Float96NoW, ACF_Fixed48NoW, ACF_IntervalFixed32NoW, ACF_Fixed32NoW, ACF_Float32NoW, ACF_Identity = range(7)
ROT_STRIDE = [4, 4, 2, 4, 4, 4, 0]
NUM_COMP = [4] * 8 + [3, 1, 1, 2, 1, 2, 2, 3] * 2 + [6, 2, 2, 4, 2, 4, 4, 6] + [1] * 16 + [0] * 8


def _sizes(fmt, flags, rot):
    comp = NUM_COMP[(flags & 7) | (fmt << 3)]
    size = ROT_STRIDE[fmt]           # 4.11 GetAllSizesFromFormat uses the rotation strides for every track kind
    if fmt == ACF_IntervalFixed32NoW:
        return size, comp * 4          # one packed key, comp floats of bounds
    return comp * size, 0


def _key(fmt, flags, buf, top, kd, rot):
    if fmt == ACF_Identity:
        return np.array([0, 0, 0, 1.0]) if rot else np.zeros(3)
    if fmt == ACF_IntervalFixed32NoW:
        mins, rng = [0.0] * 3, [0.0] * 3
        o = top
        for c in range(3):
            if flags & (1 << c):
                mins[c], rng[c] = struct.unpack_from('<2f', buf, o); o += 8
        p = struct.unpack_from('<I', buf, kd)[0]
        if rot:
            ux, uy, uz = p >> 21, (p & 0x1ffc00) >> 10, p & 0x3ff
            x = (ux - 1023) / 1023.0 * rng[0] + mins[0]
            y = (uy - 1023) / 1023.0 * rng[1] + mins[1]
            z = (uz - 511) / 511.0 * rng[2] + mins[2]
        else:
            uz, uy, ux = p >> 21, (p & 0x1ffc00) >> 10, p & 0x3ff
            x = (ux - 511) / 511.0 * rng[0] + mins[0]
            y = (uy - 1023) / 1023.0 * rng[1] + mins[1]
            z = (uz - 1023) / 1023.0 * rng[2] + mins[2]
            return np.array([x, y, z])
    elif fmt == ACF_Float96NoW:
        if rot:
            x, y, z = struct.unpack_from('<3f', buf, kd)
        else:
            v = [0.0] * 3; o = kd
            for c in range(3):
                if (flags & 7) == 0 or flags & (1 << c):
                    v[c] = struct.unpack_from('<f', buf, o)[0]; o += 4
            return np.array(v)
    elif fmt == ACF_Fixed48NoW:
        v = [32767] * 3; o = kd
        for c in range(3):
            if (flags & 7) == 0 or flags & (1 << c):
                v[c] = struct.unpack_from('<H', buf, o)[0]; o += 2
        if not rot:
            return np.array([(a - 255) for a in v], float)   # see the 4.11 comment: translation fixed48 is broken
        x, y, z = [(a - 32767) * 3.0518509475997192297128208258309e-5 for a in v]
    elif fmt == ACF_Fixed32NoW:
        p = struct.unpack_from('<I', buf, kd)[0]
        x = ((p >> 21) - 1023) / 1023.0; y = (((p & 0x1ffc00) >> 10) - 1023) / 1023.0; z = ((p & 0x3ff) - 511) / 511.0
    elif fmt == ACF_None:
        return np.array(struct.unpack_from('<4f' if rot else '<3f', buf, kd))
    else:
        raise ValueError("format %d not handled" % fmt)
    w2 = 1 - x * x - y * y - z * z
    return np.array([x, y, z, np.sqrt(w2) if w2 > 0 else 0.0])


def _track(buf, off, nframes, rot):
    """decode the track whose header is at off -> (values per frame, offset of the next track)"""
    hdr = struct.unpack_from('<i', buf, off)[0]
    nkeys, flags, fmt = hdr & 0xFFFFFF, (hdr >> 24) & 0xF, (hdr >> 28) & 0xF
    bpk, fixed = _sizes(fmt, flags, rot)
    top = off + 4
    keys = np.array([_key(fmt, flags, buf, top, top + fixed + i * bpk, rot) for i in range(nkeys)])
    nxt = top + fixed + bpk * nkeys
    if flags & 8:
        ft = (nxt + 3) & ~3
        fsz = 1 if nframes <= 0xFF else 2
        fr = np.array(struct.unpack_from('<%d%s' % (nkeys, 'B' if fsz == 1 else 'H'), buf, ft), float)
        nxt = ft + fsz * nkeys
    else:
        fr = np.linspace(0, nframes - 1, nkeys)
    nxt = (nxt + 3) & ~3
    if nkeys <= 1:
        return np.repeat(keys[:1], nframes, 0), nxt
    out = np.empty((nframes, keys.shape[1]))
    for c in range(keys.shape[1]):
        out[:, c] = np.interp(np.arange(nframes), fr, keys[:, c])
    if rot:
        out /= np.linalg.norm(out, axis=1, keepdims=True)
    return out, nxt


def decode(path):
    data = open(path, 'rb').read()
    pkg = upkg.Package(data)
    d = pkg.export_data(0)
    orig = upkg.parse_props
    def shallow(pkg_, data_, pos=0, end=None, depth=0):   # nested structs such as RawCurveData are not needed
        return upkg.PList() if depth > 0 else orig(pkg_, data_, pos, end, depth)
    upkg.parse_props = shallow
    try:
        props = upkg.parse_props(pkg, d)
    finally:
        upkg.parse_props = orig
    P = {p.name: p for p in props}
    def struct_items(p):
        cnt = struct.unpack_from('<i', d, p.vstart)[0]; items = []; ipos = p.vstart + 4
        for _ in range(cnt):
            ch = upkg.parse_props(pkg, d, ipos, p.vend, 1); items.append(ch); ipos = ch.end
        return items
    def ival(n): return struct.unpack_from('<i', d, P[n].vstart)[0]
    def iarr(n):
        p = P[n]; cnt = struct.unpack_from('<i', d, p.vstart)[0]
        return list(struct.unpack_from('<%di' % cnt, d, p.vstart + 4))
    def byte_enum(n):
        p = P.get(n)
        return pkg.name(struct.unpack_from('<ii', d, p.vend - 8)) if p else None
    nframes = ival('NumFrames')
    # TrackToSkeletonMapTable: array of struct {int32 BoneTreeIndex}
    bones = [struct.unpack_from('<i', d, next(x for x in item if x.name == 'BoneTreeIndex').vstart)[0]
             for item in struct_items(P['TrackToSkeletonMapTable'])]
    offs = iarr('CompressedTrackOffsets')
    # after None: guid flag, SkeletonGuid, the curves' own data (RawCurveData), strip flags, NumBytes, stream (to the end)
    pos = next(o for o in range(props[-1].vend + 8, len(d) - 3)
               if o + 4 + struct.unpack_from('<i', d, o)[0] == len(d))
    nbytes = struct.unpack_from('<i', d, pos)[0]
    buf = d[pos + 4:]
    # the file holds the tracks one after another (trans, rot, scale per bone); the offsets only place them in memory
    soffs = None
    if 'CompressedScaleOffsets' in P:
        sp = next(x for x in orig(pkg, d, P['CompressedScaleOffsets'].vstart, P['CompressedScaleOffsets'].vend, 1)
                  if x.name == 'OffsetData')
        n = struct.unpack_from('<i', d, sp.vstart)[0]
        soffs = struct.unpack_from('<%di' % n, d, sp.vstart + 4)
    tracks = []
    o = 0
    for i, b in enumerate(bones):
        t = q = sc = None
        if offs[2 * i] >= 0: t, o = _track(buf, o, nframes, False)
        if offs[2 * i + 1] >= 0: q, o = _track(buf, o, nframes, True)
        if soffs is not None and soffs[i] >= 0: sc, o = _track(buf, o, nframes, False)
        tracks.append({'bone_index': b, 's': sc,
                       't': t if t is not None else np.zeros((nframes, 3)),
                       'q': q if q is not None else np.tile([0, 0, 0, 1.0], (nframes, 1)),
                       'has_t': offs[2 * i] >= 0, 'has_q': offs[2 * i + 1] >= 0})
    assert o == len(buf), (o, len(buf))
    return {'frames': nframes, 'additive': byte_enum('AdditiveAnimType'), 'tracks': tracks,
            'key_format': byte_enum('KeyEncodingFormat')}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('anim', help='raw cooked AnimSequence .uasset (DgExport raw)')
    r = decode(ap.parse_args().anim)
    print(r['frames'], r['additive'], r['key_format'], len(r['tracks']))
